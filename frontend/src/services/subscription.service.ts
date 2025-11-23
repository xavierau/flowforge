/**
 * Subscription Management Service
 *
 * Provides methods for subscription and billing operations.
 * Following SOLID principles:
 * - Single Responsibility: Handles only subscription-related API calls
 * - Open/Closed: Easy to extend with new subscription operations
 *
 * Uses centralized API wrapper for:
 * - Automatic auth header injection
 * - 401 interceptor with auto-redirect to login
 * - Consistent error handling
 */

import type {
  Subscription,
  SubscriptionPlan,
  PlanFeatures,
  UsageStatistics,
} from '@/types/profile';

const API_BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : '/api/v1';  // Use Vite proxy when VITE_API_URL not set

/**
 * Custom error class for subscription API errors
 */
export class SubscriptionApiError extends Error {
  statusCode: number;
  details?: unknown;

  constructor(message: string, statusCode: number, details?: unknown) {
    super(message);
    this.name = 'SubscriptionApiError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

/**
 * Centralized fetch wrapper with 401 interceptor
 * Automatically adds Authorization header and handles auth errors
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
    throw new SubscriptionApiError('Unauthorized - Please log in again', 401);
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

    throw new SubscriptionApiError(message, response.status, errorData);
  }

  return response.json();
}

/**
 * Get current subscription details
 */
export async function getCurrentSubscription(): Promise<Subscription> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/subscriptions/current`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return handleApiResponse<Subscription>(response);
  } catch (error) {
    if (error instanceof SubscriptionApiError) {
      throw error;
    }
    throw new SubscriptionApiError(
      'Network error. Please check your connection.',
      0
    );
  }
}

/**
 * Get all available plan features
 */
export async function getPlanFeatures(): Promise<PlanFeatures[]> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/subscriptions/plans`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return handleApiResponse<PlanFeatures[]>(response);
  } catch (error) {
    if (error instanceof SubscriptionApiError) {
      throw error;
    }
    throw new SubscriptionApiError(
      'Network error. Please check your connection.',
      0
    );
  }
}

/**
 * Get usage statistics for current billing period
 */
export async function getUsageStatistics(): Promise<UsageStatistics> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/subscriptions/usage`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return handleApiResponse<UsageStatistics>(response);
  } catch (error) {
    if (error instanceof SubscriptionApiError) {
      throw error;
    }
    throw new SubscriptionApiError(
      'Network error. Please check your connection.',
      0
    );
  }
}

/**
 * Upgrade or downgrade subscription plan
 */
export async function changePlan(
  newPlan: SubscriptionPlan
): Promise<Subscription> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/subscriptions/change-plan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ plan: newPlan }),
    });

    return handleApiResponse<Subscription>(response);
  } catch (error) {
    if (error instanceof SubscriptionApiError) {
      throw error;
    }
    throw new SubscriptionApiError(
      'Network error. Please check your connection.',
      0
    );
  }
}

/**
 * Cancel subscription
 */
export async function cancelSubscription(): Promise<void> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/subscriptions/cancel`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    await handleApiResponse<void>(response);
  } catch (error) {
    if (error instanceof SubscriptionApiError) {
      throw error;
    }
    throw new SubscriptionApiError(
      'Network error. Please check your connection.',
      0
    );
  }
}

/**
 * Purchase additional credits
 */
export async function purchaseCredits(amount: number): Promise<Subscription> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/subscriptions/credits`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ credits: amount }),
    });

    return handleApiResponse<Subscription>(response);
  } catch (error) {
    if (error instanceof SubscriptionApiError) {
      throw error;
    }
    throw new SubscriptionApiError(
      'Network error. Please check your connection.',
      0
    );
  }
}
