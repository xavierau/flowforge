"""Inbound email address management endpoints."""

from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.inbound_email import InboundEmailAddress, InboundEmailLog
from app.models.schema_definition import SchemaDefinition
from app.models.user import User
from app.schemas.inbound_email import (
    InboundEmailAddressCreate,
    InboundEmailAddressUpdate,
    InboundEmailAddressResponse,
    InboundEmailAddressListResponse,
    InboundEmailLogResponse,
    InboundEmailLogListResponse,
)
from app.dependencies.auth import require_permission_flexible
from app.models.enums import Provider

router = APIRouter()

# Valid model providers for inbound email extraction (subset of all providers)
VALID_INBOUND_EMAIL_PROVIDERS = {
    Provider.GOOGLE.value,
    Provider.OPENAI.value,
    Provider.LLAMAEXTRACT.value,
}


def _to_response(address: InboundEmailAddress) -> InboundEmailAddressResponse:
    """
    Convert an InboundEmailAddress model to response schema.

    Includes the full email address using the model's property.

    Args:
        address: The InboundEmailAddress model instance

    Returns:
        InboundEmailAddressResponse with all fields populated
    """
    return InboundEmailAddressResponse(
        id=address.id,
        email_address=address.full_email_address,
        name=address.name,
        description=address.description,
        is_active=address.is_active,
        allowed_senders=address.allowed_senders,
        schema_definition_id=address.schema_definition_id,
        extraction_schema=address.extraction_schema,
        model_provider=address.model_provider,
        model_name=address.model_name,
        split_mode=address.split_mode,
        extraction_mode=address.extraction_mode,
        callback_url=address.callback_url,
        emails_received_count=address.emails_received_count,
        documents_processed_count=address.documents_processed_count,
        last_email_at=address.last_email_at,
        created_at=address.created_at,
        updated_at=address.updated_at,
    )


def _to_log_response(log: InboundEmailLog) -> InboundEmailLogResponse:
    """
    Convert an InboundEmailLog model to response schema.

    Args:
        log: The InboundEmailLog model instance

    Returns:
        InboundEmailLogResponse with all fields populated
    """
    return InboundEmailLogResponse(
        id=log.id,
        sender_email=log.sender_email,
        sender_name=log.sender_name,
        subject=log.subject,
        status=log.status,
        error_message=log.error_message,
        attachment_count=log.attachment_count,
        attachment_names=log.attachment_names,
        document_ids=log.document_ids,
        extraction_job_ids=log.extraction_job_ids,
        received_at=log.received_at,
        processed_at=log.processed_at,
    )


@router.post(
    "/inbound-emails",
    response_model=InboundEmailAddressResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Inbound email address created successfully"},
        400: {"description": "Invalid request (missing schema or invalid provider)"},
        404: {"description": "Schema definition not found"},
        422: {"description": "Validation error"},
    },
)
async def create_inbound_email_address(
    request: InboundEmailAddressCreate,
    current_user: User = Depends(require_permission_flexible("inbound_emails:create")),
    db: Session = Depends(get_db),
) -> InboundEmailAddressResponse:
    """
    Create a new inbound email address for document processing.

    Supports both JWT and API token authentication.

    Required Permission: inbound_emails:create

    The created email address can receive documents via email, which will be
    automatically processed using the configured schema and model settings.

    Args:
        request: Inbound email address creation request
        current_user: Authenticated user with inbound_emails:create permission
        db: Database session

    Returns:
        Created inbound email address with full email address

    Raises:
        HTTPException: 400 if schema validation fails or invalid provider
        HTTPException: 404 if schema_definition_id is provided but not found
    """
    # Validate: at least one schema source must be provided
    if not request.schema_definition_id and not request.extraction_schema:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either schema_definition_id or extraction_schema must be provided",
        )

    # Validate schema_definition_id belongs to tenant if provided
    if request.schema_definition_id:
        schema_def = (
            db.query(SchemaDefinition)
            .filter(SchemaDefinition.tenant_id == current_user.tenant_id)
            .filter(SchemaDefinition.id == request.schema_definition_id)
            .first()
        )
        if not schema_def:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schema definition with ID '{request.schema_definition_id}' not found",
            )

    # Validate model_provider
    if request.model_provider not in VALID_INBOUND_EMAIL_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model_provider. Must be one of: {', '.join(sorted(VALID_INBOUND_EMAIL_PROVIDERS))}",
        )

    # Generate unique email prefix using UUID
    email_prefix = str(uuid4()).replace("-", "")[:24]

    # Create inbound email address
    inbound_address = InboundEmailAddress(
        tenant_id=current_user.tenant_id,
        created_by_user_id=current_user.id,
        email_prefix=email_prefix,
        name=request.name,
        description=request.description,
        allowed_senders=request.allowed_senders,
        schema_definition_id=request.schema_definition_id,
        extraction_schema=request.extraction_schema,
        model_provider=request.model_provider,
        model_name=request.model_name,
        custom_prompt=request.custom_prompt,
        split_mode=request.split_mode,
        extraction_mode=request.extraction_mode,
        markdown_converter=request.markdown_converter,
        markdown_format=request.markdown_format,
        llamaextract_mode=request.llamaextract_mode,
        llamaextract_target=request.llamaextract_target,
        callback_url=request.callback_url,
        is_active=True,
    )

    db.add(inbound_address)
    db.commit()
    db.refresh(inbound_address)

    return _to_response(inbound_address)


