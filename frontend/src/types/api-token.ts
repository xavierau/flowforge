/**
 * API Token type definitions
 */

export interface ApiToken {
  token_id: string;
  name: string;
  token_prefix: string;
  scopes: string[];
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string;
}

export interface ApiTokenCreateRequest {
  name: string;
  scopes: string[];
  expires_in_days: number | null;
}

export interface ApiTokenCreateResponse {
  token: string;
  token_id: string;
  name: string;
  token_prefix: string;
  scopes: string[];
  expires_at: string | null;
  created_at: string;
}

export interface ApiTokenUpdateRequest {
  name?: string;
  scopes?: string[];
}

/**
 * Available scopes for API tokens
 */
export const AVAILABLE_SCOPES = [
  // Documents
  { value: 'documents:read', label: 'Read Documents', group: 'Documents' },
  { value: 'documents:create', label: 'Upload Documents', group: 'Documents' },
  { value: 'documents:update', label: 'Update Documents', group: 'Documents' },
  { value: 'documents:delete', label: 'Delete Documents', group: 'Documents' },

  // Extraction (Most Important)
  { value: 'extraction:create', label: 'Extract Data (Parse Documents)', group: 'Extraction' },

  // Schemas
  { value: 'schemas:read', label: 'Read Schemas', group: 'Schemas' },
  { value: 'schemas:create', label: 'Create Schemas', group: 'Schemas' },
  { value: 'schemas:update', label: 'Update Schemas', group: 'Schemas' },
  { value: 'schemas:delete', label: 'Delete Schemas', group: 'Schemas' },

  // Jobs
  { value: 'jobs:read', label: 'Read Extraction Jobs', group: 'Jobs' },
];

/**
 * Expiration options for API tokens
 */
export const EXPIRATION_OPTIONS = [
  { value: 30, label: '30 days' },
  { value: 60, label: '60 days' },
  { value: 90, label: '90 days' },
  { value: 365, label: '1 year' },
  { value: null, label: 'Never' },
];

export type Scope = string;
