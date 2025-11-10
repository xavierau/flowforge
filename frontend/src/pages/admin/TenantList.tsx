/**
 * TenantList Page
 *
 * Admin page for managing all tenants.
 * Follows React best practices:
 * - Proper useEffect for data fetching with cleanup
 * - Separate state for filters and pagination
 * - Loading and error states
 * - Debounced search to avoid excessive API calls
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Page, PageHeader, PageContent } from '@/components/layout';
import { TenantTable } from '@/components/admin/TenantTable';
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
  getTenants,
  updateTenantStatus,
  AdminApiError,
} from '@/services/admin.service';
import type { TenantListItem, TenantFilters } from '@/types/admin';
import { AlertCircle, RefreshCw, Search } from 'lucide-react';

/**
 * TenantList Component
 *
 * Displays paginated, filterable list of all tenants with admin actions.
 */
export function TenantList() {
  const navigate = useNavigate();

  // Data state
  const [tenants, setTenants] = useState<TenantListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [filters, setFilters] = useState<TenantFilters>({
    page: 1,
    page_size: 50,
    status: '',
    plan: '',
    search: '',
  });

  // Action dialog state
  const [actionDialog, setActionDialog] = useState<{
    open: boolean;
    tenantId: string;
    tenantName: string;
    currentStatus: string;
  }>({
    open: false,
    tenantId: '',
    tenantName: '',
    currentStatus: '',
  });
  const [isProcessing, setIsProcessing] = useState(false);

  /**
   * Fetch tenants based on current filters
   *
   * Dependencies: [filters] - refetch when any filter changes
   */
  useEffect(() => {
    let isCancelled = false;

    async function fetchTenants() {
      setIsLoading(true);
      setError(null);

      try {
        const response = await getTenants(filters);

        if (!isCancelled) {
          setTenants(response.tenants);
          setTotal(response.total);
          setIsLoading(false);
        }
      } catch (err) {
        if (!isCancelled) {
          if (err instanceof AdminApiError) {
            setError(err.message);
          } else {
            setError('Failed to load tenants');
          }
          setIsLoading(false);
        }
      }
    }

    fetchTenants();

    return () => {
      isCancelled = true;
    };
  }, [filters]);

  /**
   * Update filter and reset to page 1
   */
  const updateFilter = useCallback((key: keyof TenantFilters, value: string | number) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
      page: key === 'page' ? Number(value) : 1, // Reset to page 1 when changing filters
    }));
  }, []);

  /**
   * Handle view details navigation
   */
  function handleViewDetails(tenantId: string) {
    navigate(`/admin/tenants/${tenantId}`);
  }

  /**
   * Open status update dialog
   */
  function handleUpdateStatusClick(tenantId: string, currentStatus: string) {
    const tenant = tenants.find((t) => t.id === tenantId);
    if (!tenant) return;

    setActionDialog({
      open: true,
      tenantId,
      tenantName: tenant.name,
      currentStatus,
    });
  }

  /**
   * Confirm status update
   */
  async function handleConfirmStatusUpdate(reason?: string) {
    setIsProcessing(true);

    try {
      const newStatus =
        actionDialog.currentStatus === 'active' ? 'suspended' : 'active';

      await updateTenantStatus(actionDialog.tenantId, newStatus, reason);

      // Refresh tenant list
      const response = await getTenants(filters);
      setTenants(response.tenants);
      setTotal(response.total);

      // Close dialog
      setActionDialog({ open: false, tenantId: '', tenantName: '', currentStatus: '' });
      setIsProcessing(false);
    } catch (err) {
      if (err instanceof AdminApiError) {
        setError(err.message);
      } else {
        setError('Failed to update tenant status');
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
        breadcrumbs={[
          { label: 'Admin', href: '/admin' },
          { label: 'Tenants' },
        ]}
        title="Tenant Management"
        subtitle={`${total} total tenants`}
      >
        <Button
          onClick={() => setFilters({ ...filters })}
          variant="outline"
          size="sm"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
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
              placeholder="Search by name or slug..."
              value={filters.search || ''}
              onChange={(e) => updateFilter('search', e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Status Filter */}
          <Select
            value={filters.status || 'all'}
            onValueChange={(value) =>
              updateFilter('status', value === 'all' ? '' : value)
            }
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="suspended">Suspended</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>

          {/* Plan Filter */}
          <Select
            value={filters.plan || 'all'}
            onValueChange={(value) =>
              updateFilter('plan', value === 'all' ? '' : value)
            }
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by plan" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Plans</SelectItem>
              <SelectItem value="free">Free</SelectItem>
              <SelectItem value="starter">Starter</SelectItem>
              <SelectItem value="professional">Professional</SelectItem>
              <SelectItem value="enterprise">Enterprise</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Tenant Table */}
        {isLoading && tenants.length === 0 ? (
          <div className="flex items-center justify-center py-12 border rounded-lg">
            <div className="text-center">
              <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Loading tenants...</p>
            </div>
          </div>
        ) : (
          <TenantTable
            tenants={tenants}
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
        onOpenChange={(open) =>
          setActionDialog({ ...actionDialog, open })
        }
        title={
          actionDialog.currentStatus === 'active'
            ? 'Suspend Tenant'
            : 'Activate Tenant'
        }
        description={
          actionDialog.currentStatus === 'active'
            ? 'This will immediately suspend the tenant and prevent all users from accessing the system.'
            : 'This will activate the tenant and allow users to access the system.'
        }
        resourceName={actionDialog.tenantName}
        onConfirm={handleConfirmStatusUpdate}
        isProcessing={isProcessing}
        variant={actionDialog.currentStatus === 'active' ? 'destructive' : 'default'}
      />
    </Page>
  );
}
