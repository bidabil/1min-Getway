"""
Cache for available models with TTL (Time To Live).

Provides caching to avoid repeated model list fetches and
enable automatic refresh of available models.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("1min-gateway.model-cache")


@dataclass
class CacheEntry:
    """A cached entry with value and expiration time."""

    value: Any
    expires_at: float
    created_at: float = field(default_factory=time.time)


class ModelCache:
    """
    Simple in-memory cache with TTL support.

    Features:
    - TTL-based expiration
    - Manual refresh
    - Thread-safe operations
    - Cache statistics

    Usage:
        cache = ModelCache(ttl_seconds=300)  # 5 minutes
        models = cache.get_or_fetch("models", fetch_models)
    """

    def __init__(
        self,
        ttl_seconds: int = 300,
        max_size: int = 100,
    ):
        """
        Initialize the cache.

        Args:
            ttl_seconds: Time to live in seconds (default: 5 minutes)
            max_size: Maximum number of entries (default: 100)
        """
        self._cache: dict[str, CacheEntry] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "refreshes": 0,
        }

    def get(self, key: str) -> Any | None:
        """
        Get a value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        entry = self._cache.get(key)

        if entry is None:
            self._stats["misses"] += 1
            return None

        if time.time() > entry.expires_at:
            # Entry expired
            del self._cache[key]
            self._stats["misses"] += 1
            self._stats["evictions"] += 1
            logger.debug(f"Cache entry expired: {key}")
            return None

        self._stats["hits"] += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override (uses default if not provided)
        """
        # Evict oldest if at max size
        if len(self._cache) >= self._max_size and key not in self._cache:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
            del self._cache[oldest_key]
            self._stats["evictions"] += 1
            logger.debug(f"Cache evicted oldest entry: {oldest_key}")

        now = time.time()
        ttl_to_use = ttl if ttl is not None else self._ttl

        self._cache[key] = CacheEntry(
            value=value,
            expires_at=now + ttl_to_use,
            created_at=now,
        )

        logger.debug(f"Cache set: {key}, TTL: {ttl_to_use}s")

    def get_or_fetch(
        self,
        key: str,
        fetch_func: Callable[[], Any],
        ttl: int | None = None,
    ) -> Any:
        """
        Get from cache or fetch if not found/expired.

        Args:
            key: Cache key
            fetch_func: Function to call if cache miss
            ttl: Optional TTL override

        Returns:
            Cached or fetched value
        """
        value = self.get(key)

        if value is not None:
            return value

        # Fetch and cache
        logger.info(f"Cache miss, fetching: {key}")
        value = fetch_func()
        self.set(key, value, ttl)

        return value

    def invalidate(self, key: str) -> bool:
        """
        Invalidate a cache entry.

        Args:
            key: Cache key

        Returns:
            True if entry was removed, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache invalidated: {key}")
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.info("Cache cleared")

    def refresh(self, key: str, fetch_func: Callable[[], Any]) -> Any:
        """
        Force refresh a cache entry.

        Args:
            key: Cache key
            fetch_func: Function to fetch fresh value

        Returns:
            Fresh value
        """
        self._stats["refreshes"] += 1
        value = fetch_func()
        self.set(key, value)
        logger.info(f"Cache refreshed: {key}")
        return value

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hits, misses, evictions, refreshes, size
        """
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests * 100 if total_requests > 0 else 0

        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "evictions": self._stats["evictions"],
            "refreshes": self._stats["refreshes"],
            "hit_rate_percent": round(hit_rate, 2),
        }

    def get_entry_info(self, key: str) -> dict[str, Any] | None:
        """
        Get information about a cache entry.

        Args:
            key: Cache key

        Returns:
            Entry info or None if not found
        """
        entry = self._cache.get(key)

        if entry is None:
            return None

        now = time.time()
        remaining_ttl = max(0, entry.expires_at - now)

        return {
            "key": key,
            "created_at": entry.created_at,
            "expires_at": entry.expires_at,
            "remaining_ttl_seconds": round(remaining_ttl, 2),
            "is_expired": remaining_ttl == 0,
        }


# Global model cache instance
model_cache = ModelCache(ttl_seconds=300)  # 5 minutes default TTL
