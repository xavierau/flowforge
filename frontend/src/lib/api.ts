/**
 * API service for schema and job operations
 */

import type { ApiSchema, ApiSchemaListResponse, CreateApiSchemaRequest, UpdateApiSchemaRequest } from '@/types/api-schema';
import type { JobListResponse, JobStatusResponse, JobResultResponse } from '@/types/job';
import { clearTokens } from '@/services/auth.service';

const API_BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : '/api/v1';  // Use Vite proxy when VITE_API_URL not set

export interface CreateSchemaRequest {
  name: string;
  definitions: object;
}

export interface CreateSchemaResponse {
  id: string;
  name: string;
  definitions: object;
  created_at: string;
  updated_at: string;
}

/**
 * Structured error detail from backend (ErrorDetail schema)
 */
export interface StructuredErrorDetail {
  error_code: string;
  message: string;
  details?: Record<string, unknown>;
}

/**
 * API error response - detail can be a string or structured error object
 */
export interface ApiError {
  detail: string | StructuredErrorDetail;
}

/**
 * Extract a human-readable error message from API error response
 * Handles both string and structured error formats
 */
function extractErrorMessage(detail: string | StructuredErrorDetail | undefined, fallback: string): string {
  if (!detail) {
    return fallback;
  }
  if (typeof detail === 'string') {
    return detail;
  }
  // Structured error - extract the message field
  return detail.message || fallback;
}

export class ApiServiceError extends Error {
  statusCode: number;
  detail?: string;

  constructor(message: string, statusCode: number, detail?: string) {
    super(message);
    this.name = 'ApiServiceError';
    this.statusCode = statusCode;
    this.detail = detail;
  }
}

// Alias for backwards compatibility
export class SchemaApiError extends ApiServiceError {
  constructor(message: string, statusCode: number, detail?: string) {
    super(message, statusCode, detail);
    this.name = 'SchemaApiError';
  }
}

/**
 * Get authentication token from localStorage
 */
function getAuthToken(): string | null {
  return localStorage.getItem('access_token');
}

/**
 * Centralized fetch wrapper with 401 interceptor
 *
 * Automatically:
 * - Adds Authorization header if token exists
 * - Intercepts 401 responses and redirects to login
 * - Clears stored tokens on unauthorized access
 *
 * @param url - Request URL
 * @param options - Fetch options
 * @returns Response promise
 */
async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  // Add Authorization header if token exists
  const token = getAuthToken();
  const headers = new Headers(options.headers);

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Make the request with updated headers
  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Intercept 401 Unauthorized responses
  if (response.status === 401) {
    // Clear tokens from storage
    clearTokens();

    // Redirect to login page
    window.location.href = '/login';

    // Throw error to prevent further processing
    throw new ApiServiceError('Unauthorized - Please log in again', 401);
  }

  return response;
}

/**
 * Submit a new schema to the backend
 * @param request Schema data to submit
 * @returns Created schema response
 * @throws SchemaApiError with specific status codes (409, 400, 422, 401)
 */
