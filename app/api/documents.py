"""Document management endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Document, ExtractionJob, User
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentResponse,
)
from app.schemas.extraction import ParseRequest, ParseResponse
from app.services.storage import get_storage_service, StorageService
from app.services.schema_validator import SchemaValidator
from app.dependencies.auth import require_permission_flexible

router = APIRouter()


@router.post("/documents/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission_flexible("documents:create")),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> DocumentUploadResponse:
    """
    Upload a document (PDF or image).

    Supports both JWT and API token authentication.

    Required Permission: documents:create

    Args:
        file: File to upload
        current_user: Authenticated user with documents:create permission
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

    # Create document record with tenant isolation
    document = Document(
        tenant_id=current_user.tenant_id,  # Set tenant_id for multi-tenancy
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
    current_user: User = Depends(require_permission_flexible("extraction:create")),
    db: Session = Depends(get_db),
) -> ParseResponse:
    """
    Parse a document and extract structured data.

    Supports both JWT and API token authentication.

    Required Permission: extraction:create

    Args:
        document_id: Document ID to parse
        request: Parse request with schema and model config
        current_user: Authenticated user with documents:create permission
        db: Database session

    Returns:
        Parse response with job ID
    """
    # Validate document exists AND belongs to user's tenant
    document = (
        db.query(Document)
        .filter(Document.tenant_id == current_user.tenant_id)
        .filter(Document.id == document_id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check document status - allow uploaded, ready_for_extraction, or completed
    valid_statuses = ["uploaded", "ready_for_extraction", "completed"]
    if document.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Document cannot be processed. Status: {document.status}. Expected one of: {', '.join(valid_statuses)}",
        )

    # Validate: at least one of schema_definition_id or extraction_schema must be provided
    if not request.schema_definition_id and not request.extraction_schema:
        raise HTTPException(
            status_code=400,
            detail="Either schema_definition_id or extraction_schema must be provided"
        )

    # Resolve schema (prefer schema_definition_id if both provided)
    final_schema = None
    schema_def_id = None
    if request.schema_definition_id:
        # Load saved schema definition (takes precedence over custom schema)
        from app.models import SchemaDefinition
        schema_def = (
            db.query(SchemaDefinition)
            .filter(SchemaDefinition.tenant_id == current_user.tenant_id)
            .filter(SchemaDefinition.id == request.schema_definition_id)
            .first()
        )
        if not schema_def:
            raise HTTPException(status_code=404, detail="Schema definition not found")

        final_schema = schema_def.definitions
        schema_def_id = request.schema_definition_id
    else:
        # Use custom schema
        final_schema = request.extraction_schema

    # Validate JSON schema
    validator = SchemaValidator()
    if not validator.is_valid_schema(final_schema):
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

    # --- SYNCHRONOUS CREDIT DEDUCTION (Option 2) ---
    # FIX: Deduct credits IMMEDIATELY in API endpoint (not async in Celery)
    # This eliminates TOCTOU race condition completely
    # If job fails, credits are refunded via compensating transaction
    from app.services.credit_service import CreditService
    from app.models.tenant import Tenant
    from app.exceptions.credits import InsufficientCreditsError

    # Calculate required credits (1 credit per page)
    required_credits = document.page_count or 1

    try:
        # CRITICAL: Acquire pessimistic lock on tenant row FIRST
        # This prevents concurrent requests from checking credits simultaneously
        tenant = (
            db.query(Tenant)
            .filter(Tenant.id == current_user.tenant_id)
            .with_for_update()  # SELECT FOR UPDATE - blocks other transactions
            .first()
        )

        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # Check credit balance while holding lock
        credit_service = CreditService(db)
        has_sufficient, current_balance = credit_service.check_sufficient_credits(
            tenant_id=current_user.tenant_id,
            required_credits=required_credits
        )

        if not has_sufficient:
            # Release lock by rolling back
            db.rollback()
            raise HTTPException(
                status_code=402,  # HTTP 402 Payment Required
                detail={
                    "error": "insufficient_credits",
                    "message": f"Insufficient credits to process document. Required: {required_credits}, Available: {current_balance}",
                    "required_credits": required_credits,
                    "available_credits": current_balance,
                    "credits_needed": required_credits - current_balance,
                }
            )

        # Create extraction job (within same transaction, while holding lock)
        job = ExtractionJob(
            document_id=document.id,
            tenant_id=current_user.tenant_id,  # FIX: Set tenant_id for performance
            schema_definition_id=schema_def_id,
            extraction_schema=final_schema,
            custom_prompt=request.custom_prompt,
            model_provider=request.model_provider_config.provider,
            model_name=request.model_provider_config.model,
            processing_mode=request.processing_mode,
            callback_url=request.callback_url,
            status="queued",
            credits_cost=required_credits,
        )

        db.add(job)
        db.flush()  # Get job ID without committing

        # SYNCHRONOUS DEDUCTION: Deduct credits IMMEDIATELY (before commit)
        # This is atomic with job creation - both succeed or both fail
        credit_transaction = credit_service.deduct_credits(
            tenant_id=current_user.tenant_id,
            amount=required_credits,
            reference_type="extraction_job",
            reference_id=job.id,
            description=f"Document extraction - {required_credits} page(s) (job {job.id})",
            created_by_user_id=current_user.id,
            metadata={
                "job_id": str(job.id),
                "document_id": str(document.id),
                "page_count": required_credits,
                "model_provider": request.model_provider_config.provider,
                "model_name": request.model_provider_config.model,
            },
            allow_negative=False,  # Enforce balance check
        )

        # Link transaction to job
        job.credits_deducted = True
        job.credit_transaction_id = credit_transaction.id

        # Commit atomically - job creation + credit deduction happen together
        db.commit()

    except HTTPException:
        # Re-raise HTTP exceptions (insufficient credits, tenant not found)
        raise
    except InsufficientCreditsError as e:
        # This shouldn't happen (we just checked), but handle it gracefully
        db.rollback()
        raise HTTPException(
            status_code=402,
            detail={
                "error": "insufficient_credits",
                "message": str(e),
                "required_credits": e.required,
                "available_credits": e.available,
            }
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create extraction job: {str(e)}"
        )

    # Refresh job to get generated fields
    db.refresh(job)

    # --- END SYNCHRONOUS CREDIT DEDUCTION ---

    # Queue extraction tasks - use combined task for unprocessed documents
    if document.status == "uploaded":
        # Document needs to be processed (PDF to images) AND extracted
        from app.tasks.combined_extraction import process_document_and_extract
        task = process_document_and_extract.delay(str(job.id))
    else:
        # Document already processed, just need extraction
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
    current_user: User = Depends(require_permission_flexible("documents:read")),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    """
    List documents with pagination (tenant-scoped).

    Supports both JWT and API token authentication.

    Required Permission: documents:read

    Args:
        status: Optional status filter
        limit: Number of results per page
        offset: Pagination offset
        current_user: Authenticated user with documents:read permission
        db: Database session

    Returns:
        List of documents with pagination info (filtered by tenant)
    """
    # Build query with tenant isolation
    query = db.query(Document).filter(Document.tenant_id == current_user.tenant_id)

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
    current_user: User = Depends(require_permission_flexible("documents:read")),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """
    Get a single document by ID (tenant-scoped).

    Supports both JWT and API token authentication.

    Required Permission: documents:read

    Args:
        document_id: Document ID
        current_user: Authenticated user with documents:read permission
        db: Database session

    Returns:
        Document details

    Raises:
        404: Document not found or belongs to different tenant
    """
    # Query with tenant filter FIRST to prevent cross-tenant access
    document = (
        db.query(Document)
        .filter(Document.tenant_id == current_user.tenant_id)
        .filter(Document.id == document_id)
        .first()
    )
    if not document:
        # Don't reveal if document exists in another tenant
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


@router.get("/documents/{document_id}/file")
async def download_document_file(
    document_id: UUID,
    current_user: User = Depends(require_permission_flexible("documents:read")),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> StreamingResponse:
    """
    Download the original document file (tenant-scoped).

    Supports both JWT and API token authentication.

    Required Permission: documents:read

    Args:
        document_id: Document ID
        current_user: Authenticated user with documents:read permission
        db: Database session
        storage: Storage service

    Returns:
        Streaming response with document file

    Raises:
        404: Document not found or belongs to different tenant
    """
    # Query with tenant filter to prevent cross-tenant access
    document = (
        db.query(Document)
        .filter(Document.tenant_id == current_user.tenant_id)
        .filter(Document.id == document_id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        # Download file from storage
        file_content = await storage.download_file(document.file_path)

        # Create streaming response
        from io import BytesIO
        from urllib.parse import quote

        # Encode filename for Content-Disposition header (RFC 5987)
        # Use ASCII-safe fallback and UTF-8 encoded filename*
        ascii_filename = document.filename.encode('ascii', 'ignore').decode('ascii') or 'document'
        encoded_filename = quote(document.filename)

        return StreamingResponse(
            BytesIO(file_content),
            media_type=document.mime_type,
            headers={
                "Content-Disposition": f'inline; filename="{ascii_filename}"; filename*=UTF-8\'\'{encoded_filename}',
                "Content-Length": str(len(file_content)),
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to download file: {str(e)}"
        )
