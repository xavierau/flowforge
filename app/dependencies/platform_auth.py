"""Platform API authentication dependencies."""

import re
from datetime import datetime
from typing import Tuple, Callable, Optional, Any, Dict
from uuid import UUID

from fastapi import Depends, Header, Request, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models.platform_application import PlatformApplication
from app.models.platform_api_key import PlatformApiKey
from app.models.platform_audit_log import PlatformAuditLog
from app.services.platform_api_key_service import PlatformApiKeyService
from app.services.platform_application_service import PlatformApplicationService
from app.dependencies.platform_rate_limit import check_platform_rate_limit


# Pre-computed dummy hash for timing attack mitigation
# Generated once at module load to ensure consistent timing
# Uses the same bcrypt parameters as real key hashes
_dummy_key_data = PlatformApiKeyService.generate_key()
DUMMY_BCRYPT_HASH = _dummy_key_data[1]  # Index 1 is the hash


def get_minimum_bcrypt_comparisons() -> int:
    """
    Get the minimum number of bcrypt comparisons from config.

    This ensures constant-time verification regardless of candidate count,
    preventing timing attacks that could reveal how many keys share a prefix.

    Returns:
        Minimum number of bcrypt verifications to perform
    """
    return settings.platform_auth_min_iterations


def _verify_keys_constant_time(
    key: str,
    candidates: list,
) -> Optional[PlatformApiKey]:
    """
    Verify a key against candidate keys with constant iteration count.

    This function ensures a fixed number of bcrypt verifications are performed
    regardless of how many candidates exist. This prevents timing attacks
    that could infer the number of keys sharing a prefix.

    Args:
        key: The plaintext API key to verify
        candidates: List of PlatformApiKey candidates to check against

    Returns:
        The matching PlatformApiKey if found, None otherwise
    """
    min_iterations = get_minimum_bcrypt_comparisons()
    matched_key = None
    iterations_done = 0

    # Verify all candidates without breaking on match
    for candidate in candidates:
        if PlatformApiKeyService.verify_key(key, candidate.token_hash):
            matched_key = candidate
        iterations_done += 1
        # Don't break - continue verifying all candidates to maintain constant time

    # Pad to minimum iterations with dummy verifications
    # This ensures constant iteration count regardless of candidate count
    while iterations_done < min_iterations:
        PlatformApiKeyService.verify_key(key, DUMMY_BCRYPT_HASH)
        iterations_done += 1

    return matched_key


# Sensitive field patterns to sanitize from audit metadata
# Using (^|_) and ($|_) instead of \b to handle underscore-separated field names
# This avoids over-matching legitimate fields like "author", "authority", etc.
SENSITIVE_FIELD_PATTERNS = [
    # Password-related (matches password, user_password, password_hash, etc.)
    re.compile(r"(^|_)password($|_)", re.IGNORECASE),
    re.compile(r"(^|_)passwd($|_)", re.IGNORECASE),
    # Note: "pass" alone is too ambiguous (pass_through, bypass) - only match exact
    re.compile(r"^pass$", re.IGNORECASE),
    # Token-related (specific patterns to avoid matching "token_count", etc.)
    re.compile(r"(^|_)access[_-]?token($|_|s$)", re.IGNORECASE),
    re.compile(r"(^|_)refresh[_-]?token($|_|s$)", re.IGNORECASE),
    re.compile(r"(^|_)auth[_-]?token($|_|s$)", re.IGNORECASE),
    re.compile(r"(^|_)bearer[_-]?token($|_|s$)", re.IGNORECASE),
    re.compile(r"(^|_)api[_-]?token($|_|s$)", re.IGNORECASE),
    re.compile(r"(^|_)session[_-]?token($|_|s$)", re.IGNORECASE),
    re.compile(r"(^|_)jwt[_-]?token($|_|s$)", re.IGNORECASE),
    re.compile(r"(^|_)token[_-]?secret($|_|s$)", re.IGNORECASE),
    # Secret-related (matches secret, client_secret, api_secret, etc.)
    re.compile(r"(^|_)secret($|_|s$)", re.IGNORECASE),
    re.compile(r"(^|_)client[_-]?secret($|_|s$)", re.IGNORECASE),
    re.compile(r"(^|_)app[_-]?secret($|_|s$)", re.IGNORECASE),
    # API key patterns (matches api_key, user_api_key, etc.)
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"(^|_)api[_-]?secret($|_|s$)", re.IGNORECASE),
    # Credential-related (matches credential, credentials, user_credentials, etc.)
    re.compile(r"credential", re.IGNORECASE),
    # Auth-related (specific patterns, not just "auth")
    re.compile(r"(^|_)authorization($|_)", re.IGNORECASE),
    re.compile(r"(^|_)auth[_-]?key($|_|s$)", re.IGNORECASE),
    re.compile(r"(^|_)auth[_-]?secret($|_|s$)", re.IGNORECASE),
    re.compile(r"(^|_)auth[_-]?code($|_|s$)", re.IGNORECASE),
    re.compile(r"(^|_)auth[_-]?header($|_|s$)", re.IGNORECASE),
    # Private key patterns (not "private_notes" or similar)
    re.compile(r"private[_-]?(key|secret|token)", re.IGNORECASE),
    # Encryption-related
    re.compile(r"(^|_)encryption[_-]?key($|_|s$)", re.IGNORECASE),
    re.compile(r"(^|_)signing[_-]?key($|_|s$)", re.IGNORECASE),
    re.compile(r"(^|_)hmac[_-]?key($|_|s$)", re.IGNORECASE),
    # SSH/PGP keys
    re.compile(r"(^|_)ssh[_-]?key($|_|s$)", re.IGNORECASE),
    re.compile(r"(^|_)pgp[_-]?key($|_|s$)", re.IGNORECASE),
    re.compile(r"(^|_)rsa[_-]?key($|_|s$)", re.IGNORECASE),
    # OAuth-related
    re.compile(r"(^|_)oauth[_-]?token($|_|s$)", re.IGNORECASE),
    re.compile(r"(^|_)oauth[_-]?secret($|_|s$)", re.IGNORECASE),
    re.compile(r"(^|_)client[_-]?id($|_)", re.IGNORECASE),
    # PIN/OTP (exact match only to avoid "pinned", "pinning")
    re.compile(r"^pin$", re.IGNORECASE),
    re.compile(r"(^|_)otp($|_)", re.IGNORECASE),
    re.compile(r"(^|_)totp($|_)", re.IGNORECASE),
    re.compile(r"(^|_)hotp($|_)", re.IGNORECASE),
]


