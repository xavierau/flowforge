"""Tenant context middleware for multi-tenancy support."""

from typing import Optional
from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError

from app.services.auth_service import auth_service


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and store tenant context from JWT tokens.

    This middleware:
    1. Extracts JWT token from Authorization header (if present)
    2. Decodes token to get tenant_id
    3. Stores tenant_id in request.state for route handlers
    4. Does NOT block requests if token is missing or invalid (handles gracefully)

    The tenant_id can be accessed in route handlers via:
        request.state.tenant_id

    This is useful for:
    - Tenant-specific query filtering
    - Audit logging with tenant context
    - Multi-tenant row-level security

    Note: This middleware runs on ALL requests (including public routes).
          It gracefully handles missing/invalid tokens without raising errors.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Process request to extract tenant context.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response from downstream handler
        """
        # Initialize tenant_id as None (will be set if valid token exists)
        tenant_id: Optional[UUID] = None

        # Try to extract tenant from Authorization header
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")

            try:
                # Decode token (without full validation to avoid duplicate work)
                # The get_current_user dependency will do full validation later
                payload = auth_service.verify_token(token, token_type="access")

                # Extract tenant_id from token
                tenant_id_str = payload.get("tenant_id")
                if tenant_id_str:
                    try:
                        tenant_id = UUID(tenant_id_str)
                    except (ValueError, AttributeError):
                        # Invalid UUID format - log but don't raise
                        pass

            except (JWTError, ValueError):
                # Token is invalid or expired - gracefully ignore
                # The auth dependency will handle the error appropriately
                pass

        # Store tenant_id in request state (None if not found/invalid)
        request.state.tenant_id = tenant_id

        # Also store original user_id if available (useful for logging)
        if tenant_id and auth_header:
            token = auth_header.replace("Bearer ", "")
            try:
                payload = auth_service.verify_token(token, token_type="access")
                user_id_str = payload.get("sub")
                if user_id_str:
                    try:
                        request.state.user_id = UUID(user_id_str)
                    except (ValueError, AttributeError):
                        request.state.user_id = None
            except (JWTError, ValueError):
                request.state.user_id = None
        else:
            request.state.user_id = None

        # Continue to next middleware or route handler
        response: Response = await call_next(request)

        return response


def get_tenant_id(request: Request) -> Optional[UUID]:
    """
    Helper function to get tenant_id from request state.

    This is a convenience function to access tenant_id set by the middleware.

    Args:
        request: FastAPI request object

    Returns:
        Tenant UUID if available, None otherwise

    Example:
        @router.get("/documents")
        async def list_documents(
            request: Request,
            current_user: User = Depends(get_current_active_user)
        ):
            tenant_id = get_tenant_id(request)
            # Query documents filtered by tenant_id
            pass
    """
    return getattr(request.state, "tenant_id", None)


def get_user_id(request: Request) -> Optional[UUID]:
    """
    Helper function to get user_id from request state.

    This is a convenience function to access user_id set by the middleware.

    Args:
        request: FastAPI request object

    Returns:
        User UUID if available, None otherwise

    Example:
        @router.post("/audit-log")
        async def log_action(request: Request):
            user_id = get_user_id(request)
            # Log action with user context
            pass
    """
    return getattr(request.state, "user_id", None)
