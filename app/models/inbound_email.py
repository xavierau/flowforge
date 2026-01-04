"""Inbound email address and processing log models."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
import uuid

from app.database import Base
from app.config import settings
from app.models.enums import SplitMode, ExtractionMode, InboundEmailLogStatus


class InboundEmailAddress(Base):
    """
    InboundEmailAddress model - represents a unique email address for document ingestion.

    Each inbound email address:
    - Has a unique UUID-based email prefix (e.g., abc123@inbound.example.com)
    - Belongs to a tenant
    - Has pre-configured extraction settings (schema, model, etc.)
    - Tracks statistics on emails received and documents processed
    """

    __tablename__ = "inbound_email_addresses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Email address configuration
    email_prefix = Column(String(36), unique=True, nullable=False, index=True)  # UUID string
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    allowed_senders = Column(JSONB, nullable=True)  # Array of sender patterns (e.g., ["*@company.com"])

    # Job configuration (same as ExtractionJob)
    schema_definition_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schema_definitions.id", ondelete="SET NULL"),
        nullable=True
    )
    extraction_schema = Column(JSONB, nullable=True)  # The actual schema to use
    custom_prompt = Column(Text, nullable=True)
    model_provider = Column(String(50), nullable=False, default="google")
    model_name = Column(String(100), nullable=False, default="gemini-2.5-flash")
    split_mode = Column(String(20), nullable=False, default="batch")  # per_page, batch, auto
    extraction_mode = Column(String(20), nullable=False, default="vllm")  # vllm, markdown
    markdown_converter = Column(String(50), nullable=True)  # Converter for markdown mode
    markdown_format = Column(String(50), nullable=True)  # Format style for markdown mode
    callback_url = Column(String(1024), nullable=True)  # Optional webhook callback URL

    # LlamaExtract-specific fields
    llamaextract_mode = Column(String(20), nullable=True)  # standard or premium
    llamaextract_target = Column(String(20), nullable=True)  # per_doc or per_page

    # Statistics
    emails_received_count = Column(Integer, nullable=False, default=0)
    documents_processed_count = Column(Integer, nullable=False, default=0)
    last_email_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="inbound_email_addresses")
    created_by_user = relationship("User", backref="created_inbound_email_addresses")
    schema_definition = relationship("SchemaDefinition", backref="inbound_email_addresses")
    email_logs = relationship(
        "InboundEmailLog",
        back_populates="inbound_email_address",
        cascade="all, delete-orphan"
    )

    # Indexes
    # Note: email_prefix index is not needed here as it's already defined on the column
    # with index=True and unique=True (line 41)
    __table_args__ = (
        Index("idx_inbound_email_addresses_tenant_id", "tenant_id"),
        Index("idx_inbound_email_addresses_is_active", "is_active"),
        Index("idx_inbound_email_addresses_created_at", "created_at"),
    )

    @property
    def full_email_address(self) -> str:
        """Return the full email address including the domain."""
        return f"{self.email_prefix}@{settings.inbound_email_domain}"

    @validates('split_mode')
    def validate_split_mode(self, key, value):
        """Validate split_mode field against SplitMode enum."""
        if isinstance(value, SplitMode):
            return value.value
        if value not in [m.value for m in SplitMode]:
            raise ValueError(f"Invalid split_mode: {value}. Must be one of: {[m.value for m in SplitMode]}")
        return value

    @validates('extraction_mode')
    def validate_extraction_mode(self, key, value):
        """Validate extraction_mode field against ExtractionMode enum."""
        if isinstance(value, ExtractionMode):
            return value.value
        if value not in [m.value for m in ExtractionMode]:
            raise ValueError(f"Invalid extraction_mode: {value}. Must be one of: {[m.value for m in ExtractionMode]}")
        return value

    def __repr__(self):
        return f"<InboundEmailAddress(id={self.id}, name={self.name}, email={self.full_email_address})>"


class InboundEmailLog(Base):
    """
    InboundEmailLog model - tracks the processing status of each inbound email.

    Each log entry records:
    - The sender and email metadata
    - Processing status (received, processed, rejected, failed)
    - Attachment details
    - Created documents and extraction jobs
    - Raw email metadata (SPF, DKIM, spam scores)
    """

    __tablename__ = "inbound_email_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inbound_email_address_id = Column(
        UUID(as_uuid=True),
        ForeignKey("inbound_email_addresses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Sender information
    sender_email = Column(String(255), nullable=False)
    sender_name = Column(String(255), nullable=True)
    subject = Column(String(1000), nullable=True)
    message_id = Column(String(500), nullable=True)  # Email Message-ID header

    # Processing status
    status = Column(String(50), nullable=False)  # received, processed, rejected_*, failed
    error_message = Column(Text, nullable=True)

    # Attachment details
    attachment_count = Column(Integer, nullable=False, default=0)
    attachment_names = Column(JSONB, nullable=True)  # List of filenames
    total_attachment_size_bytes = Column(Integer, nullable=True)

    # Created entities (results of processing)
    document_ids = Column(JSONB, nullable=True)  # List of created document UUIDs
    extraction_job_ids = Column(JSONB, nullable=True)  # List of created job UUIDs

    # Raw email metadata (security checks, headers)
    raw_metadata = Column(JSONB, nullable=True)  # SPF, DKIM, spam_score, headers, etc.

    # Timestamps
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    inbound_email_address = relationship(
        "InboundEmailAddress",
        back_populates="email_logs"
    )

    # Indexes
    __table_args__ = (
        Index("idx_inbound_email_logs_inbound_email_address_id", "inbound_email_address_id"),
        Index("idx_inbound_email_logs_status", "status"),
        Index("idx_inbound_email_logs_sender_email", "sender_email"),
        Index("idx_inbound_email_logs_received_at", "received_at"),
    )

    @validates('status')
    def validate_status(self, key, value):
        """Validate status field against InboundEmailLogStatus enum."""
        if isinstance(value, InboundEmailLogStatus):
            return value.value
        if value not in [s.value for s in InboundEmailLogStatus]:
            raise ValueError(
                f"Invalid status: {value}. Must be one of: {[s.value for s in InboundEmailLogStatus]}"
            )
        return value

    def __repr__(self):
        return (
            f"<InboundEmailLog(id={self.id}, sender={self.sender_email}, "
            f"status={self.status}, attachments={self.attachment_count})>"
        )
