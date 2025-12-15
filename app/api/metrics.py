"""API endpoints for metrics and billing."""
from datetime import datetime
from typing import Optional
import logging
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_active_user, require_permission_flexible
from app.models.user import User
from app.services.metrics_service import MetricsService
from app.schemas.metrics import DashboardMetricsResponse, CompletedJobsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _log_tenant_info(endpoint: str, current_user: User) -> None:
    """Log tenant information for debugging."""
    logger.info(f"[{endpoint}] === REQUEST START ===")
    logger.info(f"[{endpoint}] User email: {current_user.email}")
    logger.info(f"[{endpoint}] User ID: {current_user.id}")
    logger.info(f"[{endpoint}] Tenant ID: {current_user.tenant_id}")
    logger.info(f"[{endpoint}] Tenant ID type: {type(current_user.tenant_id).__name__}")


@router.get("/debug/current-user")
async def debug_current_user(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Debug endpoint to check current user and tenant info.

    Returns current user details including tenant_id for troubleshooting.
    """
    from sqlalchemy import func
    from app.models.extraction_job import ExtractionJob
    from app.models.document import Document

    # Count completed jobs for this tenant
    completed_jobs_count = (
        db.query(func.count(ExtractionJob.id))
        .join(Document, ExtractionJob.document_id == Document.id)
        .filter(Document.tenant_id == current_user.tenant_id)
        .filter(ExtractionJob.status == "completed")
        .scalar()
    )

    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "tenant_id": str(current_user.tenant_id),
        "completed_jobs_for_tenant": completed_jobs_count,
    }


@router.get("/stats", response_model=DashboardMetricsResponse, status_code=200)
async def get_dashboard_stats(
    response: Response,
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Number of days to include in metrics (1-365)",
    ),
    current_user: User = Depends(require_permission_flexible("jobs:read")),
    db: Session = Depends(get_db),
):
    """Alias endpoint for dashboard metrics - testing if 'metrics' in URL is blocked."""
    return await get_dashboard_metrics(response, days, current_user, db)


@router.get("/dashboard", response_model=DashboardMetricsResponse, status_code=200)
async def get_dashboard_metrics(
    response: Response,
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Number of days to include in metrics (1-365)",
    ),
    current_user: User = Depends(require_permission_flexible("jobs:read")),
    db: Session = Depends(get_db),
):
    """
    Get dashboard metrics for the current user's tenant.

    Returns summary statistics, time series data for charts, and model distribution.

    **Permissions:** Requires `jobs:read` permission (supports both JWT and API tokens)

    **Query Parameters:**
    - days: Number of days to include (default: 30, max: 365)

    **Returns:**
    - stats: Summary statistics (total jobs, pages, tokens, cost)
    - jobs_over_time: Jobs completed per day
    - pages_over_time: Pages processed per day
    - tokens_over_time: Token usage per day
    - model_distribution: Model usage distribution
    """
    _log_tenant_info("DASHBOARD", current_user)
    logger.info(f"[DASHBOARD] Days parameter: {days}")

    # Set response headers to prevent caching
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    service = MetricsService(db)
    logger.info(f"[DASHBOARD] Calling service.get_dashboard_metrics with tenant_id={current_user.tenant_id}")

    result = service.get_dashboard_metrics(tenant_id=current_user.tenant_id, days=days)

    logger.info(f"[DASHBOARD] === RESPONSE ===")
    logger.info(f"[DASHBOARD] Total jobs: {result.stats.total_jobs}")
    logger.info(f"[DASHBOARD] Total pages: {result.stats.total_pages}")
    logger.info(f"[DASHBOARD] Total tokens: {result.stats.total_tokens}")
    logger.info(f"[DASHBOARD] Estimated cost: {result.stats.estimated_cost}")
    logger.info(f"[DASHBOARD] Jobs over time count: {len(result.jobs_over_time)}")
    logger.info(f"[DASHBOARD] Model distribution count: {len(result.model_distribution)}")
    logger.info(f"[DASHBOARD] === REQUEST END ===")

    return result


@router.get("/jobs/completed", response_model=CompletedJobsResponse, status_code=200)
async def get_completed_jobs(
    response: Response,
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
    current_user: User = Depends(require_permission_flexible("jobs:read")),
    db: Session = Depends(get_db),
):
    """
    Get paginated list of completed jobs for billing purposes.

    **Permissions:** Requires `jobs:read` permission (supports both JWT and API tokens)

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
    _log_tenant_info("COMPLETED_JOBS", current_user)
    logger.info(f"[COMPLETED_JOBS] Parameters: page={page}, page_size={page_size}, start_date={start_date}, end_date={end_date}")

    # Set response headers to prevent caching
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    service = MetricsService(db)
    logger.info(f"[COMPLETED_JOBS] Calling service.get_completed_jobs with tenant_id={current_user.tenant_id} (type: {type(current_user.tenant_id).__name__})")

    result = service.get_completed_jobs(
        tenant_id=current_user.tenant_id,
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
    )

    logger.info(f"[COMPLETED_JOBS] === RESPONSE ===")
    logger.info(f"[COMPLETED_JOBS] Total jobs found: {result.total}")
    logger.info(f"[COMPLETED_JOBS] Jobs in response: {len(result.jobs)}")
    logger.info(f"[COMPLETED_JOBS] Total pages: {result.total_pages}")
    logger.info(f"[COMPLETED_JOBS] Total cost: {result.total_cost}")
    logger.info(f"[COMPLETED_JOBS] === REQUEST END ===")

    return result
