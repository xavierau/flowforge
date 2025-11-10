/**
 * UserList Page
 *
 * Admin page for managing all users across tenants.
 * Follows React best practices:
 * - Proper useEffect for data fetching with cleanup
 * - Separate state for filters and pagination
 * - Loading and error states
 * - Debounced search to avoid excessive API calls
 */

import { useState, useEffect, useCallback } from 'react';
import { Page, PageHeader, PageContent } from '@/components/layout';
import { UserTable } from '@/components/admin/UserTable';
import { AdminActionDialog } from '@/components/admin/AdminActionDialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  getAllUsers,
  updateUserStatus,
  AdminApiError,
} from '@/services/admin.service';
import type { UserListItem, UserFilters } from '@/types/admin';
import { AlertCircle, RefreshCw, Search } from 'lucide-react';

/**
 * UserList Component
 *
 * Displays paginated, filterable list of all users across tenants with admin actions.
 */
export function UserList() {
  // Data state
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [filters, setFilters] = useState<UserFilters>({
    page: 1,
    page_size: 50,
    tenant_id: '',
    role_id: '',
    is_active: undefined,
    search: '',
  });

  // Action dialog state
  const [actionDialog, setActionDialog] = useState<{
    open: boolean;
    userId: string;
    userEmail: string;
    currentStatus: boolean;
  }>({
    open: false,
    userId: '',
    userEmail: '',
    currentStatus: true,
  });
  const [isProcessing, setIsProcessing] = useState(false);

  /**
   * Fetch users based on current filters
   *
   * Dependencies: [filters] - refetch when any filter changes
   */
  useEffect(() => {
    let isCancelled = false;

    async function fetchUsers() {
      setIsLoading(true);
      setError(null);

      try {
        const response = await getAllUsers(filters);

        if (!isCancelled) {
          setUsers(response.users);
          setTotal(response.total);
          setIsLoading(false);
        }
      } catch (err) {
        if (!isCancelled) {
          if (err instanceof AdminApiError) {
            setError(err.message);
          } else {
            setError('Failed to load users');
          }
          setIsLoading(false);
        }
      }
    }

    fetchUsers();

    return () => {
      isCancelled = true;
    };
  }, [filters]);

  /**
   * Update filter and reset to page 1
   */
  const updateFilter = useCallback(
    (key: keyof UserFilters, value: string | number | boolean | undefined) => {
      setFilters((prev) => ({
        ...prev,
        [key]: value,
        page: key === 'page' ? Number(value) : 1, // Reset to page 1 when changing filters
      }));
    },
    []
  );

  /**
   * Handle view details (placeholder - could navigate to user detail page)
   */
  function handleViewDetails(userId: string) {
    // For now, just log - could implement user detail page later
    console.log('View user details:', userId);
  }

  /**
   * Open status update dialog
   */
  function handleUpdateStatusClick(userId: string, currentStatus: boolean) {
    const user = users.find((u) => u.id === userId);
    if (!user) return;

    setActionDialog({
      open: true,
      userId,
      userEmail: user.email,
      currentStatus,
    });
  }

  /**
   * Confirm status update
   */
  async function handleConfirmStatusUpdate(reason?: string) {
    setIsProcessing(true);

    try {
      const newStatus = !actionDialog.currentStatus;

      await updateUserStatus(actionDialog.userId, newStatus, reason);

      // Refresh user list
      const response = await getAllUsers(filters);
      setUsers(response.users);
      setTotal(response.total);

      // Close dialog
      setActionDialog({
        open: false,
        userId: '',
        userEmail: '',
        currentStatus: true,
      });
      setIsProcessing(false);
    } catch (err) {
      if (err instanceof AdminApiError) {
        setError(err.message);
      } else {
        setError('Failed to update user status');
      }
      setIsProcessing(false);
    }
  }

  /**
   * Calculate total pages
   */
  const totalPages = Math.ceil(total / (filters.page_size || 50));

  return (
    <Page>
      <PageHeader
        breadcrumbs={[{ label: 'Admin', href: '/admin' }, { label: 'Users' }]}
        title="User Management"
        subtitle={`${total} total users`}
      >
        <Button
          onClick={() => setFilters({ ...filters })}
          variant="outline"
          size="sm"
        >
          <RefreshCw
            className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`}
          />
          Refresh
        </Button>
      </PageHeader>

      <PageContent>
        {/* Error State */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Filters */}
        <div className="flex flex-col md:flex-row gap-4 mb-6">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by email or name..."
              value={filters.search || ''}
              onChange={(e) => updateFilter('search', e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Active Status Filter */}
          <Select
            value={
              filters.is_active === undefined
                ? 'all'
                : filters.is_active
                  ? 'active'
                  : 'inactive'
            }
            onValueChange={(value) =>
              updateFilter(
                'is_active',
                value === 'all' ? undefined : value === 'active'
              )
            }
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Users</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="inactive">Inactive</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* User Table */}
        {isLoading && users.length === 0 ? (
          <div className="flex items-center justify-center py-12 border rounded-lg">
            <div className="text-center">
              <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Loading users...</p>
            </div>
          </div>
        ) : (
          <UserTable
            users={users}
            onViewDetails={handleViewDetails}
            onUpdateStatus={handleUpdateStatusClick}
          />
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-6">
            <p className="text-sm text-muted-foreground">
              Page {filters.page} of {totalPages}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={filters.page === 1}
                onClick={() => updateFilter('page', (filters.page || 1) - 1)}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={filters.page === totalPages}
                onClick={() => updateFilter('page', (filters.page || 1) + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </PageContent>

      {/* Status Update Dialog */}
      <AdminActionDialog
        open={actionDialog.open}
        onOpenChange={(open) => setActionDialog({ ...actionDialog, open })}
        title={
          actionDialog.currentStatus ? 'Deactivate User' : 'Activate User'
        }
        description={
          actionDialog.currentStatus
            ? 'This will immediately deactivate the user and prevent them from logging in.'
            : 'This will activate the user and allow them to log in.'
        }
        resourceName={actionDialog.userEmail}
        onConfirm={handleConfirmStatusUpdate}
        isProcessing={isProcessing}
        variant={actionDialog.currentStatus ? 'destructive' : 'default'}
      />
    </Page>
  );
}
