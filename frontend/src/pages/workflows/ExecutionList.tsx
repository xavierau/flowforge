import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { Eye, XCircle, ArrowLeft } from 'lucide-react';

import { Page, PageHeader, PageContent } from '@/components/layout';
import {
  DataTable,
  createDateColumn,
  createActionsColumn,
  createCustomColumn,
} from '@/components/data-table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  getWorkflow,
  listWorkflowExecutions,
  stopExecution,
} from '@/services/workflow.service';
import type { WorkflowResponse, WorkflowExecutionResponse } from '@/types/workflow';
import { WorkflowExecutionStatus } from '@/types/workflow';
import type { RowAction, FilterConfig } from '@/types/data-table';

/**
 * Maps execution status to Badge variant
 * - completed: green (default)
 * - running: blue (secondary)
 * - failed: red (destructive)
 * - others: outline
 */
function getStatusVariant(
  status: string
): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case WorkflowExecutionStatus.Completed:
      return 'default';
    case WorkflowExecutionStatus.Running:
      return 'secondary';
    case WorkflowExecutionStatus.Failed:
      return 'destructive';
    case WorkflowExecutionStatus.Cancelled:
    case WorkflowExecutionStatus.Timeout:
    case WorkflowExecutionStatus.Paused:
      return 'outline';
    default:
      return 'secondary';
  }
}

/**
 * Formats the duration between start and completion time
 * Returns '--' if either timestamp is missing
 */
function formatDuration(execution: WorkflowExecutionResponse): string {
  if (!execution.startedAt || !execution.completedAt) {
    return '--';
  }

  const ms =
    new Date(execution.completedAt).getTime() -
    new Date(execution.startedAt).getTime();

  if (ms < 1000) {
    return `${ms}ms`;
  }
  if (ms < 60000) {
    return `${(ms / 1000).toFixed(2)}s`;
  }
  return `${(ms / 60000).toFixed(2)}m`;
}

/**
 * ExecutionList - Displays all executions for a specific workflow
 *
 * Features:
 * - List executions with status, timing, and duration
 * - View execution details
 * - Cancel running/pending executions
 * - Filter by status
 */
export function ExecutionList() {
  const navigate = useNavigate();
  const { id: workflowId } = useParams<{ id: string }>();
  const [workflow, setWorkflow] = useState<WorkflowResponse | null>(null);
  const [executions, setExecutions] = useState<WorkflowExecutionResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  /**
   * Load workflow metadata and executions in parallel
   */
  const loadData = useCallback(async () => {
    if (!workflowId) {
      toast.error('Workflow ID is required');
      navigate('/workflows');
      return;
    }

    try {
      setIsLoading(true);

      const [workflowData, executionsData] = await Promise.all([
        getWorkflow(workflowId),
        listWorkflowExecutions(workflowId, { page: 1, pageSize: 100 }),
      ]);

      setWorkflow(workflowData);
      setExecutions(executionsData.executions);
    } catch (error) {
      toast.error('Failed to load execution data', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsLoading(false);
    }
  }, [workflowId, navigate]);

  // Fetch data on mount
  useEffect(() => {
    loadData();
  }, [loadData]);

  /**
   * Handle cancellation of a running or pending execution
   */
  const handleCancel = async (execution: WorkflowExecutionResponse) => {
    if (!confirm('Are you sure you want to cancel this execution?')) {
      return;
    }

    try {
      await stopExecution(execution.id);
      toast.success('Execution cancelled');
      loadData();
    } catch (error) {
      toast.error('Failed to cancel execution', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  /**
   * Define row actions for the DataTable
   */
  const actions: RowAction<WorkflowExecutionResponse>[] = [
    {
      label: 'View',
      icon: Eye,
      onClick: (execution) => navigate(`/workflows/executions/${execution.id}`),
    },
    {
      label: 'Cancel',
      icon: XCircle,
      onClick: handleCancel,
      show: (execution) =>
        execution.status === WorkflowExecutionStatus.Running ||
        execution.status === WorkflowExecutionStatus.Pending,
      variant: 'destructive',
    },
  ];

  /**
   * Define filterable columns for status
   */
  const filterableColumns: FilterConfig[] = [
    {
      id: 'status',
      title: 'Status',
      options: [
        { label: 'Pending', value: WorkflowExecutionStatus.Pending },
        { label: 'Running', value: WorkflowExecutionStatus.Running },
        { label: 'Completed', value: WorkflowExecutionStatus.Completed },
        { label: 'Failed', value: WorkflowExecutionStatus.Failed },
        { label: 'Cancelled', value: WorkflowExecutionStatus.Cancelled },
        { label: 'Paused', value: WorkflowExecutionStatus.Paused },
        { label: 'Timeout', value: WorkflowExecutionStatus.Timeout },
      ],
    },
  ];

  /**
   * Define columns for the DataTable
   */
  const columns = [
    // Execution ID column - truncated with monospace font
    createCustomColumn<WorkflowExecutionResponse>({
      accessorKey: 'id',
      header: 'Execution ID',
      cell: ({ row }) => (
        <span className="font-mono text-xs">
          {row.original.id.substring(0, 8)}...
        </span>
      ),
      enableSorting: false,
    }),
    // Status badge column with filtering
    createCustomColumn<WorkflowExecutionResponse>({
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <Badge variant={getStatusVariant(row.original.status)}>
          {row.original.status}
        </Badge>
      ),
      filterFn: (row, id, value) => {
        return value.includes(row.getValue(id));
      },
    }),
    // Started date column
    createDateColumn<WorkflowExecutionResponse>('startedAt', 'Started'),
    // Completed date column
    createDateColumn<WorkflowExecutionResponse>('completedAt', 'Completed'),
    // Duration column (calculated)
    createCustomColumn<WorkflowExecutionResponse>({
      id: 'duration',
      header: 'Duration',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {formatDuration(row.original)}
        </span>
      ),
      enableSorting: false,
    }),
    // Actions column
    createActionsColumn<WorkflowExecutionResponse>(actions),
  ];

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Workflows', href: '/workflows' },
          {
            label: workflow?.name || 'Workflow',
            href: `/workflows/${workflowId}`,
          },
          { label: 'Executions' },
        ]}
        title="Execution History"
        subtitle={`Executions for ${workflow?.name || 'workflow'}`}
      />
      <PageContent>
        <div className="mb-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(`/workflows/${workflowId}`)}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Workflow
          </Button>
        </div>

        <DataTable
          columns={columns}
          data={executions}
          searchPlaceholder="Search executions..."
          searchableColumns={['id']}
          filterableColumns={filterableColumns}
          exportFilename={`executions-${workflowId}`}
          exportableColumns={['id', 'status', 'startedAt', 'completedAt']}
          isLoading={isLoading}
          emptyMessage="No executions found for this workflow. Execute the workflow to see results here."
        />
      </PageContent>
    </Page>
  );
}
