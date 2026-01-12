"""Integration tests for Platform API endpoints.

Test Coverage:
- POST /platform/v1/tenants (create tenant)
- GET /platform/v1/tenants/{id} (get tenant)
- PATCH /platform/v1/tenants/{id} (update tenant)
- DELETE /platform/v1/tenants/{id} (deactivate tenant)
- POST /platform/v1/tenants/{id}/users (create user in tenant)
- GET /platform/v1/tenants/{id}/users (list tenant users)
- GET /platform/v1/users/{id} (get user)
- PATCH /platform/v1/users/{id} (update user)
- POST /platform/v1/users/{id}/tokens (create API token for user)
- GET /platform/v1/users/{id}/tokens (list user tokens)
- DELETE /platform/v1/tokens/{id} (revoke token)
- POST /platform/v1/tenants/{id}/credits (add credits)
- GET /platform/v1/tenants/{id}/credits (get credit balance)
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Tenant, User, Role
from app.models.platform_application import PlatformApplication
from app.models.platform_api_key import PlatformApiKey
from app.models.api_token import ApiToken
from app.models.enums import PlatformScope


class TestPlatformAuthenticationAndAuthorization:
    """Test Platform API authentication and authorization."""

    def test_request_without_authentication_fails(
        self,
        client: TestClient,
    ):
        """Test that requests without authentication fail."""
        response = client.post(
            "/platform/v1/tenants",
            json={"name": "Test Tenant"}
        )

        assert response.status_code == 401

    def test_request_with_invalid_token_fails(
        self,
        client: TestClient,
    ):
        """Test that requests with invalid token fail."""
        response = client.post(
            "/platform/v1/tenants",
            headers={"Authorization": "Bearer pk_live_invalid_token_abcd"},
            json={"name": "Test Tenant"}
        )

        assert response.status_code == 401

    def test_request_with_user_token_fails(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test that requests with user token (sk_live_) fail on platform endpoints."""
        response = client.post(
            "/platform/v1/tenants",
            headers=auth_headers,
            json={"name": "Test Tenant"}
        )

        # Should fail because sk_live_ tokens don't work on platform endpoints
        assert response.status_code == 401

    def test_request_without_required_scope_fails(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
    ):
        """Test that requests without required scope fail."""
        from app.services.platform_api_key_service import PlatformApiKeyService

        # Create a key with limited scopes
        full_key, key_hash, key_prefix = PlatformApiKeyService.generate_key()
        limited_key = PlatformApiKey(
            application_id=platform_application.id,
            name="Limited Key",
            token_hash=key_hash,
            token_prefix=key_prefix,
            scopes=["tenants:read"],  # No create scope
            is_active=True,
        )
        db_session.add(limited_key)
        db_session.commit()

        response = client.post(
            "/platform/v1/tenants",
            headers={"Authorization": f"Bearer {full_key}"},
            json={"name": "Test Tenant"}
        )

        assert response.status_code == 403
        assert "scope" in response.json()["detail"].lower()


