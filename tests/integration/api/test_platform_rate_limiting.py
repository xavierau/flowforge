"""Integration tests for Platform API rate limiting.

Test Coverage:
- Per-minute rate limiting enforcement
- Per-hour rate limiting enforcement
- Rate limit headers in responses
- Rate limit bypass when disabled
"""

import os
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models.platform_application import PlatformApplication
from app.models.platform_api_key import PlatformApiKey


class TestPlatformRateLimiting:
    """Test Platform API rate limiting."""

    def test_rate_limit_per_minute_enforced(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
        platform_api_key: tuple,
    ):
        """Test that per-minute rate limit is enforced."""
        from app.dependencies.platform_rate_limit import _circuit_breaker, _fallback_counter

        # Reset circuit breaker state
        _circuit_breaker.reset()
        _fallback_counter.clear()

        api_key, full_key = platform_api_key
        headers = {"Authorization": f"Bearer {full_key}"}

        # Set low rate limit for testing
        platform_application.rate_limit_per_minute = 3
        platform_application.rate_limit_per_hour = 1000
        db_session.commit()

        # Mock _get_redis_client to return a mock Redis client
        mock_redis = MagicMock()
        minute_counter = [0]

        def mock_incr(key):
            if "minute" in key:
                minute_counter[0] += 1
                return minute_counter[0]
            return 1

        mock_redis.incr.side_effect = mock_incr
        mock_redis.expire.return_value = True

        with patch("app.dependencies.platform_rate_limit.get_redis_client", return_value=mock_redis):
            with patch.object(settings, "rate_limit_enabled", True):
                # First 3 requests should succeed
                for i in range(3):
                    response = client.get(
                        f"/platform/v1/tenants/{platform_application.id}",
                        headers=headers,
                    )
                    # May get 404 (tenant not found) but not 429
                    assert response.status_code != 429, f"Request {i+1} should not be rate limited"

                # 4th request should be rate limited
                response = client.get(
                    f"/platform/v1/tenants/{platform_application.id}",
                    headers=headers,
                )
                assert response.status_code == 429
                assert "rate limit" in response.json()["detail"].lower()

    def test_rate_limit_per_hour_enforced(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
        platform_api_key: tuple,
    ):
        """Test that per-hour rate limit is enforced."""
        from app.dependencies.platform_rate_limit import _circuit_breaker, _fallback_counter

        # Reset circuit breaker state
        _circuit_breaker.reset()
        _fallback_counter.clear()

        api_key, full_key = platform_api_key
        headers = {"Authorization": f"Bearer {full_key}"}

        # Set minute limit high but hour limit low
        platform_application.rate_limit_per_minute = 1000
        platform_application.rate_limit_per_hour = 2
        db_session.commit()

        # Mock _get_redis_client to return a mock Redis client
        mock_redis = MagicMock()
        hour_counter = [0]

        def mock_incr(key):
            if "hour" in key:
                hour_counter[0] += 1
                return hour_counter[0]
            return 1  # Minute counter always returns 1 (within limit)

        mock_redis.incr.side_effect = mock_incr
        mock_redis.expire.return_value = True

        with patch("app.dependencies.platform_rate_limit.get_redis_client", return_value=mock_redis):
            with patch.object(settings, "rate_limit_enabled", True):
                # First 2 requests should succeed
                for i in range(2):
                    response = client.get(
                        f"/platform/v1/tenants/{platform_application.id}",
                        headers=headers,
                    )
                    # May get 404 (tenant not found) but not 429
                    assert response.status_code != 429, f"Request {i+1} should not be rate limited"

                # 3rd request should be rate limited
                response = client.get(
                    f"/platform/v1/tenants/{platform_application.id}",
                    headers=headers,
                )
                assert response.status_code == 429
                assert "rate limit" in response.json()["detail"].lower()

    def test_rate_limit_not_enforced_when_disabled(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
        platform_api_key: tuple,
    ):
        """Test that rate limiting is bypassed when disabled."""
        api_key, full_key = platform_api_key
        headers = {"Authorization": f"Bearer {full_key}"}

        # Set very low rate limits
        platform_application.rate_limit_per_minute = 1
        platform_application.rate_limit_per_hour = 1
        db_session.commit()

        # Explicitly disable rate limiting for this test
        with patch.object(settings, "rate_limit_enabled", False):
            # Make multiple requests - none should get 429
            for i in range(5):
                response = client.get(
                    f"/platform/v1/tenants/{platform_application.id}",
                    headers=headers,
                )
                # Should not get 429 even with low limits because rate limiting is disabled
                assert response.status_code != 429, f"Request {i+1} should not be rate limited when disabled"


