/**
 * Admin Service
 *
 * Provides methods for super admin operations.
 * Following SOLID principles:
 * - Single Responsibility: Handles only admin-related API calls
 * - Open/Closed: Easy to extend with new admin operations
 * - Interface Segregation: Focused interface for admin operations
 *
 * Uses centralized API client from lib/api-client.ts for:
 * - Automatic token refresh on 401 responses
 * - Auth header injection
 * - Consistent error handling
 */

import type {
  PlatformStatistics,
  TenantListResponse,
  TenantDetailResponse,
  TenantFilters,
  UserListResponse,
  UserDetailResponse,
  UserFilters,
  UserListItem,
  ApiTokenListItem,
  UpdateTenantStatusRequest,
  UpdateUserStatusRequest,
  RevokeApiTokenRequest,
  AddTenantCreditsRequest,
  PlatformSettingsListResponse,
  PlatformSetting,
  UpdatePlatformSettingRequest,
  SuccessResponse,
  TopTenantsResponse,
} from '@/types/admin';
import { apiFetch, API_BASE_URL, handleApiResponse } from '@/lib/api-client';

/**
 * Custom error class for admin API errors
 * @deprecated Use ApiClientError from api-client.ts
 */
export class AdminApiError extends Error {
  statusCode: number;
  details?: unknown;

