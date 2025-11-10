"""Pydantic schemas for metrics API."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# Dashboard Metrics Schemas
class MetricStats(BaseModel):
    """Summary statistics for dashboard."""

    total_jobs: int = Field(..., description="Total completed jobs")
    total_pages: int = Field(..., description="Total pages processed")
    total_tokens: int = Field(..., description="Total tokens used (input + output)")
    estimated_cost: float = Field(..., description="Estimated total cost in USD")

    model_config = ConfigDict(from_attributes=True)


class TimeSeriesDataPoint(BaseModel):
    """Single data point for time series chart."""

    date: str = Field(..., description="Date in ISO format (YYYY-MM-DD)")
    value: int = Field(..., description="Value for that date")

    model_config = ConfigDict(from_attributes=True)


class TokenUsageData(BaseModel):
    """Token usage breakdown."""

    date: str = Field(..., description="Date in ISO format")
    input_tokens: int = Field(..., description="Input tokens used")
    output_tokens: int = Field(..., description="Output tokens used")
    total_tokens: int = Field(..., description="Total tokens (input + output)")

    model_config = ConfigDict(from_attributes=True)


class ModelDistribution(BaseModel):
    """Model usage distribution for pie chart."""

    model: str = Field(..., description="Model name")
    count: int = Field(..., description="Number of jobs using this model")
    percentage: float = Field(..., description="Percentage of total jobs")

    model_config = ConfigDict(from_attributes=True)


class DashboardMetricsResponse(BaseModel):
    """Response for dashboard metrics endpoint."""

    stats: MetricStats = Field(..., description="Summary statistics")
    jobs_over_time: List[TimeSeriesDataPoint] = Field(
        ..., description="Jobs completed per day"
    )
    pages_over_time: List[TimeSeriesDataPoint] = Field(
        ..., description="Pages processed per day"
    )
    tokens_over_time: List[TokenUsageData] = Field(
        ..., description="Token usage per day"
    )
    model_distribution: List[ModelDistribution] = Field(
        ..., description="Model usage distribution"
    )

    model_config = ConfigDict(from_attributes=True)


# Billing/Completed Jobs Schemas
class CompletedJobItem(BaseModel):
    """Single completed job for billing table."""

    job_id: str = Field(..., description="Extraction job ID")
    document_id: str = Field(..., description="Document ID")
    document_name: Optional[str] = Field(None, description="Original document filename")
    model: str = Field(..., description="Model used for extraction")
    pages_processed: int = Field(..., description="Number of pages processed")
    input_tokens: int = Field(..., description="Input tokens used")
    output_tokens: int = Field(..., description="Output tokens used")
    total_tokens: int = Field(..., description="Total tokens used")
    estimated_cost: float = Field(..., description="Estimated cost in USD")
    processing_time: Optional[float] = Field(
        None, description="Processing time in seconds"
    )
    completed_at: datetime = Field(..., description="Completion timestamp")
    tenant_id: str = Field(..., description="Tenant ID (for admin only)")

    model_config = ConfigDict(from_attributes=True)


class CompletedJobsResponse(BaseModel):
    """Paginated response for completed jobs endpoint."""

    jobs: List[CompletedJobItem] = Field(..., description="List of completed jobs")
    total: int = Field(..., description="Total number of completed jobs")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    total_cost: float = Field(..., description="Total estimated cost for all jobs")

    model_config = ConfigDict(from_attributes=True)
