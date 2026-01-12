"""Platform API endpoints for external application integration.

This module provides APIs for external applications to manage tenants, users,
API tokens, and credits programmatically using Platform API keys (pk_live_).
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Tenant, User, Role, ApiToken
from app.models.platform_application import PlatformApplication
from app.models.platform_api_key import PlatformApiKey
from app.models.enums import CreditTransactionType, ReferenceType
from app.services.auth_service import AuthService
from app.services.credit_service import CreditService
from app.services.api_token_service import ApiTokenService
from app.services.permission_service import PermissionService
from app.dependencies.platform_auth import (
    require_platform_scope,
    log_platform_action,
    PlatformAuthError,
    PlatformForbiddenError,
)
from app.schemas.platform import (
    CreateTenantRequest,
    UpdateTenantRequest,
    CreateUserInTenantRequest,
    UpdateUserRequest,
    CreateApiTokenForUserRequest,
    AddCreditsRequest,
    TenantResponse,
    TenantCreatedResponse,
    UserResponse,
    UserCreatedResponse,
    ApiTokenResponse,
    ApiTokenCreatedResponse,
    CreditBalanceResponse,
    CreditTransactionResponse,
    TenantListResponse,
    UserListResponse,
    ApiTokenListResponse,
)


router = APIRouter(prefix="/platform/v1", tags=["Platform API"])

auth_service = AuthService()


# =============================================================================
# Tenant Endpoints
# =============================================================================

@router.post("/tenants", response_model=TenantCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: Request,
    data: CreateTenantRequest,
    app_info: Tuple[PlatformApplication, PlatformApiKey] = Depends(
        require_platform_scope("tenants:create")
    ),
    db: Session = Depends(get_db),
):
    """
    Create a new tenant.

    This endpoint creates a new tenant with optional initial credits.
    A slug is auto-generated from the name if not provided.

    Required scope: tenants:create
    """
    application, api_key = app_info

    # Generate slug if not provided
    slug = data.slug
    if not slug:
        slug = _generate_slug(data.name)

    # Check slug uniqueness
    existing = db.query(Tenant).filter(Tenant.slug == slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant with slug '{slug}' already exists"
        )

    # Create tenant
    tenant = Tenant(
        name=data.name,
        slug=slug,
        status="active",
        subscription_plan=data.subscription_plan or "free",
        tenant_metadata=data.metadata or {},
        cached_balance=0,
    )
    db.add(tenant)
    db.flush()

    # Add initial credits if specified
    if data.initial_credits and data.initial_credits > 0:
        credit_service = CreditService(db)
        credit_service.add_credits(
            tenant_id=tenant.id,
            amount=data.initial_credits,
            transaction_type=CreditTransactionType.ADMIN_ADJUSTMENT.value,
            reference_type=ReferenceType.ADMIN_MANUAL_ADJUSTMENT.value,
            description=f"Initial credits via Platform API (app: {application.slug})",
        )

    db.commit()
    db.refresh(tenant)

    # Log audit
    await log_platform_action(
        db=db,
        request=request,
        action="tenant_created",
        resource_type="tenant",
        resource_id=tenant.id,
        status_code=201,
        metadata={"tenant_slug": slug, "initial_credits": data.initial_credits},
    )

    # Build response
    user_count = db.query(User).filter(User.tenant_id == tenant.id).count()

    return TenantCreatedResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        status=tenant.status,
        subscription_plan=tenant.subscription_plan,
        credit_balance=tenant.cached_balance,
        user_count=user_count,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        metadata=tenant.tenant_metadata,
    )


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    app_info: Tuple[PlatformApplication, PlatformApiKey] = Depends(
        require_platform_scope("tenants:read")
    ),
    db: Session = Depends(get_db),
):
    """
    Get tenant details.

    Required scope: tenants:read
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    user_count = db.query(User).filter(User.tenant_id == tenant.id).count()

    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        status=tenant.status,
        subscription_plan=tenant.subscription_plan,
        credit_balance=tenant.cached_balance,
        user_count=user_count,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        metadata=tenant.tenant_metadata,
    )


