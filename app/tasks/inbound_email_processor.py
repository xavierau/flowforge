"""Celery task for processing inbound emails."""

import logging
import os
import re
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Optional
from uuid import UUID
import uuid

from celery import Task

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models.inbound_email import InboundEmailAddress, InboundEmailLog
from app.models.document import Document
from app.models.extraction_job import ExtractionJob
from app.models.schema_definition import SchemaDefinition
from app.models.tenant import Tenant
from app.models.enums import InboundEmailLogStatus, DocumentStatus
from app.services.storage import get_storage_service
from app.config import settings

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """
    Safely sanitize filename to prevent path traversal attacks.

    This function:
    1. Extracts just the basename (removes any path components)
    2. Removes dangerous characters that could be used in path traversal
    3. Prevents hidden files (starting with .)
    4. Limits filename length to 255 characters

    Args:
        filename: The original filename from the email attachment

    Returns:
        A sanitized filename safe for use in file paths
    """
    # Get just the filename, strip any path components (prevents ../ attacks)
    basename = os.path.basename(filename)

    # Remove any remaining dangerous characters, keeping only safe ones
    safe = re.sub(r"[^\w\-_\.]", "_", basename)

    # Prevent empty filenames or hidden files (starting with .)
    if not safe or safe.startswith("."):
        safe = "attachment_" + safe

    # Limit length to 255 characters (common filesystem limit)
    return safe[:255]


def _is_sender_allowed(sender_email: str, allowed_senders: Optional[List[str]]) -> bool:
    """
    Check if sender is allowed based on whitelist patterns.

    Args:
        sender_email: The sender's email address
        allowed_senders: List of allowed patterns (email or *@domain)

    Returns:
        True if allowed (or no whitelist configured), False otherwise
    """
    if not allowed_senders:
        return True  # No whitelist = allow all

    sender_lower = sender_email.lower().strip()

    for pattern in allowed_senders:
        pattern_lower = pattern.lower().strip()

        if pattern_lower.startswith("*@"):
            # Domain pattern: *@example.com
            domain = pattern_lower[2:]
            if sender_lower.endswith(f"@{domain}"):
                return True
        elif sender_lower == pattern_lower:
            # Exact email match
            return True

    return False


def _parse_attachments_from_raw_email(raw_email: str) -> List[Dict]:
    """
    Parse attachments from raw MIME email content.

    Args:
        raw_email: Raw MIME email string

    Returns:
        List of attachment dicts with filename, content_type, and payload
    """
    attachments = []

    if not raw_email:
        return attachments

    try:
        # Use mailparser to parse the raw email
        import mailparser
        parsed = mailparser.parse_from_string(raw_email)

        for attachment in parsed.attachments or []:
            filename = attachment.get("filename", "")
            content_type = attachment.get("mail_content_type", "application/octet-stream")
            payload = attachment.get("payload", b"")

            # Handle base64-encoded payloads
            if isinstance(payload, str):
                import base64
                try:
                    payload = base64.b64decode(payload)
                except Exception:
                    payload = payload.encode("utf-8")

            if filename and payload:
                attachments.append({
                    "filename": filename,
                    "content_type": content_type,
                    "payload": payload,
                    "size": len(payload),
                })
    except ImportError:
        logger.warning("mailparser not installed, trying email.parser fallback")
        # Fallback to standard library
        import email
        from email import policy

        try:
            msg = email.message_from_string(raw_email, policy=policy.default)

            for part in msg.walk():
                content_disposition = part.get("Content-Disposition", "")
                if "attachment" in content_disposition:
                    filename = part.get_filename() or "attachment"
                    content_type = part.get_content_type()
                    payload = part.get_payload(decode=True)

                    if payload:
                        attachments.append({
                            "filename": filename,
                            "content_type": content_type,
                            "payload": payload,
                            "size": len(payload),
                        })
        except Exception as e:
            logger.error(f"Error parsing email with stdlib: {e}")
    except Exception as e:
        logger.error(f"Error parsing attachments: {e}", exc_info=True)

    return attachments


