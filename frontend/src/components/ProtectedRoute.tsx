/**
 * ProtectedRoute component - Requires authentication and optional role check
 *
 * Redirects unauthenticated users to the login page
 * Redirects users without required role to dashboard
 */

import { useEffect, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { isAuthenticated, hasRole } from '@/services/auth.service';

interface ProtectedRouteProps {
  children: ReactNode;
  /**
   * Optional required role for access
   * If provided, user must have this exact role
   */
  requiredRole?: string;
}

export function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  const navigate = useNavigate();

  /**
   * Check authentication and role on mount and when dependencies change
   * Dependencies: [navigate, requiredRole]
   */
  useEffect(() => {
    if (!isAuthenticated()) {
      // Redirect to login if not authenticated
      navigate('/login', { replace: true });
      return;
    }

    // If a specific role is required, check if user has it
    if (requiredRole && !hasRole(requiredRole)) {
      // Redirect to dashboard if user doesn't have required role
      navigate('/dashboard', { replace: true });
    }
  }, [navigate, requiredRole]);

  // Only render children if authenticated
  if (!isAuthenticated()) {
    return null;
  }

  // Check role requirement
  if (requiredRole && !hasRole(requiredRole)) {
    return null;
  }

  return <>{children}</>;
}
