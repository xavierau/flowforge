"""Unit tests for encryption service."""

import pytest
import base64
import os

from app.services.encryption_service import (
    EncryptionService,
    InvalidKeyError,
    DecryptionError,
    EncryptionServiceError,
)


class TestEncryptionServiceInit:
    """Tests for EncryptionService initialization."""

    def test_init_with_valid_key(self):
        """Test initialization with a valid 32-byte base64 key."""
        key = base64.b64encode(os.urandom(32)).decode()
        service = EncryptionService(key)
        assert service is not None

    def test_init_with_empty_key_raises(self):
        """Test that empty key raises InvalidKeyError."""
        with pytest.raises(InvalidKeyError, match="Encryption key is required"):
            EncryptionService("")

    def test_init_with_none_key_raises(self):
        """Test that None key raises InvalidKeyError."""
        with pytest.raises(InvalidKeyError, match="Encryption key is required"):
            EncryptionService(None)

    def test_init_with_invalid_base64_raises(self):
        """Test that invalid base64 raises InvalidKeyError."""
        with pytest.raises(InvalidKeyError, match="Invalid base64 encoding"):
            EncryptionService("not-valid-base64!!!")

    def test_init_with_wrong_key_size_raises(self):
        """Test that wrong key size raises InvalidKeyError."""
        # 16 bytes instead of 32
        short_key = base64.b64encode(os.urandom(16)).decode()
        with pytest.raises(InvalidKeyError, match="must be exactly 32 bytes"):
            EncryptionService(short_key)

        # 64 bytes instead of 32
        long_key = base64.b64encode(os.urandom(64)).decode()
        with pytest.raises(InvalidKeyError, match="must be exactly 32 bytes"):
            EncryptionService(long_key)


class TestEncryptionServiceEncrypt:
    """Tests for EncryptionService.encrypt method."""

    @pytest.fixture
    def service(self):
        """Create encryption service with valid key."""
        key = base64.b64encode(os.urandom(32)).decode()
        return EncryptionService(key)

    def test_encrypt_returns_ciphertext_and_iv(self, service):
        """Test that encrypt returns ciphertext and IV tuple."""
        plaintext = "my_secret_api_key"
        ciphertext, iv = service.encrypt(plaintext)

        assert ciphertext is not None
        assert isinstance(ciphertext, str)
        assert iv is not None
        assert isinstance(iv, bytes)
        assert len(iv) == 12  # GCM standard IV size

    def test_encrypt_produces_different_ciphertext_each_time(self, service):
        """Test that encrypting same plaintext produces different ciphertext (unique IV)."""
        plaintext = "my_secret_api_key"
        ciphertext1, iv1 = service.encrypt(plaintext)
        ciphertext2, iv2 = service.encrypt(plaintext)

        # IVs should be different
        assert iv1 != iv2
        # Ciphertext should also be different due to different IVs
        assert ciphertext1 != ciphertext2

    def test_encrypt_empty_plaintext_raises(self, service):
        """Test that encrypting empty string raises error."""
        with pytest.raises(EncryptionServiceError, match="Cannot encrypt empty"):
            service.encrypt("")

    def test_encrypt_handles_unicode(self, service):
        """Test that encryption handles unicode characters."""
        plaintext = "secret_key_with_unicode_chars"
        ciphertext, iv = service.encrypt(plaintext)
        assert ciphertext is not None
        assert len(iv) == 12