class TestCreateTenant:
    """Test POST /platform/v1/tenants endpoint."""

    def test_create_tenant_success(
        self,
        client: TestClient,
        platform_auth_headers: dict,
    ):
        """Test successful tenant creation."""
        response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={
                "name": "New Tenant",
                "initial_credits": 1000,
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "New Tenant"
        assert data["credit_balance"] == 1000
        assert data["status"] == "active"
        assert "id" in data
        assert "slug" in data
        assert "created_at" in data

    def test_create_tenant_with_slug(
        self,
        client: TestClient,
        platform_auth_headers: dict,
    ):
        """Test tenant creation with custom slug."""
        response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={
                "name": "Custom Slug Tenant",
                "slug": "custom-tenant-slug",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "custom-tenant-slug"

    def test_create_tenant_with_plan(
        self,
        client: TestClient,
        platform_auth_headers: dict,
    ):
        """Test tenant creation with subscription plan."""
        response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={
                "name": "Pro Tenant",
                "subscription_plan": "pro",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["subscription_plan"] == "pro"

    def test_create_tenant_with_metadata(
        self,
        client: TestClient,
        platform_auth_headers: dict,
    ):
        """Test tenant creation with metadata."""
        response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={
                "name": "Metadata Tenant",
                "metadata": {"external_id": "ext-123", "region": "us-west-2"},
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["metadata"] == {"external_id": "ext-123", "region": "us-west-2"}

    def test_create_tenant_duplicate_slug(
        self,
        client: TestClient,
        platform_auth_headers: dict,
    ):
        """Test tenant creation with duplicate slug fails."""
        # Create first tenant
        client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "First", "slug": "duplicate-tenant-slug"}
        )

        # Try to create second with same slug
        response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Second", "slug": "duplicate-tenant-slug"}
        )

        # Returns 409 Conflict for duplicate slug
        assert response.status_code == 409


class TestGetTenant:
    """Test GET /platform/v1/tenants/{id} endpoint."""

    def test_get_tenant_success(
        self,
        client: TestClient,
        platform_auth_headers: dict,
    ):
        """Test successful tenant retrieval."""
        # Create a tenant first
        create_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Get Test Tenant"}
        )
        tenant_id = create_response.json()["id"]

        response = client.get(
            f"/platform/v1/tenants/{tenant_id}",
            headers=platform_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tenant_id
        assert data["name"] == "Get Test Tenant"

    def test_get_tenant_not_found(
        self,
        client: TestClient,
        platform_auth_headers: dict,
    ):
        """Test getting non-existent tenant."""
        response = client.get(
            f"/platform/v1/tenants/{uuid4()}",
            headers=platform_auth_headers,
        )

        assert response.status_code == 404


class TestUpdateTenant:
    """Test PATCH /platform/v1/tenants/{id} endpoint."""

    def test_update_tenant_success(
        self,
        client: TestClient,
        platform_auth_headers: dict,
    ):
        """Test successful tenant update."""
        # Create a tenant first
        create_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Update Test Tenant"}
        )
        tenant_id = create_response.json()["id"]

        response = client.patch(
            f"/platform/v1/tenants/{tenant_id}",
            headers=platform_auth_headers,
            json={
                "name": "Updated Tenant Name",
                "subscription_plan": "enterprise",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Tenant Name"
        assert data["subscription_plan"] == "enterprise"

    def test_update_tenant_status(
        self,
        client: TestClient,
        platform_auth_headers: dict,
    ):
        """Test updating tenant status."""
        # Create a tenant first
        create_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Status Test Tenant"}
        )
        tenant_id = create_response.json()["id"]

        response = client.patch(
            f"/platform/v1/tenants/{tenant_id}",
            headers=platform_auth_headers,
            json={"status": "suspended"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "suspended"


class TestDeleteTenant:
    """Test DELETE /platform/v1/tenants/{id} endpoint."""

    def test_deactivate_tenant_success(
        self,
        client: TestClient,
        platform_auth_headers: dict,
    ):
        """Test successful tenant deactivation."""
        # Create a tenant first
        create_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Delete Test Tenant"}
        )
        tenant_id = create_response.json()["id"]

        response = client.delete(
            f"/platform/v1/tenants/{tenant_id}",
            headers=platform_auth_headers,
        )

        assert response.status_code == 204

        # Verify deactivation - API uses 'cancelled' status
        get_response = client.get(
            f"/platform/v1/tenants/{tenant_id}",
            headers=platform_auth_headers,
        )
        assert get_response.json()["status"] == "cancelled"


class TestCreateUserInTenant:
    """Test POST /platform/v1/tenants/{id}/users endpoint."""

    def test_create_user_success(
        self,
        client: TestClient,
        db_session: Session,
        platform_auth_headers: dict,
        seed_roles: dict,
    ):
        """Test successful user creation in tenant with password (no invitation)."""
        # Create a tenant first
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "User Test Tenant"}
        )
        tenant_id = create_tenant_response.json()["id"]

        response = client.post(
            f"/platform/v1/tenants/{tenant_id}/users",
            headers=platform_auth_headers,
            json={
                "email": "newuser@example.com",
                "full_name": "New User",
                "role": "admin",
                "send_invitation": False,
                "password": "SecurePass123!",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert data["role_name"] == "admin"
        assert data["is_active"] is True

    def test_create_user_with_invitation(
        self,
        client: TestClient,
        db_session: Session,
        platform_auth_headers: dict,
        seed_roles: dict,
    ):
        """Test user creation with invitation flag."""
        # Create a tenant first
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Invite Test Tenant"}
        )
        tenant_id = create_tenant_response.json()["id"]

        response = client.post(
            f"/platform/v1/tenants/{tenant_id}/users",
            headers=platform_auth_headers,
            json={
                "email": "invited@example.com",
                "role": "member",
                "send_invitation": True,
            }
        )

        assert response.status_code == 201
        data = response.json()
        # User is created but not verified until invitation is accepted
        assert data["is_verified"] is False

    def test_create_user_duplicate_email(
        self,
        client: TestClient,
        platform_auth_headers: dict,
        seed_roles: dict,
    ):
        """Test user creation with duplicate email fails."""
        # Create a tenant first
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Duplicate Test Tenant"}
        )
        tenant_id = create_tenant_response.json()["id"]

        # Create first user
        client.post(
            f"/platform/v1/tenants/{tenant_id}/users",
            headers=platform_auth_headers,
            json={"email": "duplicate@example.com", "role": "member"}
        )

        # Try to create second with same email
        response = client.post(
            f"/platform/v1/tenants/{tenant_id}/users",
            headers=platform_auth_headers,
            json={"email": "duplicate@example.com", "role": "member"}
        )

        # Returns 409 Conflict for duplicate email
        assert response.status_code == 409


