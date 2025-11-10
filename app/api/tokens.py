"""API Token management endpoints for creating, listing, updating, and revoking tokens."""

from datetime import datetime, timedelta
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, ApiToken
from app.schemas.api_token import (
    ApiTokenCreateRequest,
    ApiTokenCreateResponse,
    ApiTokenInfo,
    ApiTokenUpdateRequest,
    MessageResponse,
)
from app.services.api_token_service import ApiTokenService
from app.services.permission_service import PermissionService
from app.dependencies.auth import get_current_active_user

router = APIRouter()


@router.post(
    "/tokens",
    response_model=ApiTokenCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API token",
    description="Create a new API token with specific permissions and optional expiration"
)
async def create_api_token(
    request: ApiTokenCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ApiTokenCreateResponse:
    """
    Create a new API token.

    Workflow:
    1. Validate that user has all requested scopes/permissions
    2. Generate new API token (shown only once!)
    3. Store hashed token in database
    4. Return token details with full token

    Args:
        request: Token creation request with name, scopes, and expiration
        current_user: Current authenticated user (from dependency)
        db: Database session

    Returns:
        ApiTokenCreateResponse with full token (ONLY SHOWN ONCE)

    Raises:
        HTTPException 400: User doesn't have one or more requested permissions
        HTTPException 500: Token generation or storage failed
    """
    # Validate scopes against user's permissions
    permission_service = PermissionService(db)
    user_permissions = permission_service.get_user_permissions(current_user)

    for scope in request.scopes:
        if scope not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You don't have permission: {scope}"
            )

    # Generate token
    try:
        full_token, token_hash, token_prefix = ApiTokenService.generate_token()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate token: {str(e)}"
        )

    # Calculate expiration
    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)

    # Create database record
    api_token = ApiToken(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        name=request.name,
        token_hash=token_hash,
        token_prefix=token_prefix,
        scopes=request.scopes,
        expires_at=expires_at,
        is_active=True
    )

    db.add(api_token)
    db.commit()
    db.refresh(api_token)

    return ApiTokenCreateResponse(
        token=full_token,  # ONLY shown here
        token_id=str(api_token.id),
        name=api_token.name,
        token_prefix=api_token.token_prefix,
        scopes=api_token.scopes,
        expires_at=api_token.expires_at,
        created_at=api_token.created_at
    )


@router.get(
    "/tokens",
    response_model=List[ApiTokenInfo],
    summary="List all API tokens",
    description="List all API tokens for the current user (without full token values)"
)
async def list_api_tokens(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[ApiTokenInfo]:
    """
    List all API tokens for current user.

    Workflow:
    1. Query all active tokens for current user
    2. Return token metadata (NOT the full token)

    Args:
        current_user: Current authenticated user (from dependency)
        db: Database session

    Returns:
        List of ApiTokenInfo with token metadata
    """
    tokens = (
        db.query(ApiToken)
        .filter(
            ApiToken.user_id == current_user.id,
            ApiToken.is_active == True
        )
        .order_by(ApiToken.created_at.desc())
        .all()
    )

    return [
        ApiTokenInfo(
            token_id=str(token.id),
            name=token.name,
            token_prefix=token.token_prefix,
            scopes=token.scopes,
            expires_at=token.expires_at,
            last_used_at=token.last_used_at,
            created_at=token.created_at
        )
        for token in tokens
    ]


@router.get(
    "/tokens/{token_id}",
    response_model=ApiTokenInfo,
    summary="Get API token details",
    description="Get details for a specific API token (without full token value)"
)
async def get_api_token(
    token_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ApiTokenInfo:
    """
    Get details for a specific API token.

    Workflow:
    1. Query token by ID and user ID (ensure ownership)
    2. Return token metadata

    Args:
        token_id: Token UUID
        current_user: Current authenticated user (from dependency)
        db: Database session

    Returns:
        ApiTokenInfo with token metadata

    Raises:
        HTTPException 404: Token not found or user doesn't own it
    """
    token = (
        db.query(ApiToken)
        .filter(
            ApiToken.id == token_id,
            ApiToken.user_id == current_user.id  # Ensure ownership
        )
        .first()
    )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )

    return ApiTokenInfo(
        token_id=str(token.id),
        name=token.name,
        token_prefix=token.token_prefix,
        scopes=token.scopes,
        expires_at=token.expires_at,
        last_used_at=token.last_used_at,
        created_at=token.created_at
    )


@router.patch(
    "/tokens/{token_id}",
    response_model=ApiTokenInfo,
    summary="Update API token",
    description="Update token name or scopes"
)
async def update_api_token(
    token_id: UUID,
    request: ApiTokenUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ApiTokenInfo:
    """
    Update an API token's name or scopes.

    Workflow:
    1. Query token by ID and user ID (ensure ownership)
    2. Validate new scopes against user permissions (if updating scopes)
    3. Update token fields
    4. Return updated token metadata

    Args:
        token_id: Token UUID
        request: Update request with optional name and scopes
        current_user: Current authenticated user (from dependency)
        db: Database session

    Returns:
        ApiTokenInfo with updated token metadata

    Raises:
        HTTPException 404: Token not found or user doesn't own it
        HTTPException 400: User doesn't have one or more requested permissions
    """
    token = (
        db.query(ApiToken)
        .filter(
            ApiToken.id == token_id,
            ApiToken.user_id == current_user.id  # Ensure ownership
        )
        .first()
    )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )

    # Update name if provided
    if request.name is not None:
        token.name = request.name

    # Update scopes if provided (validate against user permissions)
    if request.scopes is not None:
        permission_service = PermissionService(db)
        user_permissions = permission_service.get_user_permissions(current_user)

        for scope in request.scopes:
            if scope not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"You don't have permission: {scope}"
                )

        token.scopes = request.scopes

    db.commit()
    db.refresh(token)

    return ApiTokenInfo(
        token_id=str(token.id),
        name=token.name,
        token_prefix=token.token_prefix,
        scopes=token.scopes,
        expires_at=token.expires_at,
        last_used_at=token.last_used_at,
        created_at=token.created_at
    )


@router.delete(
    "/tokens/{token_id}",
    response_model=MessageResponse,
    summary="Revoke API token",
    description="Revoke (soft delete) an API token"
)
async def revoke_api_token(
    token_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Revoke (soft delete) an API token.

    Workflow:
    1. Query token by ID and user ID (ensure ownership)
    2. Mark token as inactive (soft delete)
    3. Record who revoked it and when

    Args:
        token_id: Token UUID
        current_user: Current authenticated user (from dependency)
        db: Database session

    Returns:
        MessageResponse confirming revocation

    Raises:
        HTTPException 404: Token not found or user doesn't own it
    """
    token = (
        db.query(ApiToken)
        .filter(
            ApiToken.id == token_id,
            ApiToken.user_id == current_user.id  # Ensure ownership
        )
        .first()
    )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )

    # Soft delete: mark as inactive and record who revoked it
    token.is_active = False
    token.revoked_at = datetime.utcnow()
    token.revoked_by_user_id = current_user.id

    db.commit()

    return MessageResponse(message="API token revoked successfully")
