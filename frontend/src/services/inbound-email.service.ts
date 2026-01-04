/**
 * Inbound Email Service
 *
 * Provides methods for managing inbound email addresses and viewing email logs.
 * Following SOLID principles:
 * - Single Responsibility: Handles only inbound email-related API calls
 * - Open/Closed: Easy to extend with new inbound email operations
 * - Interface Segregation: Focused interface for inbound email operations
 *
 * Uses centralized API client from lib/api-client.ts for:
 * - Automatic token refresh on 401 responses
 * - Auth header injection
 * - Consistent error handling
 */

import type {
  InboundEmailAddressCreate,
  InboundEmailAddressUpdate,
  InboundEmailAddressResponse,
  InboundEmailAddressListResponse,
  InboundEmailLogListResponse,
} from '@/types/inbound-email';
import { apiFetch, API_BASE_URL, handleApiResponse } from '@/lib/api-client';

// ============================================================================
// INBOUND EMAIL ADDRESS ENDPOINTS
// ============================================================================

/**
 * Create a new inbound email address
 *
 * @param data - Inbound email address configuration
 * @returns The created inbound email address with generated email
 */
export async function createInboundEmailAddress(
  data: InboundEmailAddressCreate
): Promise<InboundEmailAddressResponse> {
  const response = await apiFetch(`${API_BASE_URL}/inbound-emails`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleApiResponse<InboundEmailAddressResponse>(response);
}

/**
 * List all inbound email addresses for the current tenant
 *
 * @param params - Optional filtering and pagination parameters
 * @returns List of inbound email addresses with pagination info
 */
export async function listInboundEmailAddresses(params?: {
  is_active?: boolean;
  limit?: number;
  offset?: number;
}): Promise<InboundEmailAddressListResponse> {
  const queryParams = new URLSearchParams();

  if (params?.is_active !== undefined) {
    queryParams.set('is_active', params.is_active.toString());
  }
  if (params?.limit !== undefined) {
    queryParams.set('limit', params.limit.toString());
  }
  if (params?.offset !== undefined) {
    queryParams.set('offset', params.offset.toString());
  }

  const queryString = queryParams.toString();
  const url = `${API_BASE_URL}/inbound-emails${queryString ? `?${queryString}` : ''}`;

  const response = await apiFetch(url);
  return handleApiResponse<InboundEmailAddressListResponse>(response);
}

/**
 * Get a specific inbound email address by ID
 *
 * @param id - Inbound email address UUID
 * @returns The inbound email address details
 */
export async function getInboundEmailAddress(
  id: string
): Promise<InboundEmailAddressResponse> {
  const response = await apiFetch(`${API_BASE_URL}/inbound-emails/${id}`);
  return handleApiResponse<InboundEmailAddressResponse>(response);
}

/**
 * Update an existing inbound email address
 *
 * @param id - Inbound email address UUID
 * @param data - Fields to update (partial update supported)
 * @returns The updated inbound email address
 */
export async function updateInboundEmailAddress(
  id: string,
  data: InboundEmailAddressUpdate
): Promise<InboundEmailAddressResponse> {
  const response = await apiFetch(`${API_BASE_URL}/inbound-emails/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleApiResponse<InboundEmailAddressResponse>(response);
}

/**
 * Delete an inbound email address
 *
 * @param id - Inbound email address UUID
 */
export async function deleteInboundEmailAddress(id: string): Promise<void> {
  const response = await apiFetch(`${API_BASE_URL}/inbound-emails/${id}`, {
    method: 'DELETE',
  });
  return handleApiResponse<void>(response);
}

// ============================================================================
// INBOUND EMAIL LOG ENDPOINTS
// ============================================================================

/**
 * Get email logs for a specific inbound email address
 *
 * @param addressId - Inbound email address UUID
 * @param params - Optional filtering and pagination parameters
 * @returns List of email log entries with pagination info
 */
export async function getInboundEmailLogs(
  addressId: string,
  params?: {
    status_filter?: string;
    limit?: number;
    offset?: number;
  }
): Promise<InboundEmailLogListResponse> {
  const queryParams = new URLSearchParams();

  if (params?.status_filter) {
    queryParams.set('status_filter', params.status_filter);
  }
  if (params?.limit !== undefined) {
    queryParams.set('limit', params.limit.toString());
  }
  if (params?.offset !== undefined) {
    queryParams.set('offset', params.offset.toString());
  }

  const queryString = queryParams.toString();
  const url = `${API_BASE_URL}/inbound-emails/${addressId}/logs${queryString ? `?${queryString}` : ''}`;

  const response = await apiFetch(url);
  return handleApiResponse<InboundEmailLogListResponse>(response);
}
