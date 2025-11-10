"""Pydantic schemas for admin API endpoints."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, validator


# ============================================================================
# Platform Statistics Schemas
# ============================================================================

class PlatformStatistics(BaseModel):
    """Platform-wide statistics for super admin dashboard."""

    # Tenant metrics
    total_tenants: int = Field(..., description="Total number of tenants")
    active_tenants: int = Field(..., description="Number of active tenants")
    suspended_tenants: int = Field(..., description="Number of suspended tenants")
    new_tenants_30d: int = Field(..., description="New tenants in last 30 days")

    # User metrics
    total_users: int = Field(..., description="Total users across all tenants")
    active_users: int = Field(..., description="Active users across all tenants")

    # Job metrics
    total_jobs: int = Field(..., description="Total extraction jobs")
    completed_jobs: int = Field(..., description="Completed extraction jobs")
    failed_jobs: int = Field(..., description="Failed extraction jobs")
    jobs_24h: int = Field(..., description="Jobs created in last 24 hours")

    # Document metrics
    total_documents: int = Field(..., description="Total documents uploaded")
    total_pages: int = Field(..., description="Total pages processed")

    # Token metrics
    total_tokens: int = Field(..., description="Total tokens consumed")
    total_input_tokens: int = Field(..., description="Total input tokens")
    total_output_tokens: int = Field(..., description="Total output tokens")

    # Financial metrics
    estimated_total_cost: float = Field(..., description="Estimated total cost (USD)")
    total_credits_purchased: int = Field(..., description="Total credits purchased")
    total_credits_consumed: int = Field(..., description="Total credits consumed")

    # API Token metrics
    total_api_tokens: int = Field(..., description="Total active API tokens")

    class Config:
        """Pydantic config."""
        from_attributes = True


# ============================================================================
# Tenant Schemas
# ============================================================================

class TenantListItem(BaseModel):
    """Tenant list item with aggregated metrics."""

    # Basic info
    id: UUID
    name: str
    slug: str
    status: str
    subscription_plan: str

    # Metrics
    user_count: int = Field(..., description="Number of users")
    document_count: int = Field(..., description="Number of documents")
    job_count: int = Field(..., description="Total number of jobs")
    completed_jobs: int = Field(..., description="Completed jobs")
    failed_jobs: int = Field(..., description="Failed jobs")

    # Financial
    credit_balance: int = Field(..., validation_alias="cached_balance", serialization_alias="credit_balance", description="Current credit balance")
    total_credits_consumed: int = Field(0, description="Total credits consumed")

    # Timestamps
    created_at: datetime
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")

    class Config:
        """Pydantic config."""
        from_attributes = True
        populate_by_name = True


class TenantListResponse(BaseModel):
    """Paginated tenant list response."""

    tenants: List[TenantListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class TenantSubscriptionInfo(BaseModel):
    """Tenant subscription information."""

    plan: str
    status: str
    stripe_subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    features: Dict[str, Any] = {}

    class Config:
        """Pydantic config."""
        from_attributes = True


class TenantMetrics(BaseModel):
    """Tenant-specific metrics summary."""

    # Job metrics
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    pending_jobs: int

    # Document metrics
    total_documents: int
    total_pages: int

    # Token metrics
    total_tokens: int
    total_input_tokens: int
    total_output_tokens: int

    # Financial metrics
    estimated_cost: float
    credit_balance: int
    credits_consumed: int


class TenantDetailResponse(BaseModel):
    """Detailed tenant information with relationships."""

    tenant: TenantListItem
    subscription: Optional[TenantSubscriptionInfo] = None
    metrics: TenantMetrics
    user_count: int
    api_token_count: int


# ============================================================================
# User Schemas
# ============================================================================

class UserListItem(BaseModel):
    """User list item with tenant and role information."""

    # User info
    id: UUID
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_verified: bool

    # Tenant info
    tenant_id: UUID
    tenant_name: str
    tenant_status: str

    # Role info
    role_id: UUID
    role_name: str
    role_display_name: str

    # Activity
    last_login: Optional[datetime] = None
    created_at: datetime

    # API tokens
    api_token_count: int = Field(0, description="Number of active API tokens")

    class Config:
        """Pydantic config."""
        from_attributes = True


class UserListResponse(BaseModel):
    """Paginated user list response."""

    users: List[UserListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserDetailResponse(BaseModel):
    """Detailed user information."""

    user: UserListItem
    permissions: List[str] = Field([], description="List of permission names")
    recent_activity: Dict[str, Any] = Field({}, description="Recent activity metrics")


# ============================================================================
# API Token Schemas
# ============================================================================

class ApiTokenListItem(BaseModel):
    """API token list item."""

    id: UUID
    name: str
    token_prefix: str
    scopes: List[str]
    is_active: bool
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    last_used_ip: Optional[str] = None
    created_at: datetime

    # Owner info
    user_id: UUID
    user_email: str
    tenant_id: UUID
    tenant_name: str

    class Config:
        """Pydantic config."""
        from_attributes = True


class ApiTokenListResponse(BaseModel):
    """API token list response."""

    tokens: List[ApiTokenListItem]
    total: int


# ============================================================================
# Audit Log Schemas
# ============================================================================

class AuditLogEntry(BaseModel):
    """Admin audit log entry."""

    id: UUID
    user_id: UUID
    user_email: str
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None
    endpoint: str
    method: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime

    class Config:
        """Pydantic config."""
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Paginated audit log list response."""

    logs: List[AuditLogEntry]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Admin Action Schemas (Write Operations)
