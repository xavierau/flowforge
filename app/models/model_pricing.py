"""ModelPricing model for admin-configurable pricing."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Numeric, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
import uuid

from app.database import Base


# Maximum allowed price per 1M tokens (USD)
# This constant MUST match the value in app/schemas/admin.py
# Both database and Pydantic validation use this limit to prevent
# setting extremely high prices that could cause billing issues
MAX_PRICE_PER_MILLION_TOKENS = Decimal("10000.0000")


class ModelPricing(Base):
    """
    ModelPricing model - stores per-model pricing configuration with versioning.

    Supports:
    - Per-model input/output pricing per 1M tokens
    - Effective date ranges for pricing versioning
    - Soft delete via is_active flag
    - Audit trail via created_by and notes
    """

    __tablename__ = "model_pricing"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name = Column(String(100), nullable=False, index=True)
    input_price_per_million = Column(Numeric(10, 4), nullable=False)
    output_price_per_million = Column(Numeric(10, 4), nullable=False)
    effective_from = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    effective_until = Column(DateTime(timezone=True), nullable=True)  # NULL = currently active
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            'effective_until IS NULL OR effective_until > effective_from',
            name='model_pricing_valid_dates'
        ),
        CheckConstraint(
            'input_price_per_million >= 0 AND output_price_per_million >= 0',
            name='model_pricing_valid_prices'
        ),
        # Upper bound constraint to prevent setting extremely high prices
        # that could cause billing issues (max $10,000 per 1M tokens)
        CheckConstraint(
            'input_price_per_million <= 10000.0000 AND output_price_per_million <= 10000.0000',
            name='model_pricing_max_prices'
        ),
    )

    @validates('input_price_per_million', 'output_price_per_million')
    def validate_price(self, key: str, value) -> Decimal:
        """Validate price is non-negative and within upper bound."""
        if value is None:
            raise ValueError(f"{key} cannot be None")
        decimal_value = Decimal(str(value))
        if decimal_value < 0:
            raise ValueError(f"{key} must be non-negative")
        if decimal_value > MAX_PRICE_PER_MILLION_TOKENS:
            raise ValueError(
                f"{key} cannot exceed ${MAX_PRICE_PER_MILLION_TOKENS:,.4f} per 1M tokens"
            )
        return decimal_value

    @validates('model_name')
    def validate_model_name(self, key: str, value: str) -> str:
        """Validate model name is not empty."""
        if not value or not value.strip():
            raise ValueError("model_name cannot be empty")
        return value.strip().lower()

    @property
    def is_current(self) -> bool:
        """Check if this pricing is currently active (no end date or future end date)."""
        if not self.is_active:
            return False
        if self.effective_until is None:
            return True
        return datetime.utcnow() < self.effective_until

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "model_name": self.model_name,
            "input_price_per_million": float(self.input_price_per_million),
            "output_price_per_million": float(self.output_price_per_million),
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_until": self.effective_until.isoformat() if self.effective_until else None,
            "is_active": self.is_active,
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "notes": self.notes,
        }

    def to_pricing_snapshot(self) -> dict:
        """Create a pricing snapshot for storage in extraction_jobs."""
        return {
            "pricing_id": str(self.id),
            "model": self.model_name,
            "input_price_per_million": float(self.input_price_per_million),
            "output_price_per_million": float(self.output_price_per_million),
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
        }

    def __repr__(self) -> str:
        return (
            f"<ModelPricing(id={self.id}, model={self.model_name}, "
            f"input={self.input_price_per_million}, output={self.output_price_per_million}, "
            f"active={self.is_active})>"
        )
