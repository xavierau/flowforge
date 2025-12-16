/**
 * Metrics and Billing API Service
 *
 * Provides methods for fetching dashboard metrics and billing data.
 * Follows SOLID principles:
 * - Single Responsibility: Handles only metrics-related API calls
 * - Open/Closed: Easy to extend with new metric endpoints
 * - Interface Segregation: Focused interface for metrics operations
 *
 * Uses centralized API client from lib/api-client.ts for:
 * - Automatic token refresh on 401 responses
 * - Auth header injection
 * - Consistent error handling
 */

import type {
  DashboardMetrics,
  CompletedJobsResponse,
  CompletedJobsFilters,
  DateRangeOption,
} from '@/types/metrics';
import { apiFetch, API_BASE_URL, handleApiResponse } from '@/lib/api-client';

/**
 * @deprecated Use ApiClientError from api-client.ts
 */
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
 * Fetch dashboard metrics for specified date range
 *
 * @param days - Number of days to look back (7, 30, or 90)
 * @returns Dashboard metrics including stats and time series data
 */
export async function getDashboardMetrics(
  days: DateRangeOption = 30
): Promise<DashboardMetrics> {
  try {
    // Add cache-busting timestamp to prevent browser caching
    const cacheBuster = Date.now();
    // Use /jobs/analytics/dashboard to avoid "metrics" in URL which may be blocked
    // by ad blockers or security tools
    const response = await apiFetch(
      `${API_BASE_URL}/jobs/analytics/dashboard?days=${days}&_t=${cacheBuster}`);

    // Handle 204 No Content - return empty dashboard metrics
    // This occurs when user has no completed jobs for their tenant
    if (response.status === 204) {
      return {
        stats: {
          total_jobs: 0,
          total_pages: 0,
          total_tokens: 0,
          estimated_cost: 0,
        },
        jobs_over_time: [],
        pages_over_time: [],
        tokens_over_time: [],
        model_distribution: [],
      };
    }

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

    // Add cache-busting timestamp to prevent browser caching
    params.append('_t', Date.now().toString());

    // Use /jobs/analytics/completed to avoid "metrics" in URL which may be blocked
    // by ad blockers or security tools
    const response = await apiFetch(
      `${API_BASE_URL}/jobs/analytics/completed?${params.toString()}`
    );

    // Handle 204 No Content - return empty jobs list
    // This occurs when user has no completed jobs for their tenant
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
