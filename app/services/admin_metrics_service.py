"""Service for admin metrics and platform-wide statistics."""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import func, and_, or_, case, desc
from sqlalchemy.orm import Session

from app.models import (
    Tenant, User, Document, ExtractionJob, ExtractionResult,
    ApiToken, CreditTransaction, Subscription, DocumentPage
)
from app.schemas.admin import (
    PlatformStatistics, TenantListItem, TenantMetrics,
    TenantSubscriptionInfo, TopTenantItem
)


class AdminMetricsService:
    """
    Service for aggregating platform-wide metrics and statistics.

    This service provides super admin dashboard metrics including:
    - Platform overview statistics
    - Tenant-level aggregations with pagination
    - Financial metrics and credit usage
    - Top tenants by activity

    All methods perform cross-tenant queries (no tenant isolation).
    Security is enforced at the API layer via require_super_admin dependency.
    """

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db

    def get_platform_statistics(self) -> PlatformStatistics:
        """
        Get comprehensive platform-wide statistics.

        Returns:
            PlatformStatistics with all key metrics across all tenants

        Example:
            >>> service = AdminMetricsService(db)
            >>> stats = service.get_platform_statistics()
            >>> print(f"Total tenants: {stats.total_tenants}")
        """
        # Tenant metrics
        tenant_stats = (
            self.db.query(
                func.count(Tenant.id).label('total'),
                func.sum(case((Tenant.status == 'active', 1), else_=0)).label('active'),
                func.sum(case((Tenant.status == 'suspended', 1), else_=0)).label('suspended'),
            )
            .first()
        )

        # New tenants in last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        new_tenants_30d = (
            self.db.query(func.count(Tenant.id))
            .filter(Tenant.created_at >= thirty_days_ago)
            .scalar() or 0
        )

        # User metrics
        user_stats = (
            self.db.query(
                func.count(User.id).label('total'),
                func.sum(case((User.is_active == True, 1), else_=0)).label('active'),
            )
            .first()
        )

        # Job metrics
        job_stats = (
            self.db.query(
                func.count(ExtractionJob.id).label('total'),
                func.sum(case((ExtractionJob.status == 'completed', 1), else_=0)).label('completed'),
                func.sum(case((ExtractionJob.status == 'failed', 1), else_=0)).label('failed'),
            )
            .first()
        )

        # Jobs in last 24 hours
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        jobs_24h = (
            self.db.query(func.count(ExtractionJob.id))
            .filter(ExtractionJob.created_at >= twenty_four_hours_ago)
            .scalar() or 0
        )

        # Document and page metrics
        doc_stats = (
            self.db.query(
                func.count(Document.id).label('total_documents'),
                func.count(DocumentPage.id).label('total_pages')
            )
            .outerjoin(DocumentPage, Document.id == DocumentPage.document_id)
            .first()
        )

        # Token metrics
        token_stats = (
            self.db.query(
                func.sum(ExtractionResult.input_tokens).label('input_tokens'),
                func.sum(ExtractionResult.output_tokens).label('output_tokens'),
            )
            .first()
        )

        total_input_tokens = token_stats.input_tokens or 0
        total_output_tokens = token_stats.output_tokens or 0
        total_tokens = total_input_tokens + total_output_tokens

        # Financial metrics (simplified cost estimate: $1 per 1000 tokens)
        estimated_total_cost = (total_tokens / 1000.0) * 1.0

        # Credit metrics
        credit_stats = (
            self.db.query(
                func.sum(case((CreditTransaction.transaction_type == 'purchase', CreditTransaction.amount), else_=0)).label('purchased'),
                func.sum(case((CreditTransaction.transaction_type == 'deduction', -CreditTransaction.amount), else_=0)).label('consumed'),
            )
            .first()
        )

        # API token count
        api_token_count = (
            self.db.query(func.count(ApiToken.id))
            .filter(ApiToken.is_active == True)
            .scalar() or 0
        )

        return PlatformStatistics(
            # Tenant metrics
            total_tenants=tenant_stats.total or 0,
            active_tenants=tenant_stats.active or 0,
            suspended_tenants=tenant_stats.suspended or 0,
            new_tenants_30d=new_tenants_30d,
            # User metrics
            total_users=user_stats.total or 0,
            active_users=user_stats.active or 0,
            # Job metrics
            total_jobs=job_stats.total or 0,
            completed_jobs=job_stats.completed or 0,
            failed_jobs=job_stats.failed or 0,
            jobs_24h=jobs_24h,
            # Document metrics
            total_documents=doc_stats.total_documents or 0,
            total_pages=doc_stats.total_pages or 0,
            # Token metrics
            total_tokens=total_tokens,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            # Financial metrics
            estimated_total_cost=estimated_total_cost,
            total_credits_purchased=credit_stats.purchased or 0,
            total_credits_consumed=credit_stats.consumed or 0,
            # API Token metrics
            total_api_tokens=api_token_count,
        )

    def get_tenant_list_with_metrics(
        self,
        page: int = 1,
        page_size: int = 50,
        status_filter: Optional[str] = None,
        plan_filter: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> Tuple[List[TenantListItem], int]:
        """
        Get paginated tenant list with aggregated metrics.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            status_filter: Filter by status (active, suspended, cancelled)
            plan_filter: Filter by subscription plan (free, starter, pro, enterprise)
            search_query: Search tenants by name or slug

        Returns:
            Tuple of (tenant_list, total_count)

        Example:
            >>> service = AdminMetricsService(db)
            >>> tenants, total = service.get_tenant_list_with_metrics(
            ...     page=1, page_size=20, status_filter='active'
            ... )
        """
        # Base query with aggregations
        query = (
            self.db.query(
                Tenant.id,
                Tenant.name,
                Tenant.slug,
                Tenant.status,
                Tenant.subscription_plan,
                Tenant.cached_balance.label('credit_balance'),
                Tenant.created_at,
                func.count(func.distinct(User.id)).label('user_count'),
                func.count(func.distinct(Document.id)).label('document_count'),
                func.count(func.distinct(ExtractionJob.id)).label('job_count'),
                func.sum(case((ExtractionJob.status == 'completed', 1), else_=0)).label('completed_jobs'),
                func.sum(case((ExtractionJob.status == 'failed', 1), else_=0)).label('failed_jobs'),
                func.max(ExtractionJob.created_at).label('last_activity'),
            )
            .outerjoin(User, User.tenant_id == Tenant.id)
            .outerjoin(Document, Document.tenant_id == Tenant.id)
            .outerjoin(ExtractionJob, ExtractionJob.document_id == Document.id)
            .group_by(Tenant.id)
        )

        # Apply filters
        if status_filter:
            query = query.filter(Tenant.status == status_filter)

        if plan_filter:
            query = query.filter(Tenant.subscription_plan == plan_filter)

        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(
                or_(
                    Tenant.name.ilike(search_pattern),
                    Tenant.slug.ilike(search_pattern)
                )
            )

        # Get total count
        total_count = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        results = query.order_by(Tenant.created_at.desc()).offset(offset).limit(page_size).all()

        # Get credit consumption for tenants in this page
        tenant_ids = [r.id for r in results]
        credit_consumption = {}
        if tenant_ids:
            credit_data = (
                self.db.query(
                    CreditTransaction.tenant_id,
                    func.sum(case((CreditTransaction.transaction_type == 'deduction', -CreditTransaction.amount), else_=0)).label('consumed')
                )
                .filter(CreditTransaction.tenant_id.in_(tenant_ids))
                .group_by(CreditTransaction.tenant_id)
                .all()
            )
            credit_consumption = {row.tenant_id: row.consumed or 0 for row in credit_data}

        # Build response objects
        tenant_items = [
            TenantListItem(
                id=row.id,
                name=row.name,
                slug=row.slug,
                status=row.status,
                subscription_plan=row.subscription_plan,
                user_count=row.user_count or 0,
                document_count=row.document_count or 0,
                job_count=row.job_count or 0,
                completed_jobs=row.completed_jobs or 0,
                failed_jobs=row.failed_jobs or 0,
                credit_balance=row.credit_balance,
                total_credits_consumed=credit_consumption.get(row.id, 0),
                created_at=row.created_at,
                last_activity=row.last_activity,
            )
            for row in results
        ]

        return tenant_items, total_count

    def get_tenant_metrics(self, tenant_id: UUID) -> TenantMetrics:
        """
        Get detailed metrics for a specific tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            TenantMetrics with job, document, token, and financial metrics

        Example:
            >>> service = AdminMetricsService(db)
            >>> metrics = service.get_tenant_metrics(tenant_id)
            >>> print(f"Total jobs: {metrics.total_jobs}")
        """
        # Job metrics
        job_stats = (
            self.db.query(
                func.count(ExtractionJob.id).label('total'),
                func.sum(case((ExtractionJob.status == 'completed', 1), else_=0)).label('completed'),
                func.sum(case((ExtractionJob.status == 'failed', 1), else_=0)).label('failed'),
                func.sum(case((ExtractionJob.status == 'queued', 1), else_=0) +
                        case((ExtractionJob.status == 'processing', 1), else_=0)).label('pending'),
            )
            .join(Document, ExtractionJob.document_id == Document.id)
            .filter(Document.tenant_id == tenant_id)
            .first()
        )

        # Document and page metrics
        doc_stats = (
            self.db.query(
                func.count(func.distinct(Document.id)).label('total_documents'),
                func.count(DocumentPage.id).label('total_pages')
            )
            .outerjoin(DocumentPage, Document.id == DocumentPage.document_id)
            .filter(Document.tenant_id == tenant_id)
            .first()
        )

        # Token metrics
        token_stats = (
            self.db.query(
                func.sum(ExtractionResult.input_tokens).label('input_tokens'),
                func.sum(ExtractionResult.output_tokens).label('output_tokens'),
            )
            .join(ExtractionJob, ExtractionResult.extraction_job_id == ExtractionJob.id)
            .join(Document, ExtractionJob.document_id == Document.id)
            .filter(Document.tenant_id == tenant_id)
            .first()
        )

        total_input_tokens = token_stats.input_tokens or 0
        total_output_tokens = token_stats.output_tokens or 0
        total_tokens = total_input_tokens + total_output_tokens

        # Financial metrics
        estimated_cost = (total_tokens / 1000.0) * 1.0  # Simplified: $1 per 1000 tokens

        # Credit balance and consumption
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        credit_balance = tenant.cached_balance if tenant else 0

        credits_consumed = (
            self.db.query(
                func.sum(case((CreditTransaction.transaction_type == 'deduction', -CreditTransaction.amount), else_=0))
            )
            .filter(CreditTransaction.tenant_id == tenant_id)
            .scalar() or 0
        )

        return TenantMetrics(
            total_jobs=job_stats.total or 0,
            completed_jobs=job_stats.completed or 0,
            failed_jobs=job_stats.failed or 0,
            pending_jobs=job_stats.pending or 0,
            total_documents=doc_stats.total_documents or 0,
            total_pages=doc_stats.total_pages or 0,
            total_tokens=total_tokens,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            estimated_cost=estimated_cost,
            credit_balance=credit_balance,
            credits_consumed=credits_consumed,
        )

    def get_top_active_tenants(
        self,
        limit: int = 10,
        days: int = 30
    ) -> List[TopTenantItem]:
        """
        Get top tenants by activity (job count and token usage).

        Args:
            limit: Maximum number of tenants to return
            days: Number of days to look back

        Returns:
            List of TopTenantItem sorted by activity

        Example:
            >>> service = AdminMetricsService(db)
            >>> top_tenants = service.get_top_active_tenants(limit=5, days=30)
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        results = (
            self.db.query(
                Tenant.id,
                Tenant.name,
                Tenant.slug,
                Tenant.subscription_plan,
                Tenant.created_at,
                func.count(func.distinct(ExtractionJob.id)).label('job_count'),
                func.sum(
                    func.coalesce(ExtractionResult.input_tokens, 0) +
                    func.coalesce(ExtractionResult.output_tokens, 0)
                ).label('total_tokens'),
                func.count(func.distinct(User.id)).label('user_count'),
                func.max(ExtractionJob.created_at).label('last_activity'),
            )
            .outerjoin(User, User.tenant_id == Tenant.id)
            .outerjoin(Document, Document.tenant_id == Tenant.id)
            .outerjoin(ExtractionJob, ExtractionJob.document_id == Document.id)
            .outerjoin(ExtractionResult, ExtractionResult.extraction_job_id == ExtractionJob.id)
            .filter(
                or_(
                    ExtractionJob.created_at >= cutoff_date,
                    ExtractionJob.created_at == None
                )
            )
            .group_by(Tenant.id)
            .order_by(desc('job_count'), desc('total_tokens'))
            .limit(limit)
            .all()
        )

        top_tenants = [
            TopTenantItem(
                id=row.id,
                name=row.name,
                slug=row.slug,
                subscription_plan=row.subscription_plan,
                job_count=row.job_count or 0,
                total_tokens=row.total_tokens or 0,
                estimated_cost=((row.total_tokens or 0) / 1000.0) * 1.0,
                user_count=row.user_count or 0,
                created_at=row.created_at,
                last_activity=row.last_activity,
            )
            for row in results
        ]

        return top_tenants
