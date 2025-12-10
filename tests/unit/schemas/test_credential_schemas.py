"""Unit tests for credential Pydantic schemas."""

import pytest
from uuid import uuid4
from datetime import datetime
from pydantic import ValidationError

from app.schemas.credential import (
    CredentialCreate,
    CredentialUpdate,
    CredentialResponse,
    CredentialListResponse,
)


class TestCredentialCreate:
    """Tests for CredentialCreate schema."""

    def test_valid_credential_create(self):
        """Test creating valid credential schema."""
        data = {
            "name": "API_KEY",
            "value": "sk_live_abc123xyz",
            "description": "Test API key",
            "workflow_id": None,
        }
        credential = CredentialCreate(**data)
        assert credential.name == "API_KEY"
        assert credential.value == "sk_live_abc123xyz"
        assert credential.description == "Test API key"
        assert credential.workflow_id is None

    def test_valid_credential_with_workflow_id(self):
        """Test creating credential scoped to workflow."""
        workflow_id = uuid4()
        data = {
            "name": "VENDOR_KEY",
            "value": "secret123",
            "workflow_id": workflow_id,
        }
        credential = CredentialCreate(**data)
        assert credential.workflow_id == workflow_id

    def test_name_validation_uppercase(self):
        """Test that name must be uppercase."""
        with pytest.raises(ValidationError, match="uppercase"):
            CredentialCreate(name="api_key", value="secret")

    def test_name_validation_starts_with_letter(self):
        """Test that name must start with letter."""
        with pytest.raises(ValidationError, match="uppercase letter"):
            CredentialCreate(name="123_KEY", value="secret")

    def test_name_validation_no_special_chars(self):
        """Test that name cannot have special characters."""
        with pytest.raises(ValidationError, match="uppercase"):
            CredentialCreate(name="API-KEY", value="secret")

    def test_name_validation_valid_patterns(self):
        """Test valid name patterns."""
        valid_names = [
            "A",
            "API_KEY",
            "VENDOR_API_KEY_V2",
            "X123",
            "KEY_1_2_3",
        ]
        for name in valid_names:
            credential = CredentialCreate(name=name, value="secret")
            assert credential.name == name

    def test_empty_name_fails(self):
        """Test that empty name fails validation."""
        with pytest.raises(ValidationError):
            CredentialCreate(name="", value="secret")

    def test_empty_value_fails(self):
        """Test that empty value fails validation."""
        with pytest.raises(ValidationError):
            CredentialCreate(name="API_KEY", value="")

    def test_name_trimming(self):
        """Test that name is trimmed."""
        credential = CredentialCreate(name="  API_KEY  ", value="secret")
        assert credential.name == "API_KEY"


class TestCredentialUpdate:
    """Tests for CredentialUpdate schema."""

    def test_all_fields_optional(self):
        """Test that all fields are optional."""
        update = CredentialUpdate()
        assert update.description is None
        assert update.value is None
        assert update.is_active is None

    def test_update_description_only(self):
        """Test updating only description."""
        update = CredentialUpdate(description="New description")
        assert update.description == "New description"
        assert update.value is None
        assert update.is_active is None

    def test_update_value_only(self):
        """Test updating only value."""
        update = CredentialUpdate(value="new_secret")
        assert update.value == "new_secret"
        assert update.description is None

    def test_update_is_active_only(self):
        """Test updating only active status."""
        update = CredentialUpdate(is_active=False)
        assert update.is_active is False

    def test_update_all_fields(self):
        """Test updating all fields."""
        update = CredentialUpdate(
            description="Updated",
            value="new_secret",
            is_active=True,
        )
        assert update.description == "Updated"
        assert update.value == "new_secret"
        assert update.is_active is True


class TestCredentialResponse:
    """Tests for CredentialResponse schema."""

    def test_valid_response(self):
        """Test creating valid response schema."""
        now = datetime.utcnow()
        cred_id = uuid4()
        user_id = uuid4()

        response = CredentialResponse(
            id=cred_id,
            name="API_KEY",
            description="Test key",
            workflow_id=None,
            is_active=True,
            created_at=now,
            updated_at=now,
            created_by_user_id=user_id,
        )

        assert response.id == cred_id
        assert response.name == "API_KEY"
        assert response.is_active is True

    def test_response_without_optional_fields(self):
        """Test response without optional fields."""
        now = datetime.utcnow()
        response = CredentialResponse(
            id=uuid4(),
            name="KEY",
            description=None,
            workflow_id=None,
            is_active=True,
            created_at=now,
            updated_at=now,
            created_by_user_id=None,
        )
        assert response.description is None
        assert response.workflow_id is None
        assert response.created_by_user_id is None

    def test_response_no_value_field(self):
        """Test that response schema has no value field."""
        # This is a security check - value should never be exposed
        assert not hasattr(CredentialResponse, "value")
        assert "value" not in CredentialResponse.model_fields


class TestCredentialListResponse:
    """Tests for CredentialListResponse schema."""

    def test_empty_list(self):
        """Test response with empty list."""
        response = CredentialListResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            has_more=False,
        )
        assert response.items == []
        assert response.total == 0
        assert response.has_more is False

    def test_list_with_items(self):
        """Test response with items."""
        now = datetime.utcnow()
        items = [
            CredentialResponse(
                id=uuid4(),
                name=f"KEY_{i}",
                description=None,
                workflow_id=None,
                is_active=True,
                created_at=now,
                updated_at=now,
                created_by_user_id=None,
            )
            for i in range(3)
        ]

        response = CredentialListResponse(
            items=items,
            total=10,
            page=1,
            page_size=3,
            has_more=True,
        )

        assert len(response.items) == 3
        assert response.total == 10
        assert response.has_more is True

    def test_pagination_info(self):
        """Test pagination information."""
        response = CredentialListResponse(
            items=[],
            total=100,
            page=5,
            page_size=20,
            has_more=False,
        )
        assert response.page == 5
        assert response.page_size == 20
