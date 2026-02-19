"""
Rate limiting per API Key for 1min-Gateway.

Provides individual rate limits per API key to prevent
any single user from consuming all available quota.
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("1min-gateway.rate-limiter")


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    enabled: bool = True


@dataclass
class UsageRecord:
    """Record of API usage for a key."""

    minute_count: int = 0
    minute_start: float = 0.0
    hour_count: int = 0
    hour_start: float = 0.0
    day_count: int = 0
    day_start: float = 0.0


class InMemoryRateLimitStore:
    """
    In-memory store for rate limit counters.

    For production, consider using Redis or Memcached for distributed rate limiting.
    """

    def __init__(self):
        self._store: dict[str, UsageRecord] = {}

    def get(self, key: str) -> UsageRecord | None:
        """Get usage record for a key."""
        return self._store.get(key)

    def set(self, key: str, record: UsageRecord) -> None:
        """Set usage record for a key."""
        self._store[key] = record

    def delete(self, key: str) -> None:
        """Delete usage record for a key."""
        if key in self._store:
            del self._store[key]

    def clear_all(self) -> None:
        """Clear all records."""
        self._store.clear()

    def get_all_keys(self) -> list[str]:
        """Get all tracked keys."""
        return list(self._store.keys())


class ApiKeyRateLimiter:
    """
    Rate limiter that enforces limits per API key.

    Features:
    - Per-minute, per-hour, per-day limits
    - Configurable limits per key
    - Usage statistics
    - Automatic cleanup of expired records
    """

    def __init__(
        self,
        default_config: RateLimitConfig | None = None,
        store: InMemoryRateLimitStore | None = None,
    ):
        self._default_config = default_config or RateLimitConfig()
        self._store = store or InMemoryRateLimitStore()
        self._custom_configs: dict[str, RateLimitConfig] = {}
        self._stats = {
            "total_requests": 0,
            "allowed_requests": 0,
            "denied_requests": 0,
        }

    def _hash_key(self, api_key: str) -> str:
        """Hash the API key for storage (privacy)."""
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]

    def _get_config(self, api_key: str) -> RateLimitConfig:
        """Get rate limit config for an API key."""
        return self._custom_configs.get(api_key, self._default_config)

    def set_custom_limit(
        self,
        api_key: str,
        requests_per_minute: int | None = None,
        requests_per_hour: int | None = None,
        requests_per_day: int | None = None,
    ) -> None:
        """
        Set custom rate limits for a specific API key.

        Args:
            api_key: The API key to configure
            requests_per_minute: Custom per-minute limit (None = use default)
            requests_per_hour: Custom per-hour limit (None = use default)
            requests_per_day: Custom per-day limit (None = use default)
        """
        default = self._default_config
        config = RateLimitConfig(
            requests_per_minute=requests_per_minute or default.requests_per_minute,
            requests_per_hour=requests_per_hour or default.requests_per_hour,
            requests_per_day=requests_per_day or default.requests_per_day,
            enabled=True,
        )
        self._custom_configs[api_key] = config
        logger.info(f"Custom rate limit set for API key: {self._hash_key(api_key)}")

    def check_rate_limit(self, api_key: str) -> tuple[bool, dict[str, Any]]:
        """
        Check if an API key is within rate limits.

        Args:
            api_key: The API key to check

        Returns:
            Tuple of (is_allowed, info_dict)
            info_dict contains: limit_exceeded, retry_after, current_usage
        """
        if not self._default_config.enabled:
            return True, {"limit_exceeded": None, "retry_after": 0, "current_usage": {}}

        self._stats["total_requests"] += 1
        config = self._get_config(api_key)

        if not config.enabled:
            return True, {"limit_exceeded": None, "retry_after": 0, "current_usage": {}}

        now = time.time()
        key_hash = self._hash_key(api_key)
        record = self._store.get(key_hash)

        if record is None:
            record = UsageRecord(
                minute_count=0,
                minute_start=now,
                hour_count=0,
                hour_start=now,
                day_count=0,
                day_start=now,
            )

        # Reset counters if time windows have expired
        if now - record.minute_start >= 60:
            record.minute_count = 0
            record.minute_start = now

        if now - record.hour_start >= 3600:
            record.hour_count = 0
            record.hour_start = now

        if now - record.day_start >= 86400:
            record.day_count = 0
            record.day_start = now

        # Check limits
        info: dict[str, Any] = {
            "limit_exceeded": None,
            "retry_after": 0,
            "current_usage": {
                "minute": record.minute_count,
                "hour": record.hour_count,
                "day": record.day_count,
            },
            "limits": {
                "minute": config.requests_per_minute,
                "hour": config.requests_per_hour,
                "day": config.requests_per_day,
            },
        }

        # Check day limit
        if record.day_count >= config.requests_per_day:
            retry_after = int(86400 - (now - record.day_start))
            info["limit_exceeded"] = "day"
            info["retry_after"] = retry_after
            self._stats["denied_requests"] += 1
            logger.warning(f"Rate limit exceeded (day) for API key: {key_hash}")
            return False, info

        # Check hour limit
        if record.hour_count >= config.requests_per_hour:
            retry_after = int(3600 - (now - record.hour_start))
            info["limit_exceeded"] = "hour"
            info["retry_after"] = retry_after
            self._stats["denied_requests"] += 1
            logger.warning(f"Rate limit exceeded (hour) for API key: {key_hash}")
            return False, info

        # Check minute limit
        if record.minute_count >= config.requests_per_minute:
            retry_after = int(60 - (now - record.minute_start))
            info["limit_exceeded"] = "minute"
            info["retry_after"] = retry_after
            self._stats["denied_requests"] += 1
            logger.warning(f"Rate limit exceeded (minute) for API key: {key_hash}")
            return False, info

        # Increment counters
        record.minute_count += 1
        record.hour_count += 1
        record.day_count += 1
        self._store.set(key_hash, record)
        self._stats["allowed_requests"] += 1

        return True, info

    def get_usage(self, api_key: str) -> dict[str, Any] | None:
        """
        Get current usage for an API key.

        Args:
            api_key: The API key to check

        Returns:
            Usage dict or None if not found
        """
        key_hash = self._hash_key(api_key)
        record = self._store.get(key_hash)

        if record is None:
            return None

        config = self._get_config(api_key)

        return {
            "minute": {
                "used": record.minute_count,
                "limit": config.requests_per_minute,
                "remaining": max(0, config.requests_per_minute - record.minute_count),
            },
            "hour": {
                "used": record.hour_count,
                "limit": config.requests_per_hour,
                "remaining": max(0, config.requests_per_hour - record.hour_count),
            },
            "day": {
                "used": record.day_count,
                "limit": config.requests_per_day,
                "remaining": max(0, config.requests_per_day - record.day_count),
            },
        }

    def reset_usage(self, api_key: str) -> bool:
        """
        Reset usage counters for an API key.

        Args:
            api_key: The API key to reset

        Returns:
            True if reset, False if not found
        """
        key_hash = self._hash_key(api_key)
        if self._store.get(key_hash):
            self._store.delete(key_hash)
            logger.info(f"Usage reset for API key: {key_hash}")
            return True
        return False

    def get_stats(self) -> dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            **self._stats,
            "tracked_keys": len(self._store.get_all_keys()),
            "custom_configs": len(self._custom_configs),
            "default_limits": {
                "minute": self._default_config.requests_per_minute,
                "hour": self._default_config.requests_per_hour,
                "day": self._default_config.requests_per_day,
            },
        }

    def cleanup_expired(self) -> int:
        """
        Remove expired records from the store.

        Returns:
            Number of records removed
        """
        now = time.time()
        expired_keys = []

        for key in self._store.get_all_keys():
            record = self._store.get(key)
            if record and now - record.day_start >= 86400:
                expired_keys.append(key)

        for key in expired_keys:
            self._store.delete(key)

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired rate limit records")

        return len(expired_keys)


# Global rate limiter instance
api_key_rate_limiter = ApiKeyRateLimiter(
    default_config=RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        requests_per_day=10000,
    )
)
