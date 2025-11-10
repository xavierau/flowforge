# Metrics & Billing System - Quick Start Implementation Guide

**Date:** 2025-11-03
**For:** Development Team
**Architecture Doc:** [2025-11-03-metrics-and-billing-system.md](../architecture/2025-11-03-metrics-and-billing-system.md)

## Overview

This guide provides a streamlined implementation checklist for the metrics and billing system. Follow this sequence to implement the complete feature set.

---

## Prerequisites

- [ ] Review architecture document thoroughly
- [ ] Ensure PostgreSQL database is running
- [ ] Ensure Redis is running (for future caching)
- [ ] Backend dependencies installed (`uv sync`)
- [ ] Frontend dependencies installed (`npm install`)
- [ ] Context7 and agent tools configured

---

## Implementation Checklist

### Phase 1: Domain Layer (4 hours)

#### 1.1 Create Domain Value Objects

**File:** `app/domain/metrics/value_objects.py`

```bash
# Create domain directory
mkdir -p app/domain/metrics
touch app/domain/metrics/__init__.py
```

**Implementation:**
- [ ] Create `DateRange` value object with validation
- [ ] Create `TokenUsage` value object with aggregation methods
- [ ] Create `CostEstimate` value object with arithmetic operations
- [ ] Create `MetricsPeriod` value object for time series
- [ ] All value objects must be immutable (frozen dataclasses)

**Tests:** `tests/domain/metrics/test_value_objects.py`
- [ ] Test DateRange validation (start before end)
- [ ] Test TokenUsage addition
- [ ] Test CostEstimate addition with currency validation
- [ ] Run: `pytest tests/domain/metrics/test_value_objects.py -v`

#### 1.2 Create Domain Pricing Service

**File:** `app/domain/metrics/pricing_service.py`

**Implementation:**
- [ ] Define PRICING_TABLE with all model pricing
- [ ] Implement `calculate_cost()` method
- [ ] Add fallback pricing for unknown models
- [ ] Document pricing source (e.g., Google AI pricing page)

**Tests:** `tests/domain/metrics/test_pricing_service.py`
- [ ] Test cost calculation for Google models
- [ ] Test cost calculation for OpenAI models
- [ ] Test cost calculation for DeepSeek models
- [ ] Test fallback pricing for unknown models
- [ ] Test zero token usage
- [ ] Run: `pytest tests/domain/metrics/test_pricing_service.py -v`

**Critical Verification:**
```bash
# All domain tests must pass before proceeding
pytest tests/domain/metrics/ -v --cov=app/domain/metrics
```

---

### Phase 2: Application Layer (8 hours)

#### 2.1 Create DTOs (Schemas)

**File:** `app/schemas/metrics.py`

**Implementation Order:**
1. [ ] `DateRangeFilter` - Request schema
2. [ ] `TimeSeriesDataPoint` - Chart data point
3. [ ] `TokenUsageMetrics` - Token breakdown
4. [ ] `CostMetrics` - Cost breakdown
5. [ ] `DashboardStatsCard` - Stats card data
6. [ ] `ModelDistribution` - Pie chart data
7. [ ] `DashboardMetricsResponse` - Complete dashboard response
8. [ ] `CompletedJobItem` - Single job item
9. [ ] `PaginationMeta` - Pagination metadata
10. [ ] `CompletedJobsResponse` - Jobs list response

**Pydantic Checklist:**
- [ ] All models use `ConfigDict(from_attributes=True)`
- [ ] All fields have descriptions
- [ ] Required vs optional fields correct
- [ ] Field validators added where needed

**Tests:** `tests/schemas/test_metrics.py`
- [ ] Test all schema validations
- [ ] Test invalid data rejection
- [ ] Run: `pytest tests/schemas/test_metrics.py -v`

#### 2.2 Create Metrics Service

**File:** `app/services/metrics_service.py`

**Implementation Sequence:**

**Step 1: Private Helper Methods**
- [ ] `_resolve_tenant_id()` - Tenant isolation enforcement
- [ ] `_build_base_query()` - Base query with tenant filtering

**Step 2: Dashboard Stats Methods**
- [ ] `_calculate_stats()` - Summary statistics
- [ ] `_get_jobs_time_series()` - Jobs over time
- [ ] `_get_pages_time_series()` - Pages over time
- [ ] `_get_tokens_time_series()` - Tokens over time
- [ ] `_get_token_usage()` - Total token usage
- [ ] `_calculate_total_cost()` - Total cost estimation
- [ ] `_get_model_distribution()` - Model usage distribution

