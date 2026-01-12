"""Rate limiting for Platform API.

This module provides distributed rate limiting for Platform API endpoints
using Redis with sliding window counters. Includes configurable fail-closed
or fail-open behavior when Redis is unavailable.

Rate limiting can be disabled via RATE_LIMIT_ENABLED=false environment variable
for testing purposes.

Security Note:
- By default (RATE_LIMIT_FAIL_OPEN=false), the system fails CLOSED when Redis
  is unavailable, returning 503 Service Unavailable. This prevents rate limit
  bypass attacks.
- For development environments, set RATE_LIMIT_FAIL_OPEN=true to use an
  in-memory fallback counter instead of denying requests.
- The circuit breaker pattern minimizes Redis connection attempts when
  Redis is known to be down, reducing latency impact.

Response headers:
- X-RateLimit-Limit: Maximum requests allowed in the current window
- X-RateLimit-Remaining: Requests remaining in current window
- X-RateLimit-Reset: Unix timestamp when the rate limit resets
- Retry-After: Seconds until rate limit resets (only on 429 responses)
"""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import Request, HTTPException, status

from app.config import settings
from app.core.redis import get_redis_client
from app.models.platform_application import PlatformApplication
from app.models.platform_api_key import PlatformApiKey


logger = logging.getLogger(__name__)


@dataclass
class RateLimitInfo:
    """Rate limit information for response headers."""

    limit: int
    remaining: int
    reset: int  # Unix timestamp
    window_type: str  # "minute" or "hour"


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        detail: str,
        retry_after: int,
        rate_limit_info: RateLimitInfo,
    ):
        headers = {
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(rate_limit_info.limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(rate_limit_info.reset),
        }
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers=headers,
        )
        self.retry_after = retry_after
        self.rate_limit_info = rate_limit_info


class InMemoryRateLimitCounter:
    """Thread-safe in-memory rate limit counter.

    Used as fallback when Redis is unavailable. Stores counters with
    expiration timestamps for automatic cleanup.
    """

    def __init__(self):
        """Initialize the counter with thread lock."""
        self._lock = threading.Lock()
        self._counters: dict[str, tuple[int, float]] = {}  # key -> (count, expires_at)

    def increment(self, key: str, ttl_seconds: int) -> int:
        """Increment counter for key, creating if needed.

        Args:
            key: The rate limit key
            ttl_seconds: Time-to-live in seconds

        Returns:
            The new count value
        """
        with self._lock:
            now = time.time()
            expires_at = now + ttl_seconds

            if key in self._counters:
                count, existing_expires = self._counters[key]
                if existing_expires > now:
                    # Entry still valid, increment
                    new_count = count + 1
                    self._counters[key] = (new_count, existing_expires)
                    return new_count

            # Entry expired or doesn't exist, start fresh
            self._counters[key] = (1, expires_at)
            return 1

    def get(self, key: str) -> int:
        """Get current count for key.

        Args:
            key: The rate limit key

        Returns:
            Current count, or 0 if expired/not found
        """
        with self._lock:
            if key not in self._counters:
                return 0
            count, expires_at = self._counters[key]
            if expires_at <= time.time():
                return 0
            return count

    def cleanup(self) -> int:
        """Remove expired entries to prevent memory growth.

        Returns:
            Number of entries removed
        """
        with self._lock:
            now = time.time()
            expired_keys = [
                key for key, (_, expires_at) in self._counters.items()
                if expires_at <= now
            ]
            for key in expired_keys:
                del self._counters[key]
            return len(expired_keys)

    def clear(self):
        """Clear all entries. Useful for testing."""
        with self._lock:
            self._counters.clear()


