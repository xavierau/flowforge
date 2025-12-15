# Debugging Journal: Metrics UUID Type Mismatch

**Date:** 2025-12-15
**Issue:** `/api/v1/metrics/jobs/completed` endpoint returns 204 No Content despite completed jobs existing
**Severity:** High
**Impact:** Dashboard metrics and billing data not displaying correctly for tenants

---

## Issue Description

The metrics API endpoints were returning empty results (204 No Content for completed jobs, zero values for dashboard metrics) even when completed extraction jobs existed in the database for the authenticated user's tenant.

### Symptoms
- `/api/v1/metrics/jobs/completed` returns 204 No Content
- `/api/v1/metrics/dashboard` returns zero values for all metrics
- Debug endpoint `/api/v1/metrics/debug/current-user` correctly showed completed jobs count

---

## Root Cause Analysis

### Investigation

The database queries in `MetricsService` were filtering by `tenant_id`, but the API layer was converting the UUID to a string before passing it:

```python
# In app/api/metrics.py (BEFORE FIX)
service.get_dashboard_metrics(tenant_id=str(current_user.tenant_id), days=days)
service.get_completed_jobs(tenant_id=str(current_user.tenant_id), ...)
```

### The Problem

PostgreSQL UUID columns are type-strict. When SQLAlchemy compares a Python `str` against a PostgreSQL `UUID` column, the comparison fails silently - no rows match because the types don't align:

```sql
-- This is what was happening (implicit type mismatch)
SELECT * FROM extraction_jobs
WHERE tenant_id = 'a1b2c3d4-...'  -- String comparison against UUID column
```

The `tenant_id` column in `ExtractionJob` is defined as:
```python
tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
```

With `as_uuid=True`, SQLAlchemy expects Python `uuid.UUID` objects, not strings.

### Why Debug Endpoint Worked

The debug endpoint (`/api/v1/metrics/debug/current-user`) passed the UUID directly without string conversion:

```python
.filter(Document.tenant_id == current_user.tenant_id)  # No str() - worked correctly
```

---

## Fix Implemented

### 1. app/api/metrics.py

Removed `str()` conversion from tenant_id in both endpoint functions:

```python
# Line 79 (dashboard metrics)
- return service.get_dashboard_metrics(tenant_id=str(current_user.tenant_id), days=days)
+ return service.get_dashboard_metrics(tenant_id=current_user.tenant_id, days=days)

# Line 120 (completed jobs)
- tenant_id=str(current_user.tenant_id),
+ tenant_id=current_user.tenant_id,
```

### 2. app/services/metrics_service.py

Updated all method signatures to use proper UUID type hints for type safety:

```python
from uuid import UUID

def get_dashboard_metrics(self, tenant_id: UUID, days: int = 30) -> DashboardMetricsResponse:
def get_completed_jobs(self, tenant_id: UUID, ...) -> CompletedJobsResponse:
def _get_summary_stats(self, tenant_id: UUID, ...) -> MetricStats:
def _get_jobs_over_time(self, tenant_id: UUID, ...) -> List[TimeSeriesDataPoint]:
def _get_pages_over_time(self, tenant_id: UUID, ...) -> List[TimeSeriesDataPoint]:
def _get_tokens_over_time(self, tenant_id: UUID, ...) -> List[TokenUsageData]:
def _get_model_distribution(self, tenant_id: UUID, ...) -> List[ModelDistribution]:
```

---

### 3. app/api/metrics.py - Explicit Status Code

Added explicit `status_code=200` to ensure the endpoint never returns 204, even for empty results:

```python
# BEFORE
@router.get("/jobs/completed", response_model=CompletedJobsResponse)

# AFTER
@router.get("/jobs/completed", response_model=CompletedJobsResponse, status_code=200)
```

**Why:** FastAPI should return 200 with `{"jobs": [], "total": 0, ...}` for empty results, but some configurations (reverse proxy, CDN, or framework behavior) may convert this to 204 No Content. Explicit `status_code=200` prevents this.

---

## Files Changed

| File | Change |
|------|--------|
| `app/api/metrics.py` | Removed `str()` conversion on lines 79 and 120; Added explicit `status_code=200` |
| `app/services/metrics_service.py` | Added `from uuid import UUID` import; Updated 7 method signatures to use `UUID` type |

---

## Verification

1. All 19 metrics-related tests pass
2. No regressions in test suite (746 passed, 37 pre-existing failures unrelated to this fix)

---

## Prevention Strategies

### 1. Type Hints Enforcement
Always use proper type hints for UUID parameters. The updated type hints will help catch this issue at static analysis time if tools like mypy are configured.

### 2. Code Review Checklist
When passing tenant_id or any UUID field to service methods:
- [ ] Check if the target column uses `UUID(as_uuid=True)`
- [ ] Never convert UUID to string when passing to SQLAlchemy queries
- [ ] Use type hints to document expected types

### 3. SQLAlchemy Query Pattern
For UUID columns with `as_uuid=True`:
```python
# CORRECT - Pass UUID object directly
.filter(Model.uuid_column == uuid_value)

# WRONG - String comparison fails silently
.filter(Model.uuid_column == str(uuid_value))
```

### 4. Testing
Consider adding integration tests that verify metrics return correct data for tenants with completed jobs. The current unit tests may not catch this because they mock at the service level.

---

## Related Issues

This is similar to the pattern documented in `2025-11-25-billing-204-no-content-error.md` where type mismatches caused silent query failures.

---

## Lessons Learned

1. UUID type handling requires consistency across the entire call chain
2. SQLAlchemy's type handling with PostgreSQL UUID columns is strict but fails silently
3. Debug endpoints can reveal working patterns that differ from broken production code
4. Always verify the column type definition when writing filters
