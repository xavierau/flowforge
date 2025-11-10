"""Value objects for metrics domain."""
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DateRange:
    """Immutable date range value object."""

    start_date: datetime
    end_date: datetime

    def __post_init__(self):
        """Validate date range."""
        if self.end_date <= self.start_date:
            raise ValueError("End date must be after start date")

    @property
    def days_count(self) -> int:
        """Calculate number of days in range."""
        delta = self.end_date - self.start_date
        return delta.days

    @classmethod
    def last_30_days(cls) -> "DateRange":
        """Factory method for last 30 days."""
        end = datetime.now()
        start = end - timedelta(days=30)
        return cls(start_date=start, end_date=end)


@dataclass(frozen=True)
class TokenUsage:
    """Immutable token usage value object."""

    input_tokens: int
    output_tokens: int

    def __post_init__(self):
        """Validate token counts."""
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise ValueError("Token counts cannot be negative")

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens."""
        return self.input_tokens + self.output_tokens

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        """Add two token usages together."""
        if not isinstance(other, TokenUsage):
            raise TypeError("Can only add TokenUsage to TokenUsage")

        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )


@dataclass(frozen=True)
class CostEstimate:
    """Immutable cost estimate value object."""

    amount: float
    currency: str = "USD"

    def __post_init__(self):
        """Validate cost amount."""
        if self.amount < 0:
            raise ValueError("Cost amount cannot be negative")

    def formatted(self) -> str:
        """Format cost for display."""
        return f"${self.amount:,.2f}"

    def __add__(self, other: "CostEstimate") -> "CostEstimate":
        """Add two cost estimates together."""
        if not isinstance(other, CostEstimate):
            raise TypeError("Can only add CostEstimate to CostEstimate")

        if self.currency != other.currency:
            raise ValueError("Cannot add costs with different currencies")

        return CostEstimate(
            amount=self.amount + other.amount,
            currency=self.currency,
        )
