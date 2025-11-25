"""Markdown pipeline orchestration tasks.

Orchestrates the two-stage markdown extraction pipeline:
1. Image → Markdown conversion (vision models)
2. Markdown → JSON extraction (text models)

Implements intelligent caching to skip markdown generation if already cached.
"""

from uuid import UUID
from celery import chain
import logging

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import ExtractionJob, DocumentPage
from app.models.enums import MarkdownFormat
from app.tasks.markdown_generator import generate_markdown_from_images
from app.tasks.markdown_extractor import extract_from_markdown

logger = logging.getLogger(__name__)


@celery_app.task
def process_markdown_extraction_pipeline(extraction_job_id: str) -> dict:
    """Orchestrate the markdown extraction pipeline.

    Entry point for markdown mode extraction jobs. Implements intelligent caching:
    - If markdown already exists: Skip generation, go directly to extraction
    - If not cached: Chain generation → extraction tasks

    Args:
        extraction_job_id: Extraction job UUID as string

    Returns:
        Dictionary with pipeline status:
        {
            "extraction_job_id": str,
            "status": "queued",
            "cache_hit": bool,
            "message": str
        }
    """
    db = SessionLocal()

    try:
        # Get job
        job_uuid = UUID(extraction_job_id)
        job = db.query(ExtractionJob).filter(ExtractionJob.id == job_uuid).first()

        if not job:
            logger.error(f"Job {extraction_job_id} not found")
            return {
                "extraction_job_id": extraction_job_id,
                "status": "error",
                "cache_hit": False,
                "message": "Job not found",
            }

        # Get document
        document = job.document

        # Check if markdown already exists (caching)
        pages = (
            db.query(DocumentPage)
            .filter(DocumentPage.document_id == document.id)
            .order_by(DocumentPage.page_number)
            .all()
        )

        if not pages:
            logger.error(f"No pages found for document {document.id}")
            return {
                "extraction_job_id": extraction_job_id,
                "status": "error",
                "cache_hit": False,
                "message": "No pages found",
            }

        # Check cache status
        pages_with_markdown = sum(1 for p in pages if p.markdown_content is not None)
        cache_hit = pages_with_markdown == len(pages)

        if cache_hit:
            # CACHE HIT: Markdown already exists, skip generation
            logger.info(
                f"Markdown cache hit for document {document.id} "
                f"({len(pages)} pages). Skipping generation."
            )

            # Go directly to extraction
            task = extract_from_markdown.delay(extraction_job_id)
            job.celery_task_id = task.id
            db.commit()

            logger.info(
                f"Queued markdown extraction (cache hit) for job {job.id}, "
                f"task_id: {task.id}"
            )

            return {
                "extraction_job_id": extraction_job_id,
                "status": "queued",
                "cache_hit": True,
                "message": f"Using cached markdown for {len(pages)} pages",
            }
        else:
            # CACHE MISS: Need to generate markdown first
            logger.info(
                f"Markdown cache miss for document {document.id} "
                f"({pages_with_markdown}/{len(pages)} pages cached). "
                f"Generating markdown."
            )

            # Prepare markdown generation options
            markdown_options = {
                "format_style": job.markdown_format or MarkdownFormat.TABLE_HEAVY.value,
                "mode": "batch",  # Always use batch mode for efficiency
            }

            # Chain tasks: generation → extraction
            # Use .si() (immutable signature) to pass arguments
            pipeline = chain(
                generate_markdown_from_images.si(
                    str(document.id),
                    markdown_options,
                    job.markdown_converter,
                ),
                extract_from_markdown.si(extraction_job_id),
            )

            # Execute pipeline
            result = pipeline.apply_async()

            # Store the chain task ID
            # Note: result.id is the ID of the first task in the chain
            job.celery_task_id = result.id
            db.commit()

            logger.info(
                f"Queued markdown pipeline (cache miss) for job {job.id}, "
                f"chain_id: {result.id}"
            )

            return {
                "extraction_job_id": extraction_job_id,
                "status": "queued",
                "cache_hit": False,
                "message": f"Generating markdown for {len(pages)} pages, then extracting",
            }

    except Exception as e:
        logger.error(f"Failed to queue markdown pipeline for job {extraction_job_id}: {e}")
        return {
            "extraction_job_id": extraction_job_id,
            "status": "error",
            "cache_hit": False,
            "message": str(e),
        }

    finally:
        db.close()
