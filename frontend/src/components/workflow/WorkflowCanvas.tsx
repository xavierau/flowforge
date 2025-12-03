/**
 * WorkflowCanvas - Reusable React Flow canvas component
 *
 * A composable canvas component that can be used in:
 * - Read-only mode for viewing workflows and execution details
 * - Editable mode for workflow building
 *
 * Supports execution status overlays for visualizing workflow execution state.
 */

import { useMemo, useCallback } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  ConnectionMode,
  type NodeTypes,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  type IsValidConnection,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import {
  HttpTriggerNode,
  ExtractionNode,
  PythonRunnerNode,
  HttpRequestNode,
  IfNode,
  JoinNode,
} from '@/components/workflow/nodes';
import {
  NodeType,
  WorkflowNodeExecutionStatus,
  type WorkflowNode,
  type WorkflowEdge,
} from '@/types/workflow';

/**
 * Props for WorkflowCanvas component
 */
export interface WorkflowCanvasProps {
  /** Workflow nodes to render */
  nodes: WorkflowNode[];
  /** Workflow edges (connections between nodes) */
  edges: WorkflowEdge[];
  /** When true, disables editing capabilities */
  readOnly?: boolean;
  /** Map of node IDs to their execution status for overlays */
  nodeStatuses?: Map<string, WorkflowNodeExecutionStatus>;
  /** Currently selected node ID for highlighting */
  selectedNodeId?: string | null;
  /** Callback when a node is clicked */
  onNodeClick?: (nodeId: string) => void;
  /** Callback when nodes change (drag, select, etc.) */
  onNodesChange?: OnNodesChange;
  /** Callback when edges change */
  onEdgesChange?: OnEdgesChange;
  /** Callback when a new connection is made */
  onConnect?: OnConnect;
  /** Connection validation function */
  isValidConnection?: IsValidConnection;
  /** Additional CSS classes */
  className?: string;
  /** Show empty state when no nodes */
  showEmptyState?: boolean;
}

// Register custom node types
const nodeTypes: NodeTypes = {
  [NodeType.HttpTrigger]: HttpTriggerNode,
  [NodeType.Extraction]: ExtractionNode,
  [NodeType.PythonRunner]: PythonRunnerNode,
  [NodeType.HttpRequest]: HttpRequestNode,
  [NodeType.If]: IfNode,
  [NodeType.Join]: JoinNode,
};

/**
 * Get border color based on execution status
 */
function getStatusBorderColor(status: WorkflowNodeExecutionStatus): string {
  switch (status) {
    case WorkflowNodeExecutionStatus.Pending:
      return 'hsl(var(--muted-foreground))';
    case WorkflowNodeExecutionStatus.Running:
      return 'hsl(var(--primary))';
    case WorkflowNodeExecutionStatus.Completed:
      return 'hsl(var(--success))';
    case WorkflowNodeExecutionStatus.Failed:
      return 'hsl(var(--destructive))';
    case WorkflowNodeExecutionStatus.Skipped:
      return 'hsl(var(--muted-foreground))';
    default:
      return 'hsl(var(--border))';
  }
}

/**
 * Get border style based on execution status
 */
function getStatusBorderStyle(status: WorkflowNodeExecutionStatus): string {
  if (status === WorkflowNodeExecutionStatus.Skipped) {
    return 'dashed';
  }
  return 'solid';
}

/**
 * Get MiniMap node color based on node state and execution status
 */
function getMiniMapNodeColor(
  node: WorkflowNode,
  nodeStatuses?: Map<string, WorkflowNodeExecutionStatus>
): string {
  // If we have execution status, use that for coloring
  if (nodeStatuses?.has(node.id)) {
    const status = nodeStatuses.get(node.id)!;
    switch (status) {
      case WorkflowNodeExecutionStatus.Completed:
        return 'hsl(var(--success))';
      case WorkflowNodeExecutionStatus.Failed:
        return 'hsl(var(--destructive))';
      case WorkflowNodeExecutionStatus.Running:
        return 'hsl(var(--primary))';
      case WorkflowNodeExecutionStatus.Skipped:
        return 'hsl(var(--muted-foreground))';
      default:
        return 'hsl(var(--muted))';
    }
  }

  // Fall back to validation status
  if (node.data?.isValid) {
    return 'hsl(var(--success))';
  }
  if (node.data?.errors?.length > 0) {
    return 'hsl(var(--destructive))';
  }
  return 'hsl(var(--muted))';
}

/**
 * WorkflowCanvas - Reusable React Flow canvas for workflow visualization
 *
 * This component provides a flexible canvas that can operate in two modes:
 * 1. Editable mode (default): Full drag, connect, and edit capabilities
 * 2. Read-only mode: View-only with optional execution status overlays
 *
 * @example
 * // Read-only view (WorkflowView page)
 * <WorkflowCanvas
 *   nodes={workflow.currentVersion.definition.nodes}
 *   edges={workflow.currentVersion.definition.edges}
 *   readOnly
 * />
 *
 * @example
 * // Execution detail with status overlays
 * <WorkflowCanvas
 *   nodes={workflow.currentVersion.definition.nodes}
 *   edges={workflow.currentVersion.definition.edges}
 *   readOnly
 *   nodeStatuses={nodeStatusMap}
 *   selectedNodeId={selectedNodeId}
 *   onNodeClick={setSelectedNodeId}
 * />
 *
 * @example
 * // Editable mode (used by WorkflowBuilder)
 * <WorkflowCanvas
 *   nodes={nodes}
 *   edges={edges}
 *   onNodesChange={onNodesChange}
 *   onEdgesChange={onEdgesChange}
 *   onConnect={onConnect}
 * />
 */
