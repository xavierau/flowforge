"""Centralized job failure handling with credit refunds.

Implements DRY principle for handling job failures across all task types.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
import logging

from app.models import ExtractionJob
from app.services.credit_service import CreditService

logger = logging.getLogger(__name__)


def handle_job_failure(
    db: Session,
    job: ExtractionJob,
    error: Exception,
    max_retries: int,
    current_retry: int,
    failure_context: str = "Task",
) -> None:
    """Handle job failure: mark as failed and refund credits.

    Centralized failure handling that ensures:
    1. Job status is updated to "failed"
    2. Error message is logged
    3. Credits are refunded if they were deducted
    4. Refund failures are logged but don't crash

    Args:
        db: Database session
        job: ExtractionJob instance
        error: Exception that caused the failure
        max_retries: Maximum number of retries configured
        current_retry: Current retry attempt (0-indexed)
        failure_context: Context string for logging (e.g., "Markdown generation", "JSON extraction")

    Example:
        try:
            # ... task logic ...
        except Exception as e:
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
            else:
                handle_job_failure(
                    db=db,
                    job=job,
                    error=e,
                    max_retries=self.max_retries,
                    current_retry=self.request.retries,
                    failure_context="Markdown generation"
                )
                raise
    """
    # Mark job as failed
    job.status = "failed"
    job.error_message = str(error)[:500]  # Limit to 500 chars
    job.completed_at = datetime.utcnow()
    db.commit()

    logger.error(
        f"{failure_context} failed after {max_retries} retries for job {job.id}: {str(error)}"
    )

    # Refund credits if they were deducted
    if not job.credits_deducted or not job.credits_cost:
        logger.info(f"No credits to refund for job {job.id} (credits_deducted={job.credits_deducted}, credits_cost={job.credits_cost})")
        return

    try:
        credit_service = CreditService(db)
        refund_transaction = credit_service.refund_job_credits(
            job_id=job.id,
            tenant_id=job.document.tenant_id,
            refund_amount=job.credits_cost,
            reason=f"{failure_context} failed after {max_retries} retries: {str(error)[:100]}",
            user_id=None,  # System refund
        )
        db.commit()

        logger.info(
            f"✓ Refunded {job.credits_cost} credits for failed job {job.id} "
            f"(refund transaction {refund_transaction.id})"
        )

    except Exception as refund_error:
        # Log refund failure but don't crash - job is already marked as failed
        logger.error(
            f"BILLING ERROR: Failed to refund {job.credits_cost} credits for failed job {job.id}: {str(refund_error)}. "
            f"MANUAL REFUND REQUIRED."
        )

        # Store refund error in job metadata for manual intervention
        if not job.document_metadata:
            job.document_metadata = {}
        if isinstance(job.document_metadata, dict):
            job.document_metadata["refund_error"] = {
                "error": str(refund_error),
                "credits_to_refund": job.credits_cost,
                "timestamp": datetime.utcnow().isoformat(),
                "failure_context": failure_context,
            }
        db.commit()


def mark_jobs_failed_for_document(
    db: Session,
    document_id: str,
    error: Exception,
    max_retries: int,
    failure_context: str = "Task",
) -> int:
    """Mark all processing jobs for a document as failed and refund credits.

    Used when a prerequisite task fails (e.g., markdown generation fails,
    so all extraction jobs for that document should be marked as failed).

    Args:
        db: Database session
        document_id: Document UUID as string
        error: Exception that caused the failure
        max_retries: Maximum number of retries configured
        failure_context: Context string for logging

    Returns:
        Number of jobs marked as failed

    Example:
        # In markdown_generator.py when all retries exhausted:
        failed_count = mark_jobs_failed_for_document(
            db=db,
            document_id=document_id,
            error=e,
            max_retries=self.max_retries,
            failure_context="Markdown generation"
        )
    """
    from uuid import UUID

    doc_uuid = UUID(document_id)
    jobs = (
        db.query(ExtractionJob)
        .filter(ExtractionJob.document_id == doc_uuid)
        .filter(ExtractionJob.status == "processing")
        .all()
    )

    if not jobs:
        logger.warning(f"No processing jobs found for document {document_id}")
        return 0

    for job in jobs:
        handle_job_failure(
            db=db,
            job=job,
            error=error,
            max_retries=max_retries,
            current_retry=max_retries,  # Already exhausted
            failure_context=failure_context,
        )

    logger.info(
        f"Marked {len(jobs)} extraction job(s) as failed for document {document_id} "
        f"due to {failure_context} failure"
    )

    return len(jobs)
