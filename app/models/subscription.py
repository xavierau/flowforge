"""Subscription model for managing tenant subscriptions."""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Subscription(Base):
    """Subscription model - manages tenant subscription plans and billing cycles."""

    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    plan = Column(String(50), nullable=False)  # free, starter, pro, enterprise
    status = Column(String(50), nullable=False)  # active, canceled, past_due, unpaid

    stripe_subscription_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_price_id = Column(String(255), nullable=True)

    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)

    # Plan features (JSONB for flexibility)
    features = Column(JSONB, nullable=False, default=dict)  # { "max_users": 5, "api_access": true }

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="subscription")

    # Indexes
    __table_args__ = (
        Index("idx_subscriptions_tenant_id", "tenant_id"),
        Index("idx_subscriptions_status", "status"),
    )

    def __repr__(self):
        return f"<Subscription(id={self.id}, tenant_id={self.tenant_id}, plan={self.plan}, status={self.status})>"
