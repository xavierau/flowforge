import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Eye,
  Pencil,
  Copy,
  Play,
  Archive,
  ArchiveRestore,
  Trash2,
  Plus,
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
import type { WorkflowResponse } from '@/types/workflow';
import type { RowAction } from '@/types/data-table';
import {
  listWorkflows,
  deleteWorkflow,
  cloneWorkflow,
  archiveWorkflow,
  restoreWorkflow,
  activateWorkflow,
  deactivateWorkflow,
  listWorkflowExecutions,
} from '@/services/workflow.service';

/**
 * Filter types for workflow list
 */
type WorkflowFilter = 'active' | 'draft' | 'archived';

/**
 * WorkflowList - Main workflow management page
 *
 * Features:
 * - List workflows with filtering by status (Active/Draft/Archived)
 * - CRUD operations via actions dropdown
 * - Clone, archive, restore, activate, deactivate workflows
 * - Navigate to workflow builder for editing
 */
export function WorkflowList() {
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState<WorkflowResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [currentFilter, setCurrentFilter] = useState<WorkflowFilter>('active');

  /**
   * Load workflows based on current filter
   */
  const loadWorkflows = useCallback(async () => {
    try {
      setIsLoading(true);

      // Build filter params based on current tab
      const params = {
        pageSize: 100,
        ...(currentFilter === 'active' && { isActive: true, isArchived: false }),
        ...(currentFilter === 'draft' && { isActive: false, isArchived: false }),
        ...(currentFilter === 'archived' && { isArchived: true }),
      };

      const response = await listWorkflows(params);
      setWorkflows(response.workflows);
    } catch (error) {
      toast.error('Failed to load workflows', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsLoading(false);
    }
  }, [currentFilter]);

  // Fetch workflows on mount and when filter changes
  useEffect(() => {
    loadWorkflows();
  }, [loadWorkflows]);

  /**
   * Handle workflow deletion with execution check
   */
  const handleDelete = async (workflow: WorkflowResponse) => {
    try {
      // Check if workflow has executions
      const executionsResponse = await listWorkflowExecutions(workflow.id, {
        pageSize: 1,
      });

      if (executionsResponse.total > 0) {
        toast.error('Cannot delete workflow', {
          description: `This workflow has ${executionsResponse.total} execution(s). Archive it instead.`,
        });
        return;
      }

      // Confirm deletion
      if (!confirm('Are you sure you want to delete this workflow? This action cannot be undone.')) {
        return;
      }

      await deleteWorkflow(workflow.id);
      toast.success('Workflow deleted successfully');
      await loadWorkflows();
    } catch (error) {
      toast.error('Failed to delete workflow', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  /**
   * Handle workflow cloning
   */
  const handleClone = async (workflow: WorkflowResponse) => {
    try {
      const newWorkflow = await cloneWorkflow(workflow.id);
      toast.success('Workflow cloned successfully');
      navigate(`/workflows/${newWorkflow.id}/edit`);
    } catch (error) {
      toast.error('Failed to clone workflow', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  /**
   * Handle workflow archiving
   */
  const handleArchive = async (workflow: WorkflowResponse) => {
    try {
      await archiveWorkflow(workflow.id);
      toast.success('Workflow archived successfully');
      await loadWorkflows();
    } catch (error) {
      toast.error('Failed to archive workflow', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  /**
   * Handle workflow restoration from archive
   */
  const handleRestore = async (workflow: WorkflowResponse) => {
    try {
      await restoreWorkflow(workflow.id);
      toast.success('Workflow restored successfully');
      await loadWorkflows();
    } catch (error) {
      toast.error('Failed to restore workflow', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  /**
   * Handle workflow activation
   */
  const handleActivate = async (workflow: WorkflowResponse) => {
    try {
      await activateWorkflow(workflow.id);
      toast.success('Workflow activated successfully');
      await loadWorkflows();
    } catch (error) {
      toast.error('Failed to activate workflow', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  /**
   * Handle workflow deactivation
   */
  const handleDeactivate = async (workflow: WorkflowResponse) => {
    try {
      await deactivateWorkflow(workflow.id);
      toast.success('Workflow deactivated successfully');
      await loadWorkflows();
    } catch (error) {
      toast.error('Failed to deactivate workflow', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  /**
   * Define row actions for the DataTable
   */
  const actions: RowAction<WorkflowResponse>[] = [
    {
      label: 'View',
      icon: Eye,
      onClick: (workflow) => navigate(`/workflows/${workflow.id}`),
    },
    {
      label: 'Edit',
      icon: Pencil,
      onClick: (workflow) => navigate(`/workflows/${workflow.id}/edit`),
      show: (workflow) => !workflow.isArchived,
    },
    {
      label: 'Clone',
      icon: Copy,
      onClick: handleClone,
    },
    {
      label: 'Executions',
      icon: Play,
      onClick: (workflow) => navigate(`/workflows/${workflow.id}/executions`),
    },
    {
      label: 'Activate',
      icon: Power,
      onClick: handleActivate,
      show: (workflow) => !workflow.isActive && !workflow.isArchived,
    },
    {
      label: 'Deactivate',
      icon: PowerOff,
      onClick: handleDeactivate,
      show: (workflow) => workflow.isActive && !workflow.isArchived,
    },
    {
      label: 'Archive',
      icon: Archive,
      onClick: handleArchive,
      show: (workflow) => !workflow.isArchived,
    },
    {
      label: 'Restore',
      icon: ArchiveRestore,
      onClick: handleRestore,
      show: (workflow) => workflow.isArchived,
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
    createSelectColumn<WorkflowResponse>(),
    createSortableColumn<WorkflowResponse>('name', 'Name'),
    createCustomColumn<WorkflowResponse>({
      id: 'status',
      header: 'Status',
      cell: ({ row }) => {
        const workflow = row.original;

        if (workflow.isArchived) {
          return (
            <Badge variant="outline" className="bg-gray-100 text-gray-600">
              Archived
            </Badge>
          );
        }

        if (workflow.isActive) {
          return (
            <Badge variant="default" className="bg-green-100 text-green-700">
              Active
            </Badge>
          );
        }

        return (
          <Badge variant="secondary" className="bg-yellow-100 text-yellow-700">
            Draft
          </Badge>
        );
      },
    }),
    createCustomColumn<WorkflowResponse>({
      accessorKey: 'currentVersionNumber',
      header: 'Version',
      cell: ({ row }) => (
        <div className="text-sm text-muted-foreground">
          v{row.original.currentVersionNumber}
        </div>
      ),
    }),
    createDateColumn<WorkflowResponse>('createdAt', 'Created', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }),
    createDateColumn<WorkflowResponse>('updatedAt', 'Updated', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }),
    createActionsColumn<WorkflowResponse>(actions),
  ];

  /**
   * Handle filter tab change
   */
  const handleFilterChange = (value: string) => {
    setCurrentFilter(value as WorkflowFilter);
  };

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Workflows' },
        ]}
        title="Workflows"
        subtitle="Manage your document processing workflows"
      />
      <PageContent>
        <div className="flex items-center justify-between mb-4">
          <Tabs value={currentFilter} onValueChange={handleFilterChange}>
            <TabsList>
              <TabsTrigger value="active">Active</TabsTrigger>
              <TabsTrigger value="draft">Draft</TabsTrigger>
              <TabsTrigger value="archived">Archived</TabsTrigger>
            </TabsList>
          </Tabs>

          <Button onClick={() => navigate('/workflows/new')}>
            <Plus className="mr-2 h-4 w-4" />
            Create Workflow
          </Button>
        </div>

        <DataTable
          columns={columns}
          data={workflows}
          searchPlaceholder="Search workflows..."
          searchableColumns={['name']}
          exportFilename="workflows"
          exportableColumns={['name', 'currentVersionNumber', 'createdAt', 'updatedAt']}
          isLoading={isLoading}
          emptyMessage={
            currentFilter === 'archived'
              ? 'No archived workflows found.'
              : currentFilter === 'draft'
              ? 'No draft workflows found. Create your first workflow to get started.'
              : 'No active workflows found. Create and activate a workflow to see it here.'
          }
        />
      </PageContent>
    </Page>
  );
}
