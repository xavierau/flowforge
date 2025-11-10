"""Tests for metrics domain value objects."""
import pytest
from datetime import datetime, timedelta
from app.domain.metrics.value_objects import DateRange, TokenUsage, CostEstimate


class TestDateRange:
    """Test DateRange value object."""

    def test_create_date_range_valid(self):
        """Test creating a valid date range."""
        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 31)
        date_range = DateRange(start_date=start, end_date=end)

        assert date_range.start_date == start
        assert date_range.end_date == end

    def test_create_date_range_invalid_order(self):
        """Test that end date must be after start date."""
        start = datetime(2025, 1, 31)
        end = datetime(2025, 1, 1)

        with pytest.raises(ValueError, match="End date must be after start date"):
            DateRange(start_date=start, end_date=end)

    def test_date_range_equality(self):
        """Test date range equality."""
        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 31)

        range1 = DateRange(start_date=start, end_date=end)
        range2 = DateRange(start_date=start, end_date=end)

        assert range1 == range2

    def test_date_range_days_count(self):
        """Test calculating days in range."""
        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 8)  # 7 days
        date_range = DateRange(start_date=start, end_date=end)

        assert date_range.days_count == 7

    def test_last_30_days_factory(self):
        """Test factory method for last 30 days."""
        date_range = DateRange.last_30_days()

        assert date_range.days_count == 30
        assert date_range.end_date.date() == datetime.now().date()


class TestTokenUsage:
    """Test TokenUsage value object."""

    def test_create_token_usage(self):
        """Test creating token usage."""
        usage = TokenUsage(input_tokens=1000, output_tokens=500)

        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500

    def test_token_usage_negative_values(self):
        """Test that negative token values are rejected."""
        with pytest.raises(ValueError, match="Token counts cannot be negative"):
            TokenUsage(input_tokens=-100, output_tokens=500)

        with pytest.raises(ValueError, match="Token counts cannot be negative"):
            TokenUsage(input_tokens=1000, output_tokens=-50)

    def test_total_tokens_property(self):
        """Test total tokens calculation."""
        usage = TokenUsage(input_tokens=1000, output_tokens=500)

        assert usage.total_tokens == 1500

    def test_token_usage_equality(self):
        """Test token usage equality."""
        usage1 = TokenUsage(input_tokens=1000, output_tokens=500)
        usage2 = TokenUsage(input_tokens=1000, output_tokens=500)

        assert usage1 == usage2

    def test_token_usage_add_operator(self):
        """Test adding two token usages."""
        usage1 = TokenUsage(input_tokens=1000, output_tokens=500)
        usage2 = TokenUsage(input_tokens=2000, output_tokens=1000)

        result = usage1 + usage2

        assert result.input_tokens == 3000
        assert result.output_tokens == 1500
        assert result.total_tokens == 4500


class TestCostEstimate:
    """Test CostEstimate value object."""

    def test_create_cost_estimate(self):
        """Test creating cost estimate."""
        cost = CostEstimate(amount=10.50, currency="USD")

        assert cost.amount == 10.50
        assert cost.currency == "USD"

    def test_cost_estimate_negative_amount(self):
        """Test that negative amounts are rejected."""
        with pytest.raises(ValueError, match="Cost amount cannot be negative"):
            CostEstimate(amount=-10.00, currency="USD")

    def test_cost_estimate_default_currency(self):
        """Test default currency is USD."""
        cost = CostEstimate(amount=10.00)

        assert cost.currency == "USD"

    def test_cost_estimate_formatted_display(self):
        """Test formatted display string."""
        cost = CostEstimate(amount=10.50, currency="USD")

        assert cost.formatted() == "$10.50"

    def test_cost_estimate_large_amount_formatted(self):
        """Test formatting large amounts."""
        cost = CostEstimate(amount=1234.56, currency="USD")

        assert cost.formatted() == "$1,234.56"

    def test_cost_estimate_equality(self):
        """Test cost estimate equality."""
        cost1 = CostEstimate(amount=10.50, currency="USD")
        cost2 = CostEstimate(amount=10.50, currency="USD")

        assert cost1 == cost2

    def test_cost_estimate_add_operator(self):
        """Test adding two cost estimates."""
        cost1 = CostEstimate(amount=10.50, currency="USD")
        cost2 = CostEstimate(amount=5.25, currency="USD")

        result = cost1 + cost2

        assert result.amount == 15.75
        assert result.currency == "USD"

    def test_cost_estimate_add_different_currency_raises(self):
        """Test that adding different currencies raises error."""
        cost1 = CostEstimate(amount=10.00, currency="USD")
        cost2 = CostEstimate(amount=5.00, currency="EUR")

        with pytest.raises(ValueError, match="Cannot add costs with different currencies"):
            cost1 + cost2
