"""Extraction-related Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelConfig(BaseModel):
    """Model configuration for extraction."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "provider": "google",
                "model": "gemini-2.5-flash",
            }
        }
    )

    provider: str = Field(..., description="VLLM provider (google or openai)")
    model: str = Field(..., description="Model name")


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
        description="Processing mode: 'batch' (all pages in one call), 'per_page' (individual processing), or 'markdown' (vision → markdown → JSON pipeline)"
    )
    markdown_converter: Optional[str] = Field(
        None, description="Markdown converter (only for markdown mode): 'gemini_vision' or 'gpt4v'"
    )
    markdown_format: Optional[str] = Field(
        default="table_heavy",
        description="Markdown format style (only for markdown mode): 'standard', 'table_heavy', or 'layout_preserved'"
    )
    callback_url: Optional[str] = Field(
        None, description="Optional webhook URL to POST results to when job completes"
    )

    model_config = ConfigDict(
        json_schema_extra={
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
    )


class ParseResponse(BaseModel):
    """Response model for parse request."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "extraction_job_id": "660e8400-e29b-41d4-a716-446655440000",
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "queued",
                "estimated_time_seconds": 15,
                "created_at": "2025-11-02T10:31:00Z",
            }
        }
    )

    extraction_job_id: UUID = Field(..., description="Unique job identifier")
    document_id: UUID = Field(..., description="Document being processed")
    status: str = Field(..., description="Job status")
    estimated_time_seconds: int = Field(
        ..., description="Estimated processing time"
    )
    created_at: datetime = Field(..., description="Job creation timestamp")


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
        description="Processing mode: 'batch' (all pages in one call), 'per_page' (individual processing), or 'markdown' (vision → markdown → JSON pipeline)"
    )
    markdown_converter: Optional[str] = Field(
        None, description="Markdown converter (only for markdown mode): 'gemini_vision' or 'gpt4v'"
    )
    markdown_format: Optional[str] = Field(
        default="table_heavy",
        description="Markdown format style (only for markdown mode): 'standard', 'table_heavy', or 'layout_preserved'"
    )
    callback_url: Optional[str] = Field(
        None, description="Optional webhook URL to POST results to when job completes"
    )

    model_config = ConfigDict(
        json_schema_extra={
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
    )


class ExtractResponse(BaseModel):
    """Response model for combined extract request."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "extraction_job_id": "660e8400-e29b-41d4-a716-446655440000",
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "queued",
                "message": "Document uploaded and extraction job queued",
                "estimated_time_seconds": 30,
                "created_at": "2025-11-03T10:31:00Z",
            }
        }
    )

    extraction_job_id: UUID = Field(..., description="Unique job identifier")
    document_id: UUID = Field(..., description="Document being processed")
    status: str = Field(..., description="Job status")
    message: str = Field(..., description="Status message")
    estimated_time_seconds: int = Field(
        ..., description="Estimated total processing time"
    )
    created_at: datetime = Field(..., description="Job creation timestamp")


class DocumentPageResponse(BaseModel):
    """Response model for document page with markdown content."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "770e8400-e29b-41d4-a716-446655440000",
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "page_number": 1,
                "image_path": "documents/example.png",
                "preprocessed_image_path": "documents/example_preprocessed.png",
                "markdown_content": "<!-- PAGE 1 -->\n# Invoice\n...",
                "markdown_provider": "gemini_vision",
                "markdown_generated_at": "2025-11-17T10:31:00Z",
                "status": "completed",
                "created_at": "2025-11-17T10:30:00Z",
            }
        }
    )

    id: UUID = Field(..., description="Page unique identifier")
    document_id: UUID = Field(..., description="Parent document ID")
    page_number: int = Field(..., description="Page number (1-indexed)")
    image_path: str = Field(..., description="Original image storage path")
    preprocessed_image_path: Optional[str] = Field(
        None, description="Preprocessed image storage path"
    )
    markdown_content: Optional[str] = Field(
        None, description="Generated markdown content"
    )
    markdown_provider: Optional[str] = Field(
        None, description="Provider used for markdown generation"
    )
    markdown_generated_at: Optional[datetime] = Field(
        None, description="When markdown was generated"
    )
    status: str = Field(..., description="Page processing status")
    created_at: datetime = Field(..., description="Page creation timestamp")
