# Metrics and Billing System Architecture

**Date:** 2025-11-03
**Status:** Design Complete
**Author:** Solution Architect

## Executive Summary

This document provides a comprehensive technical design for implementing a metrics and billing system for the AI document processing SaaS platform. The system tracks completed extraction jobs, token usage, processing time, and provides dashboard visualizations and detailed billing reports with proper multi-tenant isolation.

### Key Design Decisions

1. **No New Database Tables Required**: Leverage existing `ExtractionResult` model which already tracks tokens and processing time
2. **Service Layer Aggregation**: Implement `MetricsService` for data aggregation using efficient SQL queries
3. **Multi-Tenant Isolation**: All queries filtered by `tenant_id` with admin override capability
4. **Time-Series Optimization**: Use PostgreSQL date functions and indexed queries for performance
5. **Frontend Composition**: Reusable chart components with recharts library
6. **Cost Estimation**: Configurable pricing model based on token usage and model provider

---

## Technical Design Document

### 1. Database Schema Analysis

**Current Schema (No Changes Required):**

The existing models already contain all necessary data:

```python
# ExtractionResult (app/models/extraction_result.py)
- extraction_job_id (UUID)           # Links to job
- document_page_id (UUID)            # Links to page
- extracted_data (JSONB)             # Extracted content
- model_used (String)                # Model identifier
- input_tokens (Integer)             # Prompt tokens
- output_tokens (Integer)            # Completion tokens
- tokens_used (Integer)              # Total (input + output)
- processing_time_ms (Integer)       # Processing duration
- created_at (DateTime)              # Timestamp for time-series

# ExtractionJob (app/models/extraction_job.py)
- document_id (UUID)                 # Links to document
- status (String)                    # completed, failed, etc.
- model_provider (String)            # google, openai, deepseek
- completed_at (DateTime)            # Job completion timestamp

# Document (app/models/document.py)
- tenant_id (UUID)                   # Multi-tenant isolation
- page_count (Integer)               # Pages in document
```

**Indexes for Performance:**

Current indexes are sufficient, but we'll verify query performance:

```python
# Existing indexes (already in place):
Index("idx_extraction_results_job_id", "extraction_job_id")
Index("idx_extraction_jobs_document_id", "document_id")
Index("idx_extraction_jobs_status", "status")
Index("idx_documents_tenant_id", "tenant_id")
Index("idx_documents_created_at", "created_at")
```

**Recommendation**: Monitor query performance and add composite index if needed:
```sql
CREATE INDEX idx_metrics_tenant_date
ON extraction_results (created_at DESC)
INCLUDE (input_tokens, output_tokens, processing_time_ms);
```

---

### 2. Domain Layer Design

#### 2.1 Value Objects

**File:** `app/domain/metrics/value_objects.py`

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class DateRange:
    """Value object for date range filtering."""
    start_date: datetime
    end_date: datetime

    def __post_init__(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date must be before end_date")


@dataclass(frozen=True)
class TokenUsage:
    """Value object for token usage metrics."""
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def __add__(self, other: 'TokenUsage') -> 'TokenUsage':
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens
        )


@dataclass(frozen=True)
class CostEstimate:
    """Value object for cost estimation."""
    input_cost: Decimal
    output_cost: Decimal
    total_cost: Decimal
    currency: str = "USD"

    def __add__(self, other: 'CostEstimate') -> 'CostEstimate':
        if self.currency != other.currency:
            raise ValueError("Cannot add costs with different currencies")
        return CostEstimate(
            input_cost=self.input_cost + other.input_cost,
            output_cost=self.output_cost + other.output_cost,
            total_cost=self.total_cost + other.total_cost,
            currency=self.currency
        )


@dataclass(frozen=True)
class MetricsPeriod:
    """Value object for time-series period."""
    period: str  # 'hour', 'day', 'week', 'month'
    timestamp: datetime
    value: int
```

#### 2.2 Domain Services

**File:** `app/domain/metrics/pricing_service.py`

```python
from decimal import Decimal
from typing import Dict
from app.domain.metrics.value_objects import TokenUsage, CostEstimate


class PricingService:
    """
    Domain service for cost calculation.

    Follows Single Responsibility Principle - only calculates costs.
    Pricing rules are business logic that belong in the domain layer.
    """

    # Pricing per million tokens (configurable via environment)
    PRICING_TABLE: Dict[str, Dict[str, Decimal]] = {
        "google": {
            "gemini-2.5-flash": {
                "input": Decimal("0.075"),   # $0.075 per 1M input tokens
                "output": Decimal("0.30"),   # $0.30 per 1M output tokens
            },
            "gemini-2.0-flash": {
                "input": Decimal("0.10"),
                "output": Decimal("0.40"),
            },
        },
        "openai": {
            "gpt-4o": {
                "input": Decimal("2.50"),
                "output": Decimal("10.00"),
            },
            "gpt-4o-mini": {
                "input": Decimal("0.15"),
                "output": Decimal("0.60"),
            },
        },
        "deepseek": {
            "deepseek-chat": {
                "input": Decimal("0.14"),
                "output": Decimal("0.28"),
            },
        },
    }

    def calculate_cost(
        self,
        token_usage: TokenUsage,
        model_provider: str,
        model_name: str
    ) -> CostEstimate:
        """
        Calculate cost based on token usage and model pricing.

        Args:
            token_usage: Token usage value object
            model_provider: Provider identifier (google, openai, deepseek)
            model_name: Model name (gemini-2.5-flash, gpt-4o, etc.)

        Returns:
            CostEstimate value object

        Raises:
            ValueError: If model pricing not found
        """
        try:
            pricing = self.PRICING_TABLE[model_provider][model_name]
        except KeyError:
            # Fallback to generic pricing if model not found
            pricing = {"input": Decimal("0.10"), "output": Decimal("0.40")}

        # Convert tokens to millions for pricing calculation
        input_millions = Decimal(token_usage.input_tokens) / Decimal(1_000_000)
        output_millions = Decimal(token_usage.output_tokens) / Decimal(1_000_000)

        input_cost = input_millions * pricing["input"]
        output_cost = output_millions * pricing["output"]
        total_cost = input_cost + output_cost

        return CostEstimate(
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            currency="USD"
        )
```

---

### 3. Application Layer Design

#### 3.1 DTOs (Data Transfer Objects)

**File:** `app/schemas/metrics.py`

```python
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


class DateRangeFilter(BaseModel):
    """Request schema for date range filtering."""
    start_date: datetime = Field(..., description="Start date (ISO 8601)")
    end_date: datetime = Field(..., description="End date (ISO 8601)")


class DashboardMetricsRequest(BaseModel):
    """Request schema for dashboard metrics."""
    date_range: Optional[DateRangeFilter] = None
    tenant_id: Optional[UUID] = Field(None, description="Admin-only: filter by tenant")


class TimeSeriesDataPoint(BaseModel):
    """Single data point in time series."""
    timestamp: datetime
    value: int
    label: str  # Formatted label (e.g., "Jan 2025", "Week 1")

    model_config = ConfigDict(from_attributes=True)


class TokenUsageMetrics(BaseModel):
    """Token usage breakdown."""
    input_tokens: int
    output_tokens: int
    total_tokens: int


class CostMetrics(BaseModel):
    """Cost breakdown."""
    input_cost: Decimal
    output_cost: Decimal
    total_cost: Decimal
    currency: str = "USD"


