/**
 * ExecutionPanel - Bottom collapsible panel for workflow execution monitoring
 * Three tabs: Current Execution, History, Console
 */

import { useState, useMemo } from 'react';
import { ChevronDown, ChevronUp, Clock, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { useWorkflowStore } from '@/store/workflowStore';
import { ExecutionStatus, NodeExecutionStatus, WorkflowExecutionStatus } from '@/types/workflow';
import { NodeResultViewer } from './NodeResultViewer';

const PANEL_COLLAPSED_KEY = 'workflow-execution-panel-collapsed';

export function ExecutionPanel() {
  const [isCollapsed, setIsCollapsed] = useState(() => {
    const saved = localStorage.getItem(PANEL_COLLAPSED_KEY);
    return saved === 'true';
  });

  const { currentExecution, executionHistory, nodeExecutionStates, nodes } = useWorkflowStore();

  const toggleCollapsed = () => {
    const newState = !isCollapsed;
    setIsCollapsed(newState);
    localStorage.setItem(PANEL_COLLAPSED_KEY, String(newState));
  };

  // Calculate execution progress
  const progress = useMemo(() => {
    if (!currentExecution) return 0;

    const total = nodes.length;
    if (total === 0) return 0;

    const completed = Array.from(nodeExecutionStates.values()).filter(
      (state) => state.status === NodeExecutionStatus.Success
    ).length;

    return Math.round((completed / total) * 100);
  }, [nodes.length, nodeExecutionStates, currentExecution]);

  // Get status icon
  const getStatusIcon = (status: WorkflowExecutionStatus) => {
    switch (status) {
      case ExecutionStatus.Running:
        return <Clock className="h-4 w-4 animate-spin" style={{ color: 'hsl(var(--primary))' }} />;
      case ExecutionStatus.Completed:
        return <CheckCircle2 className="h-4 w-4" style={{ color: 'hsl(var(--success))' }} />;
      case ExecutionStatus.Failed:
        return <XCircle className="h-4 w-4" style={{ color: 'hsl(var(--destructive))' }} />;
      case ExecutionStatus.Cancelled:
        return <AlertCircle className="h-4 w-4" style={{ color: 'hsl(var(--warning))' }} />;
      default:
        return null;
    }
  };

  // Format duration
  const formatDuration = (ms?: number) => {
    if (!ms) return '--';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  return (
    <div
      className="border-t flex flex-col"
      style={{
        backgroundColor: 'hsl(var(--background))',
        borderColor: 'hsl(var(--border))',
        height: isCollapsed ? '48px' : '300px',
        transition: 'height 0.2s ease-in-out',
      }}
    >
      {/* Panel Header - Always Visible */}
      <div
        className="flex items-center justify-between px-4 py-2 border-b cursor-pointer hover:bg-muted/50"
        style={{ borderColor: 'hsl(var(--border))' }}
        onClick={toggleCollapsed}
      >
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
            {isCollapsed ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
          <h3 className="text-sm font-semibold" style={{ color: 'hsl(var(--foreground))' }}>
            Execution Monitor
          </h3>

          {/* Current Execution Status */}
          {currentExecution && (
            <div className="flex items-center gap-2">
              {getStatusIcon(currentExecution.status)}
              <span className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
                {currentExecution.status === ExecutionStatus.Running && `${progress}% complete`}
                {currentExecution.status === ExecutionStatus.Completed && 'Execution completed'}
                {currentExecution.status === ExecutionStatus.Failed && 'Execution failed'}
                {currentExecution.status === ExecutionStatus.Cancelled && 'Execution cancelled'}
              </span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {currentExecution && currentExecution.status === ExecutionStatus.Running && (
            <Badge variant="default" className="animate-pulse">
              Running
            </Badge>
          )}
          <span className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
            Press Ctrl+` to toggle
          </span>
        </div>
      </div>

      {/* Panel Content */}
      {!isCollapsed && (
        <div className="flex-1 overflow-hidden">
          <Tabs defaultValue="current" className="h-full flex flex-col">
            <TabsList className="w-full justify-start border-b rounded-none" style={{ borderColor: 'hsl(var(--border))' }}>
              <TabsTrigger value="current">Current Execution</TabsTrigger>
              <TabsTrigger value="history">
                History ({executionHistory.length})
              </TabsTrigger>
              <TabsTrigger value="console">
                Console {currentExecution && `(${currentExecution.logs?.length ?? 0})`}
              </TabsTrigger>
            </TabsList>

            {/* Current Execution Tab */}
            <TabsContent value="current" className="flex-1 overflow-y-auto p-4 m-0">
              {currentExecution ? (
                <div className="space-y-4">
                  {/* Execution Info */}
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <div className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
                        Execution ID
                      </div>
                      <div className="text-sm font-mono">{currentExecution.id.substring(0, 8)}...</div>
                    </div>
                    <div>
                      <div className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
                        Started
                      </div>
                      <div className="text-sm">{currentExecution.startedAt ? new Date(currentExecution.startedAt).toLocaleTimeString() : '--'}</div>
                    </div>
                    <div>
                      <div className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
                        Duration
                      </div>
                      <div className="text-sm">{formatDuration(currentExecution.totalDuration)}</div>
                    </div>
                  </div>

                  {/* Node Executions */}
                  <div>
                    <h4 className="text-sm font-semibold mb-2" style={{ color: 'hsl(var(--foreground))' }}>
                      Node Results
                    </h4>
                    <div className="space-y-2">
                      {Array.from(nodeExecutionStates.entries()).map(([nodeId, state]) => {
                        const node = nodes.find((n) => n.id === nodeId);
                        if (!node) return null;

                        return (
                          <div
                            key={nodeId}
                            className="border rounded-lg p-3"
                            style={{ borderColor: 'hsl(var(--border))' }}
                          >
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <Badge
                                  variant={
                                    state.status === NodeExecutionStatus.Success
                                      ? 'secondary'
                                      : state.status === NodeExecutionStatus.Error
                                        ? 'destructive'
                                        : state.status === NodeExecutionStatus.Running
                                          ? 'default'
                                          : 'outline'
                                  }
                                >
                                  {state.status}
                                </Badge>
                                <span className="font-medium text-sm">{node.data.label}</span>
                              </div>
                              {state.executionTime && (
                                <span className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
                                  {formatDuration(state.executionTime)}
                                </span>
                              )}
                            </div>

                            {state.error && (
                              <div
                                className="text-xs p-2 rounded mb-2"
                                style={{
                                  backgroundColor: 'hsl(var(--destructive) / 0.1)',
                                  color: 'hsl(var(--destructive))',
                                }}
                              >
                                {state.error}
                              </div>
                            )}

                            {state.outputData && (
                              <NodeResultViewer data={state.outputData} nodeId={nodeId} />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-full" style={{ color: 'hsl(var(--muted-foreground))' }}>
                  <div className="text-center">
                    <Clock className="h-12 w-12 mx-auto mb-2 opacity-20" />
                    <p className="text-sm">No execution in progress</p>
                    <p className="text-xs">Click "Run" to start workflow execution</p>
                  </div>
                </div>
              )}
            </TabsContent>

            {/* History Tab */}
            <TabsContent value="history" className="flex-1 overflow-y-auto p-4 m-0">
              {executionHistory.length > 0 ? (
                <div className="space-y-2">
                  {executionHistory.map((execution) => (
                    <div
                      key={execution.id}
                      className="border rounded-lg p-3"
                      style={{ borderColor: 'hsl(var(--border))' }}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(execution.status)}
                          <span className="text-sm font-mono">{execution.id.substring(0, 8)}...</span>
                          <Badge
                            variant={
                              execution.status === ExecutionStatus.Completed
                                ? 'secondary'
                                : execution.status === ExecutionStatus.Failed
                                  ? 'destructive'
                                  : 'outline'
                            }
                          >
                            {execution.status}
                          </Badge>
                        </div>
                        <span className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
                          {formatDuration(execution.totalDuration)}
                        </span>
                      </div>
                      <div className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
                        {execution.startedAt ? new Date(execution.startedAt).toLocaleString() : '--'}
                      </div>
                      {execution.error && (
                        <div className="text-xs mt-2" style={{ color: 'hsl(var(--destructive))' }}>
                          {execution.error}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full" style={{ color: 'hsl(var(--muted-foreground))' }}>
                  <div className="text-center">
                    <Clock className="h-12 w-12 mx-auto mb-2 opacity-20" />
                    <p className="text-sm">No execution history</p>
                  </div>
                </div>
              )}
            </TabsContent>

            {/* Console Tab */}
            <TabsContent value="console" className="flex-1 overflow-y-auto p-4 m-0 font-mono text-xs">
              {currentExecution && (currentExecution.logs?.length ?? 0) > 0 ? (
                <div className="space-y-1">
                  {(currentExecution.logs ?? []).map((log, index) => (
                    <div
                      key={index}
                      className="flex gap-2 p-1"
                      style={{
                        color:
                          log.level === 'error'
                            ? 'hsl(var(--destructive))'
                            : log.level === 'warn'
                              ? 'hsl(var(--warning))'
                              : log.level === 'info'
                                ? 'hsl(var(--primary))'
                                : 'hsl(var(--muted-foreground))',
                      }}
                    >
                      <span style={{ color: 'hsl(var(--muted-foreground))' }}>
                        [{new Date(log.timestamp).toLocaleTimeString()}]
                      </span>
                      <span className="uppercase">[{log.level}]</span>
                      {log.nodeId && <span>[{log.nodeId.substring(0, 8)}]</span>}
                      <span>{log.message}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full" style={{ color: 'hsl(var(--muted-foreground))' }}>
                  <div className="text-center">
                    <p>No console output</p>
                  </div>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      )}
    </div>
  );
}
