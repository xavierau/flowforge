"""Combined document upload and extraction task."""

from datetime import datetime
from uuid import UUID
from celery import Task, chain
import logging

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import ExtractionJob, Document
from app.tasks.pdf_processor import pdf_to_images
from app.tasks.extractor import process_extraction_job

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document_and_extract(self: Task, extraction_job_id: str) -> dict:
    """
    Combined task that orchestrates document processing and extraction.

    This task coordinates the workflow by delegating to existing tasks:
    1. Load extraction job and get document
    2. If PDF: delegate to pdf_to_images task
    3. Delegate to process_extraction_job task for extraction

    Args:
        extraction_job_id: Extraction job UUID as string

    Returns:
        Dictionary with processing results
    """
    db = SessionLocal()
    job = None
    document = None

    try:
        # Get job
        job_uuid = UUID(extraction_job_id)
        job = db.query(ExtractionJob).filter(ExtractionJob.id == job_uuid).first()

        if not job:
            raise ValueError(f"Job {extraction_job_id} not found")

        # Get document
        document = db.query(Document).filter(Document.id == job.document_id).first()

        if not document:
            raise ValueError(f"Document {job.document_id} not found")

        document_id = str(document.id)
        is_pdf = document.mime_type == "application/pdf"

        logger.info(
            f"Starting combined workflow for job {extraction_job_id}, "
            f"document {document_id}, is_pdf={is_pdf}"
        )

        # Step 1: Process PDF to images if needed
        if is_pdf and document.status == "uploaded":
            logger.info(f"Converting PDF to images for document {document_id}")
            # Call pdf_to_images task synchronously
            pdf_result = pdf_to_images(self, document_id)
            logger.info(
                f"PDF conversion completed: {pdf_result['page_count']} pages"
            )

        # Step 2: Perform extraction using existing task
        logger.info(f"Delegating to process_extraction_job for {extraction_job_id}")
        extraction_result = process_extraction_job(self, extraction_job_id)

        logger.info(f"Combined workflow completed for job {extraction_job_id}")

        return {
            "job_id": extraction_job_id,
            "document_id": document_id,
            "status": extraction_result["status"],
            "results_count": extraction_result.get("results_count", 0),
        }

    except Exception as e:
        logger.error(
            f"Error in combined workflow for job {extraction_job_id}: {str(e)}",
            exc_info=True
        )
        db.rollback()

        # Update statuses to failed if not already handled by subtasks
        if job and job.status not in ["failed", "completed"]:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()

        if document and document.status not in ["failed", "completed"]:
            document.status = "failed"
            db.commit()

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            logger.warning(
                f"Retrying combined workflow for job {extraction_job_id} "
                f"(attempt {self.request.retries + 1}/{self.max_retries})"
            )
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        else:
            logger.error(
                f"All retries exhausted for combined workflow {extraction_job_id}"
            )
            raise

    finally:
        db.close()
