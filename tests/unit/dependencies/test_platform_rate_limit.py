"""Unit tests for Platform Rate Limit with fallback and circuit breaker.

Test Coverage:
- In-memory fallback when Redis fails
- Circuit breaker state transitions
- Thread-safe counter operations
- Stale entry cleanup
- Auto-recovery when Redis becomes available
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, PropertyMock
from uuid import uuid4

from fastapi import HTTPException


class TestInMemoryRateLimitCounter:
    """Test the in-memory fallback rate limit counter."""

    def test_counter_increments_correctly(self):
        """Test that the counter increments for a given key."""
        from app.dependencies.platform_rate_limit import InMemoryRateLimitCounter

        counter = InMemoryRateLimitCounter()
        key = "test_key"
        ttl = 60

        count1 = counter.increment(key, ttl)
        count2 = counter.increment(key, ttl)
        count3 = counter.increment(key, ttl)

        assert count1 == 1
        assert count2 == 2
        assert count3 == 3

    def test_counter_is_thread_safe(self):
        """Test that the counter handles concurrent increments safely."""
        from app.dependencies.platform_rate_limit import InMemoryRateLimitCounter

        counter = InMemoryRateLimitCounter()
        key = "concurrent_key"
        ttl = 60
        results = []
        num_threads = 10
        increments_per_thread = 100

        def increment_counter():
            for _ in range(increments_per_thread):
                count = counter.increment(key, ttl)
                results.append(count)

        threads = [threading.Thread(target=increment_counter) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Total should equal num_threads * increments_per_thread
        expected_total = num_threads * increments_per_thread
        assert len(results) == expected_total
        # The final count should match total increments
        assert counter.get(key) == expected_total

    def test_counter_expires_entries(self):
        """Test that entries expire after TTL."""
        from app.dependencies.platform_rate_limit import InMemoryRateLimitCounter

        counter = InMemoryRateLimitCounter()
        key = "expiring_key"
        ttl = 1  # 1 second TTL

        counter.increment(key, ttl)
        assert counter.get(key) == 1

        # Wait for expiration
        time.sleep(1.1)

        # After expiration, count should reset
        new_count = counter.increment(key, ttl)
        assert new_count == 1  # Should start fresh

    def test_cleanup_removes_stale_entries(self):
        """Test that cleanup removes expired entries."""
        from app.dependencies.platform_rate_limit import InMemoryRateLimitCounter

        counter = InMemoryRateLimitCounter()

        # Add entries with very short TTL
        counter.increment("stale_1", 1)
        counter.increment("stale_2", 1)
        counter.increment("fresh", 3600)  # 1 hour TTL

        # Wait for short TTL entries to expire
        time.sleep(1.1)

        # Run cleanup
        removed = counter.cleanup()

        assert removed == 2  # Two stale entries removed
        assert counter.get("fresh") == 1  # Fresh entry still exists


class TestCircuitBreaker:
    """Test the circuit breaker pattern for Redis failures."""

    def test_circuit_starts_closed(self):
        """Test that circuit breaker starts in closed state."""
        from app.dependencies.platform_rate_limit import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        assert breaker.is_closed()
        assert not breaker.is_open()

    def test_circuit_opens_after_threshold_failures(self):
        """Test that circuit opens after reaching failure threshold."""
        from app.dependencies.platform_rate_limit import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        breaker.record_failure()
        assert breaker.is_closed()

        breaker.record_failure()
        assert breaker.is_closed()

        breaker.record_failure()
        assert breaker.is_open()

    def test_circuit_resets_on_success(self):
        """Test that circuit resets failure count on success."""
        from app.dependencies.platform_rate_limit import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        breaker.record_failure()
        breaker.record_failure()
        assert breaker.failure_count == 2

        breaker.record_success()
        assert breaker.failure_count == 0
        assert breaker.is_closed()

    def test_circuit_allows_test_after_recovery_timeout(self):
        """Test that circuit allows a test request after recovery timeout."""
        from app.dependencies.platform_rate_limit import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=1)  # 1 second timeout

        breaker.record_failure()
        assert breaker.is_open()

        # Wait for recovery timeout
        time.sleep(1.1)

        # Should now be in half-open state (allow test)
        assert breaker.should_allow_test()

    def test_circuit_closes_after_successful_test(self):
        """Test that circuit closes after successful test in half-open state."""
        from app.dependencies.platform_rate_limit import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=1)

        breaker.record_failure()
        assert breaker.is_open()

        time.sleep(1.1)
        assert breaker.should_allow_test()

        breaker.record_success()
        assert breaker.is_closed()


class TestFallbackRateLimiting:
    """Test the fallback rate limiting behavior when Redis is unavailable."""

    def test_fallback_enforces_rate_limit(self):
        """Test that fallback mode still enforces rate limits."""
        from app.dependencies.platform_rate_limit import (
            InMemoryRateLimitCounter,
            _check_rate_limit_fallback,
        )
        from app.models.platform_application import PlatformApplication

        counter = InMemoryRateLimitCounter()

        # Create mock application
        app = MagicMock(spec=PlatformApplication)
        app.id = uuid4()
        app.slug = "test-app"
        app.rate_limit_per_minute = 3
        app.rate_limit_per_hour = 100

        now = datetime.utcnow()

        # First 3 requests should succeed
        for _ in range(3):
            _check_rate_limit_fallback(counter, app, now)  # Should not raise

        # 4th request should raise
        with pytest.raises(HTTPException) as exc_info:
            _check_rate_limit_fallback(counter, app, now)

        assert exc_info.value.status_code == 429
        assert "rate limit" in exc_info.value.detail.lower()

    def test_fallback_enforces_hourly_limit(self):
        """Test that fallback mode enforces hourly rate limits."""
        from app.dependencies.platform_rate_limit import (
            InMemoryRateLimitCounter,
            _check_rate_limit_fallback,
        )
        from app.models.platform_application import PlatformApplication

        counter = InMemoryRateLimitCounter()

        # Create mock application with high minute limit but low hour limit
        app = MagicMock(spec=PlatformApplication)
        app.id = uuid4()
        app.slug = "test-app"
        app.rate_limit_per_minute = 1000  # High minute limit
        app.rate_limit_per_hour = 2  # Low hour limit

        now = datetime.utcnow()

        # First 2 requests should succeed
        for _ in range(2):
            _check_rate_limit_fallback(counter, app, now)

        # 3rd request should raise due to hourly limit
        with pytest.raises(HTTPException) as exc_info:
            _check_rate_limit_fallback(counter, app, now)

        assert exc_info.value.status_code == 429
        assert "per hour" in exc_info.value.detail.lower()


class TestRateLimitWithCircuitBreaker:
    """Test the complete rate limiting with circuit breaker integration."""

    @pytest.mark.asyncio
    async def test_switches_to_fallback_on_redis_failure(self):
        """Test that system switches to fallback when Redis fails."""
        from app.dependencies.platform_rate_limit import (
            check_platform_rate_limit,
            _circuit_breaker,
            _fallback_counter,
        )
        from app.models.platform_application import PlatformApplication
        from app.models.platform_api_key import PlatformApiKey

        # Reset circuit breaker state
        _circuit_breaker.reset()
        _fallback_counter.clear()

        # Create mock objects
        app = MagicMock(spec=PlatformApplication)
        app.id = uuid4()
        app.slug = "test-app"
        app.rate_limit_per_minute = 10
        app.rate_limit_per_hour = 100

        api_key = MagicMock(spec=PlatformApiKey)
        request = MagicMock()

        # Mock get_redis_client to return a failing Redis client
        mock_redis = MagicMock()
        mock_redis.incr.side_effect = Exception("Redis connection failed")

        with patch("app.dependencies.platform_rate_limit.get_redis_client", return_value=mock_redis):
            with patch("app.config.settings.rate_limit_enabled", True):
                with patch("app.config.settings.rate_limit_fail_open", True):
                    # Multiple failures should trigger circuit breaker
                    for _ in range(5):
                        await check_platform_rate_limit(app, api_key, request)

                    # Circuit should be open now
                    assert _circuit_breaker.is_open()

    @pytest.mark.asyncio
    async def test_fallback_still_enforces_limits(self):
        """Test that fallback mode enforces rate limits when Redis is down."""
        from app.dependencies.platform_rate_limit import (
            check_platform_rate_limit,
            _circuit_breaker,
            _fallback_counter,
        )
        from app.models.platform_application import PlatformApplication
        from app.models.platform_api_key import PlatformApiKey

        # Reset and open circuit breaker
        _circuit_breaker.reset()
        _fallback_counter.clear()

        # Open the circuit breaker to force fallback
        for _ in range(3):
            _circuit_breaker.record_failure()

        assert _circuit_breaker.is_open()

        # Create mock objects with low rate limit
        app = MagicMock(spec=PlatformApplication)
        app.id = uuid4()
        app.slug = "test-app"
        app.rate_limit_per_minute = 2
        app.rate_limit_per_hour = 100

        api_key = MagicMock(spec=PlatformApiKey)
        request = MagicMock()

        with patch("app.config.settings.rate_limit_enabled", True):
            with patch("app.config.settings.rate_limit_fail_open", True):
                # First 2 requests should succeed (fallback mode)
                for _ in range(2):
                    await check_platform_rate_limit(app, api_key, request)

                # 3rd request should be rate limited
                with pytest.raises(HTTPException) as exc_info:
                    await check_platform_rate_limit(app, api_key, request)

                assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_auto_recovery_when_redis_available(self):
        """Test that system recovers to Redis when it becomes available."""
        from app.dependencies.platform_rate_limit import (
            check_platform_rate_limit,
            _circuit_breaker,
            _fallback_counter,
        )
        from app.models.platform_application import PlatformApplication
        from app.models.platform_api_key import PlatformApiKey

        # Reset state
        _circuit_breaker.reset()
        _fallback_counter.clear()

        # Open circuit breaker and set short recovery timeout
        _circuit_breaker._recovery_timeout = 0.1  # 100ms for test
        for _ in range(3):
            _circuit_breaker.record_failure()

        assert _circuit_breaker.is_open()

        # Wait for recovery timeout
        time.sleep(0.2)

        # Create mock objects
        app = MagicMock(spec=PlatformApplication)
        app.id = uuid4()
        app.slug = "test-app"
        app.rate_limit_per_minute = 100
        app.rate_limit_per_hour = 1000

        api_key = MagicMock(spec=PlatformApiKey)
        request = MagicMock()

        # Mock get_redis_client to return a working Redis client
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True

        with patch("app.dependencies.platform_rate_limit.get_redis_client", return_value=mock_redis):
            with patch("app.config.settings.rate_limit_enabled", True):
                await check_platform_rate_limit(app, api_key, request)

                # Circuit should be closed again
                assert _circuit_breaker.is_closed()


class TestLoggingAndMetrics:
    """Test logging when fallback mode is active."""

    @pytest.mark.asyncio
    async def test_logs_warning_on_fallback_activation(self, caplog):
        """Test that WARNING is logged when switching to fallback mode."""
        import logging
        from app.dependencies.platform_rate_limit import (
            check_platform_rate_limit,
            _circuit_breaker,
            _fallback_counter,
        )
        from app.models.platform_application import PlatformApplication
        from app.models.platform_api_key import PlatformApiKey

        # Reset state
        _circuit_breaker.reset()
        _fallback_counter.clear()

        # Create mock objects
        app = MagicMock(spec=PlatformApplication)
        app.id = uuid4()
        app.slug = "test-app"
        app.rate_limit_per_minute = 100
        app.rate_limit_per_hour = 1000

        api_key = MagicMock(spec=PlatformApiKey)
        request = MagicMock()

        # Mock get_redis_client to return a failing Redis client
        mock_redis = MagicMock()
        mock_redis.incr.side_effect = Exception("Redis connection failed")

        with caplog.at_level(logging.WARNING):
            with patch("app.dependencies.platform_rate_limit.get_redis_client", return_value=mock_redis):
                with patch("app.config.settings.rate_limit_enabled", True):
                    with patch("app.config.settings.rate_limit_fail_open", True):
                        # Trigger failures to open circuit
                        for _ in range(3):
                            await check_platform_rate_limit(app, api_key, request)

        # Check that warning was logged about circuit breaker opening
        assert any(
            "circuit breaker" in record.message.lower() or "fallback" in record.message.lower()
            for record in caplog.records
        )
