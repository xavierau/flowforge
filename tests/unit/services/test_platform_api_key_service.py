"""Unit tests for PlatformApiKeyService."""

import pytest
from datetime import datetime, timedelta

from app.services.platform_api_key_service import PlatformApiKeyService


class TestPlatformApiKeyService:
    """Tests for PlatformApiKeyService."""

    def test_generate_key_format(self):
        """Test that generated key has correct format."""
        full_key, key_hash, key_prefix = PlatformApiKeyService.generate_key()

        # Check full key format: pk_live_{32}_{12}
        assert full_key.startswith("pk_live_")
        parts = full_key.split("_")
        assert len(parts) == 4  # pk, live, identifier, checksum
        assert len(parts[2]) == 32  # identifier
        assert len(parts[3]) == 12  # checksum

    def test_generate_key_prefix_format(self):
        """Test that key prefix has correct format."""
        full_key, key_hash, key_prefix = PlatformApiKeyService.generate_key()

        # Prefix should be pk_live_ + first 8 chars of identifier
        assert key_prefix.startswith("pk_live_")
        assert len(key_prefix) == len("pk_live_") + 8

    def test_generate_key_hash_is_valid(self):
        """Test that key hash can be verified."""
        full_key, key_hash, key_prefix = PlatformApiKeyService.generate_key()

        # Hash should start with bcrypt signature
        assert key_hash.startswith("$2")

        # Verify the key against its hash
        assert PlatformApiKeyService.verify_key(full_key, key_hash) is True

    def test_generate_key_uniqueness(self):
        """Test that generated keys are unique."""
        keys = set()
        for _ in range(10):
            full_key, _, _ = PlatformApiKeyService.generate_key()
            keys.add(full_key)

        assert len(keys) == 10  # All keys should be unique

    def test_verify_key_correct(self):
        """Test verification of correct key."""
        full_key, key_hash, _ = PlatformApiKeyService.generate_key()

        assert PlatformApiKeyService.verify_key(full_key, key_hash) is True

    def test_verify_key_incorrect(self):
        """Test verification of incorrect key."""
        _, key_hash, _ = PlatformApiKeyService.generate_key()
        wrong_key = "pk_live_wrongkey12345678901234567890_wrongchecksum"

        assert PlatformApiKeyService.verify_key(wrong_key, key_hash) is False

    def test_verify_key_invalid_hash(self):
        """Test verification with invalid hash."""
        full_key, _, _ = PlatformApiKeyService.generate_key()

        assert PlatformApiKeyService.verify_key(full_key, "invalid_hash") is False

    def test_is_key_expired_none(self):
        """Test that None expiration means not expired."""
        assert PlatformApiKeyService.is_key_expired(None) is False

    def test_is_key_expired_future(self):
        """Test that future expiration means not expired."""
        future = datetime.utcnow() + timedelta(days=1)
        assert PlatformApiKeyService.is_key_expired(future) is False

    def test_is_key_expired_past(self):
        """Test that past expiration means expired."""
        past = datetime.utcnow() - timedelta(days=1)
        assert PlatformApiKeyService.is_key_expired(past) is True

    # matches_scope() tests - single source of truth for scope matching logic
    def test_matches_scope_exact_match(self):
        """Test matches_scope with exact matches."""
        assert PlatformApiKeyService.matches_scope("tenants:read", "tenants:read") is True
        assert PlatformApiKeyService.matches_scope("users:create", "users:create") is True

    def test_matches_scope_exact_no_match(self):
        """Test matches_scope with non-matching scopes."""
        assert PlatformApiKeyService.matches_scope("tenants:read", "tenants:create") is False
        assert PlatformApiKeyService.matches_scope("tenants:read", "users:read") is False

    def test_matches_scope_resource_wildcard(self):
        """Test matches_scope with resource wildcard."""
        assert PlatformApiKeyService.matches_scope("tenants:*", "tenants:read") is True
        assert PlatformApiKeyService.matches_scope("tenants:*", "tenants:create") is True
        assert PlatformApiKeyService.matches_scope("tenants:*", "tenants:delete") is True
        # Different resource should not match
        assert PlatformApiKeyService.matches_scope("tenants:*", "users:read") is False

    def test_matches_scope_full_wildcard(self):
        """Test matches_scope with full wildcard."""
        assert PlatformApiKeyService.matches_scope("*:*", "tenants:read") is True
        assert PlatformApiKeyService.matches_scope("*:*", "users:create") is True
        assert PlatformApiKeyService.matches_scope("*:*", "anything:anything") is True

    def test_matches_scope_partial_wildcard_in_required_not_matched(self):
        """Test that wildcards in required scope are not treated specially."""
        # If required scope has wildcard, it must match exactly
        assert PlatformApiKeyService.matches_scope("tenants:read", "tenants:*") is False
        assert PlatformApiKeyService.matches_scope("tenants:read", "*:*") is False

    # validate_scope() tests - uses matches_scope() internally
    def test_validate_scope_exact_match(self):
        """Test scope validation with exact match."""
        scopes = ["tenants:create", "users:read"]

        assert PlatformApiKeyService.validate_scope(scopes, "tenants:create") is True
        assert PlatformApiKeyService.validate_scope(scopes, "users:read") is True
        assert PlatformApiKeyService.validate_scope(scopes, "users:create") is False

    def test_validate_scope_wildcard(self):
        """Test scope validation with wildcard."""
        scopes = ["tenants:*", "users:read"]

        assert PlatformApiKeyService.validate_scope(scopes, "tenants:create") is True
        assert PlatformApiKeyService.validate_scope(scopes, "tenants:read") is True
        assert PlatformApiKeyService.validate_scope(scopes, "tenants:delete") is True
        assert PlatformApiKeyService.validate_scope(scopes, "users:read") is True
        assert PlatformApiKeyService.validate_scope(scopes, "users:create") is False

    def test_validate_scope_full_wildcard(self):
        """Test scope validation with full wildcard."""
        scopes = ["*:*"]

        assert PlatformApiKeyService.validate_scope(scopes, "tenants:create") is True
        assert PlatformApiKeyService.validate_scope(scopes, "users:read") is True
        assert PlatformApiKeyService.validate_scope(scopes, "anything:anything") is True

    def test_extract_key_from_header_bearer(self):
        """Test extracting key from Bearer header."""
        key = "pk_live_abc12345678901234567890123456_def123456789"
        header = f"Bearer {key}"

        assert PlatformApiKeyService.extract_key_from_header(header) == key

    def test_extract_key_from_header_direct(self):
        """Test extracting key from direct header (no Bearer)."""
        key = "pk_live_abc12345678901234567890123456_def123456789"

        assert PlatformApiKeyService.extract_key_from_header(key) == key

    def test_extract_key_from_header_invalid_prefix(self):
        """Test extracting key with invalid prefix returns None."""
        header = "Bearer sk_live_wrongprefix12345678901234567_wrongchecksum"

        assert PlatformApiKeyService.extract_key_from_header(header) is None

    def test_extract_key_from_header_none(self):
        """Test extracting key from None header."""
        assert PlatformApiKeyService.extract_key_from_header(None) is None

    def test_parse_key_prefix_valid(self):
        """Test parsing prefix from valid key."""
        key = "pk_live_abc12345678901234567890123456_def123456789"
        prefix = PlatformApiKeyService.parse_key_prefix(key)

        assert prefix == "pk_live_abc12345"

    def test_parse_key_prefix_invalid(self):
        """Test parsing prefix from invalid key."""
        assert PlatformApiKeyService.parse_key_prefix("sk_live_abc") is None
        assert PlatformApiKeyService.parse_key_prefix("invalid") is None
        assert PlatformApiKeyService.parse_key_prefix("") is None
        assert PlatformApiKeyService.parse_key_prefix(None) is None

    def test_generate_webhook_secret(self):
        """Test webhook secret generation."""
        secret = PlatformApiKeyService.generate_webhook_secret()

        # Should be a 64-character hex string (32 bytes)
        assert len(secret) == 64
        assert all(c in "0123456789abcdef" for c in secret)

    def test_generate_webhook_secret_uniqueness(self):
        """Test that generated secrets are unique."""
        secrets = set()
        for _ in range(10):
            secrets.add(PlatformApiKeyService.generate_webhook_secret())

        assert len(secrets) == 10
