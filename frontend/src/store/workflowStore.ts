/**
 * Workflow Store - Zustand state management with localStorage persistence
 * Handles nodes, edges, validation, and workflow operations
 */

import { create } from 'zustand';
import {
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  MarkerType,
  type NodeChange,
  type EdgeChange,
  type Connection,
} from '@xyflow/react';
import type {
  Workflow,
  WorkflowNode,
  WorkflowEdge,
  WorkflowNodeData,
  ValidationError,
  SavedWorkflows,
  WorkflowExecution,
  NodeExecutionState,
  WorkflowExecutionUpdate,
} from '@/types/workflow';
import {
  NodeType,
  HttpMethod,
  ExecutionStatus,
  NodeExecutionStatus,
  isExtractionNode,
  isPythonRunnerNode,
  isHttpRequestNode,
  isIfNode,
  isJoinNode,
} from '@/types/workflow';
import * as workflowService from '@/services/workflow.service';
import { validateExpression, hasExpressions } from '@/lib/expression-parser';

const STORAGE_KEY = 'ai-doc-workflows';
const CURRENT_WORKFLOW_KEY = 'ai-doc-current-workflow';

interface WorkflowStore {
  // Current workflow state
  workflowId: string;
  workflowName: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  selectedNodeId: string | null;

  // Execution state
  currentExecution: WorkflowExecution | null;
  executionHistory: WorkflowExecution[];
  nodeExecutionStates: Map<string, NodeExecutionState>;

  // Actions
  setWorkflowName: (name: string) => void;
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: Connection) => void;
  addNode: (type: NodeType, position: { x: number; y: number }) => void;
  updateNodeData: (nodeId: string, data: Partial<WorkflowNodeData>) => void;
  deleteNode: (nodeId: string) => void;
  setSelectedNode: (nodeId: string | null) => void;
  validateNode: (nodeId: string) => void;
  isValidConnection: (connection: Connection) => boolean;

  // Workflow management
  saveWorkflow: () => void;
  saveWorkflowToBackend: () => Promise<void>;
  loadWorkflow: (workflowId: string) => void;
  getSavedWorkflows: () => Workflow[];
  clearWorkflow: () => void;
  exportWorkflow: () => string;
  importWorkflow: (json: string) => void;

  // Execution management
  executeWorkflow: (input?: Record<string, unknown>) => Promise<void>;
  stopExecution: () => Promise<void>;
  updateExecutionStatus: (execution: WorkflowExecution) => void;
  updateNodeExecution: (nodeExecution: NodeExecutionState) => void;
  handleExecutionUpdate: (update: WorkflowExecutionUpdate) => void;
  loadExecutionHistory: () => void;
  setNodeExecutionData: (nodeId: string, data: Record<string, unknown>) => void;
  getExecutionStatus: () => ExecutionStatus;
}

/**
 * Validate node configuration and return errors
 */
