"""Unit tests for Credential Service.

Tests encryption, resolution priority, scope filtering, and uniqueness.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4

from app.services.credential_service import (
    CredentialService,
    CredentialServiceError,
    CredentialNotFoundError,
    CredentialExistsError,
)
from app.services.encryption_service import DecryptionError
from app.models.workflow_credential import WorkflowCredential


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    session.delete = MagicMock()
    session.rollback = MagicMock()
    return session


@pytest.fixture
def mock_encryption_service():
    """Create a mock encryption service."""
    mock_service = MagicMock()
    mock_service.encrypt = MagicMock(return_value=("encrypted_value_base64", b"iv_12_bytes_"))
    mock_service.decrypt = MagicMock(return_value="decrypted_plaintext")
    return mock_service


@pytest.fixture
def credential_service(mock_db_session):
    """Create credential service with mocked db session."""
    return CredentialService(mock_db_session)


@pytest.fixture
def sample_tenant_id():
    """Generate a sample tenant ID."""
    return uuid4()


@pytest.fixture
def sample_workflow_id():
    """Generate a sample workflow ID."""
    return uuid4()


@pytest.fixture
def sample_user_id():
    """Generate a sample user ID."""
    return uuid4()


@pytest.fixture
def mock_credential():
    """Create a mock credential object."""
    credential = MagicMock(spec=WorkflowCredential)
    credential.id = uuid4()
    credential.tenant_id = uuid4()
    credential.workflow_id = None
    credential.name = "API_KEY"
    credential.description = "Test API key"
    credential.encrypted_value = "encrypted_value_base64"
    credential.encryption_iv = b"iv_12_bytes_"
    credential.is_active = True
    return credential


# =============================================================================
# TestEncryption - Tests for encryption/decryption operations
# =============================================================================


class TestEncryption:
    """Tests for encryption operations in credential service."""

    def test_encrypt_decrypt_roundtrip(
        self,
        mock_db_session,
        mock_encryption_service,
        sample_tenant_id,
        sample_user_id,
    ):
        """Encrypting then decrypting returns original value."""
        original_value = "my_secret_api_key_12345"
        encrypted_data = "encrypted_base64_data"
        iv_bytes = b"random_iv_12"

        mock_encryption_service.encrypt.return_value = (encrypted_data, iv_bytes)
        mock_encryption_service.decrypt.return_value = original_value

        # Configure query to return None (no existing credential)
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        with patch(
            "app.services.credential_service.get_encryption_service",
            return_value=mock_encryption_service,
        ):
            # Create credential (encrypts)
            created = service.create_credential(
                tenant_id=sample_tenant_id,
                name="API_KEY",
                value=original_value,
                created_by_user_id=sample_user_id,
            )

            # Verify encryption was called with original value
            mock_encryption_service.encrypt.assert_called_once_with(original_value)

            # Configure query to return the credential for resolve
            mock_credential = MagicMock(spec=WorkflowCredential)
            mock_credential.encrypted_value = encrypted_data
            mock_credential.encryption_iv = iv_bytes
            mock_query.first.return_value = mock_credential

            # Resolve secret (decrypts)
            resolved = service.resolve_secret(
                tenant_id=sample_tenant_id,
                workflow_id=None,
                secret_name="API_KEY",
            )

            # Verify decryption returns original value
            assert resolved == original_value
            mock_encryption_service.decrypt.assert_called_once_with(
                encrypted_data, iv_bytes
            )

    def test_encrypted_value_different_from_plaintext(
        self,
        mock_db_session,
        mock_encryption_service,
        sample_tenant_id,
    ):
        """Encrypted value differs from plaintext."""
        plaintext = "secret_value_123"
        encrypted = "completely_different_encrypted_string"

        mock_encryption_service.encrypt.return_value = (encrypted, b"iv_12_bytes_")

        # Configure query to return None (no existing credential)
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        with patch(
            "app.services.credential_service.get_encryption_service",
            return_value=mock_encryption_service,
        ):
            service.create_credential(
                tenant_id=sample_tenant_id,
                name="SECRET_KEY",
                value=plaintext,
            )

            # Verify the added credential has encrypted value, not plaintext
            call_args = mock_db_session.add.call_args
            created_credential = call_args[0][0]
            assert created_credential.encrypted_value == encrypted
            assert created_credential.encrypted_value != plaintext

    def test_decrypt_invalid_data_raises_error(
        self,
        mock_db_session,
        mock_encryption_service,
        sample_tenant_id,
    ):
        """Decrypting invalid data raises CredentialServiceError."""
        mock_encryption_service.decrypt.side_effect = DecryptionError(
            "Decryption failed"
        )

        # Configure query to return a credential
        mock_credential = MagicMock(spec=WorkflowCredential)
        mock_credential.id = uuid4()
        mock_credential.encrypted_value = "invalid_encrypted_data"
        mock_credential.encryption_iv = b"iv_12_bytes_"
        mock_credential.name = "API_KEY"

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_credential
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        with patch(
            "app.services.credential_service.get_encryption_service",
            return_value=mock_encryption_service,
        ):
            with pytest.raises(
                CredentialServiceError, match="Failed to decrypt credential"
            ):
                service.resolve_secret(
                    tenant_id=sample_tenant_id,
                    workflow_id=None,
                    secret_name="API_KEY",
                )

    def test_encryption_with_special_characters(
        self,
        mock_db_session,
        mock_encryption_service,
        sample_tenant_id,
    ):
        """Special characters are handled correctly in encryption."""
        special_chars_value = "secret!@#$%^&*()_+-=[]{}|;':\",./<>?\n\t"
        encrypted = "encrypted_special_chars"

        mock_encryption_service.encrypt.return_value = (encrypted, b"iv_12_bytes_")
        mock_encryption_service.decrypt.return_value = special_chars_value

        # Configure query to return None (no existing credential)
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        with patch(
            "app.services.credential_service.get_encryption_service",
            return_value=mock_encryption_service,
        ):
            # Create credential with special characters
            service.create_credential(
                tenant_id=sample_tenant_id,
                name="SPECIAL_KEY",
                value=special_chars_value,
            )

            # Verify encrypt was called with the special characters
            mock_encryption_service.encrypt.assert_called_once_with(special_chars_value)

            # Configure for resolve
            mock_credential = MagicMock(spec=WorkflowCredential)
            mock_credential.encrypted_value = encrypted
            mock_credential.encryption_iv = b"iv_12_bytes_"
            mock_query.first.return_value = mock_credential

            # Resolve and verify special characters preserved
            resolved = service.resolve_secret(
                tenant_id=sample_tenant_id,
                workflow_id=None,
                secret_name="SPECIAL_KEY",
            )
            assert resolved == special_chars_value


# =============================================================================
# TestResolutionPriority - Tests for credential resolution priority
# =============================================================================


class TestResolutionPriority:
    """Tests for credential resolution priority (workflow vs tenant scope)."""

    def test_workflow_scoped_first(
        self,
        mock_db_session,
        mock_encryption_service,
        sample_tenant_id,
        sample_workflow_id,
    ):
        """Workflow-scoped credentials take priority over tenant-scoped."""
        workflow_credential = MagicMock(spec=WorkflowCredential)
        workflow_credential.id = uuid4()
        workflow_credential.encrypted_value = "workflow_encrypted"
        workflow_credential.encryption_iv = b"workflow_iv__"
        workflow_credential.workflow_id = sample_workflow_id

        mock_encryption_service.decrypt.return_value = "workflow_secret"

        # Configure query to return workflow credential on first query
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = workflow_credential
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        with patch(
            "app.services.credential_service.get_encryption_service",
            return_value=mock_encryption_service,
        ):
            result = service.resolve_secret(
                tenant_id=sample_tenant_id,
                workflow_id=sample_workflow_id,
                secret_name="API_KEY",
            )

            assert result == "workflow_secret"
            # Verify decrypt was called with workflow credential's data
            mock_encryption_service.decrypt.assert_called_once_with(
                "workflow_encrypted", b"workflow_iv__"
            )

    def test_tenant_scoped_fallback(
        self,
        mock_db_session,
        mock_encryption_service,
        sample_tenant_id,
        sample_workflow_id,
    ):
        """Falls back to tenant-scoped if no workflow-scoped credential exists."""
        tenant_credential = MagicMock(spec=WorkflowCredential)
        tenant_credential.id = uuid4()
        tenant_credential.encrypted_value = "tenant_encrypted"
        tenant_credential.encryption_iv = b"tenant_iv____"
        tenant_credential.workflow_id = None

        mock_encryption_service.decrypt.return_value = "tenant_secret"

        # Configure query: first returns None (no workflow credential),
        # second returns tenant credential
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.side_effect = [None, tenant_credential]
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        with patch(
            "app.services.credential_service.get_encryption_service",
            return_value=mock_encryption_service,
        ):
            result = service.resolve_secret(
                tenant_id=sample_tenant_id,
                workflow_id=sample_workflow_id,
                secret_name="API_KEY",
            )

            assert result == "tenant_secret"
            mock_encryption_service.decrypt.assert_called_once_with(
                "tenant_encrypted", b"tenant_iv____"
            )

    def test_no_credential_returns_none(
        self,
        mock_db_session,
        sample_tenant_id,
        sample_workflow_id,
    ):
        """Returns None if no matching credential exists."""
        # Configure query to return None for both workflow and tenant lookups
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        result = service.resolve_secret(
            tenant_id=sample_tenant_id,
            workflow_id=sample_workflow_id,
            secret_name="NON_EXISTENT_KEY",
        )

        assert result is None

    def test_name_matching(
        self,
        mock_db_session,
        mock_encryption_service,
        sample_tenant_id,
    ):
        """Credential is resolved by exact name match."""
        credential_api = MagicMock(spec=WorkflowCredential)
        credential_api.id = uuid4()
        credential_api.encrypted_value = "api_encrypted"
        credential_api.encryption_iv = b"api_iv_______"
        credential_api.name = "API_KEY"

        mock_encryption_service.decrypt.return_value = "api_key_value"

        # Configure query
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query

        # Track filter calls to verify name matching
        filter_calls = []

        def track_filter(*args):
            filter_calls.append(args)
            return mock_query

        mock_query.filter.side_effect = track_filter
        mock_query.first.return_value = credential_api
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        with patch(
            "app.services.credential_service.get_encryption_service",
            return_value=mock_encryption_service,
        ):
            result = service.resolve_secret(
                tenant_id=sample_tenant_id,
                workflow_id=None,
                secret_name="API_KEY",
            )

            assert result == "api_key_value"


# =============================================================================
# TestScopeFiltering - Tests for list_credentials scope filtering
# =============================================================================


class TestScopeFiltering:
    """Tests for credential listing with scope filtering."""

    def test_include_tenant_level_true(
        self,
        mock_db_session,
        sample_tenant_id,
        sample_workflow_id,
    ):
        """include_tenant_level=True returns both workflow and tenant credentials."""
        workflow_cred = MagicMock(spec=WorkflowCredential)
        workflow_cred.id = uuid4()
        workflow_cred.name = "WORKFLOW_KEY"
        workflow_cred.workflow_id = sample_workflow_id

        tenant_cred = MagicMock(spec=WorkflowCredential)
        tenant_cred.id = uuid4()
        tenant_cred.name = "TENANT_KEY"
        tenant_cred.workflow_id = None

        # Configure query chain
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 2
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [workflow_cred, tenant_cred]
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        credentials, total = service.list_credentials(
            tenant_id=sample_tenant_id,
            workflow_id=sample_workflow_id,
            include_tenant_level=True,
        )

        assert total == 2
        assert len(credentials) == 2
        names = [c.name for c in credentials]
        assert "WORKFLOW_KEY" in names
        assert "TENANT_KEY" in names

    def test_include_tenant_level_false(
        self,
        mock_db_session,
        sample_tenant_id,
        sample_workflow_id,
    ):
        """include_tenant_level=False returns only workflow-scoped credentials."""
        workflow_cred = MagicMock(spec=WorkflowCredential)
        workflow_cred.id = uuid4()
        workflow_cred.name = "WORKFLOW_KEY"
        workflow_cred.workflow_id = sample_workflow_id

        # Configure query chain
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [workflow_cred]
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        credentials, total = service.list_credentials(
            tenant_id=sample_tenant_id,
            workflow_id=sample_workflow_id,
            include_tenant_level=False,
        )

        assert total == 1
        assert len(credentials) == 1
        assert credentials[0].name == "WORKFLOW_KEY"

    def test_active_only_true(
        self,
        mock_db_session,
        sample_tenant_id,
    ):
        """active_only=True filters out inactive credentials."""
        active_cred = MagicMock(spec=WorkflowCredential)
        active_cred.id = uuid4()
        active_cred.name = "ACTIVE_KEY"
        active_cred.is_active = True

        # Configure query chain
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [active_cred]
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        credentials, total = service.list_credentials(
            tenant_id=sample_tenant_id,
            active_only=True,
        )

        assert total == 1
        assert credentials[0].name == "ACTIVE_KEY"
        assert credentials[0].is_active is True

    def test_active_only_false(
        self,
        mock_db_session,
        sample_tenant_id,
    ):
        """active_only=False returns all credentials including inactive."""
        active_cred = MagicMock(spec=WorkflowCredential)
        active_cred.id = uuid4()
        active_cred.name = "ACTIVE_KEY"
        active_cred.is_active = True

        inactive_cred = MagicMock(spec=WorkflowCredential)
        inactive_cred.id = uuid4()
        inactive_cred.name = "INACTIVE_KEY"
        inactive_cred.is_active = False

        # Configure query chain
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 2
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [active_cred, inactive_cred]
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        credentials, total = service.list_credentials(
            tenant_id=sample_tenant_id,
            active_only=False,
        )

        assert total == 2
        assert len(credentials) == 2
        names = [c.name for c in credentials]
        assert "ACTIVE_KEY" in names
        assert "INACTIVE_KEY" in names


# =============================================================================
# TestUniqueness - Tests for credential name uniqueness constraints
# =============================================================================


class TestUniqueness:
    """Tests for credential name uniqueness constraints."""

    def test_same_name_different_scopes_allowed(
        self,
        mock_db_session,
        mock_encryption_service,
        sample_tenant_id,
        sample_workflow_id,
    ):
        """Same credential name is allowed in different scopes."""
        mock_encryption_service.encrypt.return_value = ("encrypted", b"iv_12_bytes_")

        # Configure query to return None (no existing credential in each scope)
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        with patch(
            "app.services.credential_service.get_encryption_service",
            return_value=mock_encryption_service,
        ):
            # Create tenant-level credential
            service.create_credential(
                tenant_id=sample_tenant_id,
                name="API_KEY",
                value="tenant_value",
                workflow_id=None,  # tenant-level
            )

            # Reset mock for second creation
            mock_db_session.add.reset_mock()

            # Create workflow-level credential with same name (should succeed)
            service.create_credential(
                tenant_id=sample_tenant_id,
                name="API_KEY",
                value="workflow_value",
                workflow_id=sample_workflow_id,  # workflow-level
            )

            # Verify both were added (no exception raised)
            assert mock_db_session.add.call_count == 1

    def test_duplicate_name_same_scope_rejected(
        self,
        mock_db_session,
        mock_encryption_service,
        sample_tenant_id,
    ):
        """Duplicate credential name in same scope fails with CredentialExistsError."""
        existing_cred = MagicMock(spec=WorkflowCredential)
        existing_cred.id = uuid4()
        existing_cred.name = "API_KEY"
        existing_cred.workflow_id = None

        # Configure query to return existing credential
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = existing_cred
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        with pytest.raises(CredentialExistsError, match="already exists at tenant level"):
            service.create_credential(
                tenant_id=sample_tenant_id,
                name="API_KEY",
                value="duplicate_value",
                workflow_id=None,  # Same scope (tenant-level)
            )

    def test_duplicate_name_workflow_scope_rejected(
        self,
        mock_db_session,
        mock_encryption_service,
        sample_tenant_id,
        sample_workflow_id,
    ):
        """Duplicate credential name in same workflow scope fails."""
        existing_cred = MagicMock(spec=WorkflowCredential)
        existing_cred.id = uuid4()
        existing_cred.name = "API_KEY"
        existing_cred.workflow_id = sample_workflow_id

        # Configure query to return existing credential
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = existing_cred
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        with pytest.raises(CredentialExistsError, match="already exists at workflow"):
            service.create_credential(
                tenant_id=sample_tenant_id,
                name="API_KEY",
                value="duplicate_value",
                workflow_id=sample_workflow_id,  # Same scope (workflow-level)
            )

    def test_update_preserves_uniqueness(
        self,
        mock_db_session,
        mock_encryption_service,
        sample_tenant_id,
    ):
        """Updates maintain uniqueness constraint (only update own record)."""
        credential_id = uuid4()

        existing_cred = MagicMock(spec=WorkflowCredential)
        existing_cred.id = credential_id
        existing_cred.tenant_id = sample_tenant_id
        existing_cred.name = "API_KEY"
        existing_cred.description = "Old description"
        existing_cred.is_active = True

        mock_encryption_service.encrypt.return_value = ("new_encrypted", b"new_iv______")

        # Configure query to return the credential for get_credential_by_id
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = existing_cred
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        with patch(
            "app.services.credential_service.get_encryption_service",
            return_value=mock_encryption_service,
        ):
            # Update should succeed (not create a new duplicate)
            updated = service.update_credential(
                credential_id=credential_id,
                tenant_id=sample_tenant_id,
                description="New description",
                value="new_secret_value",
            )

            # Verify the same credential was updated
            assert updated.description == "New description"
            mock_encryption_service.encrypt.assert_called_once_with("new_secret_value")
            mock_db_session.commit.assert_called()


# =============================================================================
# Additional CRUD Tests
# =============================================================================


class TestCredentialCRUD:
    """Additional tests for CRUD operations."""

    def test_get_credential_by_id_found(
        self,
        mock_db_session,
        sample_tenant_id,
    ):
        """get_credential_by_id returns credential when found."""
        credential_id = uuid4()
        mock_cred = MagicMock(spec=WorkflowCredential)
        mock_cred.id = credential_id
        mock_cred.tenant_id = sample_tenant_id
        mock_cred.name = "API_KEY"

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_cred
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        result = service.get_credential_by_id(credential_id, sample_tenant_id)

        assert result is not None
        assert result.id == credential_id
        assert result.name == "API_KEY"

    def test_get_credential_by_id_not_found(
        self,
        mock_db_session,
        sample_tenant_id,
    ):
        """get_credential_by_id returns None when not found."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        result = service.get_credential_by_id(uuid4(), sample_tenant_id)

        assert result is None

    def test_delete_credential_success(
        self,
        mock_db_session,
        sample_tenant_id,
    ):
        """delete_credential returns True when credential is deleted."""
        credential_id = uuid4()
        mock_cred = MagicMock(spec=WorkflowCredential)
        mock_cred.id = credential_id
        mock_cred.name = "API_KEY"

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_cred
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        result = service.delete_credential(credential_id, sample_tenant_id)

        assert result is True
        mock_db_session.delete.assert_called_once_with(mock_cred)
        mock_db_session.commit.assert_called()

    def test_delete_credential_not_found(
        self,
        mock_db_session,
        sample_tenant_id,
    ):
        """delete_credential returns False when credential not found."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        result = service.delete_credential(uuid4(), sample_tenant_id)

        assert result is False
        mock_db_session.delete.assert_not_called()

    def test_update_credential_not_found(
        self,
        mock_db_session,
        sample_tenant_id,
    ):
        """update_credential raises CredentialNotFoundError when not found."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        with pytest.raises(CredentialNotFoundError, match="not found"):
            service.update_credential(
                credential_id=uuid4(),
                tenant_id=sample_tenant_id,
                description="New description",
            )

    def test_get_credential_names(
        self,
        mock_db_session,
        sample_tenant_id,
    ):
        """get_credential_names returns sorted list of names."""
        cred1 = MagicMock(spec=WorkflowCredential)
        cred1.name = "ZEBRA_KEY"
        cred2 = MagicMock(spec=WorkflowCredential)
        cred2.name = "API_KEY"
        cred3 = MagicMock(spec=WorkflowCredential)
        cred3.name = "DATABASE_URL"

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 3
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [cred1, cred2, cred3]
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        names = service.get_credential_names(sample_tenant_id)

        assert names == ["API_KEY", "DATABASE_URL", "ZEBRA_KEY"]

    def test_get_credential_names_deduplicates(
        self,
        mock_db_session,
        sample_tenant_id,
    ):
        """get_credential_names removes duplicates (same name at different scopes)."""
        cred1 = MagicMock(spec=WorkflowCredential)
        cred1.name = "API_KEY"
        cred1.workflow_id = None
        cred2 = MagicMock(spec=WorkflowCredential)
        cred2.name = "API_KEY"
        cred2.workflow_id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 2
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [cred1, cred2]
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        names = service.get_credential_names(sample_tenant_id)

        # Should only contain one "API_KEY" despite two credentials with that name
        assert names == ["API_KEY"]


