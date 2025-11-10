"""Exception classes for the application."""

from app.exceptions.auth import (
    AuthenticationError,
    InvalidTokenError,
    ExpiredTokenError,
    AuthorizationError,
    InsufficientPermissionsError,
    InsufficientRoleError,
    InactiveUserError,
    UserNotFoundError,
)

__all__ = [
    "AuthenticationError",
    "InvalidTokenError",
    "ExpiredTokenError",
    "AuthorizationError",
    "InsufficientPermissionsError",
    "InsufficientRoleError",
    "InactiveUserError",
    "UserNotFoundError",
]
