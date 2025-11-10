"""CreditPackage model for predefined credit purchase packages."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Numeric, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import Base


class CreditPackage(Base):
    """CreditPackage model - defines credit packages available for purchase."""

    __tablename__ = "credit_packages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)  # "10K Credits", "100K Credits"
    credits = Column(Integer, nullable=False)  # 10000, 100000
    price_cents = Column(Integer, nullable=False)  # $100 = 10000 cents
    unit_cost = Column(Numeric(10, 6), nullable=False)  # Auto-calculated: price / credits
    stripe_price_id = Column(String(255), unique=True, nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_credit_packages_is_active", "is_active"),
        Index("idx_credit_packages_sort_order", "sort_order"),
    )

    def __repr__(self):
        return f"<CreditPackage(id={self.id}, name={self.name}, credits={self.credits})>"
