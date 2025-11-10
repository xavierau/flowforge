"""Middleware for admin audit logging."""

import uuid
from datetime import datetime
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.database import SessionLocal
from app.models import AdminAuditLog


class AdminAuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all admin API endpoint accesses.

    This middleware intercepts all requests to /admin/* endpoints and creates
    audit log entries in the database. It captures:
    - User who made the request
    - Action performed (endpoint + method)
    - Resource affected (extracted from path parameters)
    - Request details (IP, user agent)
    - Response details (status code, errors)

    The middleware runs asynchronously and does not block the request/response cycle.
    If audit logging fails, the request continues normally (logging errors are suppressed).

    Example:
        # In app/main.py
        app.add_middleware(AdminAuditMiddleware)
    """

    def __init__(self, app: ASGIApp):
        """Initialize middleware."""
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log admin actions.

        Args:
            request: FastAPI request object
            call_next: Next middleware or endpoint handler

        Returns:
            Response from the endpoint
        """
        # Only log admin endpoints
        if not request.url.path.startswith("/api/v1/admin"):
            return await call_next(request)

        # Extract request details
        method = request.method
        endpoint = request.url.path
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Determine action from endpoint and method
        action = self._extract_action(endpoint, method)

        # Extract resource info from path
        resource_type, resource_id = self._extract_resource(endpoint)

        # Process request
        response = await call_next(request)

        # Log to database (async, non-blocking)
        try:
            await self._log_admin_action(
                request=request,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                endpoint=endpoint,
                method=method,
                ip_address=ip_address,
                user_agent=user_agent,
                status_code=response.status_code,
            )
        except Exception as e:
            # Suppress logging errors - don't fail the request
            print(f"Admin audit logging failed: {str(e)}")

        return response

    def _extract_action(self, endpoint: str, method: str) -> str:
        """
        Extract human-readable action from endpoint and method.

        Args:
            endpoint: API endpoint path
            method: HTTP method

        Returns:
            Action string (e.g., "tenant_status_updated", "user_deactivated")
        """
        # Parse endpoint to determine action
        parts = endpoint.split("/")

        if "dashboard" in endpoint:
            return "dashboard_viewed"
        elif "/tenants" in endpoint and "/status" in endpoint:
            return "tenant_status_updated" if method == "PATCH" else "tenant_status_viewed"
        elif "/tenants" in endpoint and "/users" in endpoint:
            return "tenant_users_viewed"
        elif "/tenants" in endpoint and "/tokens" in endpoint:
            return "tenant_tokens_viewed"
        elif "/tenants" in endpoint and method == "GET":
            if len(parts) > 4 and parts[4]:  # Specific tenant ID
                return "tenant_viewed"
            return "tenants_listed"
        elif "/users" in endpoint and "/status" in endpoint:
            return "user_status_updated" if method == "PATCH" else "user_status_viewed"
        elif "/users" in endpoint and method == "GET":
            if len(parts) > 4 and parts[4]:  # Specific user ID
                return "user_viewed"
            return "users_listed"
        elif "/tokens" in endpoint and method == "DELETE":
            return "api_token_revoked"
        elif "/analytics/top-tenants" in endpoint:
            return "top_tenants_viewed"
        else:
            return f"{method.lower()}_{endpoint.split('/')[-1]}"

    def _extract_resource(self, endpoint: str) -> tuple[str | None, str | None]:
        """
        Extract resource type and ID from endpoint path.

        Args:
            endpoint: API endpoint path

        Returns:
            Tuple of (resource_type, resource_id)
        """
        parts = endpoint.split("/")

        # Map endpoint segments to resource types
        if "tenants" in parts:
            idx = parts.index("tenants")
            if idx + 1 < len(parts) and parts[idx + 1]:
                # UUID validation (simple check)
                potential_id = parts[idx + 1]
                if "-" in potential_id and len(potential_id) == 36:
                    return ("tenant", potential_id)
            return ("tenant", None)
        elif "users" in parts:
            idx = parts.index("users")
            if idx + 1 < len(parts) and parts[idx + 1]:
                potential_id = parts[idx + 1]
                if "-" in potential_id and len(potential_id) == 36:
                    return ("user", potential_id)
            return ("user", None)
        elif "tokens" in parts:
            idx = parts.index("tokens")
            if idx + 1 < len(parts) and parts[idx + 1]:
                potential_id = parts[idx + 1]
                if "-" in potential_id and len(potential_id) == 36:
                    return ("api_token", potential_id)
            return ("api_token", None)

        return (None, None)

    async def _log_admin_action(
        self,
        request: Request,
        action: str,
        resource_type: str | None,
        resource_id: str | None,
        endpoint: str,
        method: str,
        ip_address: str | None,
        user_agent: str | None,
        status_code: int,
    ):
        """
        Create audit log entry in database.

        Args:
            request: FastAPI request object
            action: Action performed
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            endpoint: API endpoint
            method: HTTP method
            ip_address: Client IP address
            user_agent: User agent string
            status_code: HTTP response status code
        """
        # Get user from request state (set by authentication middleware)
        user = getattr(request.state, "user", None)
        if not user:
            # Try to get from dependency injection (may not be available here)
            return

        # Create database session
        db = SessionLocal()
        try:
            # Create audit log entry
            audit_log = AdminAuditLog(
                id=uuid.uuid4(),
                user_id=user.id,
                action=action,
                resource_type=resource_type,
                resource_id=uuid.UUID(resource_id) if resource_id else None,
                endpoint=endpoint,
                method=method,
                ip_address=ip_address,
                user_agent=user_agent,
                status_code=status_code,
                audit_metadata={},
                created_at=datetime.utcnow(),
            )

            db.add(audit_log)
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()


def add_user_to_request_state(request: Request, user) -> None:
    """
    Helper function to add user to request state.

    Call this from the require_super_admin dependency to make user available
    to the audit middleware.

    Args:
        request: FastAPI request object
        user: Authenticated user object
    """
    request.state.user = user