export function WorkflowCanvas({
  nodes,
  edges,
  readOnly = false,
  nodeStatuses,
  selectedNodeId,
  onNodeClick,
  onNodesChange,
  onEdgesChange,
  onConnect,
  isValidConnection,
  className = '',
  showEmptyState = true,
}: WorkflowCanvasProps) {
  /**
   * Process nodes to add execution status and selection styling
   *
   * This memoized computation:
   * 1. Injects execution status into node data for visual overlays
   * 2. Marks selected nodes for highlighting
   * 3. Applies status-based styling through className and style
   */
  const processedNodes = useMemo(() => {
    return nodes.map((node) => {
      const executionStatus = nodeStatuses?.get(node.id);
      const isSelected = selectedNodeId === node.id;

      // Build additional styles for execution status
      const statusStyles: Record<string, string> = {};
      if (executionStatus) {
        statusStyles.borderColor = getStatusBorderColor(executionStatus);
        statusStyles.borderStyle = getStatusBorderStyle(executionStatus);
      }

      // Build className for animations and selection
      const classNames: string[] = [];
      if (executionStatus === WorkflowNodeExecutionStatus.Running) {
        classNames.push('workflow-node-running');
      }
      if (isSelected) {
        classNames.push('workflow-node-selected');
      }

      return {
        ...node,
        selected: isSelected,
        data: {
          ...node.data,
          executionStatus,
          _statusStyles: statusStyles,
          _isHighlighted: isSelected,
        },
        className: classNames.join(' '),
      };
    });
  }, [nodes, nodeStatuses, selectedNodeId]);

  /**
   * Handle node click events
   * Extracts node ID and calls the provided callback
   */
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: { id: string }) => {
      onNodeClick?.(node.id);
    },
    [onNodeClick]
  );

  /**
   * Handle pane click (deselect all nodes)
   */
  const handlePaneClick = useCallback(() => {
    if (onNodeClick) {
      // Passing empty string or we could modify the interface to handle null
      // For now, we don't auto-deselect in read-only mode unless specifically handled
    }
  }, [onNodeClick]);

  /**
   * MiniMap node color function
   * Uses execution status if available, falls back to validation status
   */
  const miniMapNodeColor = useCallback(
    (node: WorkflowNode) => getMiniMapNodeColor(node, nodeStatuses),
    [nodeStatuses]
  );

  return (
    <div
      className={`relative w-full h-full ${className}`}
      style={{ backgroundColor: 'hsl(var(--muted) / 0.3)' }}
    >
      {/* CSS for animations */}
      <style>{`
        @keyframes pulse-border {
          0%, 100% {
            box-shadow: 0 0 0 0 hsl(var(--primary) / 0.4);
          }
          50% {
            box-shadow: 0 0 0 4px hsl(var(--primary) / 0.2);
          }
        }

        .workflow-node-running > div {
          animation: pulse-border 1.5s ease-in-out infinite;
        }

        .workflow-node-selected > div {
          box-shadow: 0 0 0 3px hsl(var(--primary) / 0.5);
        }
      `}</style>

      <ReactFlow
        nodes={processedNodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={readOnly ? undefined : onNodesChange}
        onEdgesChange={readOnly ? undefined : onEdgesChange}
        onConnect={readOnly ? undefined : onConnect}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
        isValidConnection={isValidConnection}
        connectionMode={ConnectionMode.Loose}
        fitView
        minZoom={0.1}
        maxZoom={4}
        nodesDraggable={!readOnly}
        nodesConnectable={!readOnly}
        elementsSelectable={true}
        panOnDrag={true}
        zoomOnScroll={true}
        defaultEdgeOptions={{
          type: 'smoothstep',
          animated: true,
        }}
        proOptions={{
          hideAttribution: true,
        }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={16}
          size={1}
          color="hsl(var(--muted-foreground) / 0.2)"
        />
        <Controls
          showInteractive={!readOnly}
          style={{
            backgroundColor: 'hsl(var(--background))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px',
          }}
        />
        <MiniMap
          nodeColor={miniMapNodeColor}
          maskColor="hsl(var(--background) / 0.8)"
          style={{
            backgroundColor: 'hsl(var(--background))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px',
          }}
        />
      </ReactFlow>

      {/* Empty State */}
      {showEmptyState && nodes.length === 0 && (
        <div
          className="absolute inset-0 flex items-center justify-center pointer-events-none"
          style={{ color: 'hsl(var(--muted-foreground))' }}
        >
          <div className="text-center">
            <svg
              className="mx-auto h-12 w-12 mb-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
            <h3 className="text-lg font-medium mb-1">
              {readOnly ? 'No nodes in workflow' : 'No nodes yet'}
            </h3>
            <p className="text-sm">
              {readOnly
                ? 'This workflow does not contain any nodes'
                : 'Click on a node type in the left panel to get started'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default WorkflowCanvas;
