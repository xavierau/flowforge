/**
 * Pricing Types
 *
 * Type definitions for model pricing management.
 * Following TypeScript best practices:
 * - Interface segregation for different response types
 * - Optional properties marked with ?
 * - Strict types for all fields
 */

/**
 * Model pricing record
 */
export interface ModelPricing {
  id: string;
  model_name: string;
  input_price_per_million: number;
  output_price_per_million: number;
  effective_from: string;
  effective_until: string | null;
  is_active: boolean;
  created_by: string;
  created_by_email: string;
  created_at: string;
  notes: string | null;
}

/**
 * Response for listing all model pricing
 */
export interface ModelPricingListResponse {
  pricing: ModelPricing[];
  total: number;
}

/**
 * Response for pricing history of a specific model
 */
export interface ModelPricingHistoryResponse {
  model_name: string;
  history: ModelPricing[];
  current_pricing: ModelPricing | null;
}

/**
 * Request to create new model pricing
 */
export interface CreateModelPricingRequest {
  model_name: string;
  input_price_per_million: number;
  output_price_per_million: number;
  effective_from?: string;
  notes?: string;
}

/**
 * Request to deactivate pricing
 */
export interface DeactivatePricingRequest {
  reason: string;
}

/**
 * Pricing status for UI display
 */
export type PricingStatus = 'current' | 'superseded' | 'deactivated' | 'future';

/**
 * Helper function to determine pricing status
 */
export function getPricingStatus(pricing: ModelPricing): PricingStatus {
  if (!pricing.is_active) {
    return 'deactivated';
  }

  const now = new Date();
  const effectiveFrom = new Date(pricing.effective_from);

  // Future pricing (not yet effective)
  if (effectiveFrom > now) {
    return 'future';
  }

  // Current pricing (no end date or end date in future)
  if (!pricing.effective_until || new Date(pricing.effective_until) > now) {
    return 'current';
  }

  // Superseded (has end date in the past)
  return 'superseded';
}
