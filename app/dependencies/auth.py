"""Authentication and authorization dependencies for FastAPI routes."""

from typing import Callable, List, Optional
from uuid import UUID

from fastapi import Depends, Header, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, ApiToken
from app.services.auth_service import auth_service
from app.services.permission_service import PermissionService
from app.services.api_token_service import ApiTokenService
from app.exceptions.auth import (
    AuthenticationError,
    InvalidTokenError,
    ExpiredTokenError,
    InsufficientPermissionsError,
    InsufficientRoleError,
    InactiveUserError,
    UserNotFoundError,
)


# OAuth2 scheme for token extraction from Authorization header
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=True
)


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Extract and validate JWT token, return authenticated user.

    This dependency:
    1. Extracts JWT from Authorization header (Bearer token)
    2. Validates origin (JWT tokens only work from allowed domains)
    3. Validates token signature and expiration
    4. Queries user from database
    5. Returns User object if valid

    Args:
        request: FastAPI request object (for origin validation)
        token: JWT token from Authorization header
        db: Database session

    Returns:
        Authenticated User object

    Raises:
        InvalidTokenError: Token is malformed or has wrong type
        ExpiredTokenError: Token has expired
        AuthenticationError: Token validation failed or origin not allowed
        UserNotFoundError: User in token doesn't exist

    Example:
        @router.get("/profile")
        async def get_profile(current_user: User = Depends(get_current_user)):
            return {"email": current_user.email}
    """
    # Validate origin for JWT tokens (security: only allow from trusted domains)
    from app.config import settings

    origin = request.headers.get("origin") or request.headers.get("referer", "")
    if origin and origin.endswith("/"):
        origin = origin.rstrip("/")

    allowed_origins = settings.jwt_allowed_origins_list
    if allowed_origins:  # Only enforce if configured
        # Check if origin matches any allowed origin
        origin_allowed = False
        for allowed_origin in allowed_origins:
            if origin.startswith(allowed_origin):
                origin_allowed = True
                break

        if not origin_allowed:
            raise AuthenticationError(
                f"JWT authentication not allowed from this origin. "
                f"Please use an API token for server-to-server requests."
            )

    try:
        # Verify and decode token
        payload = auth_service.verify_token(token, token_type="access")

        # Extract user ID from token
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise InvalidTokenError("Token missing user ID")

        # Convert to UUID
        try:
            user_id = UUID(user_id_str)
        except (ValueError, AttributeError):
            raise InvalidTokenError("Invalid user ID format in token")

    except ValueError as e:
        # Token type mismatch (e.g., refresh token used instead of access token)
        raise InvalidTokenError(str(e))
    except JWTError as e:
        # Check if it's an expiration error
        error_msg = str(e).lower()
        if "expired" in error_msg:
            raise ExpiredTokenError()
        # Other JWT errors (invalid signature, malformed token, etc.)
        raise InvalidTokenError(f"Token validation failed: {str(e)}")

    # Query user from database
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise UserNotFoundError("User not found")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Ensure the authenticated user has an active account.

    This dependency builds on get_current_user and adds an active status check.
    Use this for routes that should only be accessible to active users.

    Args:
        current_user: User object from get_current_user

    Returns:
        Active User object

    Raises:
        InactiveUserError: User account is not active

    Example:
        @router.post("/documents")
        async def create_document(
            current_user: User = Depends(get_current_active_user)
        ):
            # Only active users can create documents
            pass
    """
    if not current_user.is_active:
        raise InactiveUserError()

    return current_user


def require_permission(permission: str) -> Callable:
    """
    Dependency factory for requiring a specific permission.

    Creates a dependency function that checks if the current user has
    the specified permission (via role or custom grants).

    Args:
        permission: Permission name (e.g., "documents:create", "schemas:delete")

    Returns:
        Dependency function that validates permission

    Raises:
        InsufficientPermissionsError: User lacks the required permission

    Example:
        @router.delete("/documents/{doc_id}")
        async def delete_document(
            doc_id: str,
            current_user: User = Depends(require_permission("documents:delete"))
        ):
            # Only users with "documents:delete" permission can access
            pass
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> User:
        """Check if user has the required permission."""
        permission_service = PermissionService(db)

        if not permission_service.user_has_permission(current_user, permission):
            raise InsufficientPermissionsError(permission)

        return current_user

    return permission_checker


def require_role(role: str) -> Callable:
    """
    Dependency factory for requiring a specific role.

    Creates a dependency function that checks if the current user has
    the specified role.

    Args:
        role: Role name (e.g., "admin", "member", "viewer")

    Returns:
        Dependency function that validates role

    Raises:
        InsufficientRoleError: User lacks the required role

    Example:
        @router.get("/admin/users")
        async def list_all_users(
            current_user: User = Depends(require_role("admin"))
        ):
            # Only admin role can access
            pass
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> User:
        """Check if user has the required role."""
        permission_service = PermissionService(db)

        if not permission_service.user_has_role(current_user, role):
            raise InsufficientRoleError(role)

        return current_user

    return role_checker


