"""Tenant model for multi-tenancy support."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, String, Integer, DateTime, Numeric, Index, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Tenant(Base):
    """Tenant model - represents an organization/team in the multi-tenant system."""

    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(String(50), nullable=False, default="active")  # active, suspended, cancelled

    # Subscription & Credits
    subscription_plan = Column(String(50), nullable=True)  # free, starter, pro, enterprise
    stripe_customer_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    # FIX: Added cached_balance for O(1) balance lookups (updated atomically with transactions)
    # Fallback to event sourcing calculation if cached value is stale/missing
    cached_balance = Column(Integer, nullable=False, default=0, index=True)
    balance_last_updated = Column(DateTime, nullable=True)  # Timestamp of last cache update
    credit_unit_cost = Column(Numeric(10, 4), nullable=True)  # Cost per credit (tier-based)

    # HITL (Human-in-the-Loop) configuration
    # These thresholds control when extractions require human review
    hitl_auto_approve_threshold = Column(
        Float,
        nullable=False,
        default=0.70
    )  # Confidence above this: auto-approve (default: 0.70)
    hitl_critical_threshold = Column(
        Float,
        nullable=False,
        default=0.30
    )  # Below this: critical priority (1 hour SLA)
    hitl_high_threshold = Column(
        Float,
        nullable=False,
        default=0.50
    )  # 0.30-0.50: high priority (2 hour SLA)
    hitl_normal_threshold = Column(
        Float,
        nullable=False,
        default=0.60
    )  # 0.50-0.60: normal priority (4 hour SLA)
    hitl_low_threshold = Column(
        Float,
        nullable=False,
        default=0.70
    )  # 0.60-0.70: low priority (8 hour SLA)

    # Metadata for flexible storage (renamed to avoid SQLAlchemy reserved word)
    tenant_metadata = Column(JSONB, nullable=False, default=dict)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="tenant")
    schema_definitions = relationship("SchemaDefinition", back_populates="tenant")
    credit_transactions = relationship("CreditTransaction", back_populates="tenant")
    subscription = relationship("Subscription", back_populates="tenant", uselist=False)
    workflows = relationship("Workflow", back_populates="tenant")
    workflow_executions = relationship("WorkflowExecution", back_populates="tenant")
    review_requests = relationship("ReviewRequest", back_populates="tenant")

    # Indexes
    __table_args__ = (
        Index("idx_tenants_status", "status"),
        Index("idx_tenants_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<Tenant(id={self.id}, name={self.name}, slug={self.slug})>"
