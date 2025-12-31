"""Document splitting endpoints."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies.auth import require_permission_flexible
from app.models import Document, User
from app.models.document_split import SplitJob, SplitResult
from app.models.enums import SplitJobStatus
from app.schemas.document_split import (
    SplitJobCreateRequest,
    SplitJobCreateResponse,
    SplitJobStatusResponse,
    SplitJobProgress,
    SplitJobResultsResponse,
    SplitJobSummary,
    PageAnalysisResult,
    ChildDocumentResponse,
    ChildDocumentsListResponse,
)
from app.tasks.document_splitter import process_split_job

router = APIRouter()
logger = logging.getLogger(__name__)


def _sanitize_error_message(error_message: Optional[str]) -> Optional[str]:
    """Sanitize error messages to avoid exposing internal details.

    Args:
        error_message: Raw error message from database

    Returns:
        Sanitized error message safe for client display
    """
    if not error_message:
        return None

    # User-initiated cancellation - return as-is
    if error_message == "Cancelled by user":
        return error_message

    # Map known error patterns to safe messages
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
        return "Rate limit exceeded, please try again later"

    # Generic fallback - don't expose internal details
    return "An error occurred during processing"


@router.post(
    "/documents/{document_id}/split",
    response_model=SplitJobCreateResponse,
    status_code=202,
)
async def create_split_job(
    document_id: UUID,
    request: SplitJobCreateRequest,
    current_user: User = Depends(require_permission_flexible("documents:create")),
    db: Session = Depends(get_db),
) -> SplitJobCreateResponse:
    """
    Queue a split job to analyze and split a multi-document PDF.

    This endpoint:
    1. Creates a SplitJob record
    2. Queues background tasks for boundary analysis and splitting
    3. Returns immediately with the job ID

    The split process:
    - Analyzes each page for document boundaries using DSPy + Qwen VL
    - Detects page rotation using Tesseract OSD
    - Splits PDF at detected boundaries
    - Applies rotation corrections if enabled
    - Creates child Document records linked to parent

    Required Permission: documents:create

    Args:
        document_id: Source document UUID
        request: Split job configuration
        current_user: Authenticated user
        db: Database session

    Returns:
        Split job creation response with job ID
    """
    # Get source document with tenant isolation
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Validate document is a PDF
    if document.mime_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF documents can be split",
        )

    # Validate document has been processed (has pages)
    if document.status not in ("ready_for_extraction", "completed"):
        raise HTTPException(
            status_code=400,
            detail=f"Document must be processed before splitting. Current status: {document.status}",
        )

    # Check if there's already an active split job for this document
    existing_job = (
        db.query(SplitJob)
        .filter(
            SplitJob.source_document_id == document_id,
            SplitJob.status.in_([
                SplitJobStatus.QUEUED.value,
                SplitJobStatus.ANALYZING.value,
                SplitJobStatus.SPLITTING.value,
            ]),
        )
        .first()
    )

    if existing_job:
        raise HTTPException(
            status_code=409,
            detail=f"A split job is already in progress for this document: {existing_job.id}",
        )

    # Create split job
    split_job = SplitJob(
        tenant_id=current_user.tenant_id,
        source_document_id=document_id,
        status=SplitJobStatus.QUEUED.value,
        apply_rotation=request.apply_rotation,
        dspy_model=request.dspy_model or settings.default_qwen_vision_model,
    )
    db.add(split_job)
    db.commit()
    db.refresh(split_job)

    # Queue the split job task with tenant_id for defense in depth
    process_split_job.delay(str(split_job.id), str(current_user.tenant_id))

    logger.info(
        f"Created split job {split_job.id} for document {document_id} "
        f"(apply_rotation={request.apply_rotation})"
    )

    # Estimate time based on page count
    estimated_seconds = None
    if document.page_count:
        # Rough estimate: ~2 seconds per page for analysis + 1 second per page for splitting
        estimated_seconds = document.page_count * 3

    return SplitJobCreateResponse(
        split_job_id=split_job.id,
        status=split_job.status,
        message="Split job queued successfully",
        estimated_time_seconds=estimated_seconds,
    )


@router.get("/splits/{split_job_id}", response_model=SplitJobStatusResponse)
async def get_split_job_status(
    split_job_id: UUID,
    current_user: User = Depends(require_permission_flexible("documents:read")),
    db: Session = Depends(get_db),
) -> SplitJobStatusResponse:
    """
    Get the status and summary of a split job.

    Required Permission: documents:read

    Args:
        split_job_id: Split job UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Split job status and statistics
    """
    split_job = (
        db.query(SplitJob)
        .filter(
            SplitJob.id == split_job_id,
            SplitJob.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if not split_job:
        raise HTTPException(status_code=404, detail="Split job not found")

    # Get total pages from source document
    total_pages = None
    if split_job.source_document:
        total_pages = split_job.source_document.page_count

    # Build progress info
    progress = SplitJobProgress(
        total_pages=total_pages,
        pages_analyzed=split_job.pages_analyzed,
        documents_created=split_job.documents_created,
        pages_rotated=split_job.pages_rotated,
        total_input_tokens=split_job.total_input_tokens,
        total_output_tokens=split_job.total_output_tokens,
    )

    return SplitJobStatusResponse(
        split_job_id=split_job.id,
        status=split_job.status,
        source_document_id=split_job.source_document_id,
        apply_rotation=split_job.apply_rotation,
        dspy_model=split_job.dspy_model,
        progress=progress,
        error_message=_sanitize_error_message(split_job.error_message),
        started_at=split_job.started_at,
        completed_at=split_job.completed_at,
        created_at=split_job.created_at,
    )


@router.get("/splits/{split_job_id}/results", response_model=SplitJobResultsResponse)
async def get_split_job_results(
    split_job_id: UUID,
    current_user: User = Depends(require_permission_flexible("documents:read")),
    db: Session = Depends(get_db),
) -> SplitJobResultsResponse:
    """
    Get detailed per-page analysis results from a split job.

    Required Permission: documents:read

    Args:
        split_job_id: Split job UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Detailed page-by-page analysis results
    """
    split_job = (
        db.query(SplitJob)
        .filter(
            SplitJob.id == split_job_id,
            SplitJob.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if not split_job:
        raise HTTPException(status_code=404, detail="Split job not found")

    # Get split results ordered by page number
    split_results = (
        db.query(SplitResult)
        .filter(SplitResult.split_job_id == split_job_id)
        .order_by(SplitResult.page_number)
        .all()
    )

    # Convert to response format
    page_results = [
        PageAnalysisResult(
            page_number=r.page_number,
            # Boundary detection (reasoning first per LLM autoregression)
            boundary_reason=r.boundary_reason or "",
            detected_document_type=r.detected_document_type or "unknown",
            is_starting_page=r.is_starting_page,
            boundary_confidence=r.boundary_confidence or "low",
            # Rotation detection
            rotation_needed=r.rotation_needed,
            rotation_confidence=r.rotation_confidence or "low",
            rotation_method=r.rotation_method or "none",
            # Token tracking
            input_tokens=r.input_tokens,
            output_tokens=r.output_tokens,
            # Child document reference
            child_document_id=r.child_document_id,
        )
        for r in split_results
    ]

    # Build summary
    summary = SplitJobSummary(
        total_pages=split_job.pages_analyzed,
        documents_created=split_job.documents_created,
        pages_rotated=split_job.pages_rotated,
        total_input_tokens=split_job.total_input_tokens,
        total_output_tokens=split_job.total_output_tokens,
    )

    return SplitJobResultsResponse(
        split_job_id=split_job.id,
        source_document_id=split_job.source_document_id,
        status=split_job.status,
        page_results=page_results,
        summary=summary,
    )


@router.get(
    "/documents/{document_id}/children",
    response_model=ChildDocumentsListResponse,
)
async def get_child_documents(
    document_id: UUID,
    current_user: User = Depends(require_permission_flexible("documents:read")),
    db: Session = Depends(get_db),
) -> ChildDocumentsListResponse:
    """
    Get child documents created from splitting a parent document.

    Required Permission: documents:read

    Args:
        document_id: Parent document UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        List of child documents with their split information
    """
    # Verify parent document exists and belongs to tenant
    parent_doc = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if not parent_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get child documents
    children = (
        db.query(Document)
        .filter(
            Document.parent_document_id == document_id,
            Document.tenant_id == current_user.tenant_id,
        )
        .order_by(Document.split_sequence)
        .all()
    )

    child_responses = [
        ChildDocumentResponse(
            document_id=child.id,
            filename=child.filename,
            page_count=child.page_count,
            split_sequence=child.split_sequence,
            split_job_id=child.split_job_id,
            status=child.status,
            created_at=child.created_at,
        )
        for child in children
    ]

    return ChildDocumentsListResponse(
        parent_document_id=document_id,
        children=child_responses,
        total_count=len(child_responses),
    )


@router.delete("/splits/{split_job_id}", status_code=204)
async def cancel_split_job(
    split_job_id: UUID,
    current_user: User = Depends(require_permission_flexible("documents:delete")),
    db: Session = Depends(get_db),
) -> None:
    """
    Cancel a pending or in-progress split job.

    Note: This only marks the job as failed. If tasks are already running,
    they may complete before seeing the cancellation.

    Required Permission: documents:delete

    Args:
        split_job_id: Split job UUID
        current_user: Authenticated user
        db: Database session
    """
    split_job = (
        db.query(SplitJob)
        .filter(
            SplitJob.id == split_job_id,
            SplitJob.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if not split_job:
        raise HTTPException(status_code=404, detail="Split job not found")

    if split_job.status in (SplitJobStatus.COMPLETED.value, SplitJobStatus.FAILED.value):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status: {split_job.status}",
        )

    # Mark as failed/cancelled
    split_job.status = SplitJobStatus.FAILED.value
    split_job.error_message = "Cancelled by user"
    db.commit()

    logger.info(f"Split job {split_job_id} cancelled by user {current_user.id}")