def require_any_permission(permissions: List[str]) -> Callable:
    """
    Dependency factory for requiring at least one of multiple permissions.

    Creates a dependency function that checks if the current user has
    at least one of the specified permissions (OR logic).

    Args:
        permissions: List of permission names

    Returns:
        Dependency function that validates permissions

    Raises:
        InsufficientPermissionsError: User lacks all specified permissions

    Example:
        @router.put("/documents/{doc_id}")
        async def update_document(
            doc_id: str,
            current_user: User = Depends(
                require_any_permission([
                    "documents:update:own",
                    "documents:update:all"
                ])
            )
        ):
            # User needs either permission to update
            pass
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> User:
        """Check if user has at least one of the required permissions."""
        permission_service = PermissionService(db)

        if not permission_service.user_has_any_permission(current_user, permissions):
            perms_str = ", ".join(permissions)
            raise InsufficientPermissionsError(f"One of: {perms_str}")

        return current_user

    return permission_checker


def require_all_permissions(permissions: List[str]) -> Callable:
    """
    Dependency factory for requiring all of multiple permissions.

    Creates a dependency function that checks if the current user has
    all of the specified permissions (AND logic).

    Args:
        permissions: List of permission names

    Returns:
        Dependency function that validates permissions

    Raises:
        InsufficientPermissionsError: User lacks one or more required permissions

    Example:
        @router.post("/schemas/{schema_id}/publish")
        async def publish_schema(
            schema_id: str,
            current_user: User = Depends(
                require_all_permissions([
                    "schemas:read",
                    "schemas:publish"
                ])
            )
        ):
            # User needs both permissions
            pass
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> User:
        """Check if user has all of the required permissions."""
        permission_service = PermissionService(db)

        if not permission_service.user_has_all_permissions(current_user, permissions):
            perms_str = ", ".join(permissions)
            raise InsufficientPermissionsError(f"All of: {perms_str}")

        return current_user

    return permission_checker


