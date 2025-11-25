# 2025-11-25 - Metrics Pages: 204 No Content Causes "Failed to load data"

## Issue Description

**Symptoms:**
- Billing page shows "Failed to load billing data" error
- Dashboard page shows "Failed to load dashboard metrics" error
- Frontend console likely shows JSON parsing error
- API endpoints return 204 No Content:
  - `/api/v1/metrics/jobs/completed` - returns 204
  - `/api/v1/metrics/dashboard?days=30` - returns 204
- Error occurs when user has no completed jobs for their tenant

**User Impact:**
- Users cannot view billing dashboard when they have no completed jobs
- Users cannot view main dashboard when they have no completed jobs
- Error message is confusing (implies system failure, not empty state)

## Root Cause Analysis

### Investigation Steps

1. **Verified API Response:**
   - Endpoint: `GET /api/v1/metrics/jobs/completed?page=1&page_size=50`
   - Response: `204 No Content` (no body)
   - Reason: Current user's tenant has no completed jobs

2. **Database Query:**
   ```sql
   -- Found 35 completed jobs in database
   SELECT COUNT(*) FROM extraction_jobs WHERE status = 'completed';
   -- Result: 35 jobs

   -- But they belong to different tenant
   SELECT tenant_id, COUNT(*) FROM documents d
   JOIN extraction_jobs ej ON d.id = ej.document_id
   WHERE ej.status = 'completed'
   GROUP BY tenant_id;
   -- Result: tenant 808a284a-0b48-4392-8864-ed04faa4e26b has all 35 jobs
   ```

3. **Root Cause:**
   - Backend correctly returns 204 when no data matches filters (by design)
   - Frontend `handleApiResponse()` in `metrics.service.ts:38-78` doesn't handle 204
   - When `response.ok` is true (204 is success), code calls `response.json()` at line 77
   - **204 responses have no body**, so `response.json()` fails/returns undefined
   - This causes errors in both billing page and dashboard
   - **Affects TWO endpoints:**
     - `/api/v1/metrics/jobs/completed` (billing page)
     - `/api/v1/metrics/dashboard?days=30` (main dashboard)

### Code Location

**File:** `frontend/src/services/metrics.service.ts`

**Problem Function (lines 38-78):**
```typescript
async function handleApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    // ... error handling
  }

  return response.json();  // ❌ FAILS on 204 - no body to parse
}
```

## Solution Implemented

### Fix: Handle 204 No Content Responses in Each Endpoint

**Strategy:**
1. Handle 204 status in each specific endpoint function (not in generic handler)
2. Return empty data structures matching each endpoint's response type
3. Keep generic handler simple and focused on error cases

**Implementation 1: Dashboard Metrics (lines 145-158)**
```typescript
export async function getDashboardMetrics(days: DateRangeOption = 30): Promise<DashboardMetrics> {
  const response = await apiFetch(`${API_BASE_URL}/metrics/dashboard?days=${days}`);

  // Handle 204 No Content - return empty dashboard metrics
  if (response.status === 204) {
    return {
      stats: { total_jobs: 0, total_pages: 0, total_tokens: 0, estimated_cost: 0 },
      jobs_over_time: [],
      pages_over_time: [],
      tokens_over_time: [],
      model_distribution: [],
    };
  }

  return handleApiResponse<DashboardMetrics>(response);
}
```

**Implementation 2: Completed Jobs (lines 215-224)**
```typescript
export async function getCompletedJobs(
  page: number = 1,
  pageSize: number = 50,
  filters?: CompletedJobsFilters
): Promise<CompletedJobsResponse> {
  const response = await apiFetch(`${API_BASE_URL}/metrics/jobs/completed?${params}`);

  // Handle 204 No Content - return empty jobs list
  if (response.status === 204) {
    return {
      jobs: [],
      total: 0,
      page,
      page_size: pageSize,
      total_pages: 0,
      total_cost: 0,
    };
  }

  return handleApiResponse<CompletedJobsResponse>(response);
}
```

### Alternative: Backend Change

Could also change backend to return `200 OK` with empty array instead of `204 No Content`:

**Pros:**
- More consistent API responses
- Follows common REST patterns (200 + empty array)

**Cons:**
- Requires backend change
- 204 is semantically correct for "no content"

