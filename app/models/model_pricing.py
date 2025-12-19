"""ModelPricing model for admin-configurable pricing and model capabilities.

This model serves as the single source of truth for:
- Model pricing (input/output per 1M tokens)
- Model capabilities (vision, text, markdown conversion)
- Default model selection for different use cases
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Numeric, CheckConstraint, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
import uuid

from app.database import Base


# Maximum allowed price per 1M tokens (USD)
# This constant MUST match the value in app/schemas/admin.py
# Both database and Pydantic validation use this limit to prevent
# setting extremely high prices that could cause billing issues
MAX_PRICE_PER_MILLION_TOKENS = Decimal("10000.0000")

# Valid provider names
VALID_PROVIDERS = {"google", "openai", "qwen", "deepseek"}


class ModelPricing(Base):
    """
    ModelPricing model - stores per-model pricing and capabilities.

    Serves as the single source of truth for:
    - Per-model input/output pricing per 1M tokens
    - Model capabilities (vision, text, markdown conversion)
    - Default model selection for different use cases (extraction, markdown, llm)
    - Effective date ranges for pricing versioning
    - Soft delete via is_active flag
    - Audit trail via created_by and notes
    """

    __tablename__ = "model_pricing"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Provider and model identification
    provider = Column(String(50), nullable=False, default="google")  # google, openai, qwen, deepseek
    model_name = Column(String(100), nullable=False, index=True)
    display_name = Column(String(200), nullable=True)  # Human-readable name (e.g., "Gemini 2.5 Flash")

    # Pricing
    input_price_per_million = Column(Numeric(10, 4), nullable=False)
    output_price_per_million = Column(Numeric(10, 4), nullable=False)

    # Model capabilities
    supports_vision = Column(Boolean, nullable=False, default=False)
    supports_text = Column(Boolean, nullable=False, default=True)
    supports_markdown_conversion = Column(Boolean, nullable=False, default=False)
    supports_json_mode = Column(Boolean, nullable=False, default=False)

    # Model limits
    max_output_tokens = Column(Integer, nullable=True)  # Max tokens model can generate
    context_window = Column(Integer, nullable=True)  # Total context window size

    # Use case defaults (only one model per use case should be True)
    is_default_extraction = Column(Boolean, nullable=False, default=False)
    is_default_markdown = Column(Boolean, nullable=False, default=False)
    is_default_llm = Column(Boolean, nullable=False, default=False)

    # Pricing versioning
    effective_from = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    effective_until = Column(DateTime(timezone=True), nullable=True)  # NULL = currently active
    is_active = Column(Boolean, nullable=False, default=True)

    # Audit
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=datetime.utcnow)
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
        # Index for efficient provider-based lookups
        Index('idx_model_pricing_provider', 'provider'),
        Index('idx_model_pricing_is_active', 'is_active'),
        Index('idx_model_pricing_provider_model', 'provider', 'model_name'),
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

    @validates('provider')
    def validate_provider(self, key: str, value: str) -> str:
        """Validate provider is one of the allowed values."""
        if not value or not value.strip():
            raise ValueError("provider cannot be empty")
        value_lower = value.strip().lower()
        if value_lower not in VALID_PROVIDERS:
            raise ValueError(f"provider must be one of: {', '.join(sorted(VALID_PROVIDERS))}")
        return value_lower

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
            "provider": self.provider,
            "model_name": self.model_name,
            "display_name": self.display_name or self.model_name,
            "input_price_per_million": float(self.input_price_per_million),
            "output_price_per_million": float(self.output_price_per_million),
            # Capabilities
            "supports_vision": self.supports_vision,
            "supports_text": self.supports_text,
            "supports_markdown_conversion": self.supports_markdown_conversion,
            "supports_json_mode": self.supports_json_mode,
            # Limits
            "max_output_tokens": self.max_output_tokens,
            "context_window": self.context_window,
            # Defaults
            "is_default_extraction": self.is_default_extraction,
            "is_default_markdown": self.is_default_markdown,
            "is_default_llm": self.is_default_llm,
            # Versioning
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_until": self.effective_until.isoformat() if self.effective_until else None,
            "is_active": self.is_active,
            # Audit
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "notes": self.notes,
        }

    def to_pricing_snapshot(self) -> dict:
        """Create a pricing snapshot for storage in extraction_jobs."""
        return {
            "pricing_id": str(self.id),
            "provider": self.provider,
            "model": self.model_name,
            "input_price_per_million": float(self.input_price_per_million),
            "output_price_per_million": float(self.output_price_per_million),
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
        }

    def to_available_model(self) -> dict:
        """Convert to a simplified dict for frontend model selection dropdown."""
        return {
            "id": str(self.id),
            "provider": self.provider,
            "model_name": self.model_name,
            "display_name": self.display_name or self.model_name,
            "supports_vision": self.supports_vision,
            "supports_markdown_conversion": self.supports_markdown_conversion,
            "supports_json_mode": self.supports_json_mode,
            "input_price_per_million": float(self.input_price_per_million),
            "output_price_per_million": float(self.output_price_per_million),
            "is_default_extraction": self.is_default_extraction,
            "is_default_markdown": self.is_default_markdown,
            "is_default_llm": self.is_default_llm,
        }

    def __repr__(self) -> str:
        return (
            f"<ModelPricing(id={self.id}, provider={self.provider}, model={self.model_name}, "
            f"input={self.input_price_per_million}, output={self.output_price_per_million}, "
            f"vision={self.supports_vision}, active={self.is_active})>"
        )