async def get_current_user_from_api_token(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> tuple[User, Optional[ApiToken]]:
    """
    Authenticate using API token from Authorization header.

    Supports two formats:
    - Authorization: Bearer sk_live_...
    - Authorization: sk_live_...

    Args:
        request: FastAPI request object
        authorization: Authorization header value
        db: Database session

    Returns:
        Tuple of (User, ApiToken) if valid

    Raises:
        InvalidTokenError: Token is invalid, expired, or revoked
        UserNotFoundError: User associated with token not found
        InactiveUserError: User account is not active

    Example:
        @router.get("/api/v1/documents")
        async def list_documents(
            user_info: tuple = Depends(get_current_user_from_api_token)
        ):
            user, api_token = user_info
            # Use user and api_token for authorization
    """
    # Extract token from header
    token = ApiTokenService.extract_token_from_header(authorization)

    if not token:
        raise InvalidTokenError("Missing or invalid API token")

    # Extract token prefix for efficient lookup
    token_parts = token.replace(ApiTokenService.TOKEN_PREFIX, "").split("_")
    if len(token_parts) < 2:
        raise InvalidTokenError("Invalid API token format")

    identifier = token_parts[0]
    token_prefix = f"{ApiTokenService.TOKEN_PREFIX}{identifier[:8]}"

    # Query potential tokens by prefix
    potential_tokens = (
        db.query(ApiToken)
        .filter(
            ApiToken.token_prefix == token_prefix,
            ApiToken.is_active == True
        )
        .all()
    )

    # Verify hash
    matching_token = None
    for api_token in potential_tokens:
        if ApiTokenService.verify_token(token, api_token.token_hash):
            matching_token = api_token
            break

    if not matching_token:
        raise InvalidTokenError("Invalid API token")

    # Check expiration
    if ApiTokenService.is_token_expired(matching_token.expires_at):
        raise InvalidTokenError("API token has expired")

    # Update last_used_at and IP (don't block on this)
    # Consider making this async in production
    try:
        matching_token.last_used_at = __import__('datetime').datetime.utcnow()
        matching_token.last_used_ip = request.client.host if request.client else None
        db.commit()
    except Exception:
        db.rollback()
        # Don't fail request if usage tracking fails

    # Get user
    user = db.query(User).filter(User.id == matching_token.user_id).first()
    if not user:
        raise UserNotFoundError("User not found")

    if not user.is_active:
        raise InactiveUserError()

    # Store token scopes in request state for permission checks
    request.state.api_token_scopes = matching_token.scopes
    request.state.api_token = matching_token

    return user, matching_token


async def get_current_user_flexible(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Accept either JWT or API token authentication.

    This dependency tries JWT authentication first, then falls back to API token.
    Use this for endpoints that support both authentication methods.

    JWT tokens are validated against allowed origins (frontend domains only).
    API tokens (sk_*) can be used from any domain (no origin restriction).

    Args:
        request: FastAPI request object
        token: JWT token from OAuth2 scheme
        authorization: Authorization header (for API tokens)
        db: Database session

    Returns:
        Authenticated User object

    Raises:
        AuthenticationError: Both authentication methods failed

    Example:
        @router.get("/api/v1/profile")
        async def get_profile(
            current_user: User = Depends(get_current_user_flexible)
        ):
            # Works with both JWT and API tokens
            return {"email": current_user.email}
    """
    # Try JWT authentication first (with origin validation)
    if token and not token.startswith(ApiTokenService.TOKEN_PREFIX):
        try:
            return await get_current_user(request=request, token=token, db=db)
        except (InvalidTokenError, ExpiredTokenError, AuthenticationError):
            pass  # Fall through to API token auth

    # Try API token authentication (no origin restriction)
    if authorization:
        try:
            user, _ = await get_current_user_from_api_token(
                request=request,
                authorization=authorization,
                db=db
            )
            return user
        except (InvalidTokenError, InactiveUserError, UserNotFoundError):
            pass

    raise AuthenticationError("Authentication required")


def require_verified_email() -> Callable:
    """
    Dependency factory for requiring email verification.

    Creates a dependency function that checks if the current user has
    verified their email address.

    Returns:
        Dependency function that validates email verification

    Raises:
        AuthorizationError: User has not verified their email

    Example:
        @router.post("/documents/extract")
        async def extract_document(
            current_user: User = Depends(require_verified_email())
        ):
            # Only users with verified emails can extract documents
            pass
    """
    async def verification_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        """Check if user has verified their email."""
        if not current_user.is_verified:
            from app.exceptions.auth import AuthorizationError
            raise AuthorizationError("Email verification required")

        return current_user

    return verification_checker


async def require_super_admin(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency for requiring super admin access.

    This dependency checks if the current user has platform admin privileges
    by verifying either:
    - platform_admin role OR
    - platform:super_admin permission

    Args:
        request: FastAPI request object (for audit logging)
        current_user: Authenticated active user
        db: Database session

    Returns:
        User object if user has super admin privileges

    Raises:
        InsufficientPermissionsError: User lacks super admin privileges

    Example:
        @router.get("/admin/dashboard")
        async def get_admin_dashboard(
            current_user: User = Depends(require_super_admin)
        ):
            # Only super admins can access this endpoint
            pass

    Security Notes:
        - JWT-only (API tokens are NOT supported for super admin endpoints)
        - Audit logging is applied via middleware
        - Origin validation is enforced via JWT authentication
    """
    permission_service = PermissionService(db)

    # Check for platform_admin role OR platform:super_admin permission
    has_platform_admin_role = permission_service.user_has_role(current_user, "platform_admin")
    has_super_admin_permission = permission_service.user_has_permission(current_user, "platform:super_admin")

    if not (has_platform_admin_role or has_super_admin_permission):
        raise InsufficientPermissionsError("Super admin access required")

    # Add user to request state for audit middleware
    request.state.user = current_user

    return current_user


def require_permission_flexible(permission: str) -> Callable:
    """
    Dependency factory for requiring a specific permission with flexible authentication.

    Supports both JWT tokens (from login) and API tokens (sk_live_...).

    Creates a dependency function that checks if the current user has
    the specified permission (via role or custom grants), accepting
    either JWT or API token authentication.

    Args:
        permission: Permission name (e.g., "documents:create", "schemas:delete")

    Returns:
        Dependency function that validates permission

    Raises:
        InsufficientPermissionsError: User lacks the required permission
        AuthenticationError: Authentication failed

    Example:
        @router.post("/api/v1/jobs/extract")
        async def extract_document(
            current_user: User = Depends(require_permission_flexible("documents:create"))
        ):
            # Works with both JWT and API tokens
            pass
    """
    async def permission_checker(
        request: Request,
        current_user: User = Depends(get_current_user_flexible),
        db: Session = Depends(get_db)
    ) -> User:
        """Check if user has the required permission."""
        # Check if user is active
        if not current_user.is_active:
            raise InactiveUserError()

        # CRITICAL: API tokens use ONLY scope-based authorization
        # JWT tokens use ONLY role-based authorization
        if hasattr(request.state, "api_token_scopes"):
            # API token authentication: check scopes ONLY
            api_token_scopes = request.state.api_token_scopes or []
            if permission not in api_token_scopes:
                raise InsufficientPermissionsError(
                    f"API token missing required scope: {permission}"
                )
            # Early return - API tokens bypass role-based permission checks
            return current_user

        # JWT token authentication: check role-based permissions ONLY
        permission_service = PermissionService(db)
        if not permission_service.user_has_permission(current_user, permission):
            raise InsufficientPermissionsError(permission)

        return current_user

    return permission_checker
