"""PDF to images conversion task."""

import io
from uuid import UUID
from celery import Task
from pdf2image import convert_from_bytes
from PIL import Image

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import Document, DocumentPage
from app.services.storage import get_storage_service


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def pdf_to_images(self: Task, document_id: str) -> dict:
    """
    Convert PDF pages to images.

    Args:
        document_id: Document UUID as string

    Returns:
        Dictionary with conversion results
    """
    db = SessionLocal()
    storage = get_storage_service()

    try:
        # Get document
        doc_uuid = UUID(document_id)
        document = db.query(Document).filter(Document.id == doc_uuid).first()

        if not document:
            raise ValueError(f"Document {document_id} not found")

        # Update status
        document.status = "processing"
        db.commit()

        # Download PDF from storage
        pdf_bytes = storage.download_file_sync(document.file_path)

        # Convert PDF to images
        images = convert_from_bytes(
            pdf_bytes,
            dpi=200,  # Good quality for OCR
            fmt="png",
        )

        # Update page count
        document.page_count = len(images)
        db.commit()

        # Process each page
        page_ids = []
        for page_num, image in enumerate(images, start=1):
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format="PNG")
            img_bytes = img_byte_arr.getvalue()

            # Upload to storage
            filename = f"page_{page_num}.png"
            image_path = storage.upload_bytes_sync(
                img_bytes,
                filename=filename,
                prefix=f"pages/{document_id}",
            )

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

            page_ids.append(str(page.id))

        # Update document status
        document.status = "ready_for_extraction"
        db.commit()

        return {
            "document_id": document_id,
            "page_count": len(images),
            "page_ids": page_ids,
            "status": "success",
        }

    except Exception as e:
        # Update document status to failed
        if document:
            document.status = "failed"
            db.commit()

        # Retry on failure
        raise self.retry(exc=e)

    finally:
        db.close()
