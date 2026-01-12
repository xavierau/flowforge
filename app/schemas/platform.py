"""Pydantic schemas for Platform API."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, field_validator

from app.models.enums import PlatformScope


# =============================================================================
# Request Schemas
# =============================================================================

class CreateTenantRequest(BaseModel):
    """Request schema for creating a new tenant."""

    name: str = Field(..., min_length=1, max_length=255, description="Tenant display name")
    slug: Optional[str] = Field(
        None,
        min_length=3,
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$",
        description="URL-safe unique identifier (auto-generated if not provided)"
    )
    subscription_plan: Optional[str] = Field(
        "free",
        pattern=r"^(free|starter|pro|enterprise)$",
        description="Subscription plan tier"
    )
    initial_credits: Optional[int] = Field(
        100,
        ge=0,
        description="Initial credits to allocate"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional tenant metadata"
    )


class UpdateTenantRequest(BaseModel):
    """Request schema for updating a tenant."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(
        None,
        pattern=r"^(active|suspended|cancelled)$",
        description="Tenant status"
    )
    subscription_plan: Optional[str] = Field(
        None,
        pattern=r"^(free|starter|pro|enterprise)$"
    )
    metadata: Optional[Dict[str, Any]] = None


class CreateUserInTenantRequest(BaseModel):
    """Request schema for creating a user in a tenant."""

    email: EmailStr = Field(..., description="User email address")
    full_name: Optional[str] = Field(None, max_length=255)
    role: str = Field(
        "member",
        pattern=r"^(admin|member|viewer)$",
        description="User role within the tenant"
    )
    send_invitation: bool = Field(
        True,
        description="Whether to send invitation email"
    )
    password: Optional[str] = Field(
        None,
        min_length=8,
        max_length=100,
        description="Initial password (if not sending invitation)"
    )

    @field_validator('password')
    @classmethod
    def validate_password_requirement(cls, v, info):
        """Validate password is provided when not sending invitation."""
        send_invitation = info.data.get('send_invitation', True)
        if not send_invitation and not v:
            raise ValueError("Password is required when send_invitation is False")
        return v


class UpdateUserRequest(BaseModel):
    """Request schema for updating a user."""

    full_name: Optional[str] = Field(None, max_length=255)
    role: Optional[str] = Field(
        None,
        pattern=r"^(admin|member|viewer)$"
    )
    is_active: Optional[bool] = None


class CreateApiTokenForUserRequest(BaseModel):
    """Request schema for creating an API token for a user."""

    name: str = Field(..., min_length=1, max_length=100, description="Token name")
    scopes: List[str] = Field(..., min_length=1, description="Token scopes/permissions")
    expires_in_days: Optional[int] = Field(
        None,
        ge=1,
        le=365,
        description="Token expiration in days (None = never expires)"
    )


class AddCreditsRequest(BaseModel):
    """Request schema for adding credits to a tenant."""

    amount: int = Field(..., gt=0, description="Number of credits to add")
    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Reason for adding credits"
    )


# =============================================================================
# Response Schemas
# =============================================================================

class TenantResponse(BaseModel):
    """Response schema for tenant data."""

    id: UUID
    name: str
    slug: str
    status: str
    subscription_plan: str
    credit_balance: int
    user_count: int
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class TenantCreatedResponse(TenantResponse):
    """Response schema for newly created tenant."""

    admin_user: Optional["UserResponse"] = None


class UserResponse(BaseModel):
    """Response schema for user data."""

    id: UUID
    email: str
    full_name: Optional[str]
    role_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserCreatedResponse(UserResponse):
    """Response schema for newly created user.

    Note: temporary_password is intentionally NOT returned for security reasons.
    The caller already knows the password they sent in the request. Returning it
    would create log exposure risk via intermediate proxies or monitoring systems.
    """

    invitation_token: Optional[str] = None


class ApiTokenResponse(BaseModel):
    """Response schema for API token data."""

    id: UUID
    name: str
    token_prefix: str
    scopes: List[str]
    expires_at: Optional[datetime]
    created_at: datetime
    last_used_at: Optional[datetime] = None
    is_active: bool

    model_config = {"from_attributes": True}


class ApiTokenCreatedResponse(ApiTokenResponse):
    """Response schema for newly created API token (includes full token)."""

    token: str = Field(..., description="Full API token (shown only once)")


