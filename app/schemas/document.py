"""Document-related Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """Response model for a single document."""

    document_id: UUID = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    mime_type: str = Field(..., description="MIME type of the file")
    size_bytes: int = Field(..., description="File size in bytes")
    status: str = Field(..., description="Processing status")
    page_count: Optional[int] = Field(None, description="Number of pages (for PDFs)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Custom metadata")
    created_at: datetime = Field(..., description="Upload timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True
        json_schema_extra = {
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "invoice.pdf",
                "mime_type": "application/pdf",
                "size_bytes": 245678,
                "status": "ready_for_extraction",
                "page_count": 3,
                "metadata": {},
                "created_at": "2025-11-02T10:30:00Z",
            }
        }


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""

    document_id: UUID = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Uploaded filename")
    mime_type: str = Field(..., description="MIME type")
    size_bytes: int = Field(..., description="File size in bytes")
    status: str = Field(..., description="Initial status")
    page_count: Optional[int] = Field(None, description="Number of pages (for PDFs)")
    created_at: datetime = Field(..., description="Upload timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response model for listing documents."""

    documents: list[DocumentResponse] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents")
    limit: int = Field(..., description="Results per page")
    offset: int = Field(..., description="Offset for pagination")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "documents": [
                    {
                        "document_id": "550e8400-e29b-41d4-a716-446655440000",
                        "filename": "invoice.pdf",
                        "mime_type": "application/pdf",
                        "size_bytes": 245678,
                        "status": "completed",
                        "page_count": 3,
                        "metadata": {},
                        "created_at": "2025-11-02T10:30:00Z",
                    }
                ],
                "total": 45,
                "limit": 20,
                "offset": 0,
            }
        }