class TestRateLimitKeyGeneration:
    """Test rate limit key generation logic."""

    def test_rate_limit_key_uses_application_id(
        self,
        platform_application: PlatformApplication,
    ):
        """Test that rate limit keys are scoped by application ID."""
        from app.dependencies.platform_rate_limit import _generate_rate_limit_key

        now = datetime(2024, 1, 15, 10, 30, 45)

        minute_key = _generate_rate_limit_key(platform_application.id, "minute", now)
        hour_key = _generate_rate_limit_key(platform_application.id, "hour", now)

        assert str(platform_application.id) in minute_key
        assert str(platform_application.id) in hour_key
        assert "minute" in minute_key
        assert "hour" in hour_key

    def test_rate_limit_keys_are_time_scoped(
        self,
        platform_application: PlatformApplication,
    ):
        """Test that rate limit keys change with time."""
        from app.dependencies.platform_rate_limit import _generate_rate_limit_key

        time1 = datetime(2024, 1, 15, 10, 30, 0)
        time2 = datetime(2024, 1, 15, 10, 31, 0)  # Different minute
        time3 = datetime(2024, 1, 15, 11, 30, 0)  # Different hour

        minute_key1 = _generate_rate_limit_key(platform_application.id, "minute", time1)
        minute_key2 = _generate_rate_limit_key(platform_application.id, "minute", time2)

        hour_key1 = _generate_rate_limit_key(platform_application.id, "hour", time1)
        hour_key3 = _generate_rate_limit_key(platform_application.id, "hour", time3)

        # Minute keys should be different for different minutes
        assert minute_key1 != minute_key2

        # Hour keys should be different for different hours
        assert hour_key1 != hour_key3


