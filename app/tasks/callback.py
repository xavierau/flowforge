"""Callback notification tasks."""

import logging
from celery import Task
import httpx

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def send_extraction_callback(
    self: Task,
    callback_url: str,
    callback_data: dict,
) -> None:
    """
    Send HTTP POST callback with extraction results.

    Retries up to 5 times with exponential backoff if callback fails.
    Retry delays: 60s, 120s, 240s, 480s, 960s (16 minutes max)

    Args:
        callback_url: URL to POST the results to
        callback_data: Dictionary containing the extraction results
    """
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                callback_url,
                json={"data": callback_data},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            logger.info(f"Successfully sent callback to {callback_url}")
    except httpx.HTTPError as e:
        logger.warning(
            f"Callback failed to {callback_url} "
            f"(attempt {self.request.retries + 1}/{self.max_retries}): {str(e)}"
        )
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    except Exception as e:
        logger.error(f"Unexpected error sending callback to {callback_url}: {str(e)}")
        # Retry even on unexpected errors
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