export async function submitSchema(
  request: CreateSchemaRequest
): Promise<CreateSchemaResponse> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/schemas`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData: ApiError = await response.json().catch(() => ({
        detail: 'Unknown error occurred',
      }));

      const errorMessage = extractErrorMessage(errorData.detail, response.statusText);
      throw new SchemaApiError(
        errorMessage,
        response.status,
        errorMessage
      );
    }

    const data: CreateSchemaResponse = await response.json();
    return data;
  } catch (error) {
    if (error instanceof SchemaApiError) {
      throw error;
    }

    // Network or other errors
    throw new SchemaApiError(
      error instanceof Error ? error.message : 'Failed to connect to API',
      0
    );
  }
}

/**
 * Validate schema name
 * @param name Schema name to validate
 * @returns Object with isValid flag and optional error message
 */
export function validateSchemaName(name: string): {
  isValid: boolean;
  error?: string;
} {
  const trimmedName = name.trim();

  if (!trimmedName) {
    return { isValid: false, error: 'Schema name cannot be empty' };
  }

  if (trimmedName.length > 255) {
    return { isValid: false, error: 'Schema name must be 255 characters or less' };
  }

  return { isValid: true };
}

// ============================================================================
// Schema API Operations (Full CRUD)
// ============================================================================

/**
 * List all schemas with pagination
 */
export async function listSchemas(params?: {
  limit?: number;
  offset?: number;
}): Promise<ApiSchemaListResponse> {
  try {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.offset) queryParams.append('offset', params.offset.toString());

    const url = `${API_BASE_URL}/schemas${queryParams.toString() ? `?${queryParams}` : ''}`;

    const response = await apiFetch(url);

    if (!response.ok) {
      const errorData: ApiError = await response.json().catch(() => ({
        detail: 'Failed to list schemas',
      }));
      throw new ApiServiceError(extractErrorMessage(errorData.detail, 'Failed to list schemas'), response.status);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    throw new ApiServiceError(
      error instanceof Error ? error.message : 'Failed to list schemas',
      0
    );
  }
}

/**
 * Get a schema by ID
 */
export async function getSchema(schemaId: string): Promise<ApiSchema> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/schemas/${schemaId}`);

    if (!response.ok) {
      const errorData: ApiError = await response.json().catch(() => ({
        detail: 'Schema not found',
      }));
      throw new ApiServiceError(extractErrorMessage(errorData.detail, 'Schema not found'), response.status);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    throw new ApiServiceError(
      error instanceof Error ? error.message : 'Failed to get schema',
      0
    );
  }
}

/**
 * Create a new schema
 */
export async function createSchema(
  request: CreateApiSchemaRequest
): Promise<ApiSchema> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/schemas`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData: ApiError = await response.json().catch(() => ({
        detail: 'Failed to create schema',
      }));
      throw new ApiServiceError(extractErrorMessage(errorData.detail, 'Failed to create schema'), response.status);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    throw new ApiServiceError(
      error instanceof Error ? error.message : 'Failed to create schema',
      0
    );
  }
}

/**
 * Update a schema (definitions only, name is immutable)
 */
export async function updateSchema(
  schemaId: string,
  request: UpdateApiSchemaRequest
): Promise<ApiSchema> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/schemas/${schemaId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData: ApiError = await response.json().catch(() => ({
        detail: 'Failed to update schema',
      }));
      throw new ApiServiceError(extractErrorMessage(errorData.detail, 'Failed to update schema'), response.status);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    throw new ApiServiceError(
      error instanceof Error ? error.message : 'Failed to update schema',
      0
    );
  }
}

/**
 * Delete a schema
 */
export async function deleteSchema(schemaId: string): Promise<void> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/schemas/${schemaId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const errorData: ApiError = await response.json().catch(() => ({
        detail: 'Failed to delete schema',
      }));
      throw new ApiServiceError(extractErrorMessage(errorData.detail, 'Failed to delete schema'), response.status);
    }
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    throw new ApiServiceError(
      error instanceof Error ? error.message : 'Failed to delete schema',
      0
    );
  }
}

// ============================================================================
// Job API Operations
// ============================================================================

/**
 * Get job status
 */
export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/jobs/${jobId}/status`);

    if (!response.ok) {
      const errorData: ApiError = await response.json().catch(() => ({
        detail: 'Job not found',
      }));
      throw new ApiServiceError(extractErrorMessage(errorData.detail, 'Job not found'), response.status);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    throw new ApiServiceError(
      error instanceof Error ? error.message : 'Failed to get job status',
      0
    );
  }
}

/**
 * Get job result (only for completed jobs)
 */