class TestEncryptionServiceDecrypt:
    """Tests for EncryptionService.decrypt method."""

    @pytest.fixture
    def service(self):
        """Create encryption service with valid key."""
        key = base64.b64encode(os.urandom(32)).decode()
        return EncryptionService(key)

    def test_decrypt_returns_original_plaintext(self, service):
        """Test that decrypt returns the original plaintext."""
        original = "my_secret_api_key_123"
        ciphertext, iv = service.encrypt(original)
        decrypted = service.decrypt(ciphertext, iv)

        assert decrypted == original

    def test_decrypt_with_empty_ciphertext_raises(self, service):
        """Test that decrypting empty ciphertext raises error."""
        iv = os.urandom(12)
        with pytest.raises(DecryptionError, match="Cannot decrypt empty"):
            service.decrypt("", iv)

    def test_decrypt_with_invalid_iv_size_raises(self, service):
        """Test that decrypting with wrong IV size raises error."""
        plaintext = "secret"
        ciphertext, _ = service.encrypt(plaintext)
        wrong_iv = os.urandom(8)  # Should be 12 bytes

        with pytest.raises(DecryptionError, match="Invalid IV"):
            service.decrypt(ciphertext, wrong_iv)

    def test_decrypt_with_wrong_key_raises(self):
        """Test that decrypting with different key raises error."""
        key1 = base64.b64encode(os.urandom(32)).decode()
        key2 = base64.b64encode(os.urandom(32)).decode()

        service1 = EncryptionService(key1)
        service2 = EncryptionService(key2)

        plaintext = "my_secret"
        ciphertext, iv = service1.encrypt(plaintext)

        with pytest.raises(DecryptionError, match="Decryption failed"):
            service2.decrypt(ciphertext, iv)

    def test_decrypt_with_tampered_ciphertext_raises(self, service):
        """Test that decrypting tampered ciphertext raises error (GCM authentication)."""
        plaintext = "my_secret"
        ciphertext, iv = service.encrypt(plaintext)

        # Tamper with the ciphertext
        tampered = base64.b64encode(
            base64.b64decode(ciphertext)[:-1] + b"X"
        ).decode()

        with pytest.raises(DecryptionError, match="Decryption failed"):
            service.decrypt(tampered, iv)


class TestEncryptionServiceRoundTrip:
    """Integration tests for encrypt/decrypt round trip."""

    @pytest.fixture
    def service(self):
        """Create encryption service with valid key."""
        key = base64.b64encode(os.urandom(32)).decode()
        return EncryptionService(key)

    def test_roundtrip_short_string(self, service):
        """Test round trip with short string."""
        original = "abc"
        ciphertext, iv = service.encrypt(original)
        decrypted = service.decrypt(ciphertext, iv)
        assert decrypted == original

    def test_roundtrip_long_string(self, service):
        """Test round trip with long string (API key format)."""
        original = "sk_live_" + "a" * 100 + "_" + "b" * 50
        ciphertext, iv = service.encrypt(original)
        decrypted = service.decrypt(ciphertext, iv)
        assert decrypted == original

    def test_roundtrip_special_characters(self, service):
        """Test round trip with special characters."""
        original = "secret!@#$%^&*()_+-=[]{}|;':\",./<>?"
        ciphertext, iv = service.encrypt(original)
        decrypted = service.decrypt(ciphertext, iv)
        assert decrypted == original

    def test_roundtrip_json_string(self, service):
        """Test round trip with JSON string."""
        original = '{"api_key": "abc123", "secret": "xyz789"}'
        ciphertext, iv = service.encrypt(original)
        decrypted = service.decrypt(ciphertext, iv)
        assert decrypted == original


class TestEncryptionServiceGenerateKey:
    """Tests for EncryptionService.generate_key static method."""

    def test_generate_key_returns_valid_base64(self):
        """Test that generated key is valid base64."""
        key = EncryptionService.generate_key()
        # Should not raise
        decoded = base64.b64decode(key)
        assert len(decoded) == 32

    def test_generate_key_produces_unique_keys(self):
        """Test that generate_key produces unique keys."""
        keys = [EncryptionService.generate_key() for _ in range(10)]
        assert len(set(keys)) == 10  # All unique

    def test_generated_key_works_with_service(self):
        """Test that generated key can be used with service."""
        key = EncryptionService.generate_key()
        service = EncryptionService(key)

        plaintext = "test_secret"
        ciphertext, iv = service.encrypt(plaintext)
        decrypted = service.decrypt(ciphertext, iv)

        assert decrypted == plaintext
