"""Pricing service for calculating costs with database-backed pricing.

Loads pricing from database with Redis caching (1 hour TTL).
Falls back to hardcoded defaults if DB unavailable.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
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

    def get_models_for_extraction(self) -> List[Dict]:
        """Get active models that support extraction (vision capability).

        Returns:
            List of model dictionaries suitable for frontend dropdown.
        """
        if not self.db:
            return []
        models = (
            self.db.query(ModelPricing)
            .filter(ModelPricing.is_active == True)
            .filter(ModelPricing.supports_vision == True)
            .order_by(ModelPricing.provider, ModelPricing.model_name)
            .all()
        )
        return [m.to_available_model() for m in models]

    def get_models_for_markdown(self) -> List[Dict]:
        """Get active models that support markdown conversion.

        Returns:
            List of model dictionaries suitable for frontend dropdown.
        """
        if not self.db:
            return []
        models = (
            self.db.query(ModelPricing)
            .filter(ModelPricing.is_active == True)
            .filter(ModelPricing.supports_markdown_conversion == True)
            .order_by(ModelPricing.provider, ModelPricing.model_name)
            .all()
        )
        return [m.to_available_model() for m in models]

    def get_models_for_llm(self) -> List[Dict]:
        """Get active models suitable for LLM completion.

        Returns:
            List of model dictionaries suitable for frontend dropdown.
        """
        if not self.db:
            return []
        models = (
            self.db.query(ModelPricing)
            .filter(ModelPricing.is_active == True)
            .filter(ModelPricing.supports_text == True)
            .order_by(ModelPricing.provider, ModelPricing.model_name)
            .all()
        )
        return [m.to_available_model() for m in models]

    def get_default_model(self, use_case: str) -> Optional[Dict]:
        """Get the default model for a specific use case.

        Args:
            use_case: One of 'extraction', 'markdown', or 'llm'

        Returns:
            Model dict or None if no default set
        """
        if not self.db:
            return None

        field_map = {
            "extraction": ModelPricing.is_default_extraction,
            "markdown": ModelPricing.is_default_markdown,
            "llm": ModelPricing.is_default_llm,
        }

        if use_case not in field_map:
            return None

        model = (
            self.db.query(ModelPricing)
            .filter(ModelPricing.is_active == True)
            .filter(field_map[use_case] == True)
            .first()
        )

        return model.to_available_model() if model else None

    def get_models_by_provider(self, provider: str) -> List[Dict]:
        """Get all active models for a specific provider.

        Args:
            provider: Provider name (e.g., 'google', 'openai')

        Returns:
            List of model dictionaries for the provider.
        """
        if not self.db:
            return []
        models = (
            self.db.query(ModelPricing)
            .filter(ModelPricing.is_active == True)
            .filter(ModelPricing.provider == provider.lower())
            .order_by(ModelPricing.model_name)
            .all()
        )
        return [m.to_available_model() for m in models]

    def get_available_providers(self) -> List[str]:
        """Get list of providers with active models.

        Returns:
            Sorted list of provider names.
        """
        if not self.db:
            return []
        providers = (
            self.db.query(ModelPricing.provider)
            .filter(ModelPricing.is_active == True)
            .distinct()
            .all()
        )
        return sorted([p[0] for p in providers])

    def get_document_converter_pricing(
        self, converter_name: str
    ) -> Optional[Dict]:
        """Get pricing for a document converter (e.g., LlamaParse).

        Document converters use page-based or document-based pricing
        instead of token-based pricing.

        Args:
            converter_name: Converter name (e.g., 'llamaparse')

        Returns:
            Dictionary with pricing info or None if not found:
            {
                "pricing_id": str,
                "provider": str,
                "model_name": str,
                "pricing_type": str,  # 'page' or 'document'
                "credit_rate_per_page": float (if page-based),
                "credit_rate_per_document": float (if document-based),
            }
        """
        # Input validation - early return for invalid input
        if not converter_name or not converter_name.strip():
            return None
        if len(converter_name) > 100:
            return None
        converter_name = converter_name.strip().lower()

        if not self.db:
            return None

        from app.models.enums import PricingType

        try:
            now = datetime.now(timezone.utc)
            pricing = (
                self.db.query(ModelPricing)
                .filter(ModelPricing.is_active == True)
                .filter(ModelPricing.is_document_converter == True)
                .filter(ModelPricing.model_name == converter_name)
                .filter(ModelPricing.effective_from <= now)
                .filter(
                    (ModelPricing.effective_until.is_(None)) |
                    (ModelPricing.effective_until > now)
                )
                .order_by(ModelPricing.effective_from.desc())
                .first()
            )

            if not pricing:
                return None

            result = {
                "pricing_id": str(pricing.id),
                "provider": pricing.provider,
                "model_name": pricing.model_name,
                "pricing_type": pricing.pricing_type,
            }

            if pricing.pricing_type == PricingType.PAGE.value:
                result["credit_rate_per_page"] = float(
                    pricing.credit_rate_per_page or 0
                )
            elif pricing.pricing_type == PricingType.DOCUMENT.value:
                result["credit_rate_per_document"] = float(
                    pricing.credit_rate_per_document or 0
                )

            return result

        except Exception as e:
            logger.warning(f"Document converter pricing lookup failed: {e}")
            return None

    def calculate_page_based_credits(
        self,
        converter_name: str,
        page_count: int,
    ) -> Tuple[int, Dict]:
        """Calculate credits for page-based pricing.

        Used for document converters like LlamaParse that charge per page.

        Args:
            converter_name: Name of the document converter
            page_count: Number of pages to process

        Returns:
            Tuple of (credits_required, pricing_snapshot)
            - credits_required: Integer credits to charge
            - pricing_snapshot: Dict with pricing details for audit

        Raises:
            ValueError: If converter not found or pricing not configured
        """
        from app.models.enums import PricingType
        from decimal import Decimal, ROUND_CEILING

        pricing = self.get_document_converter_pricing(converter_name)

        if not pricing:
            raise ValueError(
                f"No pricing configured for document converter: {converter_name}"
            )

        if pricing["pricing_type"] != PricingType.PAGE.value:
            raise ValueError(
                f"Converter {converter_name} uses {pricing['pricing_type']} pricing, "
                f"not page-based pricing"
            )

        rate = Decimal(str(pricing.get("credit_rate_per_page", 0)))
        if rate <= 0:
            raise ValueError(
                f"Invalid credit_rate_per_page for {converter_name}: {rate}"
            )

        # Calculate credits (always round up to ensure we don't undercharge)
        total_credits = (rate * page_count).quantize(
            Decimal("1"), rounding=ROUND_CEILING
        )

        snapshot = {
            "converter": converter_name,
            "pricing_type": PricingType.PAGE.value,
            "pricing_id": pricing["pricing_id"],
            "page_count": page_count,
            "credit_rate_per_page": float(rate),
            "credits_calculated": int(total_credits),
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }

        return int(total_credits), snapshot

    def calculate_document_based_credits(
        self,
        converter_name: str,
    ) -> Tuple[int, Dict]:
        """Calculate credits for document-based (flat rate) pricing.

        Used for converters that charge per document regardless of page count.

        Args:
            converter_name: Name of the document converter

        Returns:
            Tuple of (credits_required, pricing_snapshot)

        Raises:
            ValueError: If converter not found or pricing not configured
        """
        from app.models.enums import PricingType
        from decimal import Decimal, ROUND_CEILING

        pricing = self.get_document_converter_pricing(converter_name)

        if not pricing:
            raise ValueError(
                f"No pricing configured for document converter: {converter_name}"
            )

        if pricing["pricing_type"] != PricingType.DOCUMENT.value:
            raise ValueError(
                f"Converter {converter_name} uses {pricing['pricing_type']} pricing, "
                f"not document-based pricing"
            )

        rate = Decimal(str(pricing.get("credit_rate_per_document", 0)))
        if rate <= 0:
            raise ValueError(
                f"Invalid credit_rate_per_document for {converter_name}: {rate}"
            )

        # Round up for flat rate
        credits = int(rate.quantize(Decimal("1"), rounding=ROUND_CEILING))

        snapshot = {
            "converter": converter_name,
            "pricing_type": PricingType.DOCUMENT.value,
            "pricing_id": pricing["pricing_id"],
            "credit_rate_per_document": float(rate),
            "credits_calculated": credits,
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }

        return credits, snapshot

    def get_document_converters(self) -> List[Dict]:
        """Get all active document converters with their pricing.

        Returns:
            List of document converter dictionaries for frontend selection.
        """
        if not self.db:
            return []

        converters = (
            self.db.query(ModelPricing)
            .filter(ModelPricing.is_active == True)
            .filter(ModelPricing.is_document_converter == True)
            .order_by(ModelPricing.provider, ModelPricing.model_name)
            .all()
        )

        return [c.to_available_model() for c in converters]