export async function getJobResult(jobId: string): Promise<JobResultResponse> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/jobs/${jobId}/result`);

    if (!response.ok) {
      const errorData: ApiError = await response.json().catch(() => ({
        detail: 'Job result not available',
      }));
      throw new ApiServiceError(extractErrorMessage(errorData.detail, 'Job result not available'), response.status);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    throw new ApiServiceError(
      error instanceof Error ? error.message : 'Failed to get job result',
      0
    );
  }
}

/**
 * List all jobs with pagination
 */
export async function listJobs(params?: {
  limit?: number;
  offset?: number;
}): Promise<JobListResponse> {
  try {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.offset) queryParams.append('offset', params.offset.toString());

    const url = `${API_BASE_URL}/jobs${queryParams.toString() ? `?${queryParams}` : ''}`;

    const response = await apiFetch(url);

    if (!response.ok) {
      const errorData: ApiError = await response.json().catch(() => ({
        detail: 'Failed to list jobs',
      }));
      throw new ApiServiceError(extractErrorMessage(errorData.detail, 'Failed to list jobs'), response.status);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    throw new ApiServiceError(
      error instanceof Error ? error.message : 'Failed to list jobs',
      0
    );
  }
}

// ============================================================================
// Document Upload and Job Submission
// ============================================================================

export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  status: string;
  page_count: number | null;
  created_at: string;
}

export interface ParseRequest {
  schema_definition_id?: string;  // ID of saved schema definition (takes precedence if provided)
  extraction_schema?: object;     // Custom schema (used if schema_definition_id not provided)
  custom_prompt?: string;
  processing_mode: 'batch' | 'per_page';
  callback_url?: string;
  model_provider_config: {
    provider: string;
    model: string;
  };
}

export interface ParseResponse {
  extraction_job_id: string;
  document_id: string;
  status: string;
  estimated_time_seconds: number;
  created_at: string;
}

/**
 * Upload a document (PDF or image) - Stage 1 of job creation
 */
export async function uploadDocument(file: File): Promise<DocumentUploadResponse> {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiFetch(`${API_BASE_URL}/documents/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData: ApiError = await response.json().catch(() => ({
        detail: 'Failed to upload document',
      }));
      throw new ApiServiceError(extractErrorMessage(errorData.detail, 'Failed to upload document'), response.status);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    throw new ApiServiceError(
      error instanceof Error ? error.message : 'Failed to upload document',
      0
    );
  }
}

/**
 * Submit extraction job for a document - Stage 2 of job creation
 */
export async function submitExtractionJob(
  documentId: string,
  request: ParseRequest
): Promise<ParseResponse> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/documents/${documentId}/parse`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData: ApiError = await response.json().catch(() => ({
        detail: 'Failed to submit extraction job',
      }));
      throw new ApiServiceError(extractErrorMessage(errorData.detail, 'Failed to submit extraction job'), response.status);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    throw new ApiServiceError(
      error instanceof Error ? error.message : 'Failed to submit extraction job',
      0
    );
  }
}

// ============================================================================
// Document Status Operations
// ============================================================================

export interface DocumentStatusResponse {
  document_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  status: string;
  page_count: number | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

/**
 * Get document status - Used for polling document processing state
 * Valid statuses: "uploaded", "processing", "ready_for_extraction", "failed", "completed"
 */
export async function getDocumentStatus(
  documentId: string
): Promise<DocumentStatusResponse> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/documents/${documentId}`);

    if (!response.ok) {
      const errorData: ApiError = await response.json().catch(() => ({
        detail: 'Document not found',
      }));
      throw new ApiServiceError(extractErrorMessage(errorData.detail, 'Document not found'), response.status);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    throw new ApiServiceError(
      error instanceof Error ? error.message : 'Failed to get document status',
      0
    );
  }
}

/**
 * Get document metadata including mime_type and filename
 */
export async function getDocument(documentId: string): Promise<DocumentStatusResponse> {
  return getDocumentStatus(documentId);
}

/**
 * Get document file (PDF or image) as a blob
 * This endpoint will need to be implemented in the backend
 */