function validateNodeData(
  data: WorkflowNodeData,
  allNodes: WorkflowNode[] = []
): ValidationError[] {
  const errors: ValidationError[] = [];

  switch (data.type) {
    case NodeType.HttpTrigger:
      // Always valid - no configuration needed
      break;

    case NodeType.Extraction:
      if (isExtractionNode(data)) {
        if (!data.config.schemaId) {
          errors.push({
            field: 'schemaId',
            message: 'Schema must be selected',
          });
        }
        if (!data.config.prompt.trim()) {
          errors.push({
            field: 'prompt',
            message: 'Prompt is required',
          });
        } else if (hasExpressions(data.config.prompt)) {
          // Validate expressions in prompt
          const expressionError = validateExpression(
            data.config.prompt,
            allNodes
          );
          if (expressionError) {
            errors.push({
              field: 'prompt',
              message: expressionError,
            });
          }
        }
      }
      break;

    case NodeType.PythonRunner:
      if (isPythonRunnerNode(data)) {
        if (!data.config.code.trim()) {
          errors.push({
            field: 'code',
            message: 'Python code is required',
          });
        } else {
          // Check for return statement
          if (!data.config.code.includes('return')) {
            errors.push({
              field: 'code',
              message: 'Code must contain a return statement',
            });
          }

          // Check for dangerous imports
          const dangerousImports = ['os', 'sys', 'subprocess', 'eval', 'exec'];
          const codeLines = data.config.code.toLowerCase();
          for (const dangerous of dangerousImports) {
            if (codeLines.includes(`import ${dangerous}`)) {
              errors.push({
                field: 'code',
                message: `Dangerous import detected: ${dangerous}`,
              });
              break;
            }
          }
        }
      }
      break;

    case NodeType.HttpRequest:
      if (isHttpRequestNode(data)) {
        if (!data.config.url.trim()) {
          errors.push({
            field: 'url',
            message: 'URL is required',
          });
        } else {
          // Validate expressions in URL
          if (hasExpressions(data.config.url)) {
            const expressionError = validateExpression(
              data.config.url,
              allNodes
            );
            if (expressionError) {
              errors.push({
                field: 'url',
                message: expressionError,
              });
            }
          }

          // Validate URL format (only if no unresolved expressions)
          if (
            !hasExpressions(data.config.url) ||
            !data.config.url.includes('{{')
          ) {
            try {
              new URL(data.config.url);
            } catch {
              errors.push({
                field: 'url',
                message: 'Invalid URL format',
              });
            }
          }
        }

        // Validate expressions in headers
        for (const header of data.config.headers) {
          if (hasExpressions(header.value)) {
            const expressionError = validateExpression(header.value, allNodes);
            if (expressionError) {
              errors.push({
                field: 'headers',
                message: `Header "${header.key}": ${expressionError}`,
              });
            }
          }
        }
      }
      break;

    case NodeType.If:
      if (isIfNode(data)) {
        if (!data.config?.condition || data.config.condition.trim() === '') {
          errors.push({
            field: 'condition',
            message: 'Condition is required',
          });
        } else {
          // Validate expressions in condition
          if (hasExpressions(data.config.condition)) {
            const expressionError = validateExpression(
              data.config.condition,
              allNodes
            );
            if (expressionError) {
              errors.push({
                field: 'condition',
                message: expressionError,
              });
            }
          }

          // Validate condition syntax (basic check for operators)
          const validOperators = ['>', '<', '>=', '<=', '==', '!=', '&&', '||'];
          const hasOperator = validOperators.some((op) =>
            data.config.condition.includes(op)
          );
          if (!hasOperator) {
            errors.push({
              field: 'condition',
              message: 'Condition must include a comparison operator (>, <, ==, etc.)',
            });
          }
        }
      }
      break;

    case NodeType.Join:
      if (isJoinNode(data)) {
        // Join node is always valid - no configuration required
        // Validation of incoming edges happens at workflow level
      }
      break;
  }

  return errors;
}

/**
 * Check if connection creates a cycle
 */
function hasCycle(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[],
  newEdge: Connection
): boolean {
  const adjacencyList = new Map<string, string[]>();

  // Build adjacency list with new edge
  nodes.forEach((node) => adjacencyList.set(node.id, []));
  edges.forEach((edge) => {
    const targets = adjacencyList.get(edge.source) || [];
    targets.push(edge.target);
    adjacencyList.set(edge.source, targets);
  });

  // Add new edge
  if (newEdge.source && newEdge.target) {
    const targets = adjacencyList.get(newEdge.source) || [];
    targets.push(newEdge.target);
    adjacencyList.set(newEdge.source, targets);
  }

  // DFS to detect cycle
  const visited = new Set<string>();
  const recStack = new Set<string>();

  function dfs(nodeId: string): boolean {
    visited.add(nodeId);
    recStack.add(nodeId);

    const neighbors = adjacencyList.get(nodeId) || [];
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        if (dfs(neighbor)) return true;
      } else if (recStack.has(neighbor)) {
        return true; // Cycle detected
      }
    }

    recStack.delete(nodeId);
    return false;
  }

  // Check from all nodes
  for (const node of nodes) {
    if (!visited.has(node.id)) {
      if (dfs(node.id)) return true;
    }
  }

  return false;
}

/**
 * Load saved workflows from localStorage
 */
function loadSavedWorkflows(): SavedWorkflows {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : {};
  } catch (error) {
    console.error('Failed to load workflows:', error);
    return {};
  }
}

