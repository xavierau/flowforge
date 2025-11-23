"""Health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.models import User
from app.dependencies.auth import require_permission
from app.monitoring.credit_health import CreditHealthMonitor

router = APIRouter()


@router.get("/health")
async def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    """
    Health check endpoint.

    Returns:
        Health status
    """
    try:
        # Check database connection
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "service": "ai-document-processing",
        "version": "0.1.0",
    }


@router.get("/health/credits")
async def credit_health_check(
    current_user: User = Depends(require_permission("admin:health_checks")),
    db: Session = Depends(get_db),
):
    """
    Check credit system health.

    Returns comprehensive health status including:
    - Completed jobs without credit deductions
    - Negative tenant balances
    - Duplicate credit transactions
    - Balance mismatches

    Required Permission: admin:health_checks

    Args:
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Health status with any violations found

    Status Codes:
        - "healthy": No violations detected
        - "degraded": Non-critical violations found
        - "unhealthy": Critical violations found
    """
    monitor = CreditHealthMonitor(db)
    health_summary = monitor.get_health_summary()

    return health_summary
