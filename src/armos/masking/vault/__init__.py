# SPDX-License-Identifier: MIT
from .base import BaseVault
from .memory import MemoryVault
from .redis import RedisVault

__all__ = ["BaseVault", "MemoryVault", "RedisVault"]


def build_vault(store: str | None = None, ttl: int = RedisVault.DEFAULT_TTL) -> BaseVault:
    """
    Factory function. Builds the appropriate vault from the store argument.

    Args:
        store: None for in-memory, or a Redis URL e.g. "redis://localhost:6379"
        ttl:   Redis TTL in seconds (ignored for memory vault)
    """
    if store is None:
        return MemoryVault()

    if isinstance(store, str) and (
        store.startswith("redis://") or store.startswith("rediss://")
    ):
        return RedisVault(url=store, ttl=ttl)

    raise ValueError(
        f"Unsupported store: '{store}'. "
        f"Pass a Redis URL like 'redis://localhost:6379' or None for in-memory."
    )
