"""API Token-related Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================


class ApiTokenCreateRequest(BaseModel):
    """Request schema for creating a new API token."""

    name: str = Field(
        ...,
        description="User-friendly token name",
        min_length=1,
        max_length=100,
        json_schema_extra={"example": "Production Webhook"}
    )
    scopes: List[str] = Field(
        ...,
        description="List of permissions for this token",
        min_length=1,
        json_schema_extra={"example": ["documents:read", "documents:create"]}
    )
    expires_in_days: Optional[int] = Field(
        None,
        description="Days until expiration (null=never)",
        gt=0,
        le=365,
        json_schema_extra={"example": 90}
    )


class ApiTokenUpdateRequest(BaseModel):
    """Request schema for updating an API token."""

    name: Optional[str] = Field(
        None,
        description="Updated token name",
        min_length=1,
        max_length=100,
        json_schema_extra={"example": "Updated Token Name"}
    )
    scopes: Optional[List[str]] = Field(
        None,
        description="Updated list of permissions",
        min_length=1,
        json_schema_extra={"example": ["documents:read"]}
    )


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================


class ApiTokenCreateResponse(BaseModel):
    """Response schema after creating API token (includes full token ONCE)."""

    token: str = Field(
        ...,
        description="Full API token - SAVE THIS, IT WON'T BE SHOWN AGAIN",
        json_schema_extra={"example": "sk_live_abc123xyz456def789ghi012jkl345_mno678pqr901"}
    )
    token_id: str = Field(
        ...,
        description="Token ID",
        json_schema_extra={"example": "123e4567-e89b-12d3-a456-426614174000"}
    )
    name: str = Field(
        ...,
        description="Token name",
        json_schema_extra={"example": "Production Webhook"}
    )
    token_prefix: str = Field(
        ...,
        description="Token prefix for display",
        json_schema_extra={"example": "sk_live_abc12345"}
    )
    scopes: List[str] = Field(
        ...,
        description="List of permissions",
        json_schema_extra={"example": ["documents:read", "documents:create"]}
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Token expiration timestamp",
        json_schema_extra={"example": "2025-02-02T00:00:00Z"}
    )
    created_at: datetime = Field(
        ...,
        description="Token creation timestamp",
        json_schema_extra={"example": "2024-11-04T12:00:00Z"}
    )


class ApiTokenInfo(BaseModel):
    """API token info (without full token)."""

    token_id: str = Field(
        ...,
        description="Token ID",
        json_schema_extra={"example": "123e4567-e89b-12d3-a456-426614174000"}
    )
    name: str = Field(
        ...,
        description="Token name",
        json_schema_extra={"example": "Production Webhook"}
    )
    token_prefix: str = Field(
        ...,
        description="Token prefix for display",
        json_schema_extra={"example": "sk_live_abc12345"}
    )
    scopes: List[str] = Field(
        ...,
        description="List of permissions",
        json_schema_extra={"example": ["documents:read", "documents:create"]}
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Token expiration timestamp",
        json_schema_extra={"example": "2025-02-02T00:00:00Z"}
    )
    last_used_at: Optional[datetime] = Field(
        None,
        description="Last used timestamp",
        json_schema_extra={"example": "2024-11-04T12:00:00Z"}
    )
    created_at: datetime = Field(
        ...,
        description="Token creation timestamp",
        json_schema_extra={"example": "2024-11-04T12:00:00Z"}
    )

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str = Field(
        ...,
        description="Response message",
        json_schema_extra={"example": "Operation completed successfully"}
    )
