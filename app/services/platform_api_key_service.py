"""Platform API Key service for token generation, validation, and management."""

import secrets
import string
import bcrypt
from datetime import datetime
from typing import Tuple, Optional, List

from app.models.enums import PlatformScope


class PlatformApiKeyService:
    """Service for Platform API key generation, validation, and management.

    Platform API keys use the format pk_live_{identifier}_{checksum} to distinguish
    them from tenant-scoped API tokens (sk_live_).
    """

    TOKEN_PREFIX = "pk_live_"
    IDENTIFIER_LENGTH = 32
    CHECKSUM_LENGTH = 12

    @staticmethod
    def generate_key() -> Tuple[str, str, str]:
        """
        Generate a new Platform API key.

        Returns:
            Tuple of (full_key, key_hash, key_prefix)

        Example:
            ("pk_live_abc...xyz", "$2b$12$...", "pk_live_abc12345")
        """
        # Generate random identifier (32 chars)
        alphabet = string.ascii_lowercase + string.digits
        identifier = ''.join(secrets.choice(alphabet) for _ in range(PlatformApiKeyService.IDENTIFIER_LENGTH))

        # Generate checksum (12 chars)
        checksum = ''.join(secrets.choice(alphabet) for _ in range(PlatformApiKeyService.CHECKSUM_LENGTH))

        # Construct full key
        full_key = f"{PlatformApiKeyService.TOKEN_PREFIX}{identifier}_{checksum}"

        # Hash key using bcrypt
        key_hash = bcrypt.hashpw(full_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Create display prefix (first 8 chars after prefix)
        key_prefix = f"{PlatformApiKeyService.TOKEN_PREFIX}{identifier[:8]}"

        return full_key, key_hash, key_prefix

    @staticmethod
    def verify_key(plain_key: str, key_hash: str) -> bool:
        """
        Verify a plain key against its hash.

        Args:
            plain_key: The plaintext key to verify
            key_hash: The hashed key to compare against

        Returns:
            True if key matches hash, False otherwise
        """
        try:
            return bcrypt.checkpw(plain_key.encode('utf-8'), key_hash.encode('utf-8'))
        except Exception:
            return False

    @staticmethod
    def is_key_expired(expires_at: Optional[datetime]) -> bool:
        """
        Check if key has expired.

        Args:
            expires_at: Key expiration datetime (None means never expires)

        Returns:
            True if key has expired, False otherwise
        """
        if expires_at is None:
            return False
        return datetime.utcnow() > expires_at

    @staticmethod
    def matches_scope(granted_scope: str, required_scope: str) -> bool:
        """
        Check if a single granted scope matches a required scope.

        Delegates to PlatformScope.matches_scope() as the single source of truth.

        Args:
            granted_scope: A scope that has been granted (may contain wildcards)
            required_scope: The scope required for an operation

        Returns:
            True if granted_scope matches required_scope, False otherwise

        Examples:
            matches_scope("tenants:read", "tenants:read") -> True (exact match)
            matches_scope("tenants:*", "tenants:read") -> True (resource wildcard)
            matches_scope("tenants:*", "tenants:create") -> True (resource wildcard)
            matches_scope("*:*", "tenants:read") -> True (full wildcard)
            matches_scope("tenants:read", "users:read") -> False (no match)
        """
        return PlatformScope.matches_scope(granted_scope, required_scope)

    @staticmethod
    def validate_scope(scopes: List[str], required_scope: str) -> bool:
        """
        Check if key has a specific scope.

        Delegates to PlatformScope.has_required_scope() as the single source of truth.

        Args:
            scopes: List of scopes granted to the key
            required_scope: Scope to check (e.g., "tenants:create")

        Returns:
            True if key has scope, False otherwise
        """
        return PlatformScope.has_required_scope(scopes, required_scope)

    @staticmethod
    def extract_key_from_header(authorization: Optional[str]) -> Optional[str]:
        """
        Extract Platform API key from Authorization header.

        Supports two formats:
        - Authorization: Bearer pk_live_...
        - Authorization: pk_live_...

        Args:
            authorization: Authorization header value

        Returns:
            Extracted key or None if invalid
        """
        if not authorization:
            return None

        # Remove "Bearer " prefix if present
        key = authorization.replace("Bearer ", "").strip()

        # Validate key format
        if not key.startswith(PlatformApiKeyService.TOKEN_PREFIX):
            return None

        return key

    @staticmethod
    def parse_key_prefix(key: str) -> Optional[str]:
        """
        Extract the prefix from a full key for database lookup.

        Args:
            key: Full platform API key

        Returns:
            Key prefix (e.g., "pk_live_abc12345") or None if invalid
        """
        if not key or not key.startswith(PlatformApiKeyService.TOKEN_PREFIX):
            return None

        # Extract identifier part (after prefix, before underscore)
        try:
            # Remove the prefix
            remainder = key[len(PlatformApiKeyService.TOKEN_PREFIX):]
            # Get the first 8 chars of the identifier
            identifier_start = remainder[:8]
            return f"{PlatformApiKeyService.TOKEN_PREFIX}{identifier_start}"
        except (IndexError, ValueError):
            return None

    @staticmethod
    def generate_webhook_secret() -> str:
        """
        Generate a secure webhook signing secret.

        Returns:
            A 32-character hex string for HMAC signing
        """
        return secrets.token_hex(32)
