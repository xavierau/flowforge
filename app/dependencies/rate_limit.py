"""Rate limiting dependency for FastAPI endpoints.

This module provides rate limiting functionality using slowapi to protect
sensitive endpoints from brute-force attacks.

Rate limiting can be disabled via RATE_LIMIT_ENABLED=false environment variable
for testing purposes.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings


def _get_rate_limit_key(request) -> str:
    """
    Get the key for rate limiting.

    When rate limiting is disabled (e.g., in tests), returns a unique key
    per request to effectively bypass rate limits.

    When enabled, uses the client's IP address.
    """
    if not settings.rate_limit_enabled:
        # Return unique key per request to bypass rate limiting
        import uuid
        return str(uuid.uuid4())
    return get_remote_address(request)


# Create limiter instance
# When rate_limit_enabled=False, each request gets a unique key,
# effectively bypassing rate limits (useful for testing)
limiter = Limiter(key_func=_get_rate_limit_key)
