/**
 * Metrics and Billing API Service
 *
 * Provides methods for fetching dashboard metrics and billing data.
 * Follows SOLID principles:
 * - Single Responsibility: Handles only metrics-related API calls
 * - Open/Closed: Easy to extend with new metric endpoints
 * - Interface Segregation: Focused interface for metrics operations
 */

import type {
  DashboardMetrics,
  CompletedJobsResponse,
  CompletedJobsFilters,
  DateRangeOption,
} from '@/types/metrics';
import { getAccessToken, clearTokens } from './auth.service';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export class MetricsApiError extends Error {
  statusCode: number;
  details?: unknown;

  constructor(message: string, statusCode: number, details?: unknown) {
    super(message);
    this.name = 'MetricsApiError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

/**
 * Handles API response errors with proper type checking
 */
async function handleApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const contentType = response.headers.get('content-type');
    let errorData: unknown;

    if (contentType?.includes('application/json')) {
      try {
        errorData = await response.json();
      } catch {
        // Ignore JSON parse errors
      }
    }

    // Handle specific HTTP status codes
    if (response.status === 401) {
      throw new MetricsApiError('Unauthorized. Please log in.', 401, errorData);
    }

    if (response.status === 403) {
      throw new MetricsApiError(
        'Access denied. Insufficient permissions.',
        403,
        errorData
      );
    }

    if (response.status === 404) {
      throw new MetricsApiError('Resource not found.', 404, errorData);
    }

    // Generic error
    const message =
      errorData && typeof errorData === 'object' && 'detail' in errorData
        ? String(errorData.detail)
        : 'An error occurred';

    throw new MetricsApiError(message, response.status, errorData);
  }

  return response.json();
}

/**
 * Creates authorization headers with JWT token
 */
function createAuthHeaders(): HeadersInit {
  const token = getAccessToken();
  if (!token) {
    throw new MetricsApiError('No authentication token found', 401);
  }

  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

/**
 * Centralized fetch wrapper with 401 interceptor for metrics API
 *
 * Automatically:
 * - Adds Authorization header if token exists
 * - Intercepts 401 responses and redirects to login
 * - Clears stored tokens on unauthorized access
 *
 * @param url - Request URL
 * @param options - Fetch options
 * @returns Response promise
 */
async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  // Add Authorization header if token exists
  const token = getAccessToken();
  const headers = new Headers(options.headers);

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  // Make the request with updated headers
  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Intercept 401 Unauthorized responses
  if (response.status === 401) {
    // Clear tokens from storage
    clearTokens();

    // Redirect to login page
    window.location.href = '/login';

    // Throw error to prevent further processing
    throw new MetricsApiError('Unauthorized - Please log in again', 401);
  }

  return response;
}

/**
 * Fetch dashboard metrics for specified date range
 *
 * @param days - Number of days to look back (7, 30, or 90)
 * @returns Dashboard metrics including stats and time series data
 */
export async function getDashboardMetrics(
  days: DateRangeOption = 30
): Promise<DashboardMetrics> {
  try {
    const response = await apiFetch(
      `${API_BASE_URL}/metrics/dashboard?days=${days}`,
      {
        method: 'GET',
      }
    );

    return handleApiResponse<DashboardMetrics>(response);
  } catch (error) {
    if (error instanceof MetricsApiError) {
      throw error;
    }

    // Network or other errors
    throw new MetricsApiError(
      'Network error. Please check your connection.',
      0
    );
  }
}

/**
 * Fetch completed jobs for billing with pagination and filters
 *
 * @param page - Page number (1-indexed)
 * @param pageSize - Number of items per page
 * @param filters - Optional filters (date range, model)
 * @returns Paginated list of completed jobs with total cost
 */
export async function getCompletedJobs(
  page: number = 1,
  pageSize: number = 50,
  filters?: CompletedJobsFilters
): Promise<CompletedJobsResponse> {
  try {
    // Build query parameters
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });

    if (filters?.start_date) {
      params.append('start_date', filters.start_date);
    }

    if (filters?.end_date) {
      params.append('end_date', filters.end_date);
    }

    if (filters?.model) {
      params.append('model', filters.model);
    }

    const response = await apiFetch(
      `${API_BASE_URL}/metrics/jobs/completed?${params.toString()}`,
      {
        method: 'GET',
      }
    );

    return handleApiResponse<CompletedJobsResponse>(response);
  } catch (error) {
    if (error instanceof MetricsApiError) {
      throw error;
    }

    // Network or other errors
    throw new MetricsApiError(
      'Network error. Please check your connection.',
      0
    );
  }
}

/**
 * Export completed jobs data (placeholder for future CSV/PDF export)
 *
 * @param _filters - Optional filters to apply (unused for now)
 * @returns Blob for download
 */
export async function exportCompletedJobs(
  _filters?: CompletedJobsFilters
): Promise<Blob> {
  // TODO: Implement when backend endpoint is ready
  throw new MetricsApiError('Export functionality not yet implemented', 501);
}