class CircuitBreaker:
    """Circuit breaker pattern for Redis connection resilience.

    States:
    - CLOSED: Normal operation, requests go to Redis
    - OPEN: Redis is down, use fallback directly
    - HALF_OPEN: Testing if Redis is back (after recovery timeout)
    """

    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 60.0):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
        """
        self._lock = threading.Lock()
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "CLOSED"

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        with self._lock:
            return self._failure_count

    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        with self._lock:
            return self._state == "CLOSED"

    def is_open(self) -> bool:
        """Check if circuit is open (Redis unavailable)."""
        with self._lock:
            return self._state == "OPEN"

    def should_allow_test(self) -> bool:
        """Check if we should test Redis (half-open state).

        Returns:
            True if recovery timeout has passed and we should try Redis
        """
        with self._lock:
            if self._state != "OPEN":
                return self._state == "CLOSED"

            # Check if recovery timeout has passed
            if self._last_failure_time is None:
                return True

            elapsed = time.time() - self._last_failure_time
            if elapsed >= self._recovery_timeout:
                self._state = "HALF_OPEN"
                return True

            return False

    def record_failure(self):
        """Record a Redis failure."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._failure_count >= self._failure_threshold:
                if self._state != "OPEN":
                    logger.warning(
                        "Circuit breaker opened: Redis unavailable after %d failures. "
                        "Switching to in-memory fallback rate limiting.",
                        self._failure_count
                    )
                self._state = "OPEN"

    def record_success(self):
        """Record a successful Redis operation."""
        with self._lock:
            if self._state == "HALF_OPEN":
                logger.info(
                    "Circuit breaker closed: Redis recovered. "
                    "Resuming normal rate limiting."
                )
            self._failure_count = 0
            self._state = "CLOSED"

    def reset(self):
        """Reset circuit breaker to initial state. Useful for testing."""
        with self._lock:
            self._failure_count = 0
            self._last_failure_time = None
            self._state = "CLOSED"


# Global instances for fallback and circuit breaker
_fallback_counter = InMemoryRateLimitCounter()
_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
_last_cleanup_time = time.time()
_CLEANUP_INTERVAL = 300  # 5 minutes


def _generate_rate_limit_key(
    application_id: UUID,
    window_type: str,
    now: datetime,
) -> str:
    """Generate a Redis key for rate limiting.

    Args:
        application_id: Platform application ID
        window_type: "minute" or "hour"
        now: Current timestamp

    Returns:
        Redis key string
    """
    if window_type == "minute":
        time_bucket = now.strftime("%Y%m%d%H%M")
    else:  # hour
        time_bucket = now.strftime("%Y%m%d%H")

    return f"platform_rate:{application_id}:{window_type}:{time_bucket}"


def _get_ttl_for_window(window_type: str) -> int:
    """Get TTL in seconds for a rate limit window.

    Args:
        window_type: "minute" or "hour"

    Returns:
        TTL in seconds (with safety margin)
    """
    if window_type == "minute":
        return 120  # 2 minutes TTL for minute window
    return 7200  # 2 hours TTL for hour window


def _calculate_reset_timestamp(now: datetime, window_type: str) -> int:
    """Calculate Unix timestamp when the rate limit window resets.

    Args:
        now: Current datetime
        window_type: "minute" or "hour"

    Returns:
        Unix timestamp of window reset
    """
    if window_type == "minute":
        # Reset at the start of next minute
        next_reset = now.replace(second=0, microsecond=0)
        from datetime import timedelta
        next_reset = next_reset + timedelta(minutes=1)
    else:
        # Reset at the start of next hour
        next_reset = now.replace(minute=0, second=0, microsecond=0)
        from datetime import timedelta
        next_reset = next_reset + timedelta(hours=1)

    return int(next_reset.timestamp())


def _calculate_retry_after(now: datetime, window_type: str) -> int:
    """Calculate seconds until the rate limit window resets.

    Args:
        now: Current datetime
        window_type: "minute" or "hour"

    Returns:
        Seconds until reset (minimum 1)
    """
    reset_timestamp = _calculate_reset_timestamp(now, window_type)
    current_timestamp = int(now.timestamp())
    retry_after = reset_timestamp - current_timestamp
    return max(1, retry_after)  # Ensure at least 1 second


