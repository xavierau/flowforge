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
 * - Proper useEffect usage: Only for reading/writing localStorage
 * - No prop drilling: Direct state passing to child components
 *
 * State Management:
 * - Sidebar collapse state persisted to localStorage
 * - Mobile sidebar state managed locally (no persistence needed)
 * - User data currently mocked (will be replaced with API call)
 */

import { useState } from 'react';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';
import { getMockUser } from '@/types/user';

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

  // User data (currently mocked)
  // TODO: Replace with actual user data from API
  const user = getMockUser();

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
