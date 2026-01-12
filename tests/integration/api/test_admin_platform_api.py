"""Integration tests for Admin Platform API endpoints.

Test Coverage:
- POST /api/v1/admin/platform/applications (create platform application)
- GET /api/v1/admin/platform/applications (list applications)
- GET /api/v1/admin/platform/applications/{id} (get application)
- PATCH /api/v1/admin/platform/applications/{id} (update application)
- DELETE /api/v1/admin/platform/applications/{id} (deactivate application)
- POST /api/v1/admin/platform/applications/{id}/activate (reactivate application)
- POST /api/v1/admin/platform/applications/{id}/keys (create API key)
- GET /api/v1/admin/platform/applications/{id}/keys (list keys)
- DELETE /api/v1/admin/platform/keys/{id} (revoke key)
- GET /api/v1/admin/platform/audit-logs (list audit logs)
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.models.platform_application import PlatformApplication
from app.models.platform_api_key import PlatformApiKey


class TestCreatePlatformApplication:
    """Test POST /api/v1/admin/platform/applications endpoint."""

    def test_create_application_success(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
    ):
        """Test successful application creation."""
        response = client.post(
            "/api/v1/admin/platform/applications",
            headers=super_admin_auth_headers,
            json={
                "name": "Test Application",
                "slug": "test-application",
                "description": "A test application",
                "rate_limit_per_minute": 100,
                "rate_limit_per_hour": 2000,
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Test Application"
        assert data["slug"] == "test-application"
        assert data["description"] == "A test application"
        assert data["is_active"] is True
        assert data["rate_limit_per_minute"] == 100
        assert data["rate_limit_per_hour"] == 2000
        assert "initial_api_key" in data
        assert data["initial_api_key"].startswith("pk_live_")

    def test_create_application_with_webhook(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
    ):
        """Test application creation with webhook URL."""
        response = client.post(
            "/api/v1/admin/platform/applications",
            headers=super_admin_auth_headers,
            json={
                "name": "Webhook App",
                "slug": "webhook-app",
                "webhook_url": "https://example.com/webhook",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["webhook_url"] == "https://example.com/webhook"

    def test_create_application_with_ip_whitelist(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
    ):
        """Test application creation with IP whitelist."""
        response = client.post(
            "/api/v1/admin/platform/applications",
            headers=super_admin_auth_headers,
            json={
                "name": "IP Restricted App",
                "slug": "ip-restricted-app",
                "allowed_ips": ["192.168.1.0/24", "10.0.0.1"],
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["allowed_ips"] == ["192.168.1.0/24", "10.0.0.1"]

    def test_create_application_duplicate_slug(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
    ):
        """Test application creation with duplicate slug fails."""
        # Create first application
        client.post(
            "/api/v1/admin/platform/applications",
            headers=super_admin_auth_headers,
            json={"name": "First App", "slug": "duplicate-slug-test"}
        )

        # Try to create second with same slug
        response = client.post(
            "/api/v1/admin/platform/applications",
            headers=super_admin_auth_headers,
            json={"name": "Second App", "slug": "duplicate-slug-test"}
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_create_application_invalid_slug(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
    ):
        """Test application creation with invalid slug fails."""
        response = client.post(
            "/api/v1/admin/platform/applications",
            headers=super_admin_auth_headers,
            json={"name": "Bad Slug App", "slug": "Invalid_Slug!"}
        )

        # Pydantic validation returns 422 for invalid input
        assert response.status_code == 422

    def test_create_application_unauthorized(
        self,
        client: TestClient,
    ):
        """Test application creation without authentication."""
        response = client.post(
            "/api/v1/admin/platform/applications",
            json={"name": "Test App", "slug": "test-app"}
        )

        assert response.status_code == 401

    def test_create_application_forbidden_non_super_admin(
        self,
        client: TestClient,
        admin_auth_headers: dict,
    ):
        """Test application creation by non-super admin fails."""
        response = client.post(
            "/api/v1/admin/platform/applications",
            headers=admin_auth_headers,
            json={"name": "Test App", "slug": "forbidden-test-app"}
        )

        assert response.status_code == 403


class TestListPlatformApplications:
    """Test GET /api/v1/admin/platform/applications endpoint."""

    def test_list_applications_success(
        self,
        client: TestClient,
        db_session: Session,
        super_admin_auth_headers: dict,
        platform_application: PlatformApplication,
    ):
        """Test successful application listing."""
        response = client.get(
            "/api/v1/admin/platform/applications",
            headers=super_admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "applications" in data
        assert "limit" in data
        assert "offset" in data
        assert data["total"] >= 1

    def test_list_applications_pagination(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
    ):
        """Test application listing with pagination."""
        # Create multiple applications
        for i in range(5):
            client.post(
                "/api/v1/admin/platform/applications",
                headers=super_admin_auth_headers,
                json={"name": f"App {i}", "slug": f"pagination-app-{i}"}
            )

        response = client.get(
            "/api/v1/admin/platform/applications?limit=2&offset=0",
            headers=super_admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["applications"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0

    def test_list_applications_filter_active(
        self,
        client: TestClient,
        db_session: Session,
        super_admin_auth_headers: dict,
    ):
        """Test application listing filtered by active status."""
        # Create and deactivate an application
        create_response = client.post(
            "/api/v1/admin/platform/applications",
            headers=super_admin_auth_headers,
            json={"name": "Deactivate Me", "slug": "deactivate-filter-test"}
        )
        app_id = create_response.json()["id"]

        client.delete(
            f"/api/v1/admin/platform/applications/{app_id}",
            headers=super_admin_auth_headers,
        )

        # Filter active only
        active_response = client.get(
            "/api/v1/admin/platform/applications?is_active=true",
            headers=super_admin_auth_headers,
        )

        assert active_response.status_code == 200
        for app in active_response.json()["applications"]:
            assert app["is_active"] is True


class TestGetPlatformApplication:
    """Test GET /api/v1/admin/platform/applications/{id} endpoint."""

    def test_get_application_success(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
        platform_application: PlatformApplication,
    ):
        """Test successful application retrieval."""
        response = client.get(
            f"/api/v1/admin/platform/applications/{platform_application.id}",
            headers=super_admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(platform_application.id)
        assert data["name"] == platform_application.name
        assert data["slug"] == platform_application.slug

    def test_get_application_not_found(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
    ):
        """Test getting non-existent application."""
        response = client.get(
            f"/api/v1/admin/platform/applications/{uuid4()}",
            headers=super_admin_auth_headers,
        )

        assert response.status_code == 404


class TestUpdatePlatformApplication:
    """Test PATCH /api/v1/admin/platform/applications/{id} endpoint."""

    def test_update_application_success(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
        platform_application: PlatformApplication,
    ):
        """Test successful application update."""
        response = client.patch(
            f"/api/v1/admin/platform/applications/{platform_application.id}",
            headers=super_admin_auth_headers,
            json={
                "name": "Updated Name",
                "description": "Updated description",
                "rate_limit_per_minute": 200,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
        assert data["rate_limit_per_minute"] == 200

    def test_update_application_webhook(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
        platform_application: PlatformApplication,
    ):
        """Test updating webhook URL."""
        response = client.patch(
            f"/api/v1/admin/platform/applications/{platform_application.id}",
            headers=super_admin_auth_headers,
            json={
                "webhook_url": "https://new-webhook.example.com/hook",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["webhook_url"] == "https://new-webhook.example.com/hook"

    def test_update_application_not_found(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
    ):
        """Test updating non-existent application."""
        response = client.patch(
            f"/api/v1/admin/platform/applications/{uuid4()}",
            headers=super_admin_auth_headers,
            json={"name": "New Name"}
        )

        assert response.status_code == 404


class TestDeactivatePlatformApplication:
    """Test DELETE /api/v1/admin/platform/applications/{id} endpoint."""

    def test_deactivate_application_success(
        self,
        client: TestClient,
        db_session: Session,
        super_admin_auth_headers: dict,
    ):
        """Test successful application deactivation."""
        # Create an application to deactivate
        create_response = client.post(
            "/api/v1/admin/platform/applications",
            headers=super_admin_auth_headers,
            json={"name": "To Deactivate", "slug": "to-deactivate-test"}
        )
        app_id = create_response.json()["id"]

        response = client.delete(
            f"/api/v1/admin/platform/applications/{app_id}",
            headers=super_admin_auth_headers,
        )

        assert response.status_code == 204

        # Verify deactivation
        get_response = client.get(
            f"/api/v1/admin/platform/applications/{app_id}",
            headers=super_admin_auth_headers,
        )
        assert get_response.json()["is_active"] is False

    def test_deactivate_application_not_found(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
    ):
        """Test deactivating non-existent application."""
        response = client.delete(
            f"/api/v1/admin/platform/applications/{uuid4()}",
            headers=super_admin_auth_headers,
        )

        assert response.status_code == 404


class TestActivatePlatformApplication:
    """Test POST /api/v1/admin/platform/applications/{id}/activate endpoint."""

    def test_activate_application_success(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
    ):
        """Test successful application reactivation."""
        # Create and deactivate an application
        create_response = client.post(
            "/api/v1/admin/platform/applications",
            headers=super_admin_auth_headers,
            json={"name": "To Reactivate", "slug": "to-reactivate-test"}
        )
        app_id = create_response.json()["id"]

        client.delete(
            f"/api/v1/admin/platform/applications/{app_id}",
            headers=super_admin_auth_headers,
        )

        # Reactivate
        response = client.post(
            f"/api/v1/admin/platform/applications/{app_id}/activate",
            headers=super_admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True


class TestCreatePlatformApiKey:
    """Test POST /api/v1/admin/platform/applications/{id}/keys endpoint."""

    def test_create_api_key_success(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
        platform_application: PlatformApplication,
    ):
        """Test successful API key creation."""
        response = client.post(
            f"/api/v1/admin/platform/applications/{platform_application.id}/keys",
            headers=super_admin_auth_headers,
            json={
                "name": "New API Key",
                "scopes": ["tenants:create", "tenants:read"],
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New API Key"
        assert data["scopes"] == ["tenants:create", "tenants:read"]
        assert "token" in data
        assert data["token"].startswith("pk_live_")

    def test_create_api_key_with_expiration(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
        platform_application: PlatformApplication,
    ):
        """Test API key creation with expiration."""
        response = client.post(
            f"/api/v1/admin/platform/applications/{platform_application.id}/keys",
            headers=super_admin_auth_headers,
            json={
                "name": "Expiring Key",
                "scopes": ["tenants:read"],
                "expires_in_days": 30,
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["expires_at"] is not None

    def test_create_api_key_invalid_scopes(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
        platform_application: PlatformApplication,
    ):
        """Test API key creation with invalid scopes."""
        response = client.post(
            f"/api/v1/admin/platform/applications/{platform_application.id}/keys",
            headers=super_admin_auth_headers,
            json={
                "name": "Bad Key",
                "scopes": ["invalid:scope"],
            }
        )

        # Pydantic validation returns 422 for invalid enum values
        assert response.status_code == 422

    def test_create_api_key_application_not_found(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
    ):
        """Test API key creation for non-existent application."""
        response = client.post(
            f"/api/v1/admin/platform/applications/{uuid4()}/keys",
            headers=super_admin_auth_headers,
            json={
                "name": "Orphan Key",
                "scopes": ["tenants:read"],
            }
        )

        assert response.status_code == 400


class TestListPlatformApiKeys:
    """Test GET /api/v1/admin/platform/applications/{id}/keys endpoint."""

    def test_list_api_keys_success(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
        platform_application: PlatformApplication,
        platform_api_key: tuple,
    ):
        """Test successful API key listing."""
        response = client.get(
            f"/api/v1/admin/platform/applications/{platform_application.id}/keys",
            headers=super_admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_api_keys_filter_active(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
        platform_application: PlatformApplication,
    ):
        """Test API key listing filtered by active status."""
        # Create and revoke a key
        create_response = client.post(
            f"/api/v1/admin/platform/applications/{platform_application.id}/keys",
            headers=super_admin_auth_headers,
            json={"name": "To Revoke", "scopes": ["tenants:read"]}
        )
        key_id = create_response.json()["id"]

        client.delete(
            f"/api/v1/admin/platform/keys/{key_id}",
            headers=super_admin_auth_headers,
        )

        # Filter active only
        response = client.get(
            f"/api/v1/admin/platform/applications/{platform_application.id}/keys?is_active=true",
            headers=super_admin_auth_headers,
        )

        assert response.status_code == 200
        for key in response.json():
            assert key["is_active"] is True

    def test_list_api_keys_application_not_found(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
    ):
        """Test API key listing for non-existent application."""
        response = client.get(
            f"/api/v1/admin/platform/applications/{uuid4()}/keys",
            headers=super_admin_auth_headers,
        )

        assert response.status_code == 404


class TestRevokePlatformApiKey:
    """Test DELETE /api/v1/admin/platform/keys/{id} endpoint."""

    def test_revoke_api_key_success(
        self,
        client: TestClient,
        db_session: Session,
        super_admin_auth_headers: dict,
        platform_application: PlatformApplication,
    ):
        """Test successful API key revocation."""
        # Create a key to revoke
        create_response = client.post(
            f"/api/v1/admin/platform/applications/{platform_application.id}/keys",
            headers=super_admin_auth_headers,
            json={"name": "To Revoke", "scopes": ["tenants:read"]}
        )
        key_id = create_response.json()["id"]

        response = client.delete(
            f"/api/v1/admin/platform/keys/{key_id}",
            headers=super_admin_auth_headers,
        )

        assert response.status_code == 204

        # Verify revocation
        key = db_session.query(PlatformApiKey).filter(
            PlatformApiKey.id == key_id
        ).first()
        assert key.is_active is False
        assert key.revoked_at is not None

    def test_revoke_api_key_not_found(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
    ):
        """Test revoking non-existent API key."""
        response = client.delete(
            f"/api/v1/admin/platform/keys/{uuid4()}",
            headers=super_admin_auth_headers,
        )

        assert response.status_code == 404


class TestListPlatformAuditLogs:
    """Test GET /api/v1/admin/platform/audit-logs endpoint."""

    def test_list_audit_logs_success(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
    ):
        """Test successful audit log listing."""
        response = client.get(
            "/api/v1/admin/platform/audit-logs",
            headers=super_admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "logs" in data
        assert "limit" in data
        assert "offset" in data

    def test_list_audit_logs_pagination(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
    ):
        """Test audit log listing with pagination."""
        response = client.get(
            "/api/v1/admin/platform/audit-logs?limit=10&offset=0",
            headers=super_admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0

    def test_list_audit_logs_filter_by_application(
        self,
        client: TestClient,
        super_admin_auth_headers: dict,
        platform_application: PlatformApplication,
    ):
        """Test audit log listing filtered by application."""
        response = client.get(
            f"/api/v1/admin/platform/audit-logs?application_id={platform_application.id}",
            headers=super_admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        for log in data["logs"]:
            assert log["application_id"] == str(platform_application.id)
