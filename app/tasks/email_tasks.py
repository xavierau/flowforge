"""Email notification tasks."""

import asyncio
import logging
from celery import Task

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def send_invitation_email_task(
    self: Task,
    to_email: str,
    invitation_url: str,
    invited_by: str,
    tenant_name: str,
) -> dict:
    """
    Send an invitation email to a new user.

    Retries up to 5 times with exponential backoff if email delivery fails.
    Retry delays: 60s, 120s, 240s, 480s, 960s (16 minutes max)

    Args:
        to_email: Email address of the invitee
        invitation_url: URL for the invitation link
        invited_by: Name or email of the person who sent the invitation
        tenant_name: Name of the tenant/organization

    Returns:
        Dictionary with status and details
    """
    from app.services.email_service import (
        get_email_service,
        EmailConfigurationError,
        EmailDeliveryError,
    )

    try:
        email_service = get_email_service()

        # Check if email service is configured
        if not email_service.is_configured():
            logger.warning(
                f"SMTP not configured - skipping invitation email to {to_email}"
            )
            return {
                "status": "skipped",
                "reason": "SMTP not configured",
                "to_email": to_email,
                "invited_by": invited_by,
                "tenant_name": tenant_name,
            }

        # Send the invitation email (async operation)
        asyncio.run(
            email_service.send_invitation_email(
                to_email=to_email,
                invitation_url=invitation_url,
                invited_by=invited_by,
                tenant_name=tenant_name,
            )
        )

        logger.info(f"Successfully sent invitation email to {to_email}")
        return {
            "status": "success",
            "to_email": to_email,
            "invited_by": invited_by,
            "tenant_name": tenant_name,
        }

    except EmailConfigurationError as e:
        # Configuration error - don't retry, it won't help
        logger.error(
            f"Email configuration error for invitation to {to_email}: {str(e)}"
        )
        return {
            "status": "failed",
            "reason": "configuration_error",
            "error": str(e),
            "to_email": to_email,
            "invited_by": invited_by,
            "tenant_name": tenant_name,
        }

    except EmailDeliveryError as e:
        # Delivery error - retry with exponential backoff
        logger.warning(
            f"Email delivery failed for invitation to {to_email} "
            f"(attempt {self.request.retries + 1}/{self.max_retries}): {str(e)}"
        )
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    except Exception as e:
        # Unexpected error - still retry with backoff
        logger.error(
            f"Unexpected error sending invitation email to {to_email} "
            f"(attempt {self.request.retries + 1}/{self.max_retries}): {str(e)}"
        )
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
