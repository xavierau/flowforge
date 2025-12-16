/**
 * Centralized API Client with Secure Token Refresh
 *
 * Security Features:
 * - Automatic token refresh on 401 responses
 * - Single refresh attempt per concurrent requests (mutex pattern)
 * - Token rotation support (new refresh token on each refresh)
 * - Graceful degradation to login on refresh failure
 * - No refresh attempts for auth endpoints (prevents infinite loops)
 * - Request queue during refresh to prevent race conditions
 *
 * IMPORTANT: This is the ONLY module that should make direct fetch calls.
 * All service files should import and use `apiFetch` from this module.
 */

// ============================================================================
// Configuration
// ============================================================================

export const API_BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : '/api/v1';

// Endpoints that should NOT trigger token refresh (to prevent infinite loops)
const AUTH_ENDPOINTS = [
  '/auth/login',
  '/auth/register',
  '/auth/refresh',
  '/auth/logout',
  '/auth/forgot-password',
  '/auth/reset-password',
];

// ============================================================================
// Token Management
// ============================================================================

/**
 * Get access token from localStorage
 * @security Access tokens are stored in localStorage. For higher security,
 * consider using httpOnly cookies (requires backend changes).
 */
export function getAccessToken(): string | null {
  return localStorage.getItem('access_token');
}

/**
 * Get refresh token from localStorage
 */
export function getRefreshToken(): string | null {
  return localStorage.getItem('refresh_token');
}

/**
 * Store both tokens securely
 * @security Tokens are stored in localStorage. Ensure XSS protection is in place.
 */
export function storeTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem('access_token', accessToken);
  localStorage.setItem('refresh_token', refreshToken);
}

/**
 * Clear all authentication tokens
 */
export function clearTokens(): void {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

/**
 * Check if user has valid tokens stored
 */
export function hasStoredTokens(): boolean {
  return getAccessToken() !== null;
}

// ============================================================================
// Error Classes
// ============================================================================

/**
 * Structured error detail from backend (ErrorDetail schema)
 */
export interface StructuredErrorDetail {
  error_code: string;
  message: string;
  details?: Record<string, unknown>;
}

/**
 * API error response - detail can be a string or structured error object
 */
export interface ApiErrorResponse {
  detail: string | StructuredErrorDetail;
}

/**
 * Custom error class for API errors
 */
export class ApiClientError extends Error {
  statusCode: number;
  detail?: string;
  isAuthError: boolean;

  constructor(message: string, statusCode: number, detail?: string) {
    super(message);
    this.name = 'ApiClientError';
    this.statusCode = statusCode;
    this.detail = detail;
    this.isAuthError = statusCode === 401 || statusCode === 403;
  }
}

// ============================================================================
// Token Refresh Logic
// ============================================================================

// Mutex for token refresh - prevents multiple simultaneous refresh attempts
let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

// Queue of requests waiting for token refresh
type QueuedRequest = {
  resolve: (value: boolean) => void;
  reject: (error: Error) => void;
};
let refreshQueue: QueuedRequest[] = [];

/**
 * Process all queued requests after token refresh
 */
function processRefreshQueue(success: boolean, error?: Error): void {
  refreshQueue.forEach(({ resolve, reject }) => {
    if (success) {
      resolve(true);
    } else {
      reject(error || new Error('Token refresh failed'));
    }
  });
  refreshQueue = [];
}

/**
 * Attempt to refresh the access token using the refresh token
 *
 * @security
 * - Uses POST with JSON body (not URL params) to avoid token in logs
 * - Stores new refresh token (token rotation for security)
 * - Clears all tokens on failure
 *
 * @returns true if refresh was successful, false otherwise
 */
async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();

  if (!refreshToken) {
    console.warn('[API Client] No refresh token available');
    return false;
  }

  try {
    // Direct fetch - don't use apiFetch to avoid infinite loop
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      // Log specific error for debugging (but don't expose to user)
      const errorData = await response.json().catch(() => ({}));
      console.warn('[API Client] Token refresh failed:', errorData.detail || response.status);
      return false;
    }

    const data = await response.json();

    // Validate response has required fields
    if (!data.access_token || !data.refresh_token) {
      console.error('[API Client] Invalid refresh response - missing tokens');
      return false;
    }

    // Store new tokens (implements token rotation)
    storeTokens(data.access_token, data.refresh_token);

    console.info('[API Client] Token refresh successful');
    return true;
  } catch (error) {
    console.error('[API Client] Token refresh error:', error);
    return false;
  }
}

/**
 * Handle 401 response with token refresh
 *
 * @security
 * - Only one refresh attempt at a time (mutex)
 * - Queued requests wait for refresh to complete
 * - All tokens cleared on refresh failure
 *
 * @returns true if token was refreshed and request should be retried
 */
async function handleUnauthorized(): Promise<boolean> {
  // If already refreshing, wait for the current refresh to complete
  if (isRefreshing) {
    return new Promise((resolve, reject) => {
      refreshQueue.push({ resolve, reject });
    });
  }

  isRefreshing = true;
  refreshPromise = refreshAccessToken();

  try {
    const success = await refreshPromise;

    if (success) {
      processRefreshQueue(true);
      return true;
    } else {
      // Refresh failed - clear tokens and redirect to login
      clearTokens();
      processRefreshQueue(false, new Error('Token refresh failed'));

      // Small delay to allow state cleanup before redirect
      setTimeout(() => {
        window.location.href = '/login';
      }, 100);

      return false;
    }
  } finally {
    isRefreshing = false;
    refreshPromise = null;
  }
}

