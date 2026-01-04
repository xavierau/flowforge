/**
 * InboundEmailList - Inbound email address management page
 *
 * Displays a table of inbound email addresses with:
 * - Name, email address, status, stats
 * - Active/inactive filtering
 * - CRUD actions (View, Edit, Delete)
 * - Pagination and search
 */

import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Mail,
  Plus,
  Eye,
  Pencil,
  Trash2,
  Power,
  PowerOff,
} from 'lucide-react';
import { toast } from 'sonner';

import { Page, PageHeader, PageContent } from '@/components/layout';
import {
  DataTable,
  createSelectColumn,
  createSortableColumn,
  createDateColumn,
  createActionsColumn,
  createCustomColumn,
} from '@/components/data-table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { InboundEmailAddressResponse } from '@/types/inbound-email';
import type { RowAction } from '@/types/data-table';
import {
  listInboundEmailAddresses,
  deleteInboundEmailAddress,
  updateInboundEmailAddress,
} from '@/services/inbound-email.service';

/**
 * Filter types for inbound email list
 */
type EmailAddressFilter = 'all' | 'active' | 'inactive';

/**
 * InboundEmailList - Main inbound email management page
 *
 * Features:
 * - List inbound email addresses with filtering by status
 * - View, Edit, Delete, Activate, Deactivate actions
 * - Navigate to detail page for logs
 */
export function InboundEmailList() {
  const navigate = useNavigate();
  const [addresses, setAddresses] = useState<InboundEmailAddressResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [currentFilter, setCurrentFilter] = useState<EmailAddressFilter>('all');

  /**
   * Load inbound email addresses based on current filter
   */
  const loadAddresses = useCallback(async () => {
    try {
      setIsLoading(true);

      // Build filter params based on current tab
      const params: { is_active?: boolean; limit?: number } = {
        limit: 100,
      };

      if (currentFilter === 'active') {
        params.is_active = true;
      } else if (currentFilter === 'inactive') {
        params.is_active = false;
      }

      const response = await listInboundEmailAddresses(params);
      setAddresses(response.addresses);
    } catch (error) {
      toast.error('Failed to load inbound email addresses', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsLoading(false);
    }
  }, [currentFilter]);

  // Fetch addresses on mount and when filter changes
  useEffect(() => {
    loadAddresses();
  }, [loadAddresses]);

  /**
   * Handle address deletion (soft delete - deactivates)
   */
  const handleDelete = async (address: InboundEmailAddressResponse) => {
    if (!confirm('Are you sure you want to delete this inbound email address? It will be deactivated.')) {
      return;
    }

    try {
      await deleteInboundEmailAddress(address.id);
      toast.success('Inbound email address deleted');
      await loadAddresses();
    } catch (error) {
      toast.error('Failed to delete inbound email address', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  /**
   * Handle address activation
   */
  const handleActivate = async (address: InboundEmailAddressResponse) => {
    try {
      await updateInboundEmailAddress(address.id, { is_active: true });
      toast.success('Inbound email address activated');
      await loadAddresses();
    } catch (error) {
      toast.error('Failed to activate inbound email address', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  /**
   * Handle address deactivation
   */
  const handleDeactivate = async (address: InboundEmailAddressResponse) => {
    try {
      await updateInboundEmailAddress(address.id, { is_active: false });
      toast.success('Inbound email address deactivated');
      await loadAddresses();
    } catch (error) {
      toast.error('Failed to deactivate inbound email address', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  /**
   * Define row actions for the DataTable
   */
  const actions: RowAction<InboundEmailAddressResponse>[] = [
    {
      label: 'View Details',
      icon: Eye,
      onClick: (address) => navigate(`/inbound-emails/${address.id}`),
    },
    {
      label: 'Edit',
      icon: Pencil,
      onClick: (address) => navigate(`/inbound-emails/${address.id}/edit`),
    },
    {
      label: 'Activate',
      icon: Power,
      onClick: handleActivate,
      show: (address) => !address.is_active,
    },
    {
      label: 'Deactivate',
      icon: PowerOff,
      onClick: handleDeactivate,
      show: (address) => address.is_active,
    },
    {
      label: 'Delete',
      icon: Trash2,
      onClick: handleDelete,
      variant: 'destructive',
    },
  ];

  /**
   * Define columns for the DataTable
   */
  const columns = [
    createSelectColumn<InboundEmailAddressResponse>(),
    createSortableColumn<InboundEmailAddressResponse>('name', 'Name'),
    createCustomColumn<InboundEmailAddressResponse>({
      accessorKey: 'email_address',
      header: 'Email Address',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Mail className="h-4 w-4 text-muted-foreground" />
          <span className="font-mono text-sm">{row.original.email_address}</span>
        </div>
      ),
    }),
    createCustomColumn<InboundEmailAddressResponse>({
      id: 'status',
      header: 'Status',
      cell: ({ row }) => {
        const isActive = row.original.is_active;
        return (
          <Badge
            variant={isActive ? 'default' : 'secondary'}
            className={isActive ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}
          >
            {isActive ? 'Active' : 'Inactive'}
          </Badge>
        );
      },
    }),
    createCustomColumn<InboundEmailAddressResponse>({
      accessorKey: 'emails_received_count',
      header: 'Emails Received',
      cell: ({ row }) => (
        <div className="text-sm text-muted-foreground">
          {row.original.emails_received_count.toLocaleString()}
        </div>
      ),
    }),
    createCustomColumn<InboundEmailAddressResponse>({
      accessorKey: 'documents_processed_count',
      header: 'Documents Processed',
      cell: ({ row }) => (
        <div className="text-sm text-muted-foreground">
          {row.original.documents_processed_count.toLocaleString()}
        </div>
      ),
    }),
    createDateColumn<InboundEmailAddressResponse>('last_email_at', 'Last Email', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }),
    createActionsColumn<InboundEmailAddressResponse>(actions),
  ];

  /**
   * Handle filter tab change
   */
  const handleFilterChange = (value: string) => {
    setCurrentFilter(value as EmailAddressFilter);
  };

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Inbound Emails' },
        ]}
        title="Inbound Email Addresses"
        subtitle="Manage email addresses for automatic document processing"
      />
      <PageContent>
        <div className="flex items-center justify-between mb-4">
          <Tabs value={currentFilter} onValueChange={handleFilterChange}>
            <TabsList>
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="active">Active</TabsTrigger>
              <TabsTrigger value="inactive">Inactive</TabsTrigger>
            </TabsList>
          </Tabs>

          <Button onClick={() => navigate('/inbound-emails/new')}>
            <Plus className="mr-2 h-4 w-4" />
            Create New
          </Button>
        </div>

        <DataTable
          columns={columns}
          data={addresses}
          searchPlaceholder="Search inbound emails..."
          searchableColumns={['name', 'email_address']}
          exportFilename="inbound-email-addresses"
          exportableColumns={[
            'name',
            'email_address',
            'emails_received_count',
            'documents_processed_count',
            'last_email_at',
            'created_at',
          ]}
          isLoading={isLoading}
          emptyMessage={
            currentFilter === 'inactive'
              ? 'No inactive inbound email addresses found.'
              : currentFilter === 'active'
              ? 'No active inbound email addresses found. Create and activate an address to see it here.'
              : 'No inbound email addresses found. Create your first address to get started.'
          }
        />
      </PageContent>
    </Page>
  );
}
