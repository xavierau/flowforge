/**
 * Credential Service
 *
 * Handles all credential/secret operations including creation, listing, and deletion.
 * Uses centralized API client from lib/api-client.ts for:
 * - Automatic token refresh on 401 responses
 * - Auth header injection
 * - Consistent error handling
 */

import type {
  Credential,
  CredentialCreateRequest,
  CredentialUpdateRequest,
  CredentialListResponse,
} from '@/types/credential';
import { apiFetch, API_BASE_URL } from '@/lib/api-client';

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
