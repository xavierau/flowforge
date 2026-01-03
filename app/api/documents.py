"""Document management endpoints."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Document, DocumentPage, ExtractionJob, User
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentResponse,
)
from app.schemas.extraction import ParseRequest, ParseResponse, DocumentPageResponse, resolve_mode_fields
from app.models.enums import SplitMode, ExtractionMode
from app.services.storage import get_storage_service, StorageService
from app.services.schema_validator import SchemaValidator
from app.services.extraction_service import ExtractionCreditValidator
from app.dependencies.auth import require_permission_flexible

router = APIRouter()
logger = logging.getLogger(__name__)


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
    valid_providers = ["google", "openai", "llamaextract"]
    if request.model_provider_config.provider not in valid_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}",
        )

    # --- RESOLVE SPLIT/EXTRACTION MODES (with backward compatibility) ---
    split_mode, extraction_mode = resolve_mode_fields(
        request.split_mode,
        request.extraction_mode,
        request.processing_mode
    )

    # Validate split_mode
    valid_split_modes = [m.value for m in SplitMode]
    if split_mode not in valid_split_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid split_mode. Must be one of: {', '.join(valid_split_modes)}",
        )

    # Validate extraction_mode
    valid_extraction_modes = [m.value for m in ExtractionMode]
    if extraction_mode not in valid_extraction_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid extraction_mode. Must be one of: {', '.join(valid_extraction_modes)}",
        )

    # Validate auto split mode - only valid for PDFs with multiple pages
    if split_mode == SplitMode.AUTO.value:
        if document.mime_type != "application/pdf":
            raise HTTPException(
                status_code=400,
                detail="Auto split mode is only available for PDF documents"
            )
        # Check if document has pages (needs to be processed first if not)
        if document.status == "uploaded":
            raise HTTPException(
                status_code=400,
                detail="Document must be processed before using auto split mode. "
                       "Upload the document first, wait for processing, then submit extraction."
            )

    # Validate markdown configuration if markdown extraction mode
    if extraction_mode == ExtractionMode.MARKDOWN.value:
        if not request.markdown_converter:
            raise HTTPException(
                status_code=400,
                detail="markdown_converter is required for extraction_mode='markdown'"
            )

        # Validate converter availability
        from app.services.converters import get_converter_factory
        factory = get_converter_factory()
        available = factory.list_available_converters()

        if request.markdown_converter not in available["markdown_converters"]:
            raise HTTPException(
                status_code=400,
                detail=f"Markdown converter '{request.markdown_converter}' not available. "
                       f"Available converters: {available['markdown_converters']}. "
                       f"Check API keys in settings."
            )

        # Validate markdown format
        valid_formats = ["standard", "table_heavy", "layout_preserved"]
        if request.markdown_format and request.markdown_format not in valid_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid markdown_format. Must be one of: {', '.join(valid_formats)}"
            )

    # Derive processing_mode for backward compatibility (stored in DB)
    derived_processing_mode = "batch"
    if split_mode == SplitMode.PER_PAGE.value:
        derived_processing_mode = "per_page"
    if extraction_mode == ExtractionMode.MARKDOWN.value:
        derived_processing_mode = "markdown"

    # Validate LlamaExtract configuration
    if request.model_provider_config.provider == "llamaextract":
        valid_llamaextract_modes = ["standard", "premium"]
        if request.llamaextract_mode and request.llamaextract_mode not in valid_llamaextract_modes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid llamaextract_mode. Must be one of: {', '.join(valid_llamaextract_modes)}"
            )

        valid_llamaextract_targets = ["per_doc", "per_page"]
        if request.llamaextract_target and request.llamaextract_target not in valid_llamaextract_targets:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid llamaextract_target. Must be one of: {', '.join(valid_llamaextract_targets)}"
            )

    # --- SYNCHRONOUS CREDIT DEDUCTION ---
    # Use shared ExtractionCreditValidator service (DRY principle)
    # This service handles pessimistic locking, balance checking, and transaction creation
    credit_validator = ExtractionCreditValidator(db)

    try:
        # Create extraction job FIRST (need ID for credit transaction reference)
        job = ExtractionJob(
            document_id=document.id,
            tenant_id=current_user.tenant_id,
            schema_definition_id=schema_def_id,
            extraction_schema=final_schema,
            custom_prompt=request.custom_prompt,
            model_provider=request.model_provider_config.provider,
            model_name=request.model_provider_config.model,
            # New granular mode fields
            split_mode=split_mode,
            extraction_mode=extraction_mode,
            # Legacy processing_mode for backward compatibility
            processing_mode=derived_processing_mode,
            markdown_converter=request.markdown_converter if extraction_mode == ExtractionMode.MARKDOWN.value else None,
            markdown_format=request.markdown_format if extraction_mode == ExtractionMode.MARKDOWN.value else None,
            llamaextract_mode=request.llamaextract_mode if request.model_provider_config.provider == "llamaextract" else None,
            llamaextract_target=request.llamaextract_target if request.model_provider_config.provider == "llamaextract" else None,
            callback_url=request.callback_url,
            status="queued",
            credits_cost=document.page_count or 1,
        )

        db.add(job)
        db.flush()  # Get job ID without committing

        # Atomically validate and deduct credits
        credit_transaction, required_credits = credit_validator.validate_and_deduct_credits(
            tenant_id=current_user.tenant_id,
            page_count=document.page_count or 1,
            job_id=job.id,
            document_id=document.id,
            user_id=current_user.id,
            model_provider=request.model_provider_config.provider,
            model_name=request.model_provider_config.model,
            llamaextract_mode=request.llamaextract_mode if request.model_provider_config.provider == "llamaextract" else None,
        )

        # Link transaction to job
        job.credits_deducted = True
        job.credit_transaction_id = credit_transaction.id

        # Commit atomically - job creation + credit deduction happen together
        db.commit()
        db.refresh(job)

    except HTTPException:
        # Re-raise HTTP exceptions (insufficient credits, tenant not found)
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create extraction job: {str(e)}"
        )

    # --- END SYNCHRONOUS CREDIT DEDUCTION ---

    # Route to appropriate pipeline based on split_mode and extraction_mode
    if split_mode == SplitMode.AUTO.value:
        # AUTO SPLIT MODE: Use document splitter + extraction pipeline
        # Creates SplitJob, analyzes boundaries, creates child documents, then extracts each
        from app.tasks.document_splitter import split_and_extract
        from app.models.document_split import SplitJob

        # Create SplitJob to track the splitting operation
        split_job = SplitJob(
            tenant_id=current_user.tenant_id,
            source_document_id=document.id,
            status="queued",
            apply_rotation=True,  # Enable rotation correction by default
        )
        db.add(split_job)
        db.flush()

        # Link extraction job to split job
        job.parent_split_job_id = split_job.id
        db.commit()
        db.refresh(job)

        # Build extraction config for child documents
        extraction_config = {
            "schema_definition_id": str(schema_def_id) if schema_def_id else None,
            "extraction_schema": final_schema,
            "custom_prompt": request.custom_prompt,
            "model_provider": request.model_provider_config.provider,
            "model_name": request.model_provider_config.model,
            "extraction_mode": extraction_mode,
            "markdown_converter": request.markdown_converter if extraction_mode == ExtractionMode.MARKDOWN.value else None,
            "markdown_format": request.markdown_format if extraction_mode == ExtractionMode.MARKDOWN.value else None,
            "callback_url": request.callback_url,
        }

        # Queue split_and_extract task
        task = split_and_extract.delay(
            str(split_job.id),
            str(current_user.tenant_id),
            extraction_config
        )
        logger.info(f"Queued auto-split + extraction for job {job.id}, split_job {split_job.id}")

    elif extraction_mode == ExtractionMode.MARKDOWN.value:
        # MARKDOWN EXTRACTION MODE: vision → markdown → JSON pipeline
        if document.status == "uploaded":
            # Chain: PDF→images → markdown pipeline
            from app.tasks.combined_extraction import process_document_and_extract
            task = process_document_and_extract.delay(str(job.id))
            logger.info(f"Queued combined processing (PDF+markdown) for job {job.id}")
        else:
            # Document already has images, go directly to markdown pipeline
            from app.tasks.markdown_pipeline import process_markdown_extraction_pipeline
            task = process_markdown_extraction_pipeline.delay(str(job.id))
            logger.info(f"Queued markdown pipeline for job {job.id}")

    else:
        # VLLM EXTRACTION MODE: Direct vision extraction (batch or per_page)
        if document.status == "uploaded":
            # Document needs to be processed (PDF to images) AND extracted
            from app.tasks.combined_extraction import process_document_and_extract
            task = process_document_and_extract.delay(str(job.id))
            logger.info(f"Queued combined processing (PDF+extraction) for job {job.id}")
        else:
            # Document already processed, just need extraction
            from app.tasks.extractor import process_extraction_job
            task = process_extraction_job.delay(str(job.id))
            logger.info(f"Queued direct extraction for job {job.id}")

    # Update job with celery task ID
    job.celery_task_id = task.id
    db.commit()

    # Estimate processing time (rough estimate)
    page_count = document.page_count or 1
    if split_mode == SplitMode.AUTO.value:
        # Auto split mode: analysis + splitting + extraction per child
        # Roughly 60 seconds base + 5 seconds per page for analysis + 15 seconds per page for extraction
        estimated_time = 60 + (page_count * 20)
    elif extraction_mode == ExtractionMode.MARKDOWN.value:
        # Markdown mode: 2-stage pipeline (vision→markdown + text→JSON)
        # Roughly 30 seconds base + 10 seconds per page
        estimated_time = 30 + (page_count * 10)
    elif split_mode == SplitMode.BATCH.value:
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


@router.get("/documents/{document_id}/pages", response_model=List[DocumentPageResponse])
async def get_document_pages(
    document_id: UUID,
    current_user: User = Depends(require_permission_flexible("documents:read")),
    db: Session = Depends(get_db),
) -> List[DocumentPageResponse]:
    """
    Get all pages for a document with markdown content.

    This endpoint is used by the frontend MarkdownViewer component
    to display markdown content for debugging and review.

    Supports both JWT and API token authentication.

    Required Permission: documents:read

    Args:
        document_id: Document ID to retrieve pages for
        current_user: Authenticated user with documents:read permission
        db: Database session

    Returns:
        List of document pages with markdown content (ordered by page number)
    """
    # Get document with tenant check
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .filter(Document.tenant_id == current_user.tenant_id)
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get all pages ordered by page number
    pages = (
        db.query(DocumentPage)
        .filter(DocumentPage.document_id == document_id)
        .order_by(DocumentPage.page_number)
        .all()
    )

    return pages
