"""Pricing service for calculating costs with database-backed pricing.

Loads pricing from database with Redis caching (1 hour TTL).
Falls back to hardcoded defaults if DB unavailable.
"""
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
import json
import logging
import redis

from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.models.model_pricing import ModelPricing
from .value_objects import TokenUsage, CostEstimate


logger = logging.getLogger(__name__)

# Redis client for distributed caching
_redis_client: Optional[redis.Redis] = None

# Cache TTL in seconds (1 hour)
CACHE_TTL = 3600

# Cache key namespace prefix
# This prevents collisions with other applications sharing the same Redis instance
# and makes cache keys less predictable for security
CACHE_KEY_PREFIX = "aidp:pricing"

# Fallback pricing per 1M tokens (input/output) in USD
# Used when database is unavailable
FALLBACK_PRICING_TABLE: Dict[str, Dict[str, float]] = {
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "gpt-4-vision-preview": {"input": 10.00, "output": 30.00},
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "deepseek-chat": {"input": 0.27, "output": 1.10},
    "default": {"input": 0.50, "output": 1.50},
}


class PricingService:
    """Service for calculating costs based on token usage and model.

    Supports:
    - Database-backed pricing with Redis caching
    - Fallback to hardcoded defaults if DB unavailable
    - Historical pricing lookups for job cost snapshots
    - Immutable pricing snapshots for completed jobs
    """

    def __init__(self, db: Optional[Session] = None):
        """Initialize pricing service.

        Args:
            db: Database session for queries (optional for classmethod compatibility)
        """
        self.db = db
        self._init_redis()

    def _init_redis(self):
        """Initialize Redis client if not already initialized."""
        global _redis_client
        if _redis_client is None:
            try:
                redis_url = app_settings.celery_broker_url
                _redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                _redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis not available for pricing cache: {e}")
                _redis_client = None

    def _get_cache_key(self, model: str) -> str:
        """Generate Redis cache key for model pricing.

        Uses namespaced prefix to prevent collisions and improve security.
        Format: aidp:pricing:model:<model_name>
        """
        return f"{CACHE_KEY_PREFIX}:model:{model.lower()}"

    def _get_all_pricing_cache_key(self) -> str:
        """Generate Redis cache key for all current pricing.

        Uses namespaced prefix to prevent collisions and improve security.
        Format: aidp:pricing:all_current
        """
        return f"{CACHE_KEY_PREFIX}:all_current"

    def get_current_pricing(self, model: str) -> Dict[str, float]:
        """Get current pricing for a specific model.

        Looks up pricing in this order:
        1. Redis cache
        2. Database (active record with no end date or future end date)
        3. Fallback to hardcoded defaults

        Args:
            model: Model name (e.g., "gemini-2.5-flash")

        Returns:
            Dictionary with 'input' and 'output' prices per 1M tokens
        """
        model_lower = model.lower()

        # Check Redis cache first
        if _redis_client:
            try:
                cache_key = self._get_cache_key(model_lower)
                cached_value = _redis_client.get(cache_key)
                if cached_value:
                    return json.loads(cached_value)
            except Exception as e:
                logger.warning(f"Redis cache read failed for pricing: {e}")

        # Query database
        if self.db:
            try:
                now = datetime.now(timezone.utc)
                pricing = (
                    self.db.query(ModelPricing)
                    .filter(ModelPricing.model_name == model_lower)
                    .filter(ModelPricing.is_active == True)
                    .filter(ModelPricing.effective_from <= now)
                    .filter(
                        (ModelPricing.effective_until.is_(None)) |
                        (ModelPricing.effective_until > now)
                    )
                    .order_by(ModelPricing.effective_from.desc())
                    .first()
                )

                if pricing:
                    result = {
                        "input": float(pricing.input_price_per_million),
                        "output": float(pricing.output_price_per_million),
                    }

                    # Cache in Redis
                    if _redis_client:
                        try:
                            cache_key = self._get_cache_key(model_lower)
                            _redis_client.setex(
                                cache_key,
                                CACHE_TTL,
                                json.dumps(result)
                            )
                        except Exception as e:
                            logger.warning(f"Redis cache write failed for pricing: {e}")

                    return result
            except Exception as e:
                logger.warning(f"Database pricing lookup failed: {e}")

        # Fallback to hardcoded defaults
        return FALLBACK_PRICING_TABLE.get(
            model_lower,
            FALLBACK_PRICING_TABLE["default"]
        )

    def get_pricing_for_date(
        self, model: str, date: datetime
    ) -> Dict[str, float]:
        """Get pricing that was effective at a specific date.

        Used for historical cost calculations or auditing.

        Args:
            model: Model name
            date: The date to look up pricing for

        Returns:
            Dictionary with 'input' and 'output' prices per 1M tokens
        """
        model_lower = model.lower()

        if self.db:
            try:
                # Find pricing that was active at the given date
                pricing = (
                    self.db.query(ModelPricing)
                    .filter(ModelPricing.model_name == model_lower)
                    .filter(ModelPricing.effective_from <= date)
                    .filter(
                        (ModelPricing.effective_until.is_(None)) |
                        (ModelPricing.effective_until > date)
                    )
                    .order_by(ModelPricing.effective_from.desc())
                    .first()
                )

                if pricing:
                    return {
                        "input": float(pricing.input_price_per_million),
                        "output": float(pricing.output_price_per_million),
                    }
            except Exception as e:
                logger.warning(f"Historical pricing lookup failed: {e}")

        # Fallback to current pricing or defaults
        return self.get_current_pricing(model)

    def calculate_and_snapshot(
        self, token_usage: TokenUsage, model: str
    ) -> Tuple[CostEstimate, Dict]:
        """Calculate cost and create an immutable pricing snapshot.

        Used when finalizing extraction jobs to store both the cost
        and the pricing used for auditing.

        Args:
            token_usage: Token usage (input + output)
            model: Model name used for extraction

        Returns:
            Tuple of (CostEstimate, pricing_snapshot dict)
        """
        pricing = self.get_current_pricing(model)

        # Calculate cost (pricing is per 1M tokens)
        input_cost = (token_usage.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (token_usage.output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        cost_estimate = CostEstimate(amount=total_cost, currency="USD")

        # Create immutable snapshot
        pricing_snapshot = {
            "model": model,
            "input_price_per_million": pricing["input"],
            "output_price_per_million": pricing["output"],
            "input_tokens": token_usage.input_tokens,
            "output_tokens": token_usage.output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "calculated_at": datetime.now(timezone.utc).isoformat(),
            "currency": "USD",
        }

        return cost_estimate, pricing_snapshot

    def clear_cache(self, model: Optional[str] = None) -> None:
        """Clear the Redis pricing cache.

        Args:
            model: Optional specific model to clear. If None, clears all pricing cache.
        """
        if not _redis_client:
            return

        try:
            if model:
                cache_key = self._get_cache_key(model.lower())
                _redis_client.delete(cache_key)
            else:
                # Clear all pricing cache using namespaced prefix
                pattern = f"{CACHE_KEY_PREFIX}:*"
                for cache_key in _redis_client.scan_iter(match=pattern):
                    _redis_client.delete(cache_key)
        except Exception as e:
            logger.warning(f"Redis cache clear failed: {e}")

    @classmethod
    def calculate_cost(
        cls, token_usage: TokenUsage, model: str = "default"
    ) -> CostEstimate:
        """Calculate cost based on token usage and model.

        This is a classmethod for backward compatibility.
        Uses fallback pricing table (no DB lookup).

        For DB-backed pricing, use instance methods instead.

        Args:
            token_usage: Token usage (input + output)
            model: Model name used for extraction

        Returns:
            CostEstimate with calculated amount
        """
        pricing = FALLBACK_PRICING_TABLE.get(
            model.lower(),
            FALLBACK_PRICING_TABLE["default"]
        )

        input_cost = (token_usage.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (token_usage.output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        return CostEstimate(amount=total_cost, currency="USD")

    @classmethod
    def get_model_pricing(cls, model: str = "default") -> Dict[str, float]:
        """Get pricing information for a specific model.

        This is a classmethod for backward compatibility.
        Uses fallback pricing table (no DB lookup).

        For DB-backed pricing, use get_current_pricing() instead.

        Args:
            model: Model name

        Returns:
            Dictionary with input and output pricing
        """
        return FALLBACK_PRICING_TABLE.get(
            model.lower(),
            FALLBACK_PRICING_TABLE["default"]
        )

    def get_all_supported_models(self) -> list[str]:
        """Get list of all models with configured pricing.

        Returns models from both database and fallback table.

        Returns:
            List of model names
        """
        models = set(FALLBACK_PRICING_TABLE.keys())
        models.discard("default")  # Remove 'default' placeholder

        if self.db:
            try:
                db_models = (
                    self.db.query(ModelPricing.model_name)
                    .filter(ModelPricing.is_active == True)
                    .distinct()
                    .all()
                )
                for (model_name,) in db_models:
                    models.add(model_name)
            except Exception as e:
                logger.warning(f"Failed to get models from database: {e}")

        return sorted(list(models))