class TestListTenantUsers:
    """Test GET /platform/v1/tenants/{id}/users endpoint."""

    def test_list_tenant_users_success(
        self,
        client: TestClient,
        platform_auth_headers: dict,
        seed_roles: dict,
    ):
        """Test successful user listing."""
        # Create tenant with users
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "List Users Tenant"}
        )
        tenant_id = create_tenant_response.json()["id"]

        # Create some users
        for i in range(3):
            client.post(
                f"/platform/v1/tenants/{tenant_id}/users",
                headers=platform_auth_headers,
                json={"email": f"listuser{i}@example.com", "role": "member"}
            )

        response = client.get(
            f"/platform/v1/tenants/{tenant_id}/users",
            headers=platform_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert data["total"] >= 3


class TestGetUser:
    """Test GET /platform/v1/users/{id} endpoint."""

    def test_get_user_success(
        self,
        client: TestClient,
        platform_auth_headers: dict,
        seed_roles: dict,
    ):
        """Test successful user retrieval."""
        # Create tenant and user
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Get User Tenant"}
        )
        tenant_id = create_tenant_response.json()["id"]

        create_user_response = client.post(
            f"/platform/v1/tenants/{tenant_id}/users",
            headers=platform_auth_headers,
            json={"email": "getuser@example.com", "role": "admin"}
        )
        user_id = create_user_response.json()["id"]

        response = client.get(
            f"/platform/v1/users/{user_id}",
            headers=platform_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["email"] == "getuser@example.com"


class TestUpdateUser:
    """Test PATCH /platform/v1/users/{id} endpoint."""

    def test_update_user_success(
        self,
        client: TestClient,
        platform_auth_headers: dict,
        seed_roles: dict,
    ):
        """Test successful user update."""
        # Create tenant and user
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Update User Tenant"}
        )
        tenant_id = create_tenant_response.json()["id"]

        create_user_response = client.post(
            f"/platform/v1/tenants/{tenant_id}/users",
            headers=platform_auth_headers,
            json={"email": "updateuser@example.com", "role": "member"}
        )
        user_id = create_user_response.json()["id"]

        response = client.patch(
            f"/platform/v1/users/{user_id}",
            headers=platform_auth_headers,
            json={
                "full_name": "Updated Name",
                "role": "admin",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["role_name"] == "admin"


class TestCreateUserToken:
    """Test POST /platform/v1/users/{id}/tokens endpoint."""

    def test_create_token_success(
        self,
        client: TestClient,
        platform_auth_headers: dict,
        seed_roles: dict,
        seed_role_permissions: None,  # Need to ensure permissions are assigned to roles
    ):
        """Test successful API token creation for user."""
        # Create tenant and user (with password, not invitation)
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Token User Tenant"}
        )
        tenant_id = create_tenant_response.json()["id"]

        create_user_response = client.post(
            f"/platform/v1/tenants/{tenant_id}/users",
            headers=platform_auth_headers,
            json={
                "email": "tokenuser@example.com",
                "role": "admin",
                "send_invitation": False,
                "password": "SecurePass123!",
            }
        )
        user_id = create_user_response.json()["id"]

        response = client.post(
            f"/platform/v1/users/{user_id}/tokens",
            headers=platform_auth_headers,
            json={
                "name": "API Token",
                "scopes": ["documents:create", "documents:read"],
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "API Token"
        assert data["scopes"] == ["documents:create", "documents:read"]
        assert "token" in data
        assert data["token"].startswith("sk_live_")

    def test_create_token_with_expiration(
        self,
        client: TestClient,
        platform_auth_headers: dict,
        seed_roles: dict,
        seed_role_permissions: None,  # Need to ensure permissions are assigned to roles
    ):
        """Test API token creation with expiration."""
        # Create tenant and user (with password, not invitation)
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Expiring Token Tenant"}
        )
        tenant_id = create_tenant_response.json()["id"]

        create_user_response = client.post(
            f"/platform/v1/tenants/{tenant_id}/users",
            headers=platform_auth_headers,
            json={
                "email": "expiretokenuser@example.com",
                "role": "admin",
                "send_invitation": False,
                "password": "SecurePass123!",
            }
        )
        user_id = create_user_response.json()["id"]

        response = client.post(
            f"/platform/v1/users/{user_id}/tokens",
            headers=platform_auth_headers,
            json={
                "name": "Expiring Token",
                "scopes": ["documents:read"],
                "expires_in_days": 90,
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["expires_at"] is not None


class TestListUserTokens:
    """Test GET /platform/v1/users/{id}/tokens endpoint."""

    def test_list_user_tokens_success(
        self,
        client: TestClient,
        platform_auth_headers: dict,
        seed_roles: dict,
        seed_role_permissions: None,  # Need to ensure permissions are assigned to roles
    ):
        """Test successful token listing."""
        # Create tenant and user
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "List Tokens Tenant"}
        )
        tenant_id = create_tenant_response.json()["id"]

        create_user_response = client.post(
            f"/platform/v1/tenants/{tenant_id}/users",
            headers=platform_auth_headers,
            json={
                "email": "listtokensuser@example.com",
                "role": "admin",
                "send_invitation": False,
                "password": "SecurePass123!",
            }
        )
        user_id = create_user_response.json()["id"]

        # Create some tokens
        for i in range(2):
            client.post(
                f"/platform/v1/users/{user_id}/tokens",
                headers=platform_auth_headers,
                json={"name": f"Token {i}", "scopes": ["documents:read"]}
            )

        response = client.get(
            f"/platform/v1/users/{user_id}/tokens",
            headers=platform_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Response is paginated with 'tokens' list
        assert "tokens" in data
        assert len(data["tokens"]) >= 2


class TestRevokeToken:
    """Test DELETE /platform/v1/tokens/{id} endpoint."""

    def test_revoke_token_success(
        self,
        client: TestClient,
        db_session: Session,
        platform_auth_headers: dict,
        seed_roles: dict,
        seed_role_permissions: None,  # Need to ensure permissions are assigned to roles
    ):
        """Test successful token revocation."""
        # Create tenant and user (with password, not invitation)
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Revoke Token Tenant"}
        )
        tenant_id = create_tenant_response.json()["id"]

        create_user_response = client.post(
            f"/platform/v1/tenants/{tenant_id}/users",
            headers=platform_auth_headers,
            json={
                "email": "revoketokenuser@example.com",
                "role": "admin",
                "send_invitation": False,
                "password": "SecurePass123!",
            }
        )
        user_id = create_user_response.json()["id"]

        # Create a token
        create_token_response = client.post(
            f"/platform/v1/users/{user_id}/tokens",
            headers=platform_auth_headers,
            json={"name": "To Revoke", "scopes": ["documents:read"]}
        )
        assert create_token_response.status_code == 201, f"Token creation failed: {create_token_response.json()}"
        token_id = create_token_response.json()["id"]

        response = client.delete(
            f"/platform/v1/tokens/{token_id}",
            headers=platform_auth_headers,
        )

        assert response.status_code == 204

        # Verify revocation
        token = db_session.query(ApiToken).filter(
            ApiToken.id == token_id
        ).first()
        assert token.is_active is False


class TestAddCredits:
    """Test POST /platform/v1/tenants/{id}/credits endpoint."""

    def test_add_credits_success(
        self,
        client: TestClient,
        platform_auth_headers: dict,
    ):
        """Test successful credit addition."""
        # Create tenant
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Credits Test Tenant", "initial_credits": 100}
        )
        tenant_id = create_tenant_response.json()["id"]

        response = client.post(
            f"/platform/v1/tenants/{tenant_id}/credits",
            headers=platform_auth_headers,
            json={
                "amount": 500,
                "description": "API credit addition",
            }
        )

        # API returns 201 for credit transaction creation
        assert response.status_code == 201
        data = response.json()
        # Response is CreditTransactionResponse with id, amount, transaction_type, description, created_at
        assert data["amount"] == 500
        assert "transaction_type" in data
        assert "description" in data
        assert "created_at" in data

    def test_add_credits_with_reference(
        self,
        client: TestClient,
        platform_auth_headers: dict,
    ):
        """Test credit addition with reference."""
        # Create tenant
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Credits Ref Tenant"}
        )
        tenant_id = create_tenant_response.json()["id"]

        response = client.post(
            f"/platform/v1/tenants/{tenant_id}/credits",
            headers=platform_auth_headers,
            json={
                "amount": 1000,
                "description": "Payment received",
                "reference_id": "payment-123",
            }
        )

        # API returns 201 for credit transaction creation
        assert response.status_code == 201


