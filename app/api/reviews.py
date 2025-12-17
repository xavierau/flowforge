"""Review API endpoints for Human-in-the-Loop (HITL) system.

This module provides REST API endpoints for managing human review requests
and corrections for AI document extraction results.

Endpoints:
    POST   /jobs/{job_id}/request-review    - Request manual review for a job
    GET    /reviews/queue                   - Get review queue (paginated, filtered)
    GET    /reviews/{review_id}             - Get review details
    POST   /reviews/{review_id}/assign      - Assign review to a user
    POST   /reviews/{review_id}/start       - Start review (mark as in_review)
    POST   /reviews/{review_id}/submit      - Submit corrections and complete review
    GET    /reviews/{review_id}/corrections - Get corrections for a review
    DELETE /reviews/{review_id}             - Cancel a review request
    POST   /reviews/{review_id}/escalate    - Escalate a review request
    GET    /reviews/metrics                 - Get review accuracy metrics
"""

import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, ExtractionJob
from app.models.review_request import ReviewRequest
from app.models.review_correction import ReviewCorrection
from app.models.enums import ReviewRequestStatus, ReviewPriority, CorrectionType
from app.schemas.review import (
    ReviewRequestCreate,
    ReviewRequestResponse,
    ReviewAssignRequest,
    ReviewEscalateRequest,
    ReviewSubmitRequest,
    ReviewQueueResponse,
    ReviewMetricsResponse,
    CorrectionResponse,
)
from app.services.hitl_service import HITLService
from app.dependencies.auth import require_permission_flexible, require_permission

logger = logging.getLogger(__name__)

router = APIRouter()


# ----- Manual Review Request -----

