"""Pricing service for calculating costs."""
from typing import Dict
from .value_objects import TokenUsage, CostEstimate


class PricingService:
    """Service for calculating costs based on token usage and model."""

    # Pricing per 1M tokens (input/output) in USD
    # Based on typical market rates as of 2025
    PRICING_TABLE: Dict[str, Dict[str, float]] = {
        "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
        "gpt-4-vision-preview": {"input": 10.00, "output": 30.00},
        "gpt-4o": {"input": 5.00, "output": 15.00},
        "deepseek-chat": {"input": 0.27, "output": 1.10},
        "default": {"input": 0.50, "output": 1.50},  # Fallback pricing
    }

    @classmethod
    def calculate_cost(
        cls, token_usage: TokenUsage, model: str = "default"
    ) -> CostEstimate:
        """
        Calculate cost based on token usage and model.

        Args:
            token_usage: Token usage (input + output)
            model: Model name used for extraction

        Returns:
            CostEstimate with calculated amount
        """
        # Get pricing for model (fallback to default if not found)
        pricing = cls.PRICING_TABLE.get(model, cls.PRICING_TABLE["default"])

        # Calculate cost (pricing is per 1M tokens)
        input_cost = (token_usage.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (token_usage.output_tokens / 1_000_000) * pricing["output"]

        total_cost = input_cost + output_cost

        return CostEstimate(amount=total_cost, currency="USD")

    @classmethod
    def get_model_pricing(cls, model: str = "default") -> Dict[str, float]:
        """
        Get pricing information for a specific model.

        Args:
            model: Model name

        Returns:
            Dictionary with input and output pricing
        """
        return cls.PRICING_TABLE.get(model, cls.PRICING_TABLE["default"])
