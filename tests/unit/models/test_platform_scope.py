"""Unit tests for PlatformScope enum and validation."""

import pytest

from app.models.enums import PlatformScope


class TestPlatformScope:
    """Tests for PlatformScope enum."""

    def test_all_scopes_returns_all_values(self):
        """Test that all_scopes returns all scope values."""
        scopes = PlatformScope.all_scopes()

        assert "tenants:create" in scopes
        assert "tenants:read" in scopes
        assert "users:create" in scopes
        assert "credits:add" in scopes

    def test_validate_scopes_exact_valid(self):
        """Test validation of exact valid scopes."""
        assert PlatformScope.validate_scopes(["tenants:create"]) is True
        assert PlatformScope.validate_scopes(["users:read", "credits:add"]) is True
        assert PlatformScope.validate_scopes(PlatformScope.all_scopes()) is True

    def test_validate_scopes_invalid_scope(self):
        """Test validation rejects invalid scopes."""
        assert PlatformScope.validate_scopes(["invalid:scope"]) is False
        assert PlatformScope.validate_scopes(["tenants:create", "invalid:scope"]) is False
        assert PlatformScope.validate_scopes(["foo:bar"]) is False

    def test_validate_scopes_full_wildcard(self):
        """Test validation accepts full wildcard."""
        assert PlatformScope.validate_scopes(["*:*"]) is True
        assert PlatformScope.validate_scopes(["*:*", "tenants:read"]) is True

    def test_validate_scopes_resource_wildcard(self):
        """Test validation accepts valid resource wildcards."""
        assert PlatformScope.validate_scopes(["tenants:*"]) is True
        assert PlatformScope.validate_scopes(["users:*"]) is True
        assert PlatformScope.validate_scopes(["credits:*"]) is True
        assert PlatformScope.validate_scopes(["tokens:*"]) is True

    def test_validate_scopes_invalid_resource_wildcard(self):
        """Test validation rejects invalid resource wildcards."""
        assert PlatformScope.validate_scopes(["invalid:*"]) is False
        assert PlatformScope.validate_scopes(["foo:*"]) is False

    def test_validate_scopes_empty_list(self):
        """Test validation of empty scope list."""
        assert PlatformScope.validate_scopes([]) is True

    def test_validate_scopes_mixed_valid_wildcards(self):
        """Test validation with mix of exact and wildcard scopes."""
        assert PlatformScope.validate_scopes(["tenants:*", "users:read"]) is True
        assert PlatformScope.validate_scopes(["*:*", "tenants:create"]) is True

    def test_validate_scopes_consistency_with_matches_scope(self):
        """Test that validate_scopes uses same logic as PlatformApiKeyService.matches_scope."""
        from app.services.platform_api_key_service import PlatformApiKeyService

        # If a wildcard would match any valid scope, it should be valid
        # tenants:* matches tenants:create, so it's valid
        assert PlatformApiKeyService.matches_scope("tenants:*", "tenants:create") is True
        assert PlatformScope.validate_scopes(["tenants:*"]) is True

        # invalid:* doesn't match any valid scope, so it's invalid
        valid_scopes = PlatformScope.all_scopes()
        matches_any = any(
            PlatformApiKeyService.matches_scope("invalid:*", scope)
            for scope in valid_scopes
        )
        assert matches_any is False
        assert PlatformScope.validate_scopes(["invalid:*"]) is False


