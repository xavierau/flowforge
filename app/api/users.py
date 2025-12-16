"""User management API endpoints for profile, password, and user administration."""

from datetime import timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Tenant
from app.schemas.user import (
    ProfileUpdateRequest,
    PasswordUpdateRequest,
    UserInviteRequest,
    UserUpdateRequest,
    UserDetailResponse,
    UserListResponse,
    UserListItemResponse,
    InvitationResponse,
    InvitationListItem,
    InvitationListResponse,
    RoleInfo,
    TenantInfo,
)
from app.schemas.auth import MessageResponse
from app.services.user_service import UserService
from app.services.auth_service import auth_service
from app.services.permission_service import PermissionService
from app.dependencies.auth import get_current_active_user, require_permission
from app.config import settings
from app.tasks.email_tasks import send_invitation_email_task

router = APIRouter()


@router.get(
    "/users/profile",
    response_model=UserDetailResponse,
    summary="Get current user's profile",
    description="Get authenticated user's full profile with tenant info and permissions"
)
async def get_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> UserDetailResponse:
    """
    Get current user's profile.

    Workflow:
    1. Extract current user from Bearer token (via dependency)
    2. Load tenant and role information
    3. Get user permissions via PermissionService
    4. Return full user profile

    Args:
        current_user: Current authenticated user (from dependency)
        db: Database session

    Returns:
        UserDetailResponse with user, tenant, role, and permissions

    Raises:
        HTTPException 404: Tenant not found
    """
    # Get user service
    user_service = UserService(db)

    # Reload user with relationships
    user_with_details = user_service.get_user_with_details(
        current_user.id,
        current_user.tenant_id
    )

    if not user_with_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get permissions
    permission_service = PermissionService(db)
    permissions = permission_service.get_user_permissions(user_with_details)

    return UserDetailResponse(
        id=user_with_details.id,
        email=user_with_details.email,
        full_name=user_with_details.full_name,
        avatar_url=user_with_details.avatar_url,
        is_active=user_with_details.is_active,
        is_verified=user_with_details.is_verified,
        locale=user_with_details.locale,
        last_login=user_with_details.last_login,
        created_at=user_with_details.created_at,
        role=RoleInfo.model_validate(user_with_details.role),
        tenant=TenantInfo.model_validate(user_with_details.tenant),
        permissions=permissions
    )


@router.patch(
    "/users/profile",
    response_model=UserDetailResponse,
    summary="Update current user's profile",
    description="Update profile fields like full_name, avatar_url, or locale"
)
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> UserDetailResponse:
    """
    Update current user's profile.

    Workflow:
    1. Extract current user from Bearer token
    2. Update provided fields (full_name, avatar_url, locale)
    3. Return updated profile with permissions

    Args:
        request: Profile update request with optional fields
        current_user: Current authenticated user
        db: Database session

    Returns:
        UserDetailResponse with updated user information

    Raises:
        HTTPException 400: Invalid locale value
    """
    # Get user service
    user_service = UserService(db)

    # Update profile
    updated_user = user_service.update_user_profile(
        user=current_user,
        full_name=request.full_name,
        avatar_url=request.avatar_url,
        locale=request.locale
    )

    # Reload with relationships
    user_with_details = user_service.get_user_with_details(
        updated_user.id,
        updated_user.tenant_id
    )

    # Get permissions
    permission_service = PermissionService(db)
    permissions = permission_service.get_user_permissions(user_with_details)

    return UserDetailResponse(
        id=user_with_details.id,
        email=user_with_details.email,
        full_name=user_with_details.full_name,
        avatar_url=user_with_details.avatar_url,
        is_active=user_with_details.is_active,
        is_verified=user_with_details.is_verified,
        locale=user_with_details.locale,
        last_login=user_with_details.last_login,
        created_at=user_with_details.created_at,
        role=RoleInfo.model_validate(user_with_details.role),
        tenant=TenantInfo.model_validate(user_with_details.tenant),
        permissions=permissions
    )


