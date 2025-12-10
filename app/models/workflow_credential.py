"""WorkflowCredential model for secure storage of API keys and secrets."""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Index,
    UniqueConstraint,
    LargeBinary,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
import uuid
import re

from app.database import Base


class WorkflowCredential(Base):
    """
    WorkflowCredential model - stores encrypted API keys and secrets for workflows.

    Credentials can be scoped to:
    - Tenant-level (workflow_id=NULL): Shared across all workflows in the tenant
    - Workflow-level (workflow_id=<uuid>): Only accessible to a specific workflow

    The credential value is encrypted using AES-256-GCM before storage.
    The plaintext value is NEVER stored or logged.

    Usage in workflow expressions:
        {{$secrets.MY_API_KEY}}

    Security Notes:
        - encrypted_value contains base64-encoded AES-256-GCM ciphertext
        - encryption_iv contains the unique IV used for encryption
        - Decryption requires the master key from CREDENTIAL_ENCRYPTION_KEY env var
        - The plaintext value is NEVER exposed in API responses
    """

    __tablename__ = "workflow_credentials"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Tenant isolation (always required)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Workflow scope (NULL = tenant-level, set = workflow-specific)
    workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Credential name (e.g., "VENDOR_API_KEY", "STRIPE_SECRET")
    # Must be uppercase with underscores only (valid env var format)
    name = Column(String(100), nullable=False)

    # Optional description for documentation
    description = Column(Text, nullable=True)

    # Encrypted value (base64-encoded AES-256-GCM ciphertext)
    encrypted_value = Column(Text, nullable=False)

    # Initialization vector for AES-256-GCM (12 bytes)
    encryption_iv = Column(LargeBinary, nullable=False)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)

    # Audit trail
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    tenant = relationship("Tenant")
    workflow = relationship("Workflow")
    created_by = relationship("User")

    # Constraints and Indexes
    __table_args__ = (
        # Unique constraint: name must be unique within tenant+workflow scope
        # This allows same name at different scopes:
        # - Tenant-level: (tenant_id=X, workflow_id=NULL, name=Y) - unique
        # - Workflow-level: (tenant_id=X, workflow_id=A, name=Y) - unique
        # - Same name in different workflows: allowed
        UniqueConstraint(
            "tenant_id",
            "workflow_id",
            "name",
            name="uq_credential_scope_name",
        ),
        Index("idx_credentials_tenant", "tenant_id"),
        Index("idx_credentials_workflow", "workflow_id"),
        Index("idx_credentials_is_active", "is_active"),
        Index("idx_credentials_name", "name"),
    )

    # Credential name validation pattern (uppercase with underscores)
    NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")

    @validates("name")
    def validate_name(self, key, value):
        """
        Validate credential name format.

        Rules:
        - Must start with uppercase letter
        - Can only contain uppercase letters, numbers, and underscores
        - Maximum 100 characters (enforced by column)

        Examples:
            - Valid: "API_KEY", "VENDOR_API_KEY_V2", "STRIPE_SECRET"
            - Invalid: "api_key", "Api-Key", "123_KEY", ""
        """
        if not value:
            raise ValueError("Credential name cannot be empty")

        value = value.strip()

        if not self.NAME_PATTERN.match(value):
            raise ValueError(
                "Credential name must start with an uppercase letter and "
                "contain only uppercase letters, numbers, and underscores. "
                f"Got: '{value}'"
            )

        return value

    def __repr__(self):
        scope = f"workflow={self.workflow_id}" if self.workflow_id else "tenant-level"
        return (
            f"<WorkflowCredential("
            f"id={self.id}, "
            f"name={self.name}, "
            f"tenant_id={self.tenant_id}, "
            f"{scope}"
            f")>"
        )
