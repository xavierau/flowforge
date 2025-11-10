"""FastAPI dependency functions."""

from app.dependencies.auth import (
    get_current_user,
    get_current_active_user,
    require_permission,
    require_permission_flexible,
    require_role,
    require_any_permission,
    require_all_permissions,
    require_verified_email,
)

__all__ = [
    "get_current_user",
    "get_current_active_user",
    "require_permission",
    "require_permission_flexible",
    "require_role",
    "require_any_permission",
    "require_all_permissions",
    "require_verified_email",
]