@router.get(
    "/inbound-emails",
    response_model=InboundEmailAddressListResponse,
    responses={
        200: {"description": "List of inbound email addresses"},
    },
)
async def list_inbound_email_addresses(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(require_permission_flexible("inbound_emails:read")),
    db: Session = Depends(get_db),
) -> InboundEmailAddressListResponse:
    """
    List inbound email addresses for the current tenant.

    Supports both JWT and API token authentication.

    Required Permission: inbound_emails:read

    Args:
        is_active: Optional filter by active status
        limit: Number of results per page (1-100)
        offset: Pagination offset
        current_user: Authenticated user with inbound_emails:read permission
        db: Database session

    Returns:
        List of inbound email addresses with pagination info (filtered by tenant)
    """
    # Build query with tenant isolation FIRST
    query = db.query(InboundEmailAddress).filter(
        InboundEmailAddress.tenant_id == current_user.tenant_id
    )

    # Apply optional filter
    if is_active is not None:
        query = query.filter(InboundEmailAddress.is_active == is_active)

    # Get total count
    total = query.count()

    # Get paginated results
    addresses = (
        query.order_by(InboundEmailAddress.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return InboundEmailAddressListResponse(
        addresses=[_to_response(addr) for addr in addresses],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/inbound-emails/{address_id}",
    response_model=InboundEmailAddressResponse,
    responses={
        200: {"description": "Inbound email address details"},
        404: {"description": "Inbound email address not found"},
    },
)
async def get_inbound_email_address(
    address_id: UUID,
    current_user: User = Depends(require_permission_flexible("inbound_emails:read")),
    db: Session = Depends(get_db),
) -> InboundEmailAddressResponse:
    """
    Get a single inbound email address by ID.

    Supports both JWT and API token authentication.

    Required Permission: inbound_emails:read

    Args:
        address_id: Inbound email address UUID
        current_user: Authenticated user with inbound_emails:read permission
        db: Database session

    Returns:
        Inbound email address details

    Raises:
        HTTPException: 404 if address not found or belongs to different tenant
    """
    # Query with tenant filter FIRST to prevent cross-tenant access
    address = (
        db.query(InboundEmailAddress)
        .filter(InboundEmailAddress.tenant_id == current_user.tenant_id)
        .filter(InboundEmailAddress.id == address_id)
        .first()
    )

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inbound email address with ID '{address_id}' not found",
        )

    return _to_response(address)


@router.put(
    "/inbound-emails/{address_id}",
    response_model=InboundEmailAddressResponse,
    responses={
        200: {"description": "Inbound email address updated successfully"},
        400: {"description": "Invalid request"},
        404: {"description": "Inbound email address not found"},
    },
)
async def update_inbound_email_address(
    address_id: UUID,
    request: InboundEmailAddressUpdate,
    current_user: User = Depends(require_permission_flexible("inbound_emails:update")),
    db: Session = Depends(get_db),
) -> InboundEmailAddressResponse:
    """
    Update an inbound email address.

    Supports both JWT and API token authentication.

    Required Permission: inbound_emails:update

    Only fields that are provided will be updated.

    Args:
        address_id: Inbound email address UUID
        request: Update request with fields to modify
        current_user: Authenticated user with inbound_emails:update permission
        db: Database session

    Returns:
        Updated inbound email address

    Raises:
        HTTPException: 404 if address not found or belongs to different tenant
        HTTPException: 400 if invalid provider specified
    """
    # Query with tenant filter FIRST to prevent cross-tenant access
    address = (
        db.query(InboundEmailAddress)
        .filter(InboundEmailAddress.tenant_id == current_user.tenant_id)
        .filter(InboundEmailAddress.id == address_id)
        .first()
    )

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inbound email address with ID '{address_id}' not found",
        )

    # Get update data excluding unset fields
    update_data = request.model_dump(exclude_unset=True)

    # Validate model_provider if being updated
    if "model_provider" in update_data:
        if update_data["model_provider"] not in VALID_INBOUND_EMAIL_PROVIDERS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model_provider. Must be one of: {', '.join(sorted(VALID_INBOUND_EMAIL_PROVIDERS))}",
            )

    # Validate schema_definition_id if being updated
    if "schema_definition_id" in update_data and update_data["schema_definition_id"]:
        schema_def = (
            db.query(SchemaDefinition)
            .filter(SchemaDefinition.tenant_id == current_user.tenant_id)
            .filter(SchemaDefinition.id == update_data["schema_definition_id"])
            .first()
        )
        if not schema_def:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schema definition with ID '{update_data['schema_definition_id']}' not found",
            )

    # Apply updates
    for field, value in update_data.items():
        setattr(address, field, value)

    db.commit()
    db.refresh(address)

    return _to_response(address)


