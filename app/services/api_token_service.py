"""API Token service for token generation, validation, and management."""

import secrets
import string
import bcrypt
from datetime import datetime
from typing import Tuple, Optional


class ApiTokenService:
    """Service for API token generation, validation, and management."""

    TOKEN_PREFIX = "sk_live_"
    IDENTIFIER_LENGTH = 32
    CHECKSUM_LENGTH = 12

    @staticmethod
    def generate_token() -> Tuple[str, str, str]:
        """
        Generate a new API token.

        Returns:
            Tuple of (full_token, token_hash, token_prefix)

        Example:
            ("sk_live_abc...xyz", "$2b$12$...", "sk_live_abc12345")
        """
        # Generate random identifier (32 chars)
        alphabet = string.ascii_lowercase + string.digits
        identifier = ''.join(secrets.choice(alphabet) for _ in range(ApiTokenService.IDENTIFIER_LENGTH))

        # Generate checksum (12 chars)
        checksum = ''.join(secrets.choice(alphabet) for _ in range(ApiTokenService.CHECKSUM_LENGTH))

        # Construct full token
        full_token = f"{ApiTokenService.TOKEN_PREFIX}{identifier}_{checksum}"

        # Hash token using bcrypt
        token_hash = bcrypt.hashpw(full_token.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Create display prefix (first 8 chars after prefix)
        token_prefix = f"{ApiTokenService.TOKEN_PREFIX}{identifier[:8]}"

        return full_token, token_hash, token_prefix

    @staticmethod
    def verify_token(plain_token: str, token_hash: str) -> bool:
        """
        Verify a plain token against its hash.

        Args:
            plain_token: The plaintext token to verify
            token_hash: The hashed token to compare against

        Returns:
            True if token matches hash, False otherwise
        """
        try:
            return bcrypt.checkpw(plain_token.encode('utf-8'), token_hash.encode('utf-8'))
        except Exception:
            return False

    @staticmethod
    def is_token_expired(expires_at: Optional[datetime]) -> bool:
        """
        Check if token has expired.

        Args:
            expires_at: Token expiration datetime (None means never expires)

        Returns:
            True if token has expired, False otherwise
        """
        if expires_at is None:
            return False
        return datetime.utcnow() > expires_at

    @staticmethod
    def validate_token_permission(scopes: list, required_permission: str) -> bool:
        """
        Check if API token has a specific permission.

        Args:
            scopes: List of scopes/permissions granted to the token
            required_permission: Permission to check (e.g., "documents:read")

        Returns:
            True if token has permission, False otherwise
        """
        # Check if token has the specific permission
        if required_permission in scopes:
            return True

        # Check for wildcard patterns
        # e.g., "documents:*" grants all document permissions
        resource = required_permission.split(':')[0]
        wildcard = f"{resource}:*"
        return wildcard in scopes

    @staticmethod
    def extract_token_from_header(authorization: Optional[str]) -> Optional[str]:
        """
        Extract API token from Authorization header.

        Supports two formats:
        - Authorization: Bearer sk_live_...
        - Authorization: sk_live_...

        Args:
            authorization: Authorization header value

        Returns:
            Extracted token or None if invalid
        """
        if not authorization:
            return None

        # Remove "Bearer " prefix if present
        token = authorization.replace("Bearer ", "").strip()

        # Validate token format
        if not token.startswith(ApiTokenService.TOKEN_PREFIX):
            return None

        return token
