"""
Pricing Management Service

Admin CRUD service for managing model pricing configurations.
Handles creation, expiration, and deactivation of pricing records.
"""

from datetime import datetime, timezone
from typing import Optional, List, Tuple
from uuid import UUID
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.model_pricing import ModelPricing
from app.models.enums import PricingStatus
from app.domain.metrics.pricing_service import PricingService, FALLBACK_PRICING_TABLE


logger = logging.getLogger(__name__)


class PricingManagementService:
    """
    Admin service for managing model pricing configurations.

    Handles:
    - Creating new pricing records with auto-expiration of previous
    - Listing all pricing (active and historical)
    - Getting pricing history for specific models
    - Deactivating pricing records
    - Getting list of supported models

    Security:
    - All methods assume admin authorization is enforced at API layer
    - Uses PricingStatus enum for type-safe status values
    """

    def __init__(self, db: Session):
        """
        Initialize pricing management service.

        Args:
            db: Database session for queries
        """
        self.db = db
        self._pricing_service = PricingService(db)

    def create_pricing(
        self,
        model_name: str,
        input_price: float,
        output_price: float,
        created_by: UUID,
        effective_from: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> ModelPricing:
        """
        Create a new pricing record for a model.

        Auto-expires any existing active pricing for the same model
        by setting their effective_until to the new record's effective_from.

        Args:
            model_name: Model name (will be lowercased)
            input_price: Price per 1M input tokens in USD
            output_price: Price per 1M output tokens in USD
            created_by: UUID of the admin creating the record
            effective_from: When pricing takes effect (default: now)
            notes: Optional notes about the pricing change

        Returns:
            Created ModelPricing record

        Raises:
            ValueError: If prices are negative or model_name is empty
        """
        # Validate inputs
        if not model_name or not model_name.strip():
            raise ValueError("Model name cannot be empty")
        if input_price < 0:
            raise ValueError("Input price must be non-negative")
        if output_price < 0:
            raise ValueError("Output price must be non-negative")

        model_name_lower = model_name.strip().lower()
        effective_from = effective_from or datetime.now(timezone.utc)

        # Expire existing active pricing for this model
        existing_active = (
            self.db.query(ModelPricing)
            .filter(ModelPricing.model_name == model_name_lower)
            .filter(ModelPricing.is_active == True)
            .filter(ModelPricing.effective_until.is_(None))
            .all()
        )

        for existing in existing_active:
            existing.effective_until = effective_from
            # Log at DEBUG level to avoid exposing pricing details in production logs
            logger.debug(
                f"Expired previous pricing {existing.id} for model {model_name_lower}"
            )

        # Create new pricing record
        new_pricing = ModelPricing(
            model_name=model_name_lower,
            input_price_per_million=input_price,
            output_price_per_million=output_price,
            effective_from=effective_from,
            effective_until=None,
            is_active=True,
            created_by=created_by,
            notes=notes,
        )

        self.db.add(new_pricing)
        self.db.commit()

        # CRITICAL: Clear cache IMMEDIATELY after commit to minimize race condition window
        # This ensures stale pricing data is invalidated as soon as the new pricing is committed
        self._pricing_service.clear_cache(model_name_lower)

        self.db.refresh(new_pricing)

        # Log pricing creation at INFO level (model name only for audit trail)
        # Actual pricing values logged at DEBUG level to avoid exposing sensitive data
        logger.info(f"Created new pricing {new_pricing.id} for model {model_name_lower}")
        logger.debug(
            f"Pricing details for {new_pricing.id}: "
            f"input=${input_price}/1M, output=${output_price}/1M"
        )

        return new_pricing

    def list_all_pricing(
        self,
        include_inactive: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[ModelPricing], int]:
        """
        List all model pricing records.

        Args:
            include_inactive: If True, include deactivated records
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Tuple of (pricing_list, total_count)
        """
        query = self.db.query(ModelPricing)

        if not include_inactive:
            query = query.filter(ModelPricing.is_active == True)

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        offset = (page - 1) * page_size
        records = (
            query
            .order_by(ModelPricing.model_name, ModelPricing.effective_from.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return records, total

    def get_pricing_history(
        self, model_name: str
    ) -> Tuple[List[ModelPricing], Optional[ModelPricing]]:
        """
        Get pricing history for a specific model.

        Args:
            model_name: Model name to look up

        Returns:
            Tuple of (history_list, current_pricing)
            current_pricing is None if no active pricing exists
        """
        model_name_lower = model_name.strip().lower()
        now = datetime.now(timezone.utc)

        # Get all pricing records for this model
        history = (
            self.db.query(ModelPricing)
            .filter(ModelPricing.model_name == model_name_lower)
            .order_by(ModelPricing.effective_from.desc())
            .all()
        )

        # Find current active pricing
        current = None
        for record in history:
            if record.is_active and record.effective_from <= now:
                if record.effective_until is None or record.effective_until > now:
                    current = record
                    break

        return history, current

    def deactivate_pricing(
        self,
        pricing_id: UUID,
        reason: str,
    ) -> ModelPricing:
        """
        Soft-delete a pricing record by marking it as deactivated.

        Args:
            pricing_id: UUID of the pricing record to deactivate
            reason: Reason for deactivation (stored in notes)

        Returns:
            Updated ModelPricing record

        Raises:
            ValueError: If pricing record not found
        """
        pricing = (
            self.db.query(ModelPricing)
            .filter(ModelPricing.id == pricing_id)
            .first()
        )

        if not pricing:
            raise ValueError(f"Pricing record {pricing_id} not found")

        if not pricing.is_active:
            raise ValueError(f"Pricing record {pricing_id} is already deactivated")

        # Update record
        pricing.is_active = False
        now = datetime.now(timezone.utc)
        if pricing.effective_until is None:
            pricing.effective_until = now

        # Append deactivation reason to notes
        deactivation_note = f"\n[Deactivated {now.isoformat()}] {reason}"
        if pricing.notes:
            pricing.notes += deactivation_note
        else:
            pricing.notes = deactivation_note.strip()

        self.db.commit()

        # CRITICAL: Clear cache IMMEDIATELY after commit to minimize race condition window
        # This ensures stale pricing data is invalidated as soon as the deactivation is committed
        self._pricing_service.clear_cache(pricing.model_name)

        self.db.refresh(pricing)

        # Log deactivation at INFO level (model name only for audit trail)
        # Reason logged at DEBUG to avoid potentially sensitive details in production logs
        logger.info(f"Deactivated pricing {pricing_id} for model {pricing.model_name}")
        logger.debug(f"Deactivation reason for {pricing_id}: {reason}")

        return pricing

    def get_supported_models(self) -> List[str]:
        """
        Get list of all models with configured pricing.

        Returns models from both database and fallback defaults.

        Returns:
            Sorted list of model names
        """
        return self._pricing_service.get_all_supported_models()

    def get_pricing_by_id(self, pricing_id: UUID) -> Optional[ModelPricing]:
        """
        Get a pricing record by ID.

        Args:
            pricing_id: UUID of the pricing record

        Returns:
            ModelPricing record or None if not found
        """
        return (
            self.db.query(ModelPricing)
            .filter(ModelPricing.id == pricing_id)
            .first()
        )

    def get_current_pricing_for_model(
        self, model_name: str
    ) -> Optional[ModelPricing]:
        """
        Get the current active pricing record for a model.

        Args:
            model_name: Model name

        Returns:
            Current ModelPricing record or None
        """
        model_name_lower = model_name.strip().lower()
        now = datetime.now(timezone.utc)

        return (
            self.db.query(ModelPricing)
            .filter(ModelPricing.model_name == model_name_lower)
            .filter(ModelPricing.is_active == True)
            .filter(ModelPricing.effective_from <= now)
            .filter(
                (ModelPricing.effective_until.is_(None)) |
                (ModelPricing.effective_until > now)
            )
            .order_by(ModelPricing.effective_from.desc())
            .first()
        )

    def get_default_pricing(self) -> dict:
        """
        Get the fallback default pricing table.

        Returns:
            Dictionary of model names to pricing info
        """
        return {
            model: {
                "input_price_per_million": prices["input"],
                "output_price_per_million": prices["output"],
            }
            for model, prices in FALLBACK_PRICING_TABLE.items()
            if model != "default"
        }
