/**
 * API Token Service
 *
 * Handles all API token operations including creation, listing, updating, and revocation.
 * Uses the centralized apiFetch function for consistent error handling and auth.
 */

import type {
  ApiToken,
  ApiTokenCreateRequest,
  ApiTokenCreateResponse,
  ApiTokenUpdateRequest,
} from '@/types/api-token';

const API_BASE_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1`;

/**
 * Get authentication token from localStorage
 */
function getAuthToken(): string | null {
  return localStorage.getItem('access_token');
}

/**
 * Centralized fetch wrapper with auth
 */
async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = getAuthToken();
  const headers = new Headers(options.headers);

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
    throw new Error('Unauthorized - Please log in again');
  }

  return response;
}

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