export async function getDocumentFile(documentId: string): Promise<Blob> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/documents/${documentId}/file`);

    if (!response.ok) {
      const errorData: ApiError = await response.json().catch(() => ({
        detail: 'Failed to download document file',
      }));
      throw new ApiServiceError(extractErrorMessage(errorData.detail, 'Failed to download document file'), response.status);
    }

    return await response.blob();
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    throw new ApiServiceError(
      error instanceof Error ? error.message : 'Failed to download document file',
      0
    );
  }
}

// ============================================================================
// Combined Extract Endpoint (Upload + Job Creation in one step)
// ============================================================================

export interface ExtractRequest {
  file: File;
  schema_definition_id?: string;      // ID of saved schema (optional)
  extraction_schema?: object;         // Custom JSON schema (optional)
  custom_prompt?: string;
  model_provider: string;             // e.g., "google", "openai"
  model_name: string;                 // e.g., "gemini-2.5-flash"
  processing_mode?: 'batch' | 'per_page' | 'markdown'; // Default: "batch"
  markdown_converter?: string;        // Required when processing_mode is "markdown"
  markdown_format?: string;           // Required when processing_mode is "markdown"
  callback_url?: string;
  enable_thinking?: boolean;          // Enable thinking mode (default: false)
  thinking_budget?: number;           // Thinking budget in tokens (default: 3000)
  source?: 'webui' | 'api';           // Job source (default: 'webui' for frontend)
}

export interface ExtractResponse {
  extraction_job_id: string;  // UUID
  document_id: string;        // UUID
  status: string;
  message: string;
  estimated_time_seconds: number;
  created_at: string;         // ISO datetime
}

/**
 * Combined extract endpoint - Upload document and create extraction job in one API call
 * This simplifies the previous two-step process (upload → poll → submit)
 *
 * @param request - Extract request parameters
 * @returns Extract response with job and document IDs
 * @throws ApiServiceError with specific status codes
 */
export async function extractFromFile(request: ExtractRequest): Promise<ExtractResponse> {
  try {
    const formData = new FormData();

    // File is required
    formData.append('file', request.file);

    // Model configuration (required)
    formData.append('model_provider', request.model_provider);
    formData.append('model_name', request.model_name);

    // Schema configuration (one of schema_definition_id or extraction_schema)
    if (request.schema_definition_id) {
      formData.append('schema_definition_id', request.schema_definition_id);
    } else if (request.extraction_schema) {
      formData.append('extraction_schema', JSON.stringify(request.extraction_schema));
    }

    // Optional fields
    if (request.custom_prompt) {
      formData.append('custom_prompt', request.custom_prompt);
    }

    if (request.processing_mode) {
      formData.append('processing_mode', request.processing_mode);
    }

    // Markdown pipeline configuration (required when processing_mode is 'markdown')
    if (request.markdown_converter) {
      formData.append('markdown_converter', request.markdown_converter);
    }

    if (request.markdown_format) {
      formData.append('markdown_format', request.markdown_format);
    }

    if (request.callback_url) {
      formData.append('callback_url', request.callback_url);
    }

    // Thinking mode configuration
    if (request.enable_thinking !== undefined) {
      formData.append('enable_thinking', String(request.enable_thinking));
    }

    if (request.thinking_budget !== undefined) {
      formData.append('thinking_budget', String(request.thinking_budget));
    }

    // Always set source to 'webui' for frontend requests
    formData.append('source', request.source || 'webui');

    const response = await apiFetch(`${API_BASE_URL}/jobs/extract`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData: ApiError = await response.json().catch(() => ({
        detail: 'Failed to extract from file',
      }));
      throw new ApiServiceError(extractErrorMessage(errorData.detail, 'Failed to extract from file'), response.status);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    throw new ApiServiceError(
      error instanceof Error ? error.message : 'Failed to extract from file',
      0
    );
  }
}

/**
 * Retry an extraction job with the same configuration
 *
 * @param jobId - ID of the job to retry
 * @param source - Job source ('webui' or 'api'), defaults to 'webui' for frontend
 * @returns Extract response with new job and document IDs
 * @throws ApiServiceError with specific status codes
 */
export async function retryJob(jobId: string, source: 'webui' | 'api' = 'webui'): Promise<ExtractResponse> {
  try {
    const response = await apiFetch(`${API_BASE_URL}/jobs/${jobId}/retry?source=${source}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData: ApiError = await response.json().catch(() => ({
        detail: 'Failed to retry job',
      }));
      throw new ApiServiceError(extractErrorMessage(errorData.detail, 'Failed to retry job'), response.status);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    throw new ApiServiceError(
      error instanceof Error ? error.message : 'Failed to retry job',
      0
    );
  }
}
