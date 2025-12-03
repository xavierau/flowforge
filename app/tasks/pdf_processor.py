"""PDF to images conversion task."""

import io
import logging
from uuid import UUID
from celery import Task
from pdf2image import convert_from_bytes
from PIL import Image

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import Document, DocumentPage
from app.services.storage import get_storage_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def pdf_to_images(self: Task, document_id: str) -> dict:
    """
    Convert PDF pages to images.

    Args:
        document_id: Document UUID as string

    Returns:
        Dictionary with conversion results
    """
    logger.info(f"Starting PDF to images conversion for document: {document_id}")

    db = SessionLocal()
    storage = get_storage_service()
    document = None

    try:
        # Get document
        logger.info(f"Fetching document {document_id} from database")
        doc_uuid = UUID(document_id)
        document = db.query(Document).filter(Document.id == doc_uuid).first()

        if not document:
            logger.error(f"Document {document_id} not found in database")
            raise ValueError(f"Document {document_id} not found")

        logger.info(f"Document found - filename: {document.filename}, file_path: {document.file_path}")

        # Update status
        logger.info(f"Updating document {document_id} status to 'processing'")
        document.status = "processing"
        db.commit()

        # Download PDF from storage
        logger.info(f"Downloading PDF from storage: {document.file_path}")
        pdf_bytes = storage.download_file_sync(document.file_path)
        logger.info(f"PDF downloaded successfully - size: {len(pdf_bytes)} bytes")

        # Convert PDF to images
        logger.info("Converting PDF to images (DPI: 200, format: PNG)")
        images = convert_from_bytes(
            pdf_bytes,
            dpi=200,  # Good quality for OCR
            fmt="png",
        )
        logger.info(f"PDF conversion completed - total pages: {len(images)}")

        # Update page count
        document.page_count = len(images)
        db.commit()
        logger.info(f"Updated document page_count to {len(images)}")

        # Process each page
        page_ids = []
        for page_num, image in enumerate(images, start=1):
            logger.info(f"Processing page {page_num}/{len(images)}")

            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format="PNG")
            img_bytes = img_byte_arr.getvalue()
            logger.info(f"Page {page_num} image size: {len(img_bytes)} bytes")

            # Upload to storage
            filename = f"page_{page_num}.png"
            logger.info(f"Uploading page {page_num} to storage as {filename}")
            image_path = storage.upload_bytes_sync(
                img_bytes,
                filename=filename,
                prefix=f"pages/{document_id}",
            )
            logger.info(f"Page {page_num} uploaded to: {image_path}")

            # Create DocumentPage record
            page = DocumentPage(
                document_id=document.id,
                page_number=page_num,
                image_path=image_path,
                status="completed",
            )
            db.add(page)
            db.commit()
            db.refresh(page)
            logger.info(f"Page {page_num} record created with ID: {page.id}")

            page_ids.append(str(page.id))

        # Update document status
        logger.info(f"All pages processed successfully - updating document status to 'ready_for_extraction'")
        document.status = "ready_for_extraction"
        db.commit()

        result = {
            "document_id": document_id,
            "page_count": len(images),
            "page_ids": page_ids,
            "status": "success",
        }
        logger.info(f"PDF to images conversion completed successfully for document {document_id}: {result}")
        return result

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}", exc_info=True)

        # Update document status to failed
        if document:
            logger.info(f"Updating document {document_id} status to 'failed'")
            document.status = "failed"
            db.commit()

        # Retry on failure
        retry_count = self.request.retries
        logger.warning(f"Retrying task for document {document_id} (attempt {retry_count + 1}/{self.max_retries})")
        raise self.retry(exc=e)

    finally:
        db.close()
        logger.info(f"Database session closed for document {document_id}")
