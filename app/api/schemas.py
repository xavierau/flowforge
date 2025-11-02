"""Schema definition management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.schema_definition import SchemaDefinition
from app.schemas.schema_definition import (
    SchemaDefinitionCreate,
    SchemaDefinitionUpdate,
    SchemaDefinitionResponse,
    SchemaDefinitionListResponse,
)
from app.services.schema_validator import SchemaValidator

router = APIRouter()


@router.post(
    "/schemas",
    response_model=SchemaDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Schema created successfully"},
        400: {"description": "Invalid schema definition"},
        409: {"description": "Schema with this name already exists"},
        422: {"description": "Validation error"},
    },
)
async def create_schema(
    request: SchemaDefinitionCreate,
    db: Session = Depends(get_db),
) -> SchemaDefinitionResponse:
    """
    Create a new schema definition.

    Args:
        request: Schema creation request
        db: Database session

    Returns:
        Created schema definition

    Raises:
        HTTPException: 400 if schema is invalid, 409 if name exists
    """
    # Validate JSON schema structure
    validator = SchemaValidator()
    if not validator.is_valid_schema(request.definitions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON schema definition",
        )

    # Create schema definition
    schema_def = SchemaDefinition(
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
            detail=f"Schema with name '{request.name}' already exists",
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
    db: Session = Depends(get_db),
) -> SchemaDefinitionListResponse:
    """
    List all schema definitions with pagination.

    Args:
        limit: Number of results per page (1-100)
        offset: Pagination offset
        db: Database session

    Returns:
        List of schema definitions with pagination info
    """
    # Get total count
    total = db.query(SchemaDefinition).count()

    # Get paginated results
    schemas = (
        db.query(SchemaDefinition)
        .order_by(SchemaDefinition.created_at.desc())
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
    db: Session = Depends(get_db),
) -> SchemaDefinitionResponse:
    """
    Get a schema definition by ID.

    Args:
        schema_id: Schema UUID
        db: Database session

    Returns:
        Schema definition

    Raises:
        HTTPException: 404 if schema not found
    """
    schema_def = db.query(SchemaDefinition).filter(SchemaDefinition.id == schema_id).first()

    if not schema_def:
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
    db: Session = Depends(get_db),
) -> SchemaDefinitionResponse:
    """
    Get a schema definition by name.

    Args:
        schema_name: Schema name
        db: Database session

    Returns:
        Schema definition

    Raises:
        HTTPException: 404 if schema not found
    """
    schema_def = (
        db.query(SchemaDefinition).filter(SchemaDefinition.name == schema_name).first()
    )

    if not schema_def:
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
    db: Session = Depends(get_db),
) -> SchemaDefinitionResponse:
    """
    Update a schema definition (definitions only, name is immutable).

    Args:
        schema_id: Schema UUID
        request: Schema update request
        db: Database session

    Returns:
        Updated schema definition

    Raises:
        HTTPException: 404 if schema not found, 400 if schema invalid
    """
    # Validate JSON schema structure
    validator = SchemaValidator()
    if not validator.is_valid_schema(request.definitions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON schema definition",
        )

    # Get existing schema
    schema_def = db.query(SchemaDefinition).filter(SchemaDefinition.id == schema_id).first()

    if not schema_def:
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
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a schema definition.

    Args:
        schema_id: Schema UUID
        db: Database session

    Raises:
        HTTPException: 404 if schema not found
    """
    schema_def = db.query(SchemaDefinition).filter(SchemaDefinition.id == schema_id).first()

    if not schema_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema with ID '{schema_id}' not found",
        )

    db.delete(schema_def)
    db.commit()
