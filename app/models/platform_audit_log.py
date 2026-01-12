"""Platform Audit Log model for tracking platform API operations."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class PlatformAuditLog(Base):
    """
    Platform Audit Log model - immutable record of all Platform API operations.

    Used for security auditing, debugging, and compliance tracking.
    """

    __tablename__ = "platform_audit_logs"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Actor information
    application_id = Column(
        UUID(as_uuid=True),
        ForeignKey("platform_applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    api_key_id = Column(
        UUID(as_uuid=True),
        ForeignKey("platform_api_keys.id", ondelete="SET NULL"),
        nullable=True
    )

    # Action details
    action = Column(String(100), nullable=False, index=True)  # "tenant_created", "user_created"
    resource_type = Column(String(50), nullable=False)  # "tenant", "user", "token"
    resource_id = Column(UUID(as_uuid=True), nullable=True)  # ID of affected resource

    # Request details
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)  # GET, POST, PATCH, DELETE
    ip_address = Column(String(45), nullable=True)  # IPv6 max length

    # Response details
    status_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Additional metadata
    request_metadata = Column(JSONB, nullable=True, server_default='{}')

    # Timestamp (immutable)
    created_at = Column(DateTime, nullable=False, default=func.now(), index=True)

    # Relationships
    application = relationship("PlatformApplication", back_populates="audit_logs")
    api_key = relationship("PlatformApiKey")

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_platform_audit_logs_application_id", "application_id"),
        Index("idx_platform_audit_logs_action", "action"),
        Index("idx_platform_audit_logs_resource_type", "resource_type"),
        Index("idx_platform_audit_logs_created_at", "created_at"),
        # Composite index for common query patterns
        Index(
            "idx_platform_audit_logs_app_action_created",
            "application_id",
            "action",
            "created_at"
        ),
    )

    def __repr__(self):
        return (
            f"<PlatformAuditLog(id={self.id}, action={self.action}, "
            f"resource_type={self.resource_type}, application_id={self.application_id})>"
        )