class TestGetCredits:
    """Test GET /platform/v1/tenants/{id}/credits endpoint."""

    def test_get_credits_success(
        self,
        client: TestClient,
        platform_auth_headers: dict,
    ):
        """Test successful credit balance retrieval."""
        # Create tenant with credits
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Get Credits Tenant", "initial_credits": 750}
        )
        tenant_id = create_tenant_response.json()["id"]

        response = client.get(
            f"/platform/v1/tenants/{tenant_id}/credits",
            headers=platform_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["balance"] == 750
        assert data["tenant_id"] == tenant_id


class TestScopeEnforcement:
    """Test that scopes are properly enforced for all operations."""

    def test_tenants_create_scope_required(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
    ):
        """Test tenants:create scope is required for tenant creation."""
        from app.services.platform_api_key_service import PlatformApiKeyService

        # Create a key with read-only scope
        full_key, key_hash, key_prefix = PlatformApiKeyService.generate_key()
        read_only_key = PlatformApiKey(
            application_id=platform_application.id,
            name="Read Only Key",
            token_hash=key_hash,
            token_prefix=key_prefix,
            scopes=["tenants:read"],  # No create scope
            is_active=True,
        )
        db_session.add(read_only_key)
        db_session.commit()

        response = client.post(
            "/platform/v1/tenants",
            headers={"Authorization": f"Bearer {full_key}"},
            json={"name": "Test Tenant"}
        )

        assert response.status_code == 403

    def test_users_create_scope_required(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
        platform_auth_headers: dict,
    ):
        """Test users:create scope is required for user creation."""
        from app.services.platform_api_key_service import PlatformApiKeyService

        # Create tenant using full-scope key
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Scope Test Tenant"}
        )
        tenant_id = create_tenant_response.json()["id"]

        # Create a key without users:create scope
        full_key, key_hash, key_prefix = PlatformApiKeyService.generate_key()
        limited_key = PlatformApiKey(
            application_id=platform_application.id,
            name="Limited Key",
            token_hash=key_hash,
            token_prefix=key_prefix,
            scopes=["tenants:read", "tenants:create", "users:read"],  # No users:create
            is_active=True,
        )
        db_session.add(limited_key)
        db_session.commit()

        response = client.post(
            f"/platform/v1/tenants/{tenant_id}/users",
            headers={"Authorization": f"Bearer {full_key}"},
            json={"email": "scopetest@example.com", "role": "member"}
        )

        assert response.status_code == 403

    def test_credits_add_scope_required(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
        platform_auth_headers: dict,
    ):
        """Test credits:add scope is required for adding credits."""
        from app.services.platform_api_key_service import PlatformApiKeyService

        # Create tenant using full-scope key
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Credits Scope Test Tenant"}
        )
        tenant_id = create_tenant_response.json()["id"]

        # Create a key without credits:add scope
        full_key, key_hash, key_prefix = PlatformApiKeyService.generate_key()
        limited_key = PlatformApiKey(
            application_id=platform_application.id,
            name="No Credits Key",
            token_hash=key_hash,
            token_prefix=key_prefix,
            scopes=["tenants:read", "credits:read"],  # No credits:add
            is_active=True,
        )
        db_session.add(limited_key)
        db_session.commit()

        response = client.post(
            f"/platform/v1/tenants/{tenant_id}/credits",
            headers={"Authorization": f"Bearer {full_key}"},
            json={"amount": 100, "description": "Test"}
        )

        assert response.status_code == 403


