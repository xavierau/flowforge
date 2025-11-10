"""Credit management service for event-sourced credit tracking."""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.credit_transaction import CreditTransaction
from app.models.tenant import Tenant
from app.models.extraction_job import ExtractionJob
from app.exceptions.credits import InsufficientCreditsError, CreditOperationError
from sqlalchemy import update


class CreditService:
    """
    Service for managing tenant credit operations.

    Implements event sourcing pattern: balance is calculated on-demand
    by summing transaction log. All operations create immutable transaction records.

    SOLID Compliance:
    - Single Responsibility: Credit operations only
    - Open/Closed: Extensible via transaction types
    - Dependency Inversion: Depends on Session abstraction, not concrete DB
    """

    def __init__(self, db: Session):
        """
        Initialize credit service.

        Args:
            db: Database session for queries (injected dependency)
        """
        self.db = db

    def calculate_balance(self, tenant_id: UUID, use_cache: bool = True) -> int:
        """
        Calculate current credit balance.

        FIX: Now uses cached_balance from tenant table for O(1) lookup.
        Falls back to event sourcing calculation if cache is missing/stale.

        Args:
            tenant_id: Tenant UUID
            use_cache: If True, use cached_balance; if False, recalculate from transactions

        Returns:
            Current credit balance (non-negative integer)

        Time Complexity: O(1) with cache, O(n) without cache
        Query Performance: <1ms with cache, <10ms without for <10k transactions
        """
        if use_cache:
            # O(1) lookup from cached column
            tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if tenant and tenant.cached_balance is not None:
                return max(0, tenant.cached_balance)

        # Fallback: Calculate from transaction log (event sourcing)
        result = (
            self.db.query(func.sum(CreditTransaction.amount))
            .filter(CreditTransaction.tenant_id == tenant_id)
            .scalar()
        )

        # Return 0 if no transactions exist
        balance = result if result is not None else 0

        # Balance should never go negative (enforced by check_sufficient_credits)
        # but defensively return 0 if it does
        return max(0, balance)

    def check_sufficient_credits(
        self,
        tenant_id: UUID,
        required_credits: int
    ) -> Tuple[bool, int]:
        """
        Check if tenant has sufficient credits for an operation.

        Args:
            tenant_id: Tenant UUID
            required_credits: Number of credits needed

        Returns:
            Tuple of (has_sufficient_credits, current_balance)

        Raises:
            ValueError: If required_credits is negative
        """
        if required_credits < 0:
            raise ValueError("Required credits must be non-negative")

        current_balance = self.calculate_balance(tenant_id)
        has_sufficient = current_balance >= required_credits

        return has_sufficient, current_balance

    def deduct_credits(
        self,
        tenant_id: UUID,
        amount: int,
        reference_type: str,
        reference_id: UUID,
        description: str,
        created_by_user_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
        allow_negative: bool = False
    ) -> CreditTransaction:
        """
        Deduct credits from tenant balance (create negative transaction).

        FIX: Added balance enforcement to prevent negative balances.
        This method now checks balance BEFORE deducting unless allow_negative=True.

        Args:
            tenant_id: Tenant UUID
            amount: Number of credits to deduct (positive integer)
            reference_type: Type of entity (e.g., 'extraction_job')
            reference_id: UUID of related entity
            description: Human-readable description
            created_by_user_id: User who initiated (None for system operations)
            metadata: Additional metadata dict
            allow_negative: If False (default), raises error if balance insufficient

        Returns:
            Created CreditTransaction record

        Raises:
            ValueError: If amount is not positive
            InsufficientCreditsError: If balance insufficient and allow_negative=False
            CreditOperationError: If transaction creation fails
        """
        if amount <= 0:
            raise ValueError("Deduction amount must be positive")

        try:
            # FIXED: Use SELECT FOR UPDATE to lock tenant row and prevent race conditions
            # This prevents double-spending attacks where multiple requests
            # check balance simultaneously before deduction
            tenant = (
                self.db.query(Tenant)
                .filter(Tenant.id == tenant_id)
                .with_for_update()  # Pessimistic lock - blocks other transactions
                .first()
            )

            if not tenant:
                raise ValueError(f"Tenant {tenant_id} not found")

            # Check balance AFTER acquiring lock (unless explicitly allowed)
            if not allow_negative:
                current_balance = tenant.cached_balance
                if current_balance < amount:
                    raise InsufficientCreditsError(
                        required=amount,
                        available=current_balance
                    )

            # Create deduction transaction
            transaction = CreditTransaction(
                tenant_id=tenant_id,
                transaction_type="deduction",
                amount=-amount,  # Store as negative
                reference_type=reference_type,
                reference_id=reference_id,
                description=description,
                created_by_user_id=created_by_user_id,
                transaction_metadata=metadata or {},
            )

            self.db.add(transaction)

            # Update cached balance atomically in same transaction
            tenant.cached_balance = max(0, tenant.cached_balance - amount)
            tenant.balance_last_updated = datetime.utcnow()

            self.db.flush()

            return transaction

        except InsufficientCreditsError:
            # Re-raise insufficient credits error
            raise
        except Exception as e:
            self.db.rollback()
            raise CreditOperationError(f"Failed to deduct credits: {str(e)}")

    def add_credits(
        self,
        tenant_id: UUID,
        amount: int,
        transaction_type: str,
        description: str,
        created_by_user_id: Optional[UUID] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[UUID] = None,
        stripe_payment_intent_id: Optional[str] = None,
        stripe_charge_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CreditTransaction:
        """
        Add credits to tenant balance (create positive transaction).

        Args:
            tenant_id: Tenant UUID
            amount: Number of credits to add (positive integer)
            transaction_type: Type (topup, refund, admin_adjustment, trial_signup)
            description: Human-readable description
            created_by_user_id: User who created (required for admin_adjustment)
            reference_type: Optional reference type (auto-determined if not provided)
            reference_id: Optional reference ID (can be None)
            stripe_payment_intent_id: Stripe payment intent ID (for topup)
            stripe_charge_id: Stripe charge ID (for topup)
            metadata: Additional metadata

        Returns:
            Created CreditTransaction record

        Raises:
            ValueError: If amount is not positive or invalid transaction_type
            CreditOperationError: If transaction creation fails
        """
        if amount <= 0:
            raise ValueError("Credit amount must be positive")

        # FIXED: Added "trial_signup" and "deduction" to valid types
        valid_types = [
            "topup",                    # Manual credit purchase
            "deduction",                # Credit consumption (jobs)
            "refund",                   # Refund for failed jobs
            "admin_adjustment",         # Manual admin addition/subtraction
            "trial_signup",             # Trial credits on registration
            "migration_balance_import"  # Data migration
        ]
        if transaction_type not in valid_types:
            raise ValueError(f"Invalid transaction type. Must be one of: {valid_types}")

        # Determine reference_type based on transaction
        if reference_type is None:
            if stripe_payment_intent_id:
                reference_type = "payment"
            elif transaction_type == "trial_signup":
                reference_type = reference_type or "tenant_registration"
            elif transaction_type == "admin_adjustment":
                reference_type = "admin_manual_adjustment"
            else:
                reference_type = "manual"

        try:
            # Create credit transaction
            transaction = CreditTransaction(
                tenant_id=tenant_id,
                transaction_type=transaction_type,
                amount=amount,  # Store as positive
                reference_type=reference_type,
                reference_id=reference_id,
                description=description,
                created_by_user_id=created_by_user_id,
                stripe_payment_intent_id=stripe_payment_intent_id,
                stripe_charge_id=stripe_charge_id,
                transaction_metadata=metadata or {},
            )

            self.db.add(transaction)
            self.db.flush()

            # FIX: Atomically update cached_balance using SQL-level arithmetic
            # This prevents READ-MODIFY-WRITE race conditions
            self.db.execute(
                update(Tenant)
                .where(Tenant.id == tenant_id)
                .values(
                    cached_balance=Tenant.cached_balance + amount,
                    balance_last_updated=datetime.utcnow()
                )
            )
            self.db.flush()

            return transaction

        except Exception as e:
            self.db.rollback()
            raise CreditOperationError(f"Failed to add credits: {str(e)}")

    def recalculate_cached_balance(self, tenant_id: UUID) -> int:
        """
        Recalculate cached_balance from transaction log and update tenant record.

        Use this method for consistency checks or cache repairs.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Recalculated balance

        Raises:
            CreditOperationError: If tenant not found or update fails
        """
        try:
            # Calculate balance from transaction log
            actual_balance = self.calculate_balance(tenant_id, use_cache=False)

            # Update tenant's cached_balance
            tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if not tenant:
                raise CreditOperationError(f"Tenant {tenant_id} not found")

            tenant.cached_balance = actual_balance
            tenant.balance_last_updated = datetime.utcnow()
            self.db.flush()

            return actual_balance

        except Exception as e:
            self.db.rollback()
            raise CreditOperationError(f"Failed to recalculate balance: {str(e)}")

    def get_transaction_history(
        self,
        tenant_id: UUID,
        limit: int = 50,
        offset: int = 0,
        transaction_type: Optional[str] = None
    ) -> Tuple[List[CreditTransaction], int]:
        """
        Get paginated transaction history for tenant.

        Args:
            tenant_id: Tenant UUID
            limit: Number of records to return
            offset: Pagination offset
            transaction_type: Optional filter by type

        Returns:
            Tuple of (transactions_list, total_count)
        """
        query = (
            self.db.query(CreditTransaction)
            .filter(CreditTransaction.tenant_id == tenant_id)
        )

        if transaction_type:
            query = query.filter(CreditTransaction.transaction_type == transaction_type)

        total = query.count()

        transactions = (
            query.order_by(desc(CreditTransaction.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

        return transactions, total

    def reserve_credits_for_job(
        self,
        tenant_id: UUID,
        job_id: UUID,
        required_credits: int,
        user_id: Optional[UUID] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Atomically check and reserve credits for an extraction job.

        Uses database-level pessimistic locking (SELECT FOR UPDATE) to prevent
        race conditions when multiple jobs are submitted concurrently.

        Args:
            tenant_id: Tenant UUID
            job_id: Extraction job UUID
            required_credits: Number of credits needed (page count)
            user_id: User initiating the job

        Returns:
            Tuple of (success: bool, error_message: Optional[str])

        Note: This does NOT deduct credits. Deduction happens on job completion.
        This method only validates balance and creates a pending marker.
        """
        try:
            # Lock tenant row to prevent concurrent modifications
            tenant = (
                self.db.query(Tenant)
                .filter(Tenant.id == tenant_id)
                .with_for_update()  # Pessimistic lock
                .first()
            )

            if not tenant:
                return False, "Tenant not found"

            # Check balance
            has_sufficient, current_balance = self.check_sufficient_credits(
                tenant_id, required_credits
            )

            if not has_sufficient:
                return False, (
                    f"Insufficient credits. Required: {required_credits}, "
                    f"Available: {current_balance}"
                )

            # Update job with cost estimate
            job = self.db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
            if job:
                job.credits_cost = required_credits
                self.db.flush()

            return True, None

        except Exception as e:
            return False, f"Credit reservation failed: {str(e)}"

    def finalize_job_credits(
        self,
        job_id: UUID,
        tenant_id: UUID,
        actual_credits_used: int,
        user_id: Optional[UUID] = None
    ) -> Optional[CreditTransaction]:
        """
        Deduct credits for a completed extraction job (idempotent).

        This is called from the Celery task AFTER job completion.
        Uses idempotency flag to prevent duplicate deductions.

        Args:
            job_id: Extraction job UUID
            tenant_id: Tenant UUID
            actual_credits_used: Actual number of credits consumed
            user_id: User who created the job (optional)

        Returns:
            CreditTransaction if deduction occurred, None if already deducted

        Raises:
            CreditOperationError: If job not found or deduction fails
        """
        # Get job with lock to prevent duplicate deductions
        job = (
            self.db.query(ExtractionJob)
            .filter(ExtractionJob.id == job_id)
            .with_for_update()
            .first()
        )

        if not job:
            raise CreditOperationError(f"Job {job_id} not found")

        # Idempotency check
        if job.credits_deducted:
            # Already deducted, skip
            return None

        # Create deduction transaction
        transaction = self.deduct_credits(
            tenant_id=tenant_id,
            amount=actual_credits_used,
            reference_type="extraction_job",
            reference_id=job_id,
            description=f"Document extraction - {actual_credits_used} page(s)",
            created_by_user_id=user_id,
            metadata={
                "job_id": str(job_id),
                "document_id": str(job.document_id),
                "page_count": actual_credits_used,
                "model_provider": job.model_provider,
                "model_name": job.model_name,
            }
        )

        # Mark job as deducted
        job.credits_deducted = True
        job.credit_transaction_id = transaction.id
        self.db.flush()

        return transaction

    def refund_job_credits(
        self,
        job_id: UUID,
        tenant_id: UUID,
        refund_amount: int,
        reason: str,
        user_id: Optional[UUID] = None
    ) -> CreditTransaction:
        """
        Refund credits for a failed or cancelled extraction job.

        This creates a compensating transaction (credit addition) to reverse
        the deduction that occurred when the job was created.

        Args:
            job_id: Extraction job UUID
            tenant_id: Tenant UUID
            refund_amount: Number of credits to refund
            reason: Reason for refund (e.g., "Job failed", "Job cancelled")
            user_id: User who initiated refund (optional)

        Returns:
            Created refund transaction

        Raises:
            ValueError: If refund_amount is not positive
            CreditOperationError: If transaction creation fails
        """
        if refund_amount <= 0:
            raise ValueError("Refund amount must be positive")

        try:
            # Get job for metadata
            job = self.db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()

            # Create refund transaction (positive amount)
            transaction = self.add_credits(
                tenant_id=tenant_id,
                amount=refund_amount,
                transaction_type="refund",
                description=f"Refund for failed job {job_id}: {reason}",
                created_by_user_id=user_id,
                metadata={
                    "job_id": str(job_id),
                    "refund_reason": reason,
                    "original_deduction_id": str(job.credit_transaction_id) if job and job.credit_transaction_id else None,
                    "document_id": str(job.document_id) if job else None,
                    "page_count": refund_amount,
                }
            )

            return transaction

        except Exception as e:
            self.db.rollback()
            raise CreditOperationError(f"Failed to refund credits: {str(e)}")
