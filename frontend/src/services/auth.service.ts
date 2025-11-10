/**
 * Authentication API Service
 *
 * Provides methods for user authentication, following SOLID principles:
 * - Single Responsibility: Handles only auth-related API calls
 * - Open/Closed: Easy to extend with new auth methods
 * - Interface Segregation: Focused interface for auth operations
 */

import type {
  LoginRequest,
  LoginResponse,
  SignupRequest,
  SignupResponse,
  AuthError,
  ValidationError,
} from '@/types/auth';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export class AuthApiError extends Error {
  statusCode: number;
  details?: AuthError | ValidationError;

  constructor(
    message: string,
    statusCode: number,
    details?: AuthError | ValidationError
  ) {
    super(message);
    this.name = 'AuthApiError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

/**
 * Handles API response errors with proper type checking
 */
async function handleApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const contentType = response.headers.get('content-type');
    let errorData: AuthError | ValidationError | undefined;

    if (contentType?.includes('application/json')) {
      errorData = await response.json();
    }

    // Handle specific HTTP status codes
    if (response.status === 409) {
      throw new AuthApiError('Email already registered', 409, errorData);
    }

    if (response.status === 401) {
      throw new AuthApiError('Invalid email or password', 401, errorData);
    }

    if (response.status === 422) {
      throw new AuthApiError('Validation error', 422, errorData);
    }

    // Generic error
    const message =
      errorData && 'detail' in errorData && typeof errorData.detail === 'string'
        ? errorData.detail
        : 'An error occurred';

    throw new AuthApiError(message, response.status, errorData);
  }

  return response.json();
}

/**
 * Login with email and password
 */
export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(credentials),
    });

    return handleApiResponse<LoginResponse>(response);
  } catch (error) {
    if (error instanceof AuthApiError) {
      throw error;
    }

    // Network or other errors
    throw new AuthApiError(
      'Network error. Please check your connection.',
      0
    );
  }
}

/**
 * Register new user account
 */
export async function signup(data: SignupRequest): Promise<SignupResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    return handleApiResponse<SignupResponse>(response);
  } catch (error) {
    if (error instanceof AuthApiError) {
      throw error;
    }

    // Network or other errors
    throw new AuthApiError(
      'Network error. Please check your connection.',
      0
    );
  }
}

/**
 * Store authentication tokens in localStorage
 */
export function storeTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem('access_token', accessToken);
  localStorage.setItem('refresh_token', refreshToken);
}

/**
 * Retrieve access token from localStorage
 */
export function getAccessToken(): string | null {
  return localStorage.getItem('access_token');
}

/**
 * Clear authentication tokens from localStorage
 */
export function clearTokens(): void {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return getAccessToken() !== null;
}

/**
 * Decode JWT token and extract payload
 */
function decodeJWT(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;

    const payload = parts[1];
    const decoded = atob(payload);
    return JSON.parse(decoded);
  } catch {
    return null;
  }
}

/**
 * Get current user's role from JWT token
 */
export function getUserRole(): string | null {
  const token = getAccessToken();
  if (!token) return null;

  const payload = decodeJWT(token);
  if (!payload) return null;

  // JWT payload contains role_name
  return (payload.role_name as string) || null;
}

/**
 * Check if current user has a specific role
 */
export function hasRole(requiredRole: string): boolean {
  const userRole = getUserRole();
  return userRole === requiredRole;
}
