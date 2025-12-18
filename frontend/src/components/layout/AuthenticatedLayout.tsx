/**
 * AuthenticatedLayout Component
 *
 * Main layout wrapper for authenticated pages in the SaaS application.
 * Composes Navbar and Sidebar components with proper state management.
 *
 * Design Principles:
 * - Composition: Combines Navbar and Sidebar components
 * - Single Responsibility: Manages layout structure and sidebar state
 * - State Management: Handles sidebar collapse/mobile state in one place
 * - Proper useEffect usage: For reading localStorage and fetching user data
 * - No prop drilling: Direct state passing to child components
 *
 * State Management:
 * - Sidebar collapse state persisted to localStorage
 * - Mobile sidebar state managed locally (no persistence needed)
 * - User data fetched from API on mount
 */

import { useState, useEffect } from 'react';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';
import { getCurrentUser } from '@/services/user.service';
import type { User } from '@/types/user';

interface AuthenticatedLayoutProps {
  children: React.ReactNode;
}

const SIDEBAR_COLLAPSE_KEY = 'sidebar-collapsed';

/**
 * Read sidebar collapse preference from localStorage
 * Returns false (expanded) by default
 */
function getInitialCollapseState(): boolean {
  try {
    const stored = localStorage.getItem(SIDEBAR_COLLAPSE_KEY);
    return stored === 'true';
  } catch {
    return false;
  }
}

/**
 * Save sidebar collapse preference to localStorage
 */
function saveCollapseState(isCollapsed: boolean): void {
  try {
    localStorage.setItem(SIDEBAR_COLLAPSE_KEY, String(isCollapsed));
  } catch {
    // Silently fail if localStorage is unavailable
  }
}

export function AuthenticatedLayout({ children }: AuthenticatedLayoutProps) {
  // Sidebar collapse state (persisted to localStorage)
  const [isCollapsed, setIsCollapsed] = useState(getInitialCollapseState);

  // Mobile sidebar state (not persisted)
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  // User data fetched from API
  const [user, setUser] = useState<User | null>(null);
  const [isLoadingUser, setIsLoadingUser] = useState(true);

  // Fetch user data on mount
  useEffect(() => {
    let isMounted = true;

    async function fetchUser() {
      try {
        const userProfile = await getCurrentUser();
        if (isMounted) {
          // Map UserProfile to User type expected by Navbar
          setUser({
            id: userProfile.id,
            email: userProfile.email,
            name: userProfile.full_name,
            avatar: userProfile.avatar_url,
          });
        }
      } catch (error) {
        // Error handling is done in apiFetch (redirects to login on 401)
        console.error('Failed to fetch user:', error);
      } finally {
        if (isMounted) {
          setIsLoadingUser(false);
        }
      }
    }

    fetchUser();

    return () => {
      isMounted = false;
    };
  }, []);

  /**
   * Toggle sidebar collapse and persist preference
   * No useEffect needed - state update triggers re-render
   * Persistence happens synchronously in the handler
   */
  const handleToggleCollapse = () => {
    setIsCollapsed((prev) => {
      const newState = !prev;
      saveCollapseState(newState);
      return newState;
    });
  };

  /**
   * Toggle mobile sidebar
   * Mobile state is ephemeral, no persistence needed
   */
  const handleMobileMenuToggle = () => {
    setIsMobileOpen((prev) => !prev);
  };

  /**
   * Close mobile sidebar
   * Called when clicking overlay or navigation item
   */
  const handleMobileClose = () => {
    setIsMobileOpen(false);
  };

  // Show loading state while fetching user
  if (isLoadingUser || !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Sidebar */}
      <Sidebar
        isCollapsed={isCollapsed}
        onToggleCollapse={handleToggleCollapse}
        isMobileOpen={isMobileOpen}
        onMobileClose={handleMobileClose}
      />

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Navbar */}
        <Navbar user={user} onMobileMenuToggle={handleMobileMenuToggle} />

        {/* Page Content */}
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
