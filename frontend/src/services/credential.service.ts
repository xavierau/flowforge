/**
 * Credential Service
 *
 * Handles all credential/secret operations including creation, listing, and deletion.
 * Uses the centralized apiFetch function for consistent error handling and auth.
 */

import type {
  Credential,
  CredentialCreateRequest,
  CredentialUpdateRequest,
  CredentialListResponse,
} from '@/types/credential';

const API_BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : '/api/v1'; // Use Vite proxy when VITE_API_URL not set

/**
 * Get authentication token from localStorage
 */
function getAuthToken(): string | null {
  return localStorage.getItem('access_token');
}

/**
 * Centralized fetch wrapper with auth
 */
async function apiFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
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

export const credentialService = {
  /**
   * Create a new credential
   */
  async createCredential(data: CredentialCreateRequest): Promise<Credential> {
    const response = await apiFetch(`${API_BASE_URL}/credentials`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: 'Failed to create credential' }));
      throw new Error(error.detail || 'Failed to create credential');
    }

    return response.json();
  },

  /**
   * List all credentials with optional filters
   */
  async listCredentials(params?: {
    scope?: 'tenant' | 'workflow';
    workflowId?: string;
    page?: number;
    pageSize?: number;
  }): Promise<CredentialListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.scope) searchParams.set('scope', params.scope);
    if (params?.workflowId) searchParams.set('workflow_id', params.workflowId);
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.pageSize) searchParams.set('page_size', String(params.pageSize));

    const url = `${API_BASE_URL}/credentials${searchParams.toString() ? `?${searchParams}` : ''}`;
    const response = await apiFetch(url);

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: 'Failed to list credentials' }));
      throw new Error(error.detail || 'Failed to list credentials');
    }

    return response.json();
  },

  /**
   * Get a specific credential by ID
   */
  async getCredential(credentialId: string): Promise<Credential> {
    const response = await apiFetch(
      `${API_BASE_URL}/credentials/${credentialId}`
    );

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: 'Credential not found' }));
      throw new Error(error.detail || 'Credential not found');
    }

    return response.json();
  },

  /**
   * Update an existing credential
   */
  async updateCredential(
    credentialId: string,
    data: CredentialUpdateRequest
  ): Promise<Credential> {
    const response = await apiFetch(
      `${API_BASE_URL}/credentials/${credentialId}`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }
    );

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: 'Failed to update credential' }));
      throw new Error(error.detail || 'Failed to update credential');
    }

    return response.json();
  },

  /**
   * Delete a credential
   */
  async deleteCredential(credentialId: string): Promise<void> {
    const response = await apiFetch(
      `${API_BASE_URL}/credentials/${credentialId}`,
      {
        method: 'DELETE',
      }
    );

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: 'Failed to delete credential' }));
      throw new Error(error.detail || 'Failed to delete credential');
    }
  },
};
