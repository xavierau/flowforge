/**
 * Workflow Service - API layer for workflow CRUD and execution
 * Handles all backend communication for workflows
 */

import type { Workflow, WorkflowExecution } from '@/types/workflow';

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
export async function createWorkflow(workflow: Omit<Workflow, 'id' | 'createdAt' | 'updatedAt'>): Promise<Workflow> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/workflows`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(workflow),
  });

  return handleApiResponse<Workflow>(response);
}

/**
 * Update an existing workflow
 */
export async function updateWorkflow(workflowId: string, workflow: Partial<Workflow>): Promise<Workflow> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/workflows/${workflowId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(workflow),
  });

  return handleApiResponse<Workflow>(response);
}

/**
 * Get a specific workflow by ID
 */
export async function getWorkflow(workflowId: string): Promise<Workflow> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/workflows/${workflowId}`, {
    method: 'GET',
  });

  return handleApiResponse<Workflow>(response);
}

/**
 * List all workflows
 */
export async function listWorkflows(): Promise<Workflow[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/workflows`, {
    method: 'GET',
  });

  return handleApiResponse<Workflow[]>(response);
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
  input?: Record<string, unknown>
): Promise<WorkflowExecution> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/workflows/${workflowId}/execute`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ input: input || {} }),
  });

  return handleApiResponse<WorkflowExecution>(response);
}

/**
 * Get execution status and results
 */
export async function getExecutionStatus(executionId: string): Promise<WorkflowExecution> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/workflows/executions/${executionId}`, {
    method: 'GET',
  });

  return handleApiResponse<WorkflowExecution>(response);
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
