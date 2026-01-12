"""Platform API Key model for platform-level authentication."""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class PlatformApiKey(Base):
    """
    Platform API Key model - represents authentication keys for platform applications.

    These keys use the format pk_live_{identifier}_{checksum} and are distinct
    from tenant-scoped API tokens (sk_live_).
    """

    __tablename__ = "platform_api_keys"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(
        UUID(as_uuid=True),
        ForeignKey("platform_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Token data
    name = Column(String(100), nullable=False)  # User-friendly name
    token_hash = Column(String(255), nullable=False, unique=True, index=True)  # bcrypt hash
    token_prefix = Column(String(24), nullable=False)  # "pk_live_abc12345" for display

    # Scopes/permissions
    scopes = Column(JSONB, nullable=False, default=list)  # ["tenants:create", "users:create"]

    # Expiration
    expires_at = Column(DateTime, nullable=True)  # NULL = never expires

    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    last_used_ip = Column(String(45), nullable=True)  # IPv6 max length

    # Status
    is_active = Column(Boolean, nullable=False, default=True)

    # Audit trail
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    revoked_at = Column(DateTime, nullable=True)
    revoked_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    application = relationship("PlatformApplication", back_populates="api_keys")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    revoked_by = relationship("User", foreign_keys=[revoked_by_user_id])

    # Indexes
    __table_args__ = (
        Index("idx_platform_api_keys_application_id", "application_id"),
        Index("idx_platform_api_keys_token_hash", "token_hash", unique=True),
        Index("idx_platform_api_keys_token_prefix", "token_prefix"),
        Index("idx_platform_api_keys_is_active", "is_active"),
        Index("idx_platform_api_keys_expires_at", "expires_at"),
    )

    def __repr__(self):
        return f"<PlatformApiKey(id={self.id}, name={self.name}, application_id={self.application_id})>"
