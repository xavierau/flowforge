"""Authentication service for JWT tokens and password management."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
import bcrypt
from jose import JWTError, jwt

from app.config import settings


class AuthService:
    """Service for handling authentication operations."""

    def hash_password(self, password: str) -> str:
        """
        Hash a plaintext password using bcrypt.

        Args:
            password: The plaintext password to hash

        Returns:
            The hashed password as a string
        """
        # Generate a salt and hash the password
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        # Return as string (decode from bytes)
        return hashed.decode('utf-8')

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plaintext password against a hashed password.

        Args:
            plain_password: The plaintext password to verify
            hashed_password: The hashed password to compare against

        Returns:
            True if password matches, False otherwise
        """
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)

    def create_access_token(
        self,
        user_id: str,
        tenant_id: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new JWT access token.

        Args:
            user_id: The user's ID
            tenant_id: The tenant's ID
            additional_claims: Optional additional claims to include in the token

        Returns:
            The encoded JWT token
        """
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )

        to_encode = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "exp": expire,
            "type": "access"
        }

        if additional_claims:
            to_encode.update(additional_claims)

        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        return encoded_jwt

    def create_refresh_token(self, user_id: str) -> str:
        """
        Create a new JWT refresh token.

        Args:
            user_id: The user's ID

        Returns:
            The encoded JWT refresh token
        """
        expire = datetime.utcnow() + timedelta(
            days=settings.refresh_token_expire_days
        )

        to_encode = {
            "sub": str(user_id),
            "exp": expire,
            "type": "refresh",
            "jti": secrets.token_hex(16)  # Unique JWT ID ensures each token is different
        }

        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        return encoded_jwt

    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verify and decode a JWT token.

        Args:
            token: The JWT token to verify
            token_type: The expected token type (access or refresh)

        Returns:
            The decoded token payload

        Raises:
            JWTError: If the token is invalid or expired
            ValueError: If the token type doesn't match
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )

            # Verify token type
            if payload.get("type") != token_type:
                raise ValueError(f"Invalid token type. Expected {token_type}")

            return payload

        except JWTError as e:
            raise JWTError(f"Token validation failed: {str(e)}")

    def generate_verification_token(self) -> str:
        """
        Generate a random email verification token.

        Returns:
            A secure random token string
        """
        return secrets.token_urlsafe(32)

    def generate_reset_token(self) -> str:
        """
        Generate a random password reset token.

        Returns:
            A secure random token string
        """
        return secrets.token_urlsafe(32)

    def get_password_reset_expires(self) -> datetime:
        """
        Get the expiration datetime for a password reset token.

        Returns:
            Datetime 6 hours from now
        """
        return datetime.utcnow() + timedelta(hours=6)


# Global instance
auth_service = AuthService()
