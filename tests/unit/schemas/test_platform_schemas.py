"""Unit tests for platform API Pydantic schemas.

This module contains tests for platform schemas including security tests
to ensure sensitive data is never exposed in API responses.
"""

import pytest

from app.schemas.platform import UserCreatedResponse, UserResponse


class TestPlatformSchemasSecurity:
    """Security tests for platform schemas.

    These tests ensure that sensitive fields like passwords are never
    accidentally exposed in API responses. This is a critical security
    control that prevents credential leakage.
    """

    # List of field names that should NEVER appear in user response schemas
    # These represent various common naming patterns for password fields
    SENSITIVE_FIELDS = [
        'password',
        'temporary_password',
        'password_hash',
        'hashed_password',
        'temp_password',
        'plain_password',
        'raw_password',
    ]

    def test_user_response_excludes_password_fields(self):
        """Verify UserResponse does not expose any password fields.

        This test exists to prevent accidental re-introduction of password
        fields in API responses, which would be a security vulnerability.
        Password fields should NEVER be included in response schemas as they:
        - Could be logged by intermediate proxies
        - Could be exposed in monitoring/APM systems
        - Could be cached by CDNs or browsers
        - Violate the principle of least privilege
        """
        for field in self.SENSITIVE_FIELDS:
            assert field not in UserResponse.model_fields, \
                f"Security violation: '{field}' should not be in UserResponse. " \
                f"Password fields must never be exposed in API responses."

    def test_user_created_response_excludes_password_fields(self):
        """Verify UserCreatedResponse does not expose any password fields.

        This test exists to prevent accidental re-introduction of password
        fields in API responses, which would be a security vulnerability.

        Note: Even though the caller may know the password they sent in the
        request, returning it in the response creates unnecessary exposure risk
        through logging, monitoring, and caching systems.
        """
        for field in self.SENSITIVE_FIELDS:
            assert field not in UserCreatedResponse.model_fields, \
                f"Security violation: '{field}' should not be in UserCreatedResponse. " \
                f"Password fields must never be exposed in API responses."

    def test_user_created_response_inherits_from_user_response(self):
        """Verify UserCreatedResponse properly inherits from UserResponse.

        This ensures that any security constraints on UserResponse
        automatically apply to UserCreatedResponse.
        """
        assert issubclass(UserCreatedResponse, UserResponse), \
            "UserCreatedResponse should inherit from UserResponse"

    def test_user_response_has_expected_fields(self):
        """Verify UserResponse has the expected non-sensitive fields.

        This test ensures the schema contains the fields we expect,
        serving as a sanity check that the schema hasn't been
        accidentally modified.
        """
        expected_fields = {
            'id',
            'email',
            'full_name',
            'role_name',
            'is_active',
            'is_verified',
            'created_at',
            'last_login',
        }
        actual_fields = set(UserResponse.model_fields.keys())

        assert expected_fields == actual_fields, \
            f"UserResponse fields mismatch. " \
            f"Expected: {expected_fields}, Got: {actual_fields}"

    def test_user_created_response_has_expected_additional_fields(self):
        """Verify UserCreatedResponse has only the expected additional fields.

        UserCreatedResponse should only add invitation_token to the base
        UserResponse fields. No other fields (especially password fields)
        should be added.
        """
        base_fields = set(UserResponse.model_fields.keys())
        created_fields = set(UserCreatedResponse.model_fields.keys())

        additional_fields = created_fields - base_fields
        expected_additional = {'invitation_token'}

        assert additional_fields == expected_additional, \
            f"UserCreatedResponse has unexpected additional fields. " \
            f"Expected only: {expected_additional}, Got: {additional_fields}"
