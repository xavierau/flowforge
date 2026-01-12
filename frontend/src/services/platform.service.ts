/**
 * Platform API Service
 *
 * Provides API methods for managing platform applications and API keys.
 * All endpoints require super_admin role.
 */

const API_BASE_URL = '/api/v1/admin/platform';

// ============================================================================
// Types
// ============================================================================

export interface PlatformApplication {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  webhook_url: string | null;
  allowed_ips: string[];
  rate_limit_per_minute: number;
  rate_limit_per_hour: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  api_key_count: number;
}

export interface PlatformApplicationCreated extends PlatformApplication {
  initial_api_key: string;
}

export interface PlatformApiKey {
  id: string;
  name: string;
  token_prefix: string;
  scopes: string[];
  expires_at: string | null;
  created_at: string;
  last_used_at: string | null;
  is_active: boolean;
}

export interface PlatformApiKeyCreated extends PlatformApiKey {
  token: string;
}

export interface PlatformAuditLog {
  id: string;
  application_id: string | null;
  api_key_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  endpoint: string;
  method: string;
  ip_address: string | null;
  status_code: number | null;
  error_message: string | null;
  created_at: string;
}

export interface CreateApplicationRequest {
  name: string;
  slug: string;
  description?: string;
  webhook_url?: string;
  allowed_ips?: string[];
  rate_limit_per_minute?: number;
  rate_limit_per_hour?: number;
}

export interface UpdateApplicationRequest {
  name?: string;
  description?: string;
  webhook_url?: string;
  allowed_ips?: string[];
  rate_limit_per_minute?: number;
  rate_limit_per_hour?: number;
}

export interface CreateApiKeyRequest {
  name: string;
  scopes: string[];
  expires_in_days?: number;
}

export interface PaginatedResponse<T> {
  total: number;
  limit: number;
  offset: number;
  items: T[];
}

// ============================================================================
// API Helper
// ============================================================================

async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem('access_token');
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

async function handleApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'An error occurred');
  }
  return response.json();
}

// ============================================================================
// Platform Application APIs
// ============================================================================

export async function listApplications(params?: {
  limit?: number;
  offset?: number;
  is_active?: boolean;
}): Promise<{
  total: number;
  limit: number;
  offset: number;
  applications: PlatformApplication[];
}> {
  const queryParams = new URLSearchParams();
  if (params?.limit) queryParams.set('limit', params.limit.toString());
  if (params?.offset) queryParams.set('offset', params.offset.toString());
  if (params?.is_active !== undefined) queryParams.set('is_active', params.is_active.toString());

  const response = await apiFetch(
    `${API_BASE_URL}/applications?${queryParams}`,
    { method: 'GET' }
  );
  return handleApiResponse(response);
}

export async function getApplication(id: string): Promise<PlatformApplication> {
  const response = await apiFetch(
    `${API_BASE_URL}/applications/${id}`,
    { method: 'GET' }
  );
  return handleApiResponse(response);
}

export async function createApplication(
  data: CreateApplicationRequest
): Promise<PlatformApplicationCreated> {
  const response = await apiFetch(`${API_BASE_URL}/applications`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleApiResponse(response);
}

export async function updateApplication(
  id: string,
  data: UpdateApplicationRequest
): Promise<PlatformApplication> {
  const response = await apiFetch(`${API_BASE_URL}/applications/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleApiResponse(response);
}

export async function deactivateApplication(id: string): Promise<void> {
  const response = await apiFetch(`${API_BASE_URL}/applications/${id}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to deactivate application');
  }
}

export async function activateApplication(id: string): Promise<PlatformApplication> {
  const response = await apiFetch(`${API_BASE_URL}/applications/${id}/activate`, {
    method: 'POST',
  });
  return handleApiResponse(response);
}

// ============================================================================
// Platform API Key APIs
// ============================================================================

export async function listApiKeys(
  applicationId: string,
  isActive?: boolean
): Promise<PlatformApiKey[]> {
  const queryParams = new URLSearchParams();
  if (isActive !== undefined) queryParams.set('is_active', isActive.toString());

  const response = await apiFetch(
    `${API_BASE_URL}/applications/${applicationId}/keys?${queryParams}`,
    { method: 'GET' }
  );
  return handleApiResponse(response);
}

export async function createApiKey(
  applicationId: string,
  data: CreateApiKeyRequest
): Promise<PlatformApiKeyCreated> {
  const response = await apiFetch(`${API_BASE_URL}/applications/${applicationId}/keys`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleApiResponse(response);
}

export async function revokeApiKey(keyId: string): Promise<void> {
  const response = await apiFetch(`${API_BASE_URL}/keys/${keyId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to revoke API key');
  }
}

// ============================================================================
// Audit Log APIs
// ============================================================================

export async function listAuditLogs(params?: {
  limit?: number;
  offset?: number;
  application_id?: string;
  action?: string;
  resource_type?: string;
}): Promise<{
  total: number;
  limit: number;
  offset: number;
  logs: PlatformAuditLog[];
}> {
  const queryParams = new URLSearchParams();
  if (params?.limit) queryParams.set('limit', params.limit.toString());
  if (params?.offset) queryParams.set('offset', params.offset.toString());
  if (params?.application_id) queryParams.set('application_id', params.application_id);
  if (params?.action) queryParams.set('action', params.action);
  if (params?.resource_type) queryParams.set('resource_type', params.resource_type);

  const response = await apiFetch(
    `${API_BASE_URL}/audit-logs?${queryParams}`,
    { method: 'GET' }
  );
  return handleApiResponse(response);
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Available platform API scopes
 */
export const PLATFORM_SCOPES = [
  { value: '*:*', label: 'All Scopes', description: 'Full access to all platform APIs' },
  { value: 'tenants:*', label: 'All Tenant Operations', description: 'Full access to tenant management' },
  { value: 'tenants:create', label: 'Create Tenants', description: 'Create new tenants' },
  { value: 'tenants:read', label: 'Read Tenants', description: 'View tenant details' },
  { value: 'tenants:update', label: 'Update Tenants', description: 'Modify tenant information' },
  { value: 'tenants:delete', label: 'Delete Tenants', description: 'Deactivate tenants' },
  { value: 'users:*', label: 'All User Operations', description: 'Full access to user management' },
  { value: 'users:create', label: 'Create Users', description: 'Create new users in tenants' },
  { value: 'users:read', label: 'Read Users', description: 'View user details' },
  { value: 'users:update', label: 'Update Users', description: 'Modify user information' },
  { value: 'users:delete', label: 'Delete Users', description: 'Deactivate users' },
  { value: 'tokens:*', label: 'All Token Operations', description: 'Full access to token management' },
  { value: 'tokens:create', label: 'Create Tokens', description: 'Generate API tokens for users' },
  { value: 'tokens:read', label: 'Read Tokens', description: 'View token details' },
  { value: 'tokens:revoke', label: 'Revoke Tokens', description: 'Deactivate API tokens' },
  { value: 'credits:*', label: 'All Credit Operations', description: 'Full access to credit management' },
  { value: 'credits:add', label: 'Add Credits', description: 'Add credits to tenant accounts' },
  { value: 'credits:read', label: 'Read Credits', description: 'View credit balances' },
] as const;

/**
 * Format a date string for display
 */
export function formatDate(dateString: string | null): string {
  if (!dateString) return 'Never';
  return new Date(dateString).toLocaleString();
}

/**
 * Copy text to clipboard
 */
export async function copyToClipboard(text: string): Promise<void> {
  await navigator.clipboard.writeText(text);
}
