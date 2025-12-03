"""Review-related Pydantic schemas for HITL system."""

from datetime import datetime
from typing import Any, Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ReviewRequestStatus, ReviewPriority, CorrectionType


# Request/Response Schemas

class CorrectionCreate(BaseModel):
    """Schema for creating a correction."""

    extraction_result_id: UUID = Field(..., description="ID of extraction result being corrected")
    field_path: str = Field(..., description="JSONPath to field (e.g., 'invoice.total')")
    original_value: Optional[Any] = Field(None, description="Original AI-extracted value")
    corrected_value: Optional[Any] = Field(None, description="Human-corrected value")
    correction_type: CorrectionType = Field(..., description="Type of correction")
    correction_notes: Optional[str] = Field(None, description="Explanation for correction")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "extraction_result_id": "123e4567-e89b-12d3-a456-426614174000",
                "field_path": "invoice.total",
                "original_value": "100.00",
                "corrected_value": "150.00",
                "correction_type": "value_change",
                "correction_notes": "Handwritten total was misread by AI"
            }
        }
    )


class CorrectionResponse(BaseModel):
    """Schema for correction response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    review_request_id: UUID
    extraction_result_id: UUID
    field_path: str
    original_value: Optional[Any]
    corrected_value: Optional[Any]
    correction_type: str
    correction_notes: Optional[str]
    corrected_by_user_id: Optional[UUID]
    created_at: datetime


class ReviewRequestCreate(BaseModel):
    """Schema for manual review request creation."""

    extraction_job_id: UUID = Field(..., description="Extraction job ID to review")
    priority: Optional[ReviewPriority] = Field(
        ReviewPriority.NORMAL,
        description="Review priority (affects SLA)"
    )
    trigger_reason: Optional[str] = Field(
        "manual_request",
        description="Reason for review request"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "extraction_job_id": "123e4567-e89b-12d3-a456-426614174000",
                "priority": "high",
                "trigger_reason": "manual_request"
            }
        }
    )


class ReviewRequestResponse(BaseModel):
    """Schema for review request response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    extraction_job_id: UUID
    assigned_to_user_id: Optional[UUID]
    status: str
    priority: str
    confidence_score: float
    trigger_reason: Optional[str]
    review_notes: Optional[str]
    conductor_task_id: Optional[str]
    conductor_workflow_id: Optional[str]
    sla_deadline: datetime
    created_at: datetime
    assigned_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    updated_at: datetime


class ReviewAssignRequest(BaseModel):
    """Schema for assigning a review."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }
    )

    user_id: UUID = Field(..., description="User ID to assign review to")


class ReviewEscalateRequest(BaseModel):
    """Schema for escalating a review."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reason": "Document requires specialist expertise in technical terminology"
            }
        }
    )

    reason: str = Field(..., min_length=10, max_length=1000, description="Reason for escalation")


class ReviewSubmitRequest(BaseModel):
    """Schema for submitting review corrections."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "corrections": [
                    {
                        "extraction_result_id": "123e4567-e89b-12d3-a456-426614174000",
                        "field_path": "invoice.total",
                        "original_value": "100.00",
                        "corrected_value": "150.00",
                        "correction_type": "value_change",
                        "correction_notes": "Handwritten total was misread"
                    }
                ],
                "review_notes": "Document quality was poor, several fields required correction"
            }
        }
    )

    corrections: List[CorrectionCreate] = Field(
        ...,
        description="List of corrections made"
    )
    review_notes: Optional[str] = Field(
        None,
        description="General notes about the review"
    )


class ReviewQueueFilter(BaseModel):
    """Schema for filtering review queue."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "pending",
                "priority": "high",
                "page": 1,
                "page_size": 50
            }
        }
    )

    status: Optional[ReviewRequestStatus] = Field(None, description="Filter by status")
    priority: Optional[ReviewPriority] = Field(None, description="Filter by priority")
    assigned_to_user_id: Optional[UUID] = Field(None, description="Filter by assignee")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=100, description="Items per page")


class ReviewQueueResponse(BaseModel):
    """Schema for review queue response."""

    model_config = ConfigDict(from_attributes=True)

    items: List[ReviewRequestResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ReviewMetricsResponse(BaseModel):
    """Schema for review metrics response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_reviews": 1000,
                "completed_reviews": 950,
                "pending_reviews": 50,
                "average_review_time_minutes": 15.5,
                "sla_breach_count": 5,
                "accuracy_by_schema": {
                    "invoice_schema": 0.95,
                    "receipt_schema": 0.88
                },
                "most_corrected_fields": [
                    {"field_path": "invoice.total", "correction_count": 45},
                    {"field_path": "invoice.date", "correction_count": 32}
                ]
            }
        }
    )

    total_reviews: int
    completed_reviews: int
    pending_reviews: int
    average_review_time_minutes: Optional[float]
    sla_breach_count: int
    accuracy_by_schema: dict[str, float]
    most_corrected_fields: List[dict[str, Any]]
