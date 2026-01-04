"""Job status and results endpoints."""

from datetime import datetime
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

logger = logging.getLogger(__name__)

from app.config import settings
from app.database import get_db
from app.models import ExtractionJob, ExtractionResult, DocumentPage, Document, User, SchemaDefinition
from app.models.tenant import Tenant
from app.schemas.job import (
    JobStatusResponse,
    JobResultResponse,
    JobProgress,
    ExtractionMetadata,
    JobListResponse,
    JobListItem,
)
from app.schemas.extraction import ExtractRequest, ExtractResponse
from app.services.storage import get_storage_service, StorageService
from app.services.schema_validator import SchemaValidator
from app.services.extraction_service import ExtractionCreditValidator
from app.dependencies.auth import require_permission, require_permission_flexible
from app.models.enums import JobSource, SplitMode, ExtractionMode
from app.schemas.extraction import resolve_mode_fields

router = APIRouter()


@router.post("/jobs/extract", response_model=ExtractResponse, status_code=202)
async def extract_from_file(
    file: UploadFile = File(...),
    schema_definition_id: str = Form(None),
    extraction_schema: str = Form(None),
    custom_prompt: str = Form(None),
    model_provider: str = Form(None),
    model_name: str = Form(None),
    # New granular mode fields
    split_mode: str = Form("batch"),
    extraction_mode: str = Form("vllm"),
    # Deprecated - use split_mode and extraction_mode instead
    processing_mode: str = Form(None),
    markdown_converter: str = Form(None),
    markdown_format: str = Form(None),
    callback_url: str = Form(None),
    enable_thinking: bool = Form(False),
    thinking_budget: int = Form(3000),
    source: str = Form("api"),
    current_user: User = Depends(require_permission_flexible("extraction:create")),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> ExtractResponse:
    """
    Combined upload and extract operation.

    Accepts a file and extraction configuration, creates both Document and ExtractionJob,
    and returns the job ID immediately for status polling.

    Required Permission: extraction:create

    Mode Configuration:
        - split_mode: How pages are grouped - 'per_page', 'batch', or 'auto'
        - extraction_mode: How extraction is performed - 'vllm' or 'markdown'

    Backward Compatibility:
        - processing_mode is deprecated but still accepted
        - If processing_mode is provided without split_mode/extraction_mode, it will be mapped:
          - 'batch' -> split_mode='batch', extraction_mode='vllm'
          - 'per_page' -> split_mode='per_page', extraction_mode='vllm'
          - 'markdown' -> split_mode='batch', extraction_mode='markdown'

    Args:
        file: File to upload and extract from
        schema_definition_id: Optional ID of saved schema definition
        extraction_schema: Optional custom JSON schema
        custom_prompt: Optional custom extraction instructions
        model_provider: Optional VLLM provider (google, openai, etc.). Uses default from .env if not provided
        model_name: Optional model name. Uses default from .env if not provided
        split_mode: Split mode - 'per_page', 'batch', or 'auto' (default: 'batch')
        extraction_mode: Extraction mode - 'vllm' or 'markdown' (default: 'vllm')
        processing_mode: DEPRECATED - use split_mode and extraction_mode instead
        callback_url: Optional webhook URL for completion notification
        enable_thinking: Enable AI thinking mode (default: False)
        thinking_budget: Token budget for thinking when enabled (default: 3000)
        source: Job source - 'webui' for web interface, 'api' for programmatic access (default: 'api')
        current_user: Authenticated user
        db: Database session
        storage: Storage service

    Returns:
        Extraction job ID and status

    Raises:
        400: Invalid request (schema, file type, or mode configuration)
        402: Insufficient credits
        404: Schema definition not found
        500: Server error

    Credit Deduction:
        Credits are deducted SYNCHRONOUSLY before job creation to prevent
        race conditions. If credit deduction fails, job creation is rolled back.
        Cost: 1 credit per page (minimum 1 credit for unknown page count).
        Auto split mode costs additional credits for LLM boundary detection.

    Note:
        - At least one of schema_definition_id or extraction_schema must be provided
        - If both are provided, schema_definition_id takes precedence
        - If model_provider or model_name not provided, defaults from .env are used
        - thinking_budget only applies when enable_thinking is True
        - Auto split mode only works with PDF files
    """
    # Use defaults from settings if not provided
    if not model_provider:
        model_provider = settings.default_model_provider
    if not model_name:
        model_name = settings.default_model_name

    # Validate: at least one of schema_definition_id or extraction_schema must be provided
    if not schema_definition_id and not extraction_schema:
        raise HTTPException(
            status_code=400,
            detail="Either schema_definition_id or extraction_schema must be provided"
        )

    # Resolve schema (prefer schema_definition_id if both provided)
    final_schema = None
    if schema_definition_id:
        # Load saved schema definition (takes precedence over custom schema)
        schema_def = (
            db.query(SchemaDefinition)
            .filter(SchemaDefinition.tenant_id == current_user.tenant_id)
            .filter(SchemaDefinition.id == schema_definition_id)
            .first()
        )
        if not schema_def:
            raise HTTPException(status_code=404, detail="Schema definition not found")

        final_schema = schema_def.definitions
    else:
        # Parse custom schema from JSON string
        try:
            final_schema = json.loads(extraction_schema)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in extraction_schema")

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

    # Validate schema
    validator = SchemaValidator()
    if not validator.is_valid_schema(final_schema):
        raise HTTPException(status_code=400, detail="Invalid JSON schema")

    # Validate provider
    valid_providers = ["google", "openai"]
    if model_provider not in valid_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}",
        )

    # Resolve split_mode and extraction_mode from request (handles backward compatibility)
    resolved_split_mode, resolved_extraction_mode = resolve_mode_fields(
        split_mode, extraction_mode, processing_mode
    )

    # Validate split_mode
    valid_split_modes = [m.value for m in SplitMode]
    if resolved_split_mode not in valid_split_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid split_mode. Must be one of: {', '.join(valid_split_modes)}",
        )

    # Validate extraction_mode
    valid_extraction_modes = [m.value for m in ExtractionMode]
    if resolved_extraction_mode not in valid_extraction_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid extraction_mode. Must be one of: {', '.join(valid_extraction_modes)}",
        )

    # Validate markdown configuration if markdown extraction mode
    if resolved_extraction_mode == "markdown":
        if not markdown_converter:
            raise HTTPException(
                status_code=400,
                detail="markdown_converter is required for markdown extraction mode"
            )

        # Validate converter availability
        from app.services.converters import get_converter_factory
        factory = get_converter_factory()
        available = factory.list_available_converters()

        if markdown_converter not in available["markdown_converters"]:
            raise HTTPException(
                status_code=400,
                detail=f"Markdown converter '{markdown_converter}' not available. "
                       f"Available converters: {available['markdown_converters']}. "
                       f"Check API keys in settings."
            )

        # Set default markdown format if not provided
        if not markdown_format:
            markdown_format = "table_heavy"

    # Validate source
    valid_sources = [s.value for s in JobSource]
    if source not in valid_sources:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source. Must be one of: {', '.join(valid_sources)}",
        )

    # Upload to storage
    file_path, size = await storage.upload_file(file, prefix="documents")

    # Determine initial status and page count
    is_pdf = file.content_type == settings.allowed_pdf_type
    status = "uploaded"  # Always start as uploaded for combined flow
    page_count = None  # Default for non-PDF files

    # CRITICAL FIX: For PDFs, extract page count BEFORE credit deduction
    # This ensures accurate credit calculation for per_page mode
    if is_pdf:
        try:
            from app.utils.pdf_utils import get_pdf_page_count

            # Download the uploaded file to count pages
            pdf_bytes = storage.download_file_sync(file_path)
            page_count = get_pdf_page_count(pdf_bytes)

            logger.info(f"PDF page count extracted: {page_count} pages for {file.filename}")
        except Exception as e:
            logger.error(f"Failed to extract PDF page count: {str(e)}", exc_info=True)
            # Clean up uploaded file
            storage.delete_file_sync(file_path)
            raise HTTPException(
                status_code=400,
                detail=f"Failed to process PDF: {str(e)}"
            )

    # Validate auto split mode (PDF only)
    if resolved_split_mode == "auto" and not is_pdf:
        # Clean up uploaded file
        storage.delete_file_sync(file_path)
        raise HTTPException(
            status_code=400,
            detail="Auto split mode is only supported for PDF files"
        )

    # Create document record with tenant isolation
    document = Document(
        tenant_id=current_user.tenant_id,
        filename=file.filename or "untitled",
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        file_path=file_path,
        status=status,
        page_count=page_count,  # Now set for PDFs
        metadata={},
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    # --- CRITICAL FIX: SYNCHRONOUS CREDIT DEDUCTION ---
    # FIX: Deduct credits IMMEDIATELY before creating job (not async in Celery)
    # This follows the same pattern as /api/v1/documents/{id}/parse endpoint

    # Initialize credit validator
    credit_validator = ExtractionCreditValidator(db)

    try:
        # Create job FIRST (need ID for credit transaction reference)
        job = ExtractionJob(
            document_id=document.id,
            tenant_id=current_user.tenant_id,
            schema_definition_id=schema_definition_id if schema_definition_id else None,
            extraction_schema=final_schema,
            custom_prompt=custom_prompt,
            model_provider=model_provider,
            model_name=model_name,
            # New granular mode fields
            split_mode=resolved_split_mode,
            extraction_mode=resolved_extraction_mode,
            # Keep processing_mode for backward compatibility (derived from new fields)
            processing_mode=resolved_split_mode if resolved_extraction_mode == "vllm" else "markdown",
            markdown_converter=markdown_converter if resolved_extraction_mode == "markdown" else None,
            markdown_format=markdown_format if resolved_extraction_mode == "markdown" else None,
            callback_url=callback_url,
            enable_thinking=enable_thinking,
            thinking_budget=thinking_budget if enable_thinking else 0,
            status="queued",
            credits_cost=page_count or 1,  # Now accurate for PDFs (extracted above)
            source=source,  # Track job origin (webui or api)
        )

        db.add(job)
        db.flush()  # Get job ID without committing

        # Atomically validate and deduct credits
        # This acquires SELECT FOR UPDATE lock on tenant row
        # page_count is now accurate for PDFs (extracted synchronously above)
        credit_transaction, required_credits = credit_validator.validate_and_deduct_credits(
            tenant_id=current_user.tenant_id,
            page_count=page_count or 1,  # Accurate page count for PDFs
            job_id=job.id,
            document_id=document.id,
            user_id=current_user.id,
            model_provider=model_provider,
            model_name=model_name
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
    # --- END CREDIT DEDUCTION ---

    # Route to appropriate task based on split_mode
    if resolved_split_mode == "auto":
        # Auto split mode: Create SplitJob and trigger split_and_extract pipeline
        from celery import chain
        from app.models.document_split import SplitJob
        from app.tasks.document_splitter import (
            analyze_document_boundaries,
            split_and_create_documents,
            split_and_extract,
        )

        # Create SplitJob record
        # Note: Splitting uses Dashscope/Qwen VL models via DSPy, not the extraction model
        # The default qwen_vision_model will be used for boundary detection
        split_job = SplitJob(
            source_document_id=document.id,
            tenant_id=current_user.tenant_id,
            dspy_model=None,  # Use default Qwen VL model for splitting
            status="queued",
        )
        db.add(split_job)
        db.flush()

        # Link extraction job to split job
        job.parent_split_job_id = split_job.id
        db.commit()
        db.refresh(job)
        db.refresh(split_job)

        # Build extraction config for child jobs
        extraction_config = {
            "extraction_schema": final_schema,
            "custom_prompt": custom_prompt,
            "model_provider": model_provider,
            "model_name": model_name,
            "extraction_mode": resolved_extraction_mode,  # Pass through extraction mode
            "markdown_converter": markdown_converter if resolved_extraction_mode == "markdown" else None,
            "markdown_format": markdown_format if resolved_extraction_mode == "markdown" else None,
            "callback_url": callback_url,
            "enable_thinking": enable_thinking,
            "thinking_budget": thinking_budget if enable_thinking else 0,
            "source": source,
            "tenant_id": str(current_user.tenant_id),
            "user_id": str(current_user.id),
            # Pass parent's credit transaction so child jobs inherit credit status
            "parent_credit_transaction_id": str(job.credit_transaction_id) if job.credit_transaction_id else None,
            # Pass parent extraction job ID so child jobs can update parent status when complete
            "parent_extraction_job_id": str(job.id),
        }
        if schema_definition_id:
            extraction_config["schema_definition_id"] = schema_definition_id

        # Chain all split tasks sequentially:
        # 1. analyze_document_boundaries - detect page boundaries and rotation
        # 2. split_and_create_documents - create child documents from boundaries
        # 3. split_and_extract - queue extraction for each child document
        # Using a single chain ensures proper sequencing (no nested async chains)
        workflow = chain(
            analyze_document_boundaries.s(str(split_job.id), str(current_user.tenant_id)),
            split_and_create_documents.s(),  # receives analysis result
            split_and_extract.si(str(split_job.id), str(current_user.tenant_id), extraction_config),
        )
        task = workflow.apply_async()

        # Update split job with celery task ID
        split_job.celery_task_id = task.id
        job.celery_task_id = task.id  # Also set on extraction job for tracking
        job.status = "processing"  # Mark parent job as processing
        job.started_at = datetime.utcnow()
        db.commit()

        message = "Document uploaded and split+extract pipeline queued (auto split mode)"
    else:
        # Standard modes: Queue combined processing task
        from app.tasks.combined_extraction import process_document_and_extract

        task = process_document_and_extract.delay(str(job.id))

        # Update job with celery task ID
        job.celery_task_id = task.id
        db.commit()

        message = "Document uploaded and extraction job queued"

    # Estimate processing time
    # PDF processing ~10s + extraction time
    base_time = 10 if is_pdf else 0
    page_estimate = page_count or 1

    if resolved_split_mode == "auto":
        # Auto split: boundary detection + per-child extraction
        extraction_time = 30 + (page_estimate * 10)  # Extra time for LLM splitting
    elif resolved_split_mode == "batch":
        extraction_time = 20  # Base time for batch processing
    else:  # per_page
        extraction_time = page_estimate * 15

    # Markdown mode adds extra time for conversion
    if resolved_extraction_mode == "markdown":
        extraction_time += page_estimate * 5

    estimated_time = base_time + extraction_time

    return ExtractResponse(
        extraction_job_id=job.id,
        document_id=document.id,
        status=job.status,
        message=message,
        estimated_time_seconds=estimated_time,
        created_at=job.created_at,
    )


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(require_permission_flexible("jobs:read")),
    db: Session = Depends(get_db),
) -> JobListResponse:
    """
    List all extraction jobs with pagination (tenant-scoped).

    Required Permission: jobs:read

    Args:
        limit: Number of results per page (1-100)
        offset: Pagination offset
        current_user: Authenticated user with documents:read permission
        db: Database session

    Returns:
        List of jobs with pagination info (filtered by tenant)
    """
    # Build query with tenant isolation through document relationship
    query = (
        db.query(ExtractionJob)
        .join(Document)
        .filter(Document.tenant_id == current_user.tenant_id)
    )

    # Get total count
    total = query.count()

    # Get paginated results
    jobs = (
        query.order_by(ExtractionJob.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    # Build response with progress and document name
    job_items = []
    for job in jobs:
        # Calculate progress if multi-page
        progress = None
        if job.document.page_count:
            total_pages = job.document.page_count

            # For completed jobs, all pages are processed
            if job.status == "completed":
                completed_pages = total_pages
            else:
                # For in-progress jobs, count extraction results
                # Note: In batch mode, there's only 1 result for all pages
                completed_pages = (
                    db.query(func.count(ExtractionResult.id))
                    .filter(ExtractionResult.extraction_job_id == job.id)
                    .scalar()
                )

            progress = JobProgress(
                total_pages=total_pages,
                completed_pages=completed_pages or 0,
            )

        # Get model from first result if available
        model_used = None
        if job.status == "completed":
            first_result = (
                db.query(ExtractionResult.model_used)
                .filter(ExtractionResult.extraction_job_id == job.id)
                .first()
            )
            if first_result:
                model_used = first_result[0]

        job_items.append(
            JobListItem(
                id=job.id,
                document_id=job.document_id,
                document_name=job.document.filename,
                schema_definition_id=job.schema_definition_id,
                status=job.status,
                progress=progress,
                started_at=job.started_at,
                completed_at=job.completed_at,
                created_at=job.created_at,
                updated_at=job.updated_at,
                error=job.error_message,
                model_used=model_used,
                source=job.source,
            )
        )

    return JobListResponse(
        jobs=job_items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: UUID,
    current_user: User = Depends(require_permission_flexible("jobs:read")),
    db: Session = Depends(get_db),
) -> JobStatusResponse:
    """
    Get extraction job status (tenant-scoped).

    Required Permission: jobs:read

    Args:
        job_id: Extraction job ID
        current_user: Authenticated user with documents:read permission
        db: Database session

    Returns:
        Job status with progress information

    Raises:
        404: Job not found or belongs to different tenant
    """
    # Get job with tenant filtering through document relationship
    job = (
        db.query(ExtractionJob)
        .join(Document)
        .filter(Document.tenant_id == current_user.tenant_id)
        .filter(ExtractionJob.id == job_id)
        .first()
    )
    if not job:
        # Don't reveal if job exists in another tenant
        raise HTTPException(status_code=404, detail="Job not found")

    # Calculate progress
    progress = None
    if job.document.page_count:
        # Multi-page document
        total_pages = job.document.page_count

        # For completed jobs, all pages are processed
        if job.status == "completed":
            completed_pages = total_pages
        else:
            # For in-progress jobs, count extraction results
            # Note: In batch mode, there's only 1 result for all pages
            completed_pages = (
                db.query(func.count(ExtractionResult.id))
                .filter(ExtractionResult.extraction_job_id == job.id)
                .scalar()
            )

        progress = JobProgress(
            total_pages=total_pages,
            completed_pages=completed_pages or 0,
        )

    return JobStatusResponse(
        job_id=job.id,
        document_id=job.document_id,
        status=job.status,
        progress=progress,
        started_at=job.started_at,
        updated_at=job.updated_at,
        error=job.error_message,
    )


@router.get("/jobs/{job_id}/result", response_model=JobResultResponse)
async def get_job_result(
    job_id: UUID,
    current_user: User = Depends(require_permission_flexible("jobs:read")),
    db: Session = Depends(get_db),
) -> JobResultResponse:
    """
    Get extraction job results (tenant-scoped).

    Required Permission: jobs:read

    Args:
        job_id: Extraction job ID
        current_user: Authenticated user with documents:read permission
        db: Database session

    Returns:
        Extracted data and metadata

    Raises:
        404: Job not found or belongs to different tenant
        400: Job not completed yet
    """
    # Get job with tenant filtering through document relationship
    job = (
        db.query(ExtractionJob)
        .join(Document)
        .filter(Document.tenant_id == current_user.tenant_id)
        .filter(ExtractionJob.id == job_id)
        .first()
    )
    if not job:
        # Don't reveal if job exists in another tenant
        raise HTTPException(status_code=404, detail="Job not found")

    # Check if job is completed
    if job.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed yet. Status: {job.status}",
        )

    # Get results
    results = (
        db.query(ExtractionResult)
        .filter(ExtractionResult.extraction_job_id == job.id)
        .order_by(ExtractionResult.created_at)
        .all()
    )

    if not results:
        raise HTTPException(status_code=404, detail="No results found for this job")

    # Aggregate results
    if len(results) == 1:
        # Single page or single result
        result = results[0]
        extracted_data = result.extracted_data
        metadata = ExtractionMetadata(
            model_used=result.model_used,
            input_tokens=result.input_tokens or 0,
            output_tokens=result.output_tokens or 0,
            tokens_used=result.tokens_used or 0,
            processing_time_ms=result.processing_time_ms or 0,
            confidence_score=result.confidence_score or 0.0,
        )
    else:
        # Multi-page: combine results
        extracted_data = {
            "pages": [result.extracted_data for result in results],
            "page_count": len(results),
        }

        # Aggregate metadata
        total_input_tokens = sum(r.input_tokens or 0 for r in results)
        total_output_tokens = sum(r.output_tokens or 0 for r in results)
        total_tokens = sum(r.tokens_used or 0 for r in results)
        total_time = sum(r.processing_time_ms or 0 for r in results)
        avg_confidence = sum(r.confidence_score or 0 for r in results) / len(results)

        metadata = ExtractionMetadata(
            model_used=results[0].model_used,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            tokens_used=total_tokens,
            processing_time_ms=total_time,
            confidence_score=avg_confidence,
        )

    return JobResultResponse(
        job_id=job.id,
        document_id=job.document_id,
        schema_definition_id=job.schema_definition_id,
        status=job.status,
        extracted_data=extracted_data,
        metadata=metadata,
        completed_at=job.completed_at or job.updated_at,
        # Include job configuration
        extraction_schema=job.extraction_schema,
        custom_prompt=job.custom_prompt,
        model_provider=job.model_provider,
        model_name=job.model_name,
        callback_url=job.callback_url,
        # New granular mode fields
        split_mode=job.split_mode,
        extraction_mode=job.extraction_mode,
        processing_mode=job.processing_mode,
        # Thinking mode fields
        enable_thinking=job.enable_thinking,
        thinking_budget=job.thinking_budget,
    )


@router.post("/jobs/{job_id}/retry", response_model=ExtractResponse, status_code=202)
async def retry_job(
    job_id: UUID,
    source: str = Query("api", description="Job source - 'webui' or 'api'"),
    current_user: User = Depends(require_permission_flexible("extraction:create")),
    db: Session = Depends(get_db),
) -> ExtractResponse:
    """
    Retry an extraction job with the same configuration.

    Creates a new extraction job with identical configuration to the original job,
    using the same document without re-uploading.

    Required Permission: extraction:create

    Args:
        job_id: ID of the job to retry
        source: Job source - 'webui' for web interface, 'api' for programmatic access (default: 'api')
        current_user: Authenticated user with extraction:create permission
        db: Database session

    Returns:
        New extraction job ID and status

    Raises:
        402: Insufficient credits
        404: Job not found or belongs to different tenant

    Credit Deduction:
        Credits are deducted SYNCHRONOUSLY before job creation.
        Cost: 1 credit per page (same as original job).
    """
    # Validate source
    valid_sources = [s.value for s in JobSource]
    if source not in valid_sources:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source. Must be one of: {', '.join(valid_sources)}",
        )
    # Get original job with tenant filtering
    original_job = (
        db.query(ExtractionJob)
        .join(Document)
        .filter(Document.tenant_id == current_user.tenant_id)
        .filter(ExtractionJob.id == job_id)
        .first()
    )
    if not original_job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Verify document still exists and belongs to tenant
    document = (
        db.query(Document)
        .filter(Document.tenant_id == current_user.tenant_id)
        .filter(Document.id == original_job.document_id)
        .first()
    )
    if not document:
        raise HTTPException(
            status_code=404,
            detail="Original document not found or has been deleted"
        )

    # --- CRITICAL FIX: Re-fetch schema from SchemaDefinition if available ---
    # This ensures retried jobs use the LATEST schema version, not the old snapshot
    final_schema = None
    final_schema_definition_id = original_job.schema_definition_id

    if original_job.schema_definition_id:
        # Attempt to fetch current schema from SchemaDefinition
        schema_def = (
            db.query(SchemaDefinition)
            .filter(SchemaDefinition.tenant_id == current_user.tenant_id)
            .filter(SchemaDefinition.id == original_job.schema_definition_id)
            .first()
        )
        if schema_def:
            # Use fresh schema from SchemaDefinition
            final_schema = schema_def.definitions
            logger.info(
                f"Retry job {job_id}: Using updated schema from SchemaDefinition "
                f"{schema_def.id} (name: {schema_def.name})"
            )
        else:
            # SchemaDefinition was deleted - fall back to original snapshot
            final_schema = original_job.extraction_schema
            final_schema_definition_id = None  # Clear reference to deleted schema
            logger.warning(
                f"Retry job {job_id}: SchemaDefinition {original_job.schema_definition_id} "
                f"was deleted. Falling back to original schema snapshot."
            )
    else:
        # No schema_definition_id - use original custom schema snapshot
        final_schema = original_job.extraction_schema
        logger.info(
            f"Retry job {job_id}: Using original custom schema (no SchemaDefinition linked)"
        )

    # --- CRITICAL: SYNCHRONOUS CREDIT DEDUCTION FOR RETRY ---
    # Initialize credit validator
    credit_validator = ExtractionCreditValidator(db)

    try:
        # Create new extraction job with same configuration
        new_job = ExtractionJob(
            document_id=original_job.document_id,
            tenant_id=current_user.tenant_id,  # Set tenant_id
            schema_definition_id=final_schema_definition_id,
            extraction_schema=final_schema,
            custom_prompt=original_job.custom_prompt,
            model_provider=original_job.model_provider,
            model_name=original_job.model_name,
            # Copy new granular mode fields
            split_mode=original_job.split_mode,
            extraction_mode=original_job.extraction_mode,
            processing_mode=original_job.processing_mode,  # Keep for backward compatibility
            markdown_converter=original_job.markdown_converter,
            markdown_format=original_job.markdown_format,
            callback_url=original_job.callback_url,
            enable_thinking=original_job.enable_thinking,
            thinking_budget=original_job.thinking_budget,
            status="queued",
            credits_cost=document.page_count or 1,  # Set cost upfront
            source=source,  # Track job origin (webui or api)
        )

        db.add(new_job)
        db.flush()  # Get job ID without committing

        # Atomically validate and deduct credits
        credit_transaction, required_credits = credit_validator.validate_and_deduct_credits(
            tenant_id=current_user.tenant_id,
            page_count=document.page_count or 1,
            job_id=new_job.id,
            document_id=document.id,
            user_id=current_user.id,
            model_provider=original_job.model_provider,
            model_name=original_job.model_name
        )

        # Link transaction to job
        new_job.credits_deducted = True
        new_job.credit_transaction_id = credit_transaction.id

        # Commit atomically
        db.commit()
        db.refresh(new_job)

    except HTTPException:
        # Re-raise HTTP exceptions (insufficient credits, tenant not found)
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retry extraction job: {str(e)}"
        )
    # --- END CREDIT DEDUCTION ---

    # Queue extraction task
    # Note: For retry, we always use the standard combined task, even if original was auto-split.
    # Auto-split only applies to initial job creation (document splitting already happened).
    from app.tasks.combined_extraction import process_document_and_extract

    task = process_document_and_extract.delay(str(new_job.id))

    # Update job with celery task ID
    new_job.celery_task_id = task.id
    db.commit()

    # Estimate processing time using new granular mode fields
    is_pdf = document.mime_type == settings.allowed_pdf_type
    base_time = 10 if is_pdf else 0
    page_estimate = document.page_count or 1

    if new_job.split_mode == "batch" or new_job.split_mode == "auto":
        # Auto mode retries use batch since document is already processed
        extraction_time = 20
    else:  # per_page
        extraction_time = page_estimate * 15

    # Markdown mode adds extra time for conversion
    if new_job.extraction_mode == "markdown":
        extraction_time += page_estimate * 5

    estimated_time = base_time + extraction_time

    return ExtractResponse(
        extraction_job_id=new_job.id,
        document_id=document.id,
        status=new_job.status,
        message="Extraction job retried successfully",
        estimated_time_seconds=estimated_time,
        created_at=new_job.created_at,
    )


