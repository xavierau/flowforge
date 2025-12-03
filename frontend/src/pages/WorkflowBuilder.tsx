/**
 * WorkflowBuilder - Main workflow canvas page
 * Integrates React Flow with custom nodes and configuration panels
 */

import { useCallback, useEffect, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  ConnectionMode,
  type NodeTypes,
  type Connection,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { Page, PageHeader, PageContent } from '@/components/layout';
import { WorkflowToolbar } from '@/components/workflow/WorkflowToolbar';
import { NodeConfigPanel } from '@/components/workflow/NodeConfigPanel';
import { ExecutionPanel } from '@/components/workflow/ExecutionPanel';
import {
  HttpTriggerNode,
  ExtractionNode,
  PythonRunnerNode,
  HttpRequestNode,
  IfNode,
  JoinNode,
} from '@/components/workflow/nodes';
import { useWorkflowStore } from '@/store/workflowStore';
import { useWorkflowWebSocket } from '@/hooks/useWorkflowWebSocket';
import { NodeType } from '@/types/workflow';

// Register custom node types
const nodeTypes: NodeTypes = {
  [NodeType.HttpTrigger]: HttpTriggerNode,
  [NodeType.Extraction]: ExtractionNode,
  [NodeType.PythonRunner]: PythonRunnerNode,
  [NodeType.HttpRequest]: HttpRequestNode,
  [NodeType.If]: IfNode,
  [NodeType.Join]: JoinNode,
};

export function WorkflowBuilder() {
  const [, setExecutionPanelCollapsed] = useState(false);

  const {
    nodes,
    edges,
    selectedNodeId,
    currentExecution,
    onNodesChange,
    onEdgesChange,
    onConnect,
    setSelectedNode,
    isValidConnection,
    handleExecutionUpdate,
    executeWorkflow,
    stopExecution,
    getExecutionStatus,
  } = useWorkflowStore();

  // Connect to WebSocket for real-time execution updates
  useWorkflowWebSocket(currentExecution?.id || null, handleExecutionUpdate);

  // Handle node selection
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: { id: string }) => {
      setSelectedNode(node.id);
    },
    [setSelectedNode]
  );

  // Handle pane click (deselect)
  const handlePaneClick = useCallback(() => {
    setSelectedNode(null);
  }, [setSelectedNode]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Ctrl+Enter (or Cmd+Enter on Mac) - Run workflow
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();

        const status = getExecutionStatus();
        if (status === 'running') {
          return; // Already running
        }

        if (nodes.length === 0) {
          return; // Empty workflow
        }

        executeWorkflow().catch((error) => {
          console.error('Keyboard shortcut execution error:', error);
        });
      }

      // Ctrl+` (backtick) - Toggle execution panel
      if ((event.ctrlKey || event.metaKey) && event.key === '`') {
        event.preventDefault();
        setExecutionPanelCollapsed((prev) => {
          const newState = !prev;
          localStorage.setItem('workflow-execution-panel-collapsed', String(newState));
          return newState;
        });
      }

      // Escape - Stop execution (with confirmation)
      if (event.key === 'Escape' && getExecutionStatus() === 'running') {
        if (window.confirm('Stop the running workflow execution?')) {
          stopExecution().catch((error) => {
            console.error('Keyboard shortcut stop error:', error);
          });
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    // Cleanup
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [nodes.length, executeWorkflow, stopExecution, getExecutionStatus]);

  return (
    <Page>
      <PageHeader
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Workflows', href: '/workflows' },
          { label: 'New Workflow' },
        ]}
        title="Workflow Builder"
        subtitle="Create and manage n8n-style document processing workflows"
      />
      <PageContent>
        <div className="flex flex-col h-[calc(100vh-200px)] rounded-lg border overflow-hidden" style={{ borderColor: 'hsl(var(--border))' }}>
          {/* Top Section - Canvas */}
          <div className="flex flex-1 overflow-hidden">
            {/* Left: Toolbar */}
            <WorkflowToolbar />

            {/* Center: React Flow Canvas */}
            <div className="flex-1 relative" style={{ backgroundColor: 'hsl(var(--muted) / 0.3)' }}>
            <ReactFlow
              nodes={nodes as any}
              edges={edges}
              nodeTypes={nodeTypes}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onNodeClick={handleNodeClick}
              onPaneClick={handlePaneClick}
              isValidConnection={(connection) => isValidConnection(connection as Connection)}
              connectionMode={ConnectionMode.Loose}
              fitView
              minZoom={0.1}
              maxZoom={4}
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
                style={{
                  backgroundColor: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                }}
              />
              <MiniMap
                nodeColor={(node: any) => {
                  // Color nodes based on validation status
                  if (node.data?.isValid) {
                    return 'hsl(var(--success))';
                  }
                  if (node.data?.errors?.length > 0) {
                    return 'hsl(var(--destructive))';
                  }
                  return 'hsl(var(--muted))';
                }}
                maskColor="hsl(var(--background) / 0.8)"
                style={{
                  backgroundColor: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                }}
              />
            </ReactFlow>

            {/* Empty State */}
            {nodes.length === 0 && (
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
                  <h3 className="text-lg font-medium mb-1">No nodes yet</h3>
                  <p className="text-sm">
                    Click on a node type in the left panel to get started
                  </p>
                </div>
              </div>
            )}
          </div>

            {/* Right: Config Panel (conditional) */}
            {selectedNodeId && <NodeConfigPanel />}
          </div>

          {/* Bottom Section - Execution Panel */}
          <ExecutionPanel />
        </div>
      </PageContent>
    </Page>
  );
}
