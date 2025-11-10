"""Service for cross-tenant user management (super admin only)."""

from datetime import datetime
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models import User, Tenant, Role, ApiToken
from app.schemas.admin import UserListItem, UserDetailResponse
from app.services.permission_service import PermissionService
from app.exceptions.auth import AuthorizationError


class AdminUserService:
    """
    Service for managing users across all tenants.

    This service provides user management operations including:
    - Cross-tenant user listing with filters
    - User search by email/name
    - User details retrieval
    - User status updates (activate/deactivate)

    All methods are designed for super admin use only.
    Security is enforced at the API layer via require_super_admin dependency.
    """

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db

    def list_all_users(
        self,
        page: int = 1,
        page_size: int = 50,
        tenant_id_filter: Optional[UUID] = None,
        role_id_filter: Optional[UUID] = None,
        is_active_filter: Optional[bool] = None,
        search_query: Optional[str] = None
    ) -> Tuple[List[UserListItem], int]:
        """
        List users across all tenants with pagination and filters.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            tenant_id_filter: Filter by tenant ID
            role_id_filter: Filter by role ID
            is_active_filter: Filter by active status
            search_query: Search by email or full name

        Returns:
            Tuple of (user_list, total_count)

        Example:
            >>> service = AdminUserService(db)
            >>> users, total = service.list_all_users(
            ...     page=1,
            ...     page_size=20,
            ...     is_active_filter=True
            ... )
        """
        # Base query
        query = (
            self.db.query(
                User,
                Tenant.name.label('tenant_name'),
                Tenant.status.label('tenant_status'),
                Role.name.label('role_name'),
                Role.display_name.label('role_display_name')
            )
            .join(Tenant, User.tenant_id == Tenant.id)
            .join(Role, User.role_id == Role.id)
        )

        # Apply filters
        if tenant_id_filter:
            query = query.filter(User.tenant_id == tenant_id_filter)

        if role_id_filter:
            query = query.filter(User.role_id == role_id_filter)

        if is_active_filter is not None:
            query = query.filter(User.is_active == is_active_filter)

        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(
                or_(
                    User.email.ilike(search_pattern),
                    User.full_name.ilike(search_pattern)
                )
            )

        # Get total count
        total_count = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        results = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()

        # Get API token counts for users in this page
        user_ids = [user.User.id for user in results]
        token_counts = {}
        if user_ids:
            token_data = (
                self.db.query(
                    ApiToken.user_id,
                    func.count(ApiToken.id).label('count')
                )
                .filter(
                    ApiToken.user_id.in_(user_ids),
                    ApiToken.is_active == True
                )
                .group_by(ApiToken.user_id)
                .all()
            )
            token_counts = {row.user_id: row.count for row in token_data}

        # Build response objects
        user_items = [
            UserListItem(
                id=user.User.id,
                email=user.User.email,
                full_name=user.User.full_name,
                is_active=user.User.is_active,
                is_verified=user.User.is_verified,
                tenant_id=user.User.tenant_id,
                tenant_name=user.tenant_name,
                tenant_status=user.tenant_status,
                role_id=user.User.role_id,
                role_name=user.role_name,
                role_display_name=user.role_display_name,
                last_login=user.User.last_login,
                created_at=user.User.created_at,
                api_token_count=token_counts.get(user.User.id, 0),
            )
            for user in results
        ]

        return user_items, total_count

    def get_user_details(self, user_id: UUID) -> Optional[UserDetailResponse]:
        """
        Get detailed information for a specific user.

        Args:
            user_id: User UUID

        Returns:
            UserDetailResponse with full user info and permissions
            None if user not found

        Example:
            >>> service = AdminUserService(db)
            >>> details = service.get_user_details(user_id)
            >>> if details:
            ...     print(f"User: {details.user.email}")
            ...     print(f"Permissions: {details.permissions}")
        """
        # Get user basic info
        user_data = (
            self.db.query(
                User,
                Tenant.name.label('tenant_name'),
                Tenant.status.label('tenant_status'),
                Role.name.label('role_name'),
                Role.display_name.label('role_display_name')
            )
            .join(Tenant, User.tenant_id == Tenant.id)
            .join(Role, User.role_id == Role.id)
            .filter(User.id == user_id)
            .first()
        )

        if not user_data:
            return None

        # Get API token count
        api_token_count = (
            self.db.query(func.count(ApiToken.id))
            .filter(ApiToken.user_id == user_id, ApiToken.is_active == True)
            .scalar() or 0
        )

        user_item = UserListItem(
            id=user_data.User.id,
            email=user_data.User.email,
            full_name=user_data.User.full_name,
            is_active=user_data.User.is_active,
            is_verified=user_data.User.is_verified,
            tenant_id=user_data.User.tenant_id,
            tenant_name=user_data.tenant_name,
            tenant_status=user_data.tenant_status,
            role_id=user_data.User.role_id,
            role_name=user_data.role_name,
            role_display_name=user_data.role_display_name,
            last_login=user_data.User.last_login,
            created_at=user_data.User.created_at,
            api_token_count=api_token_count,
        )

        # Get user permissions
        permission_service = PermissionService(self.db)
        permissions = permission_service.get_user_permissions(user_data.User)
        permission_list = sorted(list(permissions))

        # Get recent activity metrics
        from app.models import Document, ExtractionJob

        recent_documents = (
            self.db.query(func.count(Document.id))
            .join(Tenant, Document.tenant_id == Tenant.id)
            .filter(Tenant.id == user_data.User.tenant_id)
            .scalar() or 0
        )

        recent_jobs = (
            self.db.query(func.count(ExtractionJob.id))
            .join(Document, ExtractionJob.document_id == Document.id)
            .filter(Document.tenant_id == user_data.User.tenant_id)
            .scalar() or 0
        )

        recent_activity = {
            "documents_uploaded": recent_documents,
            "jobs_created": recent_jobs,
            "api_tokens": api_token_count,
        }

        return UserDetailResponse(
            user=user_item,
            permissions=permission_list,
            recent_activity=recent_activity,
        )

    def update_user_status(
        self,
        user_id: UUID,
        is_active: bool,
        reason: Optional[str] = None
    ) -> User:
        """
        Activate or deactivate a user account.

        Args:
            user_id: User UUID
            is_active: New active status
            reason: Optional reason for status change

        Returns:
            Updated User object

        Raises:
            ValueError: If user not found
            AuthorizationError: If trying to modify platform admin user

        Example:
            >>> service = AdminUserService(db)
            >>> user = service.update_user_status(
            ...     user_id=user_id,
            ...     is_active=False,
            ...     reason='Terms of service violation'
            ... )
        """
        # Get user
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        # Prevent deactivating platform admins
        from app.db.seed import PLATFORM_TENANT_ID
        if user.tenant_id == PLATFORM_TENANT_ID and not is_active:
            raise AuthorizationError("Cannot deactivate platform admin users")

        # Update status
        old_status = user.is_active
        user.is_active = is_active
        user.updated_at = datetime.utcnow()

        # Optionally store reason in user metadata (if we add it later)
        # For now, just update the status

        self.db.commit()
        self.db.refresh(user)

        return user

    def revoke_api_token(
        self,
        token_id: UUID,
        revoked_by_user_id: UUID,
        reason: Optional[str] = None
    ) -> ApiToken:
        """
        Revoke an API token.

        Args:
            token_id: API token UUID
            revoked_by_user_id: ID of the admin user revoking the token
            reason: Optional reason for revocation

        Returns:
            Updated ApiToken object

        Raises:
            ValueError: If token not found

        Example:
            >>> service = AdminUserService(db)
            >>> token = service.revoke_api_token(
            ...     token_id=token_id,
            ...     revoked_by_user_id=admin_user_id,
            ...     reason='Security incident'
            ... )
        """
        # Get token
        token = self.db.query(ApiToken).filter(ApiToken.id == token_id).first()
        if not token:
            raise ValueError("API token not found")

        # Revoke token
        token.is_active = False
        token.revoked_at = datetime.utcnow()
        token.revoked_by_user_id = revoked_by_user_id
        token.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(token)

        return token

    def search_users(self, query: str, limit: int = 10) -> List[UserListItem]:
        """
        Search users by email or name across all tenants.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of UserListItem matching the search

        Example:
            >>> service = AdminUserService(db)
            >>> users = service.search_users('john@example.com')
        """
        users, _ = self.list_all_users(
            page=1,
            page_size=limit,
            search_query=query
        )
        return users

    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User object or None if not found

        Example:
            >>> service = AdminUserService(db)
            >>> user = service.get_user_by_id(user_id)
        """
        return self.db.query(User).filter(User.id == user_id).first()
