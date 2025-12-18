/**
 * Pricing Service
 *
 * Provides methods for admin model pricing management.
 * Following SOLID principles:
 * - Single Responsibility: Handles only pricing-related API calls
 * - Open/Closed: Easy to extend with new pricing operations
 * - Interface Segregation: Focused interface for pricing operations
 *
 * Uses centralized API client from lib/api-client.ts for:
 * - Automatic token refresh on 401 responses
 * - Auth header injection
 * - Consistent error handling
 */

import type {
  ModelPricing,
  ModelPricingListResponse,
  ModelPricingHistoryResponse,
  CreateModelPricingRequest,
} from '@/types/pricing';
import { apiFetch, API_BASE_URL, handleApiResponse } from '@/lib/api-client';

/**
 * Custom error class for pricing API errors
 * @deprecated Use ApiClientError from api-client.ts
 */
export class PricingApiError extends Error {
  statusCode: number;
  details?: unknown;

  constructor(message: string, statusCode: number, details?: unknown) {
    super(message);
    this.name = 'PricingApiError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

// ============================================================================
// Pricing Management
// ============================================================================

/**
 * List all model pricing
 */
export async function listPricing(): Promise<ModelPricingListResponse> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/admin/pricing`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return handleApiResponse<ModelPricingListResponse>(response);
  } catch (error) {
    if (error instanceof PricingApiError) {
      throw error;
    }
    throw new PricingApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Create new model pricing
 */
export async function createPricing(
  data: CreateModelPricingRequest
): Promise<ModelPricing> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/admin/pricing`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    return handleApiResponse<ModelPricing>(response);
  } catch (error) {
    if (error instanceof PricingApiError) {
      throw error;
    }
    throw new PricingApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Get pricing history for a specific model
 */
export async function getPricingHistory(
  modelName: string
): Promise<ModelPricingHistoryResponse> {
  try {
    const encodedModelName = encodeURIComponent(modelName);
    const response = await apiFetch(
      `${API_BASE_URL}/admin/pricing/${encodedModelName}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    return handleApiResponse<ModelPricingHistoryResponse>(response);
  } catch (error) {
    if (error instanceof PricingApiError) {
      throw error;
    }
    throw new PricingApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Deactivate (soft delete) a pricing record
 */
export async function deactivatePricing(
  pricingId: string,
  reason: string
): Promise<void> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/admin/pricing/${pricingId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ reason }),
    });

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

      throw new PricingApiError(message, response.status, errorData);
    }
  } catch (error) {
    if (error instanceof PricingApiError) {
      throw error;
    }
    throw new PricingApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Response type for supported models API
 */
interface SupportedModelsResponse {
  models: string[];
  total: number;
}

/**
 * Get list of supported models
 */
export async function getSupportedModels(): Promise<string[]> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/admin/pricing/models`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await handleApiResponse<SupportedModelsResponse>(response);
    return data.models;
  } catch (error) {
    if (error instanceof PricingApiError) {
      throw error;
    }
    throw new PricingApiError('Network error. Please check your connection.', 0);
  }
}