# =============================================================================
# TestTenantIsolation - Tests for multi-tenant security
# =============================================================================


class TestTenantIsolation:
    """Tests for tenant isolation in credential operations."""

    def test_resolve_secret_requires_tenant_match(
        self,
        mock_db_session,
        mock_encryption_service,
    ):
        """resolve_secret only returns credentials matching the tenant."""
        tenant_a = uuid4()
        tenant_b = uuid4()

        # Credential belongs to tenant_a
        cred_tenant_a = MagicMock(spec=WorkflowCredential)
        cred_tenant_a.id = uuid4()
        cred_tenant_a.tenant_id = tenant_a
        cred_tenant_a.encrypted_value = "encrypted"
        cred_tenant_a.encryption_iv = b"iv_12_bytes_"

        mock_encryption_service.decrypt.return_value = "secret_value"

        # Configure query - return None for tenant_b queries
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # No credential for tenant_b
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        with patch(
            "app.services.credential_service.get_encryption_service",
            return_value=mock_encryption_service,
        ):
            # Try to resolve with wrong tenant - should return None
            result = service.resolve_secret(
                tenant_id=tenant_b,
                workflow_id=None,
                secret_name="API_KEY",
            )

            assert result is None

    def test_list_credentials_tenant_isolation(
        self,
        mock_db_session,
    ):
        """list_credentials only returns credentials for the specified tenant."""
        tenant_id = uuid4()

        tenant_cred = MagicMock(spec=WorkflowCredential)
        tenant_cred.id = uuid4()
        tenant_cred.tenant_id = tenant_id
        tenant_cred.name = "API_KEY"

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [tenant_cred]
        mock_db_session.query.return_value = mock_query

        service = CredentialService(mock_db_session)

        credentials, total = service.list_credentials(tenant_id=tenant_id)

        assert total == 1
        assert credentials[0].tenant_id == tenant_id
