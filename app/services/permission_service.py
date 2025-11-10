"""Permission service for RBAC and custom permissions."""

from typing import List, Set
from sqlalchemy.orm import Session

from app.models import User, Role, Permission, RolePermission, UserPermission


class PermissionService:
    """Service for handling permission checks and management."""

    def __init__(self, db: Session):
        """
        Initialize the permission service.

        Args:
            db: Database session
        """
        self.db = db

    def get_user_permissions(self, user: User) -> Set[str]:
        """
        Get all permissions for a user (role-based + custom).

        Args:
            user: The user to get permissions for

        Returns:
            Set of permission names (e.g., {"documents:create", "schemas:read"})
        """
        permissions = set()

        # Get role-based permissions
        if user.role:
            role_permissions = (
                self.db.query(Permission.name)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .filter(RolePermission.role_id == user.role_id)
                .all()
            )
            permissions.update(perm[0] for perm in role_permissions)

        # Get custom user permissions
        user_permissions = (
            self.db.query(Permission.name, UserPermission.granted)
            .join(UserPermission, UserPermission.permission_id == Permission.id)
            .filter(UserPermission.user_id == user.id)
            .all()
        )

        # Apply custom permissions (grants and revocations)
        for perm_name, granted in user_permissions:
            if granted:
                permissions.add(perm_name)
            else:
                permissions.discard(perm_name)  # Revoke permission

        return permissions

    def user_has_permission(self, user: User, permission: str) -> bool:
        """
        Check if a user has a specific permission.

        Args:
            user: The user to check
            permission: The permission name (e.g., "documents:create")

        Returns:
            True if user has the permission, False otherwise
        """
        user_permissions = self.get_user_permissions(user)
        return permission in user_permissions

    def user_has_any_permission(self, user: User, permissions: List[str]) -> bool:
        """
        Check if a user has any of the specified permissions.

        Args:
            user: The user to check
            permissions: List of permission names

        Returns:
            True if user has at least one permission, False otherwise
        """
        user_permissions = self.get_user_permissions(user)
        return bool(set(permissions) & user_permissions)

    def user_has_all_permissions(self, user: User, permissions: List[str]) -> bool:
        """
        Check if a user has all of the specified permissions.

        Args:
            user: The user to check
            permissions: List of permission names

        Returns:
            True if user has all permissions, False otherwise
        """
        user_permissions = self.get_user_permissions(user)
        return all(perm in user_permissions for perm in permissions)

    def user_has_role(self, user: User, role_name: str) -> bool:
        """
        Check if a user has a specific role.

        Args:
            user: The user to check
            role_name: The role name (e.g., "admin", "member")

        Returns:
            True if user has the role, False otherwise
        """
        return user.role and user.role.name == role_name

    def grant_permission(self, user_id: str, permission_id: str) -> UserPermission:
        """
        Grant a custom permission to a user.

        Args:
            user_id: The user's ID
            permission_id: The permission's ID

        Returns:
            The created or updated UserPermission
        """
        # Check if permission already exists
        user_perm = (
            self.db.query(UserPermission)
            .filter(
                UserPermission.user_id == user_id,
                UserPermission.permission_id == permission_id
            )
            .first()
        )

        if user_perm:
            # Update existing permission
            user_perm.granted = True
        else:
            # Create new permission grant
            user_perm = UserPermission(
                user_id=user_id,
                permission_id=permission_id,
                granted=True
            )
            self.db.add(user_perm)

        self.db.commit()
        self.db.refresh(user_perm)
        return user_perm

    def revoke_permission(self, user_id: str, permission_id: str) -> UserPermission:
        """
        Revoke a custom permission from a user.

        Args:
            user_id: The user's ID
            permission_id: The permission's ID

        Returns:
            The updated UserPermission
        """
        # Check if permission exists
        user_perm = (
            self.db.query(UserPermission)
            .filter(
                UserPermission.user_id == user_id,
                UserPermission.permission_id == permission_id
            )
            .first()
        )

        if user_perm:
            # Update to revoked
            user_perm.granted = False
        else:
            # Create revocation entry
            user_perm = UserPermission(
                user_id=user_id,
                permission_id=permission_id,
                granted=False
            )
            self.db.add(user_perm)

        self.db.commit()
        self.db.refresh(user_perm)
        return user_perm

    def remove_custom_permission(self, user_id: str, permission_id: str) -> bool:
        """
        Remove a custom permission entry (both grants and revocations).

        Args:
            user_id: The user's ID
            permission_id: The permission's ID

        Returns:
            True if permission was removed, False if not found
        """
        user_perm = (
            self.db.query(UserPermission)
            .filter(
                UserPermission.user_id == user_id,
                UserPermission.permission_id == permission_id
            )
            .first()
        )

        if user_perm:
            self.db.delete(user_perm)
            self.db.commit()
            return True

        return False
