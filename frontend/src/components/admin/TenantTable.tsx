/**
 * TenantTable Component
 *
 * Displays tenant list in a table format with actions.
 * Follows React best practices:
 * - Single responsibility (tenant display)
 * - Composition over complexity
 * - Proper event handling with callbacks
 * - Accessible table markup
 */

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { TenantListItem } from '@/types/admin';
import { Eye, Ban, CheckCircle, Coins } from 'lucide-react';

interface TenantTableProps {
  /**
   * List of tenants to display
   */
  tenants: TenantListItem[];

  /**
   * Callback when viewing tenant details
   */
  onViewDetails: (tenantId: string) => void;

  /**
   * Callback when updating tenant status
   */
  onUpdateStatus: (tenantId: string, currentStatus: string) => void;

  /**
   * Callback when adding credits to a tenant
   */
  onAddCredits: (tenantId: string, tenantName: string, currentBalance: number) => void;

  /**
   * Whether the table is loading
   */
  isLoading?: boolean;
}

/**
 * Get badge variant based on tenant status
 */
function getStatusBadge(status: string) {
  switch (status.toLowerCase()) {
    case 'active':
      return <Badge variant="default">Active</Badge>;
    case 'suspended':
      return <Badge variant="destructive">Suspended</Badge>;
    case 'cancelled':
      return <Badge variant="outline">Cancelled</Badge>;
    default:
      return <Badge variant="secondary">{status}</Badge>;
  }
}

/**
 * Format date for display
 */
function formatDate(dateString: string | null): string {
  if (!dateString) return 'Never';
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * TenantTable Component
 *
 * Displays a sortable, actionable table of tenants.
 *
 * @example
 * ```tsx
 * <TenantTable
 *   tenants={tenantList}
 *   onViewDetails={handleViewDetails}
 *   onUpdateStatus={handleUpdateStatus}
 * />
 * ```
 */
export function TenantTable({
  tenants,
  onViewDetails,
  onUpdateStatus,
  onAddCredits,
  isLoading = false,
}: TenantTableProps) {
  if (tenants.length === 0 && !isLoading) {
    return (
      <div className="text-center py-12 border rounded-lg">
        <p className="text-muted-foreground">No tenants found</p>
      </div>
    );
  }

  return (
    <div className="border rounded-lg">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Plan</TableHead>
            <TableHead className="text-right">Users</TableHead>
            <TableHead className="text-right">Jobs</TableHead>
            <TableHead className="text-right">Credits</TableHead>
            <TableHead>Created</TableHead>
            <TableHead>Last Activity</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {tenants.map((tenant) => (
            <TableRow key={tenant.id}>
              <TableCell className="font-medium">
                <div>
                  <div>{tenant.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {tenant.slug}
                  </div>
                </div>
              </TableCell>
              <TableCell>{getStatusBadge(tenant.status)}</TableCell>
              <TableCell>
                <Badge variant="outline">{tenant.subscription_plan}</Badge>
              </TableCell>
              <TableCell className="text-right">{tenant.user_count}</TableCell>
              <TableCell className="text-right">
                <div>
                  <div>{tenant.job_count}</div>
                  <div className="text-xs text-muted-foreground">
                    {tenant.completed_jobs} completed
                  </div>
                </div>
              </TableCell>
              <TableCell className="text-right">
                <div>
                  <div className="font-medium">
                    {new Intl.NumberFormat('en-US').format(
                      tenant.credit_balance
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {new Intl.NumberFormat('en-US').format(
                      tenant.total_credits_consumed
                    )}{' '}
                    used
                  </div>
                </div>
              </TableCell>
              <TableCell>{formatDate(tenant.created_at)}</TableCell>
              <TableCell>{formatDate(tenant.last_activity)}</TableCell>
              <TableCell className="text-right">
                <div className="flex items-center justify-end gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onViewDetails(tenant.id)}
                  >
                    <Eye className="h-4 w-4 mr-1" />
                    View
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onAddCredits(tenant.id, tenant.name, tenant.credit_balance)}
                  >
                    <Coins className="h-4 w-4 mr-1" />
                    Add Credits
                  </Button>
                  <Button
                    variant={
                      tenant.status === 'active' ? 'destructive' : 'default'
                    }
                    size="sm"
                    onClick={() => onUpdateStatus(tenant.id, tenant.status)}
                  >
                    {tenant.status === 'active' ? (
                      <>
                        <Ban className="h-4 w-4 mr-1" />
                        Suspend
                      </>
                    ) : (
                      <>
                        <CheckCircle className="h-4 w-4 mr-1" />
                        Activate
                      </>
                    )}
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
