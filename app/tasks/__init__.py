"""Celery tasks for async document processing."""

from app.tasks.celery_app import celery_app
from app.tasks.pdf_processor import pdf_to_images
from app.tasks.extractor import process_extraction_job, extract_from_page
from app.tasks.combined_extraction import process_document_and_extract

__all__ = [
    "celery_app",
    "pdf_to_images",
    "process_extraction_job",
    "extract_from_page",
    "process_document_and_extract",
]