def _get_most_restrictive_rate_info(
    minute_count: int,
    minute_limit: int,
    hour_count: int,
    hour_limit: int,
    now: datetime,
) -> RateLimitInfo:
    """Determine which rate limit window is more restrictive.

    Returns the RateLimitInfo for the window that has consumed
    a higher percentage of its limit.

    Args:
        minute_count: Current requests in minute window
        minute_limit: Maximum requests per minute
        hour_count: Current requests in hour window
        hour_limit: Maximum requests per hour
        now: Current datetime

    Returns:
        RateLimitInfo for the most restrictive window
    """
    minute_pct = minute_count / minute_limit if minute_limit > 0 else 0
    hour_pct = hour_count / hour_limit if hour_limit > 0 else 0

    if minute_pct >= hour_pct:
        return RateLimitInfo(
            limit=minute_limit,
            remaining=max(0, minute_limit - minute_count),
            reset=_calculate_reset_timestamp(now, "minute"),
            window_type="minute",
        )
    return RateLimitInfo(
        limit=hour_limit,
        remaining=max(0, hour_limit - hour_count),
        reset=_calculate_reset_timestamp(now, "hour"),
        window_type="hour",
    )


def _maybe_cleanup_fallback():
    """Periodically cleanup expired entries from fallback counter."""
    global _last_cleanup_time
    now = time.time()
    if now - _last_cleanup_time > _CLEANUP_INTERVAL:
        removed = _fallback_counter.cleanup()
        if removed > 0:
            logger.debug(
                "Cleaned up %d expired rate limit entries from fallback counter",
                removed
            )
        _last_cleanup_time = now


def _handle_redis_unavailable(
    application: PlatformApplication,
    now: datetime,
    error_message: str,
) -> None:
    """Handle Redis unavailability based on fail_open configuration.

    Args:
        application: Platform application making the request
        now: Current timestamp
        error_message: Error message describing the Redis failure

    Raises:
        HTTPException: 503 Service Unavailable if fail_open=False
    """
    if settings.rate_limit_fail_open:
        # Use in-memory fallback counter
        logger.warning(
            "Redis unavailable (fail_open=True), using in-memory fallback: %s",
            error_message,
        )
        _check_rate_limit_fallback(_fallback_counter, application, now)
    else:
        # Fail closed - deny the request
        logger.error(
            "Redis unavailable (fail_open=False), denying request: %s",
            error_message,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limiting service unavailable. Please try again later.",
        )


def _check_rate_limit_fallback(
    counter: InMemoryRateLimitCounter,
    application: PlatformApplication,
    now: datetime,
) -> None:
    """Check rate limits using in-memory fallback counter.

    Args:
        counter: The in-memory counter instance
        application: Platform application making the request
        now: Current timestamp

    Raises:
        HTTPException: 429 Too Many Requests if rate limit exceeded
    """
    # Check minute-level rate limit
    minute_key = _generate_rate_limit_key(application.id, "minute", now)
    minute_ttl = _get_ttl_for_window("minute")
    minute_count = counter.increment(minute_key, minute_ttl)

    if minute_count > application.rate_limit_per_minute:
        logger.warning(
            "Platform rate limit exceeded (minute, fallback): app=%s, count=%d, limit=%d",
            application.slug,
            minute_count,
            application.rate_limit_per_minute,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {application.rate_limit_per_minute} requests per minute",
        )

    # Check hour-level rate limit
    hour_key = _generate_rate_limit_key(application.id, "hour", now)
    hour_ttl = _get_ttl_for_window("hour")
    hour_count = counter.increment(hour_key, hour_ttl)

    if hour_count > application.rate_limit_per_hour:
        logger.warning(
            "Platform rate limit exceeded (hour, fallback): app=%s, count=%d, limit=%d",
            application.slug,
            hour_count,
            application.rate_limit_per_hour,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {application.rate_limit_per_hour} requests per hour",
        )


