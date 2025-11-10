"""Authentication and authorization exception classes."""

from fastapi import HTTPException, status


class AuthenticationError(HTTPException):
    """Base exception for authentication failures (401 Unauthorized)."""

    def __init__(
        self,
        detail: str = "Could not validate credentials",
        headers: dict = None
    ):
        """
        Initialize authentication error.

        Args:
            detail: Error message
            headers: Optional HTTP headers (e.g., WWW-Authenticate)
        """
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers=headers or {"WWW-Authenticate": "Bearer"}
        )


class InvalidTokenError(AuthenticationError):
    """Token is invalid, malformed, or has wrong type."""

    def __init__(self, detail: str = "Invalid authentication token"):
        """
        Initialize invalid token error.

        Args:
            detail: Error message
        """
        super().__init__(detail=detail)


class ExpiredTokenError(AuthenticationError):
    """Token has expired."""

    def __init__(self, detail: str = "Authentication token has expired"):
        """
        Initialize expired token error.

        Args:
            detail: Error message
        """
        super().__init__(detail=detail)


class AuthorizationError(HTTPException):
    """Base exception for authorization failures (403 Forbidden)."""

    def __init__(self, detail: str = "Insufficient permissions"):
        """
        Initialize authorization error.

        Args:
            detail: Error message
        """
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class InsufficientPermissionsError(AuthorizationError):
    """User lacks required permissions."""

    def __init__(self, required_permission: str = None):
        """
        Initialize insufficient permissions error.

        Args:
            required_permission: The permission that was required
        """
        detail = "Insufficient permissions"
        if required_permission:
            detail = f"Missing required permission: {required_permission}"
        super().__init__(detail=detail)


class InsufficientRoleError(AuthorizationError):
    """User lacks required role."""

    def __init__(self, required_role: str = None):
        """
        Initialize insufficient role error.

        Args:
            required_role: The role that was required
        """
        detail = "Insufficient role"
        if required_role:
            detail = f"Required role: {required_role}"
        super().__init__(detail=detail)


class InactiveUserError(AuthorizationError):
    """User account is inactive or disabled."""

    def __init__(self, detail: str = "User account is inactive"):
        """
        Initialize inactive user error.

        Args:
            detail: Error message
        """
        super().__init__(detail=detail)


class UserNotFoundError(HTTPException):
    """User referenced in token does not exist in database."""

    def __init__(self, detail: str = "User not found"):
        """
        Initialize user not found error.

        Args:
            detail: Error message
        """
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )
