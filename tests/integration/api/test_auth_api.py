"""Integration tests for authentication API endpoints.

Test Coverage:
- POST /api/v1/auth/register (with and without tenant)
- POST /api/v1/auth/login (success, failure, inactive user)
- POST /api/v1/auth/refresh (valid, invalid, expired tokens)
- POST /api/v1/auth/logout
- POST /api/v1/auth/forgot-password
- POST /api/v1/auth/reset-password
- POST /api/v1/auth/verify-email
- POST /api/v1/auth/accept-invitation
- GET /api/v1/auth/me
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, Tenant
from app.services.auth_service import auth_service


class TestRegisterEndpoint:
    """Test /api/v1/auth/register endpoint."""

    def test_register_with_new_tenant(
        self,
        client: TestClient,
        db_session: Session,
        seed_roles
    ):
        """Test successful registration with new tenant creation."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123",
                "full_name": "New User",
                "tenant_name": "New Company"
            }
        )

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "user" in data
        assert "tenant" in data
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

        # Verify user data
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["full_name"] == "New User"
        assert data["user"]["is_active"] is True
        assert data["user"]["is_verified"] is False  # Requires email verification

        # Verify tenant data
        assert data["tenant"]["name"] == "New Company"
        assert data["tenant"]["slug"] == "new-company"
        assert data["tenant"]["status"] == "active"
        assert data["tenant"]["subscription_plan"] == "free"
        assert data["tenant"]["credit_balance"] == 100

        # Verify user exists in database
        user = db_session.query(User).filter(
            User.email == "newuser@example.com"
        ).first()
        assert user is not None
        assert user.email_verification_token is not None
        assert user.refresh_token == data["refresh_token"]

    def test_register_without_tenant(
        self,
        client: TestClient,
        db_session: Session,
        seed_roles
    ):
        """Test registration without tenant (uses default tenant)."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "user2@example.com",
                "password": "SecurePass123"
            }
        )

        assert response.status_code == 201
        data = response.json()

        # Should use default tenant
        assert data["tenant"]["slug"] == "default"

    def test_register_duplicate_email(
        self,
        client: TestClient,
        test_user: User,
        seed_roles
    ):
        """Test registration with already registered email fails."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,  # Already exists
                "password": "SecurePass123",
                "tenant_name": "Another Company"
            }
        )

        assert response.status_code == 409
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client: TestClient, seed_roles):
        """Test registration with invalid email format."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123"
            }
        )

        assert response.status_code == 422  # Validation error

    def test_register_weak_password(self, client: TestClient, seed_roles):
        """Test registration with weak password fails validation."""
        weak_passwords = [
            "short",  # Too short
            "nouppercase123",  # No uppercase
            "NoNumbers",  # No numbers
        ]

        for password in weak_passwords:
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": "test@example.com",
                    "password": password
                }
            )
            assert response.status_code == 422

    def test_register_slug_collision_handled(
        self,
        client: TestClient,
        db_session: Session,
        seed_roles
    ):
        """Test slug collision is handled with numeric suffix."""
        # Create first tenant
        response1 = client.post(
            "/api/v1/auth/register",
            json={
                "email": "user1@example.com",
                "password": "SecurePass123",
                "tenant_name": "Acme Corp"
            }
        )
        assert response1.status_code == 201
        assert response1.json()["tenant"]["slug"] == "acme-corp"

        # Create second tenant with same name
        response2 = client.post(
            "/api/v1/auth/register",
            json={
                "email": "user2@example.com",
                "password": "SecurePass123",
                "tenant_name": "Acme Corp"
            }
        )
        assert response2.status_code == 201
        assert response2.json()["tenant"]["slug"] == "acme-corp-1"


class TestLoginEndpoint:
    """Test /api/v1/auth/login endpoint."""

    def test_login_success(
        self,
        client: TestClient,
        test_user: User,
        test_tenant: Tenant,
        db_session: Session
    ):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPass123"  # From fixture
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "user" in data
        assert "tenant" in data
        assert "access_token" in data
        assert "refresh_token" in data

        # Verify user data
        assert data["user"]["email"] == test_user.email
        assert data["tenant"]["name"] == test_tenant.name

        # Verify last_login was updated
        db_session.refresh(test_user)
        assert test_user.last_login is not None

        # Verify refresh token was stored
        assert test_user.refresh_token == data["refresh_token"]

    def test_login_wrong_password(self, client: TestClient, test_user: User):
        """Test login with wrong password fails."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123"
            }
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_email(self, client: TestClient):
        """Test login with non-existent email fails."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123"
            }
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_inactive_user(
        self,
        client: TestClient,
        test_user: User,
        db_session: Session
    ):
        """Test login with inactive user fails."""
        # Deactivate user
        test_user.is_active = False
        db_session.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPass123"
            }
        )

        assert response.status_code == 401
        assert "inactive" in response.json()["detail"].lower()

    def test_login_case_insensitive_email(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test login works with different email case."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email.upper(),  # UPPERCASE email
                "password": "TestPass123"
            }
        )

        assert response.status_code == 200


class TestRefreshTokenEndpoint:
    """Test /api/v1/auth/refresh endpoint."""

    def test_refresh_token_success(
        self,
        client: TestClient,
        test_user: User,
        db_session: Session
    ):
        """Test successful token refresh."""
        # Generate and store refresh token
        refresh_token = auth_service.create_refresh_token(
            user_id=str(test_user.id)
        )
        test_user.refresh_token = refresh_token
        db_session.commit()

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

        # Verify new refresh token was stored
        db_session.refresh(test_user)
        assert test_user.refresh_token == data["refresh_token"]
        assert test_user.refresh_token != refresh_token  # Should be new token

    def test_refresh_token_invalid(self, client: TestClient):
        """Test refresh with invalid token fails."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token"}
        )

        assert response.status_code == 401

    def test_refresh_token_revoked(
        self,
        client: TestClient,
        test_user: User,
        db_session: Session
    ):
        """Test refresh with revoked token fails."""
        # Generate refresh token
        refresh_token = auth_service.create_refresh_token(
            user_id=str(test_user.id)
        )

        # Store different token (simulate revocation)
        test_user.refresh_token = "different-token"
        db_session.commit()

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 401
        assert "revoked" in response.json()["detail"].lower()

    def test_refresh_token_wrong_type(
        self,
        client: TestClient,
        test_user: User,
        test_tenant: Tenant
    ):
        """Test using access token instead of refresh token fails."""
        # Use access token instead of refresh token
        access_token = auth_service.create_access_token(
            user_id=str(test_user.id),
            tenant_id=str(test_tenant.id)
        )

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token}
        )

        assert response.status_code == 401