  constructor(message: string, statusCode: number, details?: unknown) {
    super(message);
    this.name = 'AdminApiError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

// ============================================================================
// Platform Dashboard
// ============================================================================

/**
 * Get platform-wide statistics
 */
export async function getDashboardMetrics(): Promise<PlatformStatistics> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/admin/dashboard`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return handleApiResponse<PlatformStatistics>(response);
  } catch (error) {
    if (error instanceof AdminApiError) {
      throw error;
    }
    throw new AdminApiError('Network error. Please check your connection.', 0);
  }
}

// ============================================================================
// Tenant Management
// ============================================================================

/**
 * Get paginated tenant list with filters
 */
export async function getTenants(filters: TenantFilters = {}): Promise<TenantListResponse> {
  try {
    const params = new URLSearchParams();
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.page_size) params.append('page_size', filters.page_size.toString());
    if (filters.status) params.append('status', filters.status);
    if (filters.plan) params.append('plan', filters.plan);
    if (filters.search) params.append('search', filters.search);

    const response = await apiFetch(
      `${API_BASE_URL}/admin/tenants?${params.toString()}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    return handleApiResponse<TenantListResponse>(response);
  } catch (error) {
    if (error instanceof AdminApiError) {
      throw error;
    }
    throw new AdminApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Get detailed tenant information
 */
export async function getTenantDetails(tenantId: string): Promise<TenantDetailResponse> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/admin/tenants/${tenantId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return handleApiResponse<TenantDetailResponse>(response);
  } catch (error) {
    if (error instanceof AdminApiError) {
      throw error;
    }
    throw new AdminApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Get users in a tenant
 */
export async function getTenantUsers(tenantId: string): Promise<UserListItem[]> {
  try {
    const response = await apiFetch(
      `${API_BASE_URL}/admin/tenants/${tenantId}/users`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    return handleApiResponse<UserListItem[]>(response);
  } catch (error) {
    if (error instanceof AdminApiError) {
      throw error;
    }
    throw new AdminApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Get API tokens in a tenant
 */
export async function getTenantTokens(tenantId: string): Promise<ApiTokenListItem[]> {
  try {
    const response = await apiFetch(
      `${API_BASE_URL}/admin/tenants/${tenantId}/tokens`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    return handleApiResponse<ApiTokenListItem[]>(response);
  } catch (error) {
    if (error instanceof AdminApiError) {
      throw error;
    }
    throw new AdminApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Update tenant status (activate/suspend)
 */
export async function updateTenantStatus(
  tenantId: string,
  status: string,
  reason?: string
): Promise<SuccessResponse> {
  try {
    const body: UpdateTenantStatusRequest = { status };
    if (reason) body.reason = reason;

    const response = await apiFetch(
      `${API_BASE_URL}/admin/tenants/${tenantId}/status`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      }
    );

    return handleApiResponse<SuccessResponse>(response);
  } catch (error) {
    if (error instanceof AdminApiError) {
      throw error;
    }
    throw new AdminApiError('Network error. Please check your connection.', 0);
  }
}

// ============================================================================
// User Management
// ============================================================================

/**
 * Get all users across tenants with filters
 */
export async function getAllUsers(filters: UserFilters = {}): Promise<UserListResponse> {
  try {
    const params = new URLSearchParams();
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.page_size) params.append('page_size', filters.page_size.toString());
    if (filters.tenant_id) params.append('tenant_id', filters.tenant_id);
    if (filters.role_id) params.append('role_id', filters.role_id);
    if (filters.is_active !== undefined)
      params.append('is_active', filters.is_active.toString());
    if (filters.search) params.append('search', filters.search);

    const response = await apiFetch(
      `${API_BASE_URL}/admin/users?${params.toString()}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    return handleApiResponse<UserListResponse>(response);
  } catch (error) {
    if (error instanceof AdminApiError) {
      throw error;
    }
    throw new AdminApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Get detailed user information
 */
export async function getUserDetails(userId: string): Promise<UserDetailResponse> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/admin/users/${userId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return handleApiResponse<UserDetailResponse>(response);
  } catch (error) {
    if (error instanceof AdminApiError) {
      throw error;
    }
    throw new AdminApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Update user status (activate/deactivate)
 */
export async function updateUserStatus(
  userId: string,
  isActive: boolean,
  reason?: string
): Promise<SuccessResponse> {
  try {
    const body: UpdateUserStatusRequest = { is_active: isActive };
    if (reason) body.reason = reason;

    const response = await apiFetch(
      `${API_BASE_URL}/admin/users/${userId}/status`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      }
    );

    return handleApiResponse<SuccessResponse>(response);
  } catch (error) {
    if (error instanceof AdminApiError) {
      throw error;
    }
    throw new AdminApiError('Network error. Please check your connection.', 0);
  }
}

// ============================================================================
// Token Management
// ============================================================================

/**
 * Revoke an API token
 */
export async function revokeApiToken(
  tokenId: string,
  reason?: string
): Promise<SuccessResponse> {
  try {
    const body: RevokeApiTokenRequest = {};
    if (reason) body.reason = reason;

    const response = await apiFetch(`${API_BASE_URL}/admin/tokens/${tokenId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    return handleApiResponse<SuccessResponse>(response);
  } catch (error) {
    if (error instanceof AdminApiError) {
      throw error;
    }
    throw new AdminApiError('Network error. Please check your connection.', 0);
  }
}

// ============================================================================
// Analytics
// ============================================================================

/**
 * Get top tenants by activity
 */
export async function getTopTenants(
  limit: number = 10,
  days: number = 30
): Promise<TopTenantsResponse> {
  try {
    const params = new URLSearchParams({
      limit: limit.toString(),
      days: days.toString(),
    });

    const response = await apiFetch(
      `${API_BASE_URL}/admin/analytics/top-tenants?${params.toString()}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    return handleApiResponse<TopTenantsResponse>(response);
  } catch (error) {
    if (error instanceof AdminApiError) {
      throw error;
    }
    throw new AdminApiError('Network error. Please check your connection.', 0);
  }
}

// ============================================================================
// Platform Settings Management
// ============================================================================

/**
 * Get all platform settings
 */
export async function getPlatformSettings(
  category?: string
): Promise<PlatformSettingsListResponse> {
  try {
    const params = new URLSearchParams();
    if (category) params.append('category', category);

    const response = await apiFetch(
      `${API_BASE_URL}/admin/settings${params.toString() ? '?' + params.toString() : ''}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    return handleApiResponse<PlatformSettingsListResponse>(response);
  } catch (error) {
    if (error instanceof AdminApiError) {
      throw error;
    }
    throw new AdminApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Update a platform setting
 */
export async function updatePlatformSetting(
  key: string,
  value: unknown,
  description?: string
): Promise<PlatformSetting> {
  try {
    const body: UpdatePlatformSettingRequest = { value };
    if (description !== undefined) body.description = description;

    const response = await apiFetch(`${API_BASE_URL}/admin/settings/${key}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    return handleApiResponse<PlatformSetting>(response);
  } catch (error) {
    if (error instanceof AdminApiError) {
      throw error;
    }
    throw new AdminApiError('Network error. Please check your connection.', 0);
  }
}

// ============================================================================
// Credit Management
// ============================================================================

/**
 * Add credits to a tenant account
 */
export async function addTenantCredits(
  tenantId: string,
  amount: number,
  reason: string
): Promise<SuccessResponse> {
  try {
    const body: AddTenantCreditsRequest = { amount, reason };

    const response = await apiFetch(
      `${API_BASE_URL}/admin/tenants/${tenantId}/credits`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      }
    );

    return handleApiResponse<SuccessResponse>(response);
  } catch (error) {
    if (error instanceof AdminApiError) {
      throw error;
    }
    throw new AdminApiError('Network error. Please check your connection.', 0);
  }
}
