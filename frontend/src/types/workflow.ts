/**
 * Workflow Builder Type Definitions
 * Comprehensive types for n8n-style workflow system
 */

import type { Node, Edge } from '@xyflow/react';

/**
 * Node types available in the workflow builder
 */
export enum NodeType {
  HttpTrigger = 'httpTrigger',
  Extraction = 'extraction',
  PythonRunner = 'pythonRunner',
  HttpRequest = 'httpRequest',
  If = 'if',
  Join = 'join',
}

/**
 * HTTP methods for HttpRequest nodes
 */
export enum HttpMethod {
  GET = 'GET',
  POST = 'POST',
  PUT = 'PUT',
  DELETE = 'DELETE',
}

/**
 * Validation error structure
 */
export interface ValidationError {
  field: string;
  message: string;
}

/**
 * Base node data interface with common properties
 */
export interface BaseNodeData extends Record<string, unknown> {
  label: string;
  type: NodeType;
  isValid: boolean;
  errors: ValidationError[];
  /**
   * Runtime output data from node execution (for expression resolution)
   * Structure: { data: { field1: value1, field2: value2, ... } }
   */
  outputData?: {
    data: Record<string, unknown>;
  };
}

/**
 * HttpTrigger node configuration
 * Entry point for workflow - accepts webhook data at runtime
 */
export interface HttpTriggerNodeData extends BaseNodeData {
  type: NodeType.HttpTrigger;
  // No configuration needed - runtime data structure:
  // { prompt: string, file_url?: string, base64?: string, callback_url?: string }
}

/**
 * Extraction node configuration
 */
export interface ExtractionNodeData extends BaseNodeData {
  type: NodeType.Extraction;
  config: {
    fileSource: 'previous_node' | 'url' | 'base64';
    prompt: string;
    schemaId: string; // Reference to schema in system
  };
}

/**
 * PythonRunner node configuration
 */
export interface PythonRunnerNodeData extends BaseNodeData {
  type: NodeType.PythonRunner;
  config: {
    code: string; // Python code to execute
  };
}

/**
 * HTTP header key-value pair
 */
export interface HttpHeader {
  key: string;
  value: string;
  enabled: boolean;
}

/**
 * HttpRequest node configuration
 */
export interface HttpRequestNodeData extends BaseNodeData {
  type: NodeType.HttpRequest;
  config: {
    url: string;
    method: HttpMethod;
    headers: HttpHeader[];
  };
}

/**
 * If node configuration
 * Evaluates a condition and branches to True or False paths
 */
export interface IfNodeData extends BaseNodeData {
  type: NodeType.If;
  config: {
    condition: string; // Expression like "{{$('Node').data.field}} > 100"
  };
}

/**
 * Join node configuration
 * Synchronization barrier - waits for ALL incoming branches to complete
 * Maps to Conductor's JOIN task type
 */
export interface JoinNodeData extends BaseNodeData {
  type: NodeType.Join;
  // No configuration needed - automatically waits for all incoming edges
  // Output: Aggregated map of all upstream task outputs
}

/**
 * Union type for all node data types
 */
export type WorkflowNodeData =
  | HttpTriggerNodeData
  | ExtractionNodeData
  | PythonRunnerNodeData
  | HttpRequestNodeData
  | IfNodeData
  | JoinNodeData;

/**
 * Workflow node with typed data
 */
export type WorkflowNode = Node<WorkflowNodeData>;

/**
 * Workflow edge (connection between nodes)
 */
export type WorkflowEdge = Edge;

/**
 * Complete workflow definition
 */
export interface Workflow {
  id: string;
  name: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  createdAt: string;
  updatedAt: string;
}

/**
 * Workflow execution context (runtime data)
 * Each node can access previous node results
 */
export interface WorkflowExecutionContext {
  [nodeId: string]: {
    data: unknown;
  };
}

/**
 * Saved workflows in localStorage
 */
export interface SavedWorkflows {
  [workflowId: string]: Workflow;
}

/**
 * Workflow execution status
 */
export enum ExecutionStatus {
  Idle = 'idle',
  Running = 'running',
  Completed = 'completed',
  Failed = 'failed',
  Cancelled = 'cancelled',
}

/**
 * Node execution status within a workflow execution
 */
export enum NodeExecutionStatus {
  Pending = 'pending',
  Running = 'running',
  Success = 'success',
  Error = 'error',
  Skipped = 'skipped',
}

/**
 * Individual node execution state
 */
export interface NodeExecutionState {
  nodeId: string;
  status: NodeExecutionStatus;
  startedAt?: string;
  completedAt?: string;
  executionTime?: number; // milliseconds
  outputData?: Record<string, unknown>;
  error?: string;
}

/**
 * Workflow execution instance
 */
export interface WorkflowExecution {
  id: string;
  workflowId: string;
  status: ExecutionStatus;
  startedAt: string;
  completedAt?: string;
  totalDuration?: number; // milliseconds
  nodeExecutions: NodeExecutionState[];
  error?: string;
  logs: ExecutionLog[];
}

/**
 * Execution log entry
 */
export interface ExecutionLog {
  timestamp: string;
  level: 'info' | 'warn' | 'error' | 'debug';
  nodeId?: string;
  message: string;
}

/**
 * WebSocket message for real-time updates
 */
export interface WorkflowExecutionUpdate {
  type: 'execution_started' | 'node_started' | 'node_completed' | 'node_failed' | 'execution_completed' | 'execution_failed' | 'log';
  executionId: string;
  nodeId?: string;
  data?: Record<string, unknown>;
  status?: NodeExecutionStatus | ExecutionStatus;
  error?: string;
  log?: ExecutionLog;
}

/**
 * Type guard to check node data type
 */
export function isHttpTriggerNode(
  data: WorkflowNodeData
): data is HttpTriggerNodeData {
  return data.type === NodeType.HttpTrigger;
}

export function isExtractionNode(
  data: WorkflowNodeData
): data is ExtractionNodeData {
  return data.type === NodeType.Extraction;
}

export function isPythonRunnerNode(
  data: WorkflowNodeData
): data is PythonRunnerNodeData {
  return data.type === NodeType.PythonRunner;
}

export function isHttpRequestNode(
  data: WorkflowNodeData
): data is HttpRequestNodeData {
  return data.type === NodeType.HttpRequest;
}

export function isIfNode(data: WorkflowNodeData): data is IfNodeData {
  return data.type === NodeType.If;
}

export function isJoinNode(data: WorkflowNodeData): data is JoinNodeData {
  return data.type === NodeType.Join;
}
