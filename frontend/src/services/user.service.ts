/**
 * User Management Service
 *
 * Provides methods for user profile and invitation management.
 * Following SOLID principles:
 * - Single Responsibility: Handles only user-related API calls
 * - Open/Closed: Easy to extend with new user operations
 * - Interface Segregation: Focused interface for user operations
 *
 * Uses centralized API wrapper from lib/api.ts for:
 * - Automatic auth header injection
 * - 401 interceptor with auto-redirect to login
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

const API_BASE_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1`;

/**
 * Custom error class for user API errors
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
 * Centralized fetch wrapper with 401 interceptor
 * Automatically adds Authorization header and handles auth errors
 */
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

  // Intercept 401 - clear tokens and redirect to login
  if (response.status === 401) {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
    throw new UserApiError('Unauthorized - Please log in again', 401);
  }

  return response;
}

/**
 * Handle API response errors
 */
async function handleApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const contentType = response.headers.get('content-type');
    let errorData: unknown;

    if (contentType?.includes('application/json')) {
      errorData = await response.json();
    }

    const message =
      errorData &&
      typeof errorData === 'object' &&
      'detail' in errorData &&
      typeof errorData.detail === 'string'
        ? errorData.detail
        : 'An error occurred';

    throw new UserApiError(message, response.status, errorData);
  }

  return response.json();
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
