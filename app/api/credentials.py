"""Credential management API endpoints for secure storage of API keys and secrets."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas.credential import (
    CredentialCreate,
    CredentialUpdate,
    CredentialResponse,
    CredentialListResponse,
    MessageResponse,
)
from app.services.credential_service import (
    CredentialService,
    CredentialNotFoundError,
    CredentialExistsError,
    CredentialServiceError,
)
from app.dependencies.auth import require_permission

router = APIRouter()


@router.post(
    "/credentials",
    response_model=CredentialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new credential",
    description=(
        "Create a new encrypted credential (API key, secret, etc.). "
        "The value is encrypted before storage and never exposed in responses."
    ),
)
async def create_credential(
    request: CredentialCreate,
    current_user: User = Depends(require_permission("credentials:create")),
    db: Session = Depends(get_db),
) -> CredentialResponse:
    """
    Create a new credential.

    The credential value is encrypted using AES-256-GCM before storage.
    Once created, the plaintext value can never be retrieved via the API.

    Args:
        request: Credential creation request with name, value, and optional description
        current_user: Current authenticated user (from dependency)
        db: Database session

    Returns:
        CredentialResponse with credential metadata (NO value)

    Raises:
        HTTPException 400: Credential name already exists in scope
        HTTPException 500: Encryption failed

    Security Notes:
        - Requires 'credentials:create' permission
        - Value is encrypted immediately, never stored in plaintext
        - Value is NEVER returned in API responses
    """
    service = CredentialService(db)

    try:
        credential = service.create_credential(
            tenant_id=current_user.tenant_id,
            name=request.name,
            value=request.value,
            created_by_user_id=current_user.id,
            description=request.description,
            workflow_id=request.workflow_id,
        )

        return CredentialResponse(
            id=credential.id,
            name=credential.name,
            description=credential.description,
            workflow_id=credential.workflow_id,
            is_active=credential.is_active,
            created_at=credential.created_at,
            updated_at=credential.updated_at,
            created_by_user_id=credential.created_by_user_id,
        )

    except CredentialExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except CredentialServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/credentials",
    response_model=CredentialListResponse,
    summary="List credentials",
    description="List all credentials for the tenant with optional filtering.",
)
async def list_credentials(
    workflow_id: Optional[UUID] = Query(
        None,
        description="Filter by workflow ID (null = all credentials)",
    ),
    include_tenant_level: bool = Query(
        True,
        description="Include tenant-level credentials when workflow_id is set",
    ),
    active_only: bool = Query(
        True,
        description="Only return active credentials",
    ),
    page: int = Query(
        1,
        ge=1,
        description="Page number (1-based)",
    ),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="Items per page",
    ),
    current_user: User = Depends(require_permission("credentials:read")),
    db: Session = Depends(get_db),
) -> CredentialListResponse:
    """
    List credentials for the tenant.

    Supports filtering by workflow scope and pagination.
    Credential values are NEVER included in the response.

    Args:
        workflow_id: Optional filter by workflow ID
        include_tenant_level: Include tenant-level when filtering by workflow
        active_only: Only return active credentials
        page: Page number (1-based)
        page_size: Items per page (max 100)
        current_user: Current authenticated user (from dependency)
        db: Database session

    Returns:
        CredentialListResponse with paginated credentials

    Security Notes:
        - Requires 'credentials:read' permission
        - Filters by tenant_id automatically
        - Values are NEVER exposed
    """
    service = CredentialService(db)

    credentials, total = service.list_credentials(
        tenant_id=current_user.tenant_id,
        workflow_id=workflow_id,
        include_tenant_level=include_tenant_level,
        active_only=active_only,
        page=page,
        page_size=page_size,
    )

    items = [
        CredentialResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            workflow_id=c.workflow_id,
            is_active=c.is_active,
            created_at=c.created_at,
            updated_at=c.updated_at,
            created_by_user_id=c.created_by_user_id,
        )
        for c in credentials
    ]

    return CredentialListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get(
    "/credentials/{credential_id}",
    response_model=CredentialResponse,
    summary="Get credential details",
    description="Get details for a specific credential (value is NOT included).",
)
async def get_credential(
    credential_id: UUID,
    current_user: User = Depends(require_permission("credentials:read")),
    db: Session = Depends(get_db),
) -> CredentialResponse:
    """
    Get details for a specific credential.

    The credential value is NEVER included in the response.

    Args:
        credential_id: Credential UUID
        current_user: Current authenticated user (from dependency)
        db: Database session

    Returns:
        CredentialResponse with credential metadata

    Raises:
        HTTPException 404: Credential not found or not owned by tenant

    Security Notes:
        - Requires 'credentials:read' permission
        - Filters by tenant_id automatically
        - Value is NEVER exposed
    """
    service = CredentialService(db)

    credential = service.get_credential_by_id(
        credential_id=credential_id,
        tenant_id=current_user.tenant_id,
    )

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    return CredentialResponse(
        id=credential.id,
        name=credential.name,
        description=credential.description,
        workflow_id=credential.workflow_id,
        is_active=credential.is_active,
        created_at=credential.created_at,
        updated_at=credential.updated_at,
        created_by_user_id=credential.created_by_user_id,
    )


@router.patch(
    "/credentials/{credential_id}",
    response_model=CredentialResponse,
    summary="Update credential",
    description="Update credential description, value, or active status.",
)
async def update_credential(
    credential_id: UUID,
    request: CredentialUpdate,
    current_user: User = Depends(require_permission("credentials:update")),
    db: Session = Depends(get_db),
) -> CredentialResponse:
    """
    Update a credential.

    Can update description, value (re-encrypted), or active status.
    The new value (if provided) is encrypted before storage.

    Args:
        credential_id: Credential UUID
        request: Update request with optional fields
        current_user: Current authenticated user (from dependency)
        db: Database session

    Returns:
        CredentialResponse with updated metadata

    Raises:
        HTTPException 404: Credential not found
        HTTPException 500: Encryption failed (if updating value)

    Security Notes:
        - Requires 'credentials:update' permission
        - New value is encrypted immediately
        - Value is NEVER returned
    """
    service = CredentialService(db)

    try:
        credential = service.update_credential(
            credential_id=credential_id,
            tenant_id=current_user.tenant_id,
            description=request.description,
            value=request.value,
            is_active=request.is_active,
        )

        return CredentialResponse(
            id=credential.id,
            name=credential.name,
            description=credential.description,
            workflow_id=credential.workflow_id,
            is_active=credential.is_active,
            created_at=credential.created_at,
            updated_at=credential.updated_at,
            created_by_user_id=credential.created_by_user_id,
        )

    except CredentialNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )
    except CredentialServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete(
    "/credentials/{credential_id}",
    response_model=MessageResponse,
    summary="Delete credential",
    description="Permanently delete a credential.",
)
async def delete_credential(
    credential_id: UUID,
    current_user: User = Depends(require_permission("credentials:delete")),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Delete a credential permanently.

    This is a hard delete - the credential cannot be recovered.
    Consider using PATCH with is_active=false for soft delete.

    Args:
        credential_id: Credential UUID
        current_user: Current authenticated user (from dependency)
        db: Database session

    Returns:
        MessageResponse confirming deletion

    Raises:
        HTTPException 404: Credential not found

    Security Notes:
        - Requires 'credentials:delete' permission
        - This is a permanent deletion
    """
    service = CredentialService(db)

    deleted = service.delete_credential(
        credential_id=credential_id,
        tenant_id=current_user.tenant_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    return MessageResponse(message="Credential deleted successfully")


@router.get(
    "/credentials/names/available",
    response_model=list[str],
    summary="Get available credential names",
    description="Get list of credential names for autocomplete/validation.",
)
async def get_credential_names(
    workflow_id: Optional[UUID] = Query(
        None,
        description="Workflow ID to include workflow-specific credentials",
    ),
    current_user: User = Depends(require_permission("credentials:read")),
    db: Session = Depends(get_db),
) -> list[str]:
    """
    Get list of available credential names.

    Useful for autocomplete in workflow builder expression editor.
    Returns names of active credentials at both tenant and workflow level.

    Args:
        workflow_id: Optional workflow ID for workflow-specific credentials
        current_user: Current authenticated user (from dependency)
        db: Database session

    Returns:
        List of credential names (sorted)

    Security Notes:
        - Requires 'credentials:read' permission
        - Only returns names, not values
    """
    service = CredentialService(db)

    return service.get_credential_names(
        tenant_id=current_user.tenant_id,
        workflow_id=workflow_id,
    )
