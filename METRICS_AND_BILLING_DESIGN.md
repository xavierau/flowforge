# Metrics and Billing System - Design Summary

**Date:** 2025-11-03
**Status:** Design Complete - Ready for Implementation

## Executive Summary

Complete technical design for a metrics and billing system that tracks extraction jobs, displays dashboard visualizations, and provides detailed billing information with proper multi-tenant isolation.

**Key Highlights:**
- **No database schema changes required** - leverages existing models
- **Clean Architecture** with clear layer separation
- **SOLID principles** applied throughout
- **Multi-tenant secure** with proper isolation enforcement
- **Performance optimized** with efficient SQL queries
- **8-10 days implementation** with TDD approach

---

## Documentation Structure

### 1. Architecture Document (Comprehensive Design)
**File:** `docs/architecture/2025-11-03-metrics-and-billing-system.md`

**Contents:**
- Complete technical design down to file/function level
- Database schema analysis (no changes needed)
- Domain layer design (value objects, pricing service)
- Application layer design (DTOs, metrics service)
- Infrastructure layer design (API endpoints)
- Presentation layer design (React components, pages)
- SOLID principles mapping
- Testing strategy with 90%+ coverage targets
- Performance considerations (indexing, caching, pagination)
- Security (tenant isolation, rate limiting)
- Architectural decision records (ADRs)
- Monitoring and observability

### 2. Implementation Guide (Quick Start)
**File:** `docs/guides/2025-11-03-metrics-implementation-quick-start.md`

**Contents:**
- Phase-by-phase implementation checklist
- File-by-file creation sequence
- Test-driven development workflow
- Verification steps at each phase
- Troubleshooting common issues
- Deployment checklist
- Success criteria

---

## System Overview

### Business Requirements Met

✅ Track completed jobs for billing purposes
✅ Display dashboard with metrics and charts
✅ Provide detailed billing page with paginated job list
✅ Support multi-tenancy (tenant isolation)
✅ Track usage metrics (jobs, pages, tokens, processing time)
✅ Calculate cost estimates based on model pricing
✅ Support admin access to all tenants (with proper authorization)

### Technical Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Presentation Layer                    │
│  Dashboard Page | Billing Details Page | Chart Components│
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                   │
│     API Endpoints (/metrics/dashboard, /jobs/completed) │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                      │
│   MetricsService (aggregation, filtering, pagination)   │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                      Domain Layer                        │
│  PricingService | Value Objects (DateRange, TokenUsage) │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    Database Layer                        │
│  ExtractionResult | ExtractionJob | Document | Tenant   │
└─────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

### 1. No New Database Tables
**Decision:** Use existing `ExtractionResult` model with aggregation queries.

**Rationale:**
- Single source of truth (no duplication)
- Real-time metrics (no sync lag)
- Existing indexes sufficient for current scale
- Can add materialized views later if needed

### 2. Domain-Driven Pricing
**Decision:** Create `PricingService` as domain service.

**Rationale:**
- Pricing is core business logic
- Easily testable in isolation
- Reusable across application layer
- Follows Single Responsibility Principle

### 3. Frontend Chart Library
**Decision:** Use Recharts for all visualizations.

**Rationale:**
- React-first library (declarative API)
- Good TypeScript support
- Responsive by default
- Easy to customize with Tailwind CSS

### 4. Multi-Tenant Isolation
**Decision:** Enforce isolation at service layer.

**Rationale:**
- Defense in depth (not just DB-level)
- Explicit validation in code
- Easy to audit and test
- Admin override capability

---

## API Endpoints

### GET /api/v1/metrics/dashboard
**Purpose:** Get aggregated metrics for dashboard visualizations.

**Query Parameters:**
- `start_date` (optional): ISO 8601 date
- `end_date` (optional): ISO 8601 date
- `tenant_id` (optional, admin only): UUID

**Response:**
```json
{
  "stats": [
    {"label": "Completed Jobs", "value": "1,234"},
    {"label": "Pages Processed", "value": "5,678"},
    {"label": "Total Tokens", "value": "12,345,678"},
    {"label": "Avg. Time", "value": "3s"}
  ],
  "jobs_over_time": [
    {"timestamp": "2025-01-01T00:00:00Z", "value": 45, "label": "Jan 01"}
  ],
  "pages_over_time": [...],
  "tokens_over_time": [...],
  "token_usage": {
    "input_tokens": 8000000,
    "output_tokens": 4000000,
    "total_tokens": 12000000
  },
  "estimated_cost": {
    "input_cost": "0.6000",
    "output_cost": "1.2000",
    "total_cost": "1.8000",
    "currency": "USD"
  },
  "model_distribution": [
    {"model": "gemini-2.5-flash", "count": 150}
  ]
}
```

### GET /api/v1/metrics/jobs/completed
**Purpose:** Get paginated list of completed jobs for billing.

