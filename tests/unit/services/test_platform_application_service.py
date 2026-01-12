"""Unit tests for PlatformApplicationService."""

import pytest
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.platform_application import PlatformApplication
from app.services.platform_application_service import PlatformApplicationService


class TestPlatformApplicationService:
    """Tests for PlatformApplicationService."""

    def test_create_application_success(self, db_session: Session):
        """Test successful application creation."""
        service = PlatformApplicationService(db_session)

        application, initial_key = service.create_application(
            name="Test App",
            slug="test-app",
            description="Test application",
            rate_limit_per_minute=100,
            rate_limit_per_hour=2000,
        )

        assert application.name == "Test App"
        assert application.slug == "test-app"
        assert application.is_active is True
        assert initial_key.startswith("pk_live_")

    def test_create_application_with_webhook(self, db_session: Session):
        """Test application creation with webhook URL."""
        service = PlatformApplicationService(db_session)

        application, _ = service.create_application(
            name="Webhook App",
            slug="webhook-app",
            webhook_url="https://example.com/webhook",
        )

        assert application.webhook_url == "https://example.com/webhook"
        assert application.webhook_secret is not None

    def test_create_application_duplicate_slug(self, db_session: Session):
        """Test application creation with duplicate slug fails."""
        service = PlatformApplicationService(db_session)

        # Create first application
        service.create_application(name="First App", slug="duplicate-slug")

        # Try to create second with same slug
        with pytest.raises(ValueError, match="already exists"):
            service.create_application(name="Second App", slug="duplicate-slug")

    def test_create_application_invalid_slug(self, db_session: Session):
        """Test application creation with invalid slug fails."""
        service = PlatformApplicationService(db_session)

        # Too short
        with pytest.raises(ValueError, match="lowercase alphanumeric"):
            service.create_application(name="App", slug="ab")

        # Invalid characters
        with pytest.raises(ValueError, match="lowercase alphanumeric"):
            service.create_application(name="App", slug="Test_App")

    def test_get_application_by_id(self, db_session: Session):
        """Test getting application by ID."""
        service = PlatformApplicationService(db_session)
        application, _ = service.create_application(name="Test App", slug="test-app-id")

        found = service.get_application_by_id(application.id)
        assert found is not None
        assert found.id == application.id

    def test_get_application_by_id_not_found(self, db_session: Session):
        """Test getting non-existent application by ID."""
        service = PlatformApplicationService(db_session)

        found = service.get_application_by_id(uuid4())
        assert found is None

    def test_get_application_by_slug(self, db_session: Session):
        """Test getting application by slug."""
        service = PlatformApplicationService(db_session)
        application, _ = service.create_application(name="Test App", slug="test-app-slug")

        found = service.get_application_by_slug("test-app-slug")
        assert found is not None
        assert found.slug == "test-app-slug"

    def test_list_applications(self, db_session: Session):
        """Test listing applications."""
        service = PlatformApplicationService(db_session)

        # Create some applications
        for i in range(3):
            service.create_application(name=f"App {i}", slug=f"app-{i}")

        applications, total = service.list_applications(limit=10)
        assert total == 3
        assert len(applications) == 3

    def test_list_applications_filter_active(self, db_session: Session):
        """Test listing applications with active filter."""
        service = PlatformApplicationService(db_session)

        # Create active and inactive apps
        app1, _ = service.create_application(name="Active App", slug="active-app")
        app2, _ = service.create_application(name="Inactive App", slug="inactive-app")
        service.deactivate_application(app2.id)

        active_apps, _ = service.list_applications(is_active=True)
        inactive_apps, _ = service.list_applications(is_active=False)

        assert len(active_apps) == 1
        assert len(inactive_apps) == 1

    def test_update_application(self, db_session: Session):
        """Test updating application."""
        service = PlatformApplicationService(db_session)
        application, _ = service.create_application(name="Original Name", slug="update-test")

        updated = service.update_application(
            application_id=application.id,
            name="Updated Name",
            description="New description",
            rate_limit_per_minute=200,
        )

        assert updated.name == "Updated Name"
        assert updated.description == "New description"
        assert updated.rate_limit_per_minute == 200

    def test_update_application_not_found(self, db_session: Session):
        """Test updating non-existent application."""
        service = PlatformApplicationService(db_session)

        result = service.update_application(
            application_id=uuid4(),
            name="New Name",
        )
        assert result is None

    def test_deactivate_application(self, db_session: Session):
        """Test deactivating application."""
        service = PlatformApplicationService(db_session)
        application, _ = service.create_application(name="App to Deactivate", slug="deactivate-test")

        deactivated = service.deactivate_application(application.id)

        assert deactivated.is_active is False

    def test_activate_application(self, db_session: Session):
        """Test reactivating application."""
        service = PlatformApplicationService(db_session)
        application, _ = service.create_application(name="App to Reactivate", slug="reactivate-test")
        service.deactivate_application(application.id)

        activated = service.activate_application(application.id)

        assert activated.is_active is True

    def test_validate_ip_whitelist_empty(self, db_session: Session):
        """Test IP validation with empty whitelist (allow all)."""
        service = PlatformApplicationService(db_session)

        assert service.validate_ip_whitelist("1.2.3.4", []) is True
        assert service.validate_ip_whitelist("192.168.1.1", []) is True

    def test_validate_ip_whitelist_single_ip(self, db_session: Session):
        """Test IP validation with single IP."""
        service = PlatformApplicationService(db_session)
        allowed = ["1.2.3.4"]

        assert service.validate_ip_whitelist("1.2.3.4", allowed) is True
        assert service.validate_ip_whitelist("1.2.3.5", allowed) is False

    def test_validate_ip_whitelist_cidr(self, db_session: Session):
        """Test IP validation with CIDR range."""
        service = PlatformApplicationService(db_session)
        allowed = ["10.0.0.0/8"]

        assert service.validate_ip_whitelist("10.0.0.1", allowed) is True
        assert service.validate_ip_whitelist("10.255.255.255", allowed) is True
        assert service.validate_ip_whitelist("11.0.0.1", allowed) is False

    def test_validate_ip_whitelist_multiple(self, db_session: Session):
        """Test IP validation with multiple entries."""
        service = PlatformApplicationService(db_session)
        allowed = ["1.2.3.4", "192.168.0.0/16"]

        assert service.validate_ip_whitelist("1.2.3.4", allowed) is True
        assert service.validate_ip_whitelist("192.168.1.100", allowed) is True
        assert service.validate_ip_whitelist("8.8.8.8", allowed) is False

    def test_validate_ip_whitelist_invalid_ip(self, db_session: Session):
        """Test IP validation with invalid IP address."""
        service = PlatformApplicationService(db_session)
        allowed = ["1.2.3.4"]

        assert service.validate_ip_whitelist("invalid", allowed) is False

    def test_create_api_key(self, db_session: Session):
        """Test creating API key for application."""
        service = PlatformApplicationService(db_session)
        application, _ = service.create_application(name="Key Test App", slug="key-test-app")

        api_key, full_key = service.create_api_key(
            application_id=application.id,
            name="Test Key",
            scopes=["tenants:create", "tenants:read"],
        )

        assert api_key.name == "Test Key"
        assert api_key.scopes == ["tenants:create", "tenants:read"]
        assert full_key.startswith("pk_live_")

    def test_create_api_key_invalid_scopes(self, db_session: Session):
        """Test creating API key with invalid scopes."""
        service = PlatformApplicationService(db_session)
        application, _ = service.create_application(name="Invalid Scope App", slug="invalid-scope-app")

        with pytest.raises(ValueError, match="Invalid scopes"):
            service.create_api_key(
                application_id=application.id,
                name="Bad Key",
                scopes=["invalid:scope"],
            )

    def test_revoke_api_key(self, db_session: Session):
        """Test revoking API key."""
        service = PlatformApplicationService(db_session)
        application, _ = service.create_application(name="Revoke Test App", slug="revoke-test-app")
        api_key, _ = service.create_api_key(
            application_id=application.id,
            name="Key to Revoke",
            scopes=["tenants:read"],
        )

        revoked = service.revoke_api_key(api_key.id)

        assert revoked.is_active is False
        assert revoked.revoked_at is not None

    def test_list_api_keys(self, db_session: Session):
        """Test listing API keys for application."""
        service = PlatformApplicationService(db_session)
        application, _ = service.create_application(name="List Keys App", slug="list-keys-app")

        # Create additional keys (initial key is created with application)
        service.create_api_key(
            application_id=application.id,
            name="Extra Key 1",
            scopes=["tenants:read"],
        )
        service.create_api_key(
            application_id=application.id,
            name="Extra Key 2",
            scopes=["tenants:read"],
        )

        keys = service.list_api_keys(application.id)
        assert len(keys) == 3  # Initial key + 2 extra keys

    def test_list_api_keys_filter_active(self, db_session: Session):
        """Test listing API keys with active filter."""
        service = PlatformApplicationService(db_session)
        application, _ = service.create_application(name="Filter Keys App", slug="filter-keys-app")

        api_key, _ = service.create_api_key(
            application_id=application.id,
            name="Key to Revoke",
            scopes=["tenants:read"],
        )
        service.revoke_api_key(api_key.id)

        active_keys = service.list_api_keys(application.id, is_active=True)
        inactive_keys = service.list_api_keys(application.id, is_active=False)

        assert len(active_keys) == 1  # Initial key only
        assert len(inactive_keys) == 1  # Revoked key