@router.patch("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    request: Request,
    tenant_id: UUID,
    data: UpdateTenantRequest,
    app_info: Tuple[PlatformApplication, PlatformApiKey] = Depends(
        require_platform_scope("tenants:update")
    ),
    db: Session = Depends(get_db),
):
    """
    Update a tenant.

    Required scope: tenants:update
    """
    application, api_key = app_info

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    # Update fields
    if data.name is not None:
        tenant.name = data.name
    if data.status is not None:
        tenant.status = data.status
    if data.subscription_plan is not None:
        tenant.subscription_plan = data.subscription_plan
    if data.metadata is not None:
        tenant.tenant_metadata = data.metadata

    tenant.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(tenant)

    # Log audit
    await log_platform_action(
        db=db,
        request=request,
        action="tenant_updated",
        resource_type="tenant",
        resource_id=tenant.id,
        status_code=200,
    )

    user_count = db.query(User).filter(User.tenant_id == tenant.id).count()

    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        status=tenant.status,
        subscription_plan=tenant.subscription_plan,
        credit_balance=tenant.cached_balance,
        user_count=user_count,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        metadata=tenant.tenant_metadata,
    )


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    request: Request,
    tenant_id: UUID,
    app_info: Tuple[PlatformApplication, PlatformApiKey] = Depends(
        require_platform_scope("tenants:delete")
    ),
    db: Session = Depends(get_db),
):
    """
    Deactivate a tenant (soft delete).

    Required scope: tenants:delete
    """
    application, api_key = app_info

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    tenant.status = "cancelled"
    tenant.updated_at = datetime.utcnow()
    db.commit()

    # Log audit
    await log_platform_action(
        db=db,
        request=request,
        action="tenant_deleted",
        resource_type="tenant",
        resource_id=tenant.id,
        status_code=204,
    )


# =============================================================================
# User Endpoints
# =============================================================================

@router.post(
    "/tenants/{tenant_id}/users",
    response_model=UserCreatedResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_user_in_tenant(
    request: Request,
    tenant_id: UUID,
    data: CreateUserInTenantRequest,
    app_info: Tuple[PlatformApplication, PlatformApiKey] = Depends(
        require_platform_scope("users:create")
    ),
    db: Session = Depends(get_db),
):
    """
    Create a user in a tenant.

    If send_invitation is True, an invitation token is generated.
    If send_invitation is False, a password must be provided.

    Required scope: users:create
    """
    application, api_key = app_info

    # Verify tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    # Check email uniqueness
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )

    # Get role
    role = db.query(Role).filter(Role.name == data.role).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {data.role}"
        )

    # Create user
    invitation_token = None

    if data.send_invitation:
        # Generate invitation token
        invitation_token = auth_service.generate_verification_token()
        hashed_password = auth_service.hash_password(uuid4().hex)  # Placeholder
        is_active = False
        is_verified = False
        invitation_expires = datetime.utcnow() + timedelta(days=7)
    else:
        # Use provided password
        if not data.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required when send_invitation is False"
            )
        hashed_password = auth_service.hash_password(data.password)
        # Note: We intentionally do NOT return the password in the response
        # for security reasons (log exposure risk). Caller already knows it.
        is_active = True
        is_verified = True
        invitation_expires = None

    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hashed_password,
        tenant_id=tenant_id,
        role_id=role.id,
        is_active=is_active,
        is_verified=is_verified,
        email_verification_token=invitation_token,
        invitation_expires=invitation_expires,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Log audit
    await log_platform_action(
        db=db,
        request=request,
        action="user_created",
        resource_type="user",
        resource_id=user.id,
        status_code=201,
        metadata={"tenant_id": str(tenant_id), "role": data.role},
    )

    return UserCreatedResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role_name=role.name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        invitation_token=invitation_token,
    )


