"""Celery tasks for async document processing."""

from app.tasks.celery_app import celery_app
from app.tasks.pdf_processor import pdf_to_images
from app.tasks.extractor import process_extraction_job, extract_from_page
from app.tasks.combined_extraction import process_document_and_extract
from app.tasks.email_tasks import (
    send_invitation_email_task,
    send_password_reset_email_task,
    send_verification_email_task,
    send_welcome_email_task,
)
from app.tasks.document_splitter import (
    process_split_job,
    analyze_document_boundaries,
    split_and_create_documents,
    split_and_extract,
)

__all__ = [
    "celery_app",
    "pdf_to_images",
    "process_extraction_job",
    "extract_from_page",
    "process_document_and_extract",
    "send_invitation_email_task",
    "send_password_reset_email_task",
    "send_verification_email_task",
    "send_welcome_email_task",
    # Document splitting tasks
    "process_split_job",
    "analyze_document_boundaries",
    "split_and_create_documents",
    "split_and_extract",
]
