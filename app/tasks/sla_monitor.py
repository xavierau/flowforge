"""SLA monitoring task for HITL review system.

This module provides a Celery periodic task that monitors review request SLA
deadlines and escalates reviews that have breached their SLA.

The task runs every 5 minutes and:
1. Finds all review requests past their SLA deadline
2. Marks them as ESCALATED status
3. Logs warnings for operational monitoring
"""

import logging
from datetime import datetime

from celery import Task

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.services.hitl_service import HITLService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def check_sla_breaches(self: Task) -> dict:
    """
    Check for SLA breaches and escalate reviews.

    This task should be run periodically (recommended: every 5 minutes) via
    Celery Beat or a similar scheduler.

    The task:
    1. Queries all review requests past their SLA deadline
    2. Marks them as ESCALATED status
    3. Updates the escalated_at timestamp
    4. Logs warnings for each breached review

    Returns:
        Dictionary with:
            - escalated_count: Number of reviews escalated
            - escalated_ids: List of escalated review request IDs

    Example Celery Beat configuration:
        CELERY_BEAT_SCHEDULE = {
            'check-sla-breaches': {
                'task': 'app.tasks.sla_monitor.check_sla_breaches',
                'schedule': 300.0,  # Every 5 minutes (300 seconds)
            },
        }
    """
    db = SessionLocal()

    try:
        logger.info("Starting SLA breach check...")
        start_time = datetime.utcnow()

        hitl_service = HITLService(db)
        escalated_reviews = hitl_service.check_sla_breaches()

        escalated_count = len(escalated_reviews)
        escalated_ids = [str(r.id) for r in escalated_reviews]

        if escalated_count > 0:
            logger.warning(
                f"SLA breach check completed: {escalated_count} reviews escalated",
                extra={
                    "escalated_count": escalated_count,
                    "escalated_ids": escalated_ids,
                    "check_duration_ms": int(
                        (datetime.utcnow() - start_time).total_seconds() * 1000
                    )
                }
            )
        else:
            logger.info(
                "SLA breach check completed: No breaches found",
                extra={
                    "check_duration_ms": int(
                        (datetime.utcnow() - start_time).total_seconds() * 1000
                    )
                }
            )

        return {
            "escalated_count": escalated_count,
            "escalated_ids": escalated_ids,
            "checked_at": start_time.isoformat()
        }

    except Exception as e:
        logger.error(
            f"Error during SLA breach check: {str(e)}",
            exc_info=True
        )
        raise

    finally:
        db.close()


# Configure Celery Beat schedule
# This can be imported in celery_app.py or configured in settings
CELERY_BEAT_SCHEDULE = {
    'check-sla-breaches-every-5-minutes': {
        'task': 'app.tasks.sla_monitor.check_sla_breaches',
        'schedule': 300.0,  # Every 5 minutes (300 seconds)
        'options': {
            'queue': 'default',
            'expires': 290,  # Expire before next scheduled run
        }
    },
}
