"""Schema definition-related Pydantic schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SchemaDefinitionCreate(BaseModel):
    """Request model for creating a schema definition."""

    name: str = Field(
        ...,
        description="Unique name for the schema",
        min_length=1,
        max_length=255,
    )
    definitions: dict[str, Any] = Field(
        ..., description="Complete JSON schema definition"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name contains only allowed characters."""
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace only")
        return v.strip()

    @field_validator("definitions")
    @classmethod
    def validate_definitions(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate definitions is not empty."""
        if not v:
            raise ValueError("Definitions cannot be empty")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "invoice_schema_v1",
                "definitions": {
                    "type": "object",
                    "properties": {
                        "vendor_name": {"type": "string"},
                        "invoice_number": {"type": "string"},
                        "total_amount": {"type": "number"},
                        "line_items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "description": {"type": "string"},
                                    "quantity": {"type": "number"},
                                    "price": {"type": "number"},
                                },
                            },
                        },
                    },
                    "required": ["vendor_name", "total_amount"],
                },
            }
        }
    )


class SchemaDefinitionUpdate(BaseModel):
    """Request model for updating a schema definition."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "definitions": {
                    "type": "object",
                    "properties": {
                        "vendor_name": {"type": "string"},
                        "invoice_number": {"type": "string"},
                        "total_amount": {"type": "number"},
                        "tax_amount": {"type": "number"},
                    },
                    "required": ["vendor_name", "total_amount"],
                },
            }
        }
    )

    definitions: dict[str, Any] = Field(
        ..., description="Updated JSON schema definition"
    )

    @field_validator("definitions")
    @classmethod
    def validate_definitions(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate definitions is not empty."""
        if not v:
            raise ValueError("Definitions cannot be empty")
        return v


class SchemaDefinitionResponse(BaseModel):
    """Response model for a schema definition."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440000",
                "name": "invoice_schema_v1",
                "definitions": {
                    "type": "object",
                    "properties": {
                        "vendor_name": {"type": "string"},
                        "total_amount": {"type": "number"},
                    },
                    "required": ["vendor_name", "total_amount"],
                },
                "created_at": "2025-11-02T10:30:00Z",
                "updated_at": "2025-11-02T10:30:00Z",
            }
        }
    )

    id: UUID = Field(..., description="Unique schema identifier")
    name: str = Field(..., description="Schema name")
    definitions: dict[str, Any] = Field(..., description="JSON schema definition")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class SchemaDefinitionListResponse(BaseModel):
    """Response model for listing schema definitions."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "schemas": [
                    {
                        "id": "660e8400-e29b-41d4-a716-446655440000",
                        "name": "invoice_schema_v1",
                        "definitions": {
                            "type": "object",
                            "properties": {"vendor_name": {"type": "string"}},
                        },
                        "created_at": "2025-11-02T10:30:00Z",
                        "updated_at": "2025-11-02T10:30:00Z",
                    }
                ],
                "total": 5,
                "limit": 20,
                "offset": 0,
            }
        }
    )

    schemas: list[SchemaDefinitionResponse] = Field(
        ..., description="List of schema definitions"
    )
    total: int = Field(..., description="Total number of schemas")
    limit: int = Field(..., description="Results per page")
    offset: int = Field(..., description="Offset for pagination")
