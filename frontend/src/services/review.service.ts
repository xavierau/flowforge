/**
 * Review Management Service (HITL System)
 *
 * Provides methods for human review queue and correction management.
 * Following SOLID principles:
 * - Single Responsibility: Handles only review-related API calls
 * - Open/Closed: Easy to extend with new review operations
 * - Interface Segregation: Focused interface for review operations
 *
 * CRITICAL: Uses centralized API wrapper for:
 * - Automatic auth header injection
 * - 401 interceptor with auto-redirect to login
 * - Consistent error handling
 */

import type {
  ReviewRequest,
  ReviewCorrection,
  QueueFilters,
  ReviewQueueResponse,
  ReviewMetrics,
  SubmitReviewRequest,
  AssignReviewRequest,
} from '@/types/review';

const API_BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : '/api/v1'; // Use Vite proxy when VITE_API_URL not set

/**
 * Custom error class for review API errors
 */
export class ReviewApiError extends Error {
  statusCode: number;
  details?: unknown;

  constructor(message: string, statusCode: number, details?: unknown) {
    super(message);
    this.name = 'ReviewApiError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

/**
 * Centralized fetch wrapper with 401 interceptor
 * Automatically adds Authorization header and handles auth errors
 *
 * CRITICAL: This wrapper MUST be used for ALL API calls
 */
async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem('access_token');
  const headers = new Headers(options.headers);

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Intercept 401 - clear tokens and redirect to login
  if (response.status === 401) {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
    throw new ReviewApiError('Unauthorized - Please log in again', 401);
  }

  return response;
}

/**
 * Handle API response errors
 */
async function handleApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const contentType = response.headers.get('content-type');
    let errorData: unknown;

    if (contentType?.includes('application/json')) {
      errorData = await response.json();
    }

    const message =
      errorData &&
      typeof errorData === 'object' &&
      'detail' in errorData &&
      typeof errorData.detail === 'string'
        ? errorData.detail
        : 'An error occurred';

    throw new ReviewApiError(message, response.status, errorData);
  }

  return response.json();
}

/**
 * Get review queue with filters
 *
 * @param params - Queue filter parameters
 * @returns Paginated list of review requests
 */
export async function getReviewQueue(
  params: QueueFilters = {}
): Promise<ReviewQueueResponse> {
  try {
    // Build query string from filters
    const queryParams = new URLSearchParams();

    if (params.status) {
      if (Array.isArray(params.status)) {
        params.status.forEach(s => queryParams.append('status', s));
      } else {
        queryParams.append('status', params.status);
      }
    }

    if (params.priority) {
      if (Array.isArray(params.priority)) {
        params.priority.forEach(p => queryParams.append('priority', p));
      } else {
        queryParams.append('priority', params.priority);
      }
    }

    if (params.assigned_to_me !== undefined) {
      queryParams.append('assigned_to_me', params.assigned_to_me.toString());
    }

    if (params.unassigned !== undefined) {
      queryParams.append('unassigned', params.unassigned.toString());
    }

    if (params.escalated !== undefined) {
      queryParams.append('escalated', params.escalated.toString());
    }

    if (params.sort_by) {
      queryParams.append('sort_by', params.sort_by);
    }

    if (params.sort_order) {
      queryParams.append('sort_order', params.sort_order);
    }

    if (params.page) {
      queryParams.append('page', params.page.toString());
    }

    if (params.page_size) {
      queryParams.append('page_size', params.page_size.toString());
    }

    const queryString = queryParams.toString();
    const url = queryString
      ? `${API_BASE_URL}/reviews/queue?${queryString}`
      : `${API_BASE_URL}/reviews/queue`;

    const response = await apiFetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return handleApiResponse<ReviewQueueResponse>(response);
  } catch (error) {
    if (error instanceof ReviewApiError) {
      throw error;
    }
    throw new ReviewApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Get a single review request by ID
 *
 * @param reviewId - Review request ID
 * @returns Review request with extraction data
 */
export async function getReview(reviewId: string): Promise<ReviewRequest> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/reviews/${reviewId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return handleApiResponse<ReviewRequest>(response);
  } catch (error) {
    if (error instanceof ReviewApiError) {
      throw error;
    }
    throw new ReviewApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Assign a review request to a user
 *
 * @param reviewId - Review request ID
 * @param userId - User ID to assign to (or current user if omitted)
 * @returns Updated review request
 */
export async function assignReview(
  reviewId: string,
  userId?: string
): Promise<ReviewRequest> {
  try {
    const body: AssignReviewRequest | undefined = userId ? { user_id: userId } : undefined;

    const response = await apiFetch(`${API_BASE_URL}/reviews/${reviewId}/assign`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    return handleApiResponse<ReviewRequest>(response);
  } catch (error) {
    if (error instanceof ReviewApiError) {
      throw error;
    }
    throw new ReviewApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Start reviewing a request (changes status to in_review)
 *
 * @param reviewId - Review request ID
 * @returns Updated review request
 */
export async function startReview(reviewId: string): Promise<ReviewRequest> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/reviews/${reviewId}/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return handleApiResponse<ReviewRequest>(response);
  } catch (error) {
    if (error instanceof ReviewApiError) {
      throw error;
    }
    throw new ReviewApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Submit review with corrections
 *
 * @param reviewId - Review request ID
 * @param data - Corrections and review action
 * @returns Updated review request
 */
export async function submitReview(
  reviewId: string,
  data: SubmitReviewRequest
): Promise<ReviewRequest> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/reviews/${reviewId}/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    return handleApiResponse<ReviewRequest>(response);
  } catch (error) {
    if (error instanceof ReviewApiError) {
      throw error;
    }
    throw new ReviewApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Cancel a review request
 *
 * @param reviewId - Review request ID
 * @param reason - Optional cancellation reason
 * @returns Updated review request
 */
export async function cancelReview(
  reviewId: string,
  reason?: string
): Promise<ReviewRequest> {
  try {
    const queryParams = reason ? `?reason=${encodeURIComponent(reason)}` : '';
    const response = await apiFetch(`${API_BASE_URL}/reviews/${reviewId}${queryParams}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return handleApiResponse<ReviewRequest>(response);
  } catch (error) {
    if (error instanceof ReviewApiError) {
      throw error;
    }
    throw new ReviewApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Escalate a review request
 *
 * @param reviewId - Review request ID
 * @param reason - Escalation reason
 * @returns Updated review request
 */
export async function escalateReview(
  reviewId: string,
  reason: string
): Promise<ReviewRequest> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/reviews/${reviewId}/escalate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ reason }),
    });

    return handleApiResponse<ReviewRequest>(response);
  } catch (error) {
    if (error instanceof ReviewApiError) {
      throw error;
    }
    throw new ReviewApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Get review metrics and statistics
 *
 * @returns Review queue metrics
 */
export async function getReviewMetrics(): Promise<ReviewMetrics> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/reviews/metrics`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return handleApiResponse<ReviewMetrics>(response);
  } catch (error) {
    if (error instanceof ReviewApiError) {
      throw error;
    }
    throw new ReviewApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Get corrections for a specific review
 *
 * @param reviewId - Review request ID
 * @returns List of corrections
 */
export async function getReviewCorrections(
  reviewId: string
): Promise<ReviewCorrection[]> {
  try {
    const response = await apiFetch(
      `${API_BASE_URL}/reviews/${reviewId}/corrections`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    return handleApiResponse<ReviewCorrection[]>(response);
  } catch (error) {
    if (error instanceof ReviewApiError) {
      throw error;
    }
    throw new ReviewApiError('Network error. Please check your connection.', 0);
  }
}