// ============================================================================
// Main API Client
// ============================================================================

/**
 * Check if the URL is an auth endpoint that shouldn't trigger refresh
 */
function isAuthEndpoint(url: string): boolean {
  return AUTH_ENDPOINTS.some((endpoint) => url.includes(endpoint));
}

/**
 * Extract error message from API error response
 */
export function extractErrorMessage(
  detail: string | StructuredErrorDetail | undefined,
  fallback: string
): string {
  if (!detail) {
    return fallback;
  }
  if (typeof detail === 'string') {
    return detail;
  }
  // Structured error - extract the message field
  return detail.message || fallback;
}

/**
 * Centralized API fetch wrapper with automatic token refresh
 *
 * @security
 * - Automatically adds Authorization header
 * - Handles 401 responses with token refresh
 * - Prevents infinite loops on auth endpoints
 * - Single refresh attempt per concurrent requests
 *
 * @param url - Request URL
 * @param options - Fetch options
 * @returns Response promise
 * @throws ApiClientError on non-recoverable errors
 */
export async function apiFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  // Add Authorization header if token exists
  const token = getAccessToken();
  const headers = new Headers(options.headers);

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Make the request
  let response = await fetch(url, {
    ...options,
    headers,
  });

  // Handle 401 Unauthorized with token refresh
  if (response.status === 401 && !isAuthEndpoint(url)) {
    const refreshed = await handleUnauthorized();

    if (refreshed) {
      // Retry the original request with new token
      const newToken = getAccessToken();
      const newHeaders = new Headers(options.headers);

      if (newToken) {
        newHeaders.set('Authorization', `Bearer ${newToken}`);
      }

      response = await fetch(url, {
        ...options,
        headers: newHeaders,
      });

      // If still 401 after refresh, something is wrong - redirect to login
      if (response.status === 401) {
        clearTokens();
        window.location.href = '/login';
        throw new ApiClientError(
          'Session expired - Please log in again',
          401
        );
      }
    } else {
      // Refresh failed - error already thrown, just throw for consistency
      throw new ApiClientError(
        'Session expired - Please log in again',
        401
      );
    }
  }

  return response;
}

/**
 * Helper function to handle API response and parse JSON
 */
export async function handleApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const contentType = response.headers.get('content-type');
    let errorData: ApiErrorResponse | undefined;

    if (contentType?.includes('application/json')) {
      errorData = await response.json().catch(() => undefined);
    }

    const message = errorData
      ? extractErrorMessage(errorData.detail, response.statusText)
      : response.statusText;

    throw new ApiClientError(message, response.status, message);
  }

  // Handle empty responses (204 No Content)
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ============================================================================
// Convenience Methods
// ============================================================================

/**
 * Make a GET request
 */
export async function apiGet<T>(
  url: string,
  options?: Omit<RequestInit, 'method'>
): Promise<T> {
  const response = await apiFetch(url, { ...options, method: 'GET' });
  return handleApiResponse<T>(response);
}

/**
 * Make a POST request with JSON body
 */
export async function apiPost<T>(
  url: string,
  body?: unknown,
  options?: Omit<RequestInit, 'method' | 'body'>
): Promise<T> {
  const headers = new Headers(options?.headers);
  if (body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await apiFetch(url, {
    ...options,
    method: 'POST',
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  return handleApiResponse<T>(response);
}

/**
 * Make a PUT request with JSON body
 */
export async function apiPut<T>(
  url: string,
  body?: unknown,
  options?: Omit<RequestInit, 'method' | 'body'>
): Promise<T> {
  const headers = new Headers(options?.headers);
  if (body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await apiFetch(url, {
    ...options,
    method: 'PUT',
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  return handleApiResponse<T>(response);
}

/**
 * Make a PATCH request with JSON body
 */
export async function apiPatch<T>(
  url: string,
  body?: unknown,
  options?: Omit<RequestInit, 'method' | 'body'>
): Promise<T> {
  const headers = new Headers(options?.headers);
  if (body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await apiFetch(url, {
    ...options,
    method: 'PATCH',
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  return handleApiResponse<T>(response);
}

/**
 * Make a DELETE request
 */
export async function apiDelete<T = void>(
  url: string,
  options?: Omit<RequestInit, 'method'>
): Promise<T> {
  const response = await apiFetch(url, { ...options, method: 'DELETE' });
  return handleApiResponse<T>(response);
}

/**
 * Make a POST request with FormData
 */
export async function apiPostFormData<T>(
  url: string,
  formData: FormData,
  options?: Omit<RequestInit, 'method' | 'body'>
): Promise<T> {
  // Don't set Content-Type - browser will set it with boundary for multipart/form-data
  const response = await apiFetch(url, {
    ...options,
    method: 'POST',
    body: formData,
  });
  return handleApiResponse<T>(response);
}