@router.get("/tenants/{tenant_id}/users", response_model=UserListResponse)
async def list_tenant_users(
    tenant_id: UUID,
    app_info: Tuple[PlatformApplication, PlatformApiKey] = Depends(
        require_platform_scope("users:read")
    ),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    is_active: Optional[bool] = None,
):
    """
    List users in a tenant.

    Required scope: users:read
    """
    # Verify tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    query = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.tenant_id == tenant_id)
    )

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()

    return UserListResponse(
        total=total,
        limit=limit,
        offset=offset,
        users=[
            UserResponse(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                role_name=u.role.name if u.role else "unknown",
                is_active=u.is_active,
                is_verified=u.is_verified,
                created_at=u.created_at,
                last_login=u.last_login,
            )
            for u in users
        ],
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    app_info: Tuple[PlatformApplication, PlatformApiKey] = Depends(
        require_platform_scope("users:read")
    ),
    db: Session = Depends(get_db),
):
    """
    Get user details.

    Required scope: users:read
    """
    user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.id == user_id)
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role_name=user.role.name if user.role else "unknown",
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        last_login=user.last_login,
    )


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    request: Request,
    user_id: UUID,
    data: UpdateUserRequest,
    app_info: Tuple[PlatformApplication, PlatformApiKey] = Depends(
        require_platform_scope("users:update")
    ),
    db: Session = Depends(get_db),
):
    """
    Update a user.

    Required scope: users:update
    """
    application, api_key = app_info

    user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.id == user_id)
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if data.full_name is not None:
        user.full_name = data.full_name

    if data.role is not None:
        role = db.query(Role).filter(Role.name == data.role).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {data.role}"
            )
        user.role_id = role.id

    if data.is_active is not None:
        user.is_active = data.is_active

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    # Log audit
    await log_platform_action(
        db=db,
        request=request,
        action="user_updated",
        resource_type="user",
        resource_id=user.id,
        status_code=200,
    )

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role_name=user.role.name if user.role else "unknown",
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        last_login=user.last_login,
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    request: Request,
    user_id: UUID,
    app_info: Tuple[PlatformApplication, PlatformApiKey] = Depends(
        require_platform_scope("users:delete")
    ),
    db: Session = Depends(get_db),
):
    """
    Deactivate a user (soft delete).

    Required scope: users:delete
    """
    application, api_key = app_info

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.commit()

    # Log audit
    await log_platform_action(
        db=db,
        request=request,
        action="user_deleted",
        resource_type="user",
        resource_id=user.id,
        status_code=204,
    )


# =============================================================================
# Token Endpoints
# =============================================================================

@router.post(
    "/users/{user_id}/tokens",
    response_model=ApiTokenCreatedResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_token_for_user(
    request: Request,
    user_id: UUID,
    data: CreateApiTokenForUserRequest,
    app_info: Tuple[PlatformApplication, PlatformApiKey] = Depends(
        require_platform_scope("tokens:create")
    ),
    db: Session = Depends(get_db),
):
    """
    Create an API token for a user.

    Required scope: tokens:create
    """
    application, api_key = app_info

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get user's available permissions to validate requested scopes
    permission_service = PermissionService(db)
    user_permissions = permission_service.get_user_permissions(user)

    # Validate requested scopes against user's permissions
    for scope in data.scopes:
        if scope not in user_permissions:
            # Check for wildcard
            resource = scope.split(':')[0]
            wildcard = f"{resource}:*"
            if wildcard not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User does not have permission: {scope}"
                )

    # Generate token
    full_token, token_hash, token_prefix = ApiTokenService.generate_token()

    # Calculate expiration
    expires_at = None
    if data.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=data.expires_in_days)

    api_token = ApiToken(
        user_id=user.id,
        tenant_id=user.tenant_id,
        name=data.name,
        token_hash=token_hash,
        token_prefix=token_prefix,
        scopes=data.scopes,
        expires_at=expires_at,
        is_active=True,
    )
    db.add(api_token)
    db.commit()
    db.refresh(api_token)

    # Log audit
    await log_platform_action(
        db=db,
        request=request,
        action="token_created",
        resource_type="api_token",
        resource_id=api_token.id,
        status_code=201,
        metadata={"user_id": str(user_id), "scopes": data.scopes},
    )

    return ApiTokenCreatedResponse(
        id=api_token.id,
        name=api_token.name,
        token_prefix=api_token.token_prefix,
        scopes=api_token.scopes,
        expires_at=api_token.expires_at,
        created_at=api_token.created_at,
        is_active=api_token.is_active,
        token=full_token,
    )


