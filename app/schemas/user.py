"""User management Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional, Set, List
from uuid import UUID
import re

from pydantic import BaseModel, Field, field_validator, ConfigDict


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================


class ProfileUpdateRequest(BaseModel):
    """Request schema for updating user's own profile."""

    full_name: Optional[str] = Field(
        None,
        description="User's full name",
        max_length=255,
        json_schema_extra={"example": "Jane Smith"}
    )
    avatar_url: Optional[str] = Field(
        None,
        description="URL to user's avatar image",
        max_length=500,
        json_schema_extra={"example": "https://example.com/avatars/jane.jpg"}
    )
    locale: Optional[str] = Field(
        None,
        description="User's preferred locale",
        json_schema_extra={"example": "en"}
    )

    @field_validator("locale")
    @classmethod
    def validate_locale(cls, v: Optional[str]) -> Optional[str]:
        """Validate locale is in supported list."""
        if v is None:
            return v

        supported_locales = ["en", "zh-TW", "zh-CN"]
        if v not in supported_locales:
            raise ValueError(f"Locale must be one of: {', '.join(supported_locales)}")
        return v

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate avatar URL format."""
        if v is None:
            return v

        url_pattern = r'^https?://.+\..+'
        if not re.match(url_pattern, v):
            raise ValueError("Avatar URL must be a valid HTTP(S) URL")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "Jane Smith",
                "avatar_url": "https://example.com/avatars/jane.jpg",
                "locale": "zh-TW"
            }
        }
    )


class PasswordUpdateRequest(BaseModel):
    """Request schema for updating user's password."""

    current_password: str = Field(
        ...,
        description="User's current password for verification",
        max_length=128,
        json_schema_extra={"example": "CurrentPass123"}
    )
    new_password: str = Field(
        ...,
        description="New password (min 8 chars, 1 uppercase, 1 number)",
        min_length=8,
        max_length=128,
        json_schema_extra={"example": "NewSecurePass456"}
    )

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[0-9]', v):
            raise ValueError("Password must contain at least one number")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_password": "CurrentPass123",
                "new_password": "NewSecurePass456"
            }
        }
    )


class UserInviteRequest(BaseModel):
    """Request schema for inviting a new user to the tenant."""

    email: str = Field(
        ...,
        description="Email address of user to invite",
        max_length=255,
        json_schema_extra={"example": "newuser@example.com"}
    )
    role_id: UUID = Field(
        ...,
        description="Role ID to assign to the invited user",
        json_schema_extra={"example": "770e8400-e29b-41d4-a716-446655440002"}
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "newuser@example.com",
                "role_id": "770e8400-e29b-41d4-a716-446655440002"
            }
        }
    )


class UserUpdateRequest(BaseModel):
    """Request schema for updating another user (admin operation)."""

    role_id: Optional[UUID] = Field(
        None,
        description="New role ID for the user",
        json_schema_extra={"example": "770e8400-e29b-41d4-a716-446655440002"}
    )
    is_active: Optional[bool] = Field(
        None,
        description="Whether the user account is active",
        json_schema_extra={"example": True}
    )
    full_name: Optional[str] = Field(
        None,
        description="User's full name",
        max_length=255,
        json_schema_extra={"example": "John Updated"}
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "role_id": "770e8400-e29b-41d4-a716-446655440002",
                "is_active": True,
                "full_name": "John Updated"
            }
        }
    )


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================


class RoleInfo(BaseModel):
    """Role information for response payloads."""

    id: UUID = Field(..., description="Role unique identifier")
    name: str = Field(..., description="Role name")
    display_name: str = Field(..., description="Human-readable role name")
    description: Optional[str] = Field(None, description="Role description")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "770e8400-e29b-41d4-a716-446655440002",
                "name": "member",
                "display_name": "Member",
                "description": "Standard member with basic permissions"
            }
        }
    )


class TenantInfo(BaseModel):
    """Tenant information for response payloads."""

    id: UUID = Field(..., description="Tenant unique identifier")
    name: str = Field(..., description="Tenant name")
    slug: str = Field(..., description="Tenant URL slug")
    status: str = Field(..., description="Tenant status")
    subscription_plan: Optional[str] = Field(None, description="Subscription plan")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Acme Corporation",
                "slug": "acme-corp",
                "status": "active",
                "subscription_plan": "pro"
            }
        }
    )


