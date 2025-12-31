"""Document split-related Pydantic schemas."""

from datetime import datetime
from typing import List, Literal, Optional, Set
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Allowed DSPy models for validation
ALLOWED_DSPY_MODELS: Set[str] = {
    "qwen3-vl-32b-instruct",
    "qwen3-vl-8b-instruct",
    "qwen-vl-max",
    "qwen-vl-plus",
}


# ============================================================================
# Request Schemas
# ============================================================================


class SplitJobCreateRequest(BaseModel):
    """Request to create a document split job."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "apply_rotation": True,
                "dspy_model": "qwen3-vl-32b-instruct",
            }
        }
    )

    apply_rotation: bool = Field(
        default=True,
        description="Whether to automatically correct page rotation"
    )
    dspy_model: Optional[str] = Field(
        default=None,
        description="Vision model to use for boundary detection (default: qwen3-vl-32b-instruct)"
    )

    @field_validator("dspy_model")
    @classmethod
    def validate_dspy_model(cls, v: Optional[str]) -> Optional[str]:
        """Validate dspy_model is an allowed model."""
        if v is None:
            return v
        if v not in ALLOWED_DSPY_MODELS:
            raise ValueError(
                f"Invalid model: {v}. Allowed models: {', '.join(sorted(ALLOWED_DSPY_MODELS))}"
            )
        return v


# ============================================================================
# Response Schemas
# ============================================================================


class SplitJobCreateResponse(BaseModel):
    """Response after creating a split job."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "split_job_id": "660e8400-e29b-41d4-a716-446655440000",
                "status": "queued",
                "message": "Split job queued successfully",
                "estimated_time_seconds": 30,
            }
        }
    )

    split_job_id: UUID = Field(..., description="Split job identifier")
    status: str = Field(..., description="Job status")
    message: str = Field(default="Split job queued successfully", description="Status message")
    estimated_time_seconds: Optional[int] = Field(
        None, description="Estimated processing time in seconds"
    )


