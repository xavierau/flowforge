/**
 * User Management Service
 *
 * Provides methods for user profile and invitation management.
 * Following SOLID principles:
 * - Single Responsibility: Handles only user-related API calls
 * - Open/Closed: Easy to extend with new user operations
 * - Interface Segregation: Focused interface for user operations
 *
 * Uses centralized API client from lib/api-client.ts for:
 * - Automatic token refresh on 401 responses
 * - Auth header injection
 * - Consistent error handling
 */

import type {
  UserProfile,
  UserInvitation,
  CreateInvitationRequest,
  CreateInvitationApiRequest,
  CreateInvitationResponse,
  UpdateAccountRequest,
  ChangePasswordRequest,
  NotificationPreferences,
  RoleInfo,
  UserRole,
} from '@/types/profile';
import { apiFetch, API_BASE_URL, handleApiResponse } from '@/lib/api-client';

/**
 * Custom error class for user API errors
 * @deprecated Use ApiClientError from api-client.ts
 */
export class UserApiError extends Error {
  statusCode: number;
  details?: unknown;

  constructor(message: string, statusCode: number, details?: unknown) {
    super(message);
    this.name = 'UserApiError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

/**
 * Get current user profile
 */
export async function getCurrentUser(): Promise<UserProfile> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/users/profile`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return handleApiResponse<UserProfile>(response);
  } catch (error) {
    if (error instanceof UserApiError) {
      throw error;
    }
    throw new UserApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Update user account information
 */
export async function updateAccount(
  data: UpdateAccountRequest
): Promise<UserProfile> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/users/me`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    return handleApiResponse<UserProfile>(response);
  } catch (error) {
    if (error instanceof UserApiError) {
      throw error;
    }
    throw new UserApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Change user password
 */
export async function changePassword(
  data: ChangePasswordRequest
): Promise<void> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/users/me/password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    await handleApiResponse<void>(response);
  } catch (error) {
    if (error instanceof UserApiError) {
      throw error;
    }
    throw new UserApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Get notification preferences
 */
export async function getNotificationPreferences(): Promise<NotificationPreferences> {
  try {
    const response = await apiFetch(
      `${API_BASE_URL}/users/notifications/preferences`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    return handleApiResponse<NotificationPreferences>(response);
  } catch (error) {
    if (error instanceof UserApiError) {
      throw error;
    }
    throw new UserApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Update notification preferences
 */
export async function updateNotificationPreferences(
  preferences: NotificationPreferences
): Promise<NotificationPreferences> {
  try {
    const response = await apiFetch(
      `${API_BASE_URL}/users/notifications/preferences`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(preferences),
      }
    );

    return handleApiResponse<NotificationPreferences>(response);
  } catch (error) {
    if (error instanceof UserApiError) {
      throw error;
    }
    throw new UserApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Delete user account
 */
export async function deleteAccount(): Promise<void> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/users/me`, {
      method: 'DELETE',
    });

    await handleApiResponse<void>(response);
  } catch (error) {
    if (error instanceof UserApiError) {
      throw error;
    }
    throw new UserApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Role name to ID mapping (cached)
 * Maps frontend role names ('admin', 'user', 'viewer') to backend role IDs
 */
let cachedRoles: RoleInfo[] | null = null;

/**
 * Hardcoded role mapping as fallback when roles endpoint is unavailable
 * These values match the backend seed data role names
 */
const ROLE_NAME_MAP: Record<UserRole, string> = {
  admin: 'tenant_admin',
  user: 'member',
  viewer: 'viewer',
};

/**
 * Get available roles for the tenant
 * Fetches from dedicated /roles endpoint. Results are cached for performance.
 */
export async function getRoles(): Promise<RoleInfo[]> {
  if (cachedRoles) {
    return cachedRoles;
  }

  try {
    const response = await apiFetch(`${API_BASE_URL}/roles`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await handleApiResponse<{ roles: RoleInfo[] }>(response);
    cachedRoles = data.roles;
    return cachedRoles;
  } catch (error) {
    // Return empty array if fetching fails - component will use hardcoded mapping
    console.warn('Failed to fetch roles, will use hardcoded mapping:', error);
    return [];
  }
}

/**
 * Clear cached roles (call when tenant context changes)
 */
export function clearRolesCache(): void {
  cachedRoles = null;
}

/**
 * Get role ID from role name
 * First tries to find from fetched roles, then falls back to hardcoded mapping
 */
export async function getRoleIdByName(roleName: UserRole): Promise<string | null> {
  const roles = await getRoles();

  // Map frontend role name to backend role name
  const backendRoleName = ROLE_NAME_MAP[roleName];

  // Try to find role by name
  const role = roles.find(
    (r) => r.name === backendRoleName || r.name === roleName
  );

  if (role) {
    return role.id;
  }

  // No role found - return null, let caller handle
  console.warn(`Role not found for name: ${roleName} (mapped to: ${backendRoleName})`);
  return null;
}

/**
 * Response type for invitation list endpoint
 */
interface InvitationListResponse {
  invitations: UserInvitation[];
  total: number;
}

/**
 * Get all pending invitations for the current tenant
 * Uses: GET /api/v1/users/invitations
 */
export async function getInvitations(): Promise<UserInvitation[]> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/users/invitations`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await handleApiResponse<InvitationListResponse>(response);
    return data.invitations;
  } catch (error) {
    if (error instanceof UserApiError) {
      throw error;
    }
    throw new UserApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Create a new user invitation
 * Uses: POST /api/v1/users/invite
 *
 * This function handles role name to ID mapping internally.
 * The component passes a role name, this function converts it to role_id.
 */
export async function createInvitation(
  data: CreateInvitationRequest
): Promise<UserInvitation> {
  try {
    // Get role ID from role name
    const roleId = await getRoleIdByName(data.role);

    if (!roleId) {
      throw new UserApiError(
        `Invalid role: ${data.role}. Please contact support.`,
        400
      );
    }

    // Build API request with role_id
    const apiRequest: CreateInvitationApiRequest = {
      email: data.email,
      role_id: roleId,
    };

    const response = await apiFetch(`${API_BASE_URL}/users/invite`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(apiRequest),
    });

    // Backend returns CreateInvitationResponse, we need to transform to UserInvitation
    const invitationResponse = await handleApiResponse<CreateInvitationResponse>(response);

    // Transform response to UserInvitation format for UI
    // Note: The actual invitation is created on the backend, we return a temporary UI representation
    const invitation: UserInvitation = {
      id: invitationResponse.invitation_token, // Use token as temporary ID
      email: invitationResponse.email,
      role: data.role, // Use the role name passed from UI
      invited_by: '', // Will be filled when fetching from list
      created_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days from now
      status: 'pending',
    };

    return invitation;
  } catch (error) {
    if (error instanceof UserApiError) {
      throw error;
    }
    throw new UserApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Resend an invitation email
 * Uses: POST /api/v1/users/{user_id}/resend-invitation
 *
 * Note: The invitation ID is actually the user ID on the backend since
 * invitations create a user record with is_active=false
 */
export async function resendInvitation(invitationId: string): Promise<void> {
  try {
    const response = await apiFetch(
      `${API_BASE_URL}/users/${invitationId}/resend-invitation`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    await handleApiResponse<{ message: string }>(response);
  } catch (error) {
    if (error instanceof UserApiError) {
      throw error;
    }
    throw new UserApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Cancel an invitation (delete the invited user)
 * Uses: DELETE /api/v1/users/{user_id}
 *
 * Note: Cancelling an invitation actually deletes the user record that
 * was created with is_active=false during invitation
 */
export async function cancelInvitation(invitationId: string): Promise<void> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/users/${invitationId}`, {
      method: 'DELETE',
    });

    await handleApiResponse<{ message: string }>(response);
  } catch (error) {
    if (error instanceof UserApiError) {
      throw error;
    }
    throw new UserApiError('Network error. Please check your connection.', 0);
  }
}
