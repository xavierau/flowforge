/**
 * ExecutionDetail - Detailed workflow execution view page
 *
 * Displays comprehensive execution information including:
 * - Execution status summary with timing
 * - Canvas with node status overlays
 * - Execution timeline panel
 * - Node input/output data inspection
 *
 * Follows React best practices with proper state management,
 * memoization, and composable component design.
 */

import { useEffect, useState, useMemo, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { XCircle, ArrowLeft, Loader2, Clock, PanelRightClose, PanelRightOpen } from 'lucide-react';

import { Page, PageHeader, PageContent } from '@/components/layout';
import { WorkflowCanvas } from '@/components/workflow/WorkflowCanvas';
import { ExecutionTimeline } from '@/components/workflow/ExecutionTimeline';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  getWorkflow,
  getExecutionStatus,
  getNodeExecutions,
  stopExecution,
} from '@/services/workflow.service';
import {
  WorkflowExecutionStatus,
  type WorkflowResponse,
  type WorkflowExecutionResponse,
  type WorkflowNodeExecutionResponse,
  type WorkflowNodeExecutionStatus,
  type WorkflowDefinition,
} from '@/types/workflow';

/**
 * Get Badge variant based on execution status
 * Uses consistent color coding across the application
 */
function getStatusVariant(
  status: WorkflowExecutionStatus | WorkflowNodeExecutionStatus | string
): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case WorkflowExecutionStatus.Completed:
    case 'completed':
      return 'default';
    case WorkflowExecutionStatus.Running:
    case 'running':
      return 'secondary';
    case WorkflowExecutionStatus.Failed:
    case 'failed':
      return 'destructive';
    case WorkflowExecutionStatus.Cancelled:
    case 'cancelled':
    case WorkflowExecutionStatus.Timeout:
    case 'timeout':
      return 'destructive';
    default:
      return 'outline';
  }
}

/**
 * Format execution duration from start to completion
 * Returns human-readable duration string
 */
function formatDuration(execution: WorkflowExecutionResponse): string {
  if (!execution.startedAt || !execution.completedAt) {
    return '--';
  }

  const startTime = new Date(execution.startedAt).getTime();
  const endTime = new Date(execution.completedAt).getTime();
  const ms = endTime - startTime;

  if (ms < 1000) {
    return `${ms}ms`;
  }
  if (ms < 60000) {
    return `${(ms / 1000).toFixed(2)}s`;
  }
  return `${(ms / 60000).toFixed(2)}m`;
}

/**
 * Format node execution duration
 */
function formatNodeDuration(nodeExec: WorkflowNodeExecutionResponse): string {
  if (!nodeExec.startedAt || !nodeExec.completedAt) {
    return '--';
  }

  const startTime = new Date(nodeExec.startedAt).getTime();
  const endTime = new Date(nodeExec.completedAt).getTime();
  const ms = endTime - startTime;

  if (ms < 1000) {
    return `${ms}ms`;
  }
  if (ms < 60000) {
    return `${(ms / 1000).toFixed(2)}s`;
  }
  return `${(ms / 60000).toFixed(2)}m`;
}

/**
 * ExecutionDetail displays a comprehensive view of a workflow execution
 *
 * Features:
 * - Summary card with status, timing, and actions
 * - Interactive canvas with node status overlays
 * - Toggleable timeline panel
 * - Detailed node inspection with input/output data
 */
