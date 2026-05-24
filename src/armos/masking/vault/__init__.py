# SPDX-License-Identifier: MIT
from .base import BaseVault
from .memory import MemoryVault

try:
    from .redis import RedisVault
    _redis_available = True
except ImportError:
    RedisVault = None
    _redis_available = False

__all__ = ["BaseVault", "MemoryVault", "RedisVault"]

_DEFAULT_REDIS_TTL = 86400


def build_vault(
    store: str | None = None,
    redis_url: str | None = None,
    ttl: int = _DEFAULT_REDIS_TTL,
) -> BaseVault:
    """
    Factory function. Builds the appropriate vault from the store argument.

    Args:
        store:     None for in-memory, or "redis" for Redis-backed vault
        redis_url: Redis connection URL e.g. "redis://localhost:6379" (required when store="redis")
        ttl:       Redis TTL in seconds (ignored for memory vault)
    """
    if store is None:
        return MemoryVault()

    if store == "redis":
        if not _redis_available:
            raise ImportError(
                "Redis support requires the redis package. Install with: pip install armos[redis]"
            )
        if not redis_url:
            raise ValueError(
                "redis_url is required when store='redis'. "
                "Example: Armos(store='redis', redis_url='redis://localhost:6379')"
            )
        return RedisVault(url=redis_url, ttl=ttl)

    raise ValueError(
        f"Unsupported store: '{store}'. Valid options: None (in-memory) or 'redis'."
    )