class TestPlatformScopeMatchesScope:
    """Tests for PlatformScope.matches_scope() - the single source of truth."""

    def test_matches_scope_exact_match(self):
        """Test exact scope matches."""
        assert PlatformScope.matches_scope("tenants:read", "tenants:read") is True
        assert PlatformScope.matches_scope("users:create", "users:create") is True
        assert PlatformScope.matches_scope("credits:add", "credits:add") is True

    def test_matches_scope_exact_no_match(self):
        """Test non-matching exact scopes."""
        assert PlatformScope.matches_scope("tenants:read", "tenants:create") is False
        assert PlatformScope.matches_scope("tenants:read", "users:read") is False
        assert PlatformScope.matches_scope("users:create", "credits:add") is False

    def test_matches_scope_full_wildcard(self):
        """Test full wildcard *:* matches everything."""
        assert PlatformScope.matches_scope("*:*", "tenants:read") is True
        assert PlatformScope.matches_scope("*:*", "users:create") is True
        assert PlatformScope.matches_scope("*:*", "credits:add") is True
        assert PlatformScope.matches_scope("*:*", "anything:anything") is True

    def test_matches_scope_resource_wildcard(self):
        """Test resource wildcard matches all actions for that resource."""
        # tenants:* matches all tenant scopes
        assert PlatformScope.matches_scope("tenants:*", "tenants:create") is True
        assert PlatformScope.matches_scope("tenants:*", "tenants:read") is True
        assert PlatformScope.matches_scope("tenants:*", "tenants:update") is True
        assert PlatformScope.matches_scope("tenants:*", "tenants:delete") is True

        # users:* matches all user scopes
        assert PlatformScope.matches_scope("users:*", "users:create") is True
        assert PlatformScope.matches_scope("users:*", "users:read") is True

        # Resource wildcard doesn't match different resources
        assert PlatformScope.matches_scope("tenants:*", "users:read") is False
        assert PlatformScope.matches_scope("users:*", "tenants:create") is False

    def test_matches_scope_wildcard_in_required_not_special(self):
        """Test that wildcards in required scope are NOT treated specially."""
        # If required scope has wildcard, it must match exactly
        assert PlatformScope.matches_scope("tenants:read", "tenants:*") is False
        assert PlatformScope.matches_scope("tenants:read", "*:*") is False
        assert PlatformScope.matches_scope("users:create", "*:*") is False


class TestPlatformScopeHasRequiredScope:
    """Tests for PlatformScope.has_required_scope() method."""

    def test_has_required_scope_exact_match(self):
        """Test exact scope matching in list."""
        assert PlatformScope.has_required_scope(
            ["tenants:create", "users:read"], "tenants:create"
        ) is True
        assert PlatformScope.has_required_scope(
            ["tenants:create", "users:read"], "users:read"
        ) is True

    def test_has_required_scope_no_match(self):
        """Test when required scope is not in list."""
        assert PlatformScope.has_required_scope(
            ["tenants:create", "users:read"], "credits:add"
        ) is False
        assert PlatformScope.has_required_scope(
            ["tenants:create"], "tenants:read"
        ) is False

    def test_has_required_scope_with_full_wildcard(self):
        """Test full wildcard grants all permissions."""
        assert PlatformScope.has_required_scope(["*:*"], "tenants:create") is True
        assert PlatformScope.has_required_scope(["*:*"], "users:read") is True
        assert PlatformScope.has_required_scope(["*:*"], "anything:anything") is True

    def test_has_required_scope_with_resource_wildcard(self):
        """Test resource wildcard grants all actions for that resource."""
        assert PlatformScope.has_required_scope(
            ["tenants:*"], "tenants:create"
        ) is True
        assert PlatformScope.has_required_scope(
            ["tenants:*"], "tenants:read"
        ) is True
        assert PlatformScope.has_required_scope(
            ["tenants:*"], "tenants:delete"
        ) is True
        # But not other resources
        assert PlatformScope.has_required_scope(
            ["tenants:*"], "users:read"
        ) is False

    def test_has_required_scope_mixed_scopes(self):
        """Test with mix of exact and wildcard scopes."""
        scopes = ["tenants:*", "users:read", "credits:add"]

        # tenants:* grants all tenant operations
        assert PlatformScope.has_required_scope(scopes, "tenants:create") is True
        assert PlatformScope.has_required_scope(scopes, "tenants:delete") is True

        # Exact scopes work
        assert PlatformScope.has_required_scope(scopes, "users:read") is True
        assert PlatformScope.has_required_scope(scopes, "credits:add") is True

        # But not other scopes
        assert PlatformScope.has_required_scope(scopes, "users:create") is False
        assert PlatformScope.has_required_scope(scopes, "credits:read") is False

    def test_has_required_scope_empty_list(self):
        """Test empty scope list has no permissions."""
        assert PlatformScope.has_required_scope([], "tenants:read") is False
        assert PlatformScope.has_required_scope([], "*:*") is False
