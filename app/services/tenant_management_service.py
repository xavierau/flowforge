"""Service for tenant management operations (super admin only)."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Tenant, User, ApiToken, Subscription
from app.schemas.admin import (
    TenantListItem, TenantDetailResponse, TenantSubscriptionInfo,
    UserListItem, ApiTokenListItem
)
from app.services.admin_metrics_service import AdminMetricsService
from app.exceptions.auth import AuthorizationError


class TenantManagementService:
    """
    Service for managing tenants from super admin perspective.

    This service provides tenant operations including:
    - Tenant details retrieval
    - User listing for a tenant
    - API token listing for a tenant
    - Tenant status updates (suspend/activate)

    All methods are designed for super admin use only.
    Security is enforced at the API layer via require_super_admin dependency.
    """

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.metrics_service = AdminMetricsService(db)

    def get_tenant_details(self, tenant_id: UUID) -> Optional[TenantDetailResponse]:
        """
        Get detailed information for a specific tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            TenantDetailResponse with full tenant info, subscription, and metrics
            None if tenant not found

        Example:
            >>> service = TenantManagementService(db)
            >>> details = service.get_tenant_details(tenant_id)
            >>> if details:
            ...     print(f"Tenant: {details.tenant.name}")
        """
        # Get tenant basic info using metrics service
        tenants, _ = self.metrics_service.get_tenant_list_with_metrics(
            page=1,
            page_size=1,
            search_query=str(tenant_id)  # Search by ID
        )

        if not tenants:
            return None

        tenant_item = tenants[0]

        # Get subscription info
        subscription = self.db.query(Subscription).filter(
            Subscription.tenant_id == tenant_id
        ).first()

        subscription_info = None
        if subscription:
            subscription_info = TenantSubscriptionInfo(
                plan=subscription.plan,
                status=subscription.status,
                stripe_subscription_id=subscription.stripe_subscription_id,
                stripe_price_id=subscription.stripe_price_id,
                current_period_start=subscription.current_period_start,
                current_period_end=subscription.current_period_end,
                cancel_at_period_end=subscription.cancel_at_period_end,
                features=subscription.features or {},
            )

        # Get metrics
        metrics = self.metrics_service.get_tenant_metrics(tenant_id)

        # Get counts
        user_count = self.db.query(User).filter(User.tenant_id == tenant_id).count()
        api_token_count = (
            self.db.query(ApiToken)
            .filter(ApiToken.tenant_id == tenant_id, ApiToken.is_active == True)
            .count()
        )

        return TenantDetailResponse(
            tenant=tenant_item,
            subscription=subscription_info,
            metrics=metrics,
            user_count=user_count,
            api_token_count=api_token_count,
        )

    def get_tenant_users(self, tenant_id: UUID) -> List[UserListItem]:
        """
        Get all users for a specific tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            List of UserListItem with user and role information

        Example:
            >>> service = TenantManagementService(db)
            >>> users = service.get_tenant_users(tenant_id)
            >>> for user in users:
            ...     print(f"{user.email} - {user.role_display_name}")
        """
        from app.models import Role

        users = (
            self.db.query(
                User,
                Tenant.name.label('tenant_name'),
                Tenant.status.label('tenant_status'),
                Role.name.label('role_name'),
                Role.display_name.label('role_display_name')
            )
            .join(Tenant, User.tenant_id == Tenant.id)
            .join(Role, User.role_id == Role.id)
            .filter(User.tenant_id == tenant_id)
            .order_by(User.created_at.desc())
            .all()
        )

        # Get API token counts for users
        from sqlalchemy import func
        token_counts = (
            self.db.query(
                ApiToken.user_id,
                func.count(ApiToken.id).label('count')
            )
            .filter(
                ApiToken.tenant_id == tenant_id,
                ApiToken.is_active == True
            )
            .group_by(ApiToken.user_id)
            .all()
        )
        token_count_map = {row.user_id: row.count for row in token_counts}

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
                api_token_count=token_count_map.get(user.User.id, 0),
            )
            for user in users
        ]

        return user_items

    def get_tenant_tokens(self, tenant_id: UUID) -> List[ApiTokenListItem]:
        """
        Get all active API tokens for a specific tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            List of ApiTokenListItem

        Example:
            >>> service = TenantManagementService(db)
            >>> tokens = service.get_tenant_tokens(tenant_id)
            >>> for token in tokens:
            ...     print(f"{token.name} - Last used: {token.last_used_at}")
        """
        tokens = (
            self.db.query(
                ApiToken,
                User.email.label('user_email'),
                Tenant.name.label('tenant_name')
            )
            .join(User, ApiToken.user_id == User.id)
            .join(Tenant, ApiToken.tenant_id == Tenant.id)
            .filter(
                ApiToken.tenant_id == tenant_id,
                ApiToken.is_active == True
            )
            .order_by(ApiToken.created_at.desc())
            .all()
        )

        token_items = [
            ApiTokenListItem(
                id=token.ApiToken.id,
                name=token.ApiToken.name,
                token_prefix=token.ApiToken.token_prefix,
                scopes=token.ApiToken.scopes or [],
                is_active=token.ApiToken.is_active,
                expires_at=token.ApiToken.expires_at,
                last_used_at=token.ApiToken.last_used_at,
                last_used_ip=token.ApiToken.last_used_ip,
                created_at=token.ApiToken.created_at,
                user_id=token.ApiToken.user_id,
                user_email=token.user_email,
                tenant_id=token.ApiToken.tenant_id,
                tenant_name=token.tenant_name,
            )
            for token in tokens
        ]

        return token_items

    def update_tenant_status(
        self,
        tenant_id: UUID,
        new_status: str,
        reason: Optional[str] = None
    ) -> Tenant:
        """
        Update tenant status (suspend/activate/cancel).

        Args:
            tenant_id: Tenant UUID
            new_status: New status (active, suspended, cancelled)
            reason: Optional reason for status change

        Returns:
            Updated Tenant object

        Raises:
            ValueError: If status is invalid
            AuthorizationError: If trying to modify platform tenant

        Example:
            >>> service = TenantManagementService(db)
            >>> tenant = service.update_tenant_status(
            ...     tenant_id=tenant_id,
            ...     new_status='suspended',
            ...     reason='Payment overdue'
            ... )
        """
        # Validate status
        valid_statuses = ['active', 'suspended', 'cancelled']
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

        # Get tenant
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError("Tenant not found")

        # Prevent modifying platform tenant
        from app.db.seed import PLATFORM_TENANT_ID
        if tenant.id == PLATFORM_TENANT_ID:
            raise AuthorizationError("Cannot modify platform tenant")

        # Update status
        old_status = tenant.status
        tenant.status = new_status
        tenant.updated_at = datetime.utcnow()

        # Optionally store reason in metadata
        if reason:
            metadata = tenant.tenant_metadata or {}
            metadata['status_changes'] = metadata.get('status_changes', [])
            metadata['status_changes'].append({
                'from': old_status,
                'to': new_status,
                'reason': reason,
                'timestamp': datetime.utcnow().isoformat()
            })
            tenant.tenant_metadata = metadata

        self.db.commit()
        self.db.refresh(tenant)

        return tenant

    def get_tenant_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        """
        Get tenant by ID.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Tenant object or None if not found

        Example:
            >>> service = TenantManagementService(db)
            >>> tenant = service.get_tenant_by_id(tenant_id)
        """
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
