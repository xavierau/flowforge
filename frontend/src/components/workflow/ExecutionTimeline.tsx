/**
 * ExecutionTimeline - Vertical timeline displaying workflow node executions
 *
 * Displays node executions in order with status indicators, timing information,
 * and selection highlighting. Follows React best practices with proper
 * memoization and composable design.
 */

import React, { useMemo, useCallback } from 'react';
import { CheckCircle2, XCircle, Loader2, MinusCircle, Clock } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type {
  WorkflowNodeExecutionResponse,
  WorkflowNodeExecutionStatus,
} from '@/types/workflow';

/**
 * Props for ExecutionTimeline component
 */
interface ExecutionTimelineProps {
  /** Array of node execution records to display */
  nodeExecutions: WorkflowNodeExecutionResponse[];
  /** Currently selected node ID for highlighting */
  selectedNodeId: string | null;
  /** Callback when a node is clicked in the timeline */
  onNodeClick: (nodeId: string) => void;
  /** Optional additional CSS classes */
  className?: string;
}

/**
 * Returns the appropriate status icon for a node execution status
 * Uses consistent color coding:
 * - Green: completed successfully
 * - Red: failed with error
 * - Blue (animated): currently running
 * - Gray: pending or skipped
 */
function getStatusIcon(status: WorkflowNodeExecutionStatus): React.ReactElement {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    case 'failed':
      return <XCircle className="h-4 w-4 text-red-500" />;
    case 'running':
      return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
    case 'skipped':
      return <MinusCircle className="h-4 w-4 text-gray-400" />;
    case 'pending':
    default:
      return <Clock className="h-4 w-4 text-gray-400" />;
  }
}

/**
 * Formats the duration between start and completion times
 * Returns human-readable duration string (ms, s, or m)
 */
function formatDuration(nodeExec: WorkflowNodeExecutionResponse): string {
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
 * Gets the Badge variant based on node type for visual distinction
 */
function getNodeTypeBadgeVariant(
  nodeType: string
): 'default' | 'secondary' | 'outline' | 'destructive' {
  switch (nodeType.toLowerCase()) {
    case 'httptrigger':
      return 'default';
    case 'extraction':
      return 'secondary';
    case 'if':
    case 'join':
      return 'outline';
    default:
      return 'outline';
  }
}

/**
 * Formats node type for display (converts camelCase to readable format)
 */
function formatNodeType(nodeType: string): string {
  // Handle common node types
  const typeMap: Record<string, string> = {
    httptrigger: 'Trigger',
    httprequest: 'HTTP',
    pythonrunner: 'Python',
    extraction: 'Extract',
    if: 'If',
    join: 'Join',
  };

  const lowerType = nodeType.toLowerCase();
  return typeMap[lowerType] || nodeType;
}

/**
 * ExecutionTimeline Component
 *
 * Displays a vertical timeline of workflow node executions with:
 * - Status icons indicating execution state
 * - Node labels and type badges
 * - Timing information (start time, duration)
 * - Error message previews for failed nodes
 * - Selection highlighting and click handlers
 */
export function ExecutionTimeline({
  nodeExecutions,
  selectedNodeId,
  onNodeClick,
  className,
}: ExecutionTimelineProps) {
  // Sort executions by execution order (ascending)
  // Memoize to avoid recalculating on every render
  const sortedExecutions = useMemo(() => {
    return [...nodeExecutions].sort((a, b) => {
      const orderA = a.executionOrder ?? Number.MAX_SAFE_INTEGER;
      const orderB = b.executionOrder ?? Number.MAX_SAFE_INTEGER;
      return orderA - orderB;
    });
  }, [nodeExecutions]);

  // Memoize click handler to prevent unnecessary re-renders
  const handleNodeClick = useCallback(
    (nodeId: string) => {
      onNodeClick(nodeId);
    },
    [onNodeClick]
  );

  // Empty state
  if (sortedExecutions.length === 0) {
    return (
      <div className={cn('p-4', className)}>
        <h3
          className="text-sm font-semibold mb-4"
          style={{ color: 'hsl(var(--foreground))' }}
        >
          Execution Timeline
        </h3>
        <div
          className="flex flex-col items-center justify-center py-8"
          style={{ color: 'hsl(var(--muted-foreground))' }}
        >
          <Clock className="h-8 w-8 mb-2 opacity-30" />
          <p className="text-sm">No node executions</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('p-4', className)}>
      <h3
        className="text-sm font-semibold mb-4"
        style={{ color: 'hsl(var(--foreground))' }}
      >
        Execution Timeline
      </h3>

      <div className="space-y-1">
        {sortedExecutions.map((nodeExec, index) => {
          const isSelected = selectedNodeId === nodeExec.nodeId;
          const isLastItem = index === sortedExecutions.length - 1;

          return (
            <div
              key={nodeExec.id}
              className={cn(
                'flex items-start gap-3 p-3 rounded-lg cursor-pointer border transition-colors',
                isSelected
                  ? 'border-primary'
                  : 'border-transparent hover:border-border'
              )}
              style={{
                backgroundColor: isSelected
                  ? 'hsl(var(--primary) / 0.1)'
                  : undefined,
              }}
              onClick={() => handleNodeClick(nodeExec.nodeId)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleNodeClick(nodeExec.nodeId);
                }
              }}
              aria-selected={isSelected}
              aria-label={`Node ${nodeExec.nodeLabel}, status: ${nodeExec.status}`}
            >
              {/* Timeline connector and status icon */}
              <div className="flex flex-col items-center flex-shrink-0">
                {getStatusIcon(nodeExec.status as WorkflowNodeExecutionStatus)}
                {!isLastItem && (
                  <div
                    className="w-px h-8 mt-1"
                    style={{ backgroundColor: 'hsl(var(--border))' }}
                  />
                )}
              </div>

              {/* Node information */}
              <div className="flex-1 min-w-0">
                {/* Header row: label and type badge */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className="font-medium text-sm truncate"
                    style={{ color: 'hsl(var(--foreground))' }}
                    title={nodeExec.nodeLabel}
                  >
                    {nodeExec.nodeLabel}
                  </span>
                  <Badge
                    variant={getNodeTypeBadgeVariant(nodeExec.nodeType)}
                    className="text-xs flex-shrink-0"
                  >
                    {formatNodeType(nodeExec.nodeType)}
                  </Badge>
                </div>

                {/* Timing information */}
                <div
                  className="text-xs mt-1"
                  style={{ color: 'hsl(var(--muted-foreground))' }}
                >
                  {nodeExec.startedAt && (
                    <span>
                      {new Date(nodeExec.startedAt).toLocaleTimeString()}
                    </span>
                  )}
                  {nodeExec.completedAt && (
                    <span> &bull; {formatDuration(nodeExec)}</span>
                  )}
                  {!nodeExec.startedAt && nodeExec.status === 'pending' && (
                    <span>Waiting...</span>
                  )}
                  {!nodeExec.startedAt && nodeExec.status === 'skipped' && (
                    <span>Skipped</span>
                  )}
                </div>

                {/* Error message preview for failed nodes */}
                {nodeExec.errorMessage && (
                  <div
                    className="text-xs mt-1 truncate"
                    style={{ color: 'hsl(var(--destructive))' }}
                    title={nodeExec.errorMessage}
                  >
                    {nodeExec.errorMessage}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ExecutionTimeline;
