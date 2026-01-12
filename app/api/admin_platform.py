"""Admin endpoints for managing Platform Applications and API keys.

These endpoints are for super admins to manage platform applications
that integrate with the Platform API.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.platform_application import PlatformApplication
from app.models.platform_api_key import PlatformApiKey
from app.models.platform_audit_log import PlatformAuditLog
from app.dependencies.auth import require_super_admin
from app.services.platform_application_service import PlatformApplicationService
from app.schemas.platform import (
    CreatePlatformApplicationRequest,
    UpdatePlatformApplicationRequest,
    CreatePlatformApiKeyRequest,
    PlatformApplicationResponse,
    PlatformApplicationCreatedResponse,
    PlatformApiKeyResponse,
    PlatformApiKeyCreatedResponse,
    PlatformAuditLogResponse,
    PlatformApplicationListResponse,
    PlatformAuditLogListResponse,
)


router = APIRouter(prefix="/admin/platform", tags=["Admin - Platform"])


# =============================================================================
# Platform Application Endpoints
# =============================================================================

@router.post(
    "/applications",
    response_model=PlatformApplicationCreatedResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_platform_application(
    data: CreatePlatformApplicationRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Register a new platform application.

    This creates a new application with an initial API key that has all scopes.
    The API key is returned only once and should be stored securely.

    Requires: Super Admin
    """
    service = PlatformApplicationService(db)

    try:
        application, initial_key = service.create_application(
            name=data.name,
            slug=data.slug,
            description=data.description,
            webhook_url=data.webhook_url,
            allowed_ips=data.allowed_ips,
            rate_limit_per_minute=data.rate_limit_per_minute,
            rate_limit_per_hour=data.rate_limit_per_hour,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Get API key count
    api_key_count = db.query(PlatformApiKey).filter(
        PlatformApiKey.application_id == application.id,
        PlatformApiKey.is_active == True
    ).count()

    return PlatformApplicationCreatedResponse(
        id=application.id,
        name=application.name,
        slug=application.slug,
        description=application.description,
        webhook_url=application.webhook_url,
        allowed_ips=application.allowed_ips,
        rate_limit_per_minute=application.rate_limit_per_minute,
        rate_limit_per_hour=application.rate_limit_per_hour,
        is_active=application.is_active,
        created_at=application.created_at,
        updated_at=application.updated_at,
        api_key_count=api_key_count,
        initial_api_key=initial_key,
    )


@router.get("/applications", response_model=PlatformApplicationListResponse)
async def list_platform_applications(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    is_active: Optional[bool] = None,
):
    """
    List all platform applications.

    Requires: Super Admin
    """
    # Create subquery for API key counts to avoid N+1 query problem
    api_key_counts = (
        db.query(
            PlatformApiKey.application_id,
            func.count(PlatformApiKey.id).label('key_count')
        )
        .filter(PlatformApiKey.is_active == True)
        .group_by(PlatformApiKey.application_id)
        .subquery()
    )

    # Build base query with optional filtering
    base_query = db.query(PlatformApplication)
    if is_active is not None:
        base_query = base_query.filter(PlatformApplication.is_active == is_active)

    # Get total count before pagination
    total = base_query.count()

    # Join with API key counts and apply pagination
    query = (
        db.query(PlatformApplication, api_key_counts.c.key_count)
        .outerjoin(
            api_key_counts,
            PlatformApplication.id == api_key_counts.c.application_id
        )
    )
    if is_active is not None:
        query = query.filter(PlatformApplication.is_active == is_active)

    results = (
        query
        .order_by(PlatformApplication.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Build response using joined key_count (defaults to 0 if no keys)
    app_responses = [
        PlatformApplicationResponse(
            id=app.id,
            name=app.name,
            slug=app.slug,
            description=app.description,
            webhook_url=app.webhook_url,
            allowed_ips=app.allowed_ips,
            rate_limit_per_minute=app.rate_limit_per_minute,
            rate_limit_per_hour=app.rate_limit_per_hour,
            is_active=app.is_active,
            created_at=app.created_at,
            updated_at=app.updated_at,
            api_key_count=key_count or 0,
        )
        for app, key_count in results
    ]

    return PlatformApplicationListResponse(
        total=total,
        limit=limit,
        offset=offset,
        applications=app_responses,
    )


@router.get("/applications/{application_id}", response_model=PlatformApplicationResponse)
async def get_platform_application(
    application_id: UUID,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Get platform application details.

    Requires: Super Admin
    """
    service = PlatformApplicationService(db)
    application = service.get_application_by_id(application_id)

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform application not found"
        )

    api_key_count = db.query(PlatformApiKey).filter(
        PlatformApiKey.application_id == application.id,
        PlatformApiKey.is_active == True
    ).count()

    return PlatformApplicationResponse(
        id=application.id,
        name=application.name,
        slug=application.slug,
        description=application.description,
        webhook_url=application.webhook_url,
        allowed_ips=application.allowed_ips,
        rate_limit_per_minute=application.rate_limit_per_minute,
        rate_limit_per_hour=application.rate_limit_per_hour,
        is_active=application.is_active,
        created_at=application.created_at,
        updated_at=application.updated_at,
        api_key_count=api_key_count,
    )


@router.patch("/applications/{application_id}", response_model=PlatformApplicationResponse)
async def update_platform_application(
    application_id: UUID,
    data: UpdatePlatformApplicationRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Update a platform application.

    Requires: Super Admin
    """
    service = PlatformApplicationService(db)

    try:
        application = service.update_application(
            application_id=application_id,
            name=data.name,
            description=data.description,
            webhook_url=data.webhook_url,
            allowed_ips=data.allowed_ips,
            rate_limit_per_minute=data.rate_limit_per_minute,
            rate_limit_per_hour=data.rate_limit_per_hour,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform application not found"
        )

    api_key_count = db.query(PlatformApiKey).filter(
        PlatformApiKey.application_id == application.id,
        PlatformApiKey.is_active == True
    ).count()

    return PlatformApplicationResponse(
        id=application.id,
        name=application.name,
        slug=application.slug,
        description=application.description,
        webhook_url=application.webhook_url,
        allowed_ips=application.allowed_ips,
        rate_limit_per_minute=application.rate_limit_per_minute,
        rate_limit_per_hour=application.rate_limit_per_hour,
        is_active=application.is_active,
        created_at=application.created_at,
        updated_at=application.updated_at,
        api_key_count=api_key_count,
    )


@router.delete("/applications/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_platform_application(
    application_id: UUID,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Deactivate a platform application.

    This also deactivates all associated API keys.

    Requires: Super Admin
    """
    service = PlatformApplicationService(db)
    application = service.deactivate_application(application_id)

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform application not found"
        )


@router.post("/applications/{application_id}/activate", response_model=PlatformApplicationResponse)
async def activate_platform_application(
    application_id: UUID,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Reactivate a deactivated platform application.

    Note: API keys remain deactivated and must be recreated.

    Requires: Super Admin
    """
    service = PlatformApplicationService(db)
    application = service.activate_application(application_id)

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform application not found"
        )

    api_key_count = db.query(PlatformApiKey).filter(
        PlatformApiKey.application_id == application.id,
        PlatformApiKey.is_active == True
    ).count()

    return PlatformApplicationResponse(
        id=application.id,
        name=application.name,
        slug=application.slug,
        description=application.description,
        webhook_url=application.webhook_url,
        allowed_ips=application.allowed_ips,
        rate_limit_per_minute=application.rate_limit_per_minute,
        rate_limit_per_hour=application.rate_limit_per_hour,
        is_active=application.is_active,
        created_at=application.created_at,
        updated_at=application.updated_at,
        api_key_count=api_key_count,
    )


# =============================================================================
# Platform API Key Endpoints
# =============================================================================

@router.post(
    "/applications/{application_id}/keys",
    response_model=PlatformApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_platform_api_key(
    application_id: UUID,
    data: CreatePlatformApiKeyRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Create a new API key for a platform application.

    The full API key is returned only once and should be stored securely.

    Requires: Super Admin
    """
    service = PlatformApplicationService(db)

    try:
        api_key, full_key = service.create_api_key(
            application_id=application_id,
            name=data.name,
            scopes=data.scopes,
            expires_in_days=data.expires_in_days,
            created_by_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return PlatformApiKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        token_prefix=api_key.token_prefix,
        scopes=api_key.scopes,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        is_active=api_key.is_active,
        token=full_key,
    )


@router.get("/applications/{application_id}/keys", response_model=List[PlatformApiKeyResponse])
async def list_platform_api_keys(
    application_id: UUID,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
    is_active: Optional[bool] = None,
):
    """
    List API keys for a platform application.

    Requires: Super Admin
    """
    service = PlatformApplicationService(db)

    # Verify application exists
    application = service.get_application_by_id(application_id)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform application not found"
        )

    keys = service.list_api_keys(application_id, is_active=is_active)

    return [
        PlatformApiKeyResponse(
            id=k.id,
            name=k.name,
            token_prefix=k.token_prefix,
            scopes=k.scopes,
            expires_at=k.expires_at,
            created_at=k.created_at,
            last_used_at=k.last_used_at,
            is_active=k.is_active,
        )
        for k in keys
    ]


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_platform_api_key(
    key_id: UUID,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Revoke a platform API key.

    Requires: Super Admin
    """
    service = PlatformApplicationService(db)
    api_key = service.revoke_api_key(key_id, revoked_by_user_id=current_user.id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform API key not found"
        )


# =============================================================================
# Audit Log Endpoints
# =============================================================================

@router.get("/audit-logs", response_model=PlatformAuditLogListResponse)
async def list_platform_audit_logs(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    application_id: Optional[UUID] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
):
    """
    List platform audit logs.

    Requires: Super Admin
    """
    query = db.query(PlatformAuditLog)

    if application_id:
        query = query.filter(PlatformAuditLog.application_id == application_id)
    if action:
        query = query.filter(PlatformAuditLog.action == action)
    if resource_type:
        query = query.filter(PlatformAuditLog.resource_type == resource_type)

    total = query.count()
    logs = query.order_by(
        PlatformAuditLog.created_at.desc()
    ).offset(offset).limit(limit).all()

    return PlatformAuditLogListResponse(
        total=total,
        limit=limit,
        offset=offset,
        logs=[
            PlatformAuditLogResponse(
                id=log.id,
                application_id=log.application_id,
                api_key_id=log.api_key_id,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                endpoint=log.endpoint,
                method=log.method,
                ip_address=log.ip_address,
                status_code=log.status_code,
                error_message=log.error_message,
                created_at=log.created_at,
            )
            for log in logs
        ],
    )