# Analytics endpoints (alias to avoid "metrics" in URL which may be blocked by some tools)
from fastapi import Response
from app.schemas.metrics import DashboardMetricsResponse
from app.services.metrics_service import MetricsService


@router.get("/jobs/analytics/dashboard", response_model=DashboardMetricsResponse, status_code=200)
async def get_jobs_analytics_dashboard(
    response: Response,
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Number of days to include in analytics (1-365)",
    ),
    current_user: User = Depends(require_permission_flexible("jobs:read")),
    db: Session = Depends(get_db),
):
    """
    Get dashboard analytics for jobs (alias endpoint).

    This is an alias for /api/v1/metrics/dashboard to avoid potential URL blocking
    by ad blockers or security tools that block "metrics" in URLs.
    """
    # Set response headers to prevent caching
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    service = MetricsService(db)
    return service.get_dashboard_metrics(tenant_id=current_user.tenant_id, days=days)


from datetime import datetime
from typing import Optional
from app.schemas.metrics import CompletedJobsResponse


@router.get("/jobs/analytics/completed", response_model=CompletedJobsResponse, status_code=200)
async def get_jobs_analytics_completed(
    response: Response,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=50, ge=1, le=100, description="Number of items per page (max 100)"
    ),
    start_date: Optional[datetime] = Query(
        default=None, description="Filter by start date (ISO 8601 format)"
    ),
    end_date: Optional[datetime] = Query(
        default=None, description="Filter by end date (ISO 8601 format)"
    ),
    current_user: User = Depends(require_permission_flexible("jobs:read")),
    db: Session = Depends(get_db),
):
    """
    Get completed jobs analytics for billing (alias endpoint).

    This is an alias for /api/v1/metrics/jobs/completed to avoid potential URL blocking
    by ad blockers or security tools that block "metrics" in URLs.
    """
    # Set response headers to prevent caching
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    service = MetricsService(db)
    return service.get_completed_jobs(
        tenant_id=current_user.tenant_id,
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
    )
