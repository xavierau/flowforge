# Token Refresh Not Working - Forced Login on Access Token Expiry

**Date:** 2025-12-16
**Severity:** High
**Status:** Fixed

## Issue Description

When the access token expired (after 15 minutes), the system immediately redirected users to the login page instead of using the refresh token to obtain a new access token. This forced users to re-authenticate frequently, causing poor user experience.

## Root Cause

The `apiFetch()` wrapper function in `frontend/src/lib/api.ts` (and duplicated across 10+ service files) immediately cleared tokens and redirected to `/login` upon receiving a 401 response, without attempting to refresh the token first.

**Original problematic code:**
```typescript
if (response.status === 401) {
  clearTokens();
  window.location.href = '/login';  // Immediate redirect, no refresh attempt
  throw new ApiServiceError('Unauthorized - Please log in again', 401);
}
```

### Contributing Factors

1. **No token refresh logic implemented** - The frontend never called the `/api/v1/auth/refresh` endpoint
2. **Duplicated apiFetch across services** - 10+ service files had their own copy of the broken logic
3. **Backend support existed but unused** - The refresh endpoint was fully functional (`app/api/auth.py:353-460`)

## Solution

### 1. Created Centralized API Client (`frontend/src/lib/api-client.ts`)

A new centralized API client with:

- **Automatic token refresh** on 401 responses
- **Mutex pattern** to prevent multiple simultaneous refresh attempts
- **Request queue** for requests waiting during refresh
- **Token rotation support** (backend returns new refresh token each time)
- **Auth endpoint exclusion** to prevent infinite loops

**Key Security Features:**
- Refresh token sent via POST body (not URL params) to avoid exposure in logs
- All tokens cleared immediately on refresh failure
- Single refresh attempt per concurrent requests
- Graceful redirect to login only when refresh fails

### 2. Updated All Service Files

Removed duplicate `apiFetch` implementations from:
- `api.ts`
- `user.service.ts`
- `job.service.ts`
- `subscription.service.ts`
- `credential.service.ts`
- `admin.service.ts`
- `api-token.service.ts`
- `workflow.service.ts`
- `metrics.service.ts`
- `review.service.ts`
- `pricing.service.ts`

All now import from the centralized `@/lib/api-client`.

### 3. Updated Auth Service

Re-exported token management functions from the centralized client for backward compatibility.

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/lib/api-client.ts` | **NEW** - Centralized API client with token refresh |
| `frontend/src/lib/api.ts` | Now imports from api-client.ts |
| `frontend/src/services/auth.service.ts` | Re-exports token functions from api-client.ts |
| `frontend/src/services/user.service.ts` | Uses centralized client |
| `frontend/src/services/job.service.ts` | Uses centralized client |
| `frontend/src/services/subscription.service.ts` | Uses centralized client |
| `frontend/src/services/credential.service.ts` | Uses centralized client |
| `frontend/src/services/admin.service.ts` | Uses centralized client |
| `frontend/src/services/api-token.service.ts` | Uses centralized client |
| `frontend/src/services/workflow.service.ts` | Uses centralized client |
| `frontend/src/services/metrics.service.ts` | Uses centralized client |
| `frontend/src/services/review.service.ts` | Uses centralized client |
| `frontend/src/services/pricing.service.ts` | Uses centralized client |

## Token Refresh Flow (After Fix)

```
1. API call returns 401 (access token expired)
2. Check if refresh already in progress (mutex)
3. If not, call POST /api/v1/auth/refresh with refresh_token
4. If refresh succeeds:
   - Store new access_token and refresh_token
   - Retry original request with new token
5. If refresh fails (refresh token also expired):
   - Clear all tokens
   - Redirect to /login
```

## Configuration Reference

| Setting | Value | Location |
|---------|-------|----------|
| Access token expiry | 15 minutes | `app/config.py:54` |
| Refresh token expiry | 7 days | `app/config.py:55` |
| Refresh endpoint | POST /api/v1/auth/refresh | `app/api/auth.py:353` |

## Testing

1. Build succeeded: `npm run build`
2. TypeScript compilation: No errors
3. Manual testing recommended:
   - Log in and wait 15+ minutes
   - Perform any API action
   - Verify token refreshes silently without redirect

## Lessons Learned

1. **Centralize API logic** - Duplicate implementations lead to inconsistent behavior
2. **Implement token refresh from the start** - Short-lived tokens require refresh mechanisms
3. **Handle race conditions** - Multiple concurrent 401s need mutex pattern
4. **Security considerations** - Token rotation, secure storage, and auth endpoint exclusion are critical