@router.get("/users/{user_id}/tokens", response_model=ApiTokenListResponse)
async def list_user_tokens(
    user_id: UUID,
    app_info: Tuple[PlatformApplication, PlatformApiKey] = Depends(
        require_platform_scope("tokens:read")
    ),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    is_active: Optional[bool] = None,
):
    """
    List API tokens for a user.

    Required scope: tokens:read
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    query = db.query(ApiToken).filter(ApiToken.user_id == user_id)

    if is_active is not None:
        query = query.filter(ApiToken.is_active == is_active)

    total = query.count()
    tokens = query.order_by(ApiToken.created_at.desc()).offset(offset).limit(limit).all()

    return ApiTokenListResponse(
        total=total,
        limit=limit,
        offset=offset,
        tokens=[
            ApiTokenResponse(
                id=t.id,
                name=t.name,
                token_prefix=t.token_prefix,
                scopes=t.scopes,
                expires_at=t.expires_at,
                created_at=t.created_at,
                last_used_at=t.last_used_at,
                is_active=t.is_active,
            )
            for t in tokens
        ],
    )


@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(
    request: Request,
    token_id: UUID,
    app_info: Tuple[PlatformApplication, PlatformApiKey] = Depends(
        require_platform_scope("tokens:revoke")
    ),
    db: Session = Depends(get_db),
):
    """
    Revoke an API token.

    Required scope: tokens:revoke
    """
    application, api_key = app_info

    token = db.query(ApiToken).filter(ApiToken.id == token_id).first()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )

    token.is_active = False
    token.revoked_at = datetime.utcnow()
    db.commit()

    # Log audit
    await log_platform_action(
        db=db,
        request=request,
        action="token_revoked",
        resource_type="api_token",
        resource_id=token.id,
        status_code=204,
    )


# =============================================================================
# Credit Endpoints
# =============================================================================

@router.post(
    "/tenants/{tenant_id}/credits",
    response_model=CreditTransactionResponse,
    status_code=status.HTTP_201_CREATED
)
async def add_credits_to_tenant(
    request: Request,
    tenant_id: UUID,
    data: AddCreditsRequest,
    app_info: Tuple[PlatformApplication, PlatformApiKey] = Depends(
        require_platform_scope("credits:add")
    ),
    db: Session = Depends(get_db),
):
    """
    Add credits to a tenant.

    Required scope: credits:add
    """
    application, api_key = app_info

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    credit_service = CreditService(db)
    transaction = credit_service.add_credits(
        tenant_id=tenant_id,
        amount=data.amount,
        transaction_type=CreditTransactionType.ADMIN_ADJUSTMENT.value,
        reference_type=ReferenceType.ADMIN_MANUAL_ADJUSTMENT.value,
        description=f"{data.description} (via Platform API, app: {application.slug})",
    )

    # Log audit
    await log_platform_action(
        db=db,
        request=request,
        action="credits_added",
        resource_type="tenant",
        resource_id=tenant_id,
        status_code=201,
        metadata={"amount": data.amount, "description": data.description},
    )

    return CreditTransactionResponse(
        id=transaction.id,
        amount=transaction.amount,
        transaction_type=transaction.transaction_type,
        description=transaction.description,
        created_at=transaction.created_at,
    )


@router.get("/tenants/{tenant_id}/credits", response_model=CreditBalanceResponse)
async def get_credit_balance(
    tenant_id: UUID,
    app_info: Tuple[PlatformApplication, PlatformApiKey] = Depends(
        require_platform_scope("credits:read")
    ),
    db: Session = Depends(get_db),
):
    """
    Get tenant credit balance.

    Required scope: credits:read
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    return CreditBalanceResponse(
        tenant_id=tenant.id,
        balance=tenant.cached_balance,
        last_updated=tenant.balance_last_updated or tenant.updated_at,
    )


# =============================================================================
# Helper Functions
# =============================================================================

def _generate_slug(name: str) -> str:
    """Generate a URL-safe slug from a name."""
    # Convert to lowercase
    slug = name.lower()
    # Replace spaces and special chars with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    # Ensure minimum length
    if len(slug) < 3:
        slug = f"{slug}-org"
    # Add random suffix for uniqueness
    suffix = uuid4().hex[:6]
    return f"{slug}-{suffix}"
