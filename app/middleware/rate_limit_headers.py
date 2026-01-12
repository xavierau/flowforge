"""Middleware to add rate limit headers to responses.

This middleware reads rate limit information from request.state
(set by platform_rate_limit.check_platform_rate_limit) and adds
standard rate limit headers to the response.

Headers added:
- X-RateLimit-Limit: Maximum requests allowed in the current window
- X-RateLimit-Remaining: Requests remaining in current window
- X-RateLimit-Reset: Unix timestamp when the rate limit resets
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitHeaderMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add rate limit headers to HTTP responses.

    This middleware checks if rate limit info was stored in request.state
    by the rate limiting dependency. If present, it adds the standard
    rate limit headers to the response.

    The rate limit info is expected to be a RateLimitInfo dataclass with:
    - limit: int - Maximum requests allowed
    - remaining: int - Requests remaining in window
    - reset: int - Unix timestamp when window resets
    """

    async def dispatch(self, request: Request, call_next):
        """
        Process request and add rate limit headers to response.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response with rate limit headers (if applicable)
        """
        response: Response = await call_next(request)

        # Check if rate limit info was stored by the rate limit dependency
        rate_limit_info = getattr(request.state, "rate_limit_info", None)

        if rate_limit_info is not None:
            response.headers["X-RateLimit-Limit"] = str(rate_limit_info.limit)
            response.headers["X-RateLimit-Remaining"] = str(
                rate_limit_info.remaining
            )
            response.headers["X-RateLimit-Reset"] = str(rate_limit_info.reset)

        return response