class UserDetailResponse(BaseModel):
    """Detailed user information with role, tenant, and permissions."""

    id: UUID = Field(..., description="User unique identifier")
    email: str = Field(..., description="User's email address")
    full_name: Optional[str] = Field(None, description="User's full name")
    avatar_url: Optional[str] = Field(None, description="User's avatar URL")
    is_active: bool = Field(..., description="Whether user is active")
    is_verified: bool = Field(..., description="Whether email is verified")
    locale: str = Field(..., description="User's preferred locale")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    created_at: datetime = Field(..., description="Account creation timestamp")
    role: RoleInfo = Field(..., description="User's role")
    tenant: TenantInfo = Field(..., description="User's tenant")
    permissions: Set[str] = Field(..., description="User's permissions")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "email": "user@example.com",
                "full_name": "John Doe",
                "avatar_url": "https://example.com/avatars/john.jpg",
                "is_active": True,
                "is_verified": True,
                "locale": "en",
                "last_login": "2025-11-03T12:30:00Z",
                "created_at": "2025-11-03T10:00:00Z",
                "role": {
                    "id": "770e8400-e29b-41d4-a716-446655440002",
                    "name": "member",
                    "display_name": "Member",
                    "description": "Standard member"
                },
                "tenant": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "Acme Corporation",
                    "slug": "acme-corp",
                    "status": "active",
                    "subscription_plan": "pro"
                },
                "permissions": [
                    "documents:create",
                    "documents:read",
                    "schemas:create",
                    "schemas:read"
                ]
            }
        }
    )


class UserListItemResponse(BaseModel):
    """Simplified user information for list responses."""

    id: UUID = Field(..., description="User unique identifier")
    email: str = Field(..., description="User's email address")
    full_name: Optional[str] = Field(None, description="User's full name")
    avatar_url: Optional[str] = Field(None, description="User's avatar URL")
    is_active: bool = Field(..., description="Whether user is active")
    is_verified: bool = Field(..., description="Whether email is verified")
    role: RoleInfo = Field(..., description="User's role")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "email": "user@example.com",
                "full_name": "John Doe",
                "avatar_url": "https://example.com/avatars/john.jpg",
                "is_active": True,
                "is_verified": True,
                "role": {
                    "id": "770e8400-e29b-41d4-a716-446655440002",
                    "name": "member",
                    "display_name": "Member",
                    "description": "Standard member"
                },
                "last_login": "2025-11-03T12:30:00Z",
                "created_at": "2025-11-03T10:00:00Z"
            }
        }
    )


class UserListResponse(BaseModel):
    """Paginated list of users."""

    users: List[UserListItemResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users matching filters")
    limit: int = Field(..., description="Number of users per page")
    offset: int = Field(..., description="Number of users skipped")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "users": [
                    {
                        "id": "660e8400-e29b-41d4-a716-446655440001",
                        "email": "user1@example.com",
                        "full_name": "User One",
                        "avatar_url": None,
                        "is_active": True,
                        "is_verified": True,
                        "role": {
                            "id": "770e8400-e29b-41d4-a716-446655440002",
                            "name": "member",
                            "display_name": "Member",
                            "description": "Standard member"
                        },
                        "last_login": "2025-11-03T12:30:00Z",
                        "created_at": "2025-11-03T10:00:00Z"
                    }
                ],
                "total": 15,
                "limit": 50,
                "offset": 0
            }
        }
    )


class InvitationResponse(BaseModel):
    """Response for user invitation."""

    message: str = Field(..., description="Success message")
    invitation_token: str = Field(..., description="Invitation token to send to user")
    email: str = Field(..., description="Email address invited")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Invitation sent successfully",
                "invitation_token": "a1b2c3d4e5f6...",
                "email": "newuser@example.com"
            }
        }
    )


class InvitationListItem(BaseModel):
    """Individual pending invitation item for list response."""

    id: UUID = Field(..., description="User ID of the pending invitation")
    email: str = Field(..., description="Email address invited")
    role: str = Field(..., description="Role name assigned to the invitation (e.g., 'admin', 'member')")
    created_at: datetime = Field(..., description="When the invitation was created")
    expires_at: datetime = Field(..., description="When the invitation expires (created_at + 7 days)")
    status: str = Field(default="pending", description="Invitation status (always 'pending' for this list)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "email": "newuser@example.com",
                "role": "member",
                "created_at": "2025-11-03T10:00:00Z",
                "expires_at": "2025-11-10T10:00:00Z",
                "status": "pending"
            }
        }
    )


class InvitationListResponse(BaseModel):
    """Response for listing pending invitations."""

    invitations: List[InvitationListItem] = Field(..., description="List of pending invitations")
    total: int = Field(..., description="Total number of pending invitations")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "invitations": [
                    {
                        "id": "660e8400-e29b-41d4-a716-446655440001",
                        "email": "newuser@example.com",
                        "role": "member",
                        "created_at": "2025-11-03T10:00:00Z",
                        "expires_at": "2025-11-10T10:00:00Z",
                        "status": "pending"
                    }
                ],
                "total": 1
            }
        }
    )