class DashboardStatsCard(BaseModel):
    """Stats card data for dashboard."""
    label: str
    value: str  # Formatted value (e.g., "1,234" or "$12.34")
    change: Optional[str] = None  # e.g., "+12%" or "-5%"
    trend: Optional[str] = None  # "up" or "down"


class DashboardMetricsResponse(BaseModel):
    """Response schema for dashboard metrics."""
    # Summary stats cards
    stats: List[DashboardStatsCard]

    # Time series charts
    jobs_over_time: List[TimeSeriesDataPoint]
    pages_over_time: List[TimeSeriesDataPoint]
    tokens_over_time: List[TimeSeriesDataPoint]

    # Token usage breakdown
    token_usage: TokenUsageMetrics

    # Cost metrics
    estimated_cost: CostMetrics

    # Model distribution (for pie chart)
    model_distribution: List[dict]  # [{"model": "gemini-2.5-flash", "count": 150}]

    model_config = ConfigDict(from_attributes=True)


class CompletedJobItem(BaseModel):
    """Single completed job for billing table."""
    id: UUID
    document_id: UUID
    document_filename: str
    page_count: int
    model_provider: str
    model_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    processing_time_ms: int
    estimated_cost: Decimal
    completed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompletedJobsRequest(BaseModel):
    """Request schema for completed jobs list."""
    date_range: Optional[DateRangeFilter] = None
    tenant_id: Optional[UUID] = Field(None, description="Admin-only: filter by tenant")
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    sort_by: str = Field("completed_at", description="Sort field")
    sort_order: str = Field("desc", description="asc or desc")


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    page: int
    page_size: int
    total_items: int
    total_pages: int


class CompletedJobsResponse(BaseModel):
    """Response schema for completed jobs list."""
    jobs: List[CompletedJobItem]
    pagination: PaginationMeta
    total_cost: Decimal  # Sum of all jobs in response

    model_config = ConfigDict(from_attributes=True)
```

#### 3.2 Application Services

**File:** `app/services/metrics_service.py`

```python
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import func, and_, desc, asc
from sqlalchemy.orm import Session, joinedload

from app.models import ExtractionJob, ExtractionResult, Document, DocumentPage
from app.domain.metrics.value_objects import DateRange, TokenUsage, CostEstimate
from app.domain.metrics.pricing_service import PricingService
from app.schemas.metrics import (
    TimeSeriesDataPoint,
    TokenUsageMetrics,
    CostMetrics,
    DashboardStatsCard,
    DashboardMetricsResponse,
    CompletedJobItem,
    CompletedJobsResponse,
    PaginationMeta,
)


