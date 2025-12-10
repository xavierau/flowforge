"""Credential-related Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator
import re


# Credential name validation pattern (uppercase with underscores)
CREDENTIAL_NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================


class CredentialCreate(BaseModel):
    """Request schema for creating a new credential."""

    name: str = Field(
        ...,
        description="Credential name (uppercase with underscores, e.g., API_KEY)",
        min_length=1,
        max_length=100,
        json_schema_extra={"example": "VENDOR_API_KEY"},
    )
    value: str = Field(
        ...,
        description="The secret value to store (will be encrypted)",
        min_length=1,
        json_schema_extra={"example": "sk_live_abc123xyz..."},
    )
    description: Optional[str] = Field(
        None,
        description="Optional description of this credential",
        max_length=500,
        json_schema_extra={"example": "API key for vendor XYZ integration"},
    )
    workflow_id: Optional[UUID] = Field(
        None,
        description="Workflow ID for workflow-scoped credentials (null = tenant-level)",
        json_schema_extra={"example": "123e4567-e89b-12d3-a456-426614174000"},
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate credential name format."""
        v = v.strip()
        if not CREDENTIAL_NAME_PATTERN.match(v):
            raise ValueError(
                "Credential name must start with an uppercase letter and "
                "contain only uppercase letters, numbers, and underscores"
            )
        return v


class CredentialUpdate(BaseModel):
    """Request schema for updating a credential."""

    description: Optional[str] = Field(
        None,
        description="Updated description",
        max_length=500,
        json_schema_extra={"example": "Updated API key description"},
    )
    value: Optional[str] = Field(
        None,
        description="New secret value (will be re-encrypted)",
        min_length=1,
        json_schema_extra={"example": "sk_live_new_value..."},
    )
    is_active: Optional[bool] = Field(
        None,
        description="Whether the credential is active",
        json_schema_extra={"example": True},
    )


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================


class CredentialResponse(BaseModel):
    """Response schema for a single credential (NO value exposed)."""

    id: UUID = Field(
        ...,
        description="Credential ID",
        json_schema_extra={"example": "123e4567-e89b-12d3-a456-426614174000"},
    )
    name: str = Field(
        ...,
        description="Credential name",
        json_schema_extra={"example": "VENDOR_API_KEY"},
    )
    description: Optional[str] = Field(
        None,
        description="Credential description",
        json_schema_extra={"example": "API key for vendor XYZ integration"},
    )
    workflow_id: Optional[UUID] = Field(
        None,
        description="Workflow ID (null = tenant-level)",
        json_schema_extra={"example": "123e4567-e89b-12d3-a456-426614174000"},
    )
    is_active: bool = Field(
        ...,
        description="Whether the credential is active",
        json_schema_extra={"example": True},
    )
    created_at: datetime = Field(
        ...,
        description="Creation timestamp",
        json_schema_extra={"example": "2024-12-03T12:00:00Z"},
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
        json_schema_extra={"example": "2024-12-03T12:00:00Z"},
    )
    created_by_user_id: Optional[UUID] = Field(
        None,
        description="User ID who created this credential",
        json_schema_extra={"example": "123e4567-e89b-12d3-a456-426614174000"},
    )

    model_config = ConfigDict(from_attributes=True)


class CredentialListResponse(BaseModel):
    """Response schema for listing credentials with pagination."""

    items: List[CredentialResponse] = Field(
        ...,
        description="List of credentials",
    )
    total: int = Field(
        ...,
        description="Total number of credentials",
        json_schema_extra={"example": 10},
    )
    page: int = Field(
        ...,
        description="Current page number (1-based)",
        json_schema_extra={"example": 1},
    )
    page_size: int = Field(
        ...,
        description="Number of items per page",
        json_schema_extra={"example": 20},
    )
    has_more: bool = Field(
        ...,
        description="Whether there are more pages",
        json_schema_extra={"example": False},
    )


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str = Field(
        ...,
        description="Response message",
        json_schema_extra={"example": "Operation completed successfully"},
    )