async def check_platform_rate_limit(
    application: PlatformApplication,
    api_key: PlatformApiKey,
    request: Request,
) -> None:
    """Check and enforce rate limits for platform application.

    Uses Redis for distributed rate limiting with sliding window.
    Behavior when Redis is unavailable depends on settings.rate_limit_fail_open:
    - False (default): Returns 503 Service Unavailable (fail-closed, secure)
    - True: Uses in-memory fallback counter (fail-open, for development)

    Stores rate limit info in request.state for response headers.

    Args:
        application: Platform application making the request
        api_key: API key used for authentication
        request: FastAPI request object

    Raises:
        RateLimitExceeded: 429 Too Many Requests if rate limit exceeded
        HTTPException: 503 Service Unavailable if Redis unavailable and fail_open=False
    """
    # Skip rate limiting if disabled (e.g., in tests)
    if not settings.rate_limit_enabled:
        return

    # Periodic cleanup of fallback counter
    _maybe_cleanup_fallback()

    now = datetime.utcnow()

    # Check circuit breaker state
    if not _circuit_breaker.should_allow_test():
        # Circuit is open - handle based on fail_open setting
        _handle_redis_unavailable(
            application, now, "Circuit breaker is open"
        )
        return

    try:
        redis_client = get_redis_client()
        if redis_client is None:
            # Redis unavailable, record failure
            _circuit_breaker.record_failure()
            _handle_redis_unavailable(
                application, now, "Redis client unavailable"
            )
            return

        # Check minute-level rate limit
        minute_key = _generate_rate_limit_key(application.id, "minute", now)
        minute_count = redis_client.incr(minute_key)
        redis_client.expire(minute_key, _get_ttl_for_window("minute"))

        if minute_count > application.rate_limit_per_minute:
            logger.warning(
                "Platform rate limit exceeded (minute): app=%s, count=%d, limit=%d",
                application.slug,
                minute_count,
                application.rate_limit_per_minute,
            )
            # Record success before raising (Redis worked)
            _circuit_breaker.record_success()
            rate_info = RateLimitInfo(
                limit=application.rate_limit_per_minute,
                remaining=0,
                reset=_calculate_reset_timestamp(now, "minute"),
                window_type="minute",
            )
            raise RateLimitExceeded(
                detail=f"Rate limit exceeded: {application.rate_limit_per_minute} requests per minute",
                retry_after=_calculate_retry_after(now, "minute"),
                rate_limit_info=rate_info,
            )

        # Check hour-level rate limit
        hour_key = _generate_rate_limit_key(application.id, "hour", now)
        hour_count = redis_client.incr(hour_key)
        redis_client.expire(hour_key, _get_ttl_for_window("hour"))

        if hour_count > application.rate_limit_per_hour:
            logger.warning(
                "Platform rate limit exceeded (hour): app=%s, count=%d, limit=%d",
                application.slug,
                hour_count,
                application.rate_limit_per_hour,
            )
            # Record success before raising (Redis worked)
            _circuit_breaker.record_success()
            rate_info = RateLimitInfo(
                limit=application.rate_limit_per_hour,
                remaining=0,
                reset=_calculate_reset_timestamp(now, "hour"),
                window_type="hour",
            )
            raise RateLimitExceeded(
                detail=f"Rate limit exceeded: {application.rate_limit_per_hour} requests per hour",
                retry_after=_calculate_retry_after(now, "hour"),
                rate_limit_info=rate_info,
            )

        # Redis succeeded
        _circuit_breaker.record_success()

        # Store rate limit info in request state for response headers
        rate_info = _get_most_restrictive_rate_info(
            minute_count=minute_count,
            minute_limit=application.rate_limit_per_minute,
            hour_count=hour_count,
            hour_limit=application.rate_limit_per_hour,
            now=now,
        )
        request.state.rate_limit_info = rate_info

    except (HTTPException, RateLimitExceeded):
        # Re-raise rate limit and service unavailable exceptions
        raise
    except Exception as e:
        # Record failure
        _circuit_breaker.record_failure()

        logger.debug(
            "Redis operation failed (failure %d/%d): %s",
            _circuit_breaker.failure_count,
            3,  # failure threshold
            str(e),
        )

        # Handle based on fail_open setting
        _handle_redis_unavailable(application, now, str(e))
