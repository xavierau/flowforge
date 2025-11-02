"""Image to JSON extraction tasks."""

import asyncio
import base64
from datetime import datetime
from uuid import UUID
from celery import Task, group

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import ExtractionJob, ExtractionResult, DocumentPage, Document
from app.services.storage import get_storage_service
from app.services.vllm_service import get_vllm_service


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def extract_from_page(
    self: Task,
    extraction_job_id: str,
    document_page_id: str,
) -> dict:
    """
    Extract JSON data from a single document page.

    Args:
        extraction_job_id: Extraction job UUID as string
        document_page_id: Document page UUID as string

    Returns:
        Dictionary with extraction results
    """
    db = SessionLocal()
    storage = get_storage_service()
    vllm_service = get_vllm_service()

    try:
        # Get job and page
        job_uuid = UUID(extraction_job_id)
        page_uuid = UUID(document_page_id)

        job = db.query(ExtractionJob).filter(ExtractionJob.id == job_uuid).first()
        page = db.query(DocumentPage).filter(DocumentPage.id == page_uuid).first()

        if not job:
            raise ValueError(f"Job {extraction_job_id} not found")
        if not page:
            raise ValueError(f"Page {document_page_id} not found")

        # Download image
        image_bytes = storage.download_file_sync(page.image_path)

        # Convert to base64
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        # Extract using VLLM (async operation)
        result = asyncio.run(
            vllm_service.extract_from_image(
                image_base64=image_base64,
                schema=job.extraction_schema,
                custom_prompt=job.custom_prompt or "",
                provider=job.model_provider,
                model=job.model_name,
            )
        )

        # Store result
        extraction_result = ExtractionResult(
            extraction_job_id=job.id,
            document_page_id=page.id,
            extracted_data=result["extracted_data"],
            confidence_score=result["confidence_score"],
            model_used=result["model_used"],
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            tokens_used=result["tokens_used"],
            processing_time_ms=result["processing_time_ms"],
        )

        db.add(extraction_result)

        # Update page status (keeping as completed since extraction is done)
        # page.status remains "completed"
        db.commit()

        return {
            "extraction_job_id": extraction_job_id,
            "document_page_id": document_page_id,
            "status": "success",
            "extracted_data": result["extracted_data"],
        }

    except Exception as e:
        # Retry on failure
        raise self.retry(exc=e)

    finally:
        db.close()


@celery_app.task(bind=True)
def process_extraction_job(self: Task, extraction_job_id: str) -> dict:
    """
    Process an extraction job for all pages of a document.

    Args:
        extraction_job_id: Extraction job UUID as string

    Returns:
        Dictionary with job results
    """
    db = SessionLocal()

    try:
        # Get job
        job_uuid = UUID(extraction_job_id)
        job = db.query(ExtractionJob).filter(ExtractionJob.id == job_uuid).first()

        if not job:
            raise ValueError(f"Job {extraction_job_id} not found")

        # Update job status
        job.status = "processing"
        job.started_at = datetime.utcnow()
        db.commit()

        # Get document
        document = job.document

        # Get pages to process
        if document.mime_type == "application/pdf":
            # Multi-page PDF
            pages = (
                db.query(DocumentPage)
                .filter(DocumentPage.document_id == document.id)
                .filter(DocumentPage.status == "completed")
                .order_by(DocumentPage.page_number)
                .all()
            )

            if not pages:
                raise ValueError(f"No completed pages found for document {document.id}")

            # Process pages sequentially (for solo pool compatibility)
            # In production with prefork/threads pool, this could use group().apply_async()
            results = []
            for page in pages:
                # Queue the extraction task
                extract_from_page.apply_async(
                    args=(extraction_job_id, str(page.id))
                )

            # Since we're using async tasks, the parent job completes immediately
            # The child tasks will update the extraction_results table independently
            results = []  # Empty list since tasks are async

        else:
            # Single image - process directly
            storage_svc = get_storage_service()
            image_bytes = storage_svc.download_file_sync(document.file_path)
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            vllm_service = get_vllm_service()
            result = asyncio.run(
                vllm_service.extract_from_image(
                    image_base64=image_base64,
                    schema=job.extraction_schema,
                    custom_prompt=job.custom_prompt or "",
                    provider=job.model_provider,
                    model=job.model_name,
                )
            )

            # Store result
            extraction_result = ExtractionResult(
                extraction_job_id=job.id,
                document_page_id=None,  # No page for single images
                extracted_data=result["extracted_data"],
                confidence_score=result["confidence_score"],
                model_used=result["model_used"],
                input_tokens=result["input_tokens"],
                output_tokens=result["output_tokens"],
                tokens_used=result["tokens_used"],
                processing_time_ms=result["processing_time_ms"],
            )

            db.add(extraction_result)
            results = [result]

        # Update job status
        job.status = "completed"
        job.completed_at = datetime.utcnow()

        # Update document status
        document.status = "completed"

        db.commit()

        return {
            "extraction_job_id": extraction_job_id,
            "status": "completed",
            "results_count": len(results),
        }

    except Exception as e:
        # Update job status to failed
        if job:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()

        raise

    finally:
        db.close()