class MetricsService:
    """
    Application service for metrics and billing operations.

    Responsibilities:
    - Aggregate metrics from extraction results
    - Apply tenant filtering
    - Transform data into presentation DTOs
    - Coordinate with domain services (PricingService)

    Follows Single Responsibility and Dependency Inversion principles.
    """

    def __init__(self, db: Session):
        """
        Initialize metrics service.

        Args:
            db: Database session (injected dependency)
        """
        self.db = db
        self.pricing_service = PricingService()

    def get_dashboard_metrics(
        self,
        tenant_id: UUID,
        date_range: Optional[DateRange] = None,
        is_admin: bool = False,
        requested_tenant_id: Optional[UUID] = None
    ) -> DashboardMetricsResponse:
        """
        Get aggregated metrics for dashboard.

        Args:
            tenant_id: Current user's tenant ID
            date_range: Optional date range filter
            is_admin: Whether user has admin role
            requested_tenant_id: Admin-only tenant filter

        Returns:
            DashboardMetricsResponse with all metrics

        Raises:
            ValueError: If non-admin tries to access other tenant's data
        """
        # Determine which tenant to query
        target_tenant_id = self._resolve_tenant_id(
            tenant_id, is_admin, requested_tenant_id
        )

        # Apply date range (default: last 30 days)
        if not date_range:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            date_range = DateRange(start_date=start_date, end_date=end_date)

        # Build base query with tenant filtering
        base_query = self._build_base_query(target_tenant_id, date_range)

        # Aggregate metrics
        stats = self._calculate_stats(base_query, date_range)
        jobs_over_time = self._get_jobs_time_series(base_query, date_range)
        pages_over_time = self._get_pages_time_series(base_query, date_range)
        tokens_over_time = self._get_tokens_time_series(base_query, date_range)
        token_usage = self._get_token_usage(base_query)
        estimated_cost = self._calculate_total_cost(base_query)
        model_distribution = self._get_model_distribution(base_query)

        return DashboardMetricsResponse(
            stats=stats,
            jobs_over_time=jobs_over_time,
            pages_over_time=pages_over_time,
            tokens_over_time=tokens_over_time,
            token_usage=token_usage,
            estimated_cost=estimated_cost,
            model_distribution=model_distribution,
        )

    def get_completed_jobs(
        self,
        tenant_id: UUID,
        page: int,
        page_size: int,
        date_range: Optional[DateRange] = None,
        sort_by: str = "completed_at",
        sort_order: str = "desc",
        is_admin: bool = False,
        requested_tenant_id: Optional[UUID] = None
    ) -> CompletedJobsResponse:
        """
        Get paginated list of completed jobs for billing.

        Args:
            tenant_id: Current user's tenant ID
            page: Page number (1-indexed)
            page_size: Items per page
            date_range: Optional date range filter
            sort_by: Field to sort by
            sort_order: 'asc' or 'desc'
            is_admin: Whether user has admin role
            requested_tenant_id: Admin-only tenant filter

        Returns:
            CompletedJobsResponse with paginated jobs
        """
        # Determine which tenant to query
        target_tenant_id = self._resolve_tenant_id(
            tenant_id, is_admin, requested_tenant_id
        )

        # Build query
        query = self._build_completed_jobs_query(
            target_tenant_id, date_range, sort_by, sort_order
        )

        # Count total items
        total_items = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        jobs = query.offset(offset).limit(page_size).all()

        # Transform to DTOs
        job_items = [self._job_to_dto(job) for job in jobs]

        # Calculate total cost for this page
        total_cost = sum(item.estimated_cost for item in job_items)

        # Pagination metadata
        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=(total_items + page_size - 1) // page_size
        )

        return CompletedJobsResponse(
            jobs=job_items,
            pagination=pagination,
            total_cost=total_cost
        )

    # --- Private Helper Methods ---

    def _resolve_tenant_id(
        self,
        user_tenant_id: UUID,
        is_admin: bool,
        requested_tenant_id: Optional[UUID]
    ) -> UUID:
        """Resolve which tenant to query (enforce isolation)."""
        if requested_tenant_id:
            if not is_admin:
                raise ValueError("Only admins can access other tenants' data")
            return requested_tenant_id
        return user_tenant_id

    def _build_base_query(
        self, tenant_id: UUID, date_range: DateRange
    ):
        """Build base query with tenant and date filtering."""
        query = (
            self.db.query(ExtractionResult)
            .join(ExtractionJob, ExtractionResult.extraction_job_id == ExtractionJob.id)
            .join(Document, ExtractionJob.document_id == Document.id)
            .filter(
                Document.tenant_id == tenant_id,
                ExtractionJob.status == "completed",
                ExtractionResult.created_at >= date_range.start_date,
                ExtractionResult.created_at <= date_range.end_date
            )
        )
        return query

    def _calculate_stats(
        self, base_query, date_range: DateRange
    ) -> List[DashboardStatsCard]:
        """Calculate summary statistics."""
        # Total jobs
        total_jobs = (
            self.db.query(func.count(func.distinct(ExtractionJob.id)))
            .join(Document, ExtractionJob.document_id == Document.id)
            .join(ExtractionResult, ExtractionResult.extraction_job_id == ExtractionJob.id)
            .filter(base_query.whereclause)
            .scalar()
        )

        # Total pages
        total_pages = (
            self.db.query(func.count(ExtractionResult.id))
            .join(ExtractionJob, ExtractionResult.extraction_job_id == ExtractionJob.id)
            .join(Document, ExtractionJob.document_id == Document.id)
            .filter(base_query.whereclause)
            .scalar()
        )

        # Total tokens
        token_sum = (
            self.db.query(
                func.sum(ExtractionResult.input_tokens),
                func.sum(ExtractionResult.output_tokens)
            )
            .join(ExtractionJob, ExtractionResult.extraction_job_id == ExtractionJob.id)
            .join(Document, ExtractionJob.document_id == Document.id)
            .filter(base_query.whereclause)
            .first()
        )
        total_tokens = (token_sum[0] or 0) + (token_sum[1] or 0)

        # Average processing time
        avg_time = (
            self.db.query(func.avg(ExtractionResult.processing_time_ms))
            .join(ExtractionJob, ExtractionResult.extraction_job_id == ExtractionJob.id)
            .join(Document, ExtractionJob.document_id == Document.id)
            .filter(base_query.whereclause)
            .scalar() or 0
        )

        return [
            DashboardStatsCard(label="Completed Jobs", value=f"{total_jobs:,}"),
            DashboardStatsCard(label="Pages Processed", value=f"{total_pages:,}"),
            DashboardStatsCard(label="Total Tokens", value=f"{total_tokens:,}"),
            DashboardStatsCard(label="Avg. Time", value=f"{int(avg_time / 1000)}s"),
        ]

    def _get_jobs_time_series(
        self, base_query, date_range: DateRange
    ) -> List[TimeSeriesDataPoint]:
        """Get jobs count over time."""
        # Group by day
        results = (
            self.db.query(
                func.date_trunc('day', ExtractionResult.created_at).label('day'),
                func.count(func.distinct(ExtractionJob.id)).label('count')
            )
            .join(ExtractionJob, ExtractionResult.extraction_job_id == ExtractionJob.id)
            .join(Document, ExtractionJob.document_id == Document.id)
            .filter(base_query.whereclause)
            .group_by('day')
            .order_by('day')
            .all()
        )

        return [
            TimeSeriesDataPoint(
                timestamp=row.day,
                value=row.count,
                label=row.day.strftime("%b %d")
            )
            for row in results
        ]

    def _get_pages_time_series(
        self, base_query, date_range: DateRange
    ) -> List[TimeSeriesDataPoint]:
        """Get pages processed over time."""
        results = (
            self.db.query(
                func.date_trunc('day', ExtractionResult.created_at).label('day'),
                func.count(ExtractionResult.id).label('count')
            )
            .join(ExtractionJob, ExtractionResult.extraction_job_id == ExtractionJob.id)
            .join(Document, ExtractionJob.document_id == Document.id)
            .filter(base_query.whereclause)
            .group_by('day')
            .order_by('day')
            .all()
        )

        return [
            TimeSeriesDataPoint(
                timestamp=row.day,
                value=row.count,
                label=row.day.strftime("%b %d")
            )
            for row in results
        ]

    def _get_tokens_time_series(
        self, base_query, date_range: DateRange
    ) -> List[TimeSeriesDataPoint]:
        """Get tokens used over time."""
        results = (
            self.db.query(
                func.date_trunc('day', ExtractionResult.created_at).label('day'),
                func.sum(ExtractionResult.input_tokens + ExtractionResult.output_tokens).label('total')
            )
            .join(ExtractionJob, ExtractionResult.extraction_job_id == ExtractionJob.id)
            .join(Document, ExtractionJob.document_id == Document.id)
            .filter(base_query.whereclause)
            .group_by('day')
            .order_by('day')
            .all()
        )

        return [
            TimeSeriesDataPoint(
                timestamp=row.day,
                value=int(row.total or 0),
                label=row.day.strftime("%b %d")
            )
            for row in results
        ]

    def _get_token_usage(self, base_query) -> TokenUsageMetrics:
        """Get total token usage."""
        result = (
            self.db.query(
                func.sum(ExtractionResult.input_tokens).label('input'),
                func.sum(ExtractionResult.output_tokens).label('output')
            )
            .join(ExtractionJob, ExtractionResult.extraction_job_id == ExtractionJob.id)
            .join(Document, ExtractionJob.document_id == Document.id)
            .filter(base_query.whereclause)
            .first()
        )

        input_tokens = result.input or 0
        output_tokens = result.output or 0

        return TokenUsageMetrics(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens
        )

    def _calculate_total_cost(self, base_query) -> CostMetrics:
        """Calculate estimated total cost."""
        # Get all results with model info
        results = (
            self.db.query(
                ExtractionResult.input_tokens,
                ExtractionResult.output_tokens,
                ExtractionJob.model_provider,
                ExtractionJob.model_name
            )
            .join(ExtractionJob, ExtractionResult.extraction_job_id == ExtractionJob.id)
            .join(Document, ExtractionJob.document_id == Document.id)
            .filter(base_query.whereclause)
            .all()
        )

        total_input_cost = Decimal("0")
        total_output_cost = Decimal("0")

        for result in results:
            token_usage = TokenUsage(
                input_tokens=result.input_tokens or 0,
                output_tokens=result.output_tokens or 0
            )
            cost = self.pricing_service.calculate_cost(
                token_usage,
                result.model_provider,
                result.model_name
            )
            total_input_cost += cost.input_cost
            total_output_cost += cost.output_cost

        return CostMetrics(
            input_cost=total_input_cost,
            output_cost=total_output_cost,
            total_cost=total_input_cost + total_output_cost,
            currency="USD"
        )

    def _get_model_distribution(self, base_query) -> List[dict]:
        """Get model usage distribution."""
        results = (
            self.db.query(
                ExtractionJob.model_name,
                func.count(func.distinct(ExtractionJob.id)).label('count')
            )
            .join(ExtractionResult, ExtractionResult.extraction_job_id == ExtractionJob.id)
            .join(Document, ExtractionJob.document_id == Document.id)
            .filter(base_query.whereclause)
            .group_by(ExtractionJob.model_name)
            .all()
        )

        return [{"model": row.model_name, "count": row.count} for row in results]

    def _build_completed_jobs_query(
        self,
        tenant_id: UUID,
        date_range: Optional[DateRange],
        sort_by: str,
        sort_order: str
    ):
        """Build query for completed jobs list."""
        query = (
            self.db.query(ExtractionJob)
            .join(Document, ExtractionJob.document_id == Document.id)
            .filter(
                Document.tenant_id == tenant_id,
                ExtractionJob.status == "completed"
            )
            .options(
                joinedload(ExtractionJob.document),
                joinedload(ExtractionJob.extraction_results)
            )
        )

        # Apply date range filter
        if date_range:
            query = query.filter(
                ExtractionJob.completed_at >= date_range.start_date,
                ExtractionJob.completed_at <= date_range.end_date
            )

        # Apply sorting
        sort_column = getattr(ExtractionJob, sort_by, ExtractionJob.completed_at)
        query = query.order_by(desc(sort_column) if sort_order == "desc" else asc(sort_column))

        return query

    def _job_to_dto(self, job: ExtractionJob) -> CompletedJobItem:
        """Transform job to DTO."""
        # Aggregate tokens from all extraction results
        total_input = sum(r.input_tokens or 0 for r in job.extraction_results)
        total_output = sum(r.output_tokens or 0 for r in job.extraction_results)
        total_time = sum(r.processing_time_ms or 0 for r in job.extraction_results)

        # Calculate cost
        token_usage = TokenUsage(input_tokens=total_input, output_tokens=total_output)
        cost = self.pricing_service.calculate_cost(
            token_usage,
            job.model_provider,
            job.model_name
        )

        return CompletedJobItem(
            id=job.id,
            document_id=job.document_id,
            document_filename=job.document.filename,
            page_count=len(job.extraction_results),
            model_provider=job.model_provider,
            model_name=job.model_name,
            input_tokens=total_input,
            output_tokens=total_output,
            total_tokens=total_input + total_output,
            processing_time_ms=total_time,
            estimated_cost=cost.total_cost,
            completed_at=job.completed_at
        )