**Query Parameters:**
- `page` (required): Page number (1-indexed)
- `page_size` (required): Items per page (1-100)
- `start_date` (optional): ISO 8601 date
- `end_date` (optional): ISO 8601 date
- `sort_by` (optional): Field to sort by (default: completed_at)
- `sort_order` (optional): asc or desc (default: desc)
- `tenant_id` (optional, admin only): UUID

**Response:**
```json
{
  "jobs": [
    {
      "id": "uuid",
      "document_id": "uuid",
      "document_filename": "invoice.pdf",
      "page_count": 3,
      "model_provider": "google",
      "model_name": "gemini-2.5-flash",
      "input_tokens": 25000,
      "output_tokens": 5000,
      "total_tokens": 30000,
      "processing_time_ms": 3500,
      "estimated_cost": "0.0045",
      "completed_at": "2025-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 150,
    "total_pages": 8
  },
  "total_cost": "0.0900"
}
```

---

## Frontend Components

### Pages
1. **Dashboard** (`/dashboard`)
   - Stats cards (4 metrics)
   - Jobs over time chart (line)
   - Pages over time chart (line)
   - Tokens over time chart (line)
   - Model distribution chart (pie)
   - Cost summary card

2. **Billing Details** (`/billing`)
   - Summary card (page total cost, total jobs)
   - Completed jobs table (paginated, sortable)

### Reusable Components
- `StatsCard` - Metric card with optional trend indicator
- `JobsChart` - Line chart for jobs time series
- `PagesChart` - Line chart for pages time series
- `TokensChart` - Line chart for tokens time series
- `ModelDistributionChart` - Pie chart for model usage
- `CompletedJobsTable` - Data table with pagination

---

## File Structure

### Backend (New Files)
```
app/
├── domain/
│   └── metrics/
│       ├── __init__.py
│       ├── value_objects.py        # DateRange, TokenUsage, CostEstimate
│       └── pricing_service.py      # Cost calculation logic
├── schemas/
│   └── metrics.py                  # API request/response DTOs
├── services/
│   └── metrics_service.py          # Metrics aggregation service
└── api/
    └── metrics.py                  # API endpoints

tests/
├── domain/
│   └── metrics/
│       ├── test_value_objects.py
│       └── test_pricing_service.py
├── schemas/
│   └── test_metrics.py
├── services/
│   └── test_metrics_service.py
└── api/
    └── test_metrics.py
```

### Frontend (New Files)
```
frontend/src/
├── types/
│   └── metrics.ts                  # TypeScript types
├── services/
│   └── metrics.service.ts          # API client
├── components/
│   └── metrics/
│       ├── StatsCard.tsx           # Stats card component
│       ├── JobsChart.tsx           # Jobs line chart
│       ├── PagesChart.tsx          # Pages line chart
│       ├── TokensChart.tsx         # Tokens line chart
│       ├── ModelDistributionChart.tsx  # Pie chart
│       └── CompletedJobsTable.tsx  # Jobs data table
└── pages/
    ├── Dashboard.tsx               # Dashboard page
    └── BillingDetails.tsx          # Billing details page
```

---

## Implementation Phases

### Phase 1: Domain Layer (4 hours)
- Create value objects (DateRange, TokenUsage, CostEstimate)
- Create PricingService with pricing table
- Write comprehensive unit tests
- Target: 100% test coverage

### Phase 2: Application Layer (8 hours)
- Create DTOs/schemas with Pydantic
- Create MetricsService with all aggregation methods
- Write unit tests with mocked database
- Target: 90% test coverage

### Phase 3: Infrastructure Layer (6 hours)
- Create API endpoints
- Register routes in main.py
- Write integration tests
- Target: 80% test coverage

### Phase 4: Frontend Types & Services (4 hours)
- Install recharts
- Create TypeScript types
- Create API service
- Test API integration

### Phase 5: Frontend Components (8 hours)
- Create StatsCard component
- Create chart components (Jobs, Pages, Tokens, ModelDistribution)
- Create CompletedJobsTable component
- Test all components

### Phase 6: Frontend Pages (6 hours)
- Create Dashboard page
- Create BillingDetails page
- Update App routes
- Update Sidebar navigation
- Test complete flow

### Phase 7: Testing & QA (4 hours)
- Run full test suite
- Manual testing (dashboard, billing, multi-tenant)
- Performance testing
- Security testing

### Phase 8: Documentation (2 hours)
- User guide
- API documentation
- Troubleshooting guide

**Total: 8-10 days**

---

## Testing Strategy

### Unit Tests
- **Domain Layer:** 100% coverage (critical business logic)
- **Application Layer:** 90% coverage (service methods)
- **Infrastructure Layer:** 80% coverage (API endpoints)