class TestLogoutEndpoint:
    """Test /api/v1/auth/logout endpoint."""

    def test_logout_success(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict,
        db_session: Session
    ):
        """Test successful logout."""
        # Set refresh token
        test_user.refresh_token = "some-refresh-token"
        db_session.commit()

        response = client.post(
            "/api/v1/auth/logout",
            headers=auth_headers,
            json={}
        )

        assert response.status_code == 200
        assert "logged out" in response.json()["message"].lower()

        # Verify refresh token was cleared
        db_session.refresh(test_user)
        assert test_user.refresh_token is None

    def test_logout_without_auth(self, client: TestClient):
        """Test logout without authentication fails."""
        response = client.post(
            "/api/v1/auth/logout",
            json={}
        )

        assert response.status_code == 401


class TestForgotPasswordEndpoint:
    """Test /api/v1/auth/forgot-password endpoint."""

    def test_forgot_password_existing_user(
        self,
        client: TestClient,
        test_user: User,
        db_session: Session
    ):
        """Test password reset request for existing user."""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": test_user.email}
        )

        assert response.status_code == 200
        assert "reset link" in response.json()["message"].lower()

        # Verify reset token was generated
        db_session.refresh(test_user)
        assert test_user.password_reset_token is not None
        assert test_user.password_reset_expires is not None

    def test_forgot_password_nonexistent_user(self, client: TestClient):
        """Test password reset for non-existent user (security: same response)."""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"}
        )

        # Should return success to prevent email enumeration
        assert response.status_code == 200
        assert "reset link" in response.json()["message"].lower()


