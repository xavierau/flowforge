"""Credential service for CRUD operations and secret resolution."""

import logging
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.workflow_credential import WorkflowCredential
from app.services.encryption_service import (
    get_encryption_service,
    EncryptionServiceError,
    DecryptionError,
)

logger = logging.getLogger(__name__)


class CredentialServiceError(Exception):
    """Base exception for credential service errors."""

    pass


class CredentialNotFoundError(CredentialServiceError):
    """Exception raised when a credential is not found."""

    pass


class CredentialExistsError(CredentialServiceError):
    """Exception raised when a credential with the same name already exists."""

    pass


class CredentialService:
    """
    Service for managing workflow credentials.

    Handles CRUD operations with encryption/decryption and tenant isolation.

    Usage:
        service = CredentialService(db_session)

        # Create credential
        credential = service.create_credential(
            tenant_id=tenant_id,
            name="API_KEY",
            value="secret_value",
            created_by_user_id=user_id
        )

        # Resolve secret for workflow execution
        value = service.resolve_secret(tenant_id, workflow_id, "API_KEY")
    """

    def __init__(self, db: Session):
        """
        Initialize credential service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_credential(
        self,
        tenant_id: UUID,
        name: str,
        value: str,
        created_by_user_id: Optional[UUID] = None,
        description: Optional[str] = None,
        workflow_id: Optional[UUID] = None,
    ) -> WorkflowCredential:
        """
        Create a new credential with encrypted value.

        Args:
            tenant_id: Tenant ID for isolation
            name: Credential name (e.g., "API_KEY")
            value: Plaintext secret value to encrypt
            created_by_user_id: User ID who created this credential
            description: Optional description
            workflow_id: Optional workflow ID for workflow-scoped credentials

        Returns:
            Created WorkflowCredential model (value is encrypted)

        Raises:
            CredentialExistsError: If credential with same name exists in scope
            CredentialServiceError: If encryption fails
        """
        # Check for existing credential with same name in scope
        existing = (
            self.db.query(WorkflowCredential)
            .filter(
                WorkflowCredential.tenant_id == tenant_id,
                WorkflowCredential.workflow_id == workflow_id,
                WorkflowCredential.name == name,
            )
            .first()
        )

        if existing:
            scope = f"workflow {workflow_id}" if workflow_id else "tenant"
            raise CredentialExistsError(
                f"Credential '{name}' already exists at {scope} level"
            )

        # Encrypt the value
        try:
            encryption_service = get_encryption_service()
            encrypted_value, iv = encryption_service.encrypt(value)
        except EncryptionServiceError as e:
            logger.error("Failed to encrypt credential: %s", type(e).__name__)
            raise CredentialServiceError(f"Encryption failed: {str(e)}")

        # Create credential record
        credential = WorkflowCredential(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            name=name,
            description=description,
            encrypted_value=encrypted_value,
            encryption_iv=iv,
            created_by_user_id=created_by_user_id,
            is_active=True,
        )

        self.db.add(credential)
        self.db.commit()
        self.db.refresh(credential)

        # SECURITY: Log creation without revealing value
        logger.info(
            "Created credential %s (id=%s) for tenant %s",
            name,
            credential.id,
            tenant_id,
        )

        return credential

    def get_credential_by_id(
        self,
        credential_id: UUID,
        tenant_id: UUID,
    ) -> Optional[WorkflowCredential]:
        """
        Get a credential by ID with tenant isolation.

        Args:
            credential_id: Credential ID
            tenant_id: Tenant ID for isolation

        Returns:
            WorkflowCredential or None if not found
        """
        return (
            self.db.query(WorkflowCredential)
            .filter(
                WorkflowCredential.id == credential_id,
                WorkflowCredential.tenant_id == tenant_id,
            )
            .first()
        )

    def list_credentials(
        self,
        tenant_id: UUID,
        workflow_id: Optional[UUID] = None,
        include_tenant_level: bool = True,
        active_only: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[WorkflowCredential], int]:
        """
        List credentials with filtering and pagination.

        Args:
            tenant_id: Tenant ID for isolation
            workflow_id: Filter by workflow ID (None = all)
            include_tenant_level: Include tenant-level credentials when workflow_id is set
            active_only: Only return active credentials
            page: Page number (1-based)
            page_size: Items per page

        Returns:
            Tuple of (list of credentials, total count)
        """
        query = self.db.query(WorkflowCredential).filter(
            WorkflowCredential.tenant_id == tenant_id
        )

        # Filter by workflow scope
        if workflow_id is not None:
            if include_tenant_level:
                # Include both workflow-specific and tenant-level
                query = query.filter(
                    or_(
                        WorkflowCredential.workflow_id == workflow_id,
                        WorkflowCredential.workflow_id.is_(None),
                    )
                )
            else:
                # Only workflow-specific
                query = query.filter(WorkflowCredential.workflow_id == workflow_id)

        # Filter by active status
        if active_only:
            query = query.filter(WorkflowCredential.is_active == True)

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        credentials = (
            query.order_by(WorkflowCredential.name.asc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return credentials, total

    def update_credential(
        self,
        credential_id: UUID,
        tenant_id: UUID,
        description: Optional[str] = None,
        value: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> WorkflowCredential:
        """
        Update a credential.

        Args:
            credential_id: Credential ID
            tenant_id: Tenant ID for isolation
            description: New description (None = no change)
            value: New secret value (None = no change, will be encrypted)
            is_active: New active status (None = no change)

        Returns:
            Updated WorkflowCredential

        Raises:
            CredentialNotFoundError: If credential not found
            CredentialServiceError: If encryption fails
        """
        credential = self.get_credential_by_id(credential_id, tenant_id)
        if not credential:
            raise CredentialNotFoundError(f"Credential {credential_id} not found")

        # Update description if provided
        if description is not None:
            credential.description = description

        # Update active status if provided
        if is_active is not None:
            credential.is_active = is_active

        # Update value if provided (re-encrypt)
        if value is not None:
            try:
                encryption_service = get_encryption_service()
                encrypted_value, iv = encryption_service.encrypt(value)
                credential.encrypted_value = encrypted_value
                credential.encryption_iv = iv
            except EncryptionServiceError as e:
                logger.error("Failed to encrypt credential: %s", type(e).__name__)
                raise CredentialServiceError(f"Encryption failed: {str(e)}")

        self.db.commit()
        self.db.refresh(credential)

        # SECURITY: Log update without revealing value
        logger.info(
            "Updated credential %s (id=%s)",
            credential.name,
            credential_id,
        )

        return credential

    def delete_credential(
        self,
        credential_id: UUID,
        tenant_id: UUID,
    ) -> bool:
        """
        Delete a credential (hard delete).

        Args:
            credential_id: Credential ID
            tenant_id: Tenant ID for isolation

        Returns:
            True if deleted, False if not found

        Note:
            Consider using update_credential with is_active=False for soft delete.
        """
        credential = self.get_credential_by_id(credential_id, tenant_id)
        if not credential:
            return False

        credential_name = credential.name
        self.db.delete(credential)
        self.db.commit()

        logger.info(
            "Deleted credential %s (id=%s) for tenant %s",
            credential_name,
            credential_id,
            tenant_id,
        )

        return True

    def resolve_secret(
        self,
        tenant_id: UUID,
        workflow_id: Optional[UUID],
        secret_name: str,
    ) -> Optional[str]:
        """
        Resolve a secret by name for workflow execution.

        Resolution priority:
        1. Workflow-level credential (if workflow_id provided)
        2. Tenant-level credential

        Args:
            tenant_id: Tenant ID for isolation
            workflow_id: Workflow ID for workflow-scoped lookup
            secret_name: Name of the secret (e.g., "API_KEY")

        Returns:
            Decrypted plaintext value, or None if not found

        Raises:
            CredentialServiceError: If decryption fails

        Security Notes:
            - NEVER log the returned value
            - Only call this during workflow execution, not in API responses
        """
        credential = None

        # First, try workflow-level credential
        if workflow_id:
            credential = (
                self.db.query(WorkflowCredential)
                .filter(
                    WorkflowCredential.tenant_id == tenant_id,
                    WorkflowCredential.workflow_id == workflow_id,
                    WorkflowCredential.name == secret_name,
                    WorkflowCredential.is_active == True,
                )
                .first()
            )

        # Fall back to tenant-level credential
        if not credential:
            credential = (
                self.db.query(WorkflowCredential)
                .filter(
                    WorkflowCredential.tenant_id == tenant_id,
                    WorkflowCredential.workflow_id.is_(None),
                    WorkflowCredential.name == secret_name,
                    WorkflowCredential.is_active == True,
                )
                .first()
            )

        if not credential:
            logger.warning(
                "Secret '%s' not found for tenant %s, workflow %s",
                secret_name,
                tenant_id,
                workflow_id,
            )
            return None

        # Decrypt the value
        try:
            encryption_service = get_encryption_service()
            plaintext = encryption_service.decrypt(
                credential.encrypted_value,
                credential.encryption_iv,
            )
            return plaintext
        except DecryptionError as e:
            logger.error(
                "Failed to decrypt credential %s (id=%s): %s",
                secret_name,
                credential.id,
                type(e).__name__,
            )
            raise CredentialServiceError(
                f"Failed to decrypt credential '{secret_name}'"
            )

    def get_credential_names(
        self,
        tenant_id: UUID,
        workflow_id: Optional[UUID] = None,
    ) -> List[str]:
        """
        Get list of available credential names for a scope.

        Useful for autocomplete/validation in workflow builder.

        Args:
            tenant_id: Tenant ID for isolation
            workflow_id: Optional workflow ID

        Returns:
            List of credential names (sorted)
        """
        credentials, _ = self.list_credentials(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            include_tenant_level=True,
            active_only=True,
            page=1,
            page_size=1000,  # Reasonable limit for autocomplete
        )

        return sorted(set(c.name for c in credentials))
