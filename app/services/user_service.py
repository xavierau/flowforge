"""User service for business logic and tenant-isolated operations."""

from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from app.models import User, Role, Tenant
from app.services.auth_service import auth_service


class UserService:
    """Service for handling user management operations with tenant isolation."""

    def __init__(self, db: Session):
        """
        Initialize the user service.

        Args:
            db: Database session
        """
        self.db = db

    def get_user_with_details(self, user_id: UUID, tenant_id: UUID) -> Optional[User]:
        """
        Get user with role and tenant relationships loaded (tenant-isolated).

        Args:
            user_id: User ID to fetch
            tenant_id: Tenant ID for isolation

        Returns:
            User object with relationships loaded, or None if not found/different tenant
        """
        return (
            self.db.query(User)
            .options(
                joinedload(User.role),
                joinedload(User.tenant)
            )
            .filter(
                and_(
                    User.id == user_id,
                    User.tenant_id == tenant_id
                )
            )
            .first()
        )

    def list_tenant_users(
        self,
        tenant_id: UUID,
        limit: int = 50,
        offset: int = 0,
        role_id: Optional[UUID] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[List[User], int]:
        """
        List users in a tenant with pagination and filters.

        Args:
            tenant_id: Tenant ID for isolation
            limit: Maximum number of users to return
            offset: Number of users to skip
            role_id: Optional role filter
            is_active: Optional active status filter

        Returns:
            Tuple of (list of users, total count)
        """
        # Build query with tenant isolation
        query = (
            self.db.query(User)
            .options(joinedload(User.role))
            .filter(User.tenant_id == tenant_id)
        )

        # Apply filters
        if role_id is not None:
            query = query.filter(User.role_id == role_id)

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        # Get total count before pagination
        total = query.count()

        # Apply pagination
        users = (
            query
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        return users, total

    def update_user_profile(
        self,
        user: User,
        full_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        locale: Optional[str] = None
    ) -> User:
        """
        Update user's own profile fields.

        Args:
            user: User to update
            full_name: New full name (if provided)
            avatar_url: New avatar URL (if provided)
            locale: New locale (if provided)

        Returns:
            Updated user object
        """
        if full_name is not None:
            user.full_name = full_name

        if avatar_url is not None:
            user.avatar_url = avatar_url

        if locale is not None:
            user.locale = locale

        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)

        return user

    def update_user_password(self, user: User, new_password: str) -> None:
        """
        Update user's password (already verified).

        Args:
            user: User to update
            new_password: New plaintext password to hash and store
        """
        user.hashed_password = auth_service.hash_password(new_password)
        user.updated_at = datetime.utcnow()

        # Invalidate all refresh tokens (force re-login on all devices)
        user.refresh_token = None

        self.db.commit()

    def update_user_by_admin(
        self,
        user: User,
        role_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        full_name: Optional[str] = None
    ) -> User:
        """
        Update user fields (admin operation).

        Args:
            user: User to update
            role_id: New role ID (if provided)
            is_active: New active status (if provided)
            full_name: New full name (if provided)

        Returns:
            Updated user object
        """
        if role_id is not None:
            # Verify role exists
            role = self.db.query(Role).filter(Role.id == role_id).first()
            if not role:
                raise ValueError("Role not found")
            user.role_id = role_id

        if is_active is not None:
            user.is_active = is_active

        if full_name is not None:
            user.full_name = full_name

        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)

        return user

    def soft_delete_user(self, user: User) -> None:
        """
        Soft delete user by setting is_active=False.

        Args:
            user: User to deactivate
        """
        user.is_active = False
        user.updated_at = datetime.utcnow()

        # Invalidate refresh token
        user.refresh_token = None

        self.db.commit()

    def hard_delete_user(self, user: User) -> None:
        """
        Permanently delete user from database.

        Args:
            user: User to delete
        """
        self.db.delete(user)
        self.db.commit()

    def count_active_admins_in_tenant(self, tenant_id: UUID) -> int:
        """
        Count active users with admin role in a tenant.

        Args:
            tenant_id: Tenant ID to check

        Returns:
            Number of active admin users
        """
        admin_role = self.db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            return 0

        count = (
            self.db.query(User)
            .filter(
                and_(
                    User.tenant_id == tenant_id,
                    User.role_id == admin_role.id,
                    User.is_active == True
                )
            )
            .count()
        )

        return count

    def is_last_active_admin(self, user: User) -> bool:
        """
        Check if user is the last active admin in their tenant.

        Args:
            user: User to check

        Returns:
            True if user is the last active admin
        """
        # Check if user is an admin
        if not user.role or user.role.name != "admin":
            return False

        # Check if user is active
        if not user.is_active:
            return False

        # Count active admins (should be 1 if this is the last one)
        active_admin_count = self.count_active_admins_in_tenant(user.tenant_id)

        return active_admin_count == 1

    def user_exists_by_email(self, email: str) -> bool:
        """
        Check if a user with given email already exists.

        Args:
            email: Email address to check

        Returns:
            True if user exists, False otherwise
        """
        return self.db.query(User).filter(User.email == email.lower()).first() is not None

    def create_invitation(
        self,
        email: str,
        role_id: UUID,
        tenant_id: UUID,
        invited_by_user_id: UUID
    ) -> Tuple[User, str]:
        """
        Create an invitation for a new user.

        Creates a user record with a verification token instead of password.
        The user won't be able to login until they set their password via the invitation link.

        Args:
            email: Email address to invite
            role_id: Role to assign
            tenant_id: Tenant to add user to
            invited_by_user_id: ID of user sending invitation

        Returns:
            Tuple of (created User object, invitation_token)

        Raises:
            ValueError: If role doesn't exist
        """
        # Verify role exists
        role = self.db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise ValueError("Role not found")

        # Generate invitation token (reuse email verification token field)
        invitation_token = auth_service.generate_verification_token()

        # Create user with temporary password (they'll set real password via invitation link)
        # Set is_active=False until they accept invitation
        # Set invitation expiration to 7 days from now
        invitation_expires = datetime.utcnow() + timedelta(days=7)

        user = User(
            email=email.lower(),
            hashed_password=auth_service.hash_password(auth_service.generate_reset_token()),  # Temporary, unused
            tenant_id=tenant_id,
            role_id=role_id,
            is_active=False,  # Activate on invitation acceptance
            is_verified=False,
            email_verification_token=invitation_token,
            invitation_expires=invitation_expires,
            locale="en"
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user, invitation_token

    def get_role_by_id(self, role_id: UUID) -> Optional[Role]:
        """
        Get role by ID.

        Args:
            role_id: Role ID to fetch

        Returns:
            Role object or None if not found
        """
        return self.db.query(Role).filter(Role.id == role_id).first()

    def list_roles(self) -> List[Role]:
        """
        List all available roles.

        Returns:
            List of Role objects
        """
        return self.db.query(Role).order_by(Role.name).all()

    def list_pending_invitations(self, tenant_id: UUID) -> Tuple[List[User], int]:
        """
        List pending invitations (users with is_active=False and is_verified=False).

        Args:
            tenant_id: Tenant ID for isolation

        Returns:
            Tuple of (list of pending invitation users, total count)
        """
        query = (
            self.db.query(User)
            .options(joinedload(User.role))
            .filter(
                and_(
                    User.tenant_id == tenant_id,
                    User.is_active == False,
                    User.is_verified == False,
                    User.email_verification_token.isnot(None)
                )
            )
        )

        total = query.count()
        users = query.order_by(User.created_at.desc()).all()

        return users, total

    def get_pending_invitation(self, user_id: UUID, tenant_id: UUID) -> Optional[User]:
        """
        Get a pending invitation by user ID (tenant-isolated).

        Args:
            user_id: User ID to fetch
            tenant_id: Tenant ID for isolation

        Returns:
            User object if found and is a pending invitation, None otherwise
        """
        return (
            self.db.query(User)
            .options(joinedload(User.role))
            .filter(
                and_(
                    User.id == user_id,
                    User.tenant_id == tenant_id,
                    User.is_active == False,
                    User.is_verified == False,
                    User.email_verification_token.isnot(None)
                )
            )
            .first()
        )

    def regenerate_invitation_token(self, user: User) -> str:
        """
        Regenerate invitation token for a pending user.

        Args:
            user: User to regenerate token for

        Returns:
            New invitation token

        Raises:
            ValueError: If user is not a pending invitation
        """
        if user.is_active or user.is_verified:
            raise ValueError("Cannot regenerate token for active or verified user")

        # Generate new invitation token and reset expiration (7 days from now)
        new_token = auth_service.generate_verification_token()
        user.email_verification_token = new_token
        user.invitation_expires = datetime.utcnow() + timedelta(days=7)
        user.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(user)

        return new_token
