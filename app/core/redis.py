"""Redis connection pool management.

This module provides centralized Redis connection pooling for the application.
The pool is lazily initialized on first access and shared across all components.

Features:
- Lazy initialization with thread-safe double-checked locking
- Configurable pool size via settings.redis_pool_size
- Graceful handling of initialization failures
- Proper cleanup on application shutdown

Usage:
    from app.core.redis import get_redis_client, close_redis_pool

    # Get a Redis client using the shared pool
    client = get_redis_client()
    if client:
        client.set("key", "value")

    # Clean up on shutdown (called in FastAPI lifespan)
    close_redis_pool()
"""

import logging
import threading
from typing import Optional

import redis

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level state for connection pool (lazy initialized)
_redis_pool: Optional[redis.ConnectionPool] = None
_pool_lock = threading.Lock()
_pool_init_failed = False


def get_redis_pool() -> Optional[redis.ConnectionPool]:
    """Get the shared Redis connection pool.

    Uses lazy initialization with thread-safe double-checked locking.
    Returns None if pool creation fails.

    Returns:
        Redis connection pool instance, or None if unavailable
    """
    global _redis_pool, _pool_init_failed

    # Fast path: pool already initialized
    if _redis_pool is not None:
        return _redis_pool

    # If initialization previously failed, don't retry
    if _pool_init_failed:
        return None

    # Thread-safe lazy initialization
    with _pool_lock:
        # Double-check after acquiring lock
        if _redis_pool is not None:
            return _redis_pool

        if _pool_init_failed:
            return None

        try:
            _redis_pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                max_connections=settings.redis_pool_size,
                decode_responses=False,
            )
            logger.info(
                "Redis connection pool initialized: max_connections=%d",
                settings.redis_pool_size,
            )
            return _redis_pool
        except Exception as e:
            logger.error("Failed to create Redis connection pool: %s", str(e))
            _pool_init_failed = True
            return None


def get_redis_client() -> Optional[redis.Redis]:
    """Get a Redis client using the shared connection pool.

    Returns:
        Redis client instance, or None if pool is unavailable
    """
    pool = get_redis_pool()
    if pool is None:
        return None
    return redis.Redis(connection_pool=pool)


def close_redis_pool() -> None:
    """Close the Redis connection pool.

    Should be called during application shutdown to cleanly
    release all connections.
    """
    global _redis_pool

    if _redis_pool is not None:
        try:
            _redis_pool.disconnect()
            logger.info("Redis connection pool closed")
        except Exception as e:
            logger.warning("Error closing Redis connection pool: %s", str(e))
        finally:
            _redis_pool = None


def reset_pool_state() -> None:
    """Reset pool state for testing purposes.

    Clears the pool reference and failure flag, allowing
    pool creation to be retried.
    """
    global _redis_pool, _pool_init_failed
    _redis_pool = None
    _pool_init_failed = False
