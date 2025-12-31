"""Admin API endpoints for super admin panel."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_super_admin
from app.models import User
from app.models.admin_audit_log import AdminAuditLog
from app.services.admin_metrics_service import AdminMetricsService
from app.services.tenant_management_service import TenantManagementService
from app.services.admin_user_service import AdminUserService
from app.services.platform_settings_service import PlatformSettingsService
from app.services.credit_service import CreditService
from app.schemas.admin import (
    PlatformStatistics,
    TenantListResponse,
    TenantDetailResponse,
    TopTenantsResponse,
    UserListResponse,
    UserDetailResponse,
    ApiTokenListResponse,
    UpdateTenantStatusRequest,
    UpdateUserStatusRequest,
    RevokeApiTokenRequest,
    AddTenantCreditsRequest,
    PlatformSettingsListResponse,
    PlatformSettingResponse,
    UpdatePlatformSettingRequest,
    SuccessResponse,
    # Model Pricing
    CreateModelPricingRequest,
    DeactivatePricingRequest,
    ModelPricingResponse,
    ModelPricingListResponse,
    ModelPricingHistoryResponse,
    SupportedModelsResponse,
)
from app.exceptions.auth import AuthorizationError

router = APIRouter(prefix="/admin")


# ============================================================================
# Platform Overview & Dashboard
# ============================================================================

@router.get("/dashboard", response_model=PlatformStatistics)
async def get_platform_dashboard(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get platform-wide statistics for super admin dashboard.

    Returns comprehensive metrics including:
    - Tenant metrics (total, active, suspended, new signups)
    - User metrics (total, active)
    - Job metrics (total, completed, failed, recent)
    - Document and page metrics
    - Token consumption metrics
    - Financial metrics (estimated costs, credits)
    - API token metrics

    **Requires:** Super admin access (platform_admin role)

    **Example Response:**
    ```json
    {
        "total_tenants": 45,
        "active_tenants": 42,
        "suspended_tenants": 3,
        "new_tenants_30d": 8,
        "total_users": 234,
        "active_users": 198,
        "total_jobs": 5678,
        "completed_jobs": 5432,
        "failed_jobs": 123,
        "jobs_24h": 89,
        "total_documents": 2345,
        "total_pages": 8901,
        "total_tokens": 12345678,
        "estimated_total_cost": 12345.67,
        "total_api_tokens": 67
    }
    ```
    """
    service = AdminMetricsService(db)
    return service.get_platform_statistics()


# ============================================================================
# Tenant Management
# ============================================================================