class TestWildcardScopes:
    """Test wildcard scope support."""

    def test_resource_wildcard_scope(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
    ):
        """Test that tenants:* grants all tenant operations."""
        from app.services.platform_api_key_service import PlatformApiKeyService

        # Create a key with wildcard scope
        full_key, key_hash, key_prefix = PlatformApiKeyService.generate_key()
        wildcard_key = PlatformApiKey(
            application_id=platform_application.id,
            name="Wildcard Key",
            token_hash=key_hash,
            token_prefix=key_prefix,
            scopes=["tenants:*"],  # Wildcard for tenants
            is_active=True,
        )
        db_session.add(wildcard_key)
        db_session.commit()

        headers = {"Authorization": f"Bearer {full_key}"}

        # Should be able to create
        create_response = client.post(
            "/platform/v1/tenants",
            headers=headers,
            json={"name": "Wildcard Test Tenant"}
        )
        assert create_response.status_code == 201
        tenant_id = create_response.json()["id"]

        # Should be able to read
        read_response = client.get(
            f"/platform/v1/tenants/{tenant_id}",
            headers=headers,
        )
        assert read_response.status_code == 200

        # Should be able to update
        update_response = client.patch(
            f"/platform/v1/tenants/{tenant_id}",
            headers=headers,
            json={"name": "Updated Wildcard Tenant"}
        )
        assert update_response.status_code == 200

        # Should be able to delete
        delete_response = client.delete(
            f"/platform/v1/tenants/{tenant_id}",
            headers=headers,
        )
        assert delete_response.status_code == 204

    def test_full_wildcard_scope(
        self,
        client: TestClient,
        db_session: Session,
        platform_application: PlatformApplication,
        seed_roles: dict,
    ):
        """Test that *:* grants all operations."""
        from app.services.platform_api_key_service import PlatformApiKeyService

        # Create a key with full wildcard scope
        full_key, key_hash, key_prefix = PlatformApiKeyService.generate_key()
        super_key = PlatformApiKey(
            application_id=platform_application.id,
            name="Super Key",
            token_hash=key_hash,
            token_prefix=key_prefix,
            scopes=["*:*"],  # Full wildcard
            is_active=True,
        )
        db_session.add(super_key)
        db_session.commit()

        headers = {"Authorization": f"Bearer {full_key}"}

        # Should be able to do everything
        tenant_response = client.post(
            "/platform/v1/tenants",
            headers=headers,
            json={"name": "Super Key Tenant"}
        )
        assert tenant_response.status_code == 201
        tenant_id = tenant_response.json()["id"]

        user_response = client.post(
            f"/platform/v1/tenants/{tenant_id}/users",
            headers=headers,
            json={"email": "superkey@example.com", "role": "admin"}
        )
        assert user_response.status_code == 201

        credits_response = client.post(
            f"/platform/v1/tenants/{tenant_id}/credits",
            headers=headers,
            json={"amount": 100, "description": "Super key test"}
        )
        assert credits_response.status_code == 201


