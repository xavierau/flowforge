/**
 * NodeConfigPanel - Right sidebar for node configuration
 * Dynamic form based on selected node type
 */

import { useEffect, useState, useMemo } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { python } from '@codemirror/lang-python';
import { githubDark } from '@uiw/codemirror-theme-github';
import {
  AlertCircle,
  Trash2,
  Plus,
  X,
  Info,
  Braces,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useWorkflowStore } from '@/store/workflowStore';
import {
  HttpMethod,
  isHttpTriggerNode,
  isExtractionNode,
  isPythonRunnerNode,
  isHttpRequestNode,
  isIfNode,
  isJoinNode,
  type HttpHeader,
} from '@/types/workflow';
import { ExpressionBuilder } from '@/components/workflow/ExpressionBuilder';
import {
  getAvailableNodes,
  resolveExpressions,
  hasExpressions,
} from '@/lib/expression-parser';

export function NodeConfigPanel() {
  const {
    nodes,
    edges,
    selectedNodeId,
    updateNodeData,
    deleteNode,
    setSelectedNode,
  } = useWorkflowStore();

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);

  // Close panel if node deleted
  useEffect(() => {
    if (selectedNodeId && !selectedNode) {
      setSelectedNode(null);
    }
  }, [selectedNode, selectedNodeId, setSelectedNode]);

  if (!selectedNode) return null;

  const handleLabelChange = (label: string) => {
    updateNodeData(selectedNode.id, { label });
  };

  const handleDelete = () => {
    if (
      window.confirm(
        `Are you sure you want to delete "${selectedNode.data.label}"?`
      )
    ) {
      deleteNode(selectedNode.id);
    }
  };

  return (
    <div
      className="w-80 border-l flex flex-col"
      style={{
        backgroundColor: 'hsl(var(--background))',
        borderColor: 'hsl(var(--border))',
      }}
    >
      {/* Header */}
      <div className="p-4 border-b" style={{ borderColor: 'hsl(var(--border))' }}>
        <div className="flex items-center justify-between mb-3">
          <h3
            className="text-sm font-semibold"
            style={{ color: 'hsl(var(--foreground))' }}
          >
            Node Configuration
          </h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelectedNode(null)}
            className="h-6 w-6 p-0"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Node Name */}
        <div className="space-y-2">
          <Label htmlFor="node-label">Node Name</Label>
          <Input
            id="node-label"
            value={selectedNode.data.label}
            onChange={(e) => handleLabelChange(e.target.value)}
            placeholder="Enter node name"
          />
        </div>
      </div>

      {/* Configuration Form */}
      <div className="flex-1 overflow-y-auto p-4">
        {isHttpTriggerNode(selectedNode.data) && <HttpTriggerConfig />}
        {isExtractionNode(selectedNode.data) && (
          <ExtractionConfig
            nodeId={selectedNode.id}
            data={selectedNode.data}
            allNodes={nodes}
            edges={edges}
          />
        )}
        {isPythonRunnerNode(selectedNode.data) && (
          <PythonRunnerConfig nodeId={selectedNode.id} data={selectedNode.data} />
        )}
        {isHttpRequestNode(selectedNode.data) && (
          <HttpRequestConfig
            nodeId={selectedNode.id}
            data={selectedNode.data}
            allNodes={nodes}
            edges={edges}
          />
        )}
        {isIfNode(selectedNode.data) && (
          <IfConfig
            nodeId={selectedNode.id}
            data={selectedNode.data}
            allNodes={nodes}
            edges={edges}
          />
        )}
        {isJoinNode(selectedNode.data) && (
          <JoinConfig
            nodeId={selectedNode.id}
            edges={edges}
            allNodes={nodes}
          />
        )}

        {/* Validation Errors */}
        {selectedNode.data.errors.length > 0 && (
          <div
            className="mt-4 p-3 rounded-lg border"
            style={{
              backgroundColor: 'hsl(var(--destructive) / 0.1)',
              borderColor: 'hsl(var(--destructive))',
            }}
          >
            <div className="flex items-start gap-2">
              <AlertCircle
                className="h-4 w-4 mt-0.5 flex-shrink-0"
                style={{ color: 'hsl(var(--destructive))' }}
              />
              <div className="space-y-1">
                {selectedNode.data.errors.map((error, idx) => (
                  <p
                    key={idx}
                    className="text-xs"
                    style={{ color: 'hsl(var(--destructive))' }}
                  >
                    {error.message}
                  </p>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t" style={{ borderColor: 'hsl(var(--border))' }}>
        <Button
          variant="destructive"
          className="w-full justify-start gap-2"
          onClick={handleDelete}
        >
          <Trash2 className="h-4 w-4" />
          Delete Node
        </Button>
      </div>
    </div>
  );
}

// HttpTrigger Config (no configuration needed)
function HttpTriggerConfig() {
  return (
    <div
      className="p-3 rounded-lg border"
      style={{
        backgroundColor: 'hsl(var(--muted))',
        borderColor: 'hsl(var(--border))',
      }}
    >
      <div className="flex items-start gap-2">
        <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
        <div className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
          <p className="font-medium mb-1">HTTP Trigger Node</p>
          <p>
            This node acts as the workflow entry point. It accepts HTTP requests
            with the following data structure:
          </p>
          <pre className="mt-2 p-2 rounded" style={{ backgroundColor: 'hsl(var(--background))' }}>
{`{
  "prompt": "string",
  "file_url": "string (optional)",
  "base64": "string (optional)",
  "callback_url": "string (optional)"
}`}
          </pre>
        </div>
      </div>
    </div>
  );
}

// Extraction Config
function ExtractionConfig({
  nodeId,
  data,
  allNodes,
  edges,
}: {
  nodeId: string;
  data: import('@/types/workflow').ExtractionNodeData;
  allNodes: import('@/types/workflow').WorkflowNode[];
  edges: import('@/types/workflow').WorkflowEdge[];
}) {
  const { updateNodeData } = useWorkflowStore();

  const availableNodes = useMemo(
    () => getAvailableNodes(nodeId, allNodes, edges),
    [nodeId, allNodes, edges]
  );

  const resolvedPrompt = useMemo(
    () =>
      hasExpressions(data.config.prompt)
        ? resolveExpressions(data.config.prompt, allNodes)
        : null,
    [data.config.prompt, allNodes]
  );

  const handleConfigChange = (key: string, value: unknown) => {
    updateNodeData(nodeId, {
      config: { ...data.config, [key]: value },
    });
  };

  const handleExpressionInsert = (expression: string) => {
    const currentPrompt = data.config.prompt;
    handleConfigChange('prompt', currentPrompt + expression);
  };

  return (
    <div className="space-y-4">
      {/* File Source */}
      <div className="space-y-2">
        <Label htmlFor="file-source">File Source</Label>
        <Select
          value={data.config.fileSource}
          onValueChange={(value) => handleConfigChange('fileSource', value)}
        >
          <SelectTrigger id="file-source">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="previous_node">Previous Node</SelectItem>
            <SelectItem value="url">URL</SelectItem>
            <SelectItem value="base64">Base64</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Prompt */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="prompt">Extraction Prompt</Label>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Info className="h-4 w-4 text-muted-foreground cursor-help" />
              </TooltipTrigger>
              <TooltipContent>
                <p className="text-xs max-w-xs">
                  Use expressions to reference previous node data:
                  <br />
                  <code className="text-xs">{'{{$("NodeName").data.field}}'}</code>
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
        <Textarea
          id="prompt"
          value={data.config.prompt}
          onChange={(e) => handleConfigChange('prompt', e.target.value)}
          placeholder="Enter extraction instructions..."
          rows={4}
        />
        {availableNodes.length > 0 && (
          <ExpressionBuilder
            nodes={availableNodes}
            onInsert={handleExpressionInsert}
            variant="outline"
            size="sm"
          />
        )}
        {resolvedPrompt && (
          <div
            className="p-2 rounded border text-xs"
            style={{
              backgroundColor: 'hsl(var(--muted))',
              borderColor: 'hsl(var(--border))',
            }}
          >
            <div className="font-medium mb-1">Preview:</div>
            <div style={{ color: 'hsl(var(--muted-foreground))' }}>
              {resolvedPrompt}
            </div>
          </div>
        )}
      </div>

      {/* Schema */}
      <div className="space-y-2">
        <Label htmlFor="schema">Extraction Schema</Label>
        <Select
          value={data.config.schemaId}
          onValueChange={(value) => handleConfigChange('schemaId', value)}
        >
          <SelectTrigger id="schema">
            <SelectValue placeholder="Select schema..." />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="invoice">Invoice Schema</SelectItem>
            <SelectItem value="receipt">Receipt Schema</SelectItem>
            <SelectItem value="custom">Custom Schema</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}

// PythonRunner Config
function PythonRunnerConfig({
  nodeId,
  data,
}: {
  nodeId: string;
  data: import('@/types/workflow').PythonRunnerNodeData;
}) {
  const { updateNodeData } = useWorkflowStore();

  const handleCodeChange = (value: string) => {
    updateNodeData(nodeId, {
      config: { ...data.config, code: value },
    });
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Python Code</Label>
        <div
          className="text-xs mb-2 p-2 rounded"
          style={{
            backgroundColor: 'hsl(var(--muted))',
            color: 'hsl(var(--muted-foreground))',
          }}
        >
          <p className="font-medium mb-1">Input format:</p>
          <code>{'{ "data": extraction_result }'}</code>
          <p className="font-medium mt-2 mb-1">Must return an object</p>
        </div>
        <div className="border rounded-lg overflow-hidden" style={{ borderColor: 'hsl(var(--border))' }}>
          <CodeMirror
            value={data.config.code}
            height="400px"
            extensions={[python()]}
            theme={githubDark}
            onChange={handleCodeChange}
            basicSetup={{
              lineNumbers: true,
              highlightActiveLineGutter: true,
              highlightActiveLine: true,
              foldGutter: true,
            }}
          />
        </div>
      </div>
    </div>
  );
}

// HttpRequest Config
function HttpRequestConfig({
  nodeId,
  data,
  allNodes,
  edges,
}: {
  nodeId: string;
  data: import('@/types/workflow').HttpRequestNodeData;
  allNodes: import('@/types/workflow').WorkflowNode[];
  edges: import('@/types/workflow').WorkflowEdge[];
}) {
  const { updateNodeData } = useWorkflowStore();
  const [newHeaderKey, setNewHeaderKey] = useState('');
  const [newHeaderValue, setNewHeaderValue] = useState('');

  const availableNodes = useMemo(
    () => getAvailableNodes(nodeId, allNodes, edges),
    [nodeId, allNodes, edges]
  );

  const resolvedUrl = useMemo(
    () =>
      hasExpressions(data.config.url)
        ? resolveExpressions(data.config.url, allNodes)
        : null,
    [data.config.url, allNodes]
  );

  const handleConfigChange = (key: string, value: unknown) => {
    updateNodeData(nodeId, {
      config: { ...data.config, [key]: value },
    });
  };

  const handleUrlExpressionInsert = (expression: string) => {
    const currentUrl = data.config.url;
    handleConfigChange('url', currentUrl + expression);
  };

  const handleHeaderValueExpressionInsert = (expression: string) => {
    const currentValue = newHeaderValue;
    setNewHeaderValue(currentValue + expression);
  };

  const addHeader = () => {
    if (newHeaderKey.trim() && newHeaderValue.trim()) {
      const newHeader: HttpHeader = {
        key: newHeaderKey.trim(),
        value: newHeaderValue.trim(),
        enabled: true,
      };
      handleConfigChange('headers', [...data.config.headers, newHeader]);
      setNewHeaderKey('');
      setNewHeaderValue('');
    }
  };

  const removeHeader = (index: number) => {
    const updatedHeaders = data.config.headers.filter((_, i) => i !== index);
    handleConfigChange('headers', updatedHeaders);
  };

  const toggleHeader = (index: number) => {
    const updatedHeaders = data.config.headers.map((header, i) =>
      i === index ? { ...header, enabled: !header.enabled } : header
    );
    handleConfigChange('headers', updatedHeaders);
  };

  return (
    <div className="space-y-4">
      {/* Expression Syntax Help */}
      <div
        className="p-3 rounded-lg border"
        style={{
          backgroundColor: 'hsl(var(--muted))',
          borderColor: 'hsl(var(--border))',
        }}
      >
        <div className="flex items-start gap-2">
          <Braces className="h-4 w-4 mt-0.5 flex-shrink-0" />
          <div className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
            <p className="font-medium mb-1">Expression Syntax</p>
            <p>
              Reference data from previous nodes using:
              <br />
              <code className="text-xs">{'{{$("NodeName").data.field}}'}</code>
            </p>
          </div>
        </div>
      </div>

      {/* URL */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="url">URL</Label>
          {availableNodes.length > 0 && (
            <ExpressionBuilder
              nodes={availableNodes}
              onInsert={handleUrlExpressionInsert}
              variant="ghost"
              size="sm"
            />
          )}
        </div>
        <Input
          id="url"
          type="url"
          value={data.config.url}
          onChange={(e) => handleConfigChange('url', e.target.value)}
          placeholder="https://api.example.com/endpoint"
        />
        {resolvedUrl && (
          <div
            className="p-2 rounded border text-xs"
            style={{
              backgroundColor: 'hsl(var(--muted))',
              borderColor: 'hsl(var(--border))',
            }}
          >
            <div className="font-medium mb-1">Preview:</div>
            <div
              className="break-all"
              style={{ color: 'hsl(var(--muted-foreground))' }}
            >
              {resolvedUrl}
            </div>
          </div>
        )}
      </div>

      {/* Method */}
      <div className="space-y-2">
        <Label htmlFor="method">HTTP Method</Label>
        <Select
          value={data.config.method}
          onValueChange={(value) => handleConfigChange('method', value)}
        >
          <SelectTrigger id="method">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.values(HttpMethod).map((method) => (
              <SelectItem key={method} value={method}>
                {method}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Headers */}
      <div className="space-y-2">
        <Label>Headers</Label>

        {/* Existing Headers */}
        {data.config.headers.length > 0 && (
          <div className="space-y-2 mb-2">
            {data.config.headers.map((header, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 p-2 rounded border"
                style={{
                  backgroundColor: header.enabled
                    ? 'hsl(var(--muted))'
                    : 'hsl(var(--muted) / 0.5)',
                  borderColor: 'hsl(var(--border))',
                }}
              >
                <input
                  type="checkbox"
                  checked={header.enabled}
                  onChange={() => toggleHeader(idx)}
                  className="rounded"
                />
                <div className="flex-1 text-xs">
                  <div
                    className="font-medium"
                    style={{
                      color: header.enabled
                        ? 'hsl(var(--foreground))'
                        : 'hsl(var(--muted-foreground))',
                    }}
                  >
                    {header.key}
                  </div>
                  <div style={{ color: 'hsl(var(--muted-foreground))' }}>
                    {header.value}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeHeader(idx)}
                  className="h-6 w-6 p-0"
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
        )}

        {/* Add New Header */}
        <div className="space-y-2">
          <Input
            placeholder="Header key (e.g., Authorization)"
            value={newHeaderKey}
            onChange={(e) => setNewHeaderKey(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') addHeader();
            }}
          />
          <div className="space-y-1">
            <Input
              placeholder="Header value"
              value={newHeaderValue}
              onChange={(e) => setNewHeaderValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') addHeader();
              }}
            />
            {availableNodes.length > 0 && (
              <ExpressionBuilder
                nodes={availableNodes}
                onInsert={handleHeaderValueExpressionInsert}
                variant="ghost"
                size="sm"
              />
            )}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={addHeader}
            className="w-full gap-2"
            disabled={!newHeaderKey.trim() || !newHeaderValue.trim()}
          >
            <Plus className="h-3 w-3" />
            Add Header
          </Button>
        </div>
      </div>
    </div>
  );
}

// If Config
function IfConfig({
  nodeId,
  data,
  allNodes,
  edges,
}: {
  nodeId: string;
  data: import('@/types/workflow').IfNodeData;
  allNodes: import('@/types/workflow').WorkflowNode[];
  edges: import('@/types/workflow').WorkflowEdge[];
}) {
  const [showExpressionBuilder, setShowExpressionBuilder] = useState(false);
  const { updateNodeData } = useWorkflowStore();

  const availableNodes = useMemo(
    () => getAvailableNodes(nodeId, allNodes, edges),
    [nodeId, allNodes, edges]
  );

  const resolvedCondition = useMemo(
    () =>
      hasExpressions(data.config?.condition || '')
        ? resolveExpressions(data.config.condition, allNodes)
        : null,
    [data.config?.condition, allNodes]
  );

  const handleConfigChange = (key: string, value: unknown) => {
    updateNodeData(nodeId, {
      config: { ...data.config, [key]: value },
    });
  };

  const handleExpressionInsert = (expression: string) => {
    const currentCondition = data.config?.condition || '';
    handleConfigChange('condition', currentCondition + expression);
  };

  return (
    <div className="space-y-4">
      {/* Condition */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="condition">Condition</Label>
          <div className="flex gap-1">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-6 w-6">
                    <Info className="h-3 w-3" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent className="max-w-sm">
                  <p className="text-xs">
                    Use comparison operators: &gt;, &lt;, &gt;=, &lt;=, ==, !=
                    <br />
                    Logical operators: && (AND), || (OR)
                    <br />
                    Example: {`{{$("Extraction").data.total}} > 100`}
                    <br />
                    Complex: {`({{$("Extraction").data.amount}} > 1000) || ({{$("Extraction").data.priority}} == "high")`}
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => setShowExpressionBuilder(!showExpressionBuilder)}
            >
              <Braces className="h-3 w-3" />
            </Button>
          </div>
        </div>
        <Textarea
          id="condition"
          value={data.config?.condition || ''}
          onChange={(e) => handleConfigChange('condition', e.target.value)}
          placeholder='{{$("Extraction").data.total}} > 100'
          rows={4}
          className="font-mono text-sm"
        />
        {resolvedCondition && (
          <div className="space-y-1">
            <p className="text-xs font-medium" style={{ color: 'hsl(var(--muted-foreground))' }}>
              Preview (with current data):
            </p>
            <p className="text-xs font-mono p-2 rounded" style={{ backgroundColor: 'hsl(var(--muted))' }}>
              {resolvedCondition}
            </p>
          </div>
        )}
      </div>

      {/* Expression Builder */}
      {showExpressionBuilder && (
        <ExpressionBuilder
          nodes={availableNodes}
          onInsert={handleExpressionInsert}
        />
      )}

      {/* Output Info */}
      <div
        className="rounded-lg border p-3 space-y-3"
        style={{
          backgroundColor: 'hsl(var(--muted))',
          borderColor: 'hsl(var(--border))',
        }}
      >
        <div className="flex items-start gap-2">
          <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
          <div className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
            <p className="font-medium mb-2">Conditional Branching:</p>
            <p className="mb-2">
              This node evaluates the condition and routes to one of two paths:
            </p>
          </div>
        </div>
        <div className="space-y-2 pl-6">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full" style={{ backgroundColor: '#22c55e' }} />
            <span className="text-xs font-semibold" style={{ color: '#22c55e' }}>
              True
            </span>
            <span className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
              - When condition evaluates to true
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full" style={{ backgroundColor: '#ef4444' }} />
            <span className="text-xs font-semibold" style={{ color: '#ef4444' }}>
              False
            </span>
            <span className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
              - When condition evaluates to false
            </span>
          </div>
        </div>
      </div>

      {/* Operators Reference */}
      <div
        className="rounded-lg border p-3"
        style={{
          backgroundColor: 'hsl(var(--muted))',
          borderColor: 'hsl(var(--border))',
        }}
      >
        <p className="text-xs font-medium mb-2" style={{ color: 'hsl(var(--foreground))' }}>
          Available Operators:
        </p>
        <div className="grid grid-cols-2 gap-2 text-xs font-mono" style={{ color: 'hsl(var(--muted-foreground))' }}>
          <div>&gt; (greater than)</div>
          <div>&lt; (less than)</div>
          <div>&gt;= (greater or equal)</div>
          <div>&lt;= (less or equal)</div>
          <div>== (equals)</div>
          <div>!= (not equals)</div>
          <div>&amp;&amp; (AND)</div>
          <div>|| (OR)</div>
        </div>
      </div>
    </div>
  );
}

// Join Config
function JoinConfig({
  nodeId,
  edges,
  allNodes,
}: {
  nodeId: string;
  edges: import('@/types/workflow').WorkflowEdge[];
  allNodes: import('@/types/workflow').WorkflowNode[];
}) {
  // Get incoming edges to this node
  const incomingEdges = edges.filter((edge) => edge.target === nodeId);
  const upstreamNodes = incomingEdges
    .map((edge) => allNodes.find((node) => node.id === edge.source))
    .filter((node): node is import('@/types/workflow').WorkflowNode => node !== undefined);

  return (
    <div className="space-y-4">
      {/* Info Section */}
      <div
        className="p-3 rounded-lg border"
        style={{
          backgroundColor: 'hsl(var(--muted))',
          borderColor: 'hsl(var(--border))',
        }}
      >
        <div className="flex items-start gap-2">
          <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
          <div className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
            <p className="font-medium mb-1">Join Node (Synchronization Barrier)</p>
            <p className="mb-2">
              This node waits for ALL incoming branches to complete before executing downstream tasks.
              It aggregates outputs from all upstream nodes.
            </p>
            <p className="font-medium">Maps to Conductor's JOIN task type</p>
          </div>
        </div>
      </div>

      {/* Upstream Nodes */}
      <div className="space-y-2">
        <Label>Waiting For ({upstreamNodes.length} node{upstreamNodes.length !== 1 ? 's' : ''})</Label>
        {upstreamNodes.length === 0 ? (
          <div
            className="p-3 rounded border text-xs text-center"
            style={{
              backgroundColor: 'hsl(var(--muted) / 0.5)',
              borderColor: 'hsl(var(--border))',
              color: 'hsl(var(--muted-foreground))',
            }}
          >
            No incoming connections. Connect nodes to this Join node to create a synchronization point.
          </div>
        ) : (
          <div className="space-y-2">
            {upstreamNodes.map((node) => (
              <div
                key={node.id}
                className="flex items-center gap-2 p-2 rounded border"
                style={{
                  backgroundColor: 'hsl(var(--muted) / 0.5)',
                  borderColor: 'hsl(var(--border))',
                }}
              >
                <div
                  className="w-2 h-2 rounded-full"
                  style={{
                    backgroundColor: node.data.isValid ? '#3b82f6' : '#ef4444',
                  }}
                />
                <span className="text-xs font-medium" style={{ color: 'hsl(var(--foreground))' }}>
                  {node.data.label}
                </span>
                <span
                  className="text-xs ml-auto"
                  style={{ color: 'hsl(var(--muted-foreground))' }}
                >
                  {node.data.type}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Behavior Info */}
      <div
        className="rounded-lg border p-3"
        style={{
          backgroundColor: 'hsl(var(--muted))',
          borderColor: 'hsl(var(--border))',
        }}
      >
        <p className="text-xs font-medium mb-2" style={{ color: 'hsl(var(--foreground))' }}>
          Execution Behavior:
        </p>
        <ul className="list-disc list-inside space-y-1 text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
          <li>Blocks execution until ALL upstream nodes complete</li>
          <li>Handles asynchronous arrival (nodes may complete at different times)</li>
          <li>Aggregates outputs into a single map structure</li>
          <li>Downstream nodes can access data from all joined branches</li>
        </ul>
      </div>

      {/* Output Format */}
      <div
        className="rounded-lg border p-3"
        style={{
          backgroundColor: 'hsl(var(--muted) / 0.5)',
          borderColor: 'hsl(var(--border))',
        }}
      >
        <p className="text-xs font-medium mb-2" style={{ color: 'hsl(var(--foreground))' }}>
          Output Format (Conductor):
        </p>
        <pre
          className="text-xs p-2 rounded overflow-x-auto"
          style={{
            backgroundColor: 'hsl(var(--background))',
            color: 'hsl(var(--muted-foreground))',
          }}
        >
{`{
  "upstream_node_1_ref": {
    "output": {...}
  },
  "upstream_node_2_ref": {
    "output": {...}
  }
}`}
        </pre>
      </div>
    </div>
  );
}
