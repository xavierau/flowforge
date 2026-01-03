"""Combined document upload and extraction task."""

from datetime import datetime
from typing import Dict, Optional, Any
from uuid import UUID
from celery import Task, chain
import logging

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import ExtractionJob, Document, SchemaDefinition
from app.tasks.pdf_processor import pdf_to_images
from app.tasks.image_preprocessor import preprocess_document_images
from app.tasks.extractor import process_extraction_job
from app.tasks.markdown_pipeline import process_markdown_extraction_pipeline

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_extraction(
    self: Task,
    document_id: str,
    extraction_schema: Optional[Dict[str, Any]] = None,
    schema_definition_id: Optional[str] = None,
    custom_prompt: Optional[str] = None,
    model_provider: str = "google",
    model_name: str = "gemini-2.5-flash",
    extraction_mode: str = "vllm",
    markdown_converter: Optional[str] = None,
    markdown_format: Optional[str] = None,
    callback_url: Optional[str] = None,
    enable_thinking: bool = False,
    thinking_budget: int = 0,
    source: str = "api",
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    parent_credit_transaction_id: Optional[str] = None,
) -> dict:
    """
    Create extraction job for a document and process it.

    This task is used by split_and_extract to queue extraction for child documents
    after document splitting is complete.

    Args:
        document_id: Document UUID as string
        extraction_schema: JSON schema for extraction (required if no schema_definition_id)
        schema_definition_id: ID of saved schema definition (optional)
        custom_prompt: Custom extraction instructions (optional)
        model_provider: VLLM provider (google, openai, etc.)
        model_name: Model name
        extraction_mode: Extraction mode - 'vllm' or 'markdown'
        markdown_converter: Markdown converter (for markdown mode)
        markdown_format: Markdown format style (for markdown mode)
        callback_url: Webhook URL for completion notification
        enable_thinking: Enable AI thinking mode
        thinking_budget: Token budget for thinking
        source: Job source - 'webui' or 'api'
        tenant_id: Tenant UUID for validation
        user_id: User UUID for credit tracking
        parent_credit_transaction_id: Parent job's credit transaction ID (for child jobs)

    Returns:
        Dictionary with job ID and status
    """
    db = SessionLocal()

    try:
        # Get document with optional tenant validation
        doc_uuid = UUID(document_id)
        query = db.query(Document).filter(Document.id == doc_uuid)

        if tenant_id:
            tenant_uuid = UUID(tenant_id)
            query = query.filter(Document.tenant_id == tenant_uuid)

        document = query.first()

        if not document:
            raise ValueError(f"Document {document_id} not found")

        # Resolve schema
        final_schema = extraction_schema
        final_schema_definition_id = None

        if schema_definition_id:
            schema_uuid = UUID(schema_definition_id)
            schema_def = (
                db.query(SchemaDefinition)
                .filter(SchemaDefinition.id == schema_uuid)
                .filter(SchemaDefinition.tenant_id == document.tenant_id)
                .first()
            )
            if schema_def:
                final_schema = schema_def.definitions
                final_schema_definition_id = schema_def.id

        if not final_schema:
            raise ValueError("Either extraction_schema or valid schema_definition_id is required")

        # Create extraction job for child document
        # Child documents from split always use 'batch' split_mode (already split)
        # Child jobs inherit credit status from parent (credits already deducted for parent)
        job = ExtractionJob(
            document_id=document.id,
            tenant_id=document.tenant_id,
            schema_definition_id=final_schema_definition_id,
            extraction_schema=final_schema,
            custom_prompt=custom_prompt,
            model_provider=model_provider,
            model_name=model_name,
            split_mode="batch",  # Child docs from split always use batch
            extraction_mode=extraction_mode,
            processing_mode="batch" if extraction_mode == "vllm" else "markdown",
            markdown_converter=markdown_converter if extraction_mode == "markdown" else None,
            markdown_format=markdown_format if extraction_mode == "markdown" else None,
            callback_url=callback_url,
            enable_thinking=enable_thinking,
            thinking_budget=thinking_budget if enable_thinking else 0,
            status="queued",
            credits_cost=document.page_count or 1,
            source=source,
            # Child jobs inherit credit status from parent
            credits_deducted=True if parent_credit_transaction_id else False,
            credit_transaction_id=UUID(parent_credit_transaction_id) if parent_credit_transaction_id else None,
        )

        db.add(job)
        db.commit()
        db.refresh(job)

        job_id = str(job.id)

        logger.info(
            f"Created extraction job {job_id} for child document {document_id}, "
            f"extraction_mode={extraction_mode}"
        )

        # Delegate to process_document_and_extract for actual processing
        result = process_document_and_extract(job_id)

        return {
            "extraction_job_id": job_id,
            "document_id": document_id,
            "status": result.get("status", "completed"),
        }

    except Exception as e:
        logger.error(
            f"Error creating extraction job for document {document_id}: {str(e)}",
            exc_info=True
        )
        db.rollback()

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        else:
            raise

    finally:
        db.close()


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
            # Call pdf_to_images task synchronously (don't pass self - Celery injects it)
            pdf_result = pdf_to_images(document_id)
            logger.info(
                f"PDF conversion completed: {pdf_result['page_count']} pages"
            )

        # Step 2: Preprocess images (noise removal, contrast enhancement, grid overlay)
        logger.info(f"Preprocessing images for document {document_id}")
        preprocess_result = preprocess_document_images(document_id)
        logger.info(
            f"Image preprocessing completed: {preprocess_result['pages_processed']} "
            f"pages preprocessed"
        )

        # Step 3: Perform extraction using appropriate task based on extraction_mode
        # Use new extraction_mode field with fallback to processing_mode for backward compatibility
        extraction_mode_value = job.extraction_mode or ""
        processing_mode_value = job.processing_mode or ""

        use_markdown = (
            extraction_mode_value == "markdown"
            or (not extraction_mode_value and processing_mode_value == "markdown")
        )

        if use_markdown:
            logger.info(f"Delegating to markdown pipeline for {extraction_job_id}")
            extraction_result = process_markdown_extraction_pipeline(extraction_job_id)
        else:
            logger.info(f"Delegating to process_extraction_job for {extraction_job_id}")
            extraction_result = process_extraction_job(extraction_job_id)

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
