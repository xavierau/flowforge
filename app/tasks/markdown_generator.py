"""Markdown generation tasks for image-to-markdown conversion.

Converts document page images to markdown format using vision models.
Supports both single-page and batch processing modes with caching.
"""

import asyncio
import base64
from datetime import datetime
from typing import Dict, List
from uuid import UUID
from celery import Task
import logging

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import Document, DocumentPage
from app.models.enums import MarkdownFormat
from app.services.storage import get_storage_service
from app.services.converters import get_converter_factory

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_markdown_from_images(
    self: Task,
    document_id: str,
    converter_name: str = "qwen_vision",
    options: Dict = None,
) -> Dict:
    """Generate markdown from document page images.

    Converts images to markdown using the specified converter. Supports both
    single-page and batch processing modes. Caches results in database.

    Args:
        self: Celery task instance
        document_id: Document UUID as string
        converter_name: Converter to use (default: qwen_vision)
        options: Optional conversion options dict with keys:
            - format_style: Markdown format (standard, table_heavy, layout_preserved)
            - mode: Processing mode (single or batch)

    Returns:
        Dictionary with generation results:
        {
            "document_id": str,
            "status": "success",
            "pages_processed": int,
            "total_tokens": int
        }

    Raises:
        Exception: On conversion failure (triggers Celery retry)
    """
    db = SessionLocal()
    storage = get_storage_service()

    try:
        # Set default options if None
        if options is None:
            options = {}

        # Get document
        doc_uuid = UUID(document_id)
        document = db.query(Document).filter(Document.id == doc_uuid).first()

        if not document:
            raise ValueError(f"Document {document_id} not found")

        # Get converter
        factory = get_converter_factory()
        converter = factory.get_markdown_converter(converter_name)

        # Get format style from options
        format_style = options.get("format_style", MarkdownFormat.STANDARD.value)
        mode = options.get("mode", "batch")

        # Get all pages ordered by page number
        pages = (
            db.query(DocumentPage)
            .filter(DocumentPage.document_id == doc_uuid)
            .order_by(DocumentPage.page_number)
            .all()
        )

        if not pages:
            raise ValueError(f"No pages found for document {document_id}")

        # Check for cached markdown (skip if already generated)
        cached_count = sum(1 for p in pages if p.markdown_content is not None)
        if cached_count == len(pages):
            logger.info(
                f"All {len(pages)} pages already have markdown cached, skipping generation"
            )
            return {
                "document_id": document_id,
                "status": "cached",
                "pages_processed": len(pages),
                "total_tokens": 0,
            }

        total_input_tokens = 0
        total_output_tokens = 0

        if mode == "batch":
            # BATCH MODE: Convert all pages in one call
            logger.info(
                f"Starting batch markdown conversion for {len(pages)} pages "
                f"(converter: {converter_name}, format: {format_style})"
            )

            # Load all page images (prefer preprocessed)
            images_base64 = []
            for page in pages:
                image_path = page.preprocessed_image_path or page.image_path
                image_bytes = storage.download_file_sync(image_path)
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                images_base64.append(image_base64)

            # Convert all pages in one call
            result = asyncio.run(
                converter.convert_batch(
                    images_base64=images_base64,
                    format_style=format_style,
                )
            )

            # Use page_results if available (new parallel implementation)
            # Otherwise fall back to regex-based splitting (old batch implementation)
            if result.page_results:
                logger.info(
                    f"Using structured page_results from parallel processing "
                    f"({len(result.page_results)} pages)"
                )

                # Store markdown directly from page_results
                for page_result in result.page_results:
                    page_num = page_result["page"]
                    content = page_result["markdown"]

                    # Find corresponding page
                    page = next((p for p in pages if p.page_number == page_num), None)
                    if page:
                        page.markdown_content = content
                        page.markdown_provider = converter_name
                        page.markdown_generated_at = datetime.utcnow()

                        # Save markdown to local filesystem
                        markdown_filename = f"page_{page.page_number}.md"
                        markdown_path = storage.upload_bytes_sync(
                            content.encode('utf-8'),
                            markdown_filename,
                            prefix=f"markdown/{document_id}"
                        )
                        logger.info(f"Saved markdown for page {page.page_number} to {markdown_path}")

                total_input_tokens = result.input_tokens
                total_output_tokens = result.output_tokens

                logger.info(
                    f"Batch markdown conversion completed: {len(result.page_results)} pages, "
                    f"tokens: {total_input_tokens}+{total_output_tokens}"
                )

            else:
                # FALLBACK: Split markdown by page markers (legacy behavior)
                logger.info("Using legacy regex-based page marker splitting")

                markdown_content = result.markdown_content
                page_sections = []

                # Split by page markers (<!-- PAGE N -->)
                import re

                page_pattern = r"<!-- PAGE (\d+) -->"
                splits = re.split(page_pattern, markdown_content)

                # Reconstruct page-wise content
                # splits will be like: ["", "1", "content1", "2", "content2", ...]
                if len(splits) > 1:
                    for i in range(1, len(splits), 2):
                        if i + 1 < len(splits):
                            page_num = int(splits[i])
                            content = splits[i + 1].strip()
                            page_sections.append((page_num, content))
                else:
                    # No page markers found, treat as single page
                    page_sections = [(1, markdown_content)]

                # Store markdown for each page
                for page_num, content in page_sections:
                    # Find corresponding page
                    page = next((p for p in pages if p.page_number == page_num), None)
                    if page:
                        page.markdown_content = content
                        page.markdown_provider = converter_name
                        page.markdown_generated_at = datetime.utcnow()

                        # Save markdown to local filesystem
                        markdown_filename = f"page_{page.page_number}.md"
                        markdown_path = storage.upload_bytes_sync(
                            content.encode('utf-8'),
                            markdown_filename,
                            prefix=f"markdown/{document_id}"
                        )
                        logger.info(f"Saved markdown for page {page.page_number} to {markdown_path}")

                total_input_tokens = result.input_tokens
                total_output_tokens = result.output_tokens

                logger.info(
                    f"Batch markdown conversion completed: {len(page_sections)} pages, "
                    f"tokens: {total_input_tokens}+{total_output_tokens}"
                )

        else:
            # SINGLE MODE: Convert each page separately
            logger.info(
                f"Starting per-page markdown conversion for {len(pages)} pages "
                f"(converter: {converter_name}, format: {format_style})"
            )

            for page in pages:
                # Skip if already has markdown
                if page.markdown_content:
                    logger.debug(f"Page {page.page_number} already has markdown, skipping")
                    continue

                # Load image (prefer preprocessed)
                image_path = page.preprocessed_image_path or page.image_path
                image_bytes = storage.download_file_sync(image_path)
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")

                # Convert to markdown
                result = asyncio.run(
                    converter.convert_single(
                        image_base64=image_base64,
                        format_style=format_style,
                        page_number=page.page_number,
                    )
                )

                # Store markdown
                page.markdown_content = result.markdown_content
                page.markdown_provider = converter_name
                page.markdown_generated_at = datetime.utcnow()

                # Save markdown to local filesystem
                markdown_filename = f"page_{page.page_number}.md"
                markdown_path = storage.upload_bytes_sync(
                    result.markdown_content.encode('utf-8'),
                    markdown_filename,
                    prefix=f"markdown/{document_id}"
                )
                logger.info(f"Saved markdown for page {page.page_number} to {markdown_path}")

                total_input_tokens += result.input_tokens
                total_output_tokens += result.output_tokens

                logger.debug(
                    f"Converted page {page.page_number} to markdown "
                    f"(tokens: {result.input_tokens}+{result.output_tokens})"
                )

            logger.info(
                f"Per-page markdown conversion completed: {len(pages)} pages, "
                f"tokens: {total_input_tokens}+{total_output_tokens}"
            )

        # Commit all changes
        db.commit()

        return {
            "document_id": document_id,
            "status": "success",
            "pages_processed": len(pages),
            "total_tokens": total_input_tokens + total_output_tokens,
        }

    except Exception as e:
        db.rollback()

        # Check if we should retry
        if self.request.retries < self.max_retries:
            logger.warning(
                f"Markdown generation for document {document_id} failed "
                f"(attempt {self.request.retries + 1}/{self.max_retries}): {str(e)}"
            )
            db.close()
            # Retry with exponential backoff: 60s, 120s, 240s
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        else:
            # All retries exhausted - mark related extraction jobs as failed and refund credits
            from app.utils.job_failure_handler import mark_jobs_failed_for_document

            mark_jobs_failed_for_document(
                db=db,
                document_id=document_id,
                error=e,
                max_retries=self.max_retries,
                failure_context="Markdown generation",
            )

            raise

    finally:
        db.close()