@router.delete(
    "/inbound-emails/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Inbound email address deleted (soft delete)"},
        404: {"description": "Inbound email address not found"},
    },
)
async def delete_inbound_email_address(
    address_id: UUID,
    current_user: User = Depends(require_permission_flexible("inbound_emails:delete")),
    db: Session = Depends(get_db),
) -> None:
    """
    Soft delete an inbound email address (sets is_active=False).

    Supports both JWT and API token authentication.

    Required Permission: inbound_emails:delete

    This is a soft delete operation - the address is deactivated but not removed.
    The email address will no longer accept incoming emails.

    Args:
        address_id: Inbound email address UUID
        current_user: Authenticated user with inbound_emails:delete permission
        db: Database session

    Raises:
        HTTPException: 404 if address not found or belongs to different tenant
    """
    # Query with tenant filter FIRST to prevent cross-tenant access
    address = (
        db.query(InboundEmailAddress)
        .filter(InboundEmailAddress.tenant_id == current_user.tenant_id)
        .filter(InboundEmailAddress.id == address_id)
        .first()
    )

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inbound email address with ID '{address_id}' not found",
        )

    # Soft delete by setting is_active to False
    address.is_active = False
    db.commit()


@router.get(
    "/inbound-emails/{address_id}/logs",
    response_model=InboundEmailLogListResponse,
    responses={
        200: {"description": "List of processing logs for the address"},
        404: {"description": "Inbound email address not found"},
    },
)
async def get_inbound_email_logs(
    address_id: UUID,
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200, description="Results per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(require_permission_flexible("inbound_emails:read")),
    db: Session = Depends(get_db),
) -> InboundEmailLogListResponse:
    """
    Get processing logs for an inbound email address.

    Supports both JWT and API token authentication.

    Required Permission: inbound_emails:read

    Args:
        address_id: Inbound email address UUID
        status_filter: Optional filter by processing status
        limit: Number of results per page (1-200)
        offset: Pagination offset
        current_user: Authenticated user with inbound_emails:read permission
        db: Database session

    Returns:
        List of processing logs with pagination info

    Raises:
        HTTPException: 404 if address not found or belongs to different tenant
    """
    # Verify address belongs to tenant FIRST
    address = (
        db.query(InboundEmailAddress)
        .filter(InboundEmailAddress.tenant_id == current_user.tenant_id)
        .filter(InboundEmailAddress.id == address_id)
        .first()
    )

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inbound email address with ID '{address_id}' not found",
        )

    # Build query for logs
    query = db.query(InboundEmailLog).filter(
        InboundEmailLog.inbound_email_address_id == address_id
    )

    # Apply optional status filter
    if status_filter:
        query = query.filter(InboundEmailLog.status == status_filter)

    # Get total count
    total = query.count()

    # Get paginated results
    logs = (
        query.order_by(InboundEmailLog.received_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return InboundEmailLogListResponse(
        logs=[_to_log_response(log) for log in logs],
        total=total,
        limit=limit,
        offset=offset,
    )
