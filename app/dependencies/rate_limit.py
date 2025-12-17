"""Rate limiting dependency for FastAPI endpoints.

This module provides rate limiting functionality using slowapi to protect
sensitive endpoints from brute-force attacks.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create limiter instance with IP-based rate limiting
# Uses the client's remote address (IP) as the key for rate limiting
limiter = Limiter(key_func=get_remote_address)
