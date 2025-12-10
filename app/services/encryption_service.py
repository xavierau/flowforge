"""Encryption service for secure credential storage using AES-256-GCM."""

import base64
import os
import logging
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)


class EncryptionServiceError(Exception):
    """Base exception for encryption service errors."""

    pass


class InvalidKeyError(EncryptionServiceError):
    """Exception raised when encryption key is invalid."""

    pass


class DecryptionError(EncryptionServiceError):
    """Exception raised when decryption fails."""

    pass


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data using AES-256-GCM.

    AES-256-GCM provides:
    - 256-bit encryption strength
    - Authenticated encryption (integrity + confidentiality)
    - Unique IV/nonce per encryption operation

    Usage:
        service = EncryptionService(master_key_base64)
        ciphertext, iv = service.encrypt("my_secret")
        plaintext = service.decrypt(ciphertext, iv)

    Security Notes:
        - Master key MUST be 32 bytes (256 bits), base64 encoded
        - IV is generated randomly for each encryption (12 bytes)
        - Never reuse IV with the same key
        - Store ciphertext and IV together (IV is not secret)
    """

    # AES-256-GCM requires 256-bit (32 bytes) key
    KEY_SIZE_BYTES = 32

    # Standard IV size for GCM mode (96 bits / 12 bytes)
    IV_SIZE_BYTES = 12

    def __init__(self, master_key_base64: str):
        """
        Initialize encryption service with master key.

        Args:
            master_key_base64: Base64-encoded 32-byte encryption key.
                              Generate with: base64.b64encode(os.urandom(32)).decode()

        Raises:
            InvalidKeyError: If key is missing, empty, or wrong size
        """
        if not master_key_base64:
            raise InvalidKeyError(
                "Encryption key is required. "
                "Set CREDENTIAL_ENCRYPTION_KEY environment variable."
            )

        try:
            key_bytes = base64.b64decode(master_key_base64)
        except Exception as e:
            raise InvalidKeyError(
                f"Invalid base64 encoding for encryption key: {e}"
            )

        if len(key_bytes) != self.KEY_SIZE_BYTES:
            raise InvalidKeyError(
                f"Encryption key must be exactly {self.KEY_SIZE_BYTES} bytes "
                f"(256 bits), got {len(key_bytes)} bytes. "
                f"Generate a new key with: "
                f"python -c \"import base64, os; print(base64.b64encode(os.urandom(32)).decode())\""
            )

        self._aesgcm = AESGCM(key_bytes)

    def encrypt(self, plaintext: str) -> Tuple[str, bytes]:
        """
        Encrypt plaintext using AES-256-GCM.

        Args:
            plaintext: The string to encrypt

        Returns:
            Tuple of (ciphertext_base64, iv_bytes):
                - ciphertext_base64: Base64-encoded encrypted data
                - iv_bytes: 12-byte initialization vector (store as binary)

        Raises:
            EncryptionServiceError: If encryption fails

        Security Notes:
            - A unique random IV is generated for each encryption
            - Both ciphertext and IV must be stored to decrypt later
            - IV does not need to be secret, but must be unique per encryption
        """
        if not plaintext:
            raise EncryptionServiceError("Cannot encrypt empty plaintext")

        try:
            # Generate unique IV for this encryption
            iv = os.urandom(self.IV_SIZE_BYTES)

            # Encrypt plaintext
            plaintext_bytes = plaintext.encode("utf-8")
            ciphertext_bytes = self._aesgcm.encrypt(iv, plaintext_bytes, None)

            # Encode ciphertext as base64 for storage
            ciphertext_base64 = base64.b64encode(ciphertext_bytes).decode("utf-8")

            return ciphertext_base64, iv

        except Exception as e:
            # SECURITY: Never log the plaintext or details that could leak secrets
            logger.error("Encryption failed: %s", type(e).__name__)
            raise EncryptionServiceError(f"Encryption failed: {type(e).__name__}")

    def decrypt(self, ciphertext_base64: str, iv: bytes) -> str:
        """
        Decrypt ciphertext using AES-256-GCM.

        Args:
            ciphertext_base64: Base64-encoded encrypted data
            iv: 12-byte initialization vector used during encryption

        Returns:
            Decrypted plaintext string

        Raises:
            DecryptionError: If decryption fails (wrong key, tampered data, etc.)

        Security Notes:
            - Decryption will fail if data was tampered with (GCM authentication)
            - Never log decryption errors with ciphertext details
        """
        if not ciphertext_base64:
            raise DecryptionError("Cannot decrypt empty ciphertext")

        if not iv or len(iv) != self.IV_SIZE_BYTES:
            raise DecryptionError(
                f"Invalid IV: must be exactly {self.IV_SIZE_BYTES} bytes"
            )

        try:
            # Decode ciphertext from base64
            ciphertext_bytes = base64.b64decode(ciphertext_base64)

            # Decrypt
            plaintext_bytes = self._aesgcm.decrypt(iv, ciphertext_bytes, None)

            return plaintext_bytes.decode("utf-8")

        except Exception as e:
            # SECURITY: Never log details that could help attackers
            logger.error("Decryption failed: %s", type(e).__name__)
            raise DecryptionError(
                "Decryption failed. This may indicate the data was tampered with, "
                "the wrong encryption key was used, or the data is corrupted."
            )

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new random encryption key.

        Returns:
            Base64-encoded 32-byte key suitable for CREDENTIAL_ENCRYPTION_KEY

        Usage:
            key = EncryptionService.generate_key()
            print(f"CREDENTIAL_ENCRYPTION_KEY={key}")
        """
        key_bytes = os.urandom(EncryptionService.KEY_SIZE_BYTES)
        return base64.b64encode(key_bytes).decode("utf-8")


# Singleton instance - lazy loaded
_encryption_service: EncryptionService = None


def get_encryption_service() -> EncryptionService:
    """
    Get the singleton encryption service instance.

    Lazy loads the service using the CREDENTIAL_ENCRYPTION_KEY from settings.

    Returns:
        EncryptionService singleton instance

    Raises:
        InvalidKeyError: If encryption key is not configured or invalid
    """
    global _encryption_service

    if _encryption_service is None:
        from app.config import settings

        _encryption_service = EncryptionService(settings.credential_encryption_key)

    return _encryption_service
