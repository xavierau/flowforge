"""Job status and results endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import ExtractionJob, ExtractionResult, DocumentPage, Document
from app.schemas.job import JobStatusResponse, JobResultResponse, JobProgress, ExtractionMetadata

router = APIRouter()


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> JobStatusResponse:
    """
    Get extraction job status.

    Args:
        job_id: Extraction job ID
        db: Database session

    Returns:
        Job status with progress information
    """
    # Get job
    job = db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Calculate progress
    progress = None
    if job.document.page_count:
        # Multi-page document
        total_pages = job.document.page_count
        completed_pages = (
            db.query(func.count(ExtractionResult.id))
            .filter(ExtractionResult.extraction_job_id == job.id)
            .scalar()
        )
        progress = JobProgress(
            total_pages=total_pages,
            completed_pages=completed_pages or 0,
        )

    return JobStatusResponse(
        job_id=job.id,
        document_id=job.document_id,
        status=job.status,
        progress=progress,
        started_at=job.started_at,
        updated_at=job.updated_at,
        error=job.error_message,
    )


@router.get("/jobs/{job_id}/result", response_model=JobResultResponse)
async def get_job_result(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> JobResultResponse:
    """
    Get extraction job results.

    Args:
        job_id: Extraction job ID
        db: Database session

    Returns:
        Extracted data and metadata
    """
    # Get job
    job = db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check if job is completed
    if job.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed yet. Status: {job.status}",
        )

    # Get results
    results = (
        db.query(ExtractionResult)
        .filter(ExtractionResult.extraction_job_id == job.id)
        .order_by(ExtractionResult.created_at)
        .all()
    )

    if not results:
        raise HTTPException(status_code=404, detail="No results found for this job")

    # Aggregate results
    if len(results) == 1:
        # Single page or single result
        result = results[0]
        extracted_data = result.extracted_data
        metadata = ExtractionMetadata(
            model_used=result.model_used,
            input_tokens=result.input_tokens or 0,
            output_tokens=result.output_tokens or 0,
            tokens_used=result.tokens_used or 0,
            processing_time_ms=result.processing_time_ms or 0,
            confidence_score=result.confidence_score or 0.0,
        )
    else:
        # Multi-page: combine results
        extracted_data = {
            "pages": [result.extracted_data for result in results],
            "page_count": len(results),
        }

        # Aggregate metadata
        total_input_tokens = sum(r.input_tokens or 0 for r in results)
        total_output_tokens = sum(r.output_tokens or 0 for r in results)
        total_tokens = sum(r.tokens_used or 0 for r in results)
        total_time = sum(r.processing_time_ms or 0 for r in results)
        avg_confidence = sum(r.confidence_score or 0 for r in results) / len(results)

        metadata = ExtractionMetadata(
            model_used=results[0].model_used,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            tokens_used=total_tokens,
            processing_time_ms=total_time,
            confidence_score=avg_confidence,
        )

    return JobResultResponse(
        job_id=job.id,
        document_id=job.document_id,
        status=job.status,
        extracted_data=extracted_data,
        metadata=metadata,
        completed_at=job.completed_at or job.updated_at,
    )
