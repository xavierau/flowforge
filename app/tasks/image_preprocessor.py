"""Image preprocessing task for document pages."""

import io
import tempfile
from uuid import UUID
from celery import Task
from PIL import Image
import logging

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import Document, DocumentPage
from app.services.storage import get_storage_service
from app.utils.image_utils import (
    remove_noise_from_pil_image,
    increase_contrast_from_pil_image,
    add_grid_to_pil_image,
)

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def preprocess_document_images(self: Task, document_id: str) -> dict:
    """
    Preprocess all images for a document using the optimal workflow:
    1. Remove noise (bilateral filter, medium strength)
    2. Increase contrast (simple method, factor 1.5)
    3. Add transparent grid overlay (20px, light gray)

    This preprocessing improves LLM extraction accuracy by:
    - Removing scan artifacts and noise
    - Enhancing text clarity
    - Adding visual structure with grid overlay

    Args:
        document_id: Document UUID as string

    Returns:
        Dictionary with preprocessing results
    """
    db = SessionLocal()
    storage = get_storage_service()

    try:
        # Get document
        doc_uuid = UUID(document_id)
        document = db.query(Document).filter(Document.id == doc_uuid).first()

        if not document:
            raise ValueError(f"Document {document_id} not found")

        logger.info(f"Starting image preprocessing for document {document_id}")

        # Get all pages for this document
        pages = (
            db.query(DocumentPage)
            .filter(DocumentPage.document_id == doc_uuid)
            .order_by(DocumentPage.page_number)
            .all()
        )

        if not pages:
            logger.warning(f"No pages found for document {document_id}")
            return {
                "document_id": document_id,
                "pages_processed": 0,
                "status": "success",
                "message": "No pages to preprocess"
            }

        preprocessed_count = 0

        # Process each page
        for page in pages:
            try:
                logger.info(
                    f"Preprocessing page {page.page_number} "
                    f"(ID: {page.id}) of document {document_id}"
                )

                # Download original image from storage
                image_bytes = storage.download_file_sync(page.image_path)

                # Load as PIL Image
                img = Image.open(io.BytesIO(image_bytes))

                # Step 1: Remove noise (bilateral filter, medium strength)
                logger.debug(f"Removing noise from page {page.page_number}")
                img = remove_noise_from_pil_image(
                    img,
                    method="bilateral",
                    strength="medium"
                )

                # Step 2: Increase contrast (simple method, factor 1.5)
                logger.debug(f"Enhancing contrast for page {page.page_number}")
                img = increase_contrast_from_pil_image(
                    img,
                    method="simple",
                    factor=1.5
                )

                # Step 3: Add transparent grid overlay
                logger.debug(f"Adding grid overlay to page {page.page_number}")
                img = add_grid_to_pil_image(
                    img,
                    grid_size=20,
                    line_color=(200, 200, 200, 80),  # Light gray at 31% opacity
                    line_width=1
                )

                # Convert back to bytes
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format="PNG")
                preprocessed_bytes = img_byte_arr.getvalue()

                # Upload preprocessed image
                filename = f"page_{page.page_number}_preprocessed.png"
                preprocessed_path = storage.upload_bytes_sync(
                    preprocessed_bytes,
                    filename=filename,
                    prefix=f"preprocessed/{document_id}",
                )

                # Update page record with preprocessed image path
                page.preprocessed_image_path = preprocessed_path
                db.commit()

                preprocessed_count += 1
                logger.info(
                    f"Successfully preprocessed page {page.page_number} "
                    f"-> {preprocessed_path}"
                )

            except Exception as e:
                logger.error(
                    f"Error preprocessing page {page.page_number} "
                    f"(ID: {page.id}): {str(e)}",
                    exc_info=True
                )
                # Continue with other pages even if one fails
                continue

        logger.info(
            f"Preprocessing complete for document {document_id}: "
            f"{preprocessed_count}/{len(pages)} pages processed"
        )

        return {
            "document_id": document_id,
            "total_pages": len(pages),
            "pages_processed": preprocessed_count,
            "status": "success",
        }

    except Exception as e:
        logger.error(
            f"Error in preprocessing workflow for document {document_id}: {str(e)}",
            exc_info=True
        )
        db.rollback()

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            logger.warning(
                f"Retrying preprocessing for document {document_id} "
                f"(attempt {self.request.retries + 1}/{self.max_retries})"
            )
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        else:
            logger.error(
                f"All retries exhausted for preprocessing document {document_id}"
            )
            raise

    finally:
        db.close()