class CreditBalanceResponse(BaseModel):
    """Response schema for credit balance."""

    tenant_id: UUID
    balance: int
    last_updated: datetime


class CreditTransactionResponse(BaseModel):
    """Response schema for credit transaction."""

    id: UUID
    amount: int
    transaction_type: str
    description: Optional[str]
    created_at: datetime


# =============================================================================
# Platform Application Schemas (for Admin endpoints)
# =============================================================================

class CreatePlatformApplicationRequest(BaseModel):
    """Request schema for creating a platform application."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(
        ...,
        min_length=3,
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$"
    )
    description: Optional[str] = Field(None, max_length=1000)
    webhook_url: Optional[str] = Field(None, max_length=500)
    allowed_ips: Optional[List[str]] = Field(
        None,
        description="List of allowed IP addresses or CIDR ranges"
    )
    rate_limit_per_minute: int = Field(60, ge=1, le=10000)
    rate_limit_per_hour: int = Field(1000, ge=1, le=100000)


class UpdatePlatformApplicationRequest(BaseModel):
    """Request schema for updating a platform application."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    webhook_url: Optional[str] = Field(None, max_length=500)
    allowed_ips: Optional[List[str]] = None
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=10000)
    rate_limit_per_hour: Optional[int] = Field(None, ge=1, le=100000)


class PlatformApplicationResponse(BaseModel):
    """Response schema for platform application."""

    id: UUID
    name: str
    slug: str
    description: Optional[str]
    webhook_url: Optional[str]
    allowed_ips: List[str]
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    api_key_count: int = 0

    model_config = {"from_attributes": True}


class PlatformApplicationCreatedResponse(PlatformApplicationResponse):
    """Response schema for newly created platform application."""

    initial_api_key: str = Field(..., description="Initial API key (shown only once)")


class CreatePlatformApiKeyRequest(BaseModel):
    """Request schema for creating a platform API key."""

    name: str = Field(..., min_length=1, max_length=100)
    scopes: List[str] = Field(..., min_length=1)
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)

    @field_validator('scopes')
    @classmethod
    def validate_scopes(cls, v):
        """Validate all scopes are valid."""
        if not PlatformScope.validate_scopes(v):
            valid_scopes = PlatformScope.all_scopes()
            raise ValueError(
                f"Invalid scopes. Valid scopes are: {valid_scopes}. "
                "Also accepts wildcards: '*:*' (all scopes) or "
                "'<resource>:*' (e.g., 'tenants:*' for all tenant operations)."
            )
        return v


class PlatformApiKeyResponse(BaseModel):
    """Response schema for platform API key."""

    id: UUID
    name: str
    token_prefix: str
    scopes: List[str]
    expires_at: Optional[datetime]
    created_at: datetime
    last_used_at: Optional[datetime]
    is_active: bool

    model_config = {"from_attributes": True}


class PlatformApiKeyCreatedResponse(PlatformApiKeyResponse):
    """Response schema for newly created platform API key."""

    token: str = Field(..., description="Full API key (shown only once)")


class PlatformAuditLogResponse(BaseModel):
    """Response schema for platform audit log entry."""

    id: UUID
    application_id: Optional[UUID]
    api_key_id: Optional[UUID]
    action: str
    resource_type: str
    resource_id: Optional[UUID]
    endpoint: str
    method: str
    ip_address: Optional[str]
    status_code: Optional[int]
    error_message: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# List Response Schemas
# =============================================================================

class PaginatedResponse(BaseModel):
    """Base schema for paginated responses."""

    total: int
    limit: int
    offset: int


class TenantListResponse(PaginatedResponse):
    """Response schema for listing tenants."""

    tenants: List[TenantResponse]


class UserListResponse(PaginatedResponse):
    """Response schema for listing users."""

    users: List[UserResponse]


class ApiTokenListResponse(PaginatedResponse):
    """Response schema for listing API tokens."""

    tokens: List[ApiTokenResponse]


class PlatformApplicationListResponse(PaginatedResponse):
    """Response schema for listing platform applications."""

    applications: List[PlatformApplicationResponse]


class PlatformAuditLogListResponse(PaginatedResponse):
    """Response schema for listing audit logs."""

    logs: List[PlatformAuditLogResponse]


# Update forward references
TenantCreatedResponse.model_rebuild()
