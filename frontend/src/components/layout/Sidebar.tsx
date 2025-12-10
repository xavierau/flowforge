/**
 * Sidebar Component
 *
 * Collapseable navigation sidebar for authenticated layout.
 * Persists collapse state to localStorage for user preference.
 *
 * Design Principles:
 * - Single Responsibility: Handles only sidebar navigation
 * - Composability: Uses React Router's NavLink for routing
 * - State Management: Collapse state lifted to parent component
 * - No useEffect anti-patterns: State synchronization handled properly
 */

import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Settings,
  ChevronLeft,
  Database,
  Briefcase,
  CreditCard,
  Key,
  KeyRound,
  Shield,
  Building,
  Users,
  Workflow,
  ClipboardCheck,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { hasRole } from '@/services/auth.service';

interface NavItem {
  name: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isMobileOpen: boolean;
  onMobileClose: () => void;
}

const navItems: NavItem[] = [
  {
    name: 'Dashboard',
    path: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    name: 'Schemas',
    path: '/schemas',
    icon: Database,
  },
  {
    name: 'Jobs',
    path: '/jobs',
    icon: Briefcase,
  },
  {
    name: 'Reviews',
    path: '/reviews',
    icon: ClipboardCheck,
  },
  {
    name: 'Workflows',
    path: '/workflows',
    icon: Workflow,
  },
  {
    name: 'Credentials',
    path: '/credentials',
    icon: KeyRound,
  },
  {
    name: 'API Tokens',
    path: '/tokens',
    icon: Key,
  },
  {
    name: 'Billing',
    path: '/billing',
    icon: CreditCard,
  },
  {
    name: 'Settings',
    path: '/settings',
    icon: Settings,
  },
];

const adminNavItems: NavItem[] = [
  {
    name: 'Admin Dashboard',
    path: '/admin',
    icon: Shield,
  },
  {
    name: 'Tenants',
    path: '/admin/tenants',
    icon: Building,
  },
  {
    name: 'Users',
    path: '/admin/users',
    icon: Users,
  },
  {
    name: 'Platform Settings',
    path: '/admin/settings',
    icon: Settings,
  },
];

export function Sidebar({
  isCollapsed,
  onToggleCollapse,
  isMobileOpen,
  onMobileClose,
}: SidebarProps) {
  const isAdmin = hasRole('platform_admin');

  return (
    <>
      {/* Mobile Overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={onMobileClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-50 h-full bg-white border-r transition-all duration-300',
          'md:static md:z-auto md:translate-x-0',
          isCollapsed ? 'w-20' : 'w-[280px]',
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Sidebar Header */}
        <div className="flex h-16 items-center justify-between px-4 border-b">
          {!isCollapsed && (
            <span className="text-lg font-semibold text-gray-900">
              Navigation
            </span>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleCollapse}
            className="hidden md:flex"
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <ChevronLeft
              className={cn(
                'h-5 w-5 transition-transform duration-300',
                isCollapsed && 'rotate-180'
              )}
            />
          </Button>
        </div>

        {/* Navigation Items */}
        <nav className="flex flex-col gap-1 p-4">
          {/* Regular Navigation */}
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={onMobileClose}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 transition-colors',
                  'hover:bg-gray-100',
                  isActive
                    ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                    : 'text-gray-700',
                  isCollapsed && 'justify-center px-0'
                )
              }
            >
              {({ isActive }) => (
                <>
                  <item.icon
                    className={cn(
                      'h-5 w-5 flex-shrink-0',
                      isActive ? 'text-primary-foreground' : 'text-gray-500'
                    )}
                  />
                  {!isCollapsed && (
                    <span className="text-sm font-medium">{item.name}</span>
                  )}
                </>
              )}
            </NavLink>
          ))}

          {/* Admin Section */}
          {isAdmin && (
            <>
              {/* Divider */}
              {!isCollapsed && (
                <div className="my-4 border-t border-gray-200">
                  <div className="mt-4 mb-2 px-3">
                    <span className="text-xs font-semibold text-gray-500 uppercase">
                      Administration
                    </span>
                  </div>
                </div>
              )}
              {isCollapsed && <div className="my-4 border-t border-gray-200" />}

              {/* Admin Nav Items */}
              {adminNavItems.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={onMobileClose}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 rounded-lg px-3 py-2 transition-colors',
                      'hover:bg-gray-100',
                      isActive
                        ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                        : 'text-gray-700',
                      isCollapsed && 'justify-center px-0'
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      <item.icon
                        className={cn(
                          'h-5 w-5 flex-shrink-0',
                          isActive ? 'text-primary-foreground' : 'text-gray-500'
                        )}
                      />
                      {!isCollapsed && (
                        <span className="text-sm font-medium">{item.name}</span>
                      )}
                    </>
                  )}
                </NavLink>
              ))}
            </>
          )}
        </nav>
      </aside>
    </>
  );
}
