"""Integration tests for rate limiting on authentication endpoints.

Test Coverage:
- POST /api/v1/auth/accept-invitation - 5 requests per minute
- POST /api/v1/auth/login - 10 requests per minute
- POST /api/v1/auth/forgot-password - 3 requests per minute
- POST /api/v1/auth/reset-password - 5 requests per minute

NOTE: These tests are skipped when RATE_LIMIT_ENABLED=false (default in test environment).
To run these tests, set RATE_LIMIT_ENABLED=true before running pytest.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, Tenant
from app.services.auth_service import auth_service


# Skip all tests in this module when rate limiting is disabled
pytestmark = pytest.mark.skipif(
    not settings.rate_limit_enabled,
    reason="Rate limiting is disabled (RATE_LIMIT_ENABLED=false)"
)


# Note: rate limiter is reset automatically via conftest.py fixture


class TestAcceptInvitationRateLimit:
    """Test rate limiting on /api/v1/auth/accept-invitation endpoint."""

    def test_accept_invitation_rate_limit_exceeded(
        self,
        client: TestClient,
        test_user: User,
        db_session: Session
    ):
        """Test that 6th request within a minute returns 429 Too Many Requests."""
        # Rate limit is 5/minute for accept-invitation

        # Make 6 rapid requests (all will fail with invalid token, but rate limit applies)
        for i in range(5):
            response = client.post(
                "/api/v1/auth/accept-invitation",
                json={
                    "token": f"invalid-token-{i}",
                    "password": "SecurePass123"
                }
            )
            # First 5 should get 400 (invalid token), not 429
            assert response.status_code == 400, f"Request {i+1} should return 400, got {response.status_code}"

        # 6th request should be rate limited
        response = client.post(
            "/api/v1/auth/accept-invitation",
            json={
                "token": "invalid-token-6",
                "password": "SecurePass123"
            }
        )

        assert response.status_code == 429, f"6th request should return 429 Too Many Requests, got {response.status_code}"

    def test_accept_invitation_within_rate_limit(
        self,
        client: TestClient,
        db_session: Session
    ):
        """Test that requests within rate limit are processed normally."""
        # Make 3 requests (well within 5/minute limit)
        for i in range(3):
            response = client.post(
                "/api/v1/auth/accept-invitation",
                json={
                    "token": f"invalid-token-{i}",
                    "password": "SecurePass123"
                }
            )
            # Should get 400 (invalid token), not 429 (rate limited)
            assert response.status_code == 400, f"Request {i+1} should return 400, got {response.status_code}"


class TestLoginRateLimit:
    """Test rate limiting on /api/v1/auth/login endpoint."""

    def test_login_rate_limit_exceeded(
        self,
        client: TestClient,
        db_session: Session
    ):
        """Test that 11th login request within a minute returns 429."""
        # Rate limit is 10/minute for login

        # Make 10 rapid requests (all will fail with invalid credentials)
        for i in range(10):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": f"nonexistent{i}@example.com",
                    "password": "SomePassword123"
                }
            )
            # First 10 should get 401 (invalid credentials), not 429
            assert response.status_code == 401, f"Request {i+1} should return 401, got {response.status_code}"

        # 11th request should be rate limited
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent11@example.com",
                "password": "SomePassword123"
            }
        )

        assert response.status_code == 429, f"11th request should return 429 Too Many Requests, got {response.status_code}"


class TestForgotPasswordRateLimit:
    """Test rate limiting on /api/v1/auth/forgot-password endpoint."""

    def test_forgot_password_rate_limit_exceeded(
        self,
        client: TestClient,
        db_session: Session
    ):
        """Test that 4th forgot-password request within a minute returns 429."""
        # Rate limit is 3/minute for forgot-password

        # Make 3 rapid requests
        for i in range(3):
            response = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": f"test{i}@example.com"}
            )
            # Should get 200 (generic response to prevent email enumeration), not 429
            assert response.status_code == 200, f"Request {i+1} should return 200, got {response.status_code}"

        # 4th request should be rate limited
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "test4@example.com"}
        )

        assert response.status_code == 429, f"4th request should return 429 Too Many Requests, got {response.status_code}"


class TestResetPasswordRateLimit:
    """Test rate limiting on /api/v1/auth/reset-password endpoint."""

    def test_reset_password_rate_limit_exceeded(
        self,
        client: TestClient,
        db_session: Session
    ):
        """Test that 6th reset-password request within a minute returns 429."""
        # Rate limit is 5/minute for reset-password

        # Make 5 rapid requests (all will fail with invalid token)
        for i in range(5):
            response = client.post(
                "/api/v1/auth/reset-password",
                json={
                    "token": f"invalid-token-{i}",
                    "new_password": "NewSecurePass123"
                }
            )
            # First 5 should get 400 (invalid token), not 429
            assert response.status_code == 400, f"Request {i+1} should return 400, got {response.status_code}"

        # 6th request should be rate limited
        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "invalid-token-6",
                "new_password": "NewSecurePass123"
            }
        )

        assert response.status_code == 429, f"6th request should return 429 Too Many Requests, got {response.status_code}"
