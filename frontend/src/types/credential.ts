/**
 * Credential Types
 *
 * Type definitions for workflow credentials/secrets management.
 */

/**
 * Credential scope - determines visibility and access
 */
export type CredentialScope = 'tenant' | 'workflow';

/**
 * Credential response from API (value is masked)
 */
export interface Credential {
  id: string;
  name: string;
  description?: string;
  scope: CredentialScope;
  workflowId?: string; // Only present if scope is 'workflow'
  createdAt: string;
  updatedAt: string;
}

/**
 * Request to create a new credential
 */
export interface CredentialCreateRequest {
  name: string;
  value: string;
  description?: string;
  scope: CredentialScope;
  workflowId?: string; // Required if scope is 'workflow'
}

/**
 * Request to update an existing credential
 */
export interface CredentialUpdateRequest {
  name?: string;
  value?: string;
  description?: string;
}

/**
 * Paginated list of credentials
 */
export interface CredentialListResponse {
  credentials: Credential[];
  total: number;
  page: number;
  pageSize: number;
}
