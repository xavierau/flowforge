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
  isLoopNode,
  isLLMNode,
  isHumanReviewNode,
  type HttpHeader,
  type HumanReviewPriority,
} from '@/types/workflow';
import { Checkbox } from '@/components/ui/checkbox';
import { Slider } from '@/components/ui/slider';
import { ExpressionBuilder } from '@/components/workflow/ExpressionBuilder';
import {
  getAvailableNodes,
  resolveExpressions,
  hasExpressions,
} from '@/lib/expression-parser';
import { getAvailableModels } from '@/services/model.service';
import type { AvailableModel } from '@/types/workflow';

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
        {isLoopNode(selectedNode.data) && (
          <LoopConfig
            nodeId={selectedNode.id}
            data={selectedNode.data}
            allNodes={nodes}
            edges={edges}
          />
        )}
        {isLLMNode(selectedNode.data) && (
          <LLMConfig
            nodeId={selectedNode.id}
            data={selectedNode.data}
            allNodes={nodes}
            edges={edges}
          />
        )}
        {isHumanReviewNode(selectedNode.data) && (
          <HumanReviewConfig
            nodeId={selectedNode.id}
            data={selectedNode.data}
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

  // State for available models
  const [availableModels, setAvailableModels] = useState<AvailableModel[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState(false);

  // Fetch available models on mount
  useEffect(() => {
    async function loadModels() {
      setIsLoadingModels(true);
      try {
        const response = await getAvailableModels('extraction');
        setAvailableModels(response.models);
      } catch (error) {
        console.error('Failed to load models:', error);
      } finally {
        setIsLoadingModels(false);
      }
    }
    loadModels();
  }, []);

  // Group models by provider
  const modelsByProvider = useMemo(() => {
    const grouped: Record<string, AvailableModel[]> = {};
    for (const model of availableModels) {
      if (!grouped[model.provider]) {
        grouped[model.provider] = [];
      }
      grouped[model.provider].push(model);
    }
    return grouped;
  }, [availableModels]);

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

  // Helper to format provider name for display
  const formatProviderName = (provider: string): string => {
    switch (provider) {
      case 'google':
        return 'Google (Gemini)';
      case 'openai':
        return 'OpenAI (GPT)';
      case 'qwen':
        return 'Qwen';
      case 'deepseek':
        return 'DeepSeek';
      default:
        return provider.charAt(0).toUpperCase() + provider.slice(1);
    }
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

      {/* Model Configuration Section */}
      <div className="space-y-4 pt-4 border-t" style={{ borderColor: 'hsl(var(--border))' }}>
        <h4 className="text-sm font-medium">Model Configuration</h4>
        <p className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
          Leave empty to use workflow defaults
        </p>

        {/* Provider Selection */}
        <div className="space-y-2">
          <Label htmlFor="extraction-provider">Provider</Label>
          <Select
            value={data.config?.provider || ''}
            onValueChange={(value) => {
              handleConfigChange('provider', value || undefined);
              handleConfigChange('model', undefined); // Reset model when provider changes
            }}
            disabled={isLoadingModels}
          >
            <SelectTrigger id="extraction-provider">
              <SelectValue placeholder={isLoadingModels ? 'Loading...' : 'Use workflow default'} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Use workflow default</SelectItem>
              {Object.keys(modelsByProvider).map((provider) => (
                <SelectItem key={provider} value={provider}>
                  {formatProviderName(provider)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Model Selection - only show when provider is selected */}
        {data.config?.provider && (
          <div className="space-y-2">
            <Label htmlFor="extraction-model">Model</Label>
            <Select
              value={data.config?.model || ''}
              onValueChange={(value) => handleConfigChange('model', value || undefined)}
            >
              <SelectTrigger id="extraction-model">
                <SelectValue placeholder="Select model..." />
              </SelectTrigger>
              <SelectContent>
                {modelsByProvider[data.config.provider]?.map((model) => (
                  <SelectItem key={model.modelName} value={model.modelName}>
                    {model.displayName}
                    {model.isDefaultExtraction && ' (Default)'}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Processing Mode Toggle */}
        <div className="space-y-2">
          <Label htmlFor="processing-mode">Processing Mode</Label>
          <Select
            value={data.config?.processingMode || 'batch'}
            onValueChange={(value) => handleConfigChange('processingMode', value)}
          >
            <SelectTrigger id="processing-mode">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="batch">Direct Vision (Recommended)</SelectItem>
              <SelectItem value="markdown">Markdown Pipeline</SelectItem>
            </SelectContent>
          </Select>
          <p className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
            Markdown mode converts images to text first, useful for complex layouts
          </p>
        </div>

        {/* Markdown Converter Settings - only show when markdown mode */}
        {data.config?.processingMode === 'markdown' && (
          <div className="space-y-4 pl-4 border-l-2" style={{ borderColor: 'hsl(var(--border))' }}>
            <div className="space-y-2">
              <Label>Markdown Converter</Label>
              <Select
                value={data.config?.markdownConverter || ''}
                onValueChange={(value) => handleConfigChange('markdownConverter', value || undefined)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Use default converter" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Use default</SelectItem>
                  <SelectItem value="gemini_vision">Gemini Vision</SelectItem>
                  <SelectItem value="gpt4v">GPT-4 Vision</SelectItem>
                  <SelectItem value="qwen_vision">Qwen Vision</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        )}
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

// Loop Config
function LoopConfig({
  nodeId,
  data,
  allNodes,
  edges,
}: {
  nodeId: string;
  data: import('@/types/workflow').LoopNodeData;
  allNodes: import('@/types/workflow').WorkflowNode[];
  edges: import('@/types/workflow').WorkflowEdge[];
}) {
  const { updateNodeData } = useWorkflowStore();

  const availableNodes = useMemo(
    () => getAvailableNodes(nodeId, allNodes, edges),
    [nodeId, allNodes, edges]
  );

  const resolvedExpression = useMemo(
    () =>
      hasExpressions(data.config?.arrayExpression || '')
        ? resolveExpressions(data.config.arrayExpression, allNodes)
        : null,
    [data.config?.arrayExpression, allNodes]
  );

  const handleConfigChange = (key: string, value: unknown) => {
    updateNodeData(nodeId, {
      config: { ...data.config, [key]: value },
    });
  };

  const handleExpressionInsert = (expression: string) => {
    const currentExpression = data.config?.arrayExpression || '';
    handleConfigChange('arrayExpression', currentExpression + expression);
  };

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
            <p className="font-medium mb-1">Loop Node</p>
            <p>
              Iterates over an array and executes downstream nodes for each item.
              Access current item with <code className="text-xs">{`{{$loop.item}}`}</code>
            </p>
          </div>
        </div>
      </div>

      {/* Array Expression */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="array-expression">Array Expression</Label>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Info className="h-4 w-4 text-muted-foreground cursor-help" />
              </TooltipTrigger>
              <TooltipContent>
                <p className="text-xs max-w-xs">
                  Expression that evaluates to an array:
                  <br />
                  <code className="text-xs">{`{{$("Extraction").data.line_items}}`}</code>
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
        <Textarea
          id="array-expression"
          value={data.config?.arrayExpression || ''}
          onChange={(e) => handleConfigChange('arrayExpression', e.target.value)}
          placeholder='{{$("Extraction").data.items}}'
          rows={2}
          className="font-mono text-sm"
        />
        {availableNodes.length > 0 && (
          <ExpressionBuilder
            nodes={availableNodes}
            onInsert={handleExpressionInsert}
            variant="outline"
            size="sm"
          />
        )}
        {resolvedExpression && (
          <div
            className="p-2 rounded border text-xs"
            style={{
              backgroundColor: 'hsl(var(--muted))',
              borderColor: 'hsl(var(--border))',
            }}
          >
            <div className="font-medium mb-1">Preview:</div>
            <div style={{ color: 'hsl(var(--muted-foreground))' }}>
              {resolvedExpression}
            </div>
          </div>
        )}
      </div>

      {/* Max Iterations */}
      <div className="space-y-2">
        <Label htmlFor="max-iterations">Max Iterations</Label>
        <Input
          id="max-iterations"
          type="number"
          value={data.config?.maxIterations || ''}
          onChange={(e) => handleConfigChange('maxIterations', e.target.value ? parseInt(e.target.value, 10) : undefined)}
          placeholder="1000 (default)"
          min={1}
          max={10000}
        />
        <p className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
          Safety limit to prevent infinite loops
        </p>
      </div>

      {/* Continue on Error */}
      <div className="flex items-center space-x-2">
        <Checkbox
          id="continue-on-error"
          checked={data.config?.continueOnError || false}
          onCheckedChange={(checked) => handleConfigChange('continueOnError', checked)}
        />
        <Label htmlFor="continue-on-error" className="text-sm font-normal cursor-pointer">
          Continue on error
        </Label>
      </div>
      <p className="text-xs -mt-2" style={{ color: 'hsl(var(--muted-foreground))' }}>
        If enabled, continues processing remaining items even if one fails
      </p>

      {/* Loop Context Variables */}
      <div
        className="rounded-lg border p-3"
        style={{
          backgroundColor: 'hsl(var(--muted))',
          borderColor: 'hsl(var(--border))',
        }}
      >
        <p className="text-xs font-medium mb-2" style={{ color: 'hsl(var(--foreground))' }}>
          Loop Context Variables:
        </p>
        <div className="grid grid-cols-2 gap-2 text-xs font-mono" style={{ color: 'hsl(var(--muted-foreground))' }}>
          <div>{`{{$loop.item}}`}</div>
          <div>Current item</div>
          <div>{`{{$loop.index}}`}</div>
          <div>Current index (0-based)</div>
          <div>{`{{$loop.first}}`}</div>
          <div>Is first item</div>
          <div>{`{{$loop.last}}`}</div>
          <div>Is last item</div>
          <div>{`{{$loop.length}}`}</div>
          <div>Total array length</div>
        </div>
      </div>
    </div>
  );
}

// LLM Config
function LLMConfig({
  nodeId,
  data,
  allNodes,
  edges,
}: {
  nodeId: string;
  data: import('@/types/workflow').LLMNodeData;
  allNodes: import('@/types/workflow').WorkflowNode[];
  edges: import('@/types/workflow').WorkflowEdge[];
}) {
  const { updateNodeData } = useWorkflowStore();

  // State for API-fetched models
  const [availableModels, setAvailableModels] = useState<
    import('@/services/model.service').AvailableModel[]
  >([]);
  const [availableProviders, setAvailableProviders] = useState<string[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState(false);

  // Load models from API on mount
  useEffect(() => {
    async function loadModels() {
      setIsLoadingModels(true);
      try {
        const { getAvailableModels } = await import('@/services/model.service');
        const response = await getAvailableModels('llm');
        setAvailableModels(response.models);
        setAvailableProviders(response.providers);
      } catch (error) {
        console.error('Failed to load LLM models:', error);
      } finally {
        setIsLoadingModels(false);
      }
    }
    loadModels();
  }, []);

  // Group models by provider
  const modelsByProvider = useMemo(() => {
    const grouped: Record<
      string,
      import('@/services/model.service').AvailableModel[]
    > = {};
    for (const model of availableModels) {
      if (!grouped[model.provider]) {
        grouped[model.provider] = [];
      }
      grouped[model.provider].push(model);
    }
    return grouped;
  }, [availableModels]);

  // Get models for currently selected provider
  const currentModels = data.config?.provider
    ? modelsByProvider[data.config.provider] || []
    : [];

  const availableNodes = useMemo(
    () => getAvailableNodes(nodeId, allNodes, edges),
    [nodeId, allNodes, edges]
  );

  const resolvedPrompt = useMemo(
    () =>
      hasExpressions(data.config?.prompt || '')
        ? resolveExpressions(data.config.prompt, allNodes)
        : null,
    [data.config?.prompt, allNodes]
  );

  const handleConfigChange = (key: string, value: unknown) => {
    updateNodeData(nodeId, {
      config: { ...data.config, [key]: value },
    });
  };

  const handlePromptExpressionInsert = (expression: string) => {
    const currentPrompt = data.config?.prompt || '';
    handleConfigChange('prompt', currentPrompt + expression);
  };

  // Provider display name mapping
  const providerDisplayNames: Record<string, string> = {
    google: 'Google (Gemini)',
    openai: 'OpenAI (GPT)',
    qwen: 'Qwen',
    deepseek: 'DeepSeek',
  };

  return (
    <div className="space-y-4">
      {/* Provider Selection */}
      <div className="space-y-2">
        <Label htmlFor="llm-provider">Provider</Label>
        <Select
          value={data.config?.provider || ''}
          onValueChange={(value) => {
            handleConfigChange('provider', value);
            // Reset model when provider changes
            handleConfigChange('model', '');
          }}
          disabled={isLoadingModels}
        >
          <SelectTrigger id="llm-provider">
            <SelectValue
              placeholder={isLoadingModels ? 'Loading providers...' : 'Select provider...'}
            />
          </SelectTrigger>
          <SelectContent>
            {availableProviders.map((provider) => (
              <SelectItem key={provider} value={provider}>
                {providerDisplayNames[provider] || provider}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Model Selection */}
      <div className="space-y-2">
        <Label htmlFor="llm-model">Model</Label>
        <Select
          value={data.config?.model || ''}
          onValueChange={(value) => handleConfigChange('model', value)}
          disabled={!data.config?.provider || isLoadingModels}
        >
          <SelectTrigger id="llm-model">
            <SelectValue
              placeholder={
                isLoadingModels
                  ? 'Loading models...'
                  : data.config?.provider
                    ? 'Select model...'
                    : 'Select provider first'
              }
            />
          </SelectTrigger>
          <SelectContent>
            {currentModels.map((model) => (
              <SelectItem key={model.modelName} value={model.modelName}>
                {model.displayName}
                {model.isDefaultLlm && ' (Default)'}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* System Prompt */}
      <div className="space-y-2">
        <Label htmlFor="system-prompt">System Prompt (Optional)</Label>
        <Textarea
          id="system-prompt"
          value={data.config?.systemPrompt || ''}
          onChange={(e) => handleConfigChange('systemPrompt', e.target.value)}
          placeholder="You are a helpful assistant..."
          rows={3}
        />
        <p className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
          Sets the context and behavior for the LLM
        </p>
      </div>

      {/* Main Prompt */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="llm-prompt">Prompt</Label>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Info className="h-4 w-4 text-muted-foreground cursor-help" />
              </TooltipTrigger>
              <TooltipContent>
                <p className="text-xs max-w-xs">
                  Use expressions to include data from previous nodes:
                  <br />
                  <code className="text-xs">{`{{$("NodeName").data.field}}`}</code>
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
        <Textarea
          id="llm-prompt"
          value={data.config?.prompt || ''}
          onChange={(e) => handleConfigChange('prompt', e.target.value)}
          placeholder="Analyze the following data and provide a summary..."
          rows={4}
        />
        {availableNodes.length > 0 && (
          <ExpressionBuilder
            nodes={availableNodes}
            onInsert={handlePromptExpressionInsert}
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

      {/* Temperature Slider */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>Temperature</Label>
          <span className="text-sm" style={{ color: 'hsl(var(--muted-foreground))' }}>
            {data.config?.temperature ?? 0.7}
          </span>
        </div>
        <Slider
          value={[data.config?.temperature ?? 0.7]}
          onValueChange={(values: number[]) => handleConfigChange('temperature', values[0])}
          min={0}
          max={2}
          step={0.1}
          className="w-full"
        />
        <p className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
          Lower = more focused, Higher = more creative
        </p>
      </div>

      {/* Max Tokens */}
      <div className="space-y-2">
        <Label htmlFor="max-tokens">Max Tokens</Label>
        <Input
          id="max-tokens"
          type="number"
          value={data.config?.maxTokens || ''}
          onChange={(e) => handleConfigChange('maxTokens', e.target.value ? parseInt(e.target.value, 10) : undefined)}
          placeholder="1024 (default)"
          min={1}
          max={8192}
        />
        <p className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
          Maximum length of the generated response
        </p>
      </div>
    </div>
  );
}

// HumanReview Config
function HumanReviewConfig({
  nodeId,
  data,
}: {
  nodeId: string;
  data: import('@/types/workflow').HumanReviewNodeData;
}) {
  const { updateNodeData } = useWorkflowStore();
  const [newField, setNewField] = useState('');

  const handleConfigChange = (key: string, value: unknown) => {
    updateNodeData(nodeId, {
      config: { ...data.config, [key]: value },
    });
  };

  const addRequiredField = () => {
    if (newField.trim()) {
      const currentFields = data.config?.requiredFields || [];
      handleConfigChange('requiredFields', [...currentFields, newField.trim()]);
      setNewField('');
    }
  };

  const removeRequiredField = (index: number) => {
    const currentFields = data.config?.requiredFields || [];
    handleConfigChange('requiredFields', currentFields.filter((_, i) => i !== index));
  };

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
            <p className="font-medium mb-1">Human Review (HITL)</p>
            <p>
              Pauses workflow execution for human review and approval.
              The reviewer can approve or reject to continue different paths.
            </p>
          </div>
        </div>
      </div>

      {/* Instructions */}
      <div className="space-y-2">
        <Label htmlFor="instructions">Review Instructions</Label>
        <Textarea
          id="instructions"
          value={data.config?.instructions || ''}
          onChange={(e) => handleConfigChange('instructions', e.target.value)}
          placeholder="Please review the extracted data and verify accuracy..."
          rows={4}
        />
        <p className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
          Instructions displayed to the human reviewer
        </p>
      </div>

      {/* Priority */}
      <div className="space-y-2">
        <Label htmlFor="priority">Priority</Label>
        <Select
          value={data.config?.priority || 'normal'}
          onValueChange={(value) => handleConfigChange('priority', value as HumanReviewPriority)}
        >
          <SelectTrigger id="priority">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="critical">
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-red-600" />
                Critical
              </span>
            </SelectItem>
            <SelectItem value="high">
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-orange-500" />
                High
              </span>
            </SelectItem>
            <SelectItem value="normal">
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                Normal
              </span>
            </SelectItem>
            <SelectItem value="low">
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-gray-500" />
                Low
              </span>
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Timeout Hours */}
      <div className="space-y-2">
        <Label htmlFor="timeout-hours">Timeout (Hours)</Label>
        <Input
          id="timeout-hours"
          type="number"
          value={data.config?.timeoutHours || ''}
          onChange={(e) => handleConfigChange('timeoutHours', e.target.value ? parseInt(e.target.value, 10) : undefined)}
          placeholder="4 (default)"
          min={1}
          max={168}
        />
        <p className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
          Hours before the review task escalates or times out
        </p>
      </div>

      {/* Required Fields */}
      <div className="space-y-2">
        <Label>Required Fields (Optional)</Label>
        <p className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
          Fields that must be reviewed before approval
        </p>

        {/* Existing Fields */}
        {(data.config?.requiredFields || []).length > 0 && (
          <div className="space-y-2 mb-2">
            {(data.config?.requiredFields || []).map((field, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 p-2 rounded border"
                style={{
                  backgroundColor: 'hsl(var(--muted))',
                  borderColor: 'hsl(var(--border))',
                }}
              >
                <span className="text-xs flex-1" style={{ color: 'hsl(var(--foreground))' }}>
                  {field}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeRequiredField(idx)}
                  className="h-6 w-6 p-0"
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
        )}

        {/* Add New Field */}
        <div className="flex gap-2">
          <Input
            placeholder="Field name (e.g., total_amount)"
            value={newField}
            onChange={(e) => setNewField(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                addRequiredField();
              }
            }}
          />
          <Button
            variant="outline"
            size="sm"
            onClick={addRequiredField}
            disabled={!newField.trim()}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </div>

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
            <p className="font-medium mb-2">Output Paths:</p>
          </div>
        </div>
        <div className="space-y-2 pl-6">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full" style={{ backgroundColor: '#22c55e' }} />
            <span className="text-xs font-semibold" style={{ color: '#22c55e' }}>
              Approved
            </span>
            <span className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
              - Reviewer approved the data
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full" style={{ backgroundColor: '#ef4444' }} />
            <span className="text-xs font-semibold" style={{ color: '#ef4444' }}>
              Rejected
            </span>
            <span className="text-xs" style={{ color: 'hsl(var(--muted-foreground))' }}>
              - Reviewer rejected the data
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
