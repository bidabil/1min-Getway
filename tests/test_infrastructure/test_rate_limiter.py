"""
Tests for rate_limiter.py module.

Tests cover:
- RateLimitConfig dataclass
- UsageRecord dataclass
- InMemoryRateLimitStore class
- ApiKeyRateLimiter class
"""

import time

from src.infrastructure.rate_limiter import (
    ApiKeyRateLimiter,
    InMemoryRateLimitStore,
    RateLimitConfig,
    UsageRecord,
)


class TestRateLimitConfig:
    """Tests for RateLimitConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RateLimitConfig()
        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000
        assert config.requests_per_day == 10000
        assert config.enabled is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = RateLimitConfig(
            requests_per_minute=30,
            requests_per_hour=500,
            requests_per_day=5000,
            enabled=False,
        )
        assert config.requests_per_minute == 30
        assert config.requests_per_hour == 500
        assert config.requests_per_day == 5000
        assert config.enabled is False


class TestUsageRecord:
    """Tests for UsageRecord dataclass."""

    def test_default_record(self):
        """Test default usage record values."""
        record = UsageRecord()
        assert record.minute_count == 0
        assert record.minute_start == 0.0
        assert record.hour_count == 0
        assert record.hour_start == 0.0
        assert record.day_count == 0
        assert record.day_start == 0.0

    def test_custom_record(self):
        """Test custom usage record values."""
        record = UsageRecord(
            minute_count=10,
            minute_start=100.0,
            hour_count=100,
            hour_start=1000.0,
            day_count=500,
            day_start=10000.0,
        )
        assert record.minute_count == 10
        assert record.minute_start == 100.0
        assert record.hour_count == 100
        assert record.hour_start == 1000.0
        assert record.day_count == 500
        assert record.day_start == 10000.0


class TestInMemoryRateLimitStore:
    """Tests for InMemoryRateLimitStore class."""

    def test_store_creation(self):
        """Test store creation."""
        store = InMemoryRateLimitStore()
        assert store._store == {}

    def test_set_and_get(self):
        """Test set and get operations."""
        store = InMemoryRateLimitStore()
        record = UsageRecord(minute_count=5)
        store.set("test_key", record)

        result = store.get("test_key")
        assert result is not None
        assert result.minute_count == 5

    def test_get_nonexistent(self):
        """Test get for nonexistent key."""
        store = InMemoryRateLimitStore()
        result = store.get("nonexistent")
        assert result is None

    def test_delete(self):
        """Test delete operation."""
        store = InMemoryRateLimitStore()
        record = UsageRecord()
        store.set("test_key", record)

        store.delete("test_key")
        assert store.get("test_key") is None

    def test_delete_nonexistent(self):
        """Test delete for nonexistent key (no error)."""
        store = InMemoryRateLimitStore()
        # Should not raise
        store.delete("nonexistent")

    def test_clear_all(self):
        """Test clear_all operation."""
        store = InMemoryRateLimitStore()
        store.set("key1", UsageRecord())
        store.set("key2", UsageRecord())
        store.set("key3", UsageRecord())

        store.clear_all()
        assert store.get_all_keys() == []

    def test_get_all_keys(self):
        """Test get_all_keys operation."""
        store = InMemoryRateLimitStore()
        store.set("key1", UsageRecord())
        store.set("key2", UsageRecord())

        keys = store.get_all_keys()
        assert len(keys) == 2
        assert "key1" in keys
        assert "key2" in keys


class TestApiKeyRateLimiter:
    """Tests for ApiKeyRateLimiter class."""

    def test_limiter_creation_default(self):
        """Test limiter creation with default config."""
        limiter = ApiKeyRateLimiter()
        assert limiter._default_config.requests_per_minute == 60
        assert limiter._default_config.enabled is True

    def test_limiter_creation_custom_config(self):
        """Test limiter creation with custom config."""
        config = RateLimitConfig(
            requests_per_minute=30,
            requests_per_hour=500,
        )
        limiter = ApiKeyRateLimiter(default_config=config)
        assert limiter._default_config.requests_per_minute == 30
        assert limiter._default_config.requests_per_hour == 500

    def test_hash_key(self):
        """Test API key hashing."""
        limiter = ApiKeyRateLimiter()
        hash1 = limiter._hash_key("test_key_1")
        hash2 = limiter._hash_key("test_key_2")

        # Hashes should be different for different keys
        assert hash1 != hash2
        # Hash should be 32 characters (16 bytes hex-encoded)
        assert len(hash1) == 32
        # Same key should produce same hash
        assert limiter._hash_key("test_key_1") == hash1

    def test_check_rate_limit_allowed(self):
        """Test rate limit check when allowed."""
        limiter = ApiKeyRateLimiter()
        is_allowed, info = limiter.check_rate_limit("test_key")

        assert is_allowed is True
        assert info["limit_exceeded"] is None
        # Note: current_usage shows count BEFORE increment (0 on first call)
        assert info["current_usage"]["minute"] == 0

        # Second call should show 1 (the previous count)
        is_allowed2, info2 = limiter.check_rate_limit("test_key")
        assert is_allowed2 is True
        assert info2["current_usage"]["minute"] == 1

    def test_check_rate_limit_disabled_globally(self):
        """Test rate limit check when disabled globally."""
        config = RateLimitConfig(enabled=False)
        limiter = ApiKeyRateLimiter(default_config=config)

        is_allowed, info = limiter.check_rate_limit("test_key")

        assert is_allowed is True
        assert info["limit_exceeded"] is None

    def test_check_rate_limit_disabled_for_key(self):
        """Test rate limit check when disabled for specific key."""
        limiter = ApiKeyRateLimiter()
        # Set a custom config with enabled=False for this key
        limiter._custom_configs["test_key"] = RateLimitConfig(enabled=False)

        is_allowed, info = limiter.check_rate_limit("test_key")

        assert is_allowed is True

    def test_check_rate_limit_minute_exceeded(self):
        """Test rate limit when minute limit exceeded."""
        config = RateLimitConfig(requests_per_minute=2)
        limiter = ApiKeyRateLimiter(default_config=config)

        # First two requests should be allowed
        limiter.check_rate_limit("test_key")
        limiter.check_rate_limit("test_key")

        # Third request should be denied
        is_allowed, info = limiter.check_rate_limit("test_key")

        assert is_allowed is False
        assert info["limit_exceeded"] == "minute"
        assert info["retry_after"] > 0

    def test_check_rate_limit_hour_exceeded(self):
        """Test rate limit when hour limit exceeded."""
        config = RateLimitConfig(requests_per_minute=100, requests_per_hour=2)
        limiter = ApiKeyRateLimiter(default_config=config)

        # First two requests should be allowed
        limiter.check_rate_limit("test_key")
        limiter.check_rate_limit("test_key")

        # Third request should be denied (hour limit)
        is_allowed, info = limiter.check_rate_limit("test_key")

        assert is_allowed is False
        assert info["limit_exceeded"] == "hour"

    def test_check_rate_limit_day_exceeded(self):
        """Test rate limit when day limit exceeded."""
        config = RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=100,
            requests_per_day=2,
        )
        limiter = ApiKeyRateLimiter(default_config=config)

        # First two requests should be allowed
        limiter.check_rate_limit("test_key")
        limiter.check_rate_limit("test_key")

        # Third request should be denied (day limit)
        is_allowed, info = limiter.check_rate_limit("test_key")

        assert is_allowed is False
        assert info["limit_exceeded"] == "day"

    def test_set_custom_limit(self):
        """Test setting custom limits for a key."""
        limiter = ApiKeyRateLimiter()
        limiter.set_custom_limit(
            "custom_key",
            requests_per_minute=10,
            requests_per_hour=100,
            requests_per_day=1000,
        )

        config = limiter._get_config("custom_key")
        assert config.requests_per_minute == 10
        assert config.requests_per_hour == 100
        assert config.requests_per_day == 1000

    def test_set_custom_limit_partial(self):
        """Test setting partial custom limits."""
        limiter = ApiKeyRateLimiter()
        limiter.set_custom_limit("custom_key", requests_per_minute=10)

        config = limiter._get_config("custom_key")
        assert config.requests_per_minute == 10
        # Other values should use defaults
        assert config.requests_per_hour == 1000
        assert config.requests_per_day == 10000

    def test_get_usage(self):
        """Test getting usage for a key."""
        limiter = ApiKeyRateLimiter()
        limiter.check_rate_limit("test_key")
        limiter.check_rate_limit("test_key")

        usage = limiter.get_usage("test_key")

        assert usage is not None
        assert usage["minute"]["used"] == 2
        assert usage["minute"]["remaining"] == 58

    def test_get_usage_nonexistent(self):
        """Test getting usage for nonexistent key."""
        limiter = ApiKeyRateLimiter()
        usage = limiter.get_usage("nonexistent")

        assert usage is None

    def test_reset_usage(self):
        """Test resetting usage for a key."""
        limiter = ApiKeyRateLimiter()
        limiter.check_rate_limit("test_key")

        result = limiter.reset_usage("test_key")

        assert result is True
        assert limiter.get_usage("test_key") is None

    def test_reset_usage_nonexistent(self):
        """Test resetting usage for nonexistent key."""
        limiter = ApiKeyRateLimiter()
        result = limiter.reset_usage("nonexistent")

        assert result is False

    def test_get_stats(self):
        """Test getting limiter statistics."""
        limiter = ApiKeyRateLimiter()
        limiter.check_rate_limit("key1")
        limiter.check_rate_limit("key2")

        stats = limiter.get_stats()

        assert stats["total_requests"] == 2
        assert stats["allowed_requests"] == 2
        assert stats["denied_requests"] == 0
        assert stats["tracked_keys"] == 2

    def test_get_stats_with_denials(self):
        """Test statistics with denied requests."""
        config = RateLimitConfig(requests_per_minute=1)
        limiter = ApiKeyRateLimiter(default_config=config)

        limiter.check_rate_limit("test_key")  # Allowed
        limiter.check_rate_limit("test_key")  # Denied

        stats = limiter.get_stats()

        assert stats["total_requests"] == 2
        assert stats["allowed_requests"] == 1
        assert stats["denied_requests"] == 1

    def test_cleanup_expired(self):
        """Test cleanup of expired records."""
        limiter = ApiKeyRateLimiter()
        limiter.check_rate_limit("test_key")

        # Manually expire the record
        key_hash = limiter._hash_key("test_key")
        record = limiter._store.get(key_hash)
        record.day_start = time.time() - 100000  # Old timestamp
        limiter._store.set(key_hash, record)

        removed = limiter.cleanup_expired()

        assert removed == 1
        assert limiter.get_usage("test_key") is None

    def test_cleanup_expired_none(self):
        """Test cleanup when no expired records."""
        limiter = ApiKeyRateLimiter()
        limiter.check_rate_limit("test_key")

        removed = limiter.cleanup_expired()

        assert removed == 0

    def test_time_window_reset_minute(self):
        """Test that minute counter resets after time window."""
        config = RateLimitConfig(requests_per_minute=1)
        limiter = ApiKeyRateLimiter(default_config=config)

        # First request
        limiter.check_rate_limit("test_key")

        # Manually expire the minute window
        key_hash = limiter._hash_key("test_key")
        record = limiter._store.get(key_hash)
        record.minute_start = time.time() - 61  # Expired
        limiter._store.set(key_hash, record)

        # Should be allowed again (counter reset)
        is_allowed, info = limiter.check_rate_limit("test_key")

        assert is_allowed is True
        # Counter was reset, so current_usage shows 0 (before increment)
        assert info["current_usage"]["minute"] == 0

    def test_time_window_reset_hour(self):
        """Test that hour counter resets after time window."""
        config = RateLimitConfig(requests_per_hour=1)
        limiter = ApiKeyRateLimiter(default_config=config)

        # First request
        limiter.check_rate_limit("test_key")

        # Manually expire the hour window
        key_hash = limiter._hash_key("test_key")
        record = limiter._store.get(key_hash)
        record.hour_start = time.time() - 3601  # Expired
        limiter._store.set(key_hash, record)

        # Should be allowed again
        is_allowed, info = limiter.check_rate_limit("test_key")

        assert is_allowed is True

    def test_time_window_reset_day(self):
        """Test that day counter resets after time window."""
        config = RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=100,
            requests_per_day=1,
        )
        limiter = ApiKeyRateLimiter(default_config=config)

        # First request
        limiter.check_rate_limit("test_key")

        # Manually expire the day window
        key_hash = limiter._hash_key("test_key")
        record = limiter._store.get(key_hash)
        record.day_start = time.time() - 86401  # Expired
        limiter._store.set(key_hash, record)

        # Should be allowed again
        is_allowed, info = limiter.check_rate_limit("test_key")

        assert is_allowed is True

    def test_multiple_keys_independent(self):
        """Test that multiple keys have independent limits."""
        config = RateLimitConfig(requests_per_minute=1)
        limiter = ApiKeyRateLimiter(default_config=config)

        # First key
        is_allowed1, _ = limiter.check_rate_limit("key1")
        # Second key
        is_allowed2, _ = limiter.check_rate_limit("key2")
        # First key again (should be denied)
        is_allowed3, _ = limiter.check_rate_limit("key1")

        assert is_allowed1 is True
        assert is_allowed2 is True
        assert is_allowed3 is False

    def test_info_contains_limits(self):
        """Test that info dict contains limit information."""
        config = RateLimitConfig(
            requests_per_minute=30,
            requests_per_hour=500,
            requests_per_day=5000,
        )
        limiter = ApiKeyRateLimiter(default_config=config)

        _, info = limiter.check_rate_limit("test_key")

        assert info["limits"]["minute"] == 30
        assert info["limits"]["hour"] == 500
        assert info["limits"]["day"] == 5000

    def test_usage_remaining_calculation(self):
        """Test remaining calculation in usage."""
        config = RateLimitConfig(requests_per_minute=10)
        limiter = ApiKeyRateLimiter(default_config=config)

        limiter.check_rate_limit("test_key")
        limiter.check_rate_limit("test_key")
        limiter.check_rate_limit("test_key")

        usage = limiter.get_usage("test_key")

        assert usage["minute"]["used"] == 3
        assert usage["minute"]["remaining"] == 7
