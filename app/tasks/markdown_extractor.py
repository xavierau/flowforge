"""Markdown extraction tasks for markdown-to-JSON conversion.

Extracts structured JSON data from markdown content using text-only models.
Handles credit refunds on failure.
"""

import asyncio
from datetime import datetime
from uuid import UUID
from celery import Task
import logging

from app.tasks.celery_app import celery_app
from app.tasks.callback import send_extraction_callback
from app.database import SessionLocal
from app.models import ExtractionJob, ExtractionResult, DocumentPage, Document
from app.services.converters import get_converter_factory

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def extract_from_markdown(self: Task, extraction_job_id: str) -> dict:
    """Extract structured JSON from markdown content.

    Uses text-only models (cheaper than vision) to extract JSON from markdown.
    Combines markdown from all pages and extracts into single JSON object.

    Args:
        self: Celery task instance
        extraction_job_id: Extraction job UUID as string

    Returns:
        Dictionary with extraction results:
        {
            "extraction_job_id": str,
            "status": "completed",
            "tokens_used": int
        }

    Raises:
        Exception: On extraction failure (triggers Celery retry)
    """
    db = SessionLocal()

    try:
        # Get job
        job_uuid = UUID(extraction_job_id)
        job = db.query(ExtractionJob).filter(ExtractionJob.id == job_uuid).first()

        if not job:
            raise ValueError(f"Job {extraction_job_id} not found")

        # Update job status to processing
        job.status = "processing"
        job.started_at = datetime.utcnow()
        db.commit()

        # Get document
        document = job.document

        # Get all pages with markdown content
        pages = (
            db.query(DocumentPage)
            .filter(DocumentPage.document_id == document.id)
            .order_by(DocumentPage.page_number)
            .all()
        )

        if not pages:
            raise ValueError(f"No pages found for document {document.id}")

        # Check if all pages have markdown
        pages_with_markdown = [p for p in pages if p.markdown_content]
        if len(pages_with_markdown) < len(pages):
            missing = len(pages) - len(pages_with_markdown)
            raise ValueError(
                f"Missing markdown for {missing} pages. "
                f"Markdown generation may have failed."
            )

        # Combine markdown from all pages
        combined_markdown = "\n\n".join(
            page.markdown_content for page in pages_with_markdown
        )

        logger.info(
            f"Extracting JSON from {len(pages_with_markdown)} pages of markdown "
            f"({len(combined_markdown)} chars)"
        )

        # Get JSON extractor
        # Use same provider as the VLLM model for consistency
        # Map vllm provider to extractor name
        extractor_name = "gemini" if job.model_provider == "google" else "openai"

        factory = get_converter_factory()
        extractor = factory.get_json_extractor(extractor_name)

        # Extract JSON from markdown
        result = asyncio.run(
            extractor.extract(
                markdown_content=combined_markdown,
                schema=job.extraction_schema,
                custom_prompt=job.custom_prompt or "",
            )
        )

        # Store extraction result
        extraction_result = ExtractionResult(
            extraction_job_id=job.id,
            document_page_id=None,  # Markdown mode: result applies to all pages
            extracted_data=result.extracted_data,
            confidence_score=1.0 if result.is_valid else 0.5,
            model_used=f"{result.provider}/{result.model}",
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            tokens_used=result.input_tokens + result.output_tokens,
            processing_time_ms=result.processing_time_ms,
        )

        db.add(extraction_result)

        # --- CALCULATE AND STORE IMMUTABLE COST (BOTH STAGES) ---
        try:
            from app.domain.metrics.pricing_service import PricingService
            from app.domain.metrics.value_objects import TokenUsage
            from decimal import Decimal

            pricing_service = PricingService(db)

            # --- STAGE 1: Markdown Generation Cost (from DocumentPage) ---
            stage1_input_tokens = sum(p.markdown_input_tokens or 0 for p in pages_with_markdown)
            stage1_output_tokens = sum(p.markdown_output_tokens or 0 for p in pages_with_markdown)
            stage1_cost_from_pages = sum(float(p.markdown_cost_usd or 0) for p in pages_with_markdown)
            stage1_model = pages_with_markdown[0].markdown_model_used if pages_with_markdown else "unknown"

            # If per-page costs weren't stored, calculate now
            if stage1_cost_from_pages == 0 and (stage1_input_tokens > 0 or stage1_output_tokens > 0):
                stage1_usage = TokenUsage(input_tokens=stage1_input_tokens, output_tokens=stage1_output_tokens)
                stage1_cost_estimate, stage1_snapshot = pricing_service.calculate_and_snapshot(
                    stage1_usage, stage1_model
                )
                stage1_cost_usd = stage1_cost_estimate.amount
            else:
                stage1_cost_usd = stage1_cost_from_pages
                stage1_snapshot = {
                    "model": stage1_model,
                    "input_tokens": stage1_input_tokens,
                    "output_tokens": stage1_output_tokens,
                    "aggregated_from_pages": True,
                }

            # --- STAGE 2: JSON Extraction Cost (current result) ---
            stage2_input_tokens = result.input_tokens
            stage2_output_tokens = result.output_tokens
            stage2_model = result.model or job.model_name

            stage2_usage = TokenUsage(input_tokens=stage2_input_tokens, output_tokens=stage2_output_tokens)
            stage2_cost_estimate, stage2_snapshot = pricing_service.calculate_and_snapshot(
                stage2_usage, stage2_model
            )
            stage2_cost_usd = stage2_cost_estimate.amount

            # --- TOTAL COST ---
            total_cost_usd = stage1_cost_usd + stage2_cost_usd

            # Store on job with breakdown
            job.estimated_cost_usd = Decimal(str(total_cost_usd))
            job.pricing_snapshot = {
                "pipeline": "markdown",
                "stages": [
                    {
                        "stage": "markdown_generation",
                        "model": stage1_model,
                        "input_tokens": stage1_input_tokens,
                        "output_tokens": stage1_output_tokens,
                        "cost_usd": round(stage1_cost_usd, 6),
                        "pricing": stage1_snapshot,
                    },
                    {
                        "stage": "json_extraction",
                        "model": stage2_model,
                        "input_tokens": stage2_input_tokens,
                        "output_tokens": stage2_output_tokens,
                        "cost_usd": round(stage2_cost_usd, 6),
                        "pricing": stage2_snapshot,
                    }
                ],
                "total_cost_usd": round(total_cost_usd, 6),
                "total_input_tokens": stage1_input_tokens + stage2_input_tokens,
                "total_output_tokens": stage1_output_tokens + stage2_output_tokens,
            }

            logger.info(
                f"Calculated total cost for markdown pipeline job {extraction_job_id}: "
                f"${total_cost_usd:.6f} (Stage1: ${stage1_cost_usd:.6f}, Stage2: ${stage2_cost_usd:.6f})"
            )
        except Exception as e:
            logger.warning(f"Failed to calculate cost for job {extraction_job_id}: {e}")
        # --- END COST CALCULATION ---

        # Update job status
        job.status = "completed"
        job.completed_at = datetime.utcnow()

        # Update document status
        document.status = "completed"

        db.commit()

        logger.info(
            f"Extraction from markdown completed for job {job.id} "
            f"(tokens: {result.input_tokens}+{result.output_tokens}, "
            f"valid: {result.is_valid})"
        )

        # --- CREDIT BILLING NOTE ---
        # Credits are deducted SYNCHRONOUSLY in the API endpoint when job is created.
        # No async deduction needed here for successful jobs.
        # If job fails, credits are refunded in the exception handler below.
        # --- END CREDIT BILLING NOTE ---

        # Queue callback task asynchronously if URL is configured
        if job.callback_url:
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
            "tokens_used": result.input_tokens + result.output_tokens,
        }

    except Exception as e:
        db.rollback()

        # Check if we should retry
        if self.request.retries < self.max_retries:
            # Still have retries left - don't mark as failed yet
            logger.warning(
                f"Markdown extraction job {extraction_job_id} failed "
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
                    failure_context="Markdown extraction",
                )

            raise

    finally:
        db.close()