```

---

### 4. Infrastructure Layer Design

#### 4.1 API Endpoints

**File:** `app/api/metrics.py`

```python
from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.dependencies.auth import get_current_active_user
from app.services.metrics_service import MetricsService
from app.services.permission_service import PermissionService
from app.schemas.metrics import (
    DashboardMetricsRequest,
    DashboardMetricsResponse,
    CompletedJobsRequest,
    CompletedJobsResponse,
    DateRangeFilter,
)
from app.domain.metrics.value_objects import DateRange


router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("/dashboard", response_model=DashboardMetricsResponse)
async def get_dashboard_metrics(
    start_date: Optional[datetime] = Query(None, description="Start date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO 8601)"),
    tenant_id: Optional[UUID] = Query(None, description="Admin-only: filter by tenant"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get aggregated metrics for dashboard.

    Returns:
    - Summary statistics (jobs, pages, tokens, avg time)
    - Time series data for charts (jobs, pages, tokens over time)
    - Token usage breakdown
    - Cost estimates
    - Model distribution

    **Multi-tenant isolation**: Users see only their tenant's data.
    **Admin access**: Admins can specify tenant_id to view other tenants.

    **Example:**
    ```
    GET /api/v1/metrics/dashboard?start_date=2025-01-01T00:00:00Z&end_date=2025-01-31T23:59:59Z
    ```
    """
    # Check admin permission if tenant_id specified
    permission_service = PermissionService(db)
    is_admin = permission_service.user_has_role(current_user, "admin")

    if tenant_id and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only admins can access other tenants' metrics"
        )

    # Build date range
    date_range = None
    if start_date and end_date:
        date_range = DateRange(start_date=start_date, end_date=end_date)

    # Get metrics
    metrics_service = MetricsService(db)
    return metrics_service.get_dashboard_metrics(
        tenant_id=current_user.tenant_id,
        date_range=date_range,
        is_admin=is_admin,
        requested_tenant_id=tenant_id
    )


@router.get("/jobs/completed", response_model=CompletedJobsResponse)
async def get_completed_jobs(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    start_date: Optional[datetime] = Query(None, description="Start date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO 8601)"),
    sort_by: str = Query("completed_at", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    tenant_id: Optional[UUID] = Query(None, description="Admin-only: filter by tenant"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of completed jobs for billing.

    Returns detailed job information including:
    - Document details
    - Token usage (input/output/total)
    - Processing time
    - Estimated cost per job
    - Total cost for the page

    **Pagination**: Use page and page_size parameters.
    **Sorting**: Sort by any job field (completed_at, estimated_cost, etc.).
    **Filtering**: Optional date range filter.

    **Multi-tenant isolation**: Users see only their tenant's data.
    **Admin access**: Admins can specify tenant_id to view other tenants.

    **Example:**
    ```
    GET /api/v1/metrics/jobs/completed?page=1&page_size=20&sort_by=completed_at&sort_order=desc
    ```
    """
    # Check admin permission if tenant_id specified
    permission_service = PermissionService(db)
    is_admin = permission_service.user_has_role(current_user, "admin")

    if tenant_id and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only admins can access other tenants' jobs"
        )

    # Build date range
    date_range = None
    if start_date and end_date:
        date_range = DateRange(start_date=start_date, end_date=end_date)

    # Get completed jobs
    metrics_service = MetricsService(db)
    return metrics_service.get_completed_jobs(
        tenant_id=current_user.tenant_id,
        page=page,
        page_size=page_size,
        date_range=date_range,
        sort_by=sort_by,
        sort_order=sort_order,
        is_admin=is_admin,
        requested_tenant_id=tenant_id
    )
```

#### 4.2 API Registration

**File:** `app/main.py` (Add to existing routers)

```python
from app.api import metrics

# Add to existing router includes
app.include_router(metrics.router)
```

---

### 5. Presentation Layer Design (Frontend)

#### 5.1 Frontend Structure

```
frontend/src/
├── pages/
│   ├── Dashboard.tsx               # Metrics dashboard page
│   └── BillingDetails.tsx          # Completed jobs table page
├── components/
│   ├── metrics/
│   │   ├── StatsCard.tsx           # Reusable stats card
│   │   ├── MetricsCharts.tsx       # Chart container
│   │   ├── JobsChart.tsx           # Jobs over time line chart
│   │   ├── PagesChart.tsx          # Pages over time line chart
│   │   ├── TokensChart.tsx         # Tokens over time line chart
│   │   ├── ModelDistributionChart.tsx  # Pie chart
│   │   └── CompletedJobsTable.tsx  # Paginated data table
│   └── data-table/
│       └── DataTable.tsx           # Generic table component (reuse existing)
├── services/
│   └── metrics.service.ts          # API client for metrics
└── types/
    └── metrics.ts                  # TypeScript types
```

#### 5.2 TypeScript Types

**File:** `frontend/src/types/metrics.ts`

```typescript
export interface DateRangeFilter {
  start_date: string; // ISO 8601
  end_date: string;
}

export interface TimeSeriesDataPoint {
  timestamp: string;
  value: number;
  label: string;
}

export interface TokenUsageMetrics {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

export interface CostMetrics {
  input_cost: string; // Decimal as string
  output_cost: string;
  total_cost: string;
  currency: string;
}

export interface DashboardStatsCard {
  label: string;
  value: string;
  change?: string;
  trend?: 'up' | 'down';
}

export interface ModelDistribution {
  model: string;
  count: number;
}

export interface DashboardMetricsResponse {
  stats: DashboardStatsCard[];
  jobs_over_time: TimeSeriesDataPoint[];
  pages_over_time: TimeSeriesDataPoint[];
  tokens_over_time: TimeSeriesDataPoint[];
  token_usage: TokenUsageMetrics;
  estimated_cost: CostMetrics;
  model_distribution: ModelDistribution[];
}

export interface CompletedJobItem {
  id: string;
  document_id: string;
  document_filename: string;
  page_count: number;
  model_provider: string;
  model_name: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  processing_time_ms: number;
  estimated_cost: string; // Decimal as string
  completed_at: string;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface CompletedJobsResponse {
  jobs: CompletedJobItem[];
  pagination: PaginationMeta;
  total_cost: string;
}
```

#### 5.3 API Service

**File:** `frontend/src/services/metrics.service.ts`

```typescript
import { api } from '@/lib/api';
import type {
  DashboardMetricsResponse,
  CompletedJobsResponse,
  DateRangeFilter,
} from '@/types/metrics';

export const metricsService = {
  /**
   * Get dashboard metrics.
   */
  async getDashboardMetrics(
    dateRange?: DateRangeFilter,
    tenantId?: string
  ): Promise<DashboardMetricsResponse> {
    const params = new URLSearchParams();

    if (dateRange) {
      params.append('start_date', dateRange.start_date);
      params.append('end_date', dateRange.end_date);
    }

    if (tenantId) {
      params.append('tenant_id', tenantId);
    }

    const response = await api.get(`/metrics/dashboard?${params.toString()}`);
    return response.data;
  },

  /**
   * Get completed jobs for billing.
   */
  async getCompletedJobs(options: {
    page: number;
    pageSize: number;
    dateRange?: DateRangeFilter;
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
    tenantId?: string;
  }): Promise<CompletedJobsResponse> {
    const params = new URLSearchParams({
      page: options.page.toString(),
      page_size: options.pageSize.toString(),
      sort_by: options.sortBy || 'completed_at',
      sort_order: options.sortOrder || 'desc',
    });

    if (options.dateRange) {
      params.append('start_date', options.dateRange.start_date);
      params.append('end_date', options.dateRange.end_date);
    }

    if (options.tenantId) {
      params.append('tenant_id', options.tenantId);
    }

    const response = await api.get(`/metrics/jobs/completed?${params.toString()}`);
    return response.data;
  },
};
```

#### 5.4 Dashboard Page Component

**File:** `frontend/src/pages/Dashboard.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { Page, PageHeader, PageContent } from '@/components/layout';
import { StatsCard } from '@/components/metrics/StatsCard';
import { JobsChart } from '@/components/metrics/JobsChart';
import { PagesChart } from '@/components/metrics/PagesChart';
import { TokensChart } from '@/components/metrics/TokensChart';
import { ModelDistributionChart } from '@/components/metrics/ModelDistributionChart';
import { metricsService } from '@/services/metrics.service';
import type { DashboardMetricsResponse } from '@/types/metrics';
import { Alert } from '@/components/ui/alert';

export function Dashboard() {
  const [metrics, setMetrics] = useState<DashboardMetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMetrics();
  }, []);

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      const data = await metricsService.getDashboardMetrics();
      setMetrics(data);
    } catch (err) {
      setError('Failed to load dashboard metrics');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Page>
        <PageContent>
          <div className="flex items-center justify-center h-64">
            <p className="text-muted-foreground">Loading dashboard...</p>
          </div>
        </PageContent>
      </Page>
    );
  }

  if (error || !metrics) {
    return (
      <Page>
        <PageContent>
          <Alert variant="destructive">{error || 'Failed to load metrics'}</Alert>
        </PageContent>
      </Page>
    );
  }

  return (
    <Page>
      <PageHeader
        breadcrumbs={[{ label: 'Dashboard' }]}
        title="Dashboard"
        subtitle="Overview of your document processing metrics"
      />
      <PageContent>
        {/* Stats Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {metrics.stats.map((stat) => (
            <StatsCard
              key={stat.label}
              label={stat.label}
              value={stat.value}
              change={stat.change}
              trend={stat.trend}
            />
          ))}
        </div>

        {/* Charts Row 1 */}
        <div className="grid gap-4 md:grid-cols-2">
          <JobsChart data={metrics.jobs_over_time} />
          <PagesChart data={metrics.pages_over_time} />
        </div>

        {/* Charts Row 2 */}
        <div className="grid gap-4 md:grid-cols-2">
          <TokensChart data={metrics.tokens_over_time} />
          <ModelDistributionChart data={metrics.model_distribution} />
        </div>

        {/* Cost Summary Card */}
        <div className="rounded-lg border bg-card p-6">
          <h3 className="text-lg font-semibold mb-4">Estimated Costs</h3>
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <p className="text-sm text-muted-foreground">Input Tokens</p>
              <p className="text-2xl font-bold">
                ${parseFloat(metrics.estimated_cost.input_cost).toFixed(4)}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Output Tokens</p>
              <p className="text-2xl font-bold">
                ${parseFloat(metrics.estimated_cost.output_cost).toFixed(4)}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Total</p>
              <p className="text-2xl font-bold">
                ${parseFloat(metrics.estimated_cost.total_cost).toFixed(4)}
              </p>
            </div>
          </div>
        </div>
      </PageContent>
    </Page>
  );
}
```

#### 5.5 Chart Components

**File:** `frontend/src/components/metrics/JobsChart.tsx`

```typescript
import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { TimeSeriesDataPoint } from '@/types/metrics';

