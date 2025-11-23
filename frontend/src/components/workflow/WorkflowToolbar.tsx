/**
 * WorkflowToolbar - Left sidebar with node palette and workflow actions
 */

import { useState } from 'react';
import {
  Webhook,
  FileText,
  Code,
  Send,
  GitBranch,
  Merge,
  Save,
  FolderOpen,
  Trash2,
  Plus,
  Edit2,
  Download,
  Upload,
  Play,
  Square,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { NodeType, ExecutionStatus } from '@/types/workflow';
import { useWorkflowStore } from '@/store/workflowStore';
import { Badge } from '@/components/ui/badge';

const NODE_TYPES = [
  {
    type: NodeType.HttpTrigger,
    label: 'HTTP Trigger',
    icon: Webhook,
    description: 'Start workflow with HTTP request',
  },
  {
    type: NodeType.Extraction,
    label: 'Extraction',
    icon: FileText,
    description: 'Extract data using schema',
  },
  {
    type: NodeType.PythonRunner,
    label: 'Python Runner',
    icon: Code,
    description: 'Execute Python code',
  },
  {
    type: NodeType.HttpRequest,
    label: 'HTTP Request',
    icon: Send,
    description: 'Send HTTP request',
  },
  {
    type: NodeType.If,
    label: 'If',
    icon: GitBranch,
    description: 'Conditional branching',
  },
  {
    type: NodeType.Join,
    label: 'Join',
    icon: Merge,
    description: 'Wait for all branches to complete',
  },
];

export function WorkflowToolbar() {
  const [isEditingName, setIsEditingName] = useState(false);
  const [tempName, setTempName] = useState('');

  const {
    workflowName,
    nodes,
    setWorkflowName,
    addNode,
    saveWorkflow,
    loadWorkflow,
    getSavedWorkflows,
    clearWorkflow,
    exportWorkflow,
    importWorkflow,
    executeWorkflow,
    stopExecution,
    getExecutionStatus,
  } = useWorkflowStore();

  const executionStatus = getExecutionStatus();
  const isExecuting = executionStatus === ExecutionStatus.Running;

  const savedWorkflows = getSavedWorkflows();

  const handleAddNode = (type: NodeType) => {
    // Add node at center of viewport with some randomness
    const position = {
      x: 250 + Math.random() * 100,
      y: 150 + Math.random() * 100,
    };
    addNode(type, position);
  };

  const handleSaveWorkflow = () => {
    saveWorkflow();
    // Show success feedback (could add toast notification)
    console.log('Workflow saved successfully');
  };

  const handleLoadWorkflow = (workflowId: string) => {
    loadWorkflow(workflowId);
  };

  const handleClearWorkflow = () => {
    if (
      window.confirm(
        'Are you sure you want to clear this workflow? This action cannot be undone.'
      )
    ) {
      clearWorkflow();
    }
  };

  const handleExportWorkflow = () => {
    const json = exportWorkflow();
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${workflowName.replace(/\s+/g, '_')}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleImportWorkflow = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const json = event.target?.result as string;
          importWorkflow(json);
          console.log('Workflow imported successfully');
        } catch (error) {
          alert('Failed to import workflow. Please check the file format.');
          console.error('Import error:', error);
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  const handleNameEdit = () => {
    if (isEditingName) {
      if (tempName.trim()) {
        setWorkflowName(tempName.trim());
      }
      setIsEditingName(false);
    } else {
      setTempName(workflowName);
      setIsEditingName(true);
    }
  };

  const handleRunWorkflow = async () => {
    if (nodes.length === 0) {
      alert('Cannot run empty workflow. Add some nodes first.');
      return;
    }

    try {
      await executeWorkflow();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to execute workflow';
      alert(message);
      console.error('Execution error:', error);
    }
  };

  const handleStopExecution = async () => {
    try {
      await stopExecution();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to stop execution';
      alert(message);
      console.error('Stop execution error:', error);
    }
  };

  const getStatusBadgeVariant = (): 'default' | 'secondary' | 'destructive' | 'outline' => {
    switch (executionStatus) {
      case ExecutionStatus.Running:
        return 'default';
      case ExecutionStatus.Completed:
        return 'secondary';
      case ExecutionStatus.Failed:
        return 'destructive';
      default:
        return 'outline';
    }
  };

  const getStatusLabel = (): string => {
    switch (executionStatus) {
      case ExecutionStatus.Idle:
        return 'Idle';
      case ExecutionStatus.Running:
        return 'Running';
      case ExecutionStatus.Completed:
        return 'Completed';
      case ExecutionStatus.Failed:
        return 'Failed';
      case ExecutionStatus.Cancelled:
        return 'Cancelled';
      default:
        return 'Unknown';
    }
  };

  return (
    <div
      className="w-64 border-r flex flex-col"
      style={{
        backgroundColor: 'hsl(var(--background))',
        borderColor: 'hsl(var(--border))',
      }}
    >
      {/* Workflow Name */}
      <div className="p-4 border-b" style={{ borderColor: 'hsl(var(--border))' }}>
        <div className="flex items-center gap-2 mb-2">
          {isEditingName ? (
            <Input
              value={tempName}
              onChange={(e) => setTempName(e.target.value)}
              onBlur={handleNameEdit}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleNameEdit();
                if (e.key === 'Escape') {
                  setIsEditingName(false);
                  setTempName('');
                }
              }}
              autoFocus
              className="text-sm"
            />
          ) : (
            <>
              <h2
                className="text-sm font-semibold flex-1 truncate"
                style={{ color: 'hsl(var(--foreground))' }}
              >
                {workflowName}
              </h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleNameEdit}
                className="h-6 w-6 p-0"
              >
                <Edit2 className="h-3 w-3" />
              </Button>
            </>
          )}
        </div>

        {/* Execution Status Badge */}
        <Badge variant={getStatusBadgeVariant()} className="w-full justify-center">
          {getStatusLabel()}
        </Badge>

        {/* Execution Controls */}
        <div className="flex gap-2 mt-2">
          {!isExecuting ? (
            <Button
              variant="default"
              size="sm"
              className="flex-1 gap-2"
              onClick={handleRunWorkflow}
              disabled={nodes.length === 0}
            >
              <Play className="h-3 w-3" />
              Run
            </Button>
          ) : (
            <Button
              variant="destructive"
              size="sm"
              className="flex-1 gap-2"
              onClick={handleStopExecution}
            >
              <Square className="h-3 w-3" />
              Stop
            </Button>
          )}
        </div>
      </div>

      {/* Add Nodes Section */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4">
          <h3
            className="text-xs font-semibold mb-3 flex items-center gap-2"
            style={{ color: 'hsl(var(--muted-foreground))' }}
          >
            <Plus className="h-3 w-3" />
            Add Node
          </h3>
          <div className="space-y-2">
            {NODE_TYPES.map((nodeType) => {
              const Icon = nodeType.icon;
              return (
                <Button
                  key={nodeType.type}
                  variant="outline"
                  className="w-full justify-start gap-2 h-auto py-2"
                  onClick={() => handleAddNode(nodeType.type)}
                >
                  <Icon className="h-4 w-4" style={{ color: 'hsl(var(--primary))' }} />
                  <div className="flex flex-col items-start">
                    <span className="text-sm font-medium">{nodeType.label}</span>
                    <span
                      className="text-xs"
                      style={{ color: 'hsl(var(--muted-foreground))' }}
                    >
                      {nodeType.description}
                    </span>
                  </div>
                </Button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="p-4 space-y-2 border-t" style={{ borderColor: 'hsl(var(--border))' }}>
        {/* Save */}
        <Button
          variant="default"
          className="w-full justify-start gap-2"
          onClick={handleSaveWorkflow}
        >
          <Save className="h-4 w-4" />
          Save Workflow
        </Button>

        {/* Load */}
        {savedWorkflows.length > 0 && (
          <Select onValueChange={handleLoadWorkflow}>
            <SelectTrigger className="w-full">
              <div className="flex items-center gap-2">
                <FolderOpen className="h-4 w-4" />
                <SelectValue placeholder="Load Workflow" />
              </div>
            </SelectTrigger>
            <SelectContent>
              {savedWorkflows.map((workflow) => (
                <SelectItem key={workflow.id} value={workflow.id}>
                  {workflow.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        {/* Export/Import */}
        <div className="flex gap-2">
          <Button
            variant="outline"
            className="flex-1 justify-start gap-2"
            onClick={handleExportWorkflow}
          >
            <Download className="h-4 w-4" />
            Export
          </Button>
          <Button
            variant="outline"
            className="flex-1 justify-start gap-2"
            onClick={handleImportWorkflow}
          >
            <Upload className="h-4 w-4" />
            Import
          </Button>
        </div>

        {/* Clear */}
        <Button
          variant="destructive"
          className="w-full justify-start gap-2"
          onClick={handleClearWorkflow}
        >
          <Trash2 className="h-4 w-4" />
          Clear Canvas
        </Button>
      </div>
    </div>
  );
}
