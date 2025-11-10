"""API endpoints for metrics and billing."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.services.metrics_service import MetricsService
from app.schemas.metrics import DashboardMetricsResponse, CompletedJobsResponse


router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/dashboard", response_model=DashboardMetricsResponse)
async def get_dashboard_metrics(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Number of days to include in metrics (1-365)",
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get dashboard metrics for the current user's tenant.

    Returns summary statistics, time series data for charts, and model distribution.

    **Permissions:** Requires valid authentication (no specific permissions needed)

    **Query Parameters:**
    - days: Number of days to include (default: 30, max: 365)

    **Returns:**
    - stats: Summary statistics (total jobs, pages, tokens, cost)
    - jobs_over_time: Jobs completed per day
    - pages_over_time: Pages processed per day
    - tokens_over_time: Token usage per day
    - model_distribution: Model usage distribution
    """
    service = MetricsService(db)
    return service.get_dashboard_metrics(tenant_id=str(current_user.tenant_id), days=days)


@router.get("/jobs/completed", response_model=CompletedJobsResponse)
async def get_completed_jobs(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=50, ge=1, le=100, description="Number of items per page (max 100)"
    ),
    start_date: Optional[datetime] = Query(
        default=None, description="Filter by start date (ISO 8601 format)"
    ),
    end_date: Optional[datetime] = Query(
        default=None, description="Filter by end date (ISO 8601 format)"
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get paginated list of completed jobs for billing purposes.

    **Permissions:** Requires valid authentication (no specific permissions needed)

    **Query Parameters:**
    - page: Page number (default: 1)
    - page_size: Items per page (default: 50, max: 100)
    - start_date: Optional start date filter (ISO 8601)
    - end_date: Optional end date filter (ISO 8601)

    **Returns:**
    - jobs: List of completed jobs with cost estimates
    - total: Total number of jobs matching filters
    - page: Current page number
    - page_size: Items per page
    - total_pages: Total number of pages
    - total_cost: Sum of estimated costs for all jobs
    """
    service = MetricsService(db)
    return service.get_completed_jobs(
        tenant_id=str(current_user.tenant_id),
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
    )
