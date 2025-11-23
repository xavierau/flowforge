"""
Extraction credit validation and deduction service.

This module provides centralized credit validation and deduction logic for extraction jobs,
ensuring atomic job creation + payment and preventing race conditions.
"""

from typing import Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException
import logging

from app.models.tenant import Tenant
from app.models.credit_transaction import CreditTransaction
from app.models.enums import CreditTransactionType, ReferenceType
from app.services.credit_service import CreditService
from app.exceptions.credits import InsufficientCreditsError

# Configure structured logging for audit trail
logger = logging.getLogger(__name__)


class ExtractionCreditValidator:
    """
    Application service for validating and deducting extraction credits.

    Implements synchronous credit deduction pattern with pessimistic locking
    to prevent race conditions and ensure atomic job creation + payment.

    SOLID Principles:
    - SRP: Single responsibility - credit validation for extractions
    - OCP: Open for extension (subclass for different credit models)
    - DIP: Depends on abstractions (CreditService interface)

    Usage:
        validator = ExtractionCreditValidator(db)
        transaction, cost = validator.validate_and_deduct_credits(
            tenant_id=tenant_id,
            page_count=5,
            job_id=job_id,
            document_id=document_id,
            user_id=user_id,
            model_provider="google",
            model_name="gemini-2.5-flash"
        )
    """

    def __init__(self, db: Session):
        """
        Initialize credit validator.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.credit_service = CreditService(db)

    def validate_and_deduct_credits(
        self,
        tenant_id: UUID,
        page_count: int,
        job_id: UUID,
        document_id: UUID,
        user_id: UUID,
        model_provider: str,
        model_name: str
    ) -> Tuple[CreditTransaction, int]:
        """
        Atomically validate credit balance and deduct credits for extraction.

        This method MUST be called within an active database transaction
        BEFORE queuing the extraction task.

        Pattern copied from app/api/documents.py:206-319 (known working implementation).

        Args:
            tenant_id: Tenant UUID
            page_count: Number of pages to process (determines cost)
            job_id: ExtractionJob UUID (for reference linking)
            document_id: Document UUID (for metadata)
            user_id: User who initiated extraction
            model_provider: VLLM provider name
            model_name: Model name

        Returns:
            Tuple of (CreditTransaction, required_credits)

        Raises:
            HTTPException(400): Invalid input parameters
            HTTPException(402): Insufficient credits
            HTTPException(404): Tenant not found
            HTTPException(500): Credit deduction failed

        Database State:
            - Acquires SELECT FOR UPDATE lock on tenant row
            - Creates credit_transactions record
            - Updates tenant.cached_balance
            - All within caller's transaction (caller must commit)

        Example:
            >>> validator = ExtractionCreditValidator(db)
            >>> try:
            ...     transaction, cost = validator.validate_and_deduct_credits(
            ...         tenant_id=current_user.tenant_id,
            ...         page_count=5,
            ...         job_id=job.id,
            ...         document_id=doc.id,
            ...         user_id=current_user.id,
            ...         model_provider="google",
            ...         model_name="gemini-2.5-flash"
            ...     )
            ...     db.commit()
            ... except HTTPException as e:
            ...     db.rollback()
            ...     raise
        """
        # --- INPUT VALIDATION ---
        # Validate page_count (prevent negative values, overflow, excessive charges)
        from app.schemas.error import invalid_input_error

        if page_count is not None and page_count < 0:
            raise HTTPException(
                status_code=400,
                detail=invalid_input_error(
                    field="page_count",
                    reason="Page count cannot be negative",
                    value=page_count
                )
            )

        # Set reasonable upper limit to prevent abuse (10,000 pages max)
        MAX_PAGE_COUNT = 10000
        if page_count is not None and page_count > MAX_PAGE_COUNT:
            raise HTTPException(
                status_code=400,
                detail=invalid_input_error(
                    field="page_count",
                    reason=f"Page count exceeds maximum allowed ({MAX_PAGE_COUNT})",
                    value=page_count
                )
            )

        # Validate model_provider against whitelist
        VALID_PROVIDERS = ["google", "openai", "deepseek"]
        if model_provider not in VALID_PROVIDERS:
            raise HTTPException(
                status_code=400,
                detail=invalid_input_error(
                    field="model_provider",
                    reason=f"Invalid provider. Must be one of: {', '.join(VALID_PROVIDERS)}",
                    value=model_provider
                )
            )

        # Validate model_name is not empty or whitespace
        if not model_name or not model_name.strip():
            raise HTTPException(
                status_code=400,
                detail=invalid_input_error(
                    field="model_name",
                    reason="Model name cannot be empty",
                    value=model_name
                )
            )
        # --- END INPUT VALIDATION ---

        # Calculate required credits (1 credit per page, minimum 1)
        required_credits = page_count or 1

        # Log credit deduction attempt (for audit trail)
        logger.info(
            "credit_deduction_started",
            extra={
                "event": "credit_deduction_started",
                "tenant_id": str(tenant_id),
                "user_id": str(user_id),
                "job_id": str(job_id),
                "document_id": str(document_id),
                "page_count": page_count,
                "required_credits": required_credits,
                "model_provider": model_provider,
                "model_name": model_name,
            }
        )

        try:
            # Set lock timeout to prevent infinite blocking (5 seconds max)
            # If we can't acquire lock within 5s, fail fast and let user retry
            from sqlalchemy import text
            self.db.execute(text("SET LOCAL lock_timeout = '5s'"))

            # CRITICAL: Acquire pessimistic lock on tenant row FIRST
            # This prevents concurrent requests from checking credits simultaneously
            tenant = (
                self.db.query(Tenant)
                .filter(Tenant.id == tenant_id)
                .with_for_update()  # SELECT FOR UPDATE - blocks other transactions
                .first()
            )

            if not tenant:
                from app.schemas.error import tenant_not_found_error
                raise HTTPException(
                    status_code=404,
                    detail=tenant_not_found_error(tenant_id=str(tenant_id))
                )

            # Check credit balance inline (avoid redundant query)
            # We already fetched the tenant with SELECT FOR UPDATE, use cached_balance directly
            current_balance = tenant.cached_balance or 0

            if current_balance < required_credits:
                # Log insufficient credits rejection
                logger.warning(
                    "credit_deduction_rejected_insufficient_balance",
                    extra={
                        "event": "credit_deduction_rejected_insufficient_balance",
                        "tenant_id": str(tenant_id),
                        "user_id": str(user_id),
                        "job_id": str(job_id),
                        "required_credits": required_credits,
                        "available_credits": current_balance,
                        "deficit": required_credits - current_balance,
                    }
                )

                # Release lock by raising exception (caller will rollback)
                from app.schemas.error import insufficient_credits_error
                raise HTTPException(
                    status_code=402,  # HTTP 402 Payment Required
                    detail=insufficient_credits_error(
                        required=required_credits,
                        available=current_balance
                    )
                )

            # SYNCHRONOUS DEDUCTION: Deduct credits IMMEDIATELY
            # This is atomic with job creation - both succeed or both fail
            credit_transaction = self.credit_service.deduct_credits(
                tenant_id=tenant_id,
                amount=required_credits,
                reference_type=ReferenceType.EXTRACTION_JOB.value,
                reference_id=job_id,
                description=f"Document extraction - {required_credits} page(s) (job {job_id})",
                created_by_user_id=user_id,
                metadata={
                    "job_id": str(job_id),
                    "document_id": str(document_id),
                    "page_count": required_credits,
                    "model_provider": model_provider,
                    "model_name": model_name,
                },
                allow_negative=False,  # Enforce balance check
            )

            # Log successful credit deduction
            remaining_balance = tenant.cached_balance - required_credits
            logger.info(
                "credit_deduction_success",
                extra={
                    "event": "credit_deduction_success",
                    "tenant_id": str(tenant_id),
                    "user_id": str(user_id),
                    "job_id": str(job_id),
                    "transaction_id": str(credit_transaction.id),
                    "credits_deducted": required_credits,
                    "previous_balance": current_balance,
                    "remaining_balance": remaining_balance,
                    "model_provider": model_provider,
                    "model_name": model_name,
                }
            )

            return credit_transaction, required_credits

        except HTTPException:
            # Re-raise HTTP exceptions (insufficient credits, tenant not found)
            raise
        except InsufficientCreditsError as e:
            # This shouldn't happen (we just checked), but handle it gracefully
            from app.schemas.error import insufficient_credits_error
            raise HTTPException(
                status_code=402,
                detail=insufficient_credits_error(
                    required=e.required,
                    available=e.available
                )
            )
        except Exception as e:
            # Check for lock timeout
            from sqlalchemy.exc import OperationalError
            if isinstance(e, OperationalError) and "lock timeout" in str(e).lower():
                from app.schemas.error import service_busy_error
                raise HTTPException(
                    status_code=503,
                    detail=service_busy_error(retry_after=3)
                )

            # Generic error - log internally but don't leak details
            logger.error(
                f"Credit deduction failed for tenant {tenant_id}",
                exc_info=True,
                extra={
                    "tenant_id": str(tenant_id),
                    "job_id": str(job_id),
                    "page_count": page_count
                }
            )

            raise HTTPException(
                status_code=500,
                detail="Credit deduction failed. Please contact support if this persists."
            )
