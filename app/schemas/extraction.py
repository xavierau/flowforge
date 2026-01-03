"""Extraction-related Pydantic schemas."""

import logging
from datetime import datetime
from typing import Any, Optional, List, Tuple
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


def resolve_mode_fields(
    split_mode: str,
    extraction_mode: str,
    processing_mode: Optional[str]
) -> Tuple[str, str]:
    """
    Resolve split_mode and extraction_mode from request fields.

    Handles backward compatibility by mapping deprecated processing_mode
    to the new granular fields if provided.

    Args:
        split_mode: The split_mode from request (default: 'batch')
        extraction_mode: The extraction_mode from request (default: 'vllm')
        processing_mode: The deprecated processing_mode (optional)

    Returns:
        Tuple of (resolved_split_mode, resolved_extraction_mode)
    """
    # If processing_mode is provided and new fields are at defaults,
    # map the deprecated field to new fields
    if processing_mode and split_mode == "batch" and extraction_mode == "vllm":
        if processing_mode == "batch":
            return "batch", "vllm"
        elif processing_mode in ("per_page", "direct"):
            return "per_page", "vllm"
        elif processing_mode == "markdown":
            return "batch", "markdown"
        else:
            # Unknown processing_mode value - log warning and use defaults
            logger.warning(
                f"Unknown processing_mode '{processing_mode}' ignored. "
                f"Using defaults: split_mode='batch', extraction_mode='vllm'"
            )

    # Otherwise use the new fields as-is
    return split_mode, extraction_mode


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

    Mode Configuration:
    - split_mode: How pages are grouped - 'per_page', 'batch', or 'auto'
    - extraction_mode: How extraction is performed - 'vllm' or 'markdown'

    Backward Compatibility:
    - processing_mode is deprecated but still accepted
    - If processing_mode is provided without split_mode/extraction_mode, it will be mapped:
      - 'batch' -> split_mode='batch', extraction_mode='vllm'
      - 'per_page' -> split_mode='per_page', extraction_mode='vllm'
      - 'markdown' -> split_mode='batch', extraction_mode='markdown'
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

    # New granular mode fields
    split_mode: str = Field(
        default="batch",
        description="Split mode: 'per_page' (N calls), 'batch' (1 call), or 'auto' (LLM splitter - costs extra credits)"
    )
    extraction_mode: str = Field(
        default="vllm",
        description="Extraction mode: 'vllm' (direct vision extraction) or 'markdown' (markdown pipeline)"
    )

    # Deprecated - use split_mode and extraction_mode instead
    processing_mode: Optional[str] = Field(
        default=None,
        description="DEPRECATED: Use split_mode and extraction_mode instead. Kept for backward compatibility."
    )

    markdown_converter: Optional[str] = Field(
        None, description="Markdown converter (only for extraction_mode='markdown'): 'gemini_vision' or 'gpt4v'"
    )
    markdown_format: Optional[str] = Field(
        default="table_heavy",
        description="Markdown format style (only for extraction_mode='markdown'): 'standard', 'table_heavy', or 'layout_preserved'"
    )
    llamaextract_mode: Optional[str] = Field(
        default="standard",
        description="LlamaExtract extraction mode: 'standard' (1 credit/page) or 'premium' (2 credits/page)"
    )
    llamaextract_target: Optional[str] = Field(
        default="per_doc",
        description="LlamaExtract extraction target: 'per_doc' (single JSON) or 'per_page' (array of JSON per page)"
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
                "split_mode": "batch",
                "extraction_mode": "vllm",
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

    Mode Configuration:
    - split_mode: How pages are grouped - 'per_page', 'batch', or 'auto'
    - extraction_mode: How extraction is performed - 'vllm' or 'markdown'

    Backward Compatibility:
    - processing_mode is deprecated but still accepted
    - If processing_mode is provided without split_mode/extraction_mode, it will be mapped:
      - 'batch' -> split_mode='batch', extraction_mode='vllm'
      - 'per_page' -> split_mode='per_page', extraction_mode='vllm'
      - 'markdown' -> split_mode='batch', extraction_mode='markdown'
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

    # New granular mode fields
    split_mode: str = Field(
        default="batch",
        description="Split mode: 'per_page' (N calls), 'batch' (1 call), or 'auto' (LLM splitter - costs extra credits)"
    )
    extraction_mode: str = Field(
        default="vllm",
        description="Extraction mode: 'vllm' (direct vision extraction) or 'markdown' (markdown pipeline)"
    )

    # Deprecated - use split_mode and extraction_mode instead
    processing_mode: Optional[str] = Field(
        default=None,
        description="DEPRECATED: Use split_mode and extraction_mode instead. Kept for backward compatibility."
    )

    markdown_converter: Optional[str] = Field(
        None, description="Markdown converter (only for extraction_mode='markdown'): 'gemini_vision' or 'gpt4v'"
    )
    markdown_format: Optional[str] = Field(
        default="table_heavy",
        description="Markdown format style (only for extraction_mode='markdown'): 'standard', 'table_heavy', or 'layout_preserved'"
    )
    llamaextract_mode: Optional[str] = Field(
        default="standard",
        description="LlamaExtract extraction mode: 'standard' (1 credit/page) or 'premium' (2 credits/page)"
    )
    llamaextract_target: Optional[str] = Field(
        default="per_doc",
        description="LlamaExtract extraction target: 'per_doc' (single JSON) or 'per_page' (array of JSON per page)"
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
                "split_mode": "batch",
                "extraction_mode": "vllm",
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
