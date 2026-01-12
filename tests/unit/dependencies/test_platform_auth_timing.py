"""Unit tests for Platform Auth timing attack mitigation.

Test Coverage:
- Constant iteration count regardless of candidate count
- Configuration setting for minimum iterations
- Dummy hash usage for padding iterations
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4
from datetime import datetime


class TestConstantIterationTimingMitigation:
    """Test the constant iteration timing attack mitigation."""

    def test_minimum_iterations_config_exists(self):
        """Test that platform_auth_min_iterations setting exists in config."""
        from app.config import settings

        assert hasattr(settings, 'platform_auth_min_iterations')
        assert isinstance(settings.platform_auth_min_iterations, int)
        assert settings.platform_auth_min_iterations >= 1

    def test_minimum_iterations_default_value(self):
        """Test that platform_auth_min_iterations has appropriate default value."""
        from app.config import settings

        # Default should be 10 as per requirements
        assert settings.platform_auth_min_iterations == 10

    def test_constant_uses_config_value(self):
        """Test that MINIMUM_BCRYPT_COMPARISONS uses config value."""
        from app.config import settings
        from app.dependencies.platform_auth import get_minimum_bcrypt_comparisons

        # Should use config value, not hardcoded
        assert get_minimum_bcrypt_comparisons() == settings.platform_auth_min_iterations

    def test_dummy_hash_is_valid_bcrypt(self):
        """Test that DUMMY_BCRYPT_HASH is a valid bcrypt hash."""
        import bcrypt
        from app.dependencies.platform_auth import DUMMY_BCRYPT_HASH

        # Valid bcrypt hashes start with $2b$ or $2a$
        assert DUMMY_BCRYPT_HASH.startswith('$2')
        # Should be a string of appropriate length (60 chars for bcrypt)
        assert len(DUMMY_BCRYPT_HASH) == 60


class TestVerifyKeyConstantIterations:
    """Test that key verification always performs constant iterations."""

    @pytest.mark.asyncio
    async def test_single_candidate_performs_min_iterations(self):
        """Test that a single candidate still performs minimum iterations."""
        from app.dependencies.platform_auth import get_minimum_bcrypt_comparisons
        from app.services.platform_api_key_service import PlatformApiKeyService
        from app.config import settings

        min_iterations = settings.platform_auth_min_iterations

        # Track number of verify_key calls
        verify_calls = []
        original_verify = PlatformApiKeyService.verify_key

        def tracking_verify(key: str, key_hash: str) -> bool:
            verify_calls.append((key, key_hash))
            return original_verify(key, key_hash)

        with patch.object(PlatformApiKeyService, 'verify_key', tracking_verify):
            # Create mock request, db, and candidate
            from app.dependencies.platform_auth import (
                _verify_keys_constant_time,
                DUMMY_BCRYPT_HASH,
            )

            # Generate a real key for testing
            full_key, key_hash, key_prefix = PlatformApiKeyService.generate_key()

            # Create mock candidate
            candidate = MagicMock()
            candidate.token_hash = key_hash

            # Call with single candidate
            candidates = [candidate]
            result = _verify_keys_constant_time(full_key, candidates)

            # Should perform exactly min_iterations verifications
            assert len(verify_calls) == min_iterations
            assert result == candidate

    @pytest.mark.asyncio
    async def test_multiple_candidates_performs_min_iterations(self):
        """Test that multiple candidates still result in exactly min iterations."""
        from app.services.platform_api_key_service import PlatformApiKeyService
        from app.config import settings

        min_iterations = settings.platform_auth_min_iterations

        # Track verify calls
        verify_calls = []
        original_verify = PlatformApiKeyService.verify_key

        def tracking_verify(key: str, key_hash: str) -> bool:
            verify_calls.append((key, key_hash))
            return original_verify(key, key_hash)

        with patch.object(PlatformApiKeyService, 'verify_key', tracking_verify):
            from app.dependencies.platform_auth import _verify_keys_constant_time

            # Generate a real key and 3 fake candidate keys
            full_key, key_hash, _ = PlatformApiKeyService.generate_key()
            _, fake_hash1, _ = PlatformApiKeyService.generate_key()
            _, fake_hash2, _ = PlatformApiKeyService.generate_key()

            candidates = []
            for h in [fake_hash1, fake_hash2, key_hash]:  # Matching hash is last
                c = MagicMock()
                c.token_hash = h
                candidates.append(c)

            result = _verify_keys_constant_time(full_key, candidates)

            # Should perform exactly min_iterations verifications
            assert len(verify_calls) == min_iterations
            # Should find the matching candidate
            assert result == candidates[2]

    @pytest.mark.asyncio
    async def test_no_match_performs_min_iterations(self):
        """Test that even with no matching key, min iterations are performed."""
        from app.services.platform_api_key_service import PlatformApiKeyService
        from app.config import settings

        min_iterations = settings.platform_auth_min_iterations

        verify_calls = []
        original_verify = PlatformApiKeyService.verify_key

        def tracking_verify(key: str, key_hash: str) -> bool:
            verify_calls.append((key, key_hash))
            return original_verify(key, key_hash)

        with patch.object(PlatformApiKeyService, 'verify_key', tracking_verify):
            from app.dependencies.platform_auth import _verify_keys_constant_time

            # Generate keys that won't match
            full_key, _, _ = PlatformApiKeyService.generate_key()
            _, fake_hash1, _ = PlatformApiKeyService.generate_key()
            _, fake_hash2, _ = PlatformApiKeyService.generate_key()

            candidates = []
            for h in [fake_hash1, fake_hash2]:
                c = MagicMock()
                c.token_hash = h
                candidates.append(c)

            result = _verify_keys_constant_time(full_key, candidates)

            # Should perform exactly min_iterations verifications
            assert len(verify_calls) == min_iterations
            # No match found
            assert result is None

    @pytest.mark.asyncio
    async def test_more_candidates_than_min_iterations(self):
        """Test behavior when there are more candidates than min iterations."""
        from app.services.platform_api_key_service import PlatformApiKeyService
        from app.config import settings

        min_iterations = settings.platform_auth_min_iterations

        verify_calls = []
        original_verify = PlatformApiKeyService.verify_key

        def tracking_verify(key: str, key_hash: str) -> bool:
            verify_calls.append((key, key_hash))
            return original_verify(key, key_hash)

        with patch.object(PlatformApiKeyService, 'verify_key', tracking_verify):
            from app.dependencies.platform_auth import _verify_keys_constant_time

            # Generate a matching key
            full_key, key_hash, _ = PlatformApiKeyService.generate_key()

            # Create more candidates than min_iterations
            candidates = []
            for _ in range(min_iterations + 5):
                _, fake_hash, _ = PlatformApiKeyService.generate_key()
                c = MagicMock()
                c.token_hash = fake_hash
                candidates.append(c)

            # Add matching key at the end
            matching = MagicMock()
            matching.token_hash = key_hash
            candidates.append(matching)

            result = _verify_keys_constant_time(full_key, candidates)

            # Should verify ALL candidates (more than min)
            assert len(verify_calls) == len(candidates)
            # Should still find the match
            assert result == matching

    @pytest.mark.asyncio
    async def test_empty_candidates_performs_min_iterations(self):
        """Test that empty candidate list still performs min iterations."""
        from app.services.platform_api_key_service import PlatformApiKeyService
        from app.config import settings

        min_iterations = settings.platform_auth_min_iterations

        verify_calls = []
        original_verify = PlatformApiKeyService.verify_key

        def tracking_verify(key: str, key_hash: str) -> bool:
            verify_calls.append((key, key_hash))
            return original_verify(key, key_hash)

        with patch.object(PlatformApiKeyService, 'verify_key', tracking_verify):
            from app.dependencies.platform_auth import _verify_keys_constant_time

            full_key, _, _ = PlatformApiKeyService.generate_key()

            result = _verify_keys_constant_time(full_key, [])

            # Should still perform min_iterations dummy verifications
            assert len(verify_calls) == min_iterations
            # No match
            assert result is None


class TestDummyHashUsage:
    """Test that dummy hash is used appropriately for padding."""

    def test_dummy_hash_used_for_padding(self):
        """Test that dummy hash is used when padding iterations."""
        from app.services.platform_api_key_service import PlatformApiKeyService
        from app.dependencies.platform_auth import (
            _verify_keys_constant_time,
            DUMMY_BCRYPT_HASH,
        )
        from app.config import settings

        min_iterations = settings.platform_auth_min_iterations

        # Track which hashes are verified
        hashes_verified = []
        original_verify = PlatformApiKeyService.verify_key

        def tracking_verify(key: str, key_hash: str) -> bool:
            hashes_verified.append(key_hash)
            return original_verify(key, key_hash)

        with patch.object(PlatformApiKeyService, 'verify_key', tracking_verify):
            full_key, key_hash, _ = PlatformApiKeyService.generate_key()

            # Single candidate
            candidate = MagicMock()
            candidate.token_hash = key_hash

            _verify_keys_constant_time(full_key, [candidate])

            # First call should be real hash, rest should be dummy
            assert hashes_verified[0] == key_hash

            # Padding calls use dummy hash
            for h in hashes_verified[1:]:
                assert h == DUMMY_BCRYPT_HASH