**Step 3: Public Methods**
- [ ] `get_dashboard_metrics()` - Complete dashboard aggregation
- [ ] `get_completed_jobs()` - Paginated jobs list
- [ ] `_build_completed_jobs_query()` - Jobs query builder
- [ ] `_job_to_dto()` - Job to DTO transformer

**SQL Query Optimization:**
- [ ] Use `func.count(func.distinct(ExtractionJob.id))` for job counts
- [ ] Use `func.date_trunc('day', ...)` for time series grouping
- [ ] Use `joinedload()` for eager loading in jobs list
- [ ] Verify all queries filter by `tenant_id`

**Tests:** `tests/services/test_metrics_service.py`

**Critical Test Scenarios:**
- [ ] Test tenant isolation (user cannot access other tenant's data)
- [ ] Test admin can access any tenant's data
- [ ] Test date range filtering
- [ ] Test empty results (no jobs)
- [ ] Test pagination correctness
- [ ] Test cost calculation accuracy
- [ ] Test time series aggregation
- [ ] Run: `pytest tests/services/test_metrics_service.py -v`

**Test Data Setup:**
```python
# Use fixtures to create test data
@pytest.fixture
def sample_extraction_results(db_session, sample_tenant):
    """Create sample extraction results for testing."""
    # Create document, job, and results
    # Return created objects
```

**Verification:**
```bash
# All application layer tests must pass
pytest tests/services/test_metrics_service.py -v --cov=app/services/metrics_service
```

---

### Phase 3: Infrastructure Layer (6 hours)

#### 3.1 Create API Endpoints

**File:** `app/api/metrics.py`

**Implementation:**
- [ ] Create router: `APIRouter(prefix="/api/v1/metrics", tags=["metrics"])`
- [ ] Implement `GET /dashboard` endpoint
- [ ] Implement `GET /jobs/completed` endpoint
- [ ] Add comprehensive docstrings
- [ ] Add response examples

**Endpoint Requirements:**

**Dashboard Endpoint:**
- [ ] Query parameters: `start_date`, `end_date`, `tenant_id` (admin only)
- [ ] Authentication: `get_current_active_user` dependency
- [ ] Tenant isolation: Check admin role for tenant_id parameter
- [ ] Response: `DashboardMetricsResponse`

**Completed Jobs Endpoint:**
- [ ] Query parameters: `page`, `page_size`, `start_date`, `end_date`, `sort_by`, `sort_order`, `tenant_id`
- [ ] Authentication: `get_current_active_user` dependency
- [ ] Tenant isolation: Check admin role for tenant_id parameter
- [ ] Response: `CompletedJobsResponse`

**Error Handling:**
- [ ] 401 Unauthorized: Missing or invalid token
- [ ] 403 Forbidden: Non-admin trying to access other tenant's data
- [ ] 422 Validation Error: Invalid query parameters

**Tests:** `tests/api/test_metrics.py`

**Critical Test Scenarios:**
- [ ] Test successful dashboard metrics retrieval
- [ ] Test successful completed jobs retrieval
- [ ] Test authentication required (401)
- [ ] Test admin can access other tenant (200)
- [ ] Test non-admin blocked from other tenant (403)
- [ ] Test invalid date range (422)
- [ ] Test pagination parameters
- [ ] Run: `pytest tests/api/test_metrics.py -v`

**API Testing:**
```bash
# Manual API testing with curl
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/metrics/dashboard

curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/metrics/jobs/completed?page=1&page_size=20"
```

#### 3.2 Register Router

**File:** `app/main.py`

```python
from app.api import metrics

# Add to existing router includes
app.include_router(metrics.router)
```

**Verification:**
- [ ] Check OpenAPI docs: http://localhost:8000/docs
- [ ] Verify `/api/v1/metrics/dashboard` endpoint visible
- [ ] Verify `/api/v1/metrics/jobs/completed` endpoint visible
- [ ] Test endpoints from Swagger UI

---

### Phase 4: Frontend Types & Services (4 hours)

#### 4.1 Install Dependencies

```bash
cd frontend

# Install recharts for charts
npm install recharts

# Verify installation
npm list recharts
```

#### 4.2 Create TypeScript Types

**File:** `frontend/src/types/metrics.ts`

**Implementation:**
- [ ] All interfaces matching backend DTOs
- [ ] Use `string` for UUIDs and Decimals
- [ ] Use `string` for ISO 8601 dates
- [ ] Export all types

**Verification:**
```bash
# TypeScript compilation check
npm run type-check
```

#### 4.3 Create API Service

**File:** `frontend/src/services/metrics.service.ts`

**Implementation:**
- [ ] `getDashboardMetrics()` method
- [ ] `getCompletedJobs()` method
- [ ] Use existing `api` client from `@/lib/api`
- [ ] Proper query parameter construction
- [ ] TypeScript return types

**Testing:**
```typescript
// Manual testing in browser console
import { metricsService } from '@/services/metrics.service';

metricsService.getDashboardMetrics()
  .then(data => console.log('Dashboard:', data));

metricsService.getCompletedJobs({ page: 1, pageSize: 20 })
  .then(data => console.log('Jobs:', data));
```

---

### Phase 5: Frontend Components (8 hours)

#### 5.1 Create Stats Card Component

**File:** `frontend/src/components/metrics/StatsCard.tsx`

**Implementation:**
- [ ] Display label, value, change, trend
- [ ] Use Lucide icons (ArrowUp, ArrowDown)
- [ ] Tailwind styling with design system colors
- [ ] Responsive design

**Verification:**
- [ ] Test with different props combinations
- [ ] Check responsive layout on mobile

#### 5.2 Create Chart Components

**Files:**
- `frontend/src/components/metrics/JobsChart.tsx`
- `frontend/src/components/metrics/PagesChart.tsx`
- `frontend/src/components/metrics/TokensChart.tsx`

**Implementation (all charts):**
- [ ] Import recharts: `LineChart`, `Line`, `XAxis`, `YAxis`, `CartesianGrid`, `Tooltip`, `ResponsiveContainer`
- [ ] Use design system colors: `hsl(var(--primary))`
- [ ] Responsive container (100% width, 300px height)
- [ ] Card container with title

**Critical: Use context7 to verify Tailwind 4 syntax**

**Verification:**
- [ ] Test with empty data array
- [ ] Test with single data point
- [ ] Test with multiple data points
- [ ] Check responsive behavior

#### 5.3 Create Model Distribution Chart

**File:** `frontend/src/components/metrics/ModelDistributionChart.tsx`

**Implementation:**
- [ ] Import recharts: `PieChart`, `Pie`, `Cell`, `Tooltip`, `Legend`
- [ ] Define color palette (use CSS variables)
- [ ] Responsive container
- [ ] Custom labels showing model name and count

**Verification:**
- [ ] Test with different model distributions
- [ ] Check legend display
- [ ] Verify colors from design system

#### 5.4 Create Completed Jobs Table

**File:** `frontend/src/components/metrics/CompletedJobsTable.tsx`

**Implementation:**
- [ ] Use shadcn/ui `Table` component
- [ ] Display all job fields (filename, pages, model, tokens, time, cost)
- [ ] Format numbers with `toLocaleString()`
- [ ] Format currency with proper decimal places
- [ ] Pagination controls (Previous/Next buttons)
- [ ] Loading state
- [ ] Empty state

**Columns:**
1. Document (truncate long filenames)
2. Pages
3. Model (provider + name, two rows)
4. Input Tokens (right-aligned)
5. Output Tokens (right-aligned)
6. Total Tokens (right-aligned)
7. Time (seconds, right-aligned)
8. Cost (currency, right-aligned, bold)
9. Completed (formatted datetime)

**Verification:**
- [ ] Test with loading state
- [ ] Test with empty state
- [ ] Test with data
- [ ] Test pagination controls
- [ ] Check responsive layout

---

### Phase 6: Frontend Pages (6 hours)

#### 6.1 Create Dashboard Page

**File:** `frontend/src/pages/Dashboard.tsx`

**Implementation:**
- [ ] Use layout components: `Page`, `PageHeader`, `PageContent`
- [ ] Fetch metrics on mount with `useEffect`
- [ ] Display loading state
- [ ] Display error state
- [ ] Render stats cards grid (4 columns on desktop)
- [ ] Render charts in 2x2 grid
- [ ] Render cost summary card
- [ ] Handle API errors gracefully

**Layout:**
```
Stats Cards (4 columns)
─────────────────────────────────
Jobs Chart   | Pages Chart
─────────────────────────────────
Tokens Chart | Model Distribution
─────────────────────────────────
Cost Summary (full width)
```

**Verification:**
- [ ] Test loading state
- [ ] Test error state
- [ ] Test with real data
- [ ] Check responsive layout (mobile, tablet, desktop)

#### 6.2 Create Billing Details Page

**File:** `frontend/src/pages/BillingDetails.tsx`

**Implementation:**
- [ ] Use layout components: `Page`, `PageHeader`, `PageContent`
- [ ] Fetch completed jobs on mount
- [ ] Refetch when page changes
- [ ] Display loading state
- [ ] Display error state
- [ ] Render summary card (page total cost, total jobs)
- [ ] Render `CompletedJobsTable`
- [ ] Handle pagination state

**Verification:**
- [ ] Test loading state
- [ ] Test error state
- [ ] Test pagination
- [ ] Test with no jobs
- [ ] Check responsive layout

#### 6.3 Update App Routes

**File:** `frontend/src/App.tsx`

**Add Routes:**
```typescript
<Route
  path="/dashboard"
  element={
    <ProtectedRoute>
      <AuthenticatedLayout>
        <Dashboard />
      </AuthenticatedLayout>
    </ProtectedRoute>
  }
/>

<Route
  path="/billing"
  element={
    <ProtectedRoute>
      <AuthenticatedLayout>
        <BillingDetails />
      </AuthenticatedLayout>
    </ProtectedRoute>
  }
/>
```

#### 6.4 Update Sidebar Navigation

**File:** `frontend/src/components/layout/Sidebar.tsx`

**Add Navigation Items:**
```typescript
import { BarChart3, Receipt } from 'lucide-react';

// Add to navigation array
{ label: 'Dashboard', href: '/dashboard', icon: BarChart3 },
{ label: 'Billing', href: '/billing', icon: Receipt },
```

**Verification:**
- [ ] Click sidebar links navigate correctly
- [ ] Active link highlighted
- [ ] Icons display correctly

---

### Phase 7: Testing & QA (4 hours)

#### 7.1 Backend Testing

**Unit Tests:**
```bash
# Test domain layer
pytest tests/domain/metrics/ -v --cov=app/domain/metrics

# Test application layer
pytest tests/services/test_metrics_service.py -v --cov=app/services/metrics_service

# Test API endpoints
pytest tests/api/test_metrics.py -v
```

**Integration Testing:**
```bash
# Full test suite
pytest tests/ -v --cov=app

# Coverage report
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```

#### 7.2 Frontend Testing

**Component Tests:**
```bash
# Test stats card
npm test -- StatsCard.test.tsx

# Test charts
npm test -- JobsChart.test.tsx

# Test table
npm test -- CompletedJobsTable.test.tsx
```

**Manual Testing Checklist:**

**Dashboard Page:**
- [ ] Page loads without errors
- [ ] Stats cards display correct values
- [ ] Charts render with data
- [ ] Charts handle empty data gracefully
- [ ] Cost summary displays correctly
- [ ] Responsive layout works on mobile

**Billing Details Page:**
- [ ] Table loads with data
- [ ] Pagination works correctly
- [ ] Sorting works (if implemented)
- [ ] Cost calculations accurate
- [ ] Date formatting correct
- [ ] Responsive layout works

**Multi-Tenant Isolation:**
- [ ] Create two test tenants
- [ ] Verify each tenant sees only their data
- [ ] Test admin access to other tenant's data
- [ ] Test non-admin blocked from other tenant

#### 7.3 Performance Testing

**Database Query Performance:**
```sql
-- Test dashboard query performance
EXPLAIN ANALYZE
SELECT COUNT(DISTINCT ej.id)
FROM extraction_results er
JOIN extraction_jobs ej ON er.extraction_job_id = ej.id
JOIN documents d ON ej.document_id = d.id
WHERE d.tenant_id = '...'
  AND ej.status = 'completed';

-- Should use index scan, not seq scan
-- Target: < 100ms for 10K jobs
```

**API Response Time:**
```bash
# Test dashboard endpoint
time curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/metrics/dashboard

# Target: < 500ms

# Test completed jobs endpoint
time curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/metrics/jobs/completed?page=1&page_size=20

# Target: < 1s
```

**Frontend Performance:**
- [ ] Dashboard page loads < 2s
- [ ] Charts render < 500ms
- [ ] No console errors
- [ ] No memory leaks (check Chrome DevTools)

---

### Phase 8: Documentation (2 hours)

#### 8.1 User Guide

**File:** `docs/guides/2025-11-03-metrics-user-guide.md`

**Content:**
- How to access dashboard
- Understanding metrics (jobs, pages, tokens)
- Cost estimation explanation
- How to view billing details
- How to export data (future)

#### 8.2 API Documentation

**Update OpenAPI docs:**
- [ ] Add detailed descriptions to endpoints
- [ ] Add request/response examples
- [ ] Document query parameters
- [ ] Document error responses

#### 8.3 Architecture Updates

**Update:** `docs/architecture/2025-11-03-metrics-and-billing-system.md`

- [ ] Add deployment notes
- [ ] Add troubleshooting tips
- [ ] Add performance optimization results
- [ ] Add future enhancements section

---

## Deployment Checklist

### Pre-Deployment

- [ ] All backend tests passing
- [ ] All frontend tests passing
- [ ] Code review completed
- [ ] Architecture review completed
- [ ] Security review completed

### Backend Deployment

- [ ] Create feature branch: `feature/metrics-and-billing`
- [ ] Commit all changes
- [ ] Run migrations (if any)
- [ ] Update environment variables
- [ ] Deploy to staging
- [ ] Test on staging
- [ ] Deploy to production

### Frontend Deployment

- [ ] Build frontend: `npm run build`
- [ ] Test production build: `npm run preview`
- [ ] Deploy to CDN/hosting
- [ ] Verify production URL

### Post-Deployment

- [ ] Monitor error logs
- [ ] Monitor API response times
- [ ] Monitor frontend performance
- [ ] Verify metrics accuracy
- [ ] Create debugging journal if issues arise

---

## Troubleshooting

### Common Issues

**Issue: Dashboard shows zero metrics**
- **Check:** Is there any completed job data?
- **Fix:** Create test extraction jobs with completed status

**Issue: Tenant isolation not working**
- **Check:** Is `tenant_id` being passed correctly?
- **Fix:** Verify `_resolve_tenant_id()` logic

**Issue: Charts not rendering**
- **Check:** Browser console for errors
- **Fix:** Verify recharts data format matches expected structure

**Issue: Slow dashboard load**
- **Check:** Database query execution time
- **Fix:** Verify indexes exist, consider materialized views

**Issue: Cost calculations incorrect**
- **Check:** Pricing table values
- **Fix:** Update `PricingService.PRICING_TABLE` with correct rates

---

## Quick Reference

### Key Files Created

**Backend:**
- `app/domain/metrics/value_objects.py` - Domain value objects
- `app/domain/metrics/pricing_service.py` - Pricing logic
- `app/schemas/metrics.py` - API DTOs
- `app/services/metrics_service.py` - Metrics aggregation
- `app/api/metrics.py` - API endpoints

**Frontend:**
- `frontend/src/types/metrics.ts` - TypeScript types
- `frontend/src/services/metrics.service.ts` - API client
- `frontend/src/components/metrics/StatsCard.tsx` - Stats card
- `frontend/src/components/metrics/JobsChart.tsx` - Jobs chart
- `frontend/src/components/metrics/PagesChart.tsx` - Pages chart
- `frontend/src/components/metrics/TokensChart.tsx` - Tokens chart
- `frontend/src/components/metrics/ModelDistributionChart.tsx` - Pie chart
- `frontend/src/components/metrics/CompletedJobsTable.tsx` - Jobs table
- `frontend/src/pages/Dashboard.tsx` - Dashboard page
- `frontend/src/pages/BillingDetails.tsx` - Billing page

### API Endpoints

```
GET /api/v1/metrics/dashboard
  Query: ?start_date=...&end_date=...&tenant_id=...
  Auth: Required (Bearer token)

GET /api/v1/metrics/jobs/completed
  Query: ?page=1&page_size=20&sort_by=completed_at&sort_order=desc
  Auth: Required (Bearer token)
```

### Commands

```bash
# Backend testing
pytest tests/domain/metrics/ -v
pytest tests/services/test_metrics_service.py -v
pytest tests/api/test_metrics.py -v

# Frontend testing
npm test -- StatsCard.test.tsx
npm test -- JobsChart.test.tsx
npm test -- CompletedJobsTable.test.tsx

# Run dev servers
uvicorn app.main:app --reload          # Backend
cd frontend && npm run dev             # Frontend
```

---

## Success Criteria

### Backend
- [ ] All unit tests passing (100% domain layer coverage)
- [ ] All integration tests passing
- [ ] API response time < 500ms for dashboard
- [ ] API response time < 1s for jobs list
- [ ] Multi-tenant isolation verified
- [ ] Admin access control working

### Frontend
- [ ] Dashboard loads in < 2s
- [ ] Charts render correctly
- [ ] Table pagination works
- [ ] Responsive layout on all screen sizes
- [ ] No console errors
- [ ] Proper error handling

### Documentation
- [ ] Architecture document complete
- [ ] User guide complete
- [ ] API documentation complete
- [ ] Troubleshooting guide complete

---

**Estimated Total Implementation Time:** 8-10 days

**Questions?** Refer to [Architecture Document](../architecture/2025-11-03-metrics-and-billing-system.md) for detailed design decisions.