interface JobsChartProps {
  data: TimeSeriesDataPoint[];
}

export function JobsChart({ data }: JobsChartProps) {
  return (
    <div className="rounded-lg border bg-card p-6">
      <h3 className="text-lg font-semibold mb-4">Jobs Over Time</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 12 }}
          />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Line
            type="monotone"
            dataKey="value"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={{ fill: 'hsl(var(--primary))' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

**File:** `frontend/src/components/metrics/ModelDistributionChart.tsx`

```typescript
import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts';
import type { ModelDistribution } from '@/types/metrics';

interface ModelDistributionChartProps {
  data: ModelDistribution[];
}

const COLORS = [
  'hsl(var(--primary))',
  'hsl(var(--secondary))',
  'hsl(var(--accent))',
  'hsl(var(--muted))',
];

export function ModelDistributionChart({ data }: ModelDistributionChartProps) {
  return (
    <div className="rounded-lg border bg-card p-6">
      <h3 className="text-lg font-semibold mb-4">Model Distribution</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            dataKey="count"
            nameKey="model"
            cx="50%"
            cy="50%"
            outerRadius={100}
            label={(entry) => `${entry.model}: ${entry.count}`}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
```

#### 5.6 Completed Jobs Table Page

**File:** `frontend/src/pages/BillingDetails.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { Page, PageHeader, PageContent } from '@/components/layout';
import { CompletedJobsTable } from '@/components/metrics/CompletedJobsTable';
import { metricsService } from '@/services/metrics.service';
import type { CompletedJobsResponse } from '@/types/metrics';
import { Alert } from '@/components/ui/alert';

export function BillingDetails() {
  const [data, setData] = useState<CompletedJobsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);

  useEffect(() => {
    fetchCompletedJobs();
  }, [page]);

  const fetchCompletedJobs = async () => {
    try {
      setLoading(true);
      const response = await metricsService.getCompletedJobs({
        page,
        pageSize,
      });
      setData(response);
    } catch (err) {
      setError('Failed to load completed jobs');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (error) {
    return (
      <Page>
        <PageContent>
          <Alert variant="destructive">{error}</Alert>
        </PageContent>
      </Page>
    );
  }

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Billing Details' },
        ]}
        title="Billing Details"
        subtitle="View all completed jobs and their costs"
      />
      <PageContent>
        {data && (
          <>
            {/* Summary Card */}
            <div className="rounded-lg border bg-card p-6 mb-6">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-sm text-muted-foreground">Page Total</p>
                  <p className="text-2xl font-bold">
                    ${parseFloat(data.total_cost).toFixed(4)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Jobs</p>
                  <p className="text-2xl font-bold">
                    {data.pagination.total_items}
                  </p>
                </div>
              </div>
            </div>

            {/* Table */}
            <CompletedJobsTable
              jobs={data.jobs}
              pagination={data.pagination}
              loading={loading}
              onPageChange={setPage}
            />
          </>
        )}
      </PageContent>
    </Page>
  );
}
```

**File:** `frontend/src/components/metrics/CompletedJobsTable.tsx`

```typescript
import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import type { CompletedJobItem, PaginationMeta } from '@/types/metrics';

interface CompletedJobsTableProps {
  jobs: CompletedJobItem[];
  pagination: PaginationMeta;
  loading: boolean;
  onPageChange: (page: number) => void;
}

export function CompletedJobsTable({
  jobs,
  pagination,
  loading,
  onPageChange,
}: CompletedJobsTableProps) {
  return (
    <div className="rounded-lg border bg-card">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Document</TableHead>
            <TableHead>Pages</TableHead>
            <TableHead>Model</TableHead>
            <TableHead className="text-right">Input Tokens</TableHead>
            <TableHead className="text-right">Output Tokens</TableHead>
            <TableHead className="text-right">Total Tokens</TableHead>
            <TableHead className="text-right">Time (s)</TableHead>
            <TableHead className="text-right">Cost</TableHead>
            <TableHead>Completed</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading ? (
            <TableRow>
              <TableCell colSpan={9} className="text-center py-8">
                Loading...
              </TableCell>
            </TableRow>
          ) : jobs.length === 0 ? (
            <TableRow>
              <TableCell colSpan={9} className="text-center py-8">
                No completed jobs found
              </TableCell>
            </TableRow>
          ) : (
            jobs.map((job) => (
              <TableRow key={job.id}>
                <TableCell className="font-medium max-w-xs truncate">
                  {job.document_filename}
                </TableCell>
                <TableCell>{job.page_count}</TableCell>
                <TableCell>
                  <div className="text-sm">
                    <div className="font-medium">{job.model_provider}</div>
                    <div className="text-muted-foreground">{job.model_name}</div>
                  </div>
                </TableCell>
                <TableCell className="text-right">
                  {job.input_tokens.toLocaleString()}
                </TableCell>
                <TableCell className="text-right">
                  {job.output_tokens.toLocaleString()}
                </TableCell>
                <TableCell className="text-right">
                  {job.total_tokens.toLocaleString()}
                </TableCell>
                <TableCell className="text-right">
                  {(job.processing_time_ms / 1000).toFixed(2)}
                </TableCell>
                <TableCell className="text-right font-medium">
                  ${parseFloat(job.estimated_cost).toFixed(4)}
                </TableCell>
                <TableCell>
                  {new Date(job.completed_at).toLocaleString()}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {/* Pagination */}
      <div className="flex items-center justify-between px-6 py-4 border-t">
        <div className="text-sm text-muted-foreground">
          Showing {(pagination.page - 1) * pagination.page_size + 1} to{' '}
          {Math.min(pagination.page * pagination.page_size, pagination.total_items)} of{' '}
          {pagination.total_items} jobs
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(pagination.page - 1)}
            disabled={pagination.page === 1}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(pagination.page + 1)}
            disabled={pagination.page >= pagination.total_pages}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
```

#### 5.7 Stats Card Component

**File:** `frontend/src/components/metrics/StatsCard.tsx`

```typescript
import React from 'react';
import { ArrowUp, ArrowDown } from 'lucide-react';

interface StatsCardProps {
  label: string;
  value: string;
  change?: string;
  trend?: 'up' | 'down';
}

export function StatsCard({ label, value, change, trend }: StatsCardProps) {
  return (
    <div className="rounded-lg border bg-card p-6">
      <p className="text-sm text-muted-foreground mb-2">{label}</p>
      <p className="text-3xl font-bold mb-2">{value}</p>
      {change && trend && (
        <div
          className={`flex items-center gap-1 text-sm ${
            trend === 'up' ? 'text-green-600' : 'text-red-600'
          }`}
        >
          {trend === 'up' ? <ArrowUp size={16} /> : <ArrowDown size={16} />}
          <span>{change}</span>
        </div>
      )}
    </div>
  );
}
```

---

### 6. SOLID Principles Application

#### Single Responsibility Principle (SRP)
- **PricingService**: Only calculates costs, no data access
- **MetricsService**: Only aggregates metrics, delegates pricing to PricingService
- **Each DTO**: Single purpose for data transfer
- **Each chart component**: Only renders one type of visualization

#### Open/Closed Principle (OCP)
- **PricingService**: Pricing table is configurable, can add new models without modifying calculation logic
- **Chart components**: Extend with new chart types without modifying existing ones
- **API endpoints**: Add new endpoints without changing existing ones

#### Liskov Substitution Principle (LSP)
- **Value Objects**: All immutable, can be substituted safely
- **DTOs**: All follow Pydantic BaseModel contract

#### Interface Segregation Principle (ISP)
- **Separate DTOs**: DashboardMetricsResponse vs CompletedJobsResponse
- **Focused components**: StatsCard, chart components each have minimal props
- **API endpoints**: Each endpoint serves one specific use case

#### Dependency Inversion Principle (DIP)
- **MetricsService** depends on abstractions (Session interface, PricingService interface)
- **API routes** depend on service abstraction via dependency injection
- **Frontend components** depend on service interface, not implementation

---

### 7. Testing Strategy

#### 7.1 Unit Tests

**Domain Layer Tests** (`tests/domain/metrics/test_pricing_service.py`):
```python
def test_pricing_service_calculate_cost_google():
    """Test cost calculation for Google models."""
    service = PricingService()
    token_usage = TokenUsage(input_tokens=1_000_000, output_tokens=500_000)

    cost = service.calculate_cost(token_usage, "google", "gemini-2.5-flash")

    assert cost.input_cost == Decimal("0.075")
    assert cost.output_cost == Decimal("0.15")
    assert cost.total_cost == Decimal("0.225")
    assert cost.currency == "USD"


def test_pricing_service_unknown_model_fallback():
    """Test fallback pricing for unknown models."""
    service = PricingService()
    token_usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000)

    cost = service.calculate_cost(token_usage, "unknown", "unknown-model")

    # Should use fallback pricing
    assert cost.total_cost > Decimal("0")
```

**Application Layer Tests** (`tests/services/test_metrics_service.py`):
```python
def test_metrics_service_get_dashboard_metrics(db_session, sample_tenant):
    """Test dashboard metrics aggregation."""
    # Setup: Create test data
    # ... create documents, jobs, results

    service = MetricsService(db_session)

    result = service.get_dashboard_metrics(
        tenant_id=sample_tenant.id,
        date_range=None,
        is_admin=False
    )

    assert len(result.stats) == 4
    assert result.token_usage.total_tokens > 0
    assert len(result.jobs_over_time) > 0


def test_metrics_service_tenant_isolation(db_session, tenant_a, tenant_b):
    """Test multi-tenant isolation."""
    # Setup: Create data for both tenants
    # ... create documents for tenant_a and tenant_b

    service = MetricsService(db_session)

    # Tenant A should only see their data
    result_a = service.get_dashboard_metrics(tenant_id=tenant_a.id)
    # Tenant B should only see their data
    result_b = service.get_dashboard_metrics(tenant_id=tenant_b.id)

    # Verify isolation
    # ... assertions
```

#### 7.2 Integration Tests

**API Endpoint Tests** (`tests/api/test_metrics.py`):
```python
def test_get_dashboard_metrics_success(client, auth_headers):
    """Test successful dashboard metrics retrieval."""
    response = client.get(
        "/api/v1/metrics/dashboard",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "stats" in data
    assert "jobs_over_time" in data


def test_get_completed_jobs_pagination(client, auth_headers):
    """Test pagination for completed jobs."""
    response = client.get(
        "/api/v1/metrics/jobs/completed?page=1&page_size=10",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["jobs"]) <= 10
    assert data["pagination"]["page"] == 1


def test_admin_can_access_other_tenant_metrics(client, admin_headers, tenant_id):
    """Test admin access to other tenant's metrics."""
    response = client.get(
        f"/api/v1/metrics/dashboard?tenant_id={tenant_id}",
        headers=admin_headers
    )

    assert response.status_code == 200


def test_non_admin_cannot_access_other_tenant_metrics(client, user_headers, tenant_id):
    """Test non-admin blocked from other tenant's metrics."""
    response = client.get(
        f"/api/v1/metrics/dashboard?tenant_id={tenant_id}",
        headers=user_headers
    )

    assert response.status_code == 403
```

#### 7.3 Frontend Tests

**Component Tests** (`frontend/src/components/metrics/__tests__/StatsCard.test.tsx`):
```typescript
import { render, screen } from '@testing-library/react';
import { StatsCard } from '../StatsCard';

describe('StatsCard', () => {
  it('renders label and value', () => {
    render(<StatsCard label="Total Jobs" value="150" />);

    expect(screen.getByText('Total Jobs')).toBeInTheDocument();
    expect(screen.getByText('150')).toBeInTheDocument();
  });

  it('renders trend indicator when provided', () => {
    render(
      <StatsCard label="Total Jobs" value="150" change="+12%" trend="up" />
    );

    expect(screen.getByText('+12%')).toBeInTheDocument();
  });
});
```

#### 7.4 Coverage Targets

- **Domain Layer**: 100% (business logic critical)
- **Application Layer**: 90% (service methods)
- **Infrastructure Layer**: 80% (API endpoints)
- **Frontend Components**: 75% (UI components)

---

### 8. Implementation Plan

#### Phase 1: Domain Layer (Day 1, 4 hours)

**Files to Create:**
1. `app/domain/metrics/value_objects.py`
   - Implement DateRange, TokenUsage, CostEstimate, MetricsPeriod
   - Write unit tests

2. `app/domain/metrics/pricing_service.py`
   - Implement PricingService with PRICING_TABLE
   - Write unit tests for all models and fallback

**Dependencies:** None (pure domain logic)

**Tests:**
- `tests/domain/metrics/test_value_objects.py`
- `tests/domain/metrics/test_pricing_service.py`

#### Phase 2: Application Layer (Day 2-3, 8 hours)

**Files to Create:**
1. `app/schemas/metrics.py`
   - Implement all DTOs with Pydantic validation
   - Write schema validation tests

2. `app/services/metrics_service.py`
   - Implement MetricsService with all methods
   - Write comprehensive unit tests with mocked DB

**Dependencies:**
- Domain layer (Phase 1)
- Existing models (Document, ExtractionJob, ExtractionResult)

**Tests:**
- `tests/schemas/test_metrics.py`
- `tests/services/test_metrics_service.py`

**Critical Test Scenarios:**
- Tenant isolation enforcement
- Date range filtering
- Pagination correctness
- Cost calculation accuracy
- Time series aggregation

#### Phase 3: Infrastructure Layer (Day 4, 6 hours)

**Files to Create:**
1. `app/api/metrics.py`
   - Implement GET /metrics/dashboard endpoint
   - Implement GET /metrics/jobs/completed endpoint
   - Add comprehensive API documentation
   - Write integration tests

2. Update `app/main.py`
   - Register metrics router

**Dependencies:**
- Application layer (Phase 2)
- Auth dependencies (existing)

**Tests:**
- `tests/api/test_metrics.py`

**Critical Test Scenarios:**
- Authentication required
- Admin vs non-admin access control
- Query parameter validation
- Error handling (invalid dates, missing tenant)

#### Phase 4: Frontend Components (Day 5-6, 12 hours)

**Files to Create:**

**Day 5 (Types & Services):**
1. `frontend/src/types/metrics.ts`
2. `frontend/src/services/metrics.service.ts`
3. Write service tests

**Day 6 (Components):**
4. `frontend/src/components/metrics/StatsCard.tsx`
5. `frontend/src/components/metrics/JobsChart.tsx`
6. `frontend/src/components/metrics/PagesChart.tsx`
7. `frontend/src/components/metrics/TokensChart.tsx`
8. `frontend/src/components/metrics/ModelDistributionChart.tsx`
9. `frontend/src/components/metrics/CompletedJobsTable.tsx`

**Dependencies:**
- Backend API (Phase 3)
- Existing UI components (shadcn/ui)
- recharts library (install)

**Critical Tasks:**
- Install recharts: `npm install recharts`
- Verify Tailwind 4 styling with context7
- Test responsive layouts on mobile

#### Phase 5: Pages Integration (Day 7, 6 hours)

**Files to Create:**
1. `frontend/src/pages/Dashboard.tsx`
2. `frontend/src/pages/BillingDetails.tsx`

**Update:**
3. `frontend/src/App.tsx` - Add routes
4. `frontend/src/components/layout/Sidebar.tsx` - Add navigation links

**Dependencies:**
- Frontend components (Phase 4)
- Existing layout system

**Critical Tasks:**
- Add routes to App.tsx
- Add sidebar navigation items
- Test authentication flow
- Verify breadcrumb navigation

#### Phase 6: End-to-End Testing (Day 8, 4 hours)

**Tasks:**
1. Manual testing of complete flow
2. Verify multi-tenant isolation
3. Test admin vs non-admin access
4. Verify date range filtering
5. Test pagination
6. Verify cost calculations accuracy
7. Performance testing with large datasets

**Test Scenarios:**
- Create test data with multiple tenants
- Verify dashboard loads correctly
- Verify charts render with real data
- Test table sorting and pagination
- Verify CSV export (if implemented)

#### Phase 7: Documentation & Deployment (Day 9, 4 hours)

**Documentation to Create:**
1. `docs/guides/2025-11-03-metrics-and-billing-guide.md`
   - User guide for metrics dashboard
   - How to read billing details
   - Cost estimation explanation

2. Update `docs/architecture/2025-11-03-metrics-and-billing-system.md`
   - Add deployment notes
   - Add performance optimization tips

**Deployment Checklist:**
- [ ] Run all tests (backend + frontend)
- [ ] Database migration (if schema changed)
- [ ] Environment variable configuration
- [ ] Deploy backend API
- [ ] Deploy frontend
- [ ] Verify production metrics
- [ ] Monitor error logs

---

### 9. Performance Considerations

#### 9.1 Database Query Optimization

**Indexed Queries:**
```sql
-- Verify existing indexes
EXPLAIN ANALYZE
SELECT COUNT(DISTINCT ej.id)
FROM extraction_results er
JOIN extraction_jobs ej ON er.extraction_job_id = ej.id
JOIN documents d ON ej.document_id = d.id
WHERE d.tenant_id = '...'
  AND ej.status = 'completed'
  AND er.created_at >= '...'
  AND er.created_at <= '...';
```

**Materialized View (Future Optimization):**

If dashboard becomes slow with large datasets (>1M jobs), consider materialized view:

```sql
CREATE MATERIALIZED VIEW metrics_daily_summary AS
SELECT
    d.tenant_id,
    DATE_TRUNC('day', er.created_at) as day,
    COUNT(DISTINCT ej.id) as jobs_count,
    COUNT(er.id) as pages_count,
    SUM(er.input_tokens) as input_tokens,
    SUM(er.output_tokens) as output_tokens,
    AVG(er.processing_time_ms) as avg_processing_time
FROM extraction_results er
JOIN extraction_jobs ej ON er.extraction_job_id = ej.id
JOIN documents d ON ej.document_id = d.id
WHERE ej.status = 'completed'
GROUP BY d.tenant_id, DATE_TRUNC('day', er.created_at);

CREATE UNIQUE INDEX idx_metrics_daily_tenant_day
ON metrics_daily_summary (tenant_id, day);

-- Refresh daily via cron job
REFRESH MATERIALIZED VIEW CONCURRENTLY metrics_daily_summary;
```

#### 9.2 Caching Strategy

**Redis Cache for Dashboard Metrics:**

```python
# Future enhancement: Add Redis caching
import redis
import json
from datetime import timedelta

class MetricsService:
    def __init__(self, db: Session, redis_client: redis.Redis = None):
        self.db = db
        self.redis = redis_client
        self.pricing_service = PricingService()

    def get_dashboard_metrics(self, tenant_id: UUID, ...) -> DashboardMetricsResponse:
        # Check cache
        if self.redis:
            cache_key = f"metrics:dashboard:{tenant_id}:{date_range.start_date}:{date_range.end_date}"
            cached = self.redis.get(cache_key)
            if cached:
                return DashboardMetricsResponse(**json.loads(cached))

        # Compute metrics
        result = self._compute_metrics(...)

        # Cache for 5 minutes
        if self.redis:
            self.redis.setex(cache_key, timedelta(minutes=5), result.json())

        return result
```

#### 9.3 Pagination Performance

**Cursor-Based Pagination (Future Enhancement):**

For very large result sets, replace offset pagination with cursor-based:

```python
# Current (offset-based)
query.offset(offset).limit(page_size)

# Future (cursor-based)
query.filter(ExtractionJob.completed_at < cursor_timestamp).limit(page_size)
```

---

### 10. Security Considerations

#### 10.1 Multi-Tenant Isolation

**Enforcement at Service Layer:**
```python
def _resolve_tenant_id(self, user_tenant_id, is_admin, requested_tenant_id):
    """CRITICAL: Always enforce tenant isolation."""
    if requested_tenant_id:
        if not is_admin:
            raise ValueError("Only admins can access other tenants' data")
        return requested_tenant_id
    return user_tenant_id
```

**Database-Level Row Security (Future Enhancement):**
```sql
-- PostgreSQL Row-Level Security
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON documents
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

#### 10.2 API Rate Limiting

**Protect Metrics Endpoints:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/dashboard")
@limiter.limit("10/minute")  # Max 10 requests per minute
async def get_dashboard_metrics(...):
    ...
```

#### 10.3 Cost Data Protection

**Sensitive Information:**
- Cost estimates should only be visible to tenant users
- Admin users can see all costs (for support)
- Never expose pricing table in API responses
- Log all admin access to other tenants' data

---

### 11. Architectural Decisions

#### ADR-001: No Separate Metrics Table

**Context:**
Should we create a dedicated `metrics` table or use existing `extraction_results`?

**Decision:**
Use existing `extraction_results` table with aggregation queries.

**Rationale:**
- Single source of truth (DRY principle)
- No data duplication
- Real-time metrics (no sync lag)
- Existing indexes sufficient for current scale
- Can add materialized views later if needed

**Consequences:**
- Aggregation queries on large datasets may be slow
- Mitigation: Add materialized views or Redis cache if performance degrades
- Benefit: Simpler architecture, fewer moving parts

#### ADR-002: Domain-Driven Pricing Service

**Context:**
Where should pricing logic live?

**Decision:**
Create domain service `PricingService` separate from infrastructure.

**Rationale:**
- Pricing is core business logic (belongs in domain)
- Easily testable in isolation
- Can be reused across application layer
- Follows Single Responsibility Principle

**Consequences:**
- Clear separation of concerns
- Easy to modify pricing without touching data access
- Simple to add new models or pricing tiers

#### ADR-003: Frontend Chart Library - Recharts

**Context:**
Choose between Recharts, Chart.js, or Victory.

**Decision:**
Use Recharts for all visualizations.

**Rationale:**
- React-first library (not wrapper around Canvas)
- Declarative API matches React patterns
- Good TypeScript support
- Responsive by default
- MIT license

**Consequences:**
- Consistent chart styling across app
- Easy to customize with Tailwind CSS
- Bundle size: ~150KB (acceptable)

#### ADR-004: Pagination Strategy

**Context:**
Use offset-based or cursor-based pagination?

**Decision:**
Start with offset-based, migrate to cursor-based if needed.

**Rationale:**
- Offset-based simpler to implement
- Sufficient for current scale (<100K jobs per tenant)
- Can migrate later without API contract changes

**Consequences:**
- Performance acceptable for current scale
- Monitor query times, add cursor-based if >1M jobs

---

### 12. Monitoring & Observability

#### 12.1 Key Metrics to Monitor

**Backend:**
- `/metrics/dashboard` response time (target: <500ms)
- `/metrics/jobs/completed` response time (target: <1s)
- Database query execution time
- Cache hit rate (if Redis implemented)

**Frontend:**
- Dashboard page load time (target: <2s)
- Chart render time
- API request failures

#### 12.2 Logging

**Structured Logging for Metrics:**
```python
import logging

logger = logging.getLogger(__name__)

def get_dashboard_metrics(self, tenant_id: UUID, ...):
    logger.info(
        "Fetching dashboard metrics",
        extra={
            "tenant_id": str(tenant_id),
            "date_range": str(date_range),
            "is_admin": is_admin
        }
    )

    start_time = time.time()
    result = self._compute_metrics(...)
    duration = time.time() - start_time

    logger.info(
        "Dashboard metrics computed",
        extra={
            "tenant_id": str(tenant_id),
            "duration_ms": int(duration * 1000),
            "jobs_count": len(result.jobs_over_time)
        }
    )
```

---

## Summary

This metrics and billing system design follows Clean Architecture and SOLID principles throughout. The implementation is divided into clear layers with proper dependency management, ensuring maintainability and testability.

**Key Strengths:**

1. **No Database Schema Changes**: Leverages existing models efficiently
2. **Clean Separation**: Domain logic separate from infrastructure
3. **Testable**: Each layer can be tested in isolation
4. **Multi-Tenant Secure**: Tenant isolation enforced at service layer
5. **Performant**: Optimized queries with proper indexing
6. **Extensible**: Easy to add new metrics or pricing models

**Implementation Effort:**

- **Backend**: 3-4 days (domain, application, infrastructure layers with tests)
- **Frontend**: 3-4 days (components, pages, integration)
- **Testing & Documentation**: 1-2 days
- **Total**: 8-10 days for complete implementation

**Next Steps:**

1. Review and approve architecture
2. Begin Phase 1 (Domain Layer)
3. Implement TDD throughout all phases
4. Deploy iteratively (backend first, then frontend)