@router.post(
    "/jobs/{job_id}/request-review",
    response_model=ReviewRequestResponse,
    status_code=201
)
async def request_review_for_job(
    job_id: UUID,
    current_user: User = Depends(require_permission_flexible("extraction:review")),
    db: Session = Depends(get_db)
) -> ReviewRequestResponse:
    """
    Request manual human review for an extraction job.

    Creates a review request with NORMAL priority for the specified extraction job.
    Use this endpoint when you want to manually trigger a review regardless of
    the AI confidence score.

    Required Permission: extraction:review

    Args:
        job_id: UUID of the extraction job to review

    Returns:
        Created review request details

    Raises:
        404: Extraction job not found or belongs to different tenant
        400: Review request already exists for this job
    """
    # Verify job exists and belongs to tenant
    job = db.query(ExtractionJob).filter(
        ExtractionJob.id == job_id,
        ExtractionJob.tenant_id == current_user.tenant_id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Extraction job not found")

    # Create review request via service
    hitl_service = HITLService(db)

    try:
        review_request = hitl_service.create_review_request(
            extraction_job_id=job_id,
            tenant_id=current_user.tenant_id,  # SECURITY: Tenant isolation
            trigger_reason="manual_request"
        )
        return review_request
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----- Review Queue -----

@router.get("/reviews/queue", response_model=ReviewQueueResponse)
async def get_review_queue(
    status: Optional[ReviewRequestStatus] = Query(
        None, description="Filter by status"
    ),
    priority: Optional[ReviewPriority] = Query(
        None, description="Filter by priority"
    ),
    assigned_to_user_id: Optional[UUID] = Query(
        None, description="Filter by assignee"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_permission_flexible("reviews:read")),
    db: Session = Depends(get_db)
) -> ReviewQueueResponse:
    """
    Get paginated review queue with optional filters.

    Returns review requests for the current user's tenant, sorted by
    priority (critical first) and creation time (oldest first within same priority).

    Required Permission: reviews:read

    Args:
        status: Filter by review status
        priority: Filter by review priority
        assigned_to_user_id: Filter by assigned user
        page: Page number (1-indexed)
        page_size: Items per page (max 100)

    Returns:
        Paginated list of review requests with total count
    """
    hitl_service = HITLService(db)

    reviews, total = hitl_service.get_review_queue(
        tenant_id=current_user.tenant_id,
        status=status,
        priority=priority,
        assigned_to_user_id=assigned_to_user_id,
        page=page,
        page_size=page_size
    )

    total_pages = (total + page_size - 1) // page_size

    return ReviewQueueResponse(
        items=[ReviewRequestResponse.model_validate(r) for r in reviews],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


# ----- Review Metrics -----
# NOTE: This endpoint MUST be defined BEFORE /reviews/{review_id} to avoid route conflicts

@router.get("/reviews/metrics", response_model=ReviewMetricsResponse)
async def get_review_metrics(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    current_user: User = Depends(require_permission_flexible("reviews:read")),
    db: Session = Depends(get_db)
) -> ReviewMetricsResponse:
    """
    Get review accuracy and performance metrics for the tenant.

    Metrics include:
    - Total and completed review counts
    - Average review time
    - SLA breach count
    - Most frequently corrected fields
    - Accuracy rates by schema

    Required Permission: reviews:read

    Args:
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering

    Returns:
        Review metrics for the tenant
    """
    hitl_service = HITLService(db)

    metrics = hitl_service.calculate_review_metrics(
        tenant_id=current_user.tenant_id,
        start_date=start_date,
        end_date=end_date
    )

    # Calculate pending reviews
    pending_count = db.query(ReviewRequest).filter(
        ReviewRequest.tenant_id == current_user.tenant_id,
        ReviewRequest.status.in_([
            ReviewRequestStatus.PENDING.value,
            ReviewRequestStatus.ASSIGNED.value,
            ReviewRequestStatus.IN_REVIEW.value
        ])
    ).count()

    # Calculate SLA breach count
    sla_breach_count = db.query(ReviewRequest).filter(
        ReviewRequest.tenant_id == current_user.tenant_id,
        ReviewRequest.status == ReviewRequestStatus.ESCALATED.value
    ).count()

    return ReviewMetricsResponse(
        total_reviews=metrics["total_reviews"],
        completed_reviews=metrics["completed_reviews"],
        pending_reviews=pending_count,
        average_review_time_minutes=metrics["avg_review_time_minutes"],
        sla_breach_count=sla_breach_count,
        accuracy_by_schema={},  # TODO: Implement per-schema accuracy
        most_corrected_fields=[
            {"field_path": field, "correction_count": count}
            for field, count in metrics["top_corrected_fields"]
        ]
    )


# ----- Review Details -----

@router.get("/reviews/{review_id}", response_model=ReviewRequestResponse)
async def get_review_details(
    review_id: UUID,
    current_user: User = Depends(require_permission_flexible("reviews:read")),
    db: Session = Depends(get_db)
) -> ReviewRequestResponse:
    """
    Get details for a specific review request.

    Required Permission: reviews:read

    Args:
        review_id: UUID of the review request

    Returns:
        Review request details

    Raises:
        404: Review request not found or belongs to different tenant
    """
    review = db.query(ReviewRequest).filter(
        ReviewRequest.id == review_id,
        ReviewRequest.tenant_id == current_user.tenant_id
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review request not found")

    return review


# ----- Review Assignment -----

@router.post("/reviews/{review_id}/assign", response_model=ReviewRequestResponse)
async def assign_review(
    review_id: UUID,
    request: ReviewAssignRequest,
    current_user: User = Depends(require_permission("reviews:assign")),
    db: Session = Depends(get_db)
) -> ReviewRequestResponse:
    """
    Assign a review request to a user.

    Can only assign reviews in PENDING or ASSIGNED status.
    Re-assigning an already assigned review is allowed.

    Required Permission: reviews:assign (JWT only - no API tokens)

    Args:
        review_id: UUID of the review request
        request: Assignment request with target user ID

    Returns:
        Updated review request

    Raises:
        404: Review request not found or belongs to different tenant
        400: Review not in assignable state
    """
    # Verify review belongs to tenant
    review = db.query(ReviewRequest).filter(
        ReviewRequest.id == review_id,
        ReviewRequest.tenant_id == current_user.tenant_id
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review request not found")

    hitl_service = HITLService(db)

    try:
        updated_review = hitl_service.assign_review(
            review_id=review_id,
            tenant_id=current_user.tenant_id,  # SECURITY: Tenant isolation
            assigned_to_user_id=request.user_id,
            current_user_id=current_user.id
        )
        return updated_review
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----- Start Review -----

@router.post("/reviews/{review_id}/start", response_model=ReviewRequestResponse)
async def start_review(
    review_id: UUID,
    current_user: User = Depends(require_permission_flexible("reviews:update")),
    db: Session = Depends(get_db)
) -> ReviewRequestResponse:
    """
    Start a review (transition from ASSIGNED to IN_REVIEW).

    Can only be called by the assigned reviewer.
    Marks the review as actively being worked on.

    Required Permission: reviews:update

    Args:
        review_id: UUID of the review request

    Returns:
        Updated review request

    Raises:
        404: Review request not found or belongs to different tenant
        403: Current user is not the assigned reviewer
        400: Review not in ASSIGNED state
    """
    # Verify review belongs to tenant
    review = db.query(ReviewRequest).filter(
        ReviewRequest.id == review_id,
        ReviewRequest.tenant_id == current_user.tenant_id
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review request not found")

    hitl_service = HITLService(db)

    try:
        updated_review = hitl_service.start_review(
            review_id=review_id,
            tenant_id=current_user.tenant_id,  # SECURITY: Tenant isolation
            current_user_id=current_user.id
        )
        return updated_review
    except ValueError as e:
        error_msg = str(e)
        if "assigned to another user" in error_msg.lower():
            raise HTTPException(status_code=403, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)


# ----- Submit Corrections -----

@router.post("/reviews/{review_id}/submit", response_model=ReviewRequestResponse)
async def submit_review_corrections(
    review_id: UUID,
    request: ReviewSubmitRequest,
    current_user: User = Depends(require_permission_flexible("reviews:update")),
    db: Session = Depends(get_db)
) -> ReviewRequestResponse:
    """
    Submit corrections for a review and mark as completed.

    Applies corrections to the extraction results and completes the review.
    Can only be called by the assigned reviewer while review is IN_REVIEW.

    Required Permission: reviews:update

    Args:
        review_id: UUID of the review request
        request: Corrections to submit

    Returns:
        Completed review request

    Raises:
        404: Review request not found or belongs to different tenant
        403: Current user is not the assigned reviewer
        400: Review not in IN_REVIEW state or invalid correction data
    """
    # Verify review belongs to tenant
    review = db.query(ReviewRequest).filter(
        ReviewRequest.id == review_id,
        ReviewRequest.tenant_id == current_user.tenant_id
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review request not found")

    hitl_service = HITLService(db)

    # Convert corrections to dict format expected by service
    corrections_data = [
        {
            "extraction_result_id": str(c.extraction_result_id),
            "field_path": c.field_path,
            "original_value": c.original_value,
            "corrected_value": c.corrected_value,
            "correction_type": c.correction_type.value if isinstance(c.correction_type, CorrectionType) else c.correction_type,
            "correction_notes": c.correction_notes
        }
        for c in request.corrections
    ]

    try:
        completed_review = hitl_service.submit_corrections(
            review_id=review_id,
            tenant_id=current_user.tenant_id,  # SECURITY: Tenant isolation
            corrections=corrections_data,
            corrected_by_user_id=current_user.id,
            review_notes=request.review_notes
        )
        return completed_review
    except ValueError as e:
        error_msg = str(e)
        if "assigned to another user" in error_msg.lower():
            raise HTTPException(status_code=403, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)


# ----- Get Corrections -----

@router.get(
    "/reviews/{review_id}/corrections",
    response_model=List[CorrectionResponse]
)
async def get_review_corrections(
    review_id: UUID,
    current_user: User = Depends(require_permission_flexible("reviews:read")),
    db: Session = Depends(get_db)
) -> List[CorrectionResponse]:
    """
    Get all corrections for a review request.

    Required Permission: reviews:read

    Args:
        review_id: UUID of the review request

    Returns:
        List of corrections made during the review

    Raises:
        404: Review request not found or belongs to different tenant
    """
    # Verify review belongs to tenant
    review = db.query(ReviewRequest).filter(
        ReviewRequest.id == review_id,
        ReviewRequest.tenant_id == current_user.tenant_id
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review request not found")

    corrections = db.query(ReviewCorrection).filter(
        ReviewCorrection.review_request_id == review_id
    ).order_by(ReviewCorrection.created_at).all()

    return corrections


# ----- Cancel Review -----

@router.delete("/reviews/{review_id}", response_model=ReviewRequestResponse)
async def cancel_review(
    review_id: UUID,
    reason: Optional[str] = Query(None, description="Cancellation reason"),
    current_user: User = Depends(require_permission("reviews:delete")),
    db: Session = Depends(get_db)
) -> ReviewRequestResponse:
    """
    Cancel a review request.

    Cannot cancel completed reviews.

    Required Permission: reviews:delete (JWT only - no API tokens)

    Args:
        review_id: UUID of the review request
        reason: Optional cancellation reason

    Returns:
        Cancelled review request

    Raises:
        404: Review request not found or belongs to different tenant
        400: Review is already completed
    """
    # Verify review belongs to tenant
    review = db.query(ReviewRequest).filter(
        ReviewRequest.id == review_id,
        ReviewRequest.tenant_id == current_user.tenant_id
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review request not found")

    hitl_service = HITLService(db)

    try:
        cancelled_review = hitl_service.cancel_review(
            review_id=review_id,
            tenant_id=current_user.tenant_id,  # SECURITY: Tenant isolation
            current_user_id=current_user.id,
            reason=reason
        )
        return cancelled_review
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----- Escalate Review -----

@router.post("/reviews/{review_id}/escalate", response_model=ReviewRequestResponse)
async def escalate_review(
    review_id: UUID,
    request: ReviewEscalateRequest,
    current_user: User = Depends(require_permission_flexible("reviews:update")),
    db: Session = Depends(get_db)
) -> ReviewRequestResponse:
    """
    Escalate a review request to higher priority.

    Can be called when a review requires additional expertise or has exceeded
    the SLA deadline. Updates the review status to ESCALATED.

    Required Permission: reviews:update

    Args:
        review_id: UUID of the review request
        request: Escalation request with reason

    Returns:
        Escalated review request

    Raises:
        404: Review request not found or belongs to different tenant
        400: Review cannot be escalated (already completed/cancelled)
    """
    # Verify review belongs to tenant
    review = db.query(ReviewRequest).filter(
        ReviewRequest.id == review_id,
        ReviewRequest.tenant_id == current_user.tenant_id
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review request not found")

    hitl_service = HITLService(db)

    try:
        escalated_review = hitl_service.escalate_review(
            review_id=review_id,
            tenant_id=current_user.tenant_id,
            current_user_id=current_user.id,
            reason=request.reason
        )
        return escalated_review
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