class TestRateLimitExceptionHandling:
    """Test rate limit error handling."""

    def test_rate_limit_redis_unavailable_fails_closed_by_default(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
        platform_api_key: tuple,
    ):
        """Test that Redis unavailability returns 503 Service Unavailable by default.

        This test verifies that when Redis is unavailable and fail_open=False (default),
        requests are denied with a 503 error to prevent rate limit bypass.
        """
        from app.dependencies.platform_rate_limit import _circuit_breaker, _fallback_counter

        # Reset circuit breaker state
        _circuit_breaker.reset()
        _fallback_counter.clear()

        api_key, full_key = platform_api_key
        headers = {"Authorization": f"Bearer {full_key}"}

        # Mock _get_redis_client to return None (Redis unavailable)
        with patch("app.dependencies.platform_rate_limit.get_redis_client", return_value=None):
            with patch.object(settings, "rate_limit_enabled", True):
                with patch.object(settings, "rate_limit_fail_open", False):
                    response = client.get(
                        f"/platform/v1/tenants/{platform_application.id}",
                        headers=headers,
                    )
                    # Should return 503 Service Unavailable when fail_open=False
                    assert response.status_code == 503
                    assert "service unavailable" in response.json()["detail"].lower()

    def test_rate_limit_redis_exception_fails_closed_by_default(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
        platform_api_key: tuple,
    ):
        """Test that Redis exceptions return 503 Service Unavailable by default.

        This test verifies that when Redis throws an exception and fail_open=False (default),
        requests are denied with a 503 error.
        """
        from app.dependencies.platform_rate_limit import _circuit_breaker, _fallback_counter

        # Reset circuit breaker state
        _circuit_breaker.reset()
        _fallback_counter.clear()

        api_key, full_key = platform_api_key
        headers = {"Authorization": f"Bearer {full_key}"}

        # Mock _get_redis_client to return a failing Redis client
        mock_redis = MagicMock()
        mock_redis.incr.side_effect = Exception("Redis connection failed")

        with patch("app.dependencies.platform_rate_limit.get_redis_client", return_value=mock_redis):
            with patch.object(settings, "rate_limit_enabled", True):
                with patch.object(settings, "rate_limit_fail_open", False):
                    response = client.get(
                        f"/platform/v1/tenants/{platform_application.id}",
                        headers=headers,
                    )
                    # Should return 503 Service Unavailable when fail_open=False
                    assert response.status_code == 503
                    assert "service unavailable" in response.json()["detail"].lower()

    def test_rate_limit_redis_unavailable_uses_fallback_when_fail_open(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
        platform_api_key: tuple,
    ):
        """Test that Redis unavailability uses fallback counter when fail_open=True.

        This test verifies that when Redis is unavailable and fail_open=True,
        the in-memory fallback counter is used (for development environments).
        """
        from app.dependencies.platform_rate_limit import _circuit_breaker, _fallback_counter

        # Reset circuit breaker state and open it to ensure fallback is used
        _circuit_breaker.reset()
        _fallback_counter.clear()

        # Force circuit breaker to be open (simulate previous Redis failures)
        for _ in range(3):
            _circuit_breaker.record_failure()
        assert _circuit_breaker.is_open()

        api_key, full_key = platform_api_key
        headers = {"Authorization": f"Bearer {full_key}"}

        # Set low rate limit to test fallback enforcement
        platform_application.rate_limit_per_minute = 2
        platform_application.rate_limit_per_hour = 1000
        db_session.commit()

        with patch.object(settings, "rate_limit_enabled", True):
            with patch.object(settings, "rate_limit_fail_open", True):
                # First 2 requests should succeed (using fallback counter)
                for i in range(2):
                    response = client.get(
                        f"/platform/v1/tenants/{platform_application.id}",
                        headers=headers,
                    )
                    # Should not get 429 or 503 - fallback counter allows first 2 requests
                    assert response.status_code != 429, f"Request {i+1} should not be rate limited"
                    assert response.status_code != 503, f"Request {i+1} should not cause service unavailable"

                # 3rd request should be rate limited by fallback counter
                response = client.get(
                    f"/platform/v1/tenants/{platform_application.id}",
                    headers=headers,
                )
                assert response.status_code == 429
                assert "rate limit" in response.json()["detail"].lower()

    def test_rate_limit_redis_exception_uses_fallback_when_fail_open(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
        platform_api_key: tuple,
    ):
        """Test that Redis exceptions use fallback counter when fail_open=True.

        This test verifies that when Redis throws an exception and fail_open=True,
        the in-memory fallback counter is used instead of returning 503.
        """
        from app.dependencies.platform_rate_limit import _circuit_breaker, _fallback_counter

        # Reset circuit breaker state
        _circuit_breaker.reset()
        _fallback_counter.clear()

        api_key, full_key = platform_api_key
        headers = {"Authorization": f"Bearer {full_key}"}

        # Set low rate limit
        platform_application.rate_limit_per_minute = 2
        platform_application.rate_limit_per_hour = 1000
        db_session.commit()

        # Mock get_redis_client to return a failing Redis client
        mock_redis = MagicMock()
        mock_redis.incr.side_effect = Exception("Redis connection failed")

        with patch("app.dependencies.platform_rate_limit.get_redis_client", return_value=mock_redis):
            with patch.object(settings, "rate_limit_enabled", True):
                with patch.object(settings, "rate_limit_fail_open", True):
                    # First 2 requests should succeed (using fallback counter)
                    for i in range(2):
                        response = client.get(
                            f"/platform/v1/tenants/{platform_application.id}",
                            headers=headers,
                        )
                        # Should not get 429 or 503 - fallback handles it
                        assert response.status_code != 429, f"Request {i+1} should not be rate limited"
                        assert response.status_code != 503, f"Request {i+1} should not cause service unavailable"

                    # 3rd request should be rate limited by fallback counter
                    response = client.get(
                        f"/platform/v1/tenants/{platform_application.id}",
                        headers=headers,
                    )
                    assert response.status_code == 429

    def test_rate_limit_circuit_breaker_open_fails_closed_by_default(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
        platform_api_key: tuple,
    ):
        """Test that when circuit breaker is open, fail_closed behavior applies.

        When Redis has failed repeatedly (circuit breaker open) and fail_open=False,
        requests should be denied with 503.
        """
        from app.dependencies.platform_rate_limit import _circuit_breaker, _fallback_counter

        # Reset circuit breaker state and open it
        _circuit_breaker.reset()
        _fallback_counter.clear()

        # Force circuit breaker to be open
        for _ in range(3):
            _circuit_breaker.record_failure()
        assert _circuit_breaker.is_open()

        api_key, full_key = platform_api_key
        headers = {"Authorization": f"Bearer {full_key}"}

        with patch.object(settings, "rate_limit_enabled", True):
            with patch.object(settings, "rate_limit_fail_open", False):
                response = client.get(
                    f"/platform/v1/tenants/{platform_application.id}",
                    headers=headers,
                )
                # Should return 503 when circuit breaker is open and fail_open=False
                assert response.status_code == 503
                assert "service unavailable" in response.json()["detail"].lower()

    def test_circuit_breaker_opens_after_repeated_failures(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
        platform_api_key: tuple,
    ):
        """Test that circuit breaker opens after repeated Redis failures.

        Note: This test uses fail_open=True to allow requests to proceed with fallback.
        The circuit breaker still opens to track Redis unavailability.
        """
        from app.dependencies.platform_rate_limit import _circuit_breaker, _fallback_counter

        # Reset circuit breaker state
        _circuit_breaker.reset()
        _fallback_counter.clear()

        api_key, full_key = platform_api_key
        headers = {"Authorization": f"Bearer {full_key}"}

        # Set high rate limit so we don't hit limits
        platform_application.rate_limit_per_minute = 1000
        platform_application.rate_limit_per_hour = 10000
        db_session.commit()

        # Mock _get_redis_client to return a failing Redis client
        mock_redis = MagicMock()
        mock_redis.incr.side_effect = Exception("Redis connection failed")

        with patch("app.dependencies.platform_rate_limit.get_redis_client", return_value=mock_redis):
            with patch.object(settings, "rate_limit_enabled", True):
                with patch.object(settings, "rate_limit_fail_open", True):
                    # Make 5 requests - should trigger circuit breaker to open
                    for _ in range(5):
                        response = client.get(
                            f"/platform/v1/tenants/{platform_application.id}",
                            headers=headers,
                        )
                        # Should not get 500 - fallback should handle it
                        assert response.status_code != 500

                    # Circuit breaker should be open now
                    assert _circuit_breaker.is_open()


