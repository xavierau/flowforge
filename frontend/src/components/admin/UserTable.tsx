/**
 * UserTable Component
 *
 * Displays user list in a table format with actions.
 * Follows React best practices:
 * - Single responsibility (user display)
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
import type { UserListItem } from '@/types/admin';
import { Eye, UserX, UserCheck } from 'lucide-react';

interface UserTableProps {
  /**
   * List of users to display
   */
  users: UserListItem[];

  /**
   * Callback when viewing user details
   */
  onViewDetails: (userId: string) => void;

  /**
   * Callback when updating user status
   */
  onUpdateStatus: (userId: string, currentStatus: boolean) => void;

  /**
   * Whether the table is loading
   */
  isLoading?: boolean;
}

/**
 * Get badge variant based on user status
 */
function getStatusBadge(isActive: boolean, isVerified: boolean) {
  if (!isActive) {
    return <Badge variant="destructive">Inactive</Badge>;
  }
  if (!isVerified) {
    return <Badge variant="secondary">Unverified</Badge>;
  }
  return <Badge variant="default">Active</Badge>;
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
 * UserTable Component
 *
 * Displays a sortable, actionable table of users.
 *
 * @example
 * ```tsx
 * <UserTable
 *   users={userList}
 *   onViewDetails={handleViewDetails}
 *   onUpdateStatus={handleUpdateStatus}
 * />
 * ```
 */
export function UserTable({
  users,
  onViewDetails,
  onUpdateStatus,
  isLoading = false,
}: UserTableProps) {
  if (users.length === 0 && !isLoading) {
    return (
      <div className="text-center py-12 border rounded-lg">
        <p className="text-muted-foreground">No users found</p>
      </div>
    );
  }

  return (
    <div className="border rounded-lg">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Email</TableHead>
            <TableHead>Full Name</TableHead>
            <TableHead>Tenant</TableHead>
            <TableHead>Role</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Last Login</TableHead>
            <TableHead>Created</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {users.map((user) => (
            <TableRow key={user.id}>
              <TableCell className="font-medium">{user.email}</TableCell>
              <TableCell>{user.full_name || '-'}</TableCell>
              <TableCell>
                <div>
                  <div>{user.tenant_name}</div>
                  <Badge
                    variant={
                      user.tenant_status === 'active' ? 'default' : 'destructive'
                    }
                    className="text-xs mt-1"
                  >
                    {user.tenant_status}
                  </Badge>
                </div>
              </TableCell>
              <TableCell>
                <Badge variant="outline">{user.role_display_name}</Badge>
              </TableCell>
              <TableCell>
                {getStatusBadge(user.is_active, user.is_verified)}
              </TableCell>
              <TableCell>{formatDate(user.last_login)}</TableCell>
              <TableCell>{formatDate(user.created_at)}</TableCell>
              <TableCell className="text-right">
                <div className="flex items-center justify-end gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onViewDetails(user.id)}
                  >
                    <Eye className="h-4 w-4" />
                  </Button>
                  <Button
                    variant={user.is_active ? 'destructive' : 'default'}
                    size="sm"
                    onClick={() => onUpdateStatus(user.id, user.is_active)}
                  >
                    {user.is_active ? (
                      <>
                        <UserX className="h-4 w-4 mr-1" />
                        Deactivate
                      </>
                    ) : (
                      <>
                        <UserCheck className="h-4 w-4 mr-1" />
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
