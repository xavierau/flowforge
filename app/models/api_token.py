"""API Token model for external service authentication."""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class ApiToken(Base):
    """API Token model - represents long-lived authentication tokens for external services."""

    __tablename__ = "api_tokens"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Token data
    name = Column(String(100), nullable=False)  # User-friendly name
    token_hash = Column(String(255), nullable=False, unique=True, index=True)  # bcrypt hash
    token_prefix = Column(String(20), nullable=False)  # First chars for display (e.g., "sk_live_abc12345")

    # Permissions & Scoping
    scopes = Column(JSONB, nullable=False, default=list)  # ["documents:read", "documents:create"]

    # Expiration
    expires_at = Column(DateTime, nullable=True)  # NULL = never expires

    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    last_used_ip = Column(String(45), nullable=True)  # IPv6 max length

    # Status
    is_active = Column(Boolean, nullable=False, default=True)

    # Audit trail
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    tenant = relationship("Tenant")
    revoked_by = relationship("User", foreign_keys=[revoked_by_user_id])

    # Indexes
    __table_args__ = (
        Index("idx_api_tokens_user_id", "user_id"),
        Index("idx_api_tokens_tenant_id", "tenant_id"),
        Index("idx_api_tokens_token_hash", "token_hash", unique=True),
        Index("idx_api_tokens_is_active", "is_active"),
        Index("idx_api_tokens_expires_at", "expires_at"),
    )

    def __repr__(self):
        return f"<ApiToken(id={self.id}, name={self.name}, user_id={self.user_id}, tenant_id={self.tenant_id})>"
