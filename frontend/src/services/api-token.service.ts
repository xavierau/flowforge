/**
 * API Token Service
 *
 * Handles all API token operations including creation, listing, updating, and revocation.
 * Uses centralized API client from lib/api-client.ts for:
 * - Automatic token refresh on 401 responses
 * - Auth header injection
 * - Consistent error handling
 */

import type {
  ApiToken,
  ApiTokenCreateRequest,
  ApiTokenCreateResponse,
  ApiTokenUpdateRequest,
} from '@/types/api-token';
import { apiFetch, API_BASE_URL } from '@/lib/api-client';

export const apiTokenService = {
  /**
   * Create a new API token
   */
  async createToken(data: ApiTokenCreateRequest): Promise<ApiTokenCreateResponse> {
    const response = await apiFetch(`${API_BASE_URL}/tokens`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to create token' }));
      throw new Error(error.detail || 'Failed to create token');
    }

    return response.json();
  },

  /**
   * List all API tokens for the current user
   */
  async listTokens(): Promise<ApiToken[]> {
    const response = await apiFetch(`${API_BASE_URL}/tokens`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to list tokens' }));
      throw new Error(error.detail || 'Failed to list tokens');
    }

    return response.json();
  },

  /**
   * Get a specific API token by ID
   */
  async getToken(tokenId: string): Promise<ApiToken> {
    const response = await apiFetch(`${API_BASE_URL}/tokens/${tokenId}`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Token not found' }));
      throw new Error(error.detail || 'Token not found');
    }

    return response.json();
  },

  /**
   * Update an API token (name and/or scopes)
   */
  async updateToken(tokenId: string, data: ApiTokenUpdateRequest): Promise<ApiToken> {
    const response = await apiFetch(`${API_BASE_URL}/tokens/${tokenId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to update token' }));
      throw new Error(error.detail || 'Failed to update token');
    }

    return response.json();
  },

  /**
   * Revoke (delete) an API token
   */
  async revokeToken(tokenId: string): Promise<void> {
    const response = await apiFetch(`${API_BASE_URL}/tokens/${tokenId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to revoke token' }));
      throw new Error(error.detail || 'Failed to revoke token');
    }
  },
};