class TestRateLimitHeaders:
    """Test rate limit response headers."""

    def test_rate_limit_headers_present_in_response(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
        platform_api_key: tuple,
    ):
        """Test that rate limit headers are included in successful responses."""
        from app.dependencies.platform_rate_limit import _circuit_breaker, _fallback_counter

        # Reset circuit breaker state
        _circuit_breaker.reset()
        _fallback_counter.clear()

        api_key, full_key = platform_api_key
        headers = {"Authorization": f"Bearer {full_key}"}

        # Set rate limits
        platform_application.rate_limit_per_minute = 100
        platform_application.rate_limit_per_hour = 1000
        db_session.commit()

        # Mock _get_redis_client to return a working Redis client
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 5  # Simulate 5th request
        mock_redis.expire.return_value = True

        with patch("app.dependencies.platform_rate_limit.get_redis_client", return_value=mock_redis):
            with patch.object(settings, "rate_limit_enabled", True):
                response = client.get(
                    f"/platform/v1/tenants/{platform_application.id}",
                    headers=headers,
                )

                # Check rate limit headers are present
                assert "X-RateLimit-Limit" in response.headers
                assert "X-RateLimit-Remaining" in response.headers
                assert "X-RateLimit-Reset" in response.headers

                # Verify header values
                assert response.headers["X-RateLimit-Limit"] == "100"
                assert int(response.headers["X-RateLimit-Remaining"]) >= 0
                # Reset should be a Unix timestamp (integer)
                reset_timestamp = int(response.headers["X-RateLimit-Reset"])
                assert reset_timestamp > 0

    def test_rate_limit_headers_show_correct_remaining_count(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
        platform_api_key: tuple,
    ):
        """Test that X-RateLimit-Remaining decreases with each request."""
        from app.dependencies.platform_rate_limit import _circuit_breaker, _fallback_counter

        # Reset circuit breaker state
        _circuit_breaker.reset()
        _fallback_counter.clear()

        api_key, full_key = platform_api_key
        headers = {"Authorization": f"Bearer {full_key}"}

        platform_application.rate_limit_per_minute = 10
        platform_application.rate_limit_per_hour = 1000
        db_session.commit()

        # Mock _get_redis_client with incrementing counter
        mock_redis = MagicMock()
        request_counter = [0]

        def mock_incr(key):
            if "minute" in key:
                request_counter[0] += 1
                return request_counter[0]
            return 1

        mock_redis.incr.side_effect = mock_incr
        mock_redis.expire.return_value = True

        with patch("app.dependencies.platform_rate_limit.get_redis_client", return_value=mock_redis):
            with patch.object(settings, "rate_limit_enabled", True):
                # First request
                response1 = client.get(
                    f"/platform/v1/tenants/{platform_application.id}",
                    headers=headers,
                )
                remaining1 = int(response1.headers.get("X-RateLimit-Remaining", -1))

                # Second request
                response2 = client.get(
                    f"/platform/v1/tenants/{platform_application.id}",
                    headers=headers,
                )
                remaining2 = int(response2.headers.get("X-RateLimit-Remaining", -1))

                # Remaining should decrease
                assert remaining2 < remaining1
                assert remaining1 == 9  # 10 - 1
                assert remaining2 == 8  # 10 - 2

    def test_retry_after_header_on_429_response(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
        platform_api_key: tuple,
    ):
        """Test that Retry-After header is present when rate limited."""
        from app.dependencies.platform_rate_limit import _circuit_breaker, _fallback_counter

        # Reset circuit breaker state
        _circuit_breaker.reset()
        _fallback_counter.clear()

        api_key, full_key = platform_api_key
        headers = {"Authorization": f"Bearer {full_key}"}

        # Set very low rate limit
        platform_application.rate_limit_per_minute = 1
        platform_application.rate_limit_per_hour = 1000
        db_session.commit()

        # Mock _get_redis_client to return over-limit count
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 2  # Over the limit of 1
        mock_redis.expire.return_value = True

        with patch("app.dependencies.platform_rate_limit.get_redis_client", return_value=mock_redis):
            with patch.object(settings, "rate_limit_enabled", True):
                response = client.get(
                    f"/platform/v1/tenants/{platform_application.id}",
                    headers=headers,
                )

                assert response.status_code == 429
                assert "Retry-After" in response.headers
                # Retry-After should be a positive integer (seconds to wait)
                retry_after = int(response.headers["Retry-After"])
                assert retry_after > 0
                assert retry_after <= 60  # Should be within the minute window

    def test_rate_limit_headers_not_present_when_disabled(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
        platform_api_key: tuple,
    ):
        """Test that rate limit headers are not present when rate limiting is disabled."""
        api_key, full_key = platform_api_key
        headers = {"Authorization": f"Bearer {full_key}"}

        # Explicitly disable rate limiting for this test
        with patch.object(settings, "rate_limit_enabled", False):
            response = client.get(
                f"/platform/v1/tenants/{platform_application.id}",
                headers=headers,
            )

            # Headers should not be present when rate limiting is disabled
            assert "X-RateLimit-Limit" not in response.headers
            assert "X-RateLimit-Remaining" not in response.headers
            assert "X-RateLimit-Reset" not in response.headers

    def test_rate_limit_uses_most_restrictive_window(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
        platform_api_key: tuple,
    ):
        """Test that headers reflect the most restrictive rate limit window."""
        api_key, full_key = platform_api_key
        headers = {"Authorization": f"Bearer {full_key}"}

        # Set minute limit low (more restrictive) and hour limit high
        platform_application.rate_limit_per_minute = 10
        platform_application.rate_limit_per_hour = 1000
        db_session.commit()

        mock_redis = MagicMock()

        def mock_incr(key):
            if "minute" in key:
                return 5  # 5 of 10 minute limit used
            return 50  # 50 of 1000 hour limit used

        mock_redis.incr.side_effect = mock_incr
        mock_redis.expire.return_value = True

        with patch("app.dependencies.platform_rate_limit.get_redis_client", return_value=mock_redis):
            with patch.object(settings, "rate_limit_enabled", True):
                response = client.get(
                    f"/platform/v1/tenants/{platform_application.id}",
                    headers=headers,
                )

                # Should show minute limit (more restrictive: 5/10 = 50% vs 50/1000 = 5%)
                assert response.headers["X-RateLimit-Limit"] == "10"
                assert response.headers["X-RateLimit-Remaining"] == "5"
