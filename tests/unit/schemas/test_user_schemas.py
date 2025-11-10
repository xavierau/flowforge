"""Unit tests for user management Pydantic schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.user import (
    ProfileUpdateRequest,
    PasswordUpdateRequest,
    UserInviteRequest,
    UserUpdateRequest,
)


class TestProfileUpdateRequest:
    """Test ProfileUpdateRequest schema validation."""

    def test_valid_full_name_update(self):
        """Test valid full_name update."""
        data = {"full_name": "John Doe"}
        request = ProfileUpdateRequest(**data)
        assert request.full_name == "John Doe"

    def test_valid_locale_update(self):
        """Test valid locale update."""
        for locale in ["en", "zh-TW", "zh-CN"]:
            data = {"locale": locale}
            request = ProfileUpdateRequest(**data)
            assert request.locale == locale

    def test_invalid_locale(self):
        """Test invalid locale raises validation error."""
        data = {"locale": "fr"}
        with pytest.raises(ValidationError) as exc_info:
            ProfileUpdateRequest(**data)
        assert "locale must be one of" in str(exc_info.value).lower()

    def test_valid_avatar_url(self):
        """Test valid avatar URL."""
        data = {"avatar_url": "https://example.com/avatar.jpg"}
        request = ProfileUpdateRequest(**data)
        assert request.avatar_url == "https://example.com/avatar.jpg"

    def test_invalid_avatar_url(self):
        """Test invalid avatar URL format."""
        data = {"avatar_url": "not-a-valid-url"}
        with pytest.raises(ValidationError) as exc_info:
            ProfileUpdateRequest(**data)
        assert "valid http" in str(exc_info.value).lower()

    def test_all_fields_optional(self):
        """Test that all fields are optional."""
        request = ProfileUpdateRequest()
        assert request.full_name is None
        assert request.avatar_url is None
        assert request.locale is None

    def test_multiple_fields(self):
        """Test updating multiple fields."""
        data = {
            "full_name": "Jane Smith",
            "avatar_url": "https://example.com/jane.jpg",
            "locale": "zh-TW"
        }
        request = ProfileUpdateRequest(**data)
        assert request.full_name == "Jane Smith"
        assert request.avatar_url == "https://example.com/jane.jpg"
        assert request.locale == "zh-TW"


class TestPasswordUpdateRequest:
    """Test PasswordUpdateRequest schema validation."""

    def test_valid_password_update(self):
        """Test valid password update."""
        data = {
            "current_password": "OldPass123",
            "new_password": "NewPass456"
        }
        request = PasswordUpdateRequest(**data)
        assert request.current_password == "OldPass123"
        assert request.new_password == "NewPass456"

    def test_password_too_short(self):
        """Test password shorter than 8 characters."""
        data = {
            "current_password": "OldPass123",
            "new_password": "Short1"
        }
        with pytest.raises(ValidationError) as exc_info:
            PasswordUpdateRequest(**data)
        assert "at least 8 characters" in str(exc_info.value).lower()

    def test_password_no_uppercase(self):
        """Test password without uppercase letter."""
        data = {
            "current_password": "OldPass123",
            "new_password": "lowercase123"
        }
        with pytest.raises(ValidationError) as exc_info:
            PasswordUpdateRequest(**data)
        assert "uppercase" in str(exc_info.value).lower()

    def test_password_no_number(self):
        """Test password without number."""
        data = {
            "current_password": "OldPass123",
            "new_password": "NoNumberPass"
        }
        with pytest.raises(ValidationError) as exc_info:
            PasswordUpdateRequest(**data)
        assert "number" in str(exc_info.value).lower()

    def test_current_password_required(self):
        """Test that current_password is required."""
        data = {"new_password": "NewPass456"}
        with pytest.raises(ValidationError):
            PasswordUpdateRequest(**data)

    def test_new_password_required(self):
        """Test that new_password is required."""
        data = {"current_password": "OldPass123"}
        with pytest.raises(ValidationError):
            PasswordUpdateRequest(**data)


class TestUserInviteRequest:
    """Test UserInviteRequest schema validation."""

    def test_valid_invitation(self):
        """Test valid invitation request."""
        data = {
            "email": "newuser@example.com",
            "role_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        request = UserInviteRequest(**data)
        assert request.email == "newuser@example.com"

    def test_email_normalized_to_lowercase(self):
        """Test that email is normalized to lowercase."""
        data = {
            "email": "NewUser@Example.COM",
            "role_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        request = UserInviteRequest(**data)
        assert request.email == "newuser@example.com"

    def test_invalid_email_format(self):
        """Test invalid email format."""
        data = {
            "email": "not-an-email",
            "role_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        with pytest.raises(ValidationError) as exc_info:
            UserInviteRequest(**data)
        assert "invalid email" in str(exc_info.value).lower()

    def test_email_required(self):
        """Test that email is required."""
        data = {"role_id": "550e8400-e29b-41d4-a716-446655440000"}
        with pytest.raises(ValidationError):
            UserInviteRequest(**data)

    def test_role_id_required(self):
        """Test that role_id is required."""
        data = {"email": "newuser@example.com"}
        with pytest.raises(ValidationError):
            UserInviteRequest(**data)

    def test_invalid_role_id_format(self):
        """Test invalid UUID format for role_id."""
        data = {
            "email": "newuser@example.com",
            "role_id": "not-a-uuid"
        }
        with pytest.raises(ValidationError):
            UserInviteRequest(**data)


class TestUserUpdateRequest:
    """Test UserUpdateRequest schema validation."""

    def test_all_fields_optional(self):
        """Test that all fields are optional."""
        request = UserUpdateRequest()
        assert request.role_id is None
        assert request.is_active is None
        assert request.full_name is None

    def test_update_role_id(self):
        """Test updating role_id."""
        data = {"role_id": "550e8400-e29b-41d4-a716-446655440000"}
        request = UserUpdateRequest(**data)
        assert str(request.role_id) == "550e8400-e29b-41d4-a716-446655440000"

    def test_update_is_active(self):
        """Test updating is_active status."""
        data = {"is_active": False}
        request = UserUpdateRequest(**data)
        assert request.is_active is False

    def test_update_full_name(self):
        """Test updating full_name."""
        data = {"full_name": "Updated Name"}
        request = UserUpdateRequest(**data)
        assert request.full_name == "Updated Name"

    def test_update_multiple_fields(self):
        """Test updating multiple fields."""
        data = {
            "role_id": "550e8400-e29b-41d4-a716-446655440000",
            "is_active": True,
            "full_name": "John Updated"
        }
        request = UserUpdateRequest(**data)
        assert str(request.role_id) == "550e8400-e29b-41d4-a716-446655440000"
        assert request.is_active is True
        assert request.full_name == "John Updated"

    def test_invalid_role_id_format(self):
        """Test invalid UUID format for role_id."""
        data = {"role_id": "not-a-uuid"}
        with pytest.raises(ValidationError):
            UserUpdateRequest(**data)
