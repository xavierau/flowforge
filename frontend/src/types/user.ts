/**
 * User Type Definitions
 *
 * Defines the user data structure for authenticated users.
 * Currently using mock data, will be replaced with API integration.
 */

export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
}

/**
 * Mock user for development
 * TODO: Replace with actual user data from API
 */
export const getMockUser = (): User => ({
  id: '1',
  email: 'user@example.com',
  name: 'John Doe',
  avatar: undefined,
});
