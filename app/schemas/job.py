"""Job-related Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class JobProgress(BaseModel):
    """Job progress information."""

    total_pages: int = Field(..., description="Total number of pages")
    completed_pages: int = Field(..., description="Completed pages")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "total_pages": 3,
                "completed_pages": 1,
            }
        }


class JobStatusResponse(BaseModel):
    """Response model for job status."""

    job_id: UUID = Field(..., description="Job identifier")
    document_id: UUID = Field(..., description="Document identifier")
    status: str = Field(..., description="Job status")
    progress: Optional[JobProgress] = Field(None, description="Progress information")
    started_at: Optional[datetime] = Field(None, description="Job start time")
    updated_at: datetime = Field(..., description="Last update time")
    error: Optional[str] = Field(None, description="Error message if failed")

    class Config:
        """Pydantic config."""

        from_attributes = True
        json_schema_extra = {
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


class ExtractionMetadata(BaseModel):
    """Metadata about the extraction process."""

    model_used: str = Field(..., description="Model that performed extraction")
    input_tokens: int = Field(..., description="Input tokens (image + prompt)")
    output_tokens: int = Field(..., description="Output tokens (generated response)")
    tokens_used: int = Field(..., description="Total tokens consumed (input + output)")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    confidence_score: float = Field(..., description="Confidence score (0-1)")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "model_used": "google/gemini-2.5-flash",
                "input_tokens": 1050,
                "output_tokens": 200,
                "tokens_used": 1250,
                "processing_time_ms": 8500,
                "confidence_score": 0.95,
            }
        }


class JobResultResponse(BaseModel):
    """Response model for job results."""

    job_id: UUID = Field(..., description="Job identifier")
    document_id: UUID = Field(..., description="Document identifier")
    status: str = Field(..., description="Job status")
    extracted_data: dict[str, Any] = Field(..., description="Extracted structured data")
    metadata: ExtractionMetadata = Field(..., description="Extraction metadata")
    completed_at: datetime = Field(..., description="Completion timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True
        json_schema_extra = {
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