# ============================================================================

class UpdateTenantStatusRequest(BaseModel):
    """Request to update tenant status."""

    status: str = Field(..., description="New status (active, suspended, cancelled)")
    reason: Optional[str] = Field(None, description="Reason for status change")

    class Config:
        """Pydantic config."""
        schema_extra = {
            "example": {
                "status": "suspended",
                "reason": "Payment overdue"
            }
        }


class UpdateUserStatusRequest(BaseModel):
    """Request to update user status."""

    is_active: bool = Field(..., description="Active status")
    reason: Optional[str] = Field(None, description="Reason for status change")

    class Config:
        """Pydantic config."""
        schema_extra = {
            "example": {
                "is_active": False,
                "reason": "Terms of service violation"
            }
        }


class RevokeApiTokenRequest(BaseModel):
    """Request to revoke an API token."""

    reason: Optional[str] = Field(None, description="Reason for revocation")

    class Config:
        """Pydantic config."""
        schema_extra = {
            "example": {
                "reason": "Security incident - potential compromise"
            }
        }


class AddTenantCreditsRequest(BaseModel):
    """Request to manually add credits to a tenant."""

    amount: int = Field(..., gt=0, description="Number of credits to add (must be positive)")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for credit addition")

    class Config:
        """Pydantic config."""
        schema_extra = {
            "example": {
                "amount": 1000,
                "reason": "Compensation for service downtime"
            }
        }


# ============================================================================
# Platform Settings Schemas
# ============================================================================

class PlatformSettingResponse(BaseModel):
    """Platform setting response."""

    key: str
    value: Any = Field(..., description="Setting value (JSONB)")
    description: Optional[str] = None
    category: str
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""
        from_attributes = True


class PlatformSettingsListResponse(BaseModel):
    """List of platform settings."""

    settings: List[PlatformSettingResponse]
    total: int


class UpdatePlatformSettingRequest(BaseModel):
    """Request to update a platform setting with validation."""

    value: Any = Field(..., description="New setting value")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description update")

    @validator('value')
    def validate_value(cls, v):
        """
        Defense-in-depth: validate common value types.

        Note: Full validation is done in PlatformSettingsService,
        but this provides early validation for common cases.
        """
        # Validate integer values are non-negative
        if isinstance(v, int) and v < 0:
            raise ValueError("Integer values must be non-negative")

        # Validate string values have reasonable length
        if isinstance(v, str) and len(v) > 10000:
            raise ValueError("String values cannot exceed 10,000 characters")

        return v

    class Config:
        """Pydantic config."""
        schema_extra = {
            "example": {
                "value": 50,
                "description": "Trial credits amount for new tenants"
            }
        }


# ============================================================================
# Top Tenants / Analytics Schemas
# ============================================================================

class TopTenantItem(BaseModel):
    """Top tenant by activity."""

    id: UUID
    name: str
    slug: str
    subscription_plan: str

    # Activity metrics
    job_count: int = Field(..., description="Number of jobs in period")
    total_tokens: int = Field(..., description="Total tokens consumed")
    estimated_cost: float = Field(..., description="Estimated cost")
    user_count: int = Field(..., description="Number of users")

    # Timestamps
    created_at: datetime
    last_activity: Optional[datetime] = None

    class Config:
        """Pydantic config."""
        from_attributes = True


class TopTenantsResponse(BaseModel):
    """Top tenants by activity response."""

    tenants: List[TopTenantItem]
    period_days: int = Field(..., description="Number of days in the analysis period")


# ============================================================================
# Generic Response Schemas
# ============================================================================

class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Generic error response."""

    success: bool = False
    error: str
    detail: Optional[str] = None
