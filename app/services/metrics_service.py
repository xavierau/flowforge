"""Service for calculating and retrieving metrics."""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from app.models.extraction_job import ExtractionJob
from app.models.extraction_result import ExtractionResult
from app.models.document import Document, DocumentPage
from app.domain.metrics import PricingService
from app.schemas.metrics import (
    DashboardMetricsResponse,
    MetricStats,
    TimeSeriesDataPoint,
    TokenUsageData,
    ModelDistribution,
    CompletedJobsResponse,
    CompletedJobItem,
)


class MetricsService:
    """Service for calculating metrics and billing data."""

    def __init__(self, db: Session):
        """
        Initialize metrics service.

        Args:
            db: Database session
        """
        self.db = db

    def get_dashboard_metrics(
        self, tenant_id: UUID, days: int = 30
    ) -> DashboardMetricsResponse:
        """
        Get dashboard metrics for a tenant.

        Args:
            tenant_id: Tenant ID to filter by
            days: Number of days to include (default 30)

        Returns:
            DashboardMetricsResponse with aggregated metrics
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get summary stats
        stats = self._get_summary_stats(tenant_id, start_date, end_date)

        print("stats", stats)

        # Get time series data
        jobs_over_time = self._get_jobs_over_time(tenant_id, start_date, end_date)
        pages_over_time = self._get_pages_over_time(tenant_id, start_date, end_date)
        tokens_over_time = self._get_tokens_over_time(tenant_id, start_date, end_date)

        # Get model distribution
        model_distribution = self._get_model_distribution(
            tenant_id, start_date, end_date
        )

        return DashboardMetricsResponse(
            stats=stats,
            jobs_over_time=jobs_over_time,
            pages_over_time=pages_over_time,
            tokens_over_time=tokens_over_time,
            model_distribution=model_distribution,
        )

    def get_completed_jobs(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> CompletedJobsResponse:
        """
        Get paginated list of completed jobs for billing.

        Args:
            tenant_id: Tenant ID to filter by
            page: Page number (1-indexed)
            page_size: Number of items per page
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            CompletedJobsResponse with paginated jobs
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"get_completed_jobs called with tenant_id={tenant_id}, page={page}, page_size={page_size}, start_date={start_date}, end_date={end_date}")

        # Build base query - filter by ExtractionJob.tenant_id directly
        # Note: We still join Document to get filename for display
        query = (
            self.db.query(ExtractionJob, Document)
            .join(Document, ExtractionJob.document_id == Document.id)
            .filter(ExtractionJob.tenant_id == tenant_id)  # Changed from Document.tenant_id
            .filter(ExtractionJob.status == "completed")
        )

        # Apply date filters
        if start_date:
            query = query.filter(ExtractionJob.completed_at >= start_date)
        if end_date:
            query = query.filter(ExtractionJob.completed_at <= end_date)

        # Get total count
        total = query.count()
        logger.info(f"Total completed jobs found: {total}")

        # Calculate pagination
        total_pages = (total + page_size - 1) // page_size
        offset = (page - 1) * page_size

        # Get paginated jobs
        results = query.order_by(ExtractionJob.completed_at.desc()).limit(page_size).offset(offset).all()

        # Convert to CompletedJobItem
        jobs = []
        total_cost = 0.0

        for job, document in results:
            # Calculate processing time
            processing_time = None
            if job.started_at and job.completed_at:
                delta = job.completed_at - job.started_at
                processing_time = delta.total_seconds()

            # Get aggregated token counts from extraction results
            token_stats = (
                self.db.query(
                    func.sum(func.coalesce(ExtractionResult.input_tokens, 0)).label("total_input"),
                    func.sum(func.coalesce(ExtractionResult.output_tokens, 0)).label("total_output"),
                    func.max(ExtractionResult.model_used).label("model_name")
                )
                .filter(ExtractionResult.extraction_job_id == job.id)
                .first()
            )

            input_tokens = token_stats.total_input or 0
            output_tokens = token_stats.total_output or 0
            model_used = token_stats.model_name or job.model_name or "unknown"

            # Calculate cost
            from app.domain.metrics.value_objects import TokenUsage

            token_usage = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            cost_estimate = PricingService.calculate_cost(token_usage, model_used)
            total_cost += cost_estimate.amount

            # Count pages processed from DocumentPage table
            pages_processed = (
                self.db.query(func.count(DocumentPage.id))
                .filter(DocumentPage.document_id == job.document_id)
                .scalar()
                or 0
            )

            job_item = CompletedJobItem(
                job_id=str(job.id),
                document_id=str(job.document_id),
                document_name=document.filename,
                model=model_used,
                pages_processed=pages_processed,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                estimated_cost=round(cost_estimate.amount, 6),
                processing_time=processing_time,
                completed_at=job.completed_at,
                tenant_id=str(document.tenant_id),
            )
            jobs.append(job_item)

        return CompletedJobsResponse(
            jobs=jobs,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            total_cost=round(total_cost, 2),
        )

    def _get_summary_stats(
        self, tenant_id: UUID, start_date: datetime, end_date: datetime
    ) -> MetricStats:
        """Get summary statistics."""
        # Query token sums from ExtractionResult, filtering by ExtractionJob.tenant_id
        token_query = (
            self.db.query(
                func.count(distinct(ExtractionJob.id)).label("total_jobs"),
                func.sum(func.coalesce(ExtractionResult.input_tokens, 0)).label("input_tokens"),
                func.sum(func.coalesce(ExtractionResult.output_tokens, 0)).label("output_tokens"),
            )
            .select_from(ExtractionJob)
            .join(Document, ExtractionJob.document_id == Document.id)
            .join(ExtractionResult, ExtractionResult.extraction_job_id == ExtractionJob.id)
            .filter(ExtractionJob.tenant_id == tenant_id)  # Changed from Document.tenant_id
            .filter(ExtractionJob.status == "completed")
            .filter(ExtractionJob.completed_at >= start_date)
            .filter(ExtractionJob.completed_at <= end_date)
        )

        result = token_query.first()

        total_jobs = result.total_jobs or 0
        input_tokens = result.input_tokens or 0
        output_tokens = result.output_tokens or 0
        total_tokens = input_tokens + output_tokens

        # Calculate total pages from DocumentPage table
        total_pages = (
            self.db.query(func.count(distinct(DocumentPage.id)))
            .select_from(ExtractionJob)
            .join(Document, ExtractionJob.document_id == Document.id)
            .join(DocumentPage, DocumentPage.document_id == Document.id)
            .filter(ExtractionJob.tenant_id == tenant_id)  # Changed from Document.tenant_id
            .filter(ExtractionJob.status == "completed")
            .filter(ExtractionJob.completed_at >= start_date)
            .filter(ExtractionJob.completed_at <= end_date)
            .scalar()
            or 0
        )

        # Use stored costs where available for this tenant
        estimated_cost = (
            self.db.query(func.sum(ExtractionJob.estimated_cost_usd))
            .filter(ExtractionJob.tenant_id == tenant_id)
            .filter(ExtractionJob.status == "completed")
            .filter(ExtractionJob.completed_at >= start_date)
            .filter(ExtractionJob.completed_at <= end_date)
            .filter(ExtractionJob.estimated_cost_usd.isnot(None))
            .scalar() or 0.0
        )

        return MetricStats(
            total_jobs=total_jobs,
            total_pages=total_pages,
            total_tokens=total_tokens,
            estimated_cost=round(float(estimated_cost), 2),
        )

    def _get_jobs_over_time(
        self, tenant_id: UUID, start_date: datetime, end_date: datetime
    ) -> List[TimeSeriesDataPoint]:
        """Get jobs completed per day."""
        # Create labeled expression to reuse in GROUP BY and ORDER BY
        day_trunc = func.date_trunc("day", ExtractionJob.completed_at).label("date")

        query = (
            self.db.query(
                day_trunc,
                func.count(distinct(ExtractionJob.id)).label("count"),
            )
            .join(Document, ExtractionJob.document_id == Document.id)
            .filter(ExtractionJob.tenant_id == tenant_id)  # Changed from Document.tenant_id
            .filter(ExtractionJob.status == "completed")
            .filter(ExtractionJob.completed_at >= start_date)
            .filter(ExtractionJob.completed_at <= end_date)
            .group_by(day_trunc)
            .order_by(day_trunc)
        )

        results = query.all()

        return [
            TimeSeriesDataPoint(
                date=date.strftime("%Y-%m-%d"), value=count
            )
            for date, count in results
        ]

    def _get_pages_over_time(
        self, tenant_id: UUID, start_date: datetime, end_date: datetime
    ) -> List[TimeSeriesDataPoint]:
        """Get pages processed per day."""
        # Create labeled expression to reuse in GROUP BY and ORDER BY
        day_trunc = func.date_trunc("day", ExtractionJob.completed_at).label("date")

        query = (
            self.db.query(
                day_trunc,
                func.count(distinct(DocumentPage.id)).label("count"),
            )
            .select_from(ExtractionJob)
            .join(Document, ExtractionJob.document_id == Document.id)
            .join(DocumentPage, DocumentPage.document_id == Document.id)
            .filter(ExtractionJob.tenant_id == tenant_id)  # Changed from Document.tenant_id
            .filter(ExtractionJob.status == "completed")
            .filter(ExtractionJob.completed_at >= start_date)
            .filter(ExtractionJob.completed_at <= end_date)
            .group_by(day_trunc)
            .order_by(day_trunc)
        )

        results = query.all()

        return [
            TimeSeriesDataPoint(
                date=date.strftime("%Y-%m-%d"), value=count
            )
            for date, count in results
        ]

    def _get_tokens_over_time(
        self, tenant_id: UUID, start_date: datetime, end_date: datetime
    ) -> List[TokenUsageData]:
        """Get token usage per day."""
        # Create labeled expression to reuse in GROUP BY and ORDER BY
        day_trunc = func.date_trunc("day", ExtractionJob.completed_at).label("date")

        query = (
            self.db.query(
                day_trunc,
                func.sum(func.coalesce(ExtractionResult.input_tokens, 0)).label("input_tokens"),
                func.sum(func.coalesce(ExtractionResult.output_tokens, 0)).label("output_tokens"),
            )
            .select_from(ExtractionJob)
            .join(Document, ExtractionJob.document_id == Document.id)
            .join(ExtractionResult, ExtractionResult.extraction_job_id == ExtractionJob.id)
            .filter(ExtractionJob.tenant_id == tenant_id)  # Changed from Document.tenant_id
            .filter(ExtractionJob.status == "completed")
            .filter(ExtractionJob.completed_at >= start_date)
            .filter(ExtractionJob.completed_at <= end_date)
            .group_by(day_trunc)
            .order_by(day_trunc)
        )

        results = query.all()

        return [
            TokenUsageData(
                date=date.strftime("%Y-%m-%d"),
                input_tokens=input_tokens or 0,
                output_tokens=output_tokens or 0,
                total_tokens=(input_tokens or 0) + (output_tokens or 0),
            )
            for date, input_tokens, output_tokens in results
        ]

    def _get_model_distribution(
        self, tenant_id: UUID, start_date: datetime, end_date: datetime
    ) -> List[ModelDistribution]:
        """Get model usage distribution."""
        query = (
            self.db.query(
                ExtractionResult.model_used.label("model"),
                func.count(distinct(ExtractionJob.id)).label("count"),
            )
            .select_from(ExtractionJob)
            .join(Document, ExtractionJob.document_id == Document.id)
            .join(ExtractionResult, ExtractionResult.extraction_job_id == ExtractionJob.id)
            .filter(ExtractionJob.tenant_id == tenant_id)  # Changed from Document.tenant_id
            .filter(ExtractionJob.status == "completed")
            .filter(ExtractionJob.completed_at >= start_date)
            .filter(ExtractionJob.completed_at <= end_date)
            .group_by(ExtractionResult.model_used)
            .order_by(func.count(distinct(ExtractionJob.id)).desc())
        )

        results = query.all()

        # Calculate total for percentages
        total = sum(count for _, count in results)

        if total == 0:
            return []

        return [
            ModelDistribution(
                model=model or "unknown",
                count=count,
                percentage=round((count / total) * 100, 2),
            )
            for model, count in results
        ]