@router.patch(
    "/users/password",
    response_model=MessageResponse,
    summary="Update current user's password",
    description="Change password with current password verification"
)
async def update_password(
    request: PasswordUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Update current user's password.

    Workflow:
    1. Extract current user from Bearer token
    2. Verify current password is correct
    3. Validate new password strength (via Pydantic)
    4. Hash and update new password
    5. Invalidate all refresh tokens (force re-login on all devices)
    6. Return success message

    Args:
        request: Password update request with current and new password
        current_user: Current authenticated user
        db: Database session

    Returns:
        MessageResponse confirming password update

    Raises:
        HTTPException 400: Current password is incorrect
    """
    # Verify current password
    if not auth_service.verify_password(
        request.current_password,
        current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Update password
    user_service = UserService(db)
    user_service.update_user_password(current_user, request.new_password)

    return MessageResponse(message="Password updated successfully")


@router.post(
    "/users/invite",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a new user to the tenant",
    description="Create user invitation with specified role (requires users:invite permission)"
)
async def invite_user(
    request: UserInviteRequest,
    current_user: User = Depends(require_permission("users:invite")),
    db: Session = Depends(get_db)
) -> InvitationResponse:
    """
    Invite a new user to the tenant.

    Workflow:
    1. Check permission (users:invite required)
    2. Verify email doesn't already exist
    3. Verify role exists and is valid
    4. Generate invitation token
    5. Create user record with is_active=False
    6. Queue invitation email task
    7. Return invitation token and success message

    Args:
        request: User invitation request with email and role_id
        current_user: Current authenticated user with users:invite permission
        db: Database session

    Returns:
        InvitationResponse with invitation token and email

    Raises:
        HTTPException 409: Email already registered
        HTTPException 404: Role not found
    """
    user_service = UserService(db)

    # Check if email already exists
    if user_service.user_exists_by_email(request.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Verify role exists
    role = user_service.get_role_by_id(request.role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    try:
        # Create invitation
        invited_user, invitation_token = user_service.create_invitation(
            email=request.email,
            role_id=request.role_id,
            tenant_id=current_user.tenant_id,
            invited_by_user_id=current_user.id
        )

        # Build invitation URL
        invitation_url = f"{settings.frontend_url}/accept-invitation?token={invitation_token}"

        # Get inviter info
        invited_by = current_user.full_name or current_user.email

        # Get tenant name
        tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
        tenant_name = tenant.name if tenant else "Your Organization"

        # Queue email task (fire and forget)
        send_invitation_email_task.delay(
            to_email=invited_user.email,
            invitation_url=invitation_url,
            invited_by=invited_by,
            tenant_name=tenant_name,
        )

        return InvitationResponse(
            message="Invitation sent successfully",
            invitation_token=invitation_token,
            email=invited_user.email
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="List users in tenant",
    description="Get paginated list of users in current user's tenant (requires users:read permission)"
)
async def list_users(
    limit: int = Query(default=50, ge=1, le=100, description="Number of users per page"),
    offset: int = Query(default=0, ge=0, description="Number of users to skip"),
    role_id: Optional[UUID] = Query(default=None, description="Filter by role ID"),
    is_active: Optional[bool] = Query(default=None, description="Filter by active status"),
    current_user: User = Depends(require_permission("users:read")),
    db: Session = Depends(get_db)
) -> UserListResponse:
    """
    List users in tenant with pagination and filters.

    Workflow:
    1. Check permission (users:read required)
    2. Query users in current user's tenant (tenant isolation)
    3. Apply optional filters (role, is_active)
    4. Apply pagination (limit, offset)
    5. Return users with total count

    Args:
        limit: Maximum number of users to return (1-100, default 50)
        offset: Number of users to skip (default 0)
        role_id: Optional role filter
        is_active: Optional active status filter
        current_user: Current authenticated user with users:read permission
        db: Database session

    Returns:
        UserListResponse with paginated users and total count
    """
    user_service = UserService(db)

    # Get users with pagination and filters
    users, total = user_service.list_tenant_users(
        tenant_id=current_user.tenant_id,
        limit=limit,
        offset=offset,
        role_id=role_id,
        is_active=is_active
    )

    # Convert to response models
    user_list = [
        UserListItemResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            is_verified=user.is_verified,
            role=RoleInfo.model_validate(user.role),
            last_login=user.last_login,
            created_at=user.created_at
        )
        for user in users
    ]

    return UserListResponse(
        users=user_list,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get(
    "/users/invitations",
    response_model=InvitationListResponse,
    summary="List pending invitations",
    description="Get list of pending user invitations in current user's tenant (requires users:invite permission)"
)
async def list_invitations(
    current_user: User = Depends(require_permission("users:invite")),
    db: Session = Depends(get_db)
) -> InvitationListResponse:
    """
    List pending invitations in tenant.

    Workflow:
    1. Check permission (users:invite required)
    2. Query users with is_active=False and is_verified=False (pending invitations)
    3. Return invitations with calculated expiration dates

    Args:
        current_user: Current authenticated user with users:invite permission
        db: Database session

    Returns:
        InvitationListResponse with list of pending invitations
    """
    user_service = UserService(db)

    # Get pending invitations (users with is_active=False and is_verified=False)
    pending_users, total = user_service.list_pending_invitations(
        tenant_id=current_user.tenant_id
    )

    # Convert to response models
    # Invitation expires 7 days after creation
    invitation_expiry_days = 7

    invitation_list = [
        InvitationListItem(
            id=user.id,
            email=user.email,
            role=user.role.name if user.role else "unknown",
            created_at=user.created_at,
            expires_at=user.created_at + timedelta(days=invitation_expiry_days),
            status="pending"
        )
        for user in pending_users
    ]

    return InvitationListResponse(
        invitations=invitation_list,
        total=total
    )


@router.get(
    "/users/{user_id}",
    response_model=UserDetailResponse,
    summary="Get user details",
    description="Get specific user's details (requires users:read permission, tenant-isolated)"
)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(require_permission("users:read")),
    db: Session = Depends(get_db)
) -> UserDetailResponse:
    """
    Get specific user's details.

    Workflow:
    1. Check permission (users:read required)
    2. Query user by ID
    3. Verify user belongs to same tenant (tenant isolation)
    4. Get user permissions
    5. Return user details

    Args:
        user_id: User ID to fetch
        current_user: Current authenticated user with users:read permission
        db: Database session

    Returns:
        UserDetailResponse with user, tenant, role, and permissions

    Raises:
        HTTPException 404: User not found or belongs to different tenant
    """
    user_service = UserService(db)

    # Get user with tenant isolation
    user = user_service.get_user_with_details(user_id, current_user.tenant_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get permissions
    permission_service = PermissionService(db)
    permissions = permission_service.get_user_permissions(user)

    return UserDetailResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_verified=user.is_verified,
        locale=user.locale,
        last_login=user.last_login,
        created_at=user.created_at,
        role=RoleInfo.model_validate(user.role),
        tenant=TenantInfo.model_validate(user.tenant),
        permissions=permissions
    )


@router.post(
    "/users/{user_id}/resend-invitation",
    response_model=MessageResponse,
    summary="Resend invitation email",
    description="Resend invitation email for a pending user (requires users:invite permission)"
)
async def resend_invitation(
    user_id: UUID,
    current_user: User = Depends(require_permission("users:invite")),
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Resend invitation email for a pending user.

    Workflow:
    1. Check permission (users:invite required)
    2. Query user by ID
    3. Verify user is a pending invitation (is_active=False, is_verified=False)
    4. Regenerate invitation token if needed
    5. Queue invitation email task
    6. Return success message

    Args:
        user_id: User ID of the pending invitation
        current_user: Current authenticated user with users:invite permission
        db: Database session

    Returns:
        MessageResponse confirming invitation was resent

    Raises:
        HTTPException 404: User not found or not a pending invitation
        HTTPException 400: User is already active or verified
    """
    user_service = UserService(db)

    # Get pending invitation (tenant-isolated)
    pending_user = user_service.get_pending_invitation(user_id, current_user.tenant_id)

    if not pending_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending invitation not found"
        )

    try:
        # Regenerate invitation token
        new_token = user_service.regenerate_invitation_token(pending_user)

        # Build invitation URL
        invitation_url = f"{settings.frontend_url}/accept-invitation?token={new_token}"

        # Get inviter info
        invited_by = current_user.full_name or current_user.email

        # Get tenant name
        tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
        tenant_name = tenant.name if tenant else "Your Organization"

        # Queue email task (fire and forget)
        send_invitation_email_task.delay(
            to_email=pending_user.email,
            invitation_url=invitation_url,
            invited_by=invited_by,
            tenant_name=tenant_name,
        )

        return MessageResponse(message="Invitation email resent successfully")

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch(
    "/users/{user_id}",
    response_model=UserDetailResponse,
    summary="Update user",
    description="Update user's role, active status, or full name (requires users:update permission)"
)
async def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    current_user: User = Depends(require_permission("users:update")),
    db: Session = Depends(get_db)
) -> UserDetailResponse:
    """
    Update user (admin operation).

    Workflow:
    1. Check permission (users:update required)
    2. Query target user by ID
    3. Verify user belongs to same tenant (tenant isolation)
    4. If deactivating, check it's not last active admin
    5. Update provided fields (role_id, is_active, full_name)
    6. Return updated user

    Args:
        user_id: User ID to update
        request: User update request with optional fields
        current_user: Current authenticated user with users:update permission
        db: Database session

    Returns:
        UserDetailResponse with updated user information

    Raises:
        HTTPException 404: User not found or belongs to different tenant
        HTTPException 400: Cannot deactivate last active admin, role not found
        HTTPException 403: Cannot modify yourself (use /users/profile instead)
    """
    user_service = UserService(db)

    # Prevent users from modifying themselves via admin endpoint
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify your own user via this endpoint. Use /users/profile instead."
        )

    # Get user with tenant isolation
    user = user_service.get_user_with_details(user_id, current_user.tenant_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if trying to deactivate last active admin
    if request.is_active is False and user.is_active:
        if user_service.is_last_active_admin(user):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last active admin in the tenant"
            )

    try:
        # Update user
        updated_user = user_service.update_user_by_admin(
            user=user,
            role_id=request.role_id,
            is_active=request.is_active,
            full_name=request.full_name
        )

        # Reload with relationships
        user_with_details = user_service.get_user_with_details(
            updated_user.id,
            updated_user.tenant_id
        )

        # Get permissions
        permission_service = PermissionService(db)
        permissions = permission_service.get_user_permissions(user_with_details)

        return UserDetailResponse(
            id=user_with_details.id,
            email=user_with_details.email,
            full_name=user_with_details.full_name,
            avatar_url=user_with_details.avatar_url,
            is_active=user_with_details.is_active,
            is_verified=user_with_details.is_verified,
            locale=user_with_details.locale,
            last_login=user_with_details.last_login,
            created_at=user_with_details.created_at,
            role=RoleInfo.model_validate(user_with_details.role),
            tenant=TenantInfo.model_validate(user_with_details.tenant),
            permissions=permissions
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/users/{user_id}",
    response_model=MessageResponse,
    summary="Delete user",
    description="Soft delete user by setting is_active=False (requires users:delete permission)"
)
async def delete_user(
    user_id: UUID,
    hard_delete: bool = Query(
        default=False,
        description="If true, permanently delete user. If false, soft delete (set is_active=False)"
    ),
    current_user: User = Depends(require_permission("users:delete")),
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Delete user (soft or hard delete).

    Workflow:
    1. Check permission (users:delete required)
    2. Query target user by ID
    3. Verify user belongs to same tenant (tenant isolation)
    4. Prevent deleting self
    5. Prevent deleting last active admin
    6. Soft delete (set is_active=False) or hard delete (remove from DB)
    7. Return success message

    Args:
        user_id: User ID to delete
        hard_delete: If true, permanently delete. If false, soft delete (default)
        current_user: Current authenticated user with users:delete permission
        db: Database session

    Returns:
        MessageResponse confirming deletion

    Raises:
        HTTPException 404: User not found or belongs to different tenant
        HTTPException 400: Cannot delete last active admin
        HTTPException 403: Cannot delete yourself
    """
    user_service = UserService(db)

    # Prevent users from deleting themselves
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete your own user account"
        )

    # Get user with tenant isolation
    user = user_service.get_user_with_details(user_id, current_user.tenant_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if trying to delete last active admin
    if user_service.is_last_active_admin(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last active admin in the tenant"
        )

    # Perform deletion
    if hard_delete:
        user_service.hard_delete_user(user)
        return MessageResponse(message="User permanently deleted successfully")
    else:
        user_service.soft_delete_user(user)
        return MessageResponse(message="User deactivated successfully")


@router.get(
    "/users/notifications/preferences",
    summary="Get notification preferences",
    description="Get current user's notification preferences (stub implementation)"
)
async def get_notification_preferences(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get notification preferences (stub implementation).

    Returns default preferences for now.
    """
    return {
        "email_notifications": True,
        "document_updates": True,
        "job_completions": True,
        "system_announcements": True,
        "weekly_reports": False
    }


@router.patch(
    "/users/notifications/preferences",
    summary="Update notification preferences",
    description="Update current user's notification preferences (stub implementation)"
)
async def update_notification_preferences(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update notification preferences (stub implementation).

    Accepts and returns the same data. Full implementation pending.
    """
    return {
        "email_notifications": True,
        "document_updates": True,
        "job_completions": True,
        "system_announcements": True,
        "weekly_reports": False
    }
