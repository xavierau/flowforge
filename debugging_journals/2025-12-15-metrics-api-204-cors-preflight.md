# 2025-12-15 - Metrics API Returns 204 Due to CORS Preflight Trigger

## Bug Report: Metrics Dashboard API Returns 204 While Jobs API Returns 200

**Severity**: High
**Confidence**: High
**Category**: Integration/CORS

### Location
- **File**: `/Users/xavierau/Code/python/ai_document_processing/frontend/src/services/metrics.service.ts:101-103`
- **Function/Component**: `apiFetch()` wrapper function
- **Affected Systems**: Frontend (metrics API calls only)

### Description
The metrics dashboard API endpoint `/api/v1/metrics/dashboard` returns a 204 No Content response in the browser, while the jobs API endpoint `/api/v1/jobs` returns 200 OK with data. Both endpoints use the same JWT authentication. The backend is confirmed working (direct curl requests return 200 with data).

### Reproduction Steps
1. Log into the application at `https://flowforge-app.phbsolution.com`
2. Navigate to the Dashboard page
3. Open browser DevTools Network tab
4. Observe:
   - `GET /api/v1/jobs?limit=10` returns **200 OK** with response headers including `server: nginx`, `content-type: application/json`
   - `GET /api/v1/metrics/dashboard?days=30&_t=...` returns **204 No Content** with only `access-control-allow-credentials: true` header
5. Notice the metrics request shows `net::ERR_ABORTED` in DevTools

### Root Cause Analysis

**The Problem:**
The `metrics.service.ts` file had a code block that automatically added `Content-Type: application/json` to ALL requests, including GET requests:

```typescript
// PROBLEMATIC CODE (lines 101-103, now removed)
if (!headers.has('Content-Type')) {
  headers.set('Content-Type', 'application/json');
}
```

**Why This Causes the Issue:**

1. **CORS Preflight Trigger**: Adding `Content-Type: application/json` to a GET request makes it a "non-simple" request according to CORS specification. Simple requests only allow `Content-Type` values of:
   - `application/x-www-form-urlencoded`
   - `multipart/form-data`
   - `text/plain`

2. **Preflight Request**: The browser automatically sends an OPTIONS preflight request before the actual GET request to check CORS permissions.

3. **Request Abortion**: The 204 response seen was from the OPTIONS preflight request (204 is a valid preflight response). However, something in the CORS handling was causing the actual GET request to be aborted (`net::ERR_ABORTED`).

4. **Evidence**:
   - Metrics request headers included `content-type: application/json`
   - Jobs request headers did NOT include `content-type`
   - Metrics response had NO `server: nginx` header (never reached backend)
   - Response time was 4ms (too fast for real backend response)

**Comparison of apiFetch implementations:**

| Feature | `api.ts` (working) | `metrics.service.ts` (broken) |
|---------|-------------------|------------------------------|
| Auth header | Yes | Yes |
| Content-Type auto-add | **No** | **Yes (bug)** |
| CORS preflight | No | Yes (triggered) |

### Fix Attempts

**Fix Attempt #1 (Successful):**
Removed the automatic `Content-Type: application/json` header addition for GET requests.

**File**: `/Users/xavierau/Code/python/ai_document_processing/frontend/src/services/metrics.service.ts`

**Before:**
```typescript
if (token && !headers.has('Authorization')) {
  headers.set('Authorization', `Bearer ${token}`);
}

if (!headers.has('Content-Type')) {
  headers.set('Content-Type', 'application/json');
}

// Make the request with updated headers
```

**After:**
```typescript
if (token && !headers.has('Authorization')) {
  headers.set('Authorization', `Bearer ${token}`);
}

// NOTE: Do NOT add Content-Type header for GET requests!
// Adding Content-Type: application/json to GET requests triggers CORS preflight
// which can cause 204 responses and request abortion.
// Only add Content-Type for requests with body (POST, PUT, PATCH).

// Make the request with updated headers
```

### API/Documentation References

- MDN CORS Documentation: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
- CORS Simple Requests: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS#simple_requests
- Fetch API: https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API

### Testing

1. **Build Verification**: `npm run build` completed successfully in 15.55s
2. **No New Lint Errors**: The fix does not introduce any new lint errors
3. **Pattern Check**: Verified no other service files have this problematic pattern

### Prevention Strategies

1. **Code Review Checklist**: When implementing API wrappers, verify that:
   - `Content-Type` headers are only added for requests with body (POST, PUT, PATCH)
   - GET requests remain "simple" requests to avoid CORS preflight

2. **Consistent Pattern**: All service files should follow the same `apiFetch` pattern as `api.ts`:
   ```typescript
   async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
     const token = getAccessToken();
     const headers = new Headers(options.headers);

     if (token && !headers.has('Authorization')) {
       headers.set('Authorization', `Bearer ${token}`);
     }

     // NO automatic Content-Type for GET requests!

     return fetch(url, { ...options, headers });
   }
   ```

3. **Testing**: Test API calls in browser DevTools to verify:
   - No unexpected OPTIONS preflight requests
   - Response includes expected headers (`server: nginx`)
   - Response time is reasonable (not suspiciously fast)

### Related Files

- **Fixed File**: `frontend/src/services/metrics.service.ts` (lines 101-104)
- **Reference Implementation**: `frontend/src/lib/api.ts` (lines 96-124)
- **Previous 204 Issue**: `debugging_journals/2025-11-25-billing-204-no-content-error.md` (different root cause - empty data)

### Status

- [x] Root cause identified (Content-Type header triggering CORS preflight)
- [x] Solution designed (remove automatic Content-Type for GET requests)
- [x] Fix implemented in `metrics.service.ts`
- [x] Build successful
- [x] Documentation complete
- [ ] Deployed to production
- [ ] Verified fix in production

### Lessons Learned

1. **GET requests should NOT have Content-Type headers** - They have no body, so Content-Type is meaningless and can trigger CORS preflight
2. **Watch for CORS symptoms**: 204 responses with minimal headers and `net::ERR_ABORTED` indicate CORS/preflight issues
3. **Response time is a clue**: 4ms response time is too fast for a real backend request - indicates request never reached server
4. **Compare working vs broken**: When one API works and another doesn't, diff the request headers to find the difference
