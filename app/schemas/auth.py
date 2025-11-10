"""Authentication-related Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional, Set
from uuid import UUID
import re

from pydantic import BaseModel, Field, field_validator, ConfigDict


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: str = Field(
        ...,
        description="User's email address",
        max_length=255,
        json_schema_extra={"example": "user@example.com"}
    )
    password: str = Field(
        ...,
        description="User's password (min 8 chars, 1 uppercase, 1 number)",
        min_length=8,
        max_length=128,
        json_schema_extra={"example": "SecurePass123"}
    )
    full_name: Optional[str] = Field(
        None,
        description="User's full name",
        max_length=255,
        json_schema_extra={"example": "John Doe"}
    )
    tenant_name: Optional[str] = Field(
        None,
        description="Name for new tenant (if creating organization)",
        max_length=255,
        json_schema_extra={"example": "Acme Corporation"}
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("password")
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
                "email": "user@example.com",
                "password": "SecurePass123",
                "full_name": "John Doe",
                "tenant_name": "Acme Corporation"
            }
        }
    )


class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: str = Field(
        ...,
        description="User's email address",
        max_length=255,
        json_schema_extra={"example": "user@example.com"}
    )
    password: str = Field(
        ...,
        description="User's password",
        max_length=128,
        json_schema_extra={"example": "SecurePass123"}
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123"
            }
        }
    )


class RefreshTokenRequest(BaseModel):
    """Request schema for refreshing access token."""

    refresh_token: str = Field(
        ...,
        description="Valid refresh token",
        json_schema_extra={"example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    )


class LogoutRequest(BaseModel):
    """Request schema for user logout (optional refresh token)."""

    refresh_token: Optional[str] = Field(
        None,
        description="Optional refresh token to invalidate",
        json_schema_extra={"example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    )


class ForgotPasswordRequest(BaseModel):
    """Request schema for initiating password reset."""

    email: str = Field(
        ...,
        description="User's email address",
        max_length=255,
        json_schema_extra={"example": "user@example.com"}
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com"
            }
        }
    )


class ResetPasswordRequest(BaseModel):
    """Request schema for completing password reset."""

    token: str = Field(
        ...,
        description="Password reset token from email",
        json_schema_extra={"example": "a1b2c3d4e5f6..."}
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
                "token": "a1b2c3d4e5f6...",
                "new_password": "NewSecurePass456"
            }
        }
    )


class VerifyEmailRequest(BaseModel):
    """Request schema for email verification."""

    token: str = Field(
        ...,
        description="Email verification token from email",
        json_schema_extra={"example": "a1b2c3d4e5f6..."}
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "a1b2c3d4e5f6..."
            }
        }
    )


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================


class TenantInfo(BaseModel):
    """Tenant information for response payloads."""

    id: UUID = Field(..., description="Tenant unique identifier")
    name: str = Field(..., description="Tenant name")
    slug: str = Field(..., description="Tenant URL slug")
    status: str = Field(..., description="Tenant status (active, suspended, cancelled)")
    subscription_plan: Optional[str] = Field(None, description="Subscription plan")
    credit_balance: int = Field(..., validation_alias="cached_balance", serialization_alias="credit_balance", description="Available credits")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Acme Corporation",
                "slug": "acme-corp",
                "status": "active",
                "subscription_plan": "pro",
                "credit_balance": 1000
            }
        }
    )


class UserInfo(BaseModel):
    """User information for response payloads (excludes sensitive data)."""

    id: UUID = Field(..., description="User unique identifier")
    email: str = Field(..., description="User's email address")
    full_name: Optional[str] = Field(None, description="User's full name")
    is_active: bool = Field(..., description="Whether user is active")
    is_verified: bool = Field(..., description="Whether email is verified")
    locale: str = Field(..., description="User's preferred locale")
    role_id: UUID = Field(..., description="User's role ID")
    tenant_id: UUID = Field(..., description="User's tenant ID")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "email": "user@example.com",
                "full_name": "John Doe",
                "is_active": True,
                "is_verified": True,
                "locale": "en",
                "role_id": "770e8400-e29b-41d4-a716-446655440002",
                "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2025-11-03T10:00:00Z",
                "last_login": "2025-11-03T12:30:00Z"
            }
        }
    )


class TokenResponse(BaseModel):
    """Response schema for token operations."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }
    )


class AuthResponse(BaseModel):
    """Response schema for registration and login."""

    user: UserInfo = Field(..., description="User information")
    tenant: TenantInfo = Field(..., description="Tenant information")
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user": {
                    "id": "660e8400-e29b-41d4-a716-446655440001",
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "is_active": True,
                    "is_verified": False,
                    "locale": "en",
                    "role_id": "770e8400-e29b-41d4-a716-446655440002",
                    "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
                    "created_at": "2025-11-03T10:00:00Z",
                    "last_login": None
                },
                "tenant": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "Acme Corporation",
                    "slug": "acme-corp",
                    "status": "active",
                    "subscription_plan": "free",
                    "credit_balance": 100
                },
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }
    )


class MessageResponse(BaseModel):
    """Generic message response for operations like logout, password reset, etc."""

    message: str = Field(..., description="Response message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Operation completed successfully"
            }
        }
    )


class UserProfileResponse(BaseModel):
    """Response schema for /me endpoint (current user profile)."""

    user: UserInfo = Field(..., description="User information")
    tenant: TenantInfo = Field(..., description="Tenant information")
    permissions: Set[str] = Field(..., description="User's permissions")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user": {
                    "id": "660e8400-e29b-41d4-a716-446655440001",
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "is_active": True,
                    "is_verified": True,
                    "locale": "en",
                    "role_id": "770e8400-e29b-41d4-a716-446655440002",
                    "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
                    "created_at": "2025-11-03T10:00:00Z",
                    "last_login": "2025-11-03T12:30:00Z"
                },
                "tenant": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "Acme Corporation",
                    "slug": "acme-corp",
                    "status": "active",
                    "subscription_plan": "pro",
                    "credit_balance": 1000
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
