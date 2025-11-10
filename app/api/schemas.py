"""Schema definition management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.schema_definition import SchemaDefinition
from app.models.user import User
from app.schemas.schema_definition import (
    SchemaDefinitionCreate,
    SchemaDefinitionUpdate,
    SchemaDefinitionResponse,
    SchemaDefinitionListResponse,
)
from app.services.schema_validator import SchemaValidator
from app.dependencies.auth import require_permission_flexible

router = APIRouter()


@router.post(
    "/schemas",
    response_model=SchemaDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Schema created successfully"},
        400: {"description": "Invalid schema definition"},
        409: {"description": "Schema with this name already exists for this tenant"},
        422: {"description": "Validation error"},
    },
)
async def create_schema(
    request: SchemaDefinitionCreate,
    current_user: User = Depends(require_permission_flexible("schemas:create")),
    db: Session = Depends(get_db),
) -> SchemaDefinitionResponse:
    """
    Create a new schema definition (tenant-scoped).

    Supports both JWT and API token authentication.

    Required Permission: schemas:create

    Args:
        request: Schema creation request
        current_user: Authenticated user with schemas:create permission
        db: Database session

    Returns:
        Created schema definition

    Raises:
        HTTPException: 400 if schema is invalid, 409 if name exists for tenant
    """
    # Validate JSON schema structure
    validator = SchemaValidator()
    if not validator.is_valid_schema(request.definitions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON schema definition",
        )

    # Create schema definition with tenant isolation
    schema_def = SchemaDefinition(
        tenant_id=current_user.tenant_id,  # Set tenant_id for multi-tenancy
        name=request.name,
        definitions=request.definitions,
    )

    db.add(schema_def)

    try:
        db.commit()
        db.refresh(schema_def)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Schema with name '{request.name}' already exists for your tenant",
        )

    return SchemaDefinitionResponse.model_validate(schema_def)


@router.get(
    "/schemas",
    response_model=SchemaDefinitionListResponse,
    responses={
        200: {"description": "List of schema definitions"},
    },
)
async def list_schemas(
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(require_permission_flexible("schemas:read")),
    db: Session = Depends(get_db),
) -> SchemaDefinitionListResponse:
    """
    List all schema definitions with pagination (tenant-scoped).

    Supports both JWT and API token authentication.

    Required Permission: schemas:read

    Args:
        limit: Number of results per page (1-100)
        offset: Pagination offset
        current_user: Authenticated user with schemas:read permission
        db: Database session

    Returns:
        List of schema definitions with pagination info (filtered by tenant)
    """
    # Build query with tenant isolation
    query = db.query(SchemaDefinition).filter(
        SchemaDefinition.tenant_id == current_user.tenant_id
    )

    # Get total count
    total = query.count()

    # Get paginated results
    schemas = (
        query.order_by(SchemaDefinition.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return SchemaDefinitionListResponse(
        schemas=[SchemaDefinitionResponse.model_validate(s) for s in schemas],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/schemas/{schema_id}",
    response_model=SchemaDefinitionResponse,
    responses={
        200: {"description": "Schema definition"},
        404: {"description": "Schema not found"},
    },
)
async def get_schema_by_id(
    schema_id: UUID,
    current_user: User = Depends(require_permission_flexible("schemas:read")),
    db: Session = Depends(get_db),
) -> SchemaDefinitionResponse:
    """
    Get a schema definition by ID (tenant-scoped).

    Supports both JWT and API token authentication.

    Required Permission: schemas:read

    Args:
        schema_id: Schema UUID
        current_user: Authenticated user with schemas:read permission
        db: Database session

    Returns:
        Schema definition

    Raises:
        HTTPException: 404 if schema not found or belongs to different tenant
    """
    # Query with tenant filter FIRST to prevent cross-tenant access
    schema_def = (
        db.query(SchemaDefinition)
        .filter(SchemaDefinition.tenant_id == current_user.tenant_id)
        .filter(SchemaDefinition.id == schema_id)
        .first()
    )

    if not schema_def:
        # Don't reveal if schema exists in another tenant
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema with ID '{schema_id}' not found",
        )

    return SchemaDefinitionResponse.model_validate(schema_def)


@router.get(
    "/schemas/name/{schema_name}",
    response_model=SchemaDefinitionResponse,
    responses={
        200: {"description": "Schema definition"},
        404: {"description": "Schema not found"},
    },
)
async def get_schema_by_name(
    schema_name: str,
    current_user: User = Depends(require_permission_flexible("schemas:read")),
    db: Session = Depends(get_db),
) -> SchemaDefinitionResponse:
    """
    Get a schema definition by name (tenant-scoped).

    Supports both JWT and API token authentication.

    Required Permission: schemas:read

    Args:
        schema_name: Schema name
        current_user: Authenticated user with schemas:read permission
        db: Database session

    Returns:
        Schema definition

    Raises:
        HTTPException: 404 if schema not found or belongs to different tenant
    """
    # Query with tenant filter FIRST to prevent cross-tenant access
    schema_def = (
        db.query(SchemaDefinition)
        .filter(SchemaDefinition.tenant_id == current_user.tenant_id)
        .filter(SchemaDefinition.name == schema_name)
        .first()
    )

    if not schema_def:
        # Don't reveal if schema exists in another tenant
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema with name '{schema_name}' not found",
        )

    return SchemaDefinitionResponse.model_validate(schema_def)


@router.put(
    "/schemas/{schema_id}",
    response_model=SchemaDefinitionResponse,
    responses={
        200: {"description": "Schema updated successfully"},
        400: {"description": "Invalid schema definition"},
        404: {"description": "Schema not found"},
    },
)
async def update_schema(
    schema_id: UUID,
    request: SchemaDefinitionUpdate,
    current_user: User = Depends(require_permission_flexible("schemas:update")),
    db: Session = Depends(get_db),
) -> SchemaDefinitionResponse:
    """
    Update a schema definition (definitions only, name is immutable).

    Supports both JWT and API token authentication.

    Required Permission: schemas:update

    Args:
        schema_id: Schema UUID
        request: Schema update request
        current_user: Authenticated user with schemas:update permission
        db: Database session

    Returns:
        Updated schema definition

    Raises:
        HTTPException: 404 if schema not found or belongs to different tenant, 400 if schema invalid
    """
    # Validate JSON schema structure
    validator = SchemaValidator()
    if not validator.is_valid_schema(request.definitions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON schema definition",
        )

    # Get existing schema with tenant filter FIRST
    schema_def = (
        db.query(SchemaDefinition)
        .filter(SchemaDefinition.tenant_id == current_user.tenant_id)
        .filter(SchemaDefinition.id == schema_id)
        .first()
    )

    if not schema_def:
        # Don't reveal if schema exists in another tenant
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema with ID '{schema_id}' not found",
        )

    # Update definitions only (name is immutable)
    schema_def.definitions = request.definitions

    db.commit()
    db.refresh(schema_def)

    return SchemaDefinitionResponse.model_validate(schema_def)


@router.delete(
    "/schemas/{schema_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Schema deleted successfully"},
        404: {"description": "Schema not found"},
    },
)
async def delete_schema(
    schema_id: UUID,
    current_user: User = Depends(require_permission_flexible("schemas:delete")),
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a schema definition (tenant-scoped).

    Supports both JWT and API token authentication.

    Required Permission: schemas:delete

    Args:
        schema_id: Schema UUID
        current_user: Authenticated user with schemas:delete permission
        db: Database session

    Raises:
        HTTPException: 404 if schema not found or belongs to different tenant
    """
    # Get schema with tenant filter FIRST to prevent cross-tenant deletion
    schema_def = (
        db.query(SchemaDefinition)
        .filter(SchemaDefinition.tenant_id == current_user.tenant_id)
        .filter(SchemaDefinition.id == schema_id)
        .first()
    )

    if not schema_def:
        # Don't reveal if schema exists in another tenant
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema with ID '{schema_id}' not found",
        )

    db.delete(schema_def)
    db.commit()