**Decision:** Fix frontend only (less invasive, handles both patterns)

## Prevention Strategies

### 1. API Client Pattern
**Always handle 204 responses in API wrapper functions:**
```typescript
// Pattern for all API wrappers
async function apiFetch<T>(url: string): Promise<T> {
  const response = await fetch(url);

  if (response.status === 204) {
    return getEmptyResponse<T>();
  }

  return response.json();
}
```

### 2. Testing Checklist
**For every API endpoint integration:**
- [ ] Test with data present
- [ ] Test with empty data (204 or empty array)
- [ ] Test with errors (401, 403, 404, 500)
- [ ] Test with network failure

### 3. User Experience
**Empty state handling:**
- Show helpful empty state instead of error
- Provide actionable next steps (e.g., "Upload a document to get started")
- Distinguish between "no data" vs "error loading data"

### 4. Type Safety
**Use discriminated unions for API responses:**
```typescript
type ApiResponse<T> =
  | { status: 'success', data: T }
  | { status: 'empty' }
  | { status: 'error', message: string };
```

## Testing Workflow

### Reproduce Issue
1. Log in as user with no completed jobs
2. Navigate to `/billing`
3. Observe "Failed to load billing data" error

### Verify Fix
1. Apply changes to `metrics.service.ts`
2. Reload billing page
3. Should see empty state or empty table (not error)
4. Upload document and complete extraction
5. Verify billing page now shows the job

### Test Different Tenants
```bash
# Check which tenants have completed jobs
docker exec pgvector psql -U postgres -d doc_processing -c \
  "SELECT d.tenant_id, COUNT(ej.id) as job_count
   FROM documents d
   JOIN extraction_jobs ej ON d.id = ej.document_id
   WHERE ej.status = 'completed'
   GROUP BY d.tenant_id;"

# Test with tenant that has jobs
# Test with tenant that has no jobs
```

## Related Files

### Frontend
- **Service:** `frontend/src/services/metrics.service.ts`
  - Lines 38-78: `handleApiResponse()` (generic handler)
  - Lines 145-158: `getDashboardMetrics()` with 204 handling
  - Lines 215-224: `getCompletedJobs()` with 204 handling
- **Pages:**
  - `frontend/src/pages/Dashboard.tsx:65-99` (fetchMetrics useEffect)
  - `frontend/src/pages/BillingDetails.tsx:88-127` (fetchData useEffect)

### Backend
- **Service:** `app/services/metrics_service.py`
  - Lines 34-70: `get_dashboard_metrics()` (returns DashboardMetrics or empty)
  - Lines 72-184: `get_completed_jobs()` (returns CompletedJobsResponse or empty)
- **API:** `app/api/metrics.py`
  - Lines 17-46: Dashboard endpoint
  - Lines 49-90: Completed jobs endpoint

## Related Documentation

- **Architecture:** `docs/architecture/2025-11-03-jwt-authentication-and-multi-tenancy.md` (tenant isolation)
- **API Guide:** `docs/guides/2025-11-04-api-endpoint-security.md`

## Lessons Learned

1. **HTTP 204 has no response body** - Always check status before parsing JSON
2. **Multi-tenancy requires thorough testing** - Test with multiple tenants in different states
3. **Error messages matter** - "No data" is very different from "Failed to load"
4. **Empty states need design** - Plan for "no data yet" scenarios in UI/UX

## Status

- [x] Root cause identified
- [x] Solution designed
- [x] Fix implemented for BOTH endpoints
  - [x] `/api/v1/metrics/dashboard` (lines 145-158)
  - [x] `/api/v1/metrics/jobs/completed` (lines 215-224)
- [x] Build successful (15.87s)
- [x] Documentation updated
- [ ] Tested with empty tenant (requires deployment)
- [ ] Tested with tenant with data

**Next Steps:**
1. ~~Apply fix to `metrics.service.ts`~~ ✅ DONE
2. ~~Handle both dashboard and billing endpoints~~ ✅ DONE
3. ~~Update debugging journal~~ ✅ DONE
4. ~~Rebuild frontend~~ ✅ DONE (build passed)
5. Deploy to production/staging environment
6. Test with both tenant types
7. Consider adding empty state UI component
8. Update frontend testing guide with 204 handling pattern
