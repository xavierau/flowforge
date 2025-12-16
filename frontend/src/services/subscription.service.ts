/**
 * Subscription Management Service
 *
 * Provides methods for subscription and billing operations.
 * Following SOLID principles:
 * - Single Responsibility: Handles only subscription-related API calls
 * - Open/Closed: Easy to extend with new subscription operations
 *
 * Uses centralized API client from lib/api-client.ts for:
 * - Automatic token refresh on 401 responses
 * - Auth header injection
 * - Consistent error handling
 */

import type {
  Subscription,
  SubscriptionPlan,
  PlanFeatures,
  UsageStatistics,
} from '@/types/profile';
import { apiFetch, API_BASE_URL, handleApiResponse } from '@/lib/api-client';

/**
 * Custom error class for subscription API errors
 * @deprecated Use ApiClientError from api-client.ts
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
