"""Platform Application model for external service registration."""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class PlatformApplication(Base):
    """
    Platform Application model - represents external applications that can
    manage tenants, users, and tokens via the Platform API.
    """

    __tablename__ = "platform_applications"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Webhook configuration
    webhook_url = Column(String(500), nullable=True)  # URL for event notifications
    webhook_secret = Column(String(255), nullable=True)  # HMAC signing secret

    # Security - IP whitelist (empty = allow all)
    allowed_ips = Column(JSONB, nullable=False, default=list)  # ["1.2.3.4", "10.0.0.0/8"]

    # Rate limiting
    rate_limit_per_minute = Column(Integer, nullable=False, default=60)
    rate_limit_per_hour = Column(Integer, nullable=False, default=1000)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    api_keys = relationship(
        "PlatformApiKey",
        back_populates="application",
        cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "PlatformAuditLog",
        back_populates="application"
    )

    # Indexes
    __table_args__ = (
        Index("idx_platform_applications_slug", "slug", unique=True),
        Index("idx_platform_applications_is_active", "is_active"),
        Index("idx_platform_applications_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<PlatformApplication(id={self.id}, name={self.name}, slug={self.slug})>"