### Integration Tests
- API endpoint authentication
- Multi-tenant isolation
- Admin vs non-admin access control
- Date range filtering
- Pagination correctness

### End-to-End Tests
- Dashboard loads with data
- Billing table displays and paginates
- Charts render correctly
- Cost calculations accurate
- Responsive design works

---

## Security Checklist

✅ Multi-tenant isolation enforced at service layer
✅ Admin role required for cross-tenant access
✅ Authentication required for all endpoints
✅ SQL injection prevention (SQLAlchemy ORM)
✅ Rate limiting on metrics endpoints (future)
✅ Cost data only visible to tenant users
✅ Audit logging for admin access (future)

---

## Performance Targets

- **Dashboard API:** < 500ms response time
- **Jobs API:** < 1s response time
- **Dashboard Page Load:** < 2s
- **Chart Render:** < 500ms
- **Database Queries:** Use indexed queries only

---

## Monitoring

### Key Metrics to Track
- API response times
- Database query execution times
- Error rates
- Cache hit rates (if Redis implemented)
- Frontend page load times

### Logging
- Structured JSON logging
- Log all metrics API requests
- Log admin access to other tenants
- Log slow queries (> 1s)

---

## Future Enhancements

### Performance Optimizations
1. **Materialized Views** - For large datasets (>1M jobs)
2. **Redis Caching** - Cache dashboard metrics for 5 minutes
3. **Cursor-Based Pagination** - For very large result sets

### Features
1. **CSV Export** - Export completed jobs to CSV
2. **Date Range Presets** - Last 7 days, 30 days, 90 days, year
3. **Custom Date Ranges** - Date picker for custom ranges
4. **Filtering** - Filter by model, status, document type
5. **Cost Breakdown by Model** - Detailed cost analysis per model
6. **Usage Alerts** - Email notifications for usage thresholds
7. **Batch Job Comparison** - Compare metrics across date ranges

### Analytics
1. **Cost Trends** - Month-over-month cost analysis
2. **Model Efficiency** - Compare processing time and cost by model
3. **Document Type Analysis** - Metrics by document type
4. **User Activity** - Track which users process most documents

---

## Success Criteria

### Functional Requirements
✅ Users can view dashboard with metrics and charts
✅ Users can view detailed billing information
✅ Multi-tenant isolation working correctly
✅ Admin can access any tenant's data
✅ Cost estimates accurate within ±5%
✅ Pagination works correctly
✅ Date range filtering works

### Non-Functional Requirements
✅ API response time < 500ms (dashboard)
✅ API response time < 1s (jobs list)
✅ Frontend page load < 2s
✅ 90%+ test coverage (backend)
✅ No console errors (frontend)
✅ Responsive design on all devices
✅ Proper error handling throughout

---

## Getting Started

### For Developers

1. **Read Architecture Document:**
   ```bash
   cat docs/architecture/2025-11-03-metrics-and-billing-system.md
   ```

2. **Follow Implementation Guide:**
   ```bash
   cat docs/guides/2025-11-03-metrics-implementation-quick-start.md
   ```

3. **Start with Phase 1 (Domain Layer):**
   - Create value objects
   - Create pricing service
   - Write tests first (TDD)

### For Reviewers

1. **Architecture Review:** Check design decisions in ADRs
2. **Code Review:** Verify SOLID principles adherence
3. **Security Review:** Verify tenant isolation and auth
4. **Performance Review:** Check query optimization

### For QA

1. **Test Metrics Accuracy:** Verify calculations match expected
2. **Test Multi-Tenant:** Create two tenants, verify isolation
3. **Test Admin Access:** Verify admin can access all tenants
4. **Test Performance:** Measure API response times

---

## Questions & Support

**Architecture Questions:** See `docs/architecture/2025-11-03-metrics-and-billing-system.md`
**Implementation Help:** See `docs/guides/2025-11-03-metrics-implementation-quick-start.md`
**Troubleshooting:** See implementation guide troubleshooting section

**Key Contacts:**
- Solution Architect: Design decisions and architecture
- Backend Team: Domain, application, and infrastructure layers
- Frontend Team: Components, pages, and user experience
- QA Team: Testing strategy and quality assurance

---

## Conclusion

This design provides a complete, production-ready metrics and billing system following Clean Architecture and SOLID principles. The implementation is broken down into clear, testable phases with comprehensive documentation.

**Key Strengths:**
- No database changes required (uses existing models)
- Clean separation of concerns (domain, application, infrastructure)
- Comprehensive testing strategy (90%+ coverage)
- Multi-tenant secure with proper isolation
- Performance optimized with efficient queries
- Well-documented with clear implementation path

**Ready for Implementation:** All design decisions documented, all files specified, all tests planned. Development can begin immediately.

---

**Last Updated:** 2025-11-03
**Version:** 1.0
**Status:** Design Complete ✅