/**
 * Save workflows to localStorage
 */
function saveSavedWorkflows(workflows: SavedWorkflows): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(workflows));
  } catch (error) {
    console.error('Failed to save workflows:', error);
  }
}

/**
 * Generate unique node ID
 */
function generateNodeId(type: NodeType): string {
  return `${type}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Create default node data for a given type
 */
function createDefaultNodeData(type: NodeType): WorkflowNodeData {
  const baseData = {
    label: type.charAt(0).toUpperCase() + type.slice(1),
    type,
    isValid: type === NodeType.HttpTrigger, // HttpTrigger is always valid
    errors: [],
  };

  switch (type) {
    case NodeType.HttpTrigger:
      return {
        ...baseData,
        type: NodeType.HttpTrigger,
        // Add sample output data for expression testing
        outputData: {
          data: {
            prompt: 'Extract invoice data from the document',
            callback_url: 'https://example.com/webhook/callback',
            file_url: 'https://example.com/files/invoice.pdf',
          },
        },
      };

    case NodeType.Extraction:
      return {
        ...baseData,
        type: NodeType.Extraction,
        isValid: false,
        config: {
          fileSource: 'previous_node' as const,
          prompt: '',
          schemaId: '',
        },
        // Add sample output data for expression testing
        outputData: {
          data: {
            invoice_number: 'INV-2024-001',
            total: 1250.50,
            date: '2024-11-15',
            vendor: 'Acme Corporation',
            items: [
              { description: 'Product A', quantity: 2, price: 500.00 },
              { description: 'Product B', quantity: 1, price: 250.50 },
            ],
          },
        },
      };

    case NodeType.PythonRunner:
      return {
        ...baseData,
        type: NodeType.PythonRunner,
        isValid: false,
        config: {
          code: '# Process the input data\ndef process(data):\n    # Your code here\n    return data\n\nreturn process(data)',
        },
        // Add sample output data for expression testing
        outputData: {
          data: {
            result: {
              processed: true,
              total_with_tax: 1375.55,
              summary: 'Invoice processed successfully',
            },
          },
        },
      };

    case NodeType.HttpRequest:
      return {
        ...baseData,
        type: NodeType.HttpRequest,
        isValid: false,
        config: {
          url: '',
          method: HttpMethod.POST,
          headers: [],
        },
      };

    case NodeType.If:
      return {
        ...baseData,
        label: 'If',
        type: NodeType.If,
        isValid: false,
        config: {
          condition: '',
        },
        // Add sample output data for expression testing
        outputData: {
          data: {
            condition: '{{$("Extraction").data.total}} > 100',
            result: true,
            evaluatedValue: 1250.50,
          },
        },
      };

    case NodeType.Join:
      return {
        ...baseData,
        label: 'Join',
        type: NodeType.Join,
        isValid: true, // Join node is always valid - no configuration needed
        // Add sample output data for expression testing
        outputData: {
          data: {
            // Simulated aggregated output from multiple upstream nodes
            upstream_node_1: {
              output: { status: 'completed', data: { value: 100 } },
            },
            upstream_node_2: {
              output: { status: 'completed', data: { value: 200 } },
            },
          },
        },
      };

    default:
      throw new Error(`Unknown node type: ${type}`);
  }
}

// Debounce helper
let saveTimeout: NodeJS.Timeout | null = null;
function debouncedSave(callback: () => void, delay: number = 1000) {
  if (saveTimeout) clearTimeout(saveTimeout);
  saveTimeout = setTimeout(callback, delay);
}

export const useWorkflowStore = create<WorkflowStore>((set, get) => ({
  // Initial state
  workflowId: 'default',
  workflowName: 'Untitled Workflow',
  nodes: [],
  edges: [],
  selectedNodeId: null,

  // Execution state
  currentExecution: null,
  executionHistory: [],
  nodeExecutionStates: new Map(),

  // Workflow name
  setWorkflowName: (name) => {
    set({ workflowName: name });
    debouncedSave(() => get().saveWorkflow());
  },

  // React Flow change handlers
  onNodesChange: (changes) => {
    set((state) => ({
      nodes: applyNodeChanges(changes, state.nodes) as WorkflowNode[],
    }));
    debouncedSave(() => get().saveWorkflow());
  },

  onEdgesChange: (changes) => {
    set((state) => ({
      edges: applyEdgeChanges(changes, state.edges),
    }));
    debouncedSave(() => get().saveWorkflow());
  },

  onConnect: (connection) => {
    if (!get().isValidConnection(connection)) return;

    const { nodes } = get();
    const sourceNode = nodes.find((n) => n.id === connection.source);

    // Create edge configuration
    const edgeConfig: any = {
      ...connection,
      type: 'smoothstep',
      animated: true,
      markerEnd: {
        type: MarkerType.ArrowClosed,
      },
    };

    // Add labels and styling for If node branches
    if (sourceNode?.data.type === NodeType.If && connection.sourceHandle) {
      const isTrue = connection.sourceHandle === 'true';
      edgeConfig.label = isTrue ? 'True' : 'False';
      edgeConfig.labelStyle = {
        fill: isTrue ? '#22c55e' : '#ef4444',
        fontWeight: 600,
        fontSize: 12,
      };
      edgeConfig.style = {
        stroke: isTrue ? '#22c55e' : '#ef4444',
        strokeWidth: 2,
      };
    }

    set((state) => ({
      edges: addEdge(edgeConfig, state.edges),
    }));
    debouncedSave(() => get().saveWorkflow());
  },

  // Add new node
  addNode: (type, position) => {
    const nodeId = generateNodeId(type);
    const nodeData = createDefaultNodeData(type);

    const newNode: WorkflowNode = {
      id: nodeId,
      type: type,
      position,
      data: nodeData,
    } as WorkflowNode;

    set((state) => ({
      nodes: [...state.nodes, newNode],
    }));
    debouncedSave(() => get().saveWorkflow());
  },

  // Update node data
  updateNodeData: (nodeId, dataUpdate) => {
    set((state) => {
      const updatedNodes = state.nodes.map((node) => {
        if (node.id !== nodeId) return node;

        const updatedData = { ...node.data, ...dataUpdate };
        const errors = validateNodeData(
          updatedData as WorkflowNodeData,
          state.nodes
        );
        const isValid = errors.length === 0;

        return {
          ...node,
          data: {
            ...updatedData,
            isValid,
            errors,
          },
        } as WorkflowNode;
      });

      return { nodes: updatedNodes };
    });
    debouncedSave(() => get().saveWorkflow());
  },

  // Delete node
  deleteNode: (nodeId) => {
    set((state) => ({
      nodes: state.nodes.filter((node) => node.id !== nodeId),
      edges: state.edges.filter(
        (edge) => edge.source !== nodeId && edge.target !== nodeId
      ),
      selectedNodeId:
        state.selectedNodeId === nodeId ? null : state.selectedNodeId,
    }));
    debouncedSave(() => get().saveWorkflow());
  },

  // Select node
  setSelectedNode: (nodeId) => {
    set({ selectedNodeId: nodeId });
  },

  // Validate specific node
  validateNode: (nodeId) => {
    const { nodes } = get();
    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return;

    const errors = validateNodeData(node.data, nodes);
    const isValid = errors.length === 0;

    get().updateNodeData(nodeId, { isValid, errors });
  },

  // Connection validation
  isValidConnection: (connection) => {
    if (!connection.source || !connection.target) return false;

    const { nodes, edges } = get();

    // Prevent self-connections
    if (connection.source === connection.target) return false;

    // Check if source node is HttpTrigger - it can only be source
    const sourceNode = nodes.find((n) => n.id === connection.source);
    if (!sourceNode) return false;

    // Prevent connections TO HttpTrigger (it's an entry point)
    const targetNode = nodes.find((n) => n.id === connection.target);
    if (targetNode?.data.type === NodeType.HttpTrigger) return false;

    // Check for cycles
    if (hasCycle(nodes, edges, connection)) return false;

    return true;
  },

  // Save workflow to localStorage
  saveWorkflow: () => {
    const { workflowId, workflowName, nodes, edges } = get();
    const workflows = loadSavedWorkflows();

    const workflow: Workflow = {
      id: workflowId,
      name: workflowName,
      nodes,
      edges,
      createdAt: workflows[workflowId]?.createdAt || new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    workflows[workflowId] = workflow;
    saveSavedWorkflows(workflows);
    localStorage.setItem(CURRENT_WORKFLOW_KEY, workflowId);
  },

  // Load workflow from localStorage
  loadWorkflow: (workflowId) => {
    const workflows = loadSavedWorkflows();
    const workflow = workflows[workflowId];

    if (workflow) {
      set({
        workflowId: workflow.id,
        workflowName: workflow.name,
        nodes: workflow.nodes,
        edges: workflow.edges,
        selectedNodeId: null,
      });
      localStorage.setItem(CURRENT_WORKFLOW_KEY, workflowId);
    }
  },

  // Get all saved workflows
  getSavedWorkflows: () => {
    const workflows = loadSavedWorkflows();
    return Object.values(workflows).sort(
      (a, b) =>
        new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    );
  },

  // Clear current workflow
  clearWorkflow: () => {
    const newId = `workflow_${Date.now()}`;
    set({
      workflowId: newId,
      workflowName: 'Untitled Workflow',
      nodes: [],
      edges: [],
      selectedNodeId: null,
    });
    localStorage.setItem(CURRENT_WORKFLOW_KEY, newId);
  },

  // Export workflow as JSON
  exportWorkflow: () => {
    const { workflowId, workflowName, nodes, edges } = get();
    const workflow: Workflow = {
      id: workflowId,
      name: workflowName,
      nodes,
      edges,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    return JSON.stringify(workflow, null, 2);
  },

  // Import workflow from JSON
  importWorkflow: (json) => {
    try {
      const workflow: Workflow = JSON.parse(json);
      set({
        workflowId: workflow.id,
        workflowName: workflow.name,
        nodes: workflow.nodes,
        edges: workflow.edges,
        selectedNodeId: null,
      });
      get().saveWorkflow();
    } catch (error) {
      console.error('Failed to import workflow:', error);
      throw new Error('Invalid workflow JSON');
    }
  },

  // Save workflow to backend
  saveWorkflowToBackend: async () => {
    const { workflowId, workflowName, nodes, edges } = get();

    try {
      const workflow = {
        name: workflowName,
        nodes,
        edges,
      };

      await workflowService.updateWorkflow(workflowId, workflow);
      console.log('Workflow saved to backend successfully');
    } catch (error) {
      console.error('Failed to save workflow to backend:', error);
      throw error;
    }
  },

  // Execute workflow
  executeWorkflow: async (input) => {
    const { workflowId, nodes } = get();

    // Validate all nodes before execution
    const invalidNodes = nodes.filter((node) => !node.data.isValid);
    if (invalidNodes.length > 0) {
      throw new Error(
        `Cannot execute workflow: ${invalidNodes.length} node(s) have validation errors`
      );
    }

    try {
      // Start execution
      const execution = await workflowService.executeWorkflow(workflowId, input);

      // Initialize node execution states
      const nodeStates = new Map<string, NodeExecutionState>();
      nodes.forEach((node) => {
        nodeStates.set(node.id, {
          nodeId: node.id,
          status: NodeExecutionStatus.Pending,
        });
      });

      set({
        currentExecution: execution,
        nodeExecutionStates: nodeStates,
      });

      console.log('Workflow execution started:', execution.id);
    } catch (error) {
      console.error('Failed to execute workflow:', error);
      throw error;
    }
  },

  // Stop execution
  stopExecution: async () => {
    const { currentExecution } = get();

    if (!currentExecution) {
      throw new Error('No execution in progress');
    }

    try {
      await workflowService.stopExecution(currentExecution.id);

      set((state) => ({
        currentExecution: state.currentExecution
          ? {
              ...state.currentExecution,
              status: ExecutionStatus.Cancelled,
            }
          : null,
      }));

      console.log('Execution stopped:', currentExecution.id);
    } catch (error) {
      console.error('Failed to stop execution:', error);
      throw error;
    }
  },

  // Update execution status
  updateExecutionStatus: (execution) => {
    set({ currentExecution: execution });

    // Add to history when completed
    if (
      execution.status === ExecutionStatus.Completed ||
      execution.status === ExecutionStatus.Failed ||
      execution.status === ExecutionStatus.Cancelled
    ) {
      set((state) => ({
        executionHistory: [execution, ...state.executionHistory].slice(0, 10), // Keep last 10
      }));
    }
  },

  // Update node execution state
  updateNodeExecution: (nodeExecution) => {
    set((state) => {
      const newStates = new Map(state.nodeExecutionStates);
      newStates.set(nodeExecution.nodeId, nodeExecution);
      return { nodeExecutionStates: newStates };
    });

    // Update node data with execution results
    if (nodeExecution.outputData) {
      get().setNodeExecutionData(nodeExecution.nodeId, nodeExecution.outputData);
    }
  },

  // Handle WebSocket execution update
  handleExecutionUpdate: (update) => {
    const { currentExecution } = get();

    switch (update.type) {
      case 'execution_started':
        if (currentExecution && update.executionId === currentExecution.id) {
          set((state) => ({
            currentExecution: state.currentExecution
              ? {
                  ...state.currentExecution,
                  status: ExecutionStatus.Running,
                }
              : null,
          }));
        }
        break;

      case 'node_started':
        if (update.nodeId) {
          get().updateNodeExecution({
            nodeId: update.nodeId,
            status: NodeExecutionStatus.Running,
            startedAt: new Date().toISOString(),
          });
        }
        break;

      case 'node_completed':
        if (update.nodeId) {
          get().updateNodeExecution({
            nodeId: update.nodeId,
            status: NodeExecutionStatus.Success,
            completedAt: new Date().toISOString(),
            outputData: update.data,
          });
        }
        break;

      case 'node_failed':
        if (update.nodeId) {
          get().updateNodeExecution({
            nodeId: update.nodeId,
            status: NodeExecutionStatus.Error,
            completedAt: new Date().toISOString(),
            error: update.error,
          });
        }
        break;

      case 'execution_completed':
        if (currentExecution && update.executionId === currentExecution.id) {
          const updatedExecution: WorkflowExecution = {
            ...currentExecution,
            status: ExecutionStatus.Completed,
            completedAt: new Date().toISOString(),
          };
          get().updateExecutionStatus(updatedExecution);
        }
        break;

      case 'execution_failed':
        if (currentExecution && update.executionId === currentExecution.id) {
          const updatedExecution: WorkflowExecution = {
            ...currentExecution,
            status: ExecutionStatus.Failed,
            completedAt: new Date().toISOString(),
            error: update.error,
          };
          get().updateExecutionStatus(updatedExecution);
        }
        break;

      case 'log':
        if (currentExecution && update.log) {
          const newLog = update.log;
          set((state) => {
            if (!state.currentExecution) return {};
            return {
              currentExecution: {
                ...state.currentExecution,
                logs: [...state.currentExecution.logs, newLog],
              },
            };
          });
        }
        break;
    }
  },

  // Load execution history (placeholder - would come from backend)
  loadExecutionHistory: () => {
    // This would typically fetch from backend
    // For now, we rely on the in-memory executionHistory
    console.log('Loading execution history...');
  },

  // Set node execution data (update node's outputData)
  setNodeExecutionData: (nodeId, data) => {
    set((state) => {
      const updatedNodes = state.nodes.map((node) => {
        if (node.id === nodeId) {
          return {
            ...node,
            data: {
              ...node.data,
              outputData: { data },
            },
          };
        }
        return node;
      });

      return { nodes: updatedNodes };
    });
  },

  // Get current execution status
  getExecutionStatus: () => {
    const { currentExecution } = get();
    return currentExecution?.status || ExecutionStatus.Idle;
  },
}));

// Load current workflow on app start
const currentWorkflowId = localStorage.getItem(CURRENT_WORKFLOW_KEY);
if (currentWorkflowId) {
  const store = useWorkflowStore.getState();
  const workflows = loadSavedWorkflows();
  if (workflows[currentWorkflowId]) {
    store.loadWorkflow(currentWorkflowId);
  }
}
