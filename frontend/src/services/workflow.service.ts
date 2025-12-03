/**
 * Workflow Service - API layer for workflow CRUD and execution
 * Handles all backend communication for workflows
 */

import type {
  WorkflowResponse,
  WorkflowListResponse,
  WorkflowExecutionResponse,
  WorkflowExecutionListResponse,
  WorkflowNodeExecutionResponse,
  WorkflowCreateRequest,
  WorkflowUpdateRequest,
} from '@/types/workflow';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

/**
 * Centralized API fetch wrapper with authentication
 * CRITICAL: All API calls MUST use this wrapper
 */
async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem('access_token');
  const headers = new Headers(options.headers);

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(url, { ...options, headers });

  // Handle 401 - redirect to login
  if (response.status === 401) {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
    throw new Error('Unauthorized - Please log in again');
  }

  return response;
}

/**
 * Handle API response and parse JSON
 */
async function handleApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({
      detail: response.statusText,
    }));
    throw new Error(errorData.detail || `API Error: ${response.status}`);
  }
  return response.json();
}

/**
 * Create a new workflow
 */
export async function createWorkflow(workflow: WorkflowCreateRequest): Promise<WorkflowResponse> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/workflows`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(workflow),
  });

  return handleApiResponse<WorkflowResponse>(response);
}

/**
 * Update an existing workflow
 */
export async function updateWorkflow(workflowId: string, workflow: WorkflowUpdateRequest): Promise<WorkflowResponse> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/workflows/${workflowId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(workflow),
  });

  return handleApiResponse<WorkflowResponse>(response);
}

/**
 * Get a specific workflow by ID
 */
export async function getWorkflow(workflowId: string): Promise<WorkflowResponse> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/workflows/${workflowId}`, {
    method: 'GET',
  });

  return handleApiResponse<WorkflowResponse>(response);
}

/**
 * List workflows with pagination and filters
 */
export interface ListWorkflowsParams {
  page?: number;
  pageSize?: number;
  isActive?: boolean;
  isArchived?: boolean;
  includeAll?: boolean;
}

export async function listWorkflows(params?: ListWorkflowsParams): Promise<WorkflowListResponse> {
  const searchParams = new URLSearchParams();

  if (params?.page !== undefined) {
    searchParams.set('page', String(params.page));
  }
  if (params?.pageSize !== undefined) {
    searchParams.set('page_size', String(params.pageSize));
  }
  if (params?.isActive !== undefined) {
    searchParams.set('is_active', String(params.isActive));
  }
  if (params?.isArchived !== undefined) {
    searchParams.set('is_archived', String(params.isArchived));
  }
  if (params?.includeAll) {
    searchParams.set('include_all', 'true');
  }

  const queryString = searchParams.toString();
  const url = queryString
    ? `${API_BASE_URL}/api/v1/workflows?${queryString}`
    : `${API_BASE_URL}/api/v1/workflows`;

  const response = await apiFetch(url, {
    method: 'GET',
  });

  return handleApiResponse<WorkflowListResponse>(response);
}

/**
 * Delete a workflow
 */
export async function deleteWorkflow(workflowId: string): Promise<void> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/workflows/${workflowId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({
      detail: response.statusText,
    }));
    throw new Error(errorData.detail || `Failed to delete workflow`);
  }
}

/**
 * Execute a workflow
 */
export async function executeWorkflow(
  workflowId: string,
  inputData?: Record<string, unknown>,
  versionNumber?: number
): Promise<WorkflowExecutionResponse> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/workflows/${workflowId}/execute`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      inputData: inputData || {},
      ...(versionNumber !== undefined && { versionNumber }),
    }),
  });

  return handleApiResponse<WorkflowExecutionResponse>(response);
}

/**
 * Get execution status and results
 */
export async function getExecutionStatus(executionId: string): Promise<WorkflowExecutionResponse> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/workflows/executions/${executionId}`, {
    method: 'GET',
  });

  return handleApiResponse<WorkflowExecutionResponse>(response);
}

/**
 * Stop a running execution
 */
export async function stopExecution(executionId: string): Promise<void> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/workflows/executions/${executionId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({
      detail: response.statusText,
    }));
    throw new Error(errorData.detail || `Failed to stop execution`);
  }
}

/**
 * Get WebSocket URL for execution updates
 */
export function getExecutionWebSocketUrl(executionId: string): string {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const apiHost = API_BASE_URL.replace(/^https?:\/\//, '');
  return `${wsProtocol}//${apiHost}/api/v1/workflows/executions/${executionId}/ws`;
}

// ============================================================================
// Workflow Execution List and Node Execution Functions
// ============================================================================

/**
 * Parameters for listing workflow executions
 */
export interface ListWorkflowExecutionsParams {
  page?: number;
  pageSize?: number;
}

/**
 * List executions for a specific workflow
 */
export async function listWorkflowExecutions(
  workflowId: string,
  params?: ListWorkflowExecutionsParams
): Promise<WorkflowExecutionListResponse> {
  const searchParams = new URLSearchParams();

  if (params?.page !== undefined) {
    searchParams.set('page', String(params.page));
  }
  if (params?.pageSize !== undefined) {
    searchParams.set('page_size', String(params.pageSize));
  }

  const queryString = searchParams.toString();
  const url = queryString
    ? `${API_BASE_URL}/api/v1/workflows/${workflowId}/executions?${queryString}`
    : `${API_BASE_URL}/api/v1/workflows/${workflowId}/executions`;

  const response = await apiFetch(url, {
    method: 'GET',
  });

  return handleApiResponse<WorkflowExecutionListResponse>(response);
}

/**
 * Get node executions for a specific workflow execution
 */
export async function getNodeExecutions(
  executionId: string
): Promise<WorkflowNodeExecutionResponse[]> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/v1/workflows/executions/${executionId}/nodes`,
    {
      method: 'GET',
    }
  );

  return handleApiResponse<WorkflowNodeExecutionResponse[]>(response);
}

// ============================================================================
// Workflow Management Functions (Clone, Archive, Restore)
// ============================================================================

/**
 * Clone a workflow by creating a new workflow with copied definition
 */
export async function cloneWorkflow(workflowId: string): Promise<WorkflowResponse> {
  // Fetch the original workflow
  const original = await getWorkflow(workflowId);

  // Create new workflow with copied definition
  const newWorkflow = await createWorkflow({
    name: `Copy of ${original.name}`,
    description: original.description || undefined,
    definition: original.currentVersion?.definition || { nodes: [], edges: [] },
  });

  return newWorkflow;
}

/**
 * Archive a workflow (soft delete)
 */
export async function archiveWorkflow(workflowId: string): Promise<WorkflowResponse> {
  return updateWorkflow(workflowId, { isArchived: true });
}

/**
 * Restore an archived workflow
 */
export async function restoreWorkflow(workflowId: string): Promise<WorkflowResponse> {
  return updateWorkflow(workflowId, { isArchived: false });
}

/**
 * Activate a workflow
 */
export async function activateWorkflow(workflowId: string): Promise<WorkflowResponse> {
  return updateWorkflow(workflowId, { isActive: true });
}

/**
 * Deactivate a workflow
 */
export async function deactivateWorkflow(workflowId: string): Promise<WorkflowResponse> {
  return updateWorkflow(workflowId, { isActive: false });
}