export function ExecutionDetail() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();

  // Data states
  const [execution, setExecution] = useState<WorkflowExecutionResponse | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowResponse | null>(null);
  const [nodeExecutions, setNodeExecutions] = useState<WorkflowNodeExecutionResponse[]>([]);

  // UI states
  const [isLoading, setIsLoading] = useState(true);
  const [isCancelling, setIsCancelling] = useState(false);
  const [showTimeline, setShowTimeline] = useState(true);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  /**
   * Fetch execution data and related workflow
   * Runs on mount and when executionId changes
   */
  const loadExecutionData = useCallback(async () => {
    if (!id) {
      toast.error('Execution ID is required');
      navigate('/workflows');
      return;
    }

    try {
      setIsLoading(true);

      // Fetch execution status and node executions in parallel
      const [executionData, nodeExecData] = await Promise.all([
        getExecutionStatus(id),
        getNodeExecutions(id),
      ]);

      setExecution(executionData);
      setNodeExecutions(nodeExecData);

      // Fetch workflow details after getting execution
      if (executionData.workflowId) {
        const workflowData = await getWorkflow(executionData.workflowId);
        setWorkflow(workflowData);
      }
    } catch (error) {
      toast.error('Failed to load execution details', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
      navigate('/workflows');
    } finally {
      setIsLoading(false);
    }
  }, [id, navigate]);

  useEffect(() => {
    loadExecutionData();
  }, [loadExecutionData]);

  /**
   * Auto-refresh for running executions
   * Polls every 2 seconds while execution is in progress
   * Only depends on execution.status to avoid unnecessary re-renders
   */
  useEffect(() => {
    // Only check status, not entire execution object
    const isInProgress =
      execution?.status === WorkflowExecutionStatus.Running ||
      execution?.status === WorkflowExecutionStatus.Pending;

    if (!isInProgress || !id) return;

    const intervalId = setInterval(async () => {
      try {
        const [executionData, nodeExecData] = await Promise.all([
          getExecutionStatus(id),
          getNodeExecutions(id),
        ]);
        setExecution(executionData);
        setNodeExecutions(nodeExecData);
      } catch (error) {
        // Silently handle polling errors to avoid toast spam
        console.error('Failed to refresh execution status:', error);
      }
    }, 2000);

    return () => clearInterval(intervalId);
  }, [execution?.status, id]);

  /**
   * Cancel a running execution
   */
  const handleCancel = useCallback(async () => {
    if (!id) return;

    try {
      setIsCancelling(true);
      await stopExecution(id);
      toast.success('Execution cancelled successfully');
      await loadExecutionData();
    } catch (error) {
      toast.error('Failed to cancel execution', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsCancelling(false);
    }
  }, [id, loadExecutionData]);

  /**
   * Build node status map for canvas overlays
   * Maps node IDs to their execution status
   */
  const nodeStatusMap = useMemo(() => {
    const map = new Map<string, WorkflowNodeExecutionStatus>();
    nodeExecutions.forEach((ne) => {
      map.set(ne.nodeId, ne.status as WorkflowNodeExecutionStatus);
    });
    return map;
  }, [nodeExecutions]);

  /**
   * Get the selected node execution details
   */
  const selectedNodeExecution = useMemo(() => {
    return nodeExecutions.find((ne) => ne.nodeId === selectedNodeId);
  }, [nodeExecutions, selectedNodeId]);

  /**
   * Get workflow definition from current version
   */
  const definition: WorkflowDefinition | null = useMemo(() => {
    return workflow?.currentVersion?.definition || null;
  }, [workflow]);

  /**
   * Handle node selection from canvas or timeline
   */
  const handleNodeClick = useCallback((nodeId: string) => {
    setSelectedNodeId((prev) => (prev === nodeId ? null : nodeId));
  }, []);

  // Loading state
  if (isLoading) {
    return (
      <Page>
        <PageContent>
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </PageContent>
      </Page>
    );
  }

  // No execution found
  if (!execution) {
    return null;
  }

  const executionIdShort = id?.substring(0, 8) || 'Unknown';

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Workflows', href: '/workflows' },
          {
            label: workflow?.name || 'Workflow',
            href: `/workflows/${execution.workflowId}`,
          },
          {
            label: 'Executions',
            href: `/workflows/${execution.workflowId}/executions`,
          },
          { label: `Execution ${executionIdShort}` },
        ]}
        title={`Execution: ${executionIdShort}...`}
        subtitle={`Status: ${execution.status || 'Loading...'}`}
      />
      <PageContent>
        {/* Back Button */}
        <div className="flex gap-2 mb-4">
          <Button
            variant="outline"
            onClick={() =>
              navigate(`/workflows/${execution.workflowId}/executions`)
            }
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Executions
          </Button>
        </div>

        {/* Summary Card */}
        <Card className="mb-6">
          <CardContent className="flex items-center justify-between py-4">
            <div className="flex items-center gap-4">
              <Badge variant={getStatusVariant(execution.status)}>
                {execution.status}
              </Badge>
              <span className="text-sm text-muted-foreground flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Started:{' '}
                {execution.startedAt
                  ? new Date(execution.startedAt).toLocaleString()
                  : 'N/A'}
              </span>
              {execution.completedAt && (
                <span className="text-sm text-muted-foreground">
                  Duration: {formatDuration(execution)}
                </span>
              )}
            </div>
            <div className="flex gap-2">
              {(execution.status === WorkflowExecutionStatus.Running ||
                execution.status === WorkflowExecutionStatus.Pending) && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleCancel}
                  disabled={isCancelling}
                >
                  {isCancelling ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <XCircle className="mr-2 h-4 w-4" />
                  )}
                  Cancel
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowTimeline(!showTimeline)}
              >
                {showTimeline ? (
                  <>
                    <PanelRightClose className="mr-2 h-4 w-4" />
                    Hide Timeline
                  </>
                ) : (
                  <>
                    <PanelRightOpen className="mr-2 h-4 w-4" />
                    Show Timeline
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Error Message (if failed) */}
        {execution.errorMessage && (
          <Card className="mb-6 border-destructive">
            <CardContent className="py-4">
              <div className="flex items-start gap-2 text-destructive">
                <XCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">Execution Failed</p>
                  <p className="text-sm">{execution.errorMessage}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Main Content: Canvas + Timeline */}
        <div className="flex gap-6">
          {/* Canvas with Status Overlays */}
          <Card className="flex-1">
            <CardHeader className="py-3">
              <CardTitle className="text-base">Workflow Canvas</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="h-[500px]">
                {definition ? (
                  <WorkflowCanvas
                    nodes={definition.nodes}
                    edges={definition.edges}
                    readOnly
                    nodeStatuses={nodeStatusMap}
                    selectedNodeId={selectedNodeId}
                    onNodeClick={handleNodeClick}
                  />
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    <Loader2 className="h-6 w-6 animate-spin mr-2" />
                    Loading workflow definition...
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Timeline Panel (toggleable) */}
          {showTimeline && (
            <Card className="w-80 flex-shrink-0">
              <CardContent className="p-0">
                <ExecutionTimeline
                  nodeExecutions={nodeExecutions}
                  selectedNodeId={selectedNodeId}
                  onNodeClick={handleNodeClick}
                />
              </CardContent>
            </Card>
          )}
        </div>

        {/* Selected Node Details Panel */}
        {selectedNodeExecution && (
          <Card className="mt-6">
            <CardHeader className="py-3">
              <CardTitle className="flex items-center gap-2 text-base">
                Node: {selectedNodeExecution.nodeLabel}
                <Badge variant="outline">{selectedNodeExecution.nodeType}</Badge>
                <Badge variant={getStatusVariant(selectedNodeExecution.status)}>
                  {selectedNodeExecution.status}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="output">
                <TabsList>
                  <TabsTrigger value="input">Input Data</TabsTrigger>
                  <TabsTrigger value="output">Output Data</TabsTrigger>
                  {selectedNodeExecution.errorMessage && (
                    <TabsTrigger value="error">Error</TabsTrigger>
                  )}
                </TabsList>

                <TabsContent value="input">
                  <pre className="p-4 bg-muted rounded-lg overflow-auto max-h-64 text-sm font-mono">
                    {selectedNodeExecution.inputData
                      ? JSON.stringify(selectedNodeExecution.inputData, null, 2)
                      : 'No input data'}
                  </pre>
                </TabsContent>

                <TabsContent value="output">
                  <pre className="p-4 bg-muted rounded-lg overflow-auto max-h-64 text-sm font-mono">
                    {selectedNodeExecution.outputData
                      ? JSON.stringify(selectedNodeExecution.outputData, null, 2)
                      : 'No output data'}
                  </pre>
                </TabsContent>

                {selectedNodeExecution.errorMessage && (
                  <TabsContent value="error">
                    <div className="p-4 bg-destructive/10 rounded-lg text-destructive">
                      <p className="font-medium">Error Message:</p>
                      <p className="mt-1">{selectedNodeExecution.errorMessage}</p>
                    </div>
                  </TabsContent>
                )}
              </Tabs>

              {/* Node timing info */}
              <div className="mt-4 flex gap-4 text-sm text-muted-foreground">
                <span>
                  Started:{' '}
                  {selectedNodeExecution.startedAt
                    ? new Date(selectedNodeExecution.startedAt).toLocaleTimeString()
                    : 'N/A'}
                </span>
                <span>Duration: {formatNodeDuration(selectedNodeExecution)}</span>
              </div>
            </CardContent>
          </Card>
        )}
      </PageContent>
    </Page>
  );
}

export default ExecutionDetail;