class TestPasswordNotInApiResponses:
    """Test that passwords are NEVER returned in API responses.

    This is a critical security requirement. Passwords, even temporary ones,
    must never be exposed in API responses to prevent log exposure via
    intermediate proxies, monitoring systems, or client-side logging.
    """

    def _assert_no_password_fields(self, data: dict, context: str = "") -> None:
        """Helper to verify no password-related fields exist in response data.

        Args:
            data: The response data dictionary to check
            context: Description of where this data came from (for error messages)
        """
        # Check for specific known password field names
        forbidden_fields = [
            "password",
            "temporary_password",
            "hashed_password",
            "plain_password",
            "raw_password",
            "new_password",
            "old_password",
            "current_password",
        ]

        for field in forbidden_fields:
            assert field not in data, (
                f"Found forbidden password field '{field}' in {context} response"
            )

        # Check that no field name contains "password" (case-insensitive)
        for key in data.keys():
            assert "password" not in key.lower(), (
                f"Found password-related field '{key}' in {context} response"
            )

        # Recursively check nested objects
        for key, value in data.items():
            if isinstance(value, dict):
                self._assert_no_password_fields(
                    value, f"{context}.{key}" if context else key
                )
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        self._assert_no_password_fields(
                            item, f"{context}.{key}[{i}]" if context else f"{key}[{i}]"
                        )

    def test_create_user_response_excludes_password(
        self,
        client: TestClient,
        platform_auth_headers: dict,
        seed_roles: dict,
        db_session: Session,
    ):
        """Verify password is never returned in user creation response.

        When creating a user with send_invitation=False and providing a password,
        the API must NOT echo the password back in the response.
        """
        # Create tenant first
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Password Test Tenant"}
        )
        tenant_id = create_tenant_response.json()["id"]

        # Create user with explicit password
        response = client.post(
            f"/platform/v1/tenants/{tenant_id}/users",
            headers=platform_auth_headers,
            json={
                "email": "password-test@example.com",
                "full_name": "Password Test User",
                "role": "member",
                "send_invitation": False,
                "password": "SecureTestPass123!",
            }
        )

        assert response.status_code == 201
        data = response.json()

        # Verify no password fields in response
        self._assert_no_password_fields(data, "create_user")

        # Verify expected fields ARE present
        assert "id" in data
        assert "email" in data
        assert data["email"] == "password-test@example.com"

    def test_create_user_with_invitation_excludes_password(
        self,
        client: TestClient,
        platform_auth_headers: dict,
        seed_roles: dict,
        db_session: Session,
    ):
        """Verify password is never returned when creating user with invitation.

        Even with send_invitation=True, no password-related fields should appear.
        """
        # Create tenant first
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Invitation Password Test Tenant"}
        )
        tenant_id = create_tenant_response.json()["id"]

        # Create user with invitation
        response = client.post(
            f"/platform/v1/tenants/{tenant_id}/users",
            headers=platform_auth_headers,
            json={
                "email": "invitation-test@example.com",
                "role": "member",
                "send_invitation": True,
            }
        )

        assert response.status_code == 201
        data = response.json()

        # Verify no password fields in response
        self._assert_no_password_fields(data, "create_user_invitation")

        # Verify invitation_token IS present (this is expected and safe)
        assert "invitation_token" in data

    def test_get_user_response_excludes_password(
        self,
        client: TestClient,
        platform_auth_headers: dict,
        seed_roles: dict,
        db_session: Session,
    ):
        """Verify password is never returned in get user response."""
        # Create tenant and user
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Get User Password Test Tenant"}
        )
        tenant_id = create_tenant_response.json()["id"]

        create_user_response = client.post(
            f"/platform/v1/tenants/{tenant_id}/users",
            headers=platform_auth_headers,
            json={
                "email": "get-user-test@example.com",
                "full_name": "Get User Test",
                "role": "admin",
                "send_invitation": False,
                "password": "GetUserTestPass123!",
            }
        )
        user_id = create_user_response.json()["id"]

        # Get user details
        response = client.get(
            f"/platform/v1/users/{user_id}",
            headers=platform_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify no password fields in response
        self._assert_no_password_fields(data, "get_user")

        # Verify expected fields ARE present
        assert "id" in data
        assert "email" in data
        assert data["email"] == "get-user-test@example.com"

    def test_update_user_response_excludes_password(
        self,
        client: TestClient,
        platform_auth_headers: dict,
        seed_roles: dict,
        db_session: Session,
    ):
        """Verify password is never returned in update user response."""
        # Create tenant and user
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Update User Password Test Tenant"}
        )
        tenant_id = create_tenant_response.json()["id"]

        create_user_response = client.post(
            f"/platform/v1/tenants/{tenant_id}/users",
            headers=platform_auth_headers,
            json={
                "email": "update-user-test@example.com",
                "role": "member",
                "send_invitation": False,
                "password": "UpdateUserTestPass123!",
            }
        )
        user_id = create_user_response.json()["id"]

        # Update user
        response = client.patch(
            f"/platform/v1/users/{user_id}",
            headers=platform_auth_headers,
            json={
                "full_name": "Updated Name",
                "role": "admin",
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify no password fields in response
        self._assert_no_password_fields(data, "update_user")

        # Verify update was applied
        assert data["full_name"] == "Updated Name"
        assert data["role_name"] == "admin"

    def test_list_users_response_excludes_password(
        self,
        client: TestClient,
        platform_auth_headers: dict,
        seed_roles: dict,
        db_session: Session,
    ):
        """Verify password is never returned in list users response."""
        # Create tenant
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "List Users Password Test Tenant"}
        )
        tenant_id = create_tenant_response.json()["id"]

        # Create multiple users with passwords
        for i in range(3):
            client.post(
                f"/platform/v1/tenants/{tenant_id}/users",
                headers=platform_auth_headers,
                json={
                    "email": f"list-user-{i}@example.com",
                    "full_name": f"List User {i}",
                    "role": "member",
                    "send_invitation": False,
                    "password": f"ListUserPass{i}123!",
                }
            )

        # List users
        response = client.get(
            f"/platform/v1/tenants/{tenant_id}/users",
            headers=platform_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify no password fields in top-level response
        self._assert_no_password_fields(data, "list_users")

        # Verify we got users
        assert "users" in data
        assert data["total"] >= 3

        # Double-check each user in the list
        for i, user in enumerate(data["users"]):
            self._assert_no_password_fields(user, f"list_users.users[{i}]")

    def test_create_user_response_schema_consistency(
        self,
        client: TestClient,
        platform_auth_headers: dict,
        seed_roles: dict,
        db_session: Session,
    ):
        """Verify user creation response schema is consistent and secure.

        This test documents the expected response schema and ensures
        only allowed fields are present.
        """
        # Create tenant first
        create_tenant_response = client.post(
            "/platform/v1/tenants",
            headers=platform_auth_headers,
            json={"name": "Schema Consistency Test Tenant"}
        )
        tenant_id = create_tenant_response.json()["id"]

        # Create user with password
        response = client.post(
            f"/platform/v1/tenants/{tenant_id}/users",
            headers=platform_auth_headers,
            json={
                "email": "schema-test@example.com",
                "full_name": "Schema Test User",
                "role": "admin",
                "send_invitation": False,
                "password": "SchemaTestPass123!",
            }
        )

        assert response.status_code == 201
        data = response.json()

        # Define allowed fields for UserCreatedResponse
        allowed_fields = {
            "id",
            "email",
            "full_name",
            "role_name",
            "is_active",
            "is_verified",
            "created_at",
            "last_login",
            "invitation_token",  # Allowed but should be None for non-invitation
        }

        # Verify only allowed fields are present
        actual_fields = set(data.keys())
        unexpected_fields = actual_fields - allowed_fields

        assert not unexpected_fields, (
            f"Unexpected fields in response: {unexpected_fields}. "
            f"This may indicate a security issue if sensitive data is exposed."
        )