def _is_sensitive_key(key: str) -> bool:
    """Check if a key name matches sensitive field patterns."""
    for pattern in SENSITIVE_FIELD_PATTERNS:
        if pattern.search(key):
            return True
    return False


def sanitize_audit_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Sanitize audit metadata by removing sensitive fields.

    Recursively removes fields that match sensitive patterns like
    password, token, secret, api_key, credential, etc.

    Args:
        metadata: Dictionary of metadata to sanitize

    Returns:
        Sanitized metadata with sensitive fields replaced by "[REDACTED]"
    """
    if metadata is None:
        return {}

    if not isinstance(metadata, dict):
        return metadata

    sanitized = {}
    for key, value in metadata.items():
        if _is_sensitive_key(key):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_audit_metadata(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_audit_metadata(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized


async def _log_failed_auth_attempt(
    db: Session,
    request: Request,
    reason: str,
    key_prefix: Optional[str] = None,
) -> None:
    """
    Log a failed authentication attempt for security auditing.

    Args:
        db: Database session
        request: FastAPI request object
        reason: Reason for authentication failure
        key_prefix: Optional key prefix if available (for tracking)
    """
    try:
        audit_log = PlatformAuditLog(
            application_id=None,
            api_key_id=None,
            action="auth_failed",
            resource_type="authentication",
            resource_id=None,
            endpoint=str(request.url.path),
            method=request.method,
            ip_address=_get_client_ip(request),
            status_code=401,
            error_message=reason,
            request_metadata=sanitize_audit_metadata({
                "key_prefix": key_prefix,
                "user_agent": request.headers.get("User-Agent"),
            }),
        )
        db.add(audit_log)
        db.commit()
    except Exception:
        # Don't let audit logging failures affect auth flow
        db.rollback()


class PlatformAuthError(HTTPException):
    """Base exception for platform authentication errors."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class PlatformForbiddenError(HTTPException):
    """Exception for platform authorization errors."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


async def get_current_platform_application(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> Tuple[PlatformApplication, PlatformApiKey]:
    """
    Authenticate a Platform API key and return the application and key.

    This dependency validates:
    1. Token format (pk_live_ prefix)
    2. Token hash match
    3. Token not expired
    4. Token is active
    5. Application is active
    6. IP whitelist (if configured)
    7. Rate limits (per-minute and per-hour)

    Args:
        request: FastAPI request object
        authorization: Authorization header value
        db: Database session

    Returns:
        Tuple of (PlatformApplication, PlatformApiKey)

    Raises:
        PlatformAuthError: If authentication fails
        PlatformForbiddenError: If IP is not in whitelist
        HTTPException: 429 if rate limit exceeded
    """
    # Extract token from header
    key = PlatformApiKeyService.extract_key_from_header(authorization)
    if not key:
        await _log_failed_auth_attempt(
            db, request, "Invalid or missing platform API key"
        )
        raise PlatformAuthError("Invalid or missing platform API key")

    # Parse key prefix for database lookup
    key_prefix = PlatformApiKeyService.parse_key_prefix(key)
    if not key_prefix:
        await _log_failed_auth_attempt(
            db, request, "Invalid platform API key format"
        )
        raise PlatformAuthError("Invalid platform API key format")

    # Find matching keys by prefix
    candidate_keys = (
        db.query(PlatformApiKey)
        .options(joinedload(PlatformApiKey.application))
        .filter(
            PlatformApiKey.token_prefix == key_prefix,
            PlatformApiKey.is_active == True
        )
        .all()
    )

    if not candidate_keys:
        await _log_failed_auth_attempt(
            db, request, "Invalid platform API key", key_prefix
        )
        raise PlatformAuthError("Invalid platform API key")

    # Verify key with constant iteration count to prevent timing attacks
    matched_key = _verify_keys_constant_time(key, candidate_keys)

    if not matched_key:
        await _log_failed_auth_attempt(
            db, request, "Invalid platform API key hash", key_prefix
        )
        raise PlatformAuthError("Invalid platform API key")

    # Check expiration
    if PlatformApiKeyService.is_key_expired(matched_key.expires_at):
        await _log_failed_auth_attempt(
            db, request, "Platform API key has expired", key_prefix
        )
        raise PlatformAuthError("Platform API key has expired")

    # Get application
    application = matched_key.application
    if not application or not application.is_active:
        raise PlatformAuthError("Platform application is not active")

    # Validate IP whitelist
    client_ip = _get_client_ip(request)
    if application.allowed_ips:
        app_service = PlatformApplicationService(db)
        if not app_service.validate_ip_whitelist(client_ip, application.allowed_ips):
            raise PlatformForbiddenError(
                f"IP address {client_ip} is not in the allowed list"
            )

    # Check rate limits
    await check_platform_rate_limit(application, matched_key, request)

    # Update last used tracking
    matched_key.last_used_at = datetime.utcnow()
    matched_key.last_used_ip = client_ip
    db.commit()

    # Store in request state for later use
    request.state.platform_application = application
    request.state.platform_api_key = matched_key

    return application, matched_key


def require_platform_scope(scope: str) -> Callable:
    """
    Dependency factory for requiring a specific platform scope.

    Args:
        scope: Required scope (e.g., "tenants:create")

    Returns:
        Dependency function that validates scope

    Usage:
        @router.post("/tenants")
        async def create_tenant(
            app_info: tuple = Depends(require_platform_scope("tenants:create"))
        ):
            application, api_key = app_info
            ...
    """

    async def scope_checker(
        app_info: Tuple[PlatformApplication, PlatformApiKey] = Depends(
            get_current_platform_application
        ),
    ) -> Tuple[PlatformApplication, PlatformApiKey]:
        application, api_key = app_info

        if not PlatformApiKeyService.validate_scope(api_key.scopes, scope):
            raise PlatformForbiddenError(
                f"Platform API key does not have required scope: {scope}"
            )

        return application, api_key

    return scope_checker


def _get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.

    Only trusts X-Forwarded-For and X-Real-IP headers when
    TRUST_PROXY_HEADERS is enabled in configuration.
    This prevents IP spoofing attacks when not behind a trusted proxy.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address
    """
    # Only trust proxy headers if explicitly configured
    # This prevents IP spoofing when not behind a trusted reverse proxy
    if settings.trust_proxy_headers:
        # Check X-Forwarded-For header (for proxies/load balancers)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

    # Fall back to direct client IP
    if request.client:
        return request.client.host

    return "unknown"


async def log_platform_action(
    db: Session,
    request: Request,
    action: str,
    resource_type: str,
    resource_id: Optional[UUID] = None,
    status_code: Optional[int] = None,
    error_message: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> PlatformAuditLog:
    """
    Log a platform API action for auditing.

    Args:
        db: Database session
        request: FastAPI request object
        action: Action performed (e.g., "tenant_created")
        resource_type: Type of resource (e.g., "tenant")
        resource_id: ID of affected resource
        status_code: HTTP response status code
        error_message: Error message if failed
        metadata: Additional metadata

    Returns:
        Created audit log entry
    """
    application = getattr(request.state, "platform_application", None)
    api_key = getattr(request.state, "platform_api_key", None)

    # Sanitize metadata to remove sensitive fields before storing
    sanitized_metadata = sanitize_audit_metadata(metadata)

    audit_log = PlatformAuditLog(
        application_id=application.id if application else None,
        api_key_id=api_key.id if api_key else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        endpoint=str(request.url.path),
        method=request.method,
        ip_address=_get_client_ip(request),
        status_code=status_code,
        error_message=error_message,
        request_metadata=sanitized_metadata,
    )

    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)

    return audit_log
