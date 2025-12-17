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


@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def send_password_reset_email_task(
    self: Task,
    to_email: str,
    reset_url: str,
    user_name: str | None = None,
    expires_in_hours: int = 24,
) -> dict:
    """
    Send a password reset email to a user.

    Retries up to 5 times with exponential backoff if email delivery fails.
    Retry delays: 60s, 120s, 240s, 480s, 960s (16 minutes max)

    Args:
        to_email: Email address of the user
        reset_url: URL for resetting the password
        user_name: Optional user's name for personalization
        expires_in_hours: How many hours until the link expires (default 24)

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
                f"SMTP not configured - skipping password reset email to {to_email}"
            )
            return {
                "status": "skipped",
                "reason": "SMTP not configured",
                "to_email": to_email,
            }

        # Send the password reset email (async operation)
        asyncio.run(
            email_service.send_password_reset_email(
                to_email=to_email,
                reset_url=reset_url,
                user_name=user_name,
                expires_in_hours=expires_in_hours,
            )
        )

        logger.info(f"Successfully sent password reset email to {to_email}")
        return {
            "status": "success",
            "to_email": to_email,
        }

    except EmailConfigurationError as e:
        # Configuration error - don't retry, it won't help
        logger.error(
            f"Email configuration error for password reset to {to_email}: {str(e)}"
        )
        return {
            "status": "failed",
            "reason": "configuration_error",
            "error": str(e),
            "to_email": to_email,
        }

    except EmailDeliveryError as e:
        # Delivery error - retry with exponential backoff
        logger.warning(
            f"Email delivery failed for password reset to {to_email} "
            f"(attempt {self.request.retries + 1}/{self.max_retries}): {str(e)}"
        )
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    except Exception as e:
        # Unexpected error - still retry with backoff
        logger.error(
            f"Unexpected error sending password reset email to {to_email} "
            f"(attempt {self.request.retries + 1}/{self.max_retries}): {str(e)}"
        )
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def send_verification_email_task(
    self: Task,
    to_email: str,
    verification_url: str,
    user_name: str | None = None,
    expires_in_hours: int = 48,
) -> dict:
    """
    Send an email verification email to a user.

    Retries up to 5 times with exponential backoff if email delivery fails.
    Retry delays: 60s, 120s, 240s, 480s, 960s (16 minutes max)

    Args:
        to_email: Email address of the user
        verification_url: URL for verifying the email
        user_name: Optional user's name for personalization
        expires_in_hours: How many hours until the link expires (default 48)

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
                f"SMTP not configured - skipping verification email to {to_email}"
            )
            return {
                "status": "skipped",
                "reason": "SMTP not configured",
                "to_email": to_email,
            }

        # Send the verification email (async operation)
        asyncio.run(
            email_service.send_verification_email(
                to_email=to_email,
                verification_url=verification_url,
                user_name=user_name,
                expires_in_hours=expires_in_hours,
            )
        )

        logger.info(f"Successfully sent verification email to {to_email}")
        return {
            "status": "success",
            "to_email": to_email,
        }

    except EmailConfigurationError as e:
        # Configuration error - don't retry, it won't help
        logger.error(
            f"Email configuration error for verification to {to_email}: {str(e)}"
        )
        return {
            "status": "failed",
            "reason": "configuration_error",
            "error": str(e),
            "to_email": to_email,
        }

    except EmailDeliveryError as e:
        # Delivery error - retry with exponential backoff
        logger.warning(
            f"Email delivery failed for verification to {to_email} "
            f"(attempt {self.request.retries + 1}/{self.max_retries}): {str(e)}"
        )
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    except Exception as e:
        # Unexpected error - still retry with backoff
        logger.error(
            f"Unexpected error sending verification email to {to_email} "
            f"(attempt {self.request.retries + 1}/{self.max_retries}): {str(e)}"
        )
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def send_welcome_email_task(
    self: Task,
    to_email: str,
    login_url: str,
    user_name: str | None = None,
    tenant_name: str | None = None,
) -> dict:
    """
    Send a welcome email to a newly registered user.

    Retries up to 5 times with exponential backoff if email delivery fails.
    Retry delays: 60s, 120s, 240s, 480s, 960s (16 minutes max)

    Args:
        to_email: Email address of the user
        login_url: URL for logging in
        user_name: Optional user's name for personalization
        tenant_name: Optional tenant/organization name

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
                f"SMTP not configured - skipping welcome email to {to_email}"
            )
            return {
                "status": "skipped",
                "reason": "SMTP not configured",
                "to_email": to_email,
            }

        # Send the welcome email (async operation)
        asyncio.run(
            email_service.send_welcome_email(
                to_email=to_email,
                login_url=login_url,
                user_name=user_name,
                tenant_name=tenant_name,
            )
        )

        logger.info(f"Successfully sent welcome email to {to_email}")
        return {
            "status": "success",
            "to_email": to_email,
        }

    except EmailConfigurationError as e:
        # Configuration error - don't retry, it won't help
        logger.error(
            f"Email configuration error for welcome email to {to_email}: {str(e)}"
        )
        return {
            "status": "failed",
            "reason": "configuration_error",
            "error": str(e),
            "to_email": to_email,
        }

    except EmailDeliveryError as e:
        # Delivery error - retry with exponential backoff
        logger.warning(
            f"Email delivery failed for welcome email to {to_email} "
            f"(attempt {self.request.retries + 1}/{self.max_retries}): {str(e)}"
        )
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    except Exception as e:
        # Unexpected error - still retry with backoff
        logger.error(
            f"Unexpected error sending welcome email to {to_email} "
            f"(attempt {self.request.retries + 1}/{self.max_retries}): {str(e)}"
        )
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
