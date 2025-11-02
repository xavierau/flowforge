"""Document management endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Document, ExtractionJob
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentResponse,
)
from app.schemas.extraction import ParseRequest, ParseResponse
from app.services.storage import get_storage_service, StorageService
from app.services.schema_validator import SchemaValidator

router = APIRouter()


@router.post("/documents/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> DocumentUploadResponse:
    """
    Upload a document (PDF or image).

    Args:
        file: File to upload
        db: Database session
        storage: Storage service

    Returns:
        Document upload response with document ID and metadata
    """
    # Validate file type
    if file.content_type not in settings.allowed_mime_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(settings.allowed_mime_types)}",
        )

    # Validate file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.max_file_size_mb}MB",
        )

    if file_size == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    # Upload to storage
    file_path, size = await storage.upload_file(file, prefix="documents")

    # Determine initial status and page count
    is_pdf = file.content_type == settings.allowed_pdf_type
    status = "uploaded" if is_pdf else "ready_for_extraction"
    page_count = None  # Will be set by PDF processor

    # Create document record
    document = Document(
        filename=file.filename or "untitled",
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        file_path=file_path,
        status=status,
        page_count=page_count,
        metadata={},
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    # If PDF, queue conversion task
    if is_pdf:
        from app.tasks.pdf_processor import pdf_to_images

        pdf_to_images.delay(str(document.id))

    return DocumentUploadResponse(
        document_id=document.id,
        filename=document.filename,
        mime_type=document.mime_type,
        size_bytes=document.size_bytes,
        status=document.status,
        page_count=document.page_count,
        created_at=document.created_at,
    )


@router.post(
    "/documents/{document_id}/parse",
    response_model=ParseResponse,
    status_code=202,
)
async def parse_document(
    document_id: UUID,
    request: ParseRequest,
    db: Session = Depends(get_db),
) -> ParseResponse:
    """
    Parse a document and extract structured data.

    Args:
        document_id: Document ID to parse
        request: Parse request with schema and model config
        db: Database session

    Returns:
        Parse response with job ID
    """
    # Validate document exists
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check document status
    if document.status not in ["ready_for_extraction", "completed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Document not ready for extraction. Status: {document.status}",
        )

    # Validate JSON schema
    validator = SchemaValidator()
    if not validator.is_valid_schema(request.extraction_schema):
        raise HTTPException(status_code=400, detail="Invalid JSON schema")

    # Validate provider
    valid_providers = ["google", "openai"]
    if request.model_provider_config.provider not in valid_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}",
        )

    # Validate processing mode
    valid_modes = ["batch", "per_page"]
    if request.processing_mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid processing_mode. Must be one of: {', '.join(valid_modes)}",
        )

    # Create extraction job
    job = ExtractionJob(
        document_id=document.id,
        extraction_schema=request.extraction_schema,
        custom_prompt=request.custom_prompt,
        model_provider=request.model_provider_config.provider,
        model_name=request.model_provider_config.model,
        processing_mode=request.processing_mode,
        status="queued",
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue extraction tasks
    from app.tasks.extractor import process_extraction_job

    task = process_extraction_job.delay(str(job.id))

    # Update job with celery task ID
    job.celery_task_id = task.id
    db.commit()

    # Estimate processing time (rough estimate)
    page_count = document.page_count or 1
    if request.processing_mode == "batch":
        # Batch mode: faster since it's one API call
        estimated_time = 20  # Base time for batch processing
    else:
        # Per-page mode: 15 seconds per page
        estimated_time = page_count * 15

    return ParseResponse(
        extraction_job_id=job.id,
        document_id=document.id,
        status=job.status,
        estimated_time_seconds=estimated_time,
        created_at=job.created_at,
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    """
    List documents with pagination.

    Args:
        status: Optional status filter
        limit: Number of results per page
        offset: Pagination offset
        db: Database session

    Returns:
        List of documents with pagination info
    """
    # Build query
    query = db.query(Document)

    if status:
        query = query.filter(Document.status == status)

    # Get total count
    total = query.count()

    # Get paginated results
    documents = (
        query.order_by(Document.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                document_id=doc.id,
                filename=doc.filename,
                mime_type=doc.mime_type,
                size_bytes=doc.size_bytes,
                status=doc.status,
                page_count=doc.page_count,
                metadata=doc.document_metadata,
                created_at=doc.created_at,
            )
            for doc in documents
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """
    Get a single document by ID.

    Args:
        document_id: Document ID
        db: Database session

    Returns:
        Document details
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        document_id=document.id,
        filename=document.filename,
        mime_type=document.mime_type,
        size_bytes=document.size_bytes,
        status=document.status,
        page_count=document.page_count,
        metadata=document.document_metadata,
        created_at=document.created_at,
    )
