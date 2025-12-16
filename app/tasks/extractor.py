"""Image to JSON extraction tasks."""

import asyncio
import base64
from datetime import datetime
from uuid import UUID
from celery import Task, chord, group
import logging

from app.tasks.celery_app import celery_app
from app.tasks.callback import send_extraction_callback
from app.database import SessionLocal
from app.models import ExtractionJob, ExtractionResult, DocumentPage, Document
from app.services.storage import get_storage_service
from app.services.vllm_service import get_vllm_service
from app.services.hitl_service import HITLService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=False)
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

        # Download image (prefer preprocessed if available)
        image_path = page.preprocessed_image_path or page.image_path
        image_bytes = storage.download_file_sync(image_path)

        if page.preprocessed_image_path:
            logger.debug(f"Using preprocessed image for page {page.page_number}")
        else:
            logger.debug(f"Using original image for page {page.page_number}")

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
                thinking_budget=job.thinking_budget,
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


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=False)
def finalize_extraction_job(
    self: Task,
    page_results: list,
    extraction_job_id: str,
) -> dict:
    """
    Finalize an extraction job after all per-page extractions complete.

    This is the chord callback that runs after all extract_from_page tasks finish.
    It aggregates results, updates job status, triggers HITL if needed, and sends callback.

    Args:
        page_results: List of results from each extract_from_page task
        extraction_job_id: Extraction job UUID as string

    Returns:
        Dictionary with finalization status
    """
    db = SessionLocal()

    try:
        job_uuid = UUID(extraction_job_id)
        job = db.query(ExtractionJob).filter(ExtractionJob.id == job_uuid).first()

        if not job:
            raise ValueError(f"Job {extraction_job_id} not found")

        document = job.document

        # Query all extraction results for this job
        extraction_results = (
            db.query(ExtractionResult)
            .filter(ExtractionResult.extraction_job_id == job.id)
            .all()
        )

        # Calculate average confidence score
        if extraction_results:
            avg_confidence = sum(
                r.confidence_score or 1.0 for r in extraction_results
            ) / len(extraction_results)
        else:
            avg_confidence = 1.0

        # Count successful pages from task results
        successful_pages = sum(
            1 for r in page_results
            if r and r.get("status") == "success"
        )
        failed_pages = len(page_results) - successful_pages

        logger.info(
            f"Finalizing job {extraction_job_id}: "
            f"{successful_pages} successful, {failed_pages} failed pages"
        )

        # --- CALCULATE AND STORE IMMUTABLE COST ---
        try:
            from app.domain.metrics.pricing_service import PricingService
            from app.domain.metrics.value_objects import TokenUsage

            total_input = sum(r.input_tokens or 0 for r in extraction_results)
            total_output = sum(r.output_tokens or 0 for r in extraction_results)
            model_used = extraction_results[0].model_used if extraction_results else job.model_name

            pricing_service = PricingService(db)
            token_usage = TokenUsage(input_tokens=total_input, output_tokens=total_output)
            cost_estimate, pricing_snapshot = pricing_service.calculate_and_snapshot(token_usage, model_used)

            job.estimated_cost_usd = cost_estimate.amount
            job.pricing_snapshot = pricing_snapshot

            logger.info(
                f"Calculated cost for job {extraction_job_id}: ${cost_estimate.amount:.6f} "
                f"(input: {total_input}, output: {total_output}, model: {model_used})"
            )
        except Exception as e:
            logger.warning(f"Failed to calculate cost for job {extraction_job_id}: {e}")
        # --- END COST CALCULATION ---

        # Update job status
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.confidence_score = avg_confidence

        # Update document status
        document.status = "completed"

        db.commit()

        # --- HITL AUTO-ROUTING ---
        try:
            hitl_service = HITLService(db)
            needs_review = hitl_service.should_request_review(
                extraction_job=job,
                workflow_config=None
            )

            if needs_review:
                review_request = hitl_service.create_review_request(
                    extraction_job_id=job.id,
                    trigger_reason=f"auto_low_confidence:{avg_confidence:.3f}"
                )
                logger.info(
                    f"Created HITL review request {review_request.id} for job {job.id} "
                    f"(confidence: {avg_confidence:.3f}, priority: {review_request.priority})"
                )
        except ValueError as e:
            logger.warning(
                f"Could not create HITL review request for job {job.id}: {str(e)}"
            )
        except Exception as e:
            logger.error(
                f"Failed to create HITL review request for job {job.id}: {str(e)}",
                exc_info=True
            )
        # --- END HITL AUTO-ROUTING ---

        # --- SEND CALLBACK ---
        if job.callback_url:
            # Aggregate extracted data from all pages
            all_extracted_data = [
                {
                    "page_number": r.document_page.page_number if r.document_page else None,
                    "extracted_data": r.extracted_data,
                    "confidence_score": r.confidence_score,
                }
                for r in extraction_results
            ]

            callback_data = {
                "job_id": str(job.id),
                "document_id": str(document.id),
                "status": "completed",
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "pages_count": len(extraction_results),
                "results": all_extracted_data,
            }
            # Fire and forget
            send_extraction_callback.delay(job.callback_url, callback_data)
            logger.info(f"Queued callback task for job {job.id} to {job.callback_url}")
        # --- END SEND CALLBACK ---

        return {
            "extraction_job_id": extraction_job_id,
            "status": "completed",
            "pages_processed": len(extraction_results),
            "avg_confidence": avg_confidence,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to finalize extraction job {extraction_job_id}: {str(e)}")

        # Mark job as failed if finalization fails
        try:
            job = db.query(ExtractionJob).filter(
                ExtractionJob.id == UUID(extraction_job_id)
            ).first()
            if job:
                job.status = "failed"
                job.error_message = f"Finalization failed: {str(e)}"
                job.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass

        raise self.retry(exc=e)

    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def on_chord_error(self: Task, request, exc, traceback, extraction_job_id: str):
    """
    Handle chord errors when any page extraction fails.

    This task is called when any task in the chord group fails.
    """
    db = SessionLocal()

    try:
        job_uuid = UUID(extraction_job_id)
        job = db.query(ExtractionJob).filter(ExtractionJob.id == job_uuid).first()

        if job:
            logger.error(
                f"Chord failed for job {extraction_job_id}: {exc}"
            )

            # Check if we have any successful results
            successful_results = (
                db.query(ExtractionResult)
                .filter(ExtractionResult.extraction_job_id == job.id)
                .count()
            )

            if successful_results > 0:
                # Partial success - mark as completed with note
                job.status = "completed"
                job.error_message = f"Partial completion: {successful_results} pages extracted, some failed"
            else:
                # Complete failure
                job.status = "failed"
                job.error_message = f"All page extractions failed: {str(exc)}"

            job.completed_at = datetime.utcnow()
            db.commit()

    except Exception as e:
        logger.error(f"Failed to handle chord error for job {extraction_job_id}: {str(e)}")
        db.rollback()
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_extraction_job(self: Task, extraction_job_id: str) -> dict:
    """
    Process an extraction job for all pages of a document.

    Retries up to 3 times with exponential backoff if processing fails.
    Retry delays: 60s, 120s, 240s (4 minutes max)

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

            # Check processing mode
            if job.processing_mode == "batch":
                # BATCH MODE: Process all pages in one API call
                storage_svc = get_storage_service()
                vllm_service = get_vllm_service()

                # Load all page images (prefer preprocessed if available)
                images_base64 = []
                for page in pages:
                    image_path = page.preprocessed_image_path or page.image_path
                    image_bytes = storage_svc.download_file_sync(image_path)
                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                    images_base64.append(image_base64)

                    if page.preprocessed_image_path:
                        logger.debug(f"Using preprocessed image for page {page.page_number}")
                    else:
                        logger.debug(f"Using original image for page {page.page_number}")

                # Single API call with all images
                result = asyncio.run(
                    vllm_service.extract_from_images_batch(
                        images_base64=images_base64,
                        schema=job.extraction_schema,
                        custom_prompt=job.custom_prompt or "",
                        provider=job.model_provider,
                        model=job.model_name,
                        thinking_budget=job.thinking_budget,
                    )
                )

                # Store result (linked to the job, not to individual pages)
                extraction_result = ExtractionResult(
                    extraction_job_id=job.id,
                    document_page_id=None,  # Batch result applies to all pages
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

            else:
                # PER-PAGE MODE: Process each page separately using Celery chord
                # This ensures all pages are processed before finalization

                logger.info(
                    f"Starting per_page extraction for job {extraction_job_id} "
                    f"with {len(pages)} pages using chord pattern"
                )

                # Create a group of page extraction tasks
                page_tasks = group(
                    extract_from_page.s(extraction_job_id, str(page.id))
                    for page in pages
                )

                # Create the chord: group tasks + finalize callback
                # The callback receives results from all page tasks
                extraction_chord = chord(
                    page_tasks,
                    finalize_extraction_job.s(extraction_job_id).on_error(
                        on_chord_error.s(extraction_job_id=extraction_job_id)
                    )
                )

                # Dispatch the chord - this returns immediately
                # IMPORTANT: We do NOT call .get() here to avoid deadlock
                extraction_chord.apply_async()

                logger.info(
                    f"Dispatched chord for job {extraction_job_id} with {len(pages)} pages"
                )

                # Return early - the finalize task will handle completion
                # Close db session before returning
                db.close()

                return {
                    "extraction_job_id": extraction_job_id,
                    "status": "processing",
                    "mode": "per_page",
                    "pages_queued": len(pages),
                    "message": "Chord dispatched - finalize_extraction_job will complete the job"
                }

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
                    thinking_budget=job.thinking_budget,
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

        # Get overall confidence score from results
        if results:
            avg_confidence = sum(r.get("confidence_score", 1.0) for r in results) / len(results)
        else:
            avg_confidence = 1.0

        # --- CALCULATE AND STORE IMMUTABLE COST ---
        try:
            from app.domain.metrics.pricing_service import PricingService
            from app.domain.metrics.value_objects import TokenUsage

            total_input = sum(r.get("input_tokens", 0) for r in results)
            total_output = sum(r.get("output_tokens", 0) for r in results)
            model_used = results[0].get("model_used", job.model_name) if results else job.model_name

            pricing_service = PricingService(db)
            token_usage = TokenUsage(input_tokens=total_input, output_tokens=total_output)
            cost_estimate, pricing_snapshot = pricing_service.calculate_and_snapshot(token_usage, model_used)

            job.estimated_cost_usd = cost_estimate.amount
            job.pricing_snapshot = pricing_snapshot

            logger.info(
                f"Calculated cost for job {extraction_job_id}: ${cost_estimate.amount:.6f} "
                f"(input: {total_input}, output: {total_output}, model: {model_used})"
            )
        except Exception as e:
            logger.warning(f"Failed to calculate cost for job {extraction_job_id}: {e}")
        # --- END COST CALCULATION ---

        # Update job status with confidence score
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.confidence_score = avg_confidence

        # Update document status
        document.status = "completed"

        db.commit()

        # --- HITL AUTO-ROUTING ---
        # Check if human review is needed based on confidence threshold
        try:
            hitl_service = HITLService(db)
            needs_review = hitl_service.should_request_review(
                extraction_job=job,
                workflow_config=None  # No workflow-specific config in standard extraction
            )

            if needs_review:
                # Create review request (priority is calculated internally)
                review_request = hitl_service.create_review_request(
                    extraction_job_id=job.id,
                    trigger_reason=f"auto_low_confidence:{avg_confidence:.3f}"
                )
                logger.info(
                    f"Created HITL review request {review_request.id} for job {job.id} "
                    f"(confidence: {avg_confidence:.3f}, priority: {review_request.priority})"
                )
        except ValueError as e:
            # Review might already exist (re-processing) - log and continue
            logger.warning(
                f"Could not create HITL review request for job {job.id}: {str(e)}"
            )
        except Exception as e:
            # Log but don't fail the extraction if HITL routing fails
            logger.error(
                f"Failed to create HITL review request for job {job.id}: {str(e)}",
                exc_info=True
            )
        # --- END HITL AUTO-ROUTING ---

        # --- CREDIT BILLING NOTE ---
        # Credits are now deducted SYNCHRONOUSLY in the API endpoint (app/api/documents.py)
        # when the job is created. This eliminates the TOCTOU race condition.
        # No async deduction needed here for successful jobs.
        # If the job fails, credits are refunded in the exception handler below.
        # --- END CREDIT BILLING NOTE ---

        # Get the extraction result for callback
        extraction_result = (
            db.query(ExtractionResult)
            .filter(ExtractionResult.extraction_job_id == job.id)
            .first()
        )

        # Queue callback task asynchronously if URL is configured
        if job.callback_url and extraction_result:
            callback_data = {
                "extracted_data": extraction_result.extracted_data,
                "job_id": str(job.id),
                "document_id": str(document.id),
                "status": "completed",
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            }
            # Fire and forget - doesn't block extraction completion
            send_extraction_callback.delay(job.callback_url, callback_data)
            logger.info(f"Queued callback task for job {job.id} to {job.callback_url}")

        return {
            "extraction_job_id": extraction_job_id,
            "status": "completed",
            "results_count": len(results),
        }

    except Exception as e:
        db.rollback()

        # Check if we should retry
        if self.request.retries < self.max_retries:
            # Still have retries left - don't mark as failed yet
            logger.warning(
                f"Extraction job {extraction_job_id} failed "
                f"(attempt {self.request.retries + 1}/{self.max_retries}): {str(e)}"
            )
            db.close()
            # Retry with exponential backoff: 60s, 120s, 240s
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        else:
            # All retries exhausted - mark job as failed and refund credits
            if job:
                from app.utils.job_failure_handler import handle_job_failure

                handle_job_failure(
                    db=db,
                    job=job,
                    error=e,
                    max_retries=self.max_retries,
                    current_retry=self.request.retries,
                    failure_context="JSON extraction",
                )

            raise

    finally:
        db.close()
