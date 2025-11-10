"""Extraction-related Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Model configuration for extraction."""

    provider: str = Field(..., description="VLLM provider (google or openai)")
    model: str = Field(..., description="Model name")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "provider": "google",
                "model": "gemini-2.5-flash",
            }
        }


class ParseRequest(BaseModel):
    """Request model for document parsing.

    Either schema_definition_id OR extraction_schema must be provided.
    If both are provided, schema_definition_id takes precedence.
    """

    schema_definition_id: Optional[UUID] = Field(
        None, description="ID of saved schema definition to use (takes precedence if both provided)"
    )
    extraction_schema: Optional[dict[str, Any]] = Field(
        None, description="Custom JSON schema for extraction (used if schema_definition_id not provided)"
    )
    custom_prompt: Optional[str] = Field(
        None, description="Custom extraction instructions"
    )
    model_provider_config: ModelConfig = Field(..., description="Model configuration")
    processing_mode: str = Field(
        default="batch",
        description="Processing mode: 'batch' (all pages in one call) or 'per_page' (individual processing)"
    )
    callback_url: Optional[str] = Field(
        None, description="Optional webhook URL to POST results to when job completes"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "extraction_schema": {
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
                "custom_prompt": "Extract invoice details. Pay attention to line items.",
                "model_provider_config": {
                    "provider": "google",
                    "model": "gemini-2.5-flash",
                },
                "processing_mode": "batch",
                "callback_url": "https://example.com/webhooks/extraction-complete",
            }
        }


class ParseResponse(BaseModel):
    """Response model for parse request."""

    extraction_job_id: UUID = Field(..., description="Unique job identifier")
    document_id: UUID = Field(..., description="Document being processed")
    status: str = Field(..., description="Job status")
    estimated_time_seconds: int = Field(
        ..., description="Estimated processing time"
    )
    created_at: datetime = Field(..., description="Job creation timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True
        json_schema_extra = {
            "example": {
                "extraction_job_id": "660e8400-e29b-41d4-a716-446655440000",
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "queued",
                "estimated_time_seconds": 15,
                "created_at": "2025-11-02T10:31:00Z",
            }
        }


class ExtractRequest(BaseModel):
    """Request model for combined upload+extract operation.

    Either schema_definition_id OR extraction_schema must be provided.
    If both are provided, schema_definition_id takes precedence.
    """

    schema_definition_id: Optional[UUID] = Field(
        None, description="ID of saved schema definition to use (takes precedence if both provided)"
    )
    extraction_schema: Optional[dict[str, Any]] = Field(
        None, description="Custom JSON schema for extraction (used if schema_definition_id not provided)"
    )
    custom_prompt: Optional[str] = Field(
        None, description="Custom extraction instructions"
    )
    model_provider_config: ModelConfig = Field(..., description="Model configuration")
    processing_mode: str = Field(
        default="batch",
        description="Processing mode: 'batch' (all pages in one call) or 'per_page' (individual processing)"
    )
    callback_url: Optional[str] = Field(
        None, description="Optional webhook URL to POST results to when job completes"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "schema_definition_id": "550e8400-e29b-41d4-a716-446655440000",
                "custom_prompt": "Extract invoice details accurately",
                "model_provider_config": {
                    "provider": "google",
                    "model": "gemini-2.5-flash",
                },
                "processing_mode": "batch",
                "callback_url": "https://example.com/webhooks/extraction-complete",
            }
        }


class ExtractResponse(BaseModel):
    """Response model for combined extract request."""

    extraction_job_id: UUID = Field(..., description="Unique job identifier")
    document_id: UUID = Field(..., description="Document being processed")
    status: str = Field(..., description="Job status")
    message: str = Field(..., description="Status message")
    estimated_time_seconds: int = Field(
        ..., description="Estimated total processing time"
    )
    created_at: datetime = Field(..., description="Job creation timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True
        json_schema_extra = {
            "example": {
                "extraction_job_id": "660e8400-e29b-41d4-a716-446655440000",
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "queued",
                "message": "Document uploaded and extraction job queued",
                "estimated_time_seconds": 30,
                "created_at": "2025-11-03T10:31:00Z",
            }
        }
