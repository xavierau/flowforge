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
  UpdateAccountRequest,
  ChangePasswordRequest,
  NotificationPreferences,
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
 * Get all invitations for the current tenant
 */
export async function getInvitations(): Promise<UserInvitation[]> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/invitations`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return handleApiResponse<UserInvitation[]>(response);
  } catch (error) {
    if (error instanceof UserApiError) {
      throw error;
    }
    throw new UserApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Create a new user invitation
 */
export async function createInvitation(
  data: CreateInvitationRequest
): Promise<UserInvitation> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/invitations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    return handleApiResponse<UserInvitation>(response);
  } catch (error) {
    if (error instanceof UserApiError) {
      throw error;
    }
    throw new UserApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Resend an invitation
 */
export async function resendInvitation(invitationId: string): Promise<void> {
  try {
    const response = await apiFetch(
      `${API_BASE_URL}/invitations/${invitationId}/resend`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    await handleApiResponse<void>(response);
  } catch (error) {
    if (error instanceof UserApiError) {
      throw error;
    }
    throw new UserApiError('Network error. Please check your connection.', 0);
  }
}

/**
 * Cancel an invitation
 */
export async function cancelInvitation(invitationId: string): Promise<void> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/invitations/${invitationId}`, {
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