class SplitJobProgress(BaseModel):
    """Progress information for a split job."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_pages": 10,
                "pages_analyzed": 5,
                "documents_created": 3,
                "pages_rotated": 2,
                "total_input_tokens": 10240,
                "total_output_tokens": 1280,
            }
        }
    )

    total_pages: Optional[int] = Field(
        None, description="Total number of pages in source document"
    )
    pages_analyzed: int = Field(0, description="Number of pages analyzed so far")
    documents_created: int = Field(0, description="Number of separate documents created")
    pages_rotated: int = Field(0, description="Number of pages that needed rotation")
    total_input_tokens: int = Field(0, description="Total input tokens used")
    total_output_tokens: int = Field(0, description="Total output tokens used")


class SplitJobStatusResponse(BaseModel):
    """Response model for split job status."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "split_job_id": "660e8400-e29b-41d4-a716-446655440000",
                "source_document_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "analyzing",
                "progress": {
                    "total_pages": 10,
                    "pages_analyzed": 5,
                    "documents_created": 3,
                    "pages_rotated": 2,
                    "total_input_tokens": 10240,
                    "total_output_tokens": 1280,
                },
                "started_at": "2025-11-02T10:31:05Z",
                "created_at": "2025-11-02T10:31:00Z",
                "error_message": None,
            }
        }
    )

    split_job_id: UUID = Field(..., description="Split job identifier")
    source_document_id: UUID = Field(..., description="Source document identifier")
    status: str = Field(..., description="Job status (queued, analyzing, splitting, completed, failed)")
    progress: SplitJobProgress = Field(..., description="Progress information")
    apply_rotation: bool = Field(..., description="Whether rotation correction is enabled")
    dspy_model: Optional[str] = Field(None, description="Model used for analysis")
    started_at: Optional[datetime] = Field(None, description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    created_at: datetime = Field(..., description="Job creation time")
    error_message: Optional[str] = Field(None, description="Sanitized error message if failed")


class PageAnalysisResult(BaseModel):
    """Analysis result for a single page."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "page_number": 1,
                "boundary_reason": "This page shows a new invoice header with company logo and invoice number at the top, indicating the start of a new document.",
                "detected_document_type": "invoice",
                "is_starting_page": True,
                "boundary_confidence": "high",
                "rotation_needed": 0,
                "rotation_confidence": "high",
                "rotation_method": "tesseract_osd",
                "input_tokens": 1024,
                "output_tokens": 128,
            }
        }
    )

    page_number: int = Field(..., description="Page number (1-indexed)")
    # Reasoning fields (generated FIRST due to LLM autoregression)
    boundary_reason: str = Field(..., description="Reasoning for boundary decision")
    detected_document_type: str = Field(..., description="Type of document detected")
    # Classification fields (generated AFTER reasoning)
    is_starting_page: bool = Field(..., description="Whether this is the start of a new document")
    boundary_confidence: Literal["high", "medium", "low"] = Field(
        ..., description="Confidence in boundary detection"
    )
    # Rotation detection
    rotation_needed: int = Field(..., description="Clockwise degrees to rotate (0, 90, 180, 270)")
    rotation_confidence: Literal["high", "medium", "low"] = Field(
        ..., description="Confidence in rotation detection"
    )
    rotation_method: str = Field(..., description="Method used for rotation detection")
    # Token usage
    input_tokens: int = Field(..., description="Input tokens for this page's analysis")
    output_tokens: int = Field(..., description="Output tokens for this page's analysis")
    # Result
    child_document_id: Optional[UUID] = Field(
        None, description="ID of the child document this page belongs to (after splitting)"
    )


class SplitJobSummary(BaseModel):
    """Summary statistics for a completed split job."""

    total_pages: int = Field(..., description="Total pages analyzed")
    documents_created: int = Field(..., description="Number of child documents created")
    pages_rotated: int = Field(..., description="Number of pages that were rotated")
    total_input_tokens: int = Field(..., description="Total input tokens used")
    total_output_tokens: int = Field(..., description="Total output tokens used")


class SplitJobResultsResponse(BaseModel):
    """Response with detailed per-page analysis results."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "split_job_id": "660e8400-e29b-41d4-a716-446655440000",
                "source_document_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "page_results": [
                    {
                        "page_number": 1,
                        "boundary_reason": "New invoice header with company logo",
                        "detected_document_type": "invoice",
                        "is_starting_page": True,
                        "boundary_confidence": "high",
                        "rotation_needed": 0,
                        "rotation_confidence": "high",
                        "rotation_method": "tesseract_osd",
                        "input_tokens": 1024,
                        "output_tokens": 128,
                    }
                ],
                "summary": {
                    "total_pages": 10,
                    "documents_created": 3,
                    "pages_rotated": 2,
                    "total_input_tokens": 10240,
                    "total_output_tokens": 1280,
                },
            }
        }
    )

    split_job_id: UUID = Field(..., description="Split job identifier")
    source_document_id: UUID = Field(..., description="Source document identifier")
    status: str = Field(..., description="Job status")
    page_results: List[PageAnalysisResult] = Field(..., description="Per-page analysis results")
    summary: SplitJobSummary = Field(..., description="Summary statistics")


class ChildDocumentResponse(BaseModel):
    """Response for a child document created from splitting."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "document_id": "770e8400-e29b-41d4-a716-446655440000",
                "split_job_id": "660e8400-e29b-41d4-a716-446655440000",
                "split_sequence": 1,
                "filename": "invoice_2024_part001_p1-3.pdf",
                "page_count": 3,
                "status": "uploaded",
                "created_at": "2025-11-02T10:32:00Z",
            }
        }
    )

    document_id: UUID = Field(..., description="Child document identifier")
    split_job_id: Optional[UUID] = Field(None, description="Split job that created this document")
    split_sequence: Optional[int] = Field(None, description="Sequence number within parent (1, 2, 3...)")
    filename: str = Field(..., description="Generated filename")
    page_count: Optional[int] = Field(None, description="Number of pages in this child document")
    status: str = Field(..., description="Document status")
    created_at: datetime = Field(..., description="Creation timestamp")


class ChildDocumentsListResponse(BaseModel):
    """Response listing all child documents from splitting."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "parent_document_id": "550e8400-e29b-41d4-a716-446655440000",
                "children": [
                    {
                        "document_id": "770e8400-e29b-41d4-a716-446655440000",
                        "split_sequence": 1,
                        "filename": "invoice_2024_part001_p1-3.pdf",
                        "page_count": 3,
                        "status": "uploaded",
                    }
                ],
                "total_count": 3,
            }
        }
    )

    parent_document_id: UUID = Field(..., description="Parent document identifier")
    children: List[ChildDocumentResponse] = Field(..., description="List of child documents")
    total_count: int = Field(..., description="Total number of child documents")
