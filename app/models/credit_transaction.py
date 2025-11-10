"""CreditTransaction model for event-sourced credit tracking."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
import uuid

from app.database import Base
from app.models.enums import CreditTransactionType, ReferenceType


class CreditTransaction(Base):
    """
    CreditTransaction model - immutable event log for all credit movements.

    Balance is calculated on-demand by summing transactions, NOT stored.
    This ensures audit trail integrity and prevents race conditions.
    """

    __tablename__ = "credit_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Transaction type and amount (signed integer)
    # Positive = credits added (top-up, refund, adjustment)
    # Negative = credits deducted (job completion, manual adjustment)
    transaction_type = Column(
        String(50),
        nullable=False,
        index=True
    )  # topup, deduction, refund, admin_adjustment

    amount = Column(Integer, nullable=False)  # Signed: +100 (topup), -5 (deduction)

    # Reference to related entity (what caused this transaction)
    reference_type = Column(String(50), nullable=True)  # extraction_job, payment, manual
    reference_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # External references (Stripe payments, etc)
    stripe_payment_intent_id = Column(String(255), nullable=True, index=True, unique=True)
    stripe_charge_id = Column(String(255), nullable=True)

    # Admin tracking (for manual adjustments)
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    description = Column(Text, nullable=False)  # Human-readable description
    transaction_metadata = Column(JSONB, nullable=False, default=dict)  # Flexible metadata

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="credit_transactions")
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    # Composite indexes for performance
    __table_args__ = (
        # Fast balance calculation: ORDER BY created_at for transaction stream
        Index("idx_credit_tx_tenant_created", "tenant_id", "created_at"),

        # Fast lookup by reference (find transactions for a job)
        Index("idx_credit_tx_reference", "reference_type", "reference_id"),

        # Fast type filtering
        Index("idx_credit_tx_type", "transaction_type"),

        # Stripe payment lookups
        Index("idx_credit_tx_stripe_intent", "stripe_payment_intent_id"),
    )

    @validates('transaction_type')
    def validate_transaction_type(self, key, value):
        """Ensure transaction_type is valid enum value"""
        if isinstance(value, CreditTransactionType):
            return value.value
        if value not in [t.value for t in CreditTransactionType]:
            valid_types = [t.value for t in CreditTransactionType]
            raise ValueError(
                f"Invalid transaction_type: {value}. "
                f"Must be one of: {valid_types}"
            )
        return value

    @validates('reference_type')
    def validate_reference_type(self, key, value):
        """Ensure reference_type is valid enum value"""
        if value is None:
            return None
        if isinstance(value, ReferenceType):
            return value.value
        if value not in [t.value for t in ReferenceType]:
            valid_types = [t.value for t in ReferenceType]
            raise ValueError(
                f"Invalid reference_type: {value}. "
                f"Must be one of: {valid_types}"
            )
        return value

    def __repr__(self):
        return f"<CreditTransaction(id={self.id}, tenant_id={self.tenant_id}, type={self.transaction_type}, amount={self.amount})>"