def _filter_valid_attachments(attachments: List[Dict]) -> List[Dict]:
    """
    Filter attachments to only include valid file types and sizes.

    Args:
        attachments: List of attachment dicts

    Returns:
        Filtered list of valid attachments
    """
    # Valid MIME types for document processing
    valid_types = {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/tiff",
        "image/webp",
    }

    max_size = settings.max_email_attachment_size_mb * 1024 * 1024

    valid = []
    for attachment in attachments:
        content_type = attachment.get("content_type", "").lower()
        size = attachment.get("size", 0)

        # Check file type
        if content_type not in valid_types:
            logger.debug(f"Skipping attachment with invalid type: {content_type}")
            continue

        # Check file size
        if size > max_size:
            logger.debug(f"Skipping attachment exceeding size limit: {size} > {max_size}")
            continue

        valid.append(attachment)

    return valid


async def _send_insufficient_credits_bounce(
    sender_email: str,
    tenant_name: str,
    subject: Optional[str],
) -> None:
    """Send bounce-back email when tenant has insufficient credits."""
    try:
        from app.services.email_service import EmailService

        email_service = EmailService()
        if not email_service.is_configured():
            logger.warning("Email service not configured - cannot send bounce email")
            return

        # Send bounce email
        await email_service._send_email(
            to_email=sender_email,
            subject="Document Processing Failed - Insufficient Credits",
            html_content=f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 4px; }}
        .content {{ padding: 20px 0; }}
        .footer {{ font-size: 12px; color: #666; border-top: 1px solid #ddd; padding-top: 15px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="margin: 0;">Document Processing Failed</h2>
        </div>
        <div class="content">
            <p>Your email to <strong>{tenant_name}</strong> could not be processed due to insufficient credits.</p>
            <p><strong>Original Subject:</strong> {subject or 'No subject'}</p>
            <p>Please contact the organization administrator to add more processing credits.</p>
        </div>
        <div class="footer">
            <p>This is an automated message from AI Document Processing.</p>
        </div>
    </div>
</body>
</html>
            """,
            text_content=f"""
Document Processing Failed

Your email to {tenant_name} could not be processed due to insufficient credits.

Original Subject: {subject or 'No subject'}

Please contact the organization administrator to add more processing credits.

---
This is an automated message from AI Document Processing.
            """,
        )
        logger.info(f"Sent insufficient credits bounce to {sender_email}")
    except Exception as e:
        logger.error(f"Failed to send bounce email: {e}")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_inbound_email(
    self: Task,
    log_id: str,
    inbound_email_address_id: str,
    raw_email: str,
    form_data: Dict,
) -> Dict:
    """
    Process an inbound email asynchronously.

    Steps:
    1. Validate address is active
    2. Validate sender against whitelist (if configured)
    3. Parse attachments from raw email
    4. Filter valid attachments (type/size)
    5. Check tenant credits
    6. If insufficient credits → send bounce email, update log
    7. For each valid attachment:
       - Upload to storage
       - Create Document record
       - Create ExtractionJob with configured settings
       - Queue extraction task
    8. Update log with document_ids and job_ids
    9. Update address statistics

    Args:
        log_id: UUID of the InboundEmailLog entry
        inbound_email_address_id: UUID of the InboundEmailAddress
        raw_email: Raw MIME email content
        form_data: Metadata from SendGrid (from, to, subject, etc.)

    Returns:
        Dict with processing status and results
    """
    db = SessionLocal()
    storage_service = get_storage_service()

    try:
        log_uuid = UUID(log_id)
        address_uuid = UUID(inbound_email_address_id)

        # Load email log
        email_log = db.query(InboundEmailLog).filter(InboundEmailLog.id == log_uuid).first()
        if not email_log:
            raise ValueError(f"Email log {log_id} not found")

        # Load inbound email address
        inbound_address = (
            db.query(InboundEmailAddress)
            .filter(InboundEmailAddress.id == address_uuid)
            .first()
        )
        if not inbound_address:
            email_log.status = InboundEmailLogStatus.FAILED.value
            email_log.error_message = "Inbound email address not found"
            email_log.processed_at = datetime.utcnow()
            db.commit()
            raise ValueError(f"Inbound email address {inbound_email_address_id} not found")

        # Step 1: Check if address is active
        if not inbound_address.is_active:
            email_log.status = InboundEmailLogStatus.REJECTED_INACTIVE.value
            email_log.error_message = "Inbound email address is deactivated"
            email_log.processed_at = datetime.utcnow()
            db.commit()
            logger.info(f"Rejected email - address inactive: {inbound_address.id}")
            return {"status": "rejected", "reason": "inactive_address"}

        # Step 2: Validate sender against whitelist
        if not _is_sender_allowed(email_log.sender_email, inbound_address.allowed_senders):
            email_log.status = InboundEmailLogStatus.REJECTED_SENDER.value
            email_log.error_message = f"Sender {email_log.sender_email} not in whitelist"
            email_log.processed_at = datetime.utcnow()
            db.commit()
            logger.info(f"Rejected email from {email_log.sender_email} - not in whitelist")
            return {"status": "rejected", "reason": "sender_not_allowed"}

        # Step 3: Parse attachments from raw email
        attachments = _parse_attachments_from_raw_email(raw_email)

        # Step 4: Filter valid attachments
        valid_attachments = _filter_valid_attachments(attachments)

        if not valid_attachments:
            email_log.status = InboundEmailLogStatus.REJECTED_NO_ATTACHMENTS.value
            email_log.error_message = "No valid attachments found (check file types and sizes)"
            email_log.processed_at = datetime.utcnow()
            db.commit()
            logger.info(f"Rejected email - no valid attachments")
            return {"status": "rejected", "reason": "no_valid_attachments"}

        # Step 5: Check tenant credits
        tenant = db.query(Tenant).filter(Tenant.id == inbound_address.tenant_id).first()
        if not tenant:
            email_log.status = InboundEmailLogStatus.FAILED.value
            email_log.error_message = "Tenant not found"
            email_log.processed_at = datetime.utcnow()
            db.commit()
            raise ValueError("Tenant not found")

        # Estimate credits needed (1 per attachment initially, actual count after PDF processing)
        estimated_credits = len(valid_attachments)

        if tenant.cached_balance < estimated_credits:
            email_log.status = InboundEmailLogStatus.REJECTED_NO_CREDITS.value
            email_log.error_message = f"Insufficient credits: {tenant.cached_balance} < {estimated_credits}"
            email_log.processed_at = datetime.utcnow()
            db.commit()

            # Send bounce email to sender (run in event loop)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            loop.run_until_complete(_send_insufficient_credits_bounce(
                sender_email=email_log.sender_email,
                tenant_name=tenant.name,
                subject=email_log.subject,
            ))

            logger.info(f"Rejected email - insufficient credits: {tenant.cached_balance} < {estimated_credits}")
            return {"status": "rejected", "reason": "insufficient_credits"}

        # Step 6-7: Process attachments
        document_ids = []
        extraction_job_ids = []

        for attachment in valid_attachments:
            # Generate unique file path
            file_uuid = str(uuid.uuid4())
            safe_filename = sanitize_filename(attachment["filename"])
            file_path = f"documents/inbound/{file_uuid}/{safe_filename}"

            # Upload to storage
            file_buffer = BytesIO(attachment["payload"])
            storage_service.backend.upload_sync(file_buffer, file_path)

            # Determine document status based on type
            is_pdf = attachment["content_type"] == "application/pdf"
            initial_status = DocumentStatus.UPLOADED.value if is_pdf else DocumentStatus.READY_FOR_EXTRACTION.value

            # Create document record
            document = Document(
                tenant_id=inbound_address.tenant_id,
                filename=attachment["filename"],
                mime_type=attachment["content_type"],
                size_bytes=attachment["size"],
                file_path=file_path,
                status=initial_status,
                page_count=1 if not is_pdf else None,  # Will be updated after PDF processing
                document_metadata={
                    "source": "inbound_email",
                    "inbound_email_address_id": str(inbound_address.id),
                    "inbound_email_log_id": str(email_log.id),
                    "sender_email": email_log.sender_email,
                    "original_subject": email_log.subject,
                },
            )

            db.add(document)
            db.flush()  # Get document ID
            document_ids.append(str(document.id))

            # Resolve extraction schema
            final_schema = inbound_address.extraction_schema
            if inbound_address.schema_definition_id:
                schema_def = (
                    db.query(SchemaDefinition)
                    .filter(SchemaDefinition.id == inbound_address.schema_definition_id)
                    .first()
                )
                if schema_def:
                    final_schema = schema_def.definitions

            if not final_schema:
                logger.warning(f"No extraction schema found for inbound address {inbound_address.id}")
                continue

            # Create extraction job
            job = ExtractionJob(
                document_id=document.id,
                tenant_id=inbound_address.tenant_id,
                schema_definition_id=inbound_address.schema_definition_id,
                extraction_schema=final_schema,
                custom_prompt=inbound_address.custom_prompt,
                model_provider=inbound_address.model_provider,
                model_name=inbound_address.model_name,
                split_mode=inbound_address.split_mode,
                extraction_mode=inbound_address.extraction_mode,
                processing_mode=inbound_address.split_mode,  # Backward compat
                markdown_converter=inbound_address.markdown_converter,
                markdown_format=inbound_address.markdown_format,
                callback_url=inbound_address.callback_url,
                llamaextract_mode=inbound_address.llamaextract_mode,
                llamaextract_target=inbound_address.llamaextract_target,
                status="queued",
                credits_cost=1,  # Will be updated after PDF processing
                source="api",  # Inbound email is programmatic access
            )

            db.add(job)
            db.flush()  # Get job ID
            extraction_job_ids.append(str(job.id))

            logger.info(f"Created document {document.id} and job {job.id} from inbound email")

        # Commit all documents and jobs
        db.commit()

        # Step 8: Update email log with results
        email_log.status = InboundEmailLogStatus.PROCESSED.value
        email_log.document_ids = document_ids
        email_log.extraction_job_ids = extraction_job_ids
        email_log.processed_at = datetime.utcnow()

        # Step 9: Update address statistics (atomic update to prevent race conditions)
        db.query(InboundEmailAddress).filter(
            InboundEmailAddress.id == address_uuid
        ).update({
            InboundEmailAddress.emails_received_count: InboundEmailAddress.emails_received_count + 1,
            InboundEmailAddress.documents_processed_count: InboundEmailAddress.documents_processed_count + len(document_ids),
            InboundEmailAddress.last_email_at: datetime.utcnow()
        }, synchronize_session=False)

        db.commit()

        # Queue extraction tasks for each job (batch query to avoid N+1)
        if extraction_job_ids:
            jobs_with_docs = (
                db.query(ExtractionJob, Document)
                .join(Document, ExtractionJob.document_id == Document.id)
                .filter(ExtractionJob.id.in_([UUID(jid) for jid in extraction_job_ids]))
                .all()
            )

            for job, document in jobs_with_docs:
                job_id = str(job.id)
                is_pdf = document.mime_type == "application/pdf"

                if is_pdf:
                    # PDF needs processing first
                    from app.tasks.combined_extraction import process_document_and_extract
                    process_document_and_extract.delay(job_id)
                else:
                    # Image can go straight to extraction
                    from app.tasks.extractor import process_extraction_job
                    process_extraction_job.delay(job_id)

                logger.info(f"Queued extraction task for job {job_id}")

        logger.info(
            f"Processed inbound email: log_id={log_id}, "
            f"documents={len(document_ids)}, jobs={len(extraction_job_ids)}"
        )

        return {
            "status": "processed",
            "document_ids": document_ids,
            "extraction_job_ids": extraction_job_ids,
        }

    except Exception as e:
        logger.error(f"Error processing inbound email {log_id}: {e}", exc_info=True)
        db.rollback()

        # Update log status to failed
        try:
            email_log = db.query(InboundEmailLog).filter(InboundEmailLog.id == UUID(log_id)).first()
            if email_log and email_log.status == InboundEmailLogStatus.RECEIVED.value:
                email_log.status = InboundEmailLogStatus.FAILED.value
                email_log.error_message = str(e)
                email_log.processed_at = datetime.utcnow()
                db.commit()
        except Exception as log_error:
            logger.error(f"Failed to update log status: {log_error}")

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        else:
            raise

    finally:
        db.close()
