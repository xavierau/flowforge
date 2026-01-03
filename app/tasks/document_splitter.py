"""Document splitting Celery tasks.

This module contains tasks for:
1. analyze_document_boundaries - Analyze pages for document boundaries and rotation
2. split_and_create_documents - Split PDF and create child document records
3. process_split_job - Entry point that chains the above tasks

Security Note:
All tasks accept tenant_id as a parameter for defense-in-depth validation.
Even though the API layer enforces tenant isolation, tasks also verify
tenant_id matches to prevent cross-tenant data access if a split_job_id
is somehow obtained by an unauthorized party.
"""

import logging
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from celery import Task, chain
from pdf2image import convert_from_bytes

from app.config import settings
from app.database import SessionLocal
from app.models import Document, DocumentPage
from app.models.document_split import SplitJob, SplitResult
from app.models.enums import SplitJobStatus, DocumentStatus
from app.services.document_analyzer_service import DocumentAnalyzerService
from app.services.storage import get_storage_service
from app.tasks.celery_app import celery_app
from app.utils.pdf_utils import split_pdf_by_indices

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def analyze_document_boundaries(
    self: Task,
    split_job_id: str,
    tenant_id: Optional[str] = None,
) -> Dict:
    """
    Analyze all pages of a document for boundaries and rotation.

    This task:
    1. Downloads the source PDF
    2. Converts pages to images
    3. Uses Tesseract for rotation detection
    4. Uses DSPy for boundary detection
    5. Stores SplitResult records for each page

    Args:
        split_job_id: SplitJob UUID as string
        tenant_id: Tenant UUID for defense-in-depth validation (optional for backward compat)

    Returns:
        Dict with analysis results including starting_indices and rotation_map
    """
    logger.info(f"Starting boundary analysis for split job: {split_job_id}")

    db = SessionLocal()
    storage = get_storage_service()
    split_job: Optional[SplitJob] = None

    try:
        # Get split job with optional tenant validation
        job_uuid = UUID(split_job_id)
        query = db.query(SplitJob).filter(SplitJob.id == job_uuid)

        # Defense in depth: validate tenant_id if provided
        if tenant_id:
            tenant_uuid = UUID(tenant_id)
            query = query.filter(SplitJob.tenant_id == tenant_uuid)

        split_job = query.first()

        if not split_job:
            if tenant_id:
                # Could be tenant mismatch - log security event
                logger.warning(
                    f"Split job {split_job_id} not found or tenant mismatch "
                    f"(requested tenant: {tenant_id})"
                )
            raise ValueError(f"SplitJob {split_job_id} not found")

        # Get source document with pages
        source_doc = split_job.source_document
        if not source_doc:
            raise ValueError(f"Source document not found for split job {split_job_id}")

        # Update status
        split_job.status = SplitJobStatus.ANALYZING.value
        split_job.started_at = datetime.utcnow()
        db.commit()

        logger.info(f"Analyzing document: {source_doc.filename}")

        # Download PDF from storage
        pdf_bytes = storage.download_file_sync(source_doc.file_path)
        logger.info(f"Downloaded PDF: {len(pdf_bytes)} bytes")

        # Convert PDF to images
        dpi = settings.split_default_dpi
        images = convert_from_bytes(pdf_bytes, dpi=dpi, fmt="png")
        logger.info(f"Converted PDF to {len(images)} images at {dpi} DPI")

        # Get document pages (for linking SplitResult to DocumentPage)
        pages = (
            db.query(DocumentPage)
            .filter(DocumentPage.document_id == source_doc.id)
            .order_by(DocumentPage.page_number)
            .all()
        )

        # Build page_number -> page_id mapping
        page_id_map = {p.page_number: p.id for p in pages}

        # Initialize analyzer service
        analyzer = DocumentAnalyzerService(
            model=split_job.dspy_model or settings.default_qwen_vision_model,
        )

        # Analyze all pages
        analysis_results = analyzer.analyze_all_pages(images)

        # Store SplitResult for each page
        total_input_tokens = 0
        total_output_tokens = 0
        pages_rotated = 0

        for result in analysis_results:
            page_id = page_id_map.get(result.page_number)
            if not page_id:
                logger.warning(f"No DocumentPage found for page {result.page_number}")
                continue

            split_result = SplitResult(
                split_job_id=split_job.id,
                document_page_id=page_id,
                page_number=result.page_number,
                # Boundary detection (reasoning first!)
                boundary_reason=result.boundary_reason,
                detected_document_type=result.detected_document_type,
                is_starting_page=result.is_starting_page,
                boundary_confidence=result.boundary_confidence,
                # Rotation detection
                rotation_needed=result.rotation_needed,
                rotation_confidence=result.rotation_confidence,
                rotation_method=result.rotation_method,
                # Token tracking
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
            db.add(split_result)

            total_input_tokens += result.input_tokens
            total_output_tokens += result.output_tokens
            if result.rotation_needed != 0:
                pages_rotated += 1

        # Update split job statistics
        split_job.pages_analyzed = len(analysis_results)
        split_job.pages_rotated = pages_rotated
        split_job.total_input_tokens = total_input_tokens
        split_job.total_output_tokens = total_output_tokens

        # Calculate cost using PricingService
        if total_input_tokens > 0 or total_output_tokens > 0:
            try:
                from app.domain.metrics.pricing_service import PricingService
                from app.domain.metrics.value_objects import TokenUsage

                token_usage = TokenUsage(
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                )
                model_used = split_job.dspy_model or settings.default_qwen_vision_model

                pricing_service = PricingService(db)
                cost_estimate, pricing_snapshot = pricing_service.calculate_and_snapshot(
                    token_usage, model_used
                )

                split_job.estimated_cost = cost_estimate.amount
                split_job.pricing_snapshot = pricing_snapshot

                logger.info(
                    f"Split job {split_job_id} cost calculated: ${cost_estimate.amount:.6f} "
                    f"({total_input_tokens} input + {total_output_tokens} output tokens)"
                )
            except Exception as e:
                # Don't fail the job if cost calculation fails
                logger.warning(f"Failed to calculate cost for split job {split_job_id}: {e}")

        db.commit()

        # Calculate starting indices and rotation map
        starting_indices = analyzer.get_starting_indices(analysis_results)
        rotation_map = analyzer.get_rotation_map(analysis_results)

        result = {
            "split_job_id": split_job_id,
            "tenant_id": str(split_job.tenant_id),  # Pass tenant_id to next task
            "pages_analyzed": len(analysis_results),
            "documents_found": len(starting_indices),
            "starting_indices": starting_indices,
            "rotation_map": rotation_map,
            "pages_rotated": pages_rotated,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "status": "success",
        }

        logger.info(
            f"Boundary analysis completed for split job {split_job_id}: "
            f"found {len(starting_indices)} documents in {len(analysis_results)} pages"
        )

        return result

    except Exception as e:
        logger.error(f"Error in boundary analysis for split job {split_job_id}: {e}", exc_info=True)

        if split_job:
            split_job.status = SplitJobStatus.FAILED.value
            split_job.error_message = _sanitize_task_error(str(e))
            split_job.completed_at = datetime.utcnow()
            db.commit()

        raise self.retry(exc=e)

    finally:
        db.close()


def _sanitize_task_error(error_message: str) -> str:
    """Sanitize error messages before storing in database.

    This prevents sensitive information (file paths, API keys, stack traces)
    from being persisted in the database.
    """
    if not error_message:
        return "Unknown error"

    error_lower = error_message.lower()

    if "not found" in error_lower:
        return "Resource not found"
    if "permission" in error_lower or "unauthorized" in error_lower:
        return "Permission denied"
    if "timeout" in error_lower:
        return "Operation timed out"
    if "connection" in error_lower or "network" in error_lower:
        return "Service temporarily unavailable"
    if "api key" in error_lower or "api_key" in error_lower:
        return "External service configuration error"
    if "rate limit" in error_lower:
        return "Rate limit exceeded"
    if "invalid" in error_lower and "model" in error_lower:
        return "Invalid model configuration"

    return "An error occurred during processing"


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def split_and_create_documents(self: Task, analysis_result: Dict) -> Dict:
    """
    Split PDF into child documents based on analysis results.

    This task:
    1. Splits the PDF at boundary points
    2. Applies rotation corrections if enabled
    3. Creates child Document records
    4. Uploads split PDFs to storage
    5. Updates SplitResult with child_document_id references

    Args:
        analysis_result: Dict from analyze_document_boundaries containing
                        starting_indices, rotation_map, and tenant_id

    Returns:
        Dict with split results including child document IDs
    """
    split_job_id = analysis_result["split_job_id"]
    tenant_id = analysis_result.get("tenant_id")  # For defense in depth
    starting_indices = analysis_result["starting_indices"]
    rotation_map = analysis_result.get("rotation_map", {})

    # Convert rotation_map keys to int (JSON serialization converts to strings)
    rotation_map = {int(k): v for k, v in rotation_map.items()}

    logger.info(
        f"Starting document split for job {split_job_id}: "
        f"{len(starting_indices)} documents"
    )

    db = SessionLocal()
    storage = get_storage_service()
    split_job: Optional[SplitJob] = None

    try:
        # Get split job with optional tenant validation
        job_uuid = UUID(split_job_id)
        query = db.query(SplitJob).filter(SplitJob.id == job_uuid)

        # Defense in depth: validate tenant_id if provided
        if tenant_id:
            tenant_uuid = UUID(tenant_id)
            query = query.filter(SplitJob.tenant_id == tenant_uuid)

        split_job = query.first()

        if not split_job:
            if tenant_id:
                logger.warning(
                    f"Split job {split_job_id} not found or tenant mismatch "
                    f"(requested tenant: {tenant_id})"
                )
            raise ValueError(f"SplitJob {split_job_id} not found")

        # Update status
        split_job.status = SplitJobStatus.SPLITTING.value
        db.commit()

        source_doc = split_job.source_document
        apply_rotation = split_job.apply_rotation

        # Download PDF
        pdf_bytes = storage.download_file_sync(source_doc.file_path)
        logger.info(f"Downloaded PDF for splitting: {len(pdf_bytes)} bytes")

        # Split PDF
        split_pdfs = split_pdf_by_indices(
            pdf_bytes=pdf_bytes,
            starting_indices=starting_indices,
            rotation_map=rotation_map,
            apply_rotation=apply_rotation,
        )

        logger.info(f"Split PDF into {len(split_pdfs)} child documents")

        # Create child documents
        child_document_ids = []
        sorted_indices = sorted(starting_indices)

        for i, (pdf_data, start_idx) in enumerate(zip(split_pdfs, sorted_indices)):
            # Calculate page range for filename
            if i + 1 < len(sorted_indices):
                end_idx = sorted_indices[i + 1] - 1
            else:
                end_idx = source_doc.page_count - 1 if source_doc.page_count else start_idx

            # Generate filename for child document
            sequence = i + 1
            base_name = source_doc.filename.rsplit(".", 1)[0] if "." in source_doc.filename else source_doc.filename
            child_filename = f"{base_name}_part{sequence:03d}_p{start_idx + 1}-{end_idx + 1}.pdf"

            # Upload to storage
            child_path = storage.upload_bytes_sync(
                pdf_data,
                filename=child_filename,
                prefix=f"documents/{source_doc.tenant_id}/splits/{split_job_id}",
            )

            # Create child document record
            child_doc = Document(
                tenant_id=source_doc.tenant_id,
                filename=child_filename,
                mime_type="application/pdf",
                size_bytes=len(pdf_data),
                file_path=child_path,
                status="uploaded",
                page_count=end_idx - start_idx + 1,
                document_metadata={
                    "source": "document_split",
                    "parent_document_id": str(source_doc.id),
                    "split_job_id": str(split_job.id),
                    "page_range": {"start": start_idx + 1, "end": end_idx + 1},
                },
                parent_document_id=source_doc.id,
                split_job_id=split_job.id,
                split_sequence=sequence,
            )
            db.add(child_doc)
            db.flush()  # Get the ID

            child_document_ids.append(str(child_doc.id))

            logger.info(
                f"Created child document {sequence}: {child_filename} "
                f"(pages {start_idx + 1}-{end_idx + 1})"
            )

            # Update SplitResult records for this document's pages
            for page_idx in range(start_idx, end_idx + 1):
                page_number = page_idx + 1
                split_result = (
                    db.query(SplitResult)
                    .filter(
                        SplitResult.split_job_id == split_job.id,
                        SplitResult.page_number == page_number,
                    )
                    .first()
                )
                if split_result:
                    split_result.child_document_id = child_doc.id

        # Update split job
        split_job.documents_created = len(split_pdfs)
        split_job.status = SplitJobStatus.COMPLETED.value
        split_job.completed_at = datetime.utcnow()

        # Update parent document status to SPLIT
        # This indicates the document has been split into children and
        # extraction should happen on child documents instead
        source_doc.status = DocumentStatus.SPLIT.value
        db.commit()

        result = {
            "split_job_id": split_job_id,
            "tenant_id": str(split_job.tenant_id),
            "documents_created": len(split_pdfs),
            "child_document_ids": child_document_ids,
            "status": "success",
        }

        logger.info(
            f"Document split completed for job {split_job_id}: "
            f"created {len(child_document_ids)} child documents"
        )

        return result

    except Exception as e:
        logger.error(f"Error in document split for job {split_job_id}: {e}", exc_info=True)

        if split_job:
            split_job.status = SplitJobStatus.FAILED.value
            split_job.error_message = _sanitize_task_error(str(e))
            split_job.completed_at = datetime.utcnow()
            db.commit()

        raise self.retry(exc=e)

    finally:
        db.close()


@celery_app.task(bind=True)
def process_split_job(
    self: Task,
    split_job_id: str,
    tenant_id: Optional[str] = None,
) -> str:
    """
    Entry point for document splitting.

    Chains the analysis and splitting tasks:
    1. analyze_document_boundaries - Detect page boundaries and rotation
    2. split_and_create_documents - Split PDF and create child documents

    Args:
        split_job_id: SplitJob UUID as string
        tenant_id: Tenant UUID for defense-in-depth validation (optional)

    Returns:
        Task chain result (final task ID)
    """
    logger.info(f"Starting split job pipeline for: {split_job_id}")

    # Chain the tasks with tenant_id for defense in depth
    workflow = chain(
        analyze_document_boundaries.s(split_job_id, tenant_id),
        split_and_create_documents.s(),
    )

    # Execute the chain
    result = workflow.apply_async()

    logger.info(f"Split job pipeline started for {split_job_id}, chain ID: {result.id}")

    return result.id


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def split_and_extract(
    self: Task,
    split_job_id: str,
    tenant_id: Optional[str] = None,
    extraction_config: Optional[Dict] = None,
) -> Dict:
    """
    Pipeline integration: Split document and queue extraction for each child.

    This task waits for the split job to complete, then queues extraction
    jobs for each child document.

    Args:
        split_job_id: SplitJob UUID as string
        tenant_id: Tenant UUID for defense-in-depth validation (optional)
        extraction_config: Optional extraction configuration to apply to children
                          (schema_id, model_provider_config, etc.)

    Returns:
        Dict with split job and extraction job IDs
    """
    from app.tasks.combined_extraction import process_extraction

    logger.info(f"Starting split-and-extract pipeline for job: {split_job_id}")

    db = SessionLocal()

    try:
        # Get split job with optional tenant validation
        job_uuid = UUID(split_job_id)
        query = db.query(SplitJob).filter(SplitJob.id == job_uuid)

        if tenant_id:
            tenant_uuid = UUID(tenant_id)
            query = query.filter(SplitJob.tenant_id == tenant_uuid)

        split_job = query.first()

        if not split_job:
            if tenant_id:
                logger.warning(
                    f"Split job {split_job_id} not found or tenant mismatch "
                    f"(requested tenant: {tenant_id})"
                )
            raise ValueError(f"SplitJob {split_job_id} not found")

        # Check split job status
        if split_job.status != SplitJobStatus.COMPLETED.value:
            if split_job.status == SplitJobStatus.FAILED.value:
                raise ValueError(f"Split job {split_job_id} failed: {split_job.error_message}")
            # Still in progress - retry later
            raise self.retry(
                exc=Exception(f"Split job {split_job_id} still in progress: {split_job.status}"),
                countdown=30,
            )

        # Get child documents with tenant isolation (defense in depth)
        child_docs = (
            db.query(Document)
            .filter(
                Document.split_job_id == split_job.id,
                Document.tenant_id == split_job.tenant_id,
            )
            .order_by(Document.split_sequence)
            .all()
        )

        if not child_docs:
            logger.warning(f"No child documents found for split job {split_job_id}")
            return {
                "split_job_id": split_job_id,
                "extraction_jobs": [],
                "status": "no_children",
            }

        # Queue extraction for each child document
        extraction_job_ids = []

        for child_doc in child_docs:
            if extraction_config:
                # Queue extraction task
                result = process_extraction.delay(
                    document_id=str(child_doc.id),
                    **extraction_config,
                )
                extraction_job_ids.append(result.id)
                logger.info(
                    f"Queued extraction for child document {child_doc.id}: task {result.id}"
                )

        result = {
            "split_job_id": split_job_id,
            "child_document_ids": [str(d.id) for d in child_docs],
            "extraction_job_ids": extraction_job_ids,
            "status": "success",
        }

        logger.info(
            f"Split-and-extract completed for job {split_job_id}: "
            f"queued {len(extraction_job_ids)} extraction jobs"
        )

        return result

    except Exception as e:
        logger.error(f"Error in split-and-extract for job {split_job_id}: {e}", exc_info=True)
        raise self.retry(exc=e)

    finally:
        db.close()