@router.get("/tenants", response_model=TenantListResponse)
async def list_tenants(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status (active, suspended, cancelled)"),
    plan: Optional[str] = Query(None, description="Filter by subscription plan (free, starter, pro, enterprise)"),
    search: Optional[str] = Query(None, description="Search by tenant name or slug"),
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    List all tenants with pagination and filtering.

    Returns tenant list with aggregated metrics including user count, job count,
    credit balance, and last activity timestamp.

    **Query Parameters:**
    - `page`: Page number (1-indexed), default 1
    - `page_size`: Items per page (1-100), default 50
    - `status`: Filter by status (active, suspended, cancelled)
    - `plan`: Filter by subscription plan
    - `search`: Search by name or slug

    **Requires:** Super admin access (platform_admin role)

    **Example Response:**
    ```json
    {
        "tenants": [
            {
                "id": "...",
                "name": "Acme Corp",
                "slug": "acme-corp",
                "status": "active",
                "subscription_plan": "pro",
                "user_count": 5,
                "document_count": 120,
                "job_count": 345,
                "completed_jobs": 320,
                "failed_jobs": 12,
                "credit_balance": 5000,
                "created_at": "2025-01-15T10:30:00Z",
                "last_activity": "2025-11-05T14:20:00Z"
            }
        ],
        "total": 45,
        "page": 1,
        "page_size": 50,
        "total_pages": 1
    }
    ```
    """
    service = AdminMetricsService(db)
    tenants, total = service.get_tenant_list_with_metrics(
        page=page,
        page_size=page_size,
        status_filter=status,
        plan_filter=plan,
        search_query=search
    )

    total_pages = (total + page_size - 1) // page_size

    return TenantListResponse(
        tenants=tenants,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/tenants/{tenant_id}", response_model=TenantDetailResponse)
async def get_tenant_details(
    tenant_id: UUID,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get detailed information for a specific tenant.

    Returns comprehensive tenant information including:
    - Basic tenant info
    - Subscription details
    - 30-day metrics (jobs, documents, tokens, costs)
    - User count
    - API token count

    **Requires:** Super admin access (platform_admin role)

    **Raises:**
    - 404: Tenant not found
    """
    service = TenantManagementService(db)
    details = service.get_tenant_details(tenant_id)

    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    return details


@router.get("/tenants/{tenant_id}/users", response_model=list[UserListResponse.model_fields['users'].annotation])
async def get_tenant_users(
    tenant_id: UUID,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get all users for a specific tenant.

    Returns list of users with role information and API token counts.

    **Requires:** Super admin access (platform_admin role)

    **Raises:**
    - 404: Tenant not found
    """
    service = TenantManagementService(db)

    # Verify tenant exists
    tenant = service.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    users = service.get_tenant_users(tenant_id)
    return users


@router.get("/tenants/{tenant_id}/tokens", response_model=ApiTokenListResponse)
async def get_tenant_tokens(
    tenant_id: UUID,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get all active API tokens for a specific tenant.

    Returns list of API tokens with usage information.

    **Requires:** Super admin access (platform_admin role)

    **Raises:**
    - 404: Tenant not found
    """
    service = TenantManagementService(db)

    # Verify tenant exists
    tenant = service.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    tokens = service.get_tenant_tokens(tenant_id)
    return ApiTokenListResponse(tokens=tokens, total=len(tokens))


@router.patch("/tenants/{tenant_id}/status", response_model=SuccessResponse)
async def update_tenant_status(
    tenant_id: UUID,
    request: UpdateTenantStatusRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Update tenant status (suspend/activate/cancel).

    **Write Operation** - Updates tenant status and records reason in audit trail.

    **Request Body:**
    ```json
    {
        "status": "suspended",
        "reason": "Payment overdue"
    }
    ```

    **Valid Statuses:** active, suspended, cancelled

    **Requires:** Super admin access (platform_admin role)

    **Raises:**
    - 400: Invalid status
    - 403: Cannot modify platform tenant
    - 404: Tenant not found
    """
    service = TenantManagementService(db)

    try:
        tenant = service.update_tenant_status(
            tenant_id=tenant_id,
            new_status=request.status,
            reason=request.reason
        )

        return SuccessResponse(
            success=True,
            message=f"Tenant status updated to '{request.status}'",
            data={
                "tenant_id": str(tenant.id),
                "tenant_name": tenant.name,
                "new_status": tenant.status,
                "reason": request.reason
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


# ============================================================================
# User Management
# ============================================================================

@router.get("/users", response_model=UserListResponse)
async def list_all_users(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant ID"),
    role_id: Optional[UUID] = Query(None, description="Filter by role ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by email or name"),
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    List all users across all tenants with pagination and filtering.

    **Query Parameters:**
    - `page`: Page number (1-indexed), default 1
    - `page_size`: Items per page (1-100), default 50
    - `tenant_id`: Filter by tenant
    - `role_id`: Filter by role
    - `is_active`: Filter by active status
    - `search`: Search by email or full name

    **Requires:** Super admin access (platform_admin role)
    """
    service = AdminUserService(db)
    users, total = service.list_all_users(
        page=page,
        page_size=page_size,
        tenant_id_filter=tenant_id,
        role_id_filter=role_id,
        is_active_filter=is_active,
        search_query=search
    )

    total_pages = (total + page_size - 1) // page_size

    return UserListResponse(
        users=users,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user_details(
    user_id: UUID,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get detailed information for a specific user.

    Returns user information including:
    - Basic user info and tenant
    - Role and permissions
    - Recent activity metrics
    - API token count

    **Requires:** Super admin access (platform_admin role)

    **Raises:**
    - 404: User not found
    """
    service = AdminUserService(db)
    details = service.get_user_details(user_id)

    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return details


@router.patch("/users/{user_id}/status", response_model=SuccessResponse)
async def update_user_status(
    user_id: UUID,
    request: UpdateUserStatusRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Activate or deactivate a user account.

    **Write Operation** - Updates user active status.

    **Request Body:**
    ```json
    {
        "is_active": false,
        "reason": "Terms of service violation"
    }
    ```

    **Requires:** Super admin access (platform_admin role)

    **Raises:**
    - 400: User not found
    - 403: Cannot deactivate platform admin users
    - 404: User not found
    """
    service = AdminUserService(db)

    try:
        user = service.update_user_status(
            user_id=user_id,
            is_active=request.is_active,
            reason=request.reason
        )

        action = "activated" if request.is_active else "deactivated"
        return SuccessResponse(
            success=True,
            message=f"User {action} successfully",
            data={
                "user_id": str(user.id),
                "user_email": user.email,
                "is_active": user.is_active,
                "reason": request.reason
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


# ============================================================================
# API Token Management
# ============================================================================

@router.delete("/tokens/{token_id}", response_model=SuccessResponse)
async def revoke_api_token(
    token_id: UUID,
    request: RevokeApiTokenRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Revoke an API token.

    **Write Operation** - Permanently revokes the specified API token.

    **Request Body:**
    ```json
    {
        "reason": "Security incident - potential compromise"
    }
    ```

    **Requires:** Super admin access (platform_admin role)

    **Raises:**
    - 400: Token not found
    - 404: Token not found
    """
    service = AdminUserService(db)

    try:
        token = service.revoke_api_token(
            token_id=token_id,
            revoked_by_user_id=current_user.id,
            reason=request.reason
        )

        return SuccessResponse(
            success=True,
            message="API token revoked successfully",
            data={
                "token_id": str(token.id),
                "token_name": token.name,
                "revoked_at": token.revoked_at.isoformat() if token.revoked_at else None,
                "reason": request.reason
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# Analytics
# ============================================================================

@router.get("/analytics/top-tenants", response_model=TopTenantsResponse)
async def get_top_active_tenants(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of tenants to return"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get top tenants by activity (job count and token usage).

    Returns most active tenants sorted by activity metrics.

    **Query Parameters:**
    - `limit`: Maximum number of tenants (1-50), default 10
    - `days`: Analysis period in days (1-365), default 30

    **Requires:** Super admin access (platform_admin role)

    **Example Response:**
    ```json
    {
        "tenants": [
            {
                "id": "...",
                "name": "Acme Corp",
                "slug": "acme-corp",
                "subscription_plan": "pro",
                "job_count": 345,
                "total_tokens": 1234567,
                "estimated_cost": 1234.56,
                "user_count": 5,
                "created_at": "2025-01-15T10:30:00Z",
                "last_activity": "2025-11-05T14:20:00Z"
            }
        ],
        "period_days": 30
    }
    ```
    """
    service = AdminMetricsService(db)
    top_tenants = service.get_top_active_tenants(limit=limit, days=days)

    return TopTenantsResponse(
        tenants=top_tenants,
        period_days=days
    )


# ============================================================================
# Platform Settings Management
# ============================================================================

@router.get("/settings", response_model=PlatformSettingsListResponse)
async def get_platform_settings(
    category: Optional[str] = Query(None, description="Filter by category"),
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get all platform settings, optionally filtered by category.

    Returns system-wide configuration settings that can be modified by super admins.

    **Query Parameters:**
    - `category`: Optional category filter (e.g., "credits", "features", "billing")

    **Requires:** Super admin access (platform_admin role)

    **Example Response:**
    ```json
    {
        "settings": [
            {
                "key": "trial_credits_amount",
                "value": 100,
                "description": "Number of credits automatically granted to new tenants on signup",
                "category": "credits",
                "created_at": "2025-11-05T10:00:00Z",
                "updated_at": "2025-11-05T10:00:00Z"
            }
        ],
        "total": 1
    }
    ```
    """
    service = PlatformSettingsService(db)
    settings = service.get_all_settings(category=category)

    return PlatformSettingsListResponse(
        settings=settings,
        total=len(settings)
    )


@router.patch("/settings/{key}", response_model=PlatformSettingResponse)
async def update_platform_setting(
    key: str,
    request: UpdatePlatformSettingRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Update a platform setting value.

    **Write Operation** - Updates system-wide configuration setting.

    **Request Body:**
    ```json
    {
        "value": 50,
        "description": "Trial credits amount for new tenants"
    }
    ```

    **Requires:** Super admin access (platform_admin role)

    **Raises:**
    - 400: Invalid setting key or value
    - 404: Setting not found

    **Example:**
    - To update trial credits: PATCH /admin/settings/trial_credits_amount with body {"value": 50}
    """
    service = PlatformSettingsService(db)

    try:
        setting = service.update_setting(
            key=key,
            value=request.value,
            description=request.description
        )

        return setting

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# Credit Management
# ============================================================================

@router.post("/tenants/{tenant_id}/credits", response_model=SuccessResponse)
async def add_tenant_credits(
    tenant_id: UUID,
    request: AddTenantCreditsRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Manually add credits to a tenant account.

    **Write Operation** - Creates a credit transaction with type "admin_adjustment".

    This operation:
    1. Adds credits to the tenant's balance
    2. Creates an immutable credit transaction record
    3. Updates the cached balance atomically
    4. Logs the action in admin audit logs

    **Request Body:**
    ```json
    {
        "amount": 1000,
        "reason": "Compensation for service downtime"
    }
    ```

    **Requires:** Super admin access (platform_admin role)

    **Raises:**
    - 400: Invalid amount (must be positive) or tenant not found
    - 404: Tenant not found

    **Example Response:**
    ```json
    {
        "success": true,
        "message": "1000 credits added successfully",
        "data": {
            "tenant_id": "...",
            "tenant_name": "Acme Corp",
            "amount": 1000,
            "new_balance": 6000,
            "reason": "Compensation for service downtime",
            "transaction_id": "..."
        }
    }
    ```
    """
    # Import Tenant model
    from app.models.tenant import Tenant

    # Validate tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    # Add credits using credit service
    credit_service = CreditService(db)

    try:
        transaction = credit_service.add_credits(
            tenant_id=tenant_id,
            amount=request.amount,
            transaction_type="admin_adjustment",
            reference_type="admin_manual_adjustment",
            reference_id=str(current_user.id),
            description=f"Admin credit addition: {request.reason}"
        )

        # Commit the transaction to persist changes
        db.commit()

        # Get new balance
        new_balance = credit_service.calculate_balance(tenant_id, use_cache=True)

        return SuccessResponse(
            success=True,
            message=f"{request.amount} credits added successfully",
            data={
                "tenant_id": str(tenant_id),
                "tenant_name": tenant.name,
                "amount": request.amount,
                "new_balance": new_balance,
                "reason": request.reason,
                "transaction_id": str(transaction.id)
            }
        )

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# Model Pricing Management
# ============================================================================

@router.get("/pricing", response_model=ModelPricingListResponse)
async def list_model_pricing(
    include_inactive: bool = Query(False, description="Include deactivated pricing records"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    List all model pricing records.

    Returns paginated list of pricing configurations for all models.
    By default, only shows active pricing records.

    **Query Parameters:**
    - `include_inactive`: Include deactivated records (default: false)
    - `page`: Page number (1-indexed), default 1
    - `page_size`: Items per page (1-100), default 50

    **Requires:** Super admin access (platform_admin role)

    **Example Response:**
    ```json
    {
        "pricing": [
            {
                "id": "...",
                "model_name": "gpt-4o",
                "input_price_per_million": 5.00,
                "output_price_per_million": 15.00,
                "effective_from": "2025-01-01T00:00:00Z",
                "effective_until": null,
                "is_active": true,
                "created_by": "...",
                "created_by_email": "admin@example.com",
                "created_at": "2025-01-01T00:00:00Z",
                "notes": "Initial pricing"
            }
        ],
        "total": 5,
        "page": 1,
        "page_size": 50,
        "total_pages": 1
    }
    ```
    """
    from app.services.pricing_management_service import PricingManagementService

    service = PricingManagementService(db)
    records, total = service.list_all_pricing(
        include_inactive=include_inactive,
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size

    # Build response with creator email
    pricing_items = []
    for record in records:
        creator_email = None
        if record.creator:
            creator_email = record.creator.email

        pricing_items.append(
            ModelPricingResponse(
                id=record.id,
                model_name=record.model_name,
                input_price_per_million=float(record.input_price_per_million),
                output_price_per_million=float(record.output_price_per_million),
                effective_from=record.effective_from,
                effective_until=record.effective_until,
                is_active=record.is_active,
                created_by=record.created_by,
                created_by_email=creator_email,
                created_at=record.created_at,
                notes=record.notes,
            )
        )

    return ModelPricingListResponse(
        pricing=pricing_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/pricing", response_model=ModelPricingResponse, status_code=status.HTTP_201_CREATED)
async def create_model_pricing(
    request: CreateModelPricingRequest,
    http_request: Request,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new model pricing record.

    **Write Operation** - Creates a new pricing configuration for a model.
    If an active pricing already exists for the model, it will be auto-expired.

    **Request Body:**
    ```json
    {
        "model_name": "gpt-4o",
        "input_price_per_million": 5.00,
        "output_price_per_million": 15.00,
        "effective_from": "2025-01-01T00:00:00Z",
        "notes": "Price update for Q1 2025"
    }
    ```

    **Requires:** Super admin access (platform_admin role)

    **Raises:**
    - 400: Invalid model name or prices
    """
    from app.services.pricing_management_service import PricingManagementService

    service = PricingManagementService(db)

    try:
        record = service.create_pricing(
            model_name=request.model_name,
            input_price=request.input_price_per_million,
            output_price=request.output_price_per_million,
            created_by=current_user.id,
            effective_from=request.effective_from,
            notes=request.notes,
        )

        # Create audit log entry for pricing creation
        audit_log = AdminAuditLog(
            user_id=current_user.id,
            action="pricing_created",
            resource_type="model_pricing",
            resource_id=record.id,
            endpoint="/admin/pricing",
            method="POST",
            ip_address=http_request.client.host if http_request.client else None,
            user_agent=http_request.headers.get("user-agent"),
            status_code=201,
            audit_metadata={
                "model_name": record.model_name,
                "input_price_per_million": float(record.input_price_per_million),
                "output_price_per_million": float(record.output_price_per_million),
                "effective_from": record.effective_from.isoformat() if record.effective_from else None,
                "notes": request.notes,
            }
        )
        db.add(audit_log)
        db.commit()

        return ModelPricingResponse(
            id=record.id,
            model_name=record.model_name,
            input_price_per_million=float(record.input_price_per_million),
            output_price_per_million=float(record.output_price_per_million),
            effective_from=record.effective_from,
            effective_until=record.effective_until,
            is_active=record.is_active,
            created_by=record.created_by,
            created_by_email=current_user.email,
            created_at=record.created_at,
            notes=record.notes,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/pricing/models", response_model=SupportedModelsResponse)
async def get_supported_models(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get list of all supported models with pricing.

    Returns models from both database configurations and system defaults.

    **Requires:** Super admin access (platform_admin role)

    **Example Response:**
    ```json
    {
        "models": ["deepseek-chat", "gemini-2.5-flash", "gpt-4o", "gpt-4-vision-preview"],
        "total": 4
    }
    ```
    """
    from app.services.pricing_management_service import PricingManagementService

    service = PricingManagementService(db)
    models = service.get_supported_models()

    return SupportedModelsResponse(
        models=models,
        total=len(models),
    )


@router.get("/pricing/{model_name}", response_model=ModelPricingHistoryResponse)
async def get_model_pricing_history(
    model_name: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get pricing history for a specific model.

    Returns all pricing records (active and expired) for the specified model,
    plus identifies the current active pricing.

    **Path Parameters:**
    - `model_name`: Model name to look up (case-insensitive)

    **Requires:** Super admin access (platform_admin role)

    **Example Response:**
    ```json
    {
        "model_name": "gpt-4o",
        "history": [
            {
                "id": "...",
                "model_name": "gpt-4o",
                "input_price_per_million": 5.00,
                "output_price_per_million": 15.00,
                "effective_from": "2025-01-01T00:00:00Z",
                "effective_until": null,
                "is_active": true,
                ...
            }
        ],
        "current_pricing": {...}
    }
    ```
    """
    from app.services.pricing_management_service import PricingManagementService

    service = PricingManagementService(db)
    history, current = service.get_pricing_history(model_name)

    # Build response items
    history_items = []
    for record in history:
        creator_email = None
        if record.creator:
            creator_email = record.creator.email

        history_items.append(
            ModelPricingResponse(
                id=record.id,
                model_name=record.model_name,
                input_price_per_million=float(record.input_price_per_million),
                output_price_per_million=float(record.output_price_per_million),
                effective_from=record.effective_from,
                effective_until=record.effective_until,
                is_active=record.is_active,
                created_by=record.created_by,
                created_by_email=creator_email,
                created_at=record.created_at,
                notes=record.notes,
            )
        )

    current_response = None
    if current:
        creator_email = None
        if current.creator:
            creator_email = current.creator.email

        current_response = ModelPricingResponse(
            id=current.id,
            model_name=current.model_name,
            input_price_per_million=float(current.input_price_per_million),
            output_price_per_million=float(current.output_price_per_million),
            effective_from=current.effective_from,
            effective_until=current.effective_until,
            is_active=current.is_active,
            created_by=current.created_by,
            created_by_email=creator_email,
            created_at=current.created_at,
            notes=current.notes,
        )

    return ModelPricingHistoryResponse(
        model_name=model_name.lower(),
        history=history_items,
        current_pricing=current_response,
    )


@router.delete("/pricing/{pricing_id}", response_model=SuccessResponse)
async def deactivate_model_pricing(
    pricing_id: UUID,
    request: DeactivatePricingRequest,
    http_request: Request,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Soft-delete a pricing record.

    **Write Operation** - Marks the pricing record as deactivated.
    The record is preserved for audit purposes.

    **Path Parameters:**
    - `pricing_id`: UUID of the pricing record to deactivate

    **Request Body:**
    ```json
    {
        "reason": "Model deprecated, no longer in use"
    }
    ```

    **Requires:** Super admin access (platform_admin role)

    **Raises:**
    - 400: Pricing record not found or already deactivated
    - 404: Pricing record not found
    """
    from app.services.pricing_management_service import PricingManagementService

    service = PricingManagementService(db)

    try:
        # Get the record before deactivation for audit metadata
        existing_record = service.get_pricing_by_id(pricing_id)
        previous_input_price = float(existing_record.input_price_per_million) if existing_record else None
        previous_output_price = float(existing_record.output_price_per_million) if existing_record else None

        record = service.deactivate_pricing(
            pricing_id=pricing_id,
            reason=request.reason,
        )

        # Create audit log entry for pricing deactivation
        audit_log = AdminAuditLog(
            user_id=current_user.id,
            action="pricing_deactivated",
            resource_type="model_pricing",
            resource_id=record.id,
            endpoint=f"/admin/pricing/{pricing_id}",
            method="DELETE",
            ip_address=http_request.client.host if http_request.client else None,
            user_agent=http_request.headers.get("user-agent"),
            status_code=200,
            audit_metadata={
                "model_name": record.model_name,
                "previous_input_price_per_million": previous_input_price,
                "previous_output_price_per_million": previous_output_price,
                "reason": request.reason,
            }
        )
        db.add(audit_log)
        db.commit()

        return SuccessResponse(
            success=True,
            message=f"Pricing for '{record.model_name}' deactivated successfully",
            data={
                "pricing_id": str(record.id),
                "model_name": record.model_name,
                "reason": request.reason,
            }
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
