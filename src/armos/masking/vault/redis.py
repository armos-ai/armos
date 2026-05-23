# SPDX-License-Identifier: MIT
from typing import Optional
from .base import BaseVault

try:
    import redis as redis_lib
except ImportError:
    raise ImportError(
        "Redis support requires the redis package. "
        "Install with: pip install armos[redis]"
    )


class RedisVault(BaseVault):
    """
    Redis-backed vault. Persists token mappings across requests and processes.
    Data lives entirely in the developer's own Redis — Armos never sees it.
    """

    VAULT_PREFIX = "armos:vault:"
    REVERSE_PREFIX = "armos:rev:"
    DEFAULT_TTL = 86400  # 24 hours

    def __init__(self, url: str, ttl: int = DEFAULT_TTL):
        self._ttl = ttl
        self._client = redis_lib.from_url(url, decode_responses=True)

        try:
            self._client.ping()
        except redis_lib.ConnectionError as e:
            raise ConnectionError(
                f"Cannot connect to Redis at {url}. "
                f"Ensure Redis is running. Original error: {e}"
            )

    def store(self, real_value: str, entity_type: str) -> str:
        reverse_key = f"{self.REVERSE_PREFIX}{self.make_reverse_key(real_value, entity_type)}"

        existing_token = self._client.get(reverse_key)
        if existing_token:
            vault_key = f"{self.VAULT_PREFIX}{existing_token}"
            self._client.expire(vault_key, self._ttl)
            self._client.expire(reverse_key, self._ttl)
            return existing_token

        token = self.generate_token(real_value, entity_type)
        vault_key = f"{self.VAULT_PREFIX}{token}"

        pipe = self._client.pipeline()
        pipe.setex(vault_key, self._ttl, real_value)
        pipe.setex(reverse_key, self._ttl, token)
        pipe.execute()

        return token

    def retrieve(self, token: str) -> Optional[str]:
        vault_key = f"{self.VAULT_PREFIX}{token}"
        return self._client.get(vault_key)

    def clear(self) -> None:
        """Clear only Armos keys — never touches other Redis data."""
        for prefix in [self.VAULT_PREFIX, self.REVERSE_PREFIX]:
            keys = self._client.keys(f"{prefix}*")
            if keys:
                self._client.delete(*keys)