class TestResetPasswordEndpoint:
    """Test /api/v1/auth/reset-password endpoint."""

    def test_reset_password_success(
        self,
        client: TestClient,
        test_user: User,
        db_session: Session
    ):
        """Test successful password reset."""
        # Generate reset token
        reset_token = auth_service.generate_reset_token()
        test_user.password_reset_token = reset_token
        test_user.password_reset_expires = auth_service.get_password_reset_expires()
        test_user.refresh_token = "old-refresh-token"
        db_session.commit()

        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "NewSecurePass456"
            }
        )

        assert response.status_code == 200
        assert "reset successfully" in response.json()["message"].lower()

        # Verify password was changed
        db_session.refresh(test_user)
        assert auth_service.verify_password(
            "NewSecurePass456",
            test_user.hashed_password
        )

        # Verify reset token was cleared
        assert test_user.password_reset_token is None
        assert test_user.password_reset_expires is None

        # Verify refresh tokens were invalidated
        assert test_user.refresh_token is None

    def test_reset_password_invalid_token(self, client: TestClient):
        """Test password reset with invalid token."""
        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "invalid-token",
                "new_password": "NewSecurePass456"
            }
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_reset_password_expired_token(
        self,
        client: TestClient,
        test_user: User,
        db_session: Session
    ):
        """Test password reset with expired token."""
        # Generate expired token
        reset_token = auth_service.generate_reset_token()
        test_user.password_reset_token = reset_token
        test_user.password_reset_expires = datetime.utcnow() - timedelta(hours=1)
        db_session.commit()

        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "NewSecurePass456"
            }
        )

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    def test_reset_password_weak_password(
        self,
        client: TestClient,
        test_user: User,
        db_session: Session
    ):
        """Test password reset with weak password fails validation."""
        reset_token = auth_service.generate_reset_token()
        test_user.password_reset_token = reset_token
        test_user.password_reset_expires = auth_service.get_password_reset_expires()
        db_session.commit()

        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "weak"  # Too weak
            }
        )

        assert response.status_code == 422


class TestVerifyEmailEndpoint:
    """Test /api/v1/auth/verify-email endpoint."""

    def test_verify_email_success(
        self,
        client: TestClient,
        test_user: User,
        db_session: Session
    ):
        """Test successful email verification."""
        # Set user as unverified with token
        verification_token = auth_service.generate_verification_token()
        test_user.is_verified = False
        test_user.email_verification_token = verification_token
        db_session.commit()

        response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": verification_token}
        )

        assert response.status_code == 200
        assert "verified successfully" in response.json()["message"].lower()

        # Verify user is now verified
        db_session.refresh(test_user)
        assert test_user.is_verified is True
        assert test_user.email_verification_token is None

    def test_verify_email_invalid_token(self, client: TestClient):
        """Test email verification with invalid token."""
        response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": "invalid-token"}
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_verify_email_already_verified(
        self,
        client: TestClient,
        test_user: User,
        db_session: Session
    ):
        """Test verifying already verified email."""
        # Set user as verified but keep token
        verification_token = auth_service.generate_verification_token()
        test_user.is_verified = True
        test_user.email_verification_token = verification_token
        db_session.commit()

        response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": verification_token}
        )

        assert response.status_code == 200
        assert "already verified" in response.json()["message"].lower()


