"""Unit tests for authentication Pydantic schemas.

Test Coverage:
- Request schema validation (email format, password strength, field requirements)
- Response schema construction
- Field validators
- Edge cases and error handling
"""

import pytest
from pydantic import ValidationError
from datetime import datetime
from uuid import uuid4

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    LogoutRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
    TenantInfo,
    UserInfo,
    TokenResponse,
    AuthResponse,
    MessageResponse,
    UserProfileResponse,
)


class TestRegisterRequest:
    """Test RegisterRequest schema validation."""

    def test_valid_registration_with_tenant(self):
        """Test valid registration with tenant creation."""
        data = {
            "email": "test@example.com",
            "password": "SecurePass123",
            "full_name": "John Doe",
            "tenant_name": "Acme Corp"
        }
        request = RegisterRequest(**data)

        assert request.email == "test@example.com"
        assert request.password == "SecurePass123"
        assert request.full_name == "John Doe"
        assert request.tenant_name == "Acme Corp"

    def test_valid_registration_without_tenant(self):
        """Test valid registration without tenant (join existing)."""
        data = {
            "email": "test@example.com",
            "password": "SecurePass123"
        }
        request = RegisterRequest(**data)

        assert request.email == "test@example.com"
        assert request.password == "SecurePass123"
        assert request.full_name is None
        assert request.tenant_name is None

    def test_email_normalized_to_lowercase(self):
        """Test email is automatically converted to lowercase."""
        data = {
            "email": "TEST@EXAMPLE.COM",
            "password": "SecurePass123"
        }
        request = RegisterRequest(**data)

        assert request.email == "test@example.com"

    def test_invalid_email_format(self):
        """Test validation fails for invalid email formats."""
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user @example.com",
            "user@example",
        ]

        for email in invalid_emails:
            with pytest.raises(ValidationError) as exc_info:
                RegisterRequest(
                    email=email,
                    password="SecurePass123"
                )
            assert "email" in str(exc_info.value).lower()

    def test_password_too_short(self):
        """Test validation fails for password < 8 characters."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                email="test@example.com",
                password="Short1"
            )
        assert "at least 8 characters" in str(exc_info.value).lower()

    def test_password_missing_uppercase(self):
        """Test validation fails for password without uppercase letter."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                email="test@example.com",
                password="lowercase123"
            )
        assert "uppercase" in str(exc_info.value).lower()

    def test_password_missing_number(self):
        """Test validation fails for password without number."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                email="test@example.com",
                password="NoNumbers"
            )
        assert "number" in str(exc_info.value).lower()

    def test_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        # Missing email
        with pytest.raises(ValidationError):
            RegisterRequest(password="SecurePass123")

        # Missing password
        with pytest.raises(ValidationError):
            RegisterRequest(email="test@example.com")


class TestLoginRequest:
    """Test LoginRequest schema validation."""

    def test_valid_login(self):
        """Test valid login request."""
        data = {
            "email": "test@example.com",
            "password": "SecurePass123"
        }
        request = LoginRequest(**data)

        assert request.email == "test@example.com"
        assert request.password == "SecurePass123"

    def test_email_normalized_to_lowercase(self):
        """Test email is automatically converted to lowercase."""
        data = {
            "email": "TEST@EXAMPLE.COM",
            "password": "SecurePass123"
        }
        request = LoginRequest(**data)

        assert request.email == "test@example.com"

    def test_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        with pytest.raises(ValidationError):
            LoginRequest(email="test@example.com")

        with pytest.raises(ValidationError):
            LoginRequest(password="SecurePass123")


class TestRefreshTokenRequest:
    """Test RefreshTokenRequest schema validation."""

    def test_valid_refresh_token_request(self):
        """Test valid refresh token request."""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        request = RefreshTokenRequest(refresh_token=token)

        assert request.refresh_token == token

    def test_missing_token(self):
        """Test validation fails when token is missing."""
        with pytest.raises(ValidationError):
            RefreshTokenRequest()


class TestLogoutRequest:
    """Test LogoutRequest schema validation."""

    def test_logout_with_token(self):
        """Test logout request with optional refresh token."""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        request = LogoutRequest(refresh_token=token)

        assert request.refresh_token == token

    def test_logout_without_token(self):
        """Test logout request without refresh token (optional)."""
        request = LogoutRequest()

        assert request.refresh_token is None


class TestForgotPasswordRequest:
    """Test ForgotPasswordRequest schema validation."""

    def test_valid_forgot_password(self):
        """Test valid forgot password request."""
        request = ForgotPasswordRequest(email="test@example.com")

        assert request.email == "test@example.com"

    def test_email_normalized_to_lowercase(self):
        """Test email is automatically converted to lowercase."""
        request = ForgotPasswordRequest(email="TEST@EXAMPLE.COM")

        assert request.email == "test@example.com"

    def test_missing_email(self):
        """Test validation fails when email is missing."""
        with pytest.raises(ValidationError):
            ForgotPasswordRequest()


class TestResetPasswordRequest:
    """Test ResetPasswordRequest schema validation."""

    def test_valid_reset_password(self):
        """Test valid password reset request."""
        data = {
            "token": "reset-token-123",
            "new_password": "NewSecure456"
        }
        request = ResetPasswordRequest(**data)

        assert request.token == "reset-token-123"
        assert request.new_password == "NewSecure456"

    def test_password_validation(self):
        """Test new password must meet security requirements."""
        # Too short
        with pytest.raises(ValidationError):
            ResetPasswordRequest(
                token="token",
                new_password="Short1"
            )

        # No uppercase
        with pytest.raises(ValidationError):
            ResetPasswordRequest(
                token="token",
                new_password="lowercase123"
            )

        # No number
        with pytest.raises(ValidationError):
            ResetPasswordRequest(
                token="token",
                new_password="NoNumbers"
            )

    def test_missing_fields(self):
        """Test validation fails when required fields are missing."""
        with pytest.raises(ValidationError):
            ResetPasswordRequest(new_password="NewSecure456")

        with pytest.raises(ValidationError):
            ResetPasswordRequest(token="token")


class TestVerifyEmailRequest:
    """Test VerifyEmailRequest schema validation."""

    def test_valid_verify_email(self):
        """Test valid email verification request."""
        request = VerifyEmailRequest(token="verify-token-123")

        assert request.token == "verify-token-123"

    def test_missing_token(self):
        """Test validation fails when token is missing."""
        with pytest.raises(ValidationError):
            VerifyEmailRequest()


class TestTenantInfo:
    """Test TenantInfo response schema."""

    def test_valid_tenant_info(self):
        """Test valid tenant info construction."""
        data = {
            "id": uuid4(),
            "name": "Acme Corp",
            "slug": "acme-corp",
            "status": "active",
            "subscription_plan": "pro",
            "credit_balance": 1000
        }
        tenant = TenantInfo(**data)

        assert tenant.name == "Acme Corp"
        assert tenant.slug == "acme-corp"
        assert tenant.status == "active"
        assert tenant.subscription_plan == "pro"
        assert tenant.credit_balance == 1000

    def test_optional_subscription_plan(self):
        """Test tenant info with null subscription plan."""
        data = {
            "id": uuid4(),
            "name": "Acme Corp",
            "slug": "acme-corp",
            "status": "active",
            "subscription_plan": None,
            "credit_balance": 0
        }
        tenant = TenantInfo(**data)

        assert tenant.subscription_plan is None


class TestUserInfo:
    """Test UserInfo response schema."""

    def test_valid_user_info(self):
        """Test valid user info construction."""
        now = datetime.utcnow()
        data = {
            "id": uuid4(),
            "email": "user@example.com",
            "full_name": "John Doe",
            "is_active": True,
            "is_verified": True,
            "locale": "en",
            "role_id": uuid4(),
            "tenant_id": uuid4(),
            "created_at": now,
            "last_login": now
        }
        user = UserInfo(**data)

        assert user.email == "user@example.com"
        assert user.full_name == "John Doe"
        assert user.is_active is True
        assert user.is_verified is True
        assert user.locale == "en"

    def test_optional_fields(self):
        """Test user info with optional fields as None."""
        data = {
            "id": uuid4(),
            "email": "user@example.com",
            "full_name": None,
            "is_active": True,
            "is_verified": False,
            "locale": "en",
            "role_id": uuid4(),
            "tenant_id": uuid4(),
            "created_at": datetime.utcnow(),
            "last_login": None
        }
        user = UserInfo(**data)

        assert user.full_name is None
        assert user.last_login is None


class TestTokenResponse:
    """Test TokenResponse schema."""

    def test_valid_token_response(self):
        """Test valid token response construction."""
        data = {
            "access_token": "access-token-123",
            "refresh_token": "refresh-token-456"
        }
        response = TokenResponse(**data)

        assert response.access_token == "access-token-123"
        assert response.refresh_token == "refresh-token-456"
        assert response.token_type == "bearer"


class TestAuthResponse:
    """Test AuthResponse schema."""

    def test_valid_auth_response(self):
        """Test valid authentication response construction."""
        user_data = {
            "id": uuid4(),
            "email": "user@example.com",
            "full_name": "John Doe",
            "is_active": True,
            "is_verified": False,
            "locale": "en",
            "role_id": uuid4(),
            "tenant_id": uuid4(),
            "created_at": datetime.utcnow(),
            "last_login": None
        }
        tenant_data = {
            "id": uuid4(),
            "name": "Acme Corp",
            "slug": "acme-corp",
            "status": "active",
            "subscription_plan": "free",
            "credit_balance": 100
        }

        response = AuthResponse(
            user=UserInfo(**user_data),
            tenant=TenantInfo(**tenant_data),
            access_token="access-token",
            refresh_token="refresh-token"
        )

        assert response.user.email == "user@example.com"
        assert response.tenant.name == "Acme Corp"
        assert response.access_token == "access-token"
        assert response.refresh_token == "refresh-token"
        assert response.token_type == "bearer"


class TestMessageResponse:
    """Test MessageResponse schema."""

    def test_valid_message_response(self):
        """Test valid message response construction."""
        response = MessageResponse(message="Operation successful")

        assert response.message == "Operation successful"


class TestUserProfileResponse:
    """Test UserProfileResponse schema."""

    def test_valid_profile_response(self):
        """Test valid user profile response construction."""
        user_data = {
            "id": uuid4(),
            "email": "user@example.com",
            "full_name": "John Doe",
            "is_active": True,
            "is_verified": True,
            "locale": "en",
            "role_id": uuid4(),
            "tenant_id": uuid4(),
            "created_at": datetime.utcnow(),
            "last_login": datetime.utcnow()
        }
        tenant_data = {
            "id": uuid4(),
            "name": "Acme Corp",
            "slug": "acme-corp",
            "status": "active",
            "subscription_plan": "pro",
            "credit_balance": 1000
        }
        permissions = {"documents:create", "documents:read", "schemas:read"}

        response = UserProfileResponse(
            user=UserInfo(**user_data),
            tenant=TenantInfo(**tenant_data),
            permissions=permissions
        )

        assert response.user.email == "user@example.com"
        assert response.tenant.name == "Acme Corp"
        assert "documents:create" in response.permissions
        assert len(response.permissions) == 3
