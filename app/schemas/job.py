"""Job-related Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobProgress(BaseModel):
    """Job progress information."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_pages": 3,
                "completed_pages": 1,
            }
        }
    )

    total_pages: int = Field(..., description="Total number of pages")
    completed_pages: int = Field(..., description="Completed pages")


class JobStatusResponse(BaseModel):
    """Response model for job status."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "job_id": "660e8400-e29b-41d4-a716-446655440000",
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "progress": {
                    "total_pages": 3,
                    "completed_pages": 1,
                },
                "started_at": "2025-11-02T10:31:05Z",
                "updated_at": "2025-11-02T10:31:12Z",
                "error": None,
            }
        }
    )

    job_id: UUID = Field(..., description="Job identifier")
    document_id: UUID = Field(..., description="Document identifier")
    status: str = Field(..., description="Job status")
    progress: Optional[JobProgress] = Field(None, description="Progress information")
    started_at: Optional[datetime] = Field(None, description="Job start time")
    updated_at: datetime = Field(..., description="Last update time")
    error: Optional[str] = Field(None, description="Error message if failed")


class ExtractionMetadata(BaseModel):
    """Metadata about the extraction process."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model_used": "google/gemini-2.5-flash",
                "input_tokens": 1050,
                "output_tokens": 200,
                "tokens_used": 1250,
                "processing_time_ms": 8500,
                "confidence_score": 0.95,
            }
        }
    )

    model_used: str = Field(..., description="Model that performed extraction")
    input_tokens: int = Field(..., description="Input tokens (image + prompt)")
    output_tokens: int = Field(..., description="Output tokens (generated response)")
    tokens_used: int = Field(..., description="Total tokens consumed (input + output)")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    confidence_score: float = Field(..., description="Confidence score (0-1)")


class JobResultResponse(BaseModel):
    """Response model for job results."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "job_id": "660e8400-e29b-41d4-a716-446655440000",
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "extracted_data": {
                    "vendor_name": "ACME Corp",
                    "invoice_number": "INV-2024-001",
                    "total_amount": 1250.00,
                    "line_items": [
                        {
                            "description": "Widget A",
                            "quantity": 10,
                            "price": 100.00,
                        }
                    ],
                },
                "metadata": {
                    "model_used": "gemini-pro-vision",
                    "tokens_used": 1250,
                    "processing_time_ms": 8500,
                    "confidence_score": 0.95,
                },
                "completed_at": "2025-11-02T10:31:20Z",
            }
        }
    )

    job_id: UUID = Field(..., description="Job identifier")
    document_id: UUID = Field(..., description="Document identifier")
    schema_definition_id: Optional[UUID] = Field(None, description="ID of saved schema definition used (null if custom schema)")
    status: str = Field(..., description="Job status")
    extracted_data: dict[str, Any] = Field(..., description="Extracted structured data")
    metadata: ExtractionMetadata = Field(..., description="Extraction metadata")
    completed_at: datetime = Field(..., description="Completion timestamp")
    # Job configuration used for this extraction
    extraction_schema: dict[str, Any] = Field(..., description="JSON Schema used for extraction")
    custom_prompt: Optional[str] = Field(None, description="Custom extraction prompt")
    model_provider: str = Field(..., description="Model provider (google, openai, deepseek)")
    model_name: str = Field(..., description="Model name")
    callback_url: Optional[str] = Field(None, description="Webhook callback URL")
    # New granular mode fields
    split_mode: Optional[str] = Field(None, description="Split mode: per_page, batch, auto")
    extraction_mode: Optional[str] = Field(None, description="Extraction mode: vllm, markdown")
    processing_mode: Optional[str] = Field(None, description="DEPRECATED: Use split_mode + extraction_mode")
    # Thinking mode fields
    enable_thinking: Optional[bool] = Field(None, description="Whether thinking mode was enabled")
    thinking_budget: Optional[int] = Field(None, description="Thinking budget in tokens")


class JobListItem(BaseModel):
    """Individual job item in list response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Job identifier")
    document_id: UUID = Field(..., description="Document identifier")
    document_name: Optional[str] = Field(None, description="Document name")
    schema_definition_id: Optional[UUID] = Field(None, description="ID of saved schema definition used (null if custom schema)")
    status: str = Field(..., description="Job status")
    progress: Optional[JobProgress] = Field(None, description="Progress information")
    started_at: Optional[datetime] = Field(None, description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    created_at: datetime = Field(..., description="Job creation time")
    updated_at: datetime = Field(..., description="Last update time")
    error: Optional[str] = Field(None, description="Error message if failed")
    model_used: Optional[str] = Field(None, description="Model used for extraction")
    source: str = Field("api", description="Job source - 'webui' or 'api'")


class JobListResponse(BaseModel):
    """Response model for paginated job list."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "jobs": [
                    {
                        "id": "660e8400-e29b-41d4-a716-446655440000",
                        "document_id": "550e8400-e29b-41d4-a716-446655440000",
                        "document_name": "invoice_2024.pdf",
                        "status": "completed",
                        "model_used": "gemini-2.5-flash",
                        "created_at": "2025-11-02T10:30:00Z",
                        "updated_at": "2025-11-02T10:31:20Z",
                        "completed_at": "2025-11-02T10:31:20Z",
                    }
                ],
                "total": 42,
                "limit": 20,
                "offset": 0,
            }
        }
    )

    jobs: list[JobListItem] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs")
    limit: int = Field(..., description="Results per page")
    offset: int = Field(..., description="Pagination offset")
