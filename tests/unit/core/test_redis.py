"""Unit tests for Redis connection pool module.

Test Coverage:
- Lazy initialization of connection pool
- Thread-safe pool access
- Configurable pool size
- Pool cleanup functionality
- Client retrieval from pool
"""

import threading
from unittest.mock import patch, MagicMock

import pytest


class TestRedisConnectionPool:
    """Test the Redis connection pool functionality."""

    def setup_method(self):
        """Reset the module state before each test."""
        from app.core import redis as redis_module
        redis_module._redis_pool = None
        redis_module._pool_init_failed = False

    def test_get_redis_pool_creates_pool_lazily(self):
        """Test that the pool is created on first access."""
        with patch("app.core.redis.redis.ConnectionPool") as mock_pool_class:
            mock_pool = MagicMock()
            mock_pool_class.from_url.return_value = mock_pool

            from app.core.redis import get_redis_pool

            pool = get_redis_pool()

            assert pool == mock_pool
            mock_pool_class.from_url.assert_called_once()

    def test_get_redis_pool_returns_same_pool_on_subsequent_calls(self):
        """Test that subsequent calls return the same pool instance."""
        with patch("app.core.redis.redis.ConnectionPool") as mock_pool_class:
            mock_pool = MagicMock()
            mock_pool_class.from_url.return_value = mock_pool

            from app.core.redis import get_redis_pool

            pool1 = get_redis_pool()
            pool2 = get_redis_pool()

            assert pool1 is pool2
            # Should only create pool once
            assert mock_pool_class.from_url.call_count == 1

    def test_get_redis_pool_uses_configured_pool_size(self):
        """Test that pool uses redis_pool_size from config."""
        with patch("app.core.redis.redis.ConnectionPool") as mock_pool_class:
            mock_pool = MagicMock()
            mock_pool_class.from_url.return_value = mock_pool

            with patch("app.core.redis.settings") as mock_settings:
                mock_settings.redis_url = "redis://localhost:6379/0"
                mock_settings.redis_pool_size = 25

                from app.core import redis as redis_module
                redis_module._redis_pool = None

                from app.core.redis import get_redis_pool
                get_redis_pool()

                mock_pool_class.from_url.assert_called_once_with(
                    "redis://localhost:6379/0",
                    max_connections=25,
                    decode_responses=False,
                )

    def test_get_redis_pool_is_thread_safe(self):
        """Test that pool initialization is thread-safe."""
        call_count = {"count": 0}
        original_pool = MagicMock()

        def mock_from_url(*args, **kwargs):
            call_count["count"] += 1
            return original_pool

        with patch("app.core.redis.redis.ConnectionPool") as mock_pool_class:
            mock_pool_class.from_url.side_effect = mock_from_url

            from app.core.redis import get_redis_pool

            results = []
            threads = []

            def get_pool():
                pool = get_redis_pool()
                results.append(pool)

            for _ in range(10):
                t = threading.Thread(target=get_pool)
                threads.append(t)

            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # All results should be the same pool
            assert all(r is original_pool for r in results)
            # Pool should only be created once
            assert call_count["count"] == 1

    def test_get_redis_client_returns_client_with_pool(self):
        """Test that get_redis_client returns a Redis client using the pool."""
        with patch("app.core.redis.redis.ConnectionPool") as mock_pool_class:
            with patch("app.core.redis.redis.Redis") as mock_redis_class:
                mock_pool = MagicMock()
                mock_pool_class.from_url.return_value = mock_pool
                mock_client = MagicMock()
                mock_redis_class.return_value = mock_client

                from app.core.redis import get_redis_client

                client = get_redis_client()

                assert client == mock_client
                mock_redis_class.assert_called_once_with(connection_pool=mock_pool)

    def test_close_redis_pool_disconnects_and_clears(self):
        """Test that close_redis_pool properly cleans up."""
        with patch("app.core.redis.redis.ConnectionPool") as mock_pool_class:
            mock_pool = MagicMock()
            mock_pool_class.from_url.return_value = mock_pool

            from app.core import redis as redis_module
            from app.core.redis import get_redis_pool, close_redis_pool

            # Initialize the pool
            get_redis_pool()
            assert redis_module._redis_pool is not None

            # Close the pool
            close_redis_pool()

            mock_pool.disconnect.assert_called_once()
            assert redis_module._redis_pool is None

    def test_close_redis_pool_handles_no_pool(self):
        """Test that close_redis_pool handles case when pool doesn't exist."""
        from app.core import redis as redis_module
        from app.core.redis import close_redis_pool

        # Ensure no pool exists
        redis_module._redis_pool = None

        # Should not raise
        close_redis_pool()

    def test_get_redis_pool_handles_creation_failure(self):
        """Test that pool creation failure is handled gracefully."""
        with patch("app.core.redis.redis.ConnectionPool") as mock_pool_class:
            mock_pool_class.from_url.side_effect = Exception("Connection failed")

            from app.core.redis import get_redis_pool

            pool = get_redis_pool()

            assert pool is None

    def test_get_redis_pool_returns_none_after_init_failure(self):
        """Test that subsequent calls return None after initialization failure."""
        with patch("app.core.redis.redis.ConnectionPool") as mock_pool_class:
            mock_pool_class.from_url.side_effect = Exception("Connection failed")

            from app.core import redis as redis_module
            from app.core.redis import get_redis_pool

            # First call - should fail
            pool1 = get_redis_pool()
            assert pool1 is None
            assert redis_module._pool_init_failed is True

            # Second call - should return None without retrying
            pool2 = get_redis_pool()
            assert pool2 is None
            # Should only try once
            assert mock_pool_class.from_url.call_count == 1

    def test_get_redis_client_returns_none_when_no_pool(self):
        """Test that get_redis_client returns None when pool is unavailable."""
        with patch("app.core.redis.redis.ConnectionPool") as mock_pool_class:
            mock_pool_class.from_url.side_effect = Exception("Connection failed")

            from app.core.redis import get_redis_client

            client = get_redis_client()

            assert client is None


class TestRedisPoolReset:
    """Test the pool reset functionality for testing purposes."""

    def setup_method(self):
        """Reset the module state before each test."""
        from app.core import redis as redis_module
        redis_module._redis_pool = None
        redis_module._pool_init_failed = False

    def test_reset_pool_state_clears_pool_and_flag(self):
        """Test that reset_pool_state clears both pool and failure flag."""
        from app.core import redis as redis_module
        from app.core.redis import reset_pool_state

        # Set up some state
        redis_module._redis_pool = MagicMock()
        redis_module._pool_init_failed = True

        # Reset
        reset_pool_state()

        assert redis_module._redis_pool is None
        assert redis_module._pool_init_failed is False

    def test_reset_pool_state_allows_retry_after_failure(self):
        """Test that reset allows retrying pool creation after failure."""
        with patch("app.core.redis.redis.ConnectionPool") as mock_pool_class:
            # First call fails
            mock_pool_class.from_url.side_effect = Exception("Connection failed")

            from app.core import redis as redis_module
            from app.core.redis import get_redis_pool, reset_pool_state

            pool1 = get_redis_pool()
            assert pool1 is None
            assert redis_module._pool_init_failed is True

            # Reset state
            reset_pool_state()

            # Second call succeeds
            mock_pool = MagicMock()
            mock_pool_class.from_url.side_effect = None
            mock_pool_class.from_url.return_value = mock_pool

            pool2 = get_redis_pool()
            assert pool2 is mock_pool