class TestAcceptInvitationEndpoint:
    """Test /api/v1/auth/accept-invitation endpoint."""

    def test_accept_invitation_success(
        self,
        client: TestClient,
        test_user: User,
        test_tenant: Tenant,
        db_session: Session
    ):
        """Test successful invitation acceptance."""
        # Set user as invited (inactive with token)
        invitation_token = auth_service.generate_verification_token()
        test_user.is_active = False
        test_user.is_verified = False
        test_user.email_verification_token = invitation_token
        # Use placeholder password (will be replaced when accepting invitation)
        test_user.hashed_password = auth_service.hash_password("placeholder")
        test_user.full_name = None  # No name set yet
        db_session.commit()

        response = client.post(
            "/api/v1/auth/accept-invitation",
            json={
                "token": invitation_token,
                "password": "SecurePass123",
                "full_name": "Invited User"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure (same as login)
        assert "user" in data
        assert "tenant" in data
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

        # Verify user is now active and verified
        assert data["user"]["is_active"] is True
        assert data["user"]["is_verified"] is True
        assert data["user"]["full_name"] == "Invited User"

        # Verify database was updated
        db_session.refresh(test_user)
        assert test_user.is_active is True
        assert test_user.is_verified is True
        assert test_user.email_verification_token is None  # Token cleared
        assert test_user.full_name == "Invited User"
        assert test_user.last_login is not None
        assert auth_service.verify_password("SecurePass123", test_user.hashed_password)
        assert test_user.refresh_token == data["refresh_token"]

    def test_accept_invitation_without_full_name(
        self,
        client: TestClient,
        test_user: User,
        db_session: Session
    ):
        """Test invitation acceptance without providing full_name."""
        invitation_token = auth_service.generate_verification_token()
        test_user.is_active = False
        test_user.is_verified = False
        test_user.email_verification_token = invitation_token
        test_user.full_name = "Existing Name"  # Already has a name
        db_session.commit()

        response = client.post(
            "/api/v1/auth/accept-invitation",
            json={
                "token": invitation_token,
                "password": "SecurePass123"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify existing name is preserved
        assert data["user"]["full_name"] == "Existing Name"

    def test_accept_invitation_preserves_existing_name(
        self,
        client: TestClient,
        test_user: User,
        db_session: Session
    ):
        """Test invitation acceptance preserves existing full_name even if new one provided."""
        invitation_token = auth_service.generate_verification_token()
        test_user.is_active = False
        test_user.is_verified = False
        test_user.email_verification_token = invitation_token
        test_user.full_name = "Existing Name"  # Already has a name
        db_session.commit()

        response = client.post(
            "/api/v1/auth/accept-invitation",
            json={
                "token": invitation_token,
                "password": "SecurePass123",
                "full_name": "New Name"  # Tries to set new name
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify existing name is preserved (not overwritten)
        assert data["user"]["full_name"] == "Existing Name"

    def test_accept_invitation_invalid_token(self, client: TestClient):
        """Test invitation acceptance with invalid token."""
        response = client.post(
            "/api/v1/auth/accept-invitation",
            json={
                "token": "invalid-token",
                "password": "SecurePass123"
            }
        )

        assert response.status_code == 400
        assert "invalid invitation token" in response.json()["detail"].lower()

    def test_accept_invitation_already_accepted(
        self,
        client: TestClient,
        test_user: User,
        db_session: Session
    ):
        """Test invitation acceptance when already active (double accept)."""
        # User is active (already accepted invitation)
        invitation_token = auth_service.generate_verification_token()
        test_user.is_active = True
        test_user.is_verified = True
        test_user.email_verification_token = invitation_token
        db_session.commit()

        response = client.post(
            "/api/v1/auth/accept-invitation",
            json={
                "token": invitation_token,
                "password": "SecurePass123"
            }
        )

        assert response.status_code == 400
        assert "already accepted" in response.json()["detail"].lower()

    def test_accept_invitation_weak_password(
        self,
        client: TestClient,
        test_user: User,
        db_session: Session
    ):
        """Test invitation acceptance with weak password fails validation."""
        invitation_token = auth_service.generate_verification_token()
        test_user.is_active = False
        test_user.is_verified = False
        test_user.email_verification_token = invitation_token
        db_session.commit()

        response = client.post(
            "/api/v1/auth/accept-invitation",
            json={
                "token": invitation_token,
                "password": "weak"  # Too weak
            }
        )

        assert response.status_code == 422

    def test_accept_invitation_expired_token(
        self,
        client: TestClient,
        test_user: User,
        db_session: Session
    ):
        """Test invitation acceptance with expired token fails."""
        # Set user as invited (inactive with token) but with expired invitation
        invitation_token = auth_service.generate_verification_token()
        test_user.is_active = False
        test_user.is_verified = False
        test_user.email_verification_token = invitation_token
        # Set invitation_expires to past date (expired 1 hour ago)
        test_user.invitation_expires = datetime.utcnow() - timedelta(hours=1)
        db_session.commit()

        response = client.post(
            "/api/v1/auth/accept-invitation",
            json={
                "token": invitation_token,
                "password": "SecurePass123"
            }
        )

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

        # Verify that the token was cleared after expiration check
        db_session.refresh(test_user)
        assert test_user.email_verification_token is None
        assert test_user.invitation_expires is None
        # User should still be inactive (invitation not accepted)
        assert test_user.is_active is False
        assert test_user.is_verified is False


class TestGetCurrentUserProfileEndpoint:
    """Test GET /api/v1/auth/me endpoint."""

    def test_get_profile_success(
        self,
        client: TestClient,
        test_user: User,
        test_tenant: Tenant,
        auth_headers: dict,
        seed_role_permissions
    ):
        """Test getting current user profile."""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "user" in data
        assert "tenant" in data
        assert "permissions" in data

        # Verify user data
        assert data["user"]["email"] == test_user.email
        assert data["user"]["full_name"] == test_user.full_name

        # Verify tenant data
        assert data["tenant"]["name"] == test_tenant.name

        # Verify permissions (member role should have these)
        expected_permissions = {
            "documents:create",
            "documents:read",
            "schemas:create",
            "schemas:read"
        }
        assert set(data["permissions"]) == expected_permissions

    def test_get_profile_without_auth(self, client: TestClient):
        """Test getting profile without authentication fails."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_get_profile_invalid_token(self, client: TestClient):
        """Test getting profile with invalid token fails."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code == 401
