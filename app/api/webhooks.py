"""Webhook endpoints for external service integrations."""

import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.dependencies.rate_limit import limiter
from app.models.inbound_email import InboundEmailAddress, InboundEmailLog
from app.models.enums import InboundEmailLogStatus

router = APIRouter()
logger = logging.getLogger(__name__)


def verify_sendgrid_signature(request: Request, body: bytes) -> bool:
    """
    Verify SendGrid webhook signature.

    SendGrid signs webhooks using HMAC-SHA256 with the timestamp and body.
    See: https://docs.sendgrid.com/for-developers/tracking-events/getting-started-event-webhook-security-features

    Args:
        request: The FastAPI request object
        body: The raw request body bytes

    Returns:
        True if signature is valid or verification is disabled, False otherwise
    """
    if not settings.inbound_email_webhook_secret:
        logger.warning("Webhook secret not configured - skipping verification")
        return True  # Allow in development

    signature = request.headers.get("X-Twilio-Email-Event-Webhook-Signature")
    timestamp = request.headers.get("X-Twilio-Email-Event-Webhook-Timestamp")

    if not signature or not timestamp:
        logger.warning("Missing webhook signature or timestamp headers")
        return False

    # Construct the signed payload: timestamp + body
    payload = timestamp + body.decode("utf-8")

    # Compute expected signature
    expected = hmac.new(
        settings.inbound_email_webhook_secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(signature, expected)


@router.post(
    "/webhooks/sendgrid/inbound",
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    responses={
        200: {
            "description": "Email received and queued for processing",
            "content": {
                "application/json": {
                    "example": {"status": "queued", "log_id": "550e8400-e29b-41d4-a716-446655440000"}
                }
            }
        }
    }
)
@limiter.limit("100/minute")
async def sendgrid_inbound_email_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handle incoming emails from SendGrid Inbound Parse webhook.

    This endpoint:
    1. Verifies SendGrid webhook signature (if configured)
    2. Parses the multipart form data from SendGrid
    3. Extracts recipient email to find InboundEmailAddress
    4. Creates an InboundEmailLog entry
    5. Queues async processing via Celery
    6. Returns 200 OK immediately (required by SendGrid)

    Rate limited to 100 requests per minute.
    Webhook verification via HMAC signature when secret is configured.

    SendGrid Inbound Parse sends:
    - to, from, subject: Email headers
    - envelope: JSON with actual recipients
    - email: Raw MIME content
    - SPF, dkim, spam_score, sender_ip: Security metadata
    - attachmentX: File attachments (multipart)
    """
    try:
        # Verify webhook signature if secret is configured
        body = await request.body()
        if not verify_sendgrid_signature(request, body):
            logger.warning("Invalid webhook signature - rejecting request")
            return JSONResponse(
                content={"status": "error", "message": "Invalid signature"},
                status_code=200  # Return 200 to prevent retries
            )

        # Parse multipart form data
        form = await request.form()

        # Extract email data from SendGrid format
        to_email = form.get("to", "")
        from_email = form.get("from", "")
        subject = form.get("subject", "")
        envelope_raw = form.get("envelope", "{}")
        raw_email = form.get("email", "")
        headers = form.get("headers", "")

        # Parse envelope for actual recipients
        try:
            envelope = json.loads(envelope_raw) if envelope_raw else {}
            # SendGrid envelope format: {"to":["uuid@domain"],"from":"sender@example.com"}
            recipients = envelope.get("to", [])
        except json.JSONDecodeError:
            recipients = [to_email] if to_email else []

        # Find recipient that matches our inbound domain
        inbound_email_address: Optional[InboundEmailAddress] = None
        recipient_email: Optional[str] = None
        email_prefix: Optional[str] = None

        for recipient in recipients:
            recipient_lower = recipient.lower().strip()
            if f"@{settings.inbound_email_domain.lower()}" in recipient_lower:
                recipient_email = recipient_lower
                # Extract prefix (UUID) from email
                email_prefix = recipient_lower.split("@")[0]

                # Look up inbound email address by prefix
                inbound_email_address = (
                    db.query(InboundEmailAddress)
                    .filter(InboundEmailAddress.email_prefix == email_prefix)
                    .first()
                )
                if inbound_email_address:
                    break

        if not inbound_email_address:
            # Log unknown recipient and return 200 (don't trigger SendGrid retry)
            logger.warning(f"Unknown inbound email recipient: {recipient_email or to_email}")
            return JSONResponse(
                content={"status": "ignored", "reason": "unknown_recipient"},
                status_code=200
            )

        # Extract sender info (parse "Name <email@domain.com>" format)
        sender_email = ""
        sender_name = ""
        if from_email:
            if "<" in from_email and ">" in from_email:
                sender_name = from_email.split("<")[0].strip().strip('"')
                sender_email = from_email.split("<")[1].split(">")[0].strip()
            else:
                sender_email = from_email.strip()

        # Extract attachment info from multipart files
        attachment_files = []
        total_size = 0
        for key in form.keys():
            if key.startswith("attachment"):
                file = form[key]
                if hasattr(file, "filename") and file.filename:
                    file_size = 0
                    if hasattr(file, "size"):
                        file_size = file.size
                    elif hasattr(file, "file"):
                        # Try to get size from file object
                        try:
                            file.file.seek(0, 2)
                            file_size = file.file.tell()
                            file.file.seek(0)
                        except Exception:
                            pass

                    attachment_files.append({
                        "filename": file.filename,
                        "content_type": getattr(file, "content_type", "application/octet-stream"),
                        "size": file_size,
                    })
                    total_size += file_size

        # Extract Message-ID from headers
        message_id = None
        if headers and "Message-ID:" in headers:
            try:
                message_id = headers.split("Message-ID:")[1].split("\n")[0].strip().strip("<>")
            except Exception:
                pass

        # Build raw metadata for debugging
        raw_metadata = {
            "spf": form.get("SPF"),
            "dkim": form.get("dkim"),
            "spam_score": form.get("spam_score"),
            "sender_ip": form.get("sender_ip"),
            "message_id": message_id,
            "charsets": form.get("charsets"),
        }

        # Create log entry immediately (status=received)
        email_log = InboundEmailLog(
            inbound_email_address_id=inbound_email_address.id,
            sender_email=sender_email or "unknown",
            sender_name=sender_name or None,
            subject=subject[:1000] if subject else None,
            message_id=message_id,
            status=InboundEmailLogStatus.RECEIVED.value,
            attachment_count=len(attachment_files),
            attachment_names=[f["filename"] for f in attachment_files] if attachment_files else None,
            total_attachment_size_bytes=total_size if total_size > 0 else None,
            raw_metadata=raw_metadata,
        )

        db.add(email_log)
        db.commit()
        db.refresh(email_log)

        # Queue async processing task
        from app.tasks.inbound_email_processor import process_inbound_email

        # Prepare form data as serializable dict (exclude file contents for task params)
        form_data = {
            "from": from_email,
            "to": to_email,
            "subject": subject,
            "envelope": envelope_raw,
            "spf": form.get("SPF"),
            "dkim": form.get("dkim"),
            "spam_score": form.get("spam_score"),
            "sender_ip": form.get("sender_ip"),
        }

        process_inbound_email.delay(
            log_id=str(email_log.id),
            inbound_email_address_id=str(inbound_email_address.id),
            raw_email=raw_email,
            form_data=form_data,
        )

        logger.info(
            f"Queued inbound email processing: log_id={email_log.id}, "
            f"address_id={inbound_email_address.id}, sender={sender_email}, "
            f"attachments={len(attachment_files)}"
        )

        # Return 200 OK immediately (SendGrid requirement)
        return JSONResponse(
            content={"status": "queued", "log_id": str(email_log.id)},
            status_code=200
        )

    except Exception as e:
        logger.error(f"Error processing SendGrid inbound webhook: {e}", exc_info=True)
        # Still return 200 to prevent SendGrid retries on our errors
        # Do not expose internal error details to prevent information leakage
        return JSONResponse(
            content={"status": "error", "message": "Internal processing error"},
            status_code=200
        )
