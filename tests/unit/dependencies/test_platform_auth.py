"""Unit tests for Platform Auth sanitization logic.

Test Coverage:
- Sensitive field pattern matching (positive cases)
- False positive avoidance (negative cases)
- Recursive sanitization of nested dicts and lists
- Edge cases (None, empty dict, non-dict values)
"""

import pytest

from app.dependencies.platform_auth import (
    _is_sensitive_key,
    sanitize_audit_metadata,
    SENSITIVE_FIELD_PATTERNS,
)


class TestIsSensitiveKey:
    """Test the _is_sensitive_key helper function."""

    # --- Positive cases: These SHOULD be detected as sensitive ---

    @pytest.mark.parametrize(
        "field_name",
        [
            # Password variations
            "password",
            "Password",
            "PASSWORD",
            "user_password",
            "password_hash",
            "passwd",
            "pass",
            # Token variations (specific patterns)
            "access_token",
            "refresh_token",
            "auth_token",
            "bearer_token",
            "api_token",
            "session_token",
            "jwt_token",
            "token_secret",
            "oauth_token",
            # Secret variations
            "secret",
            "client_secret",
            "app_secret",
            "api_secret",
            # API key variations
            "api_key",
            "apikey",
            "api-key",
            "user_api_key",
            # Credential variations
            "credential",
            "credentials",
            "user_credentials",
            # Auth-related (specific patterns, not general "auth")
            "authorization",
            "auth_key",
            "auth_secret",
            "auth_code",
            "auth_header",
            "auth-token",
            "auth-key",
            # Private key patterns (security-related only)
            "private_key",
            "private_secret",
            "private_token",
            "private-key",
            # Encryption-related
            "encryption_key",
            "signing_key",
            "hmac_key",
            # SSH/PGP keys
            "ssh_key",
            "pgp_key",
            "rsa_key",
            # OAuth-related
            "oauth_secret",
            "client_id",
            # PIN/OTP
            "pin",
            "otp",
            "totp",
            "hotp",
        ],
    )
    def test_detects_sensitive_fields(self, field_name: str):
        """Test that sensitive field names are correctly detected."""
        assert _is_sensitive_key(field_name), (
            f"Expected '{field_name}' to be detected as sensitive"
        )

    # --- Negative cases: These should NOT be detected as sensitive ---

    @pytest.mark.parametrize(
        "field_name",
        [
            # Should NOT match "auth" patterns
            "author",
            "author_name",
            "author_id",
            "authors",
            "authored_by",
            "authenticate_user",
            "authentication_method",
            "authority",
            "authoritative",
            # Should NOT match "private" patterns
            "private_room_count",
            "private_notes",
            "private_mode",
            "is_private",
            "private_channel",
            "private_message",
            "private_data",
            # Should NOT match "token" patterns (these are not auth-related)
            "token_count",
            "tokenize",
            "tokenizer",
            "total_tokens",
            "input_tokens",
            "output_tokens",
            # Should NOT match "secret" patterns (non-sensitive uses)
            # Note: "secret" itself is sensitive, but compound words might not be
            # Keeping this commented as "secret" by itself should always match
            # Should NOT match - general field names
            "user_id",
            "email",
            "name",
            "description",
            "status",
            "created_at",
            "updated_at",
            "document_id",
            "file_path",
            "url",
            "endpoint",
            "method",
            # Should NOT match "pass" in compound words (not passwords)
            "pass_through",
            "passed",
            "passenger",
            "bypass",
            "passport",
            # Should NOT match "key" in general contexts
            "key",
            "primary_key",
            "foreign_key",
            "sort_key",
            "cache_key",
            "lookup_key",
            # Should NOT match "pin" in general contexts
            # Note: "pin" by itself matches - this is a known trade-off
            "pinned",
            "pinning",
            "pincode",
        ],
    )
    def test_does_not_match_legitimate_fields(self, field_name: str):
        """Test that legitimate field names are NOT falsely flagged."""
        assert not _is_sensitive_key(field_name), (
            f"Expected '{field_name}' to NOT be detected as sensitive"
        )


class TestSanitizeAuditMetadata:
    """Test the sanitize_audit_metadata function."""

    def test_sanitizes_sensitive_fields(self):
        """Test that sensitive fields are redacted."""
        metadata = {
            "user_id": "123",
            "password": "secret123",
            "api_key": "sk-abc123",
            "action": "login",
        }

        result = sanitize_audit_metadata(metadata)

        assert result["user_id"] == "123"
        assert result["password"] == "[REDACTED]"
        assert result["api_key"] == "[REDACTED]"
        assert result["action"] == "login"

    def test_preserves_legitimate_fields(self):
        """Test that legitimate fields are preserved."""
        metadata = {
            "author": "John Doe",
            "private_room_count": 5,
            "token_count": 100,
            "status": "active",
        }

        result = sanitize_audit_metadata(metadata)

        assert result["author"] == "John Doe"
        assert result["private_room_count"] == 5
        assert result["token_count"] == 100
        assert result["status"] == "active"

    def test_handles_nested_dicts(self):
        """Test recursive sanitization of nested dictionaries."""
        metadata = {
            "user": {
                "name": "John",
                "password": "secret123",
                "settings": {
                    "api_key": "sk-abc123",
                    "theme": "dark",
                },
            },
            "author": "Jane",
        }

        result = sanitize_audit_metadata(metadata)

        assert result["user"]["name"] == "John"
        assert result["user"]["password"] == "[REDACTED]"
        assert result["user"]["settings"]["api_key"] == "[REDACTED]"
        assert result["user"]["settings"]["theme"] == "dark"
        assert result["author"] == "Jane"

    def test_handles_lists_with_dicts(self):
        """Test sanitization of lists containing dictionaries."""
        metadata = {
            "tokens": [
                {"access_token": "abc123", "type": "bearer"},
                {"refresh_token": "xyz789", "type": "refresh"},
            ],
            "authors": ["John", "Jane"],
        }

        result = sanitize_audit_metadata(metadata)

        assert result["tokens"][0]["access_token"] == "[REDACTED]"
        assert result["tokens"][0]["type"] == "bearer"
        assert result["tokens"][1]["refresh_token"] == "[REDACTED]"
        assert result["tokens"][1]["type"] == "refresh"
        assert result["authors"] == ["John", "Jane"]

    def test_handles_none_input(self):
        """Test that None input returns empty dict."""
        result = sanitize_audit_metadata(None)
        assert result == {}

    def test_handles_empty_dict(self):
        """Test that empty dict returns empty dict."""
        result = sanitize_audit_metadata({})
        assert result == {}

    def test_handles_non_dict_input(self):
        """Test that non-dict input is returned as-is."""
        assert sanitize_audit_metadata("string") == "string"
        assert sanitize_audit_metadata(123) == 123
        assert sanitize_audit_metadata([1, 2, 3]) == [1, 2, 3]


class TestSensitiveFieldPatterns:
    """Test the pattern definitions themselves."""

    def test_patterns_are_compiled(self):
        """Test that all patterns are compiled regex objects."""
        import re

        for pattern in SENSITIVE_FIELD_PATTERNS:
            assert isinstance(pattern, re.Pattern), (
                f"Pattern {pattern} should be a compiled regex"
            )

    def test_patterns_use_ignore_case(self):
        """Test that all patterns use case-insensitive matching."""
        import re

        for pattern in SENSITIVE_FIELD_PATTERNS:
            assert pattern.flags & re.IGNORECASE, (
                f"Pattern {pattern.pattern} should use IGNORECASE flag"
            )
