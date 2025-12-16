/**
 * Job Service
 *
 * Provides methods for extraction job management including markdown pipeline.
 * Following SOLID principles:
 * - Single Responsibility: Handles only job-related API calls
 * - Open/Closed: Easy to extend with new job operations
 * - Interface Segregation: Focused interface for job operations
 *
 * Uses centralized API client from lib/api-client.ts for:
 * - Automatic token refresh on 401 responses
 * - Auth header injection
 * - Consistent error handling
 */

import type { Job, ExtractionJobCreate } from '@/types/job';
import type { DocumentPage } from '@/types/document';
import { apiFetch, API_BASE_URL, handleApiResponse } from '@/lib/api-client';

/**
 * Custom error class for job API errors
 * @deprecated Use ApiClientError from api-client.ts
 */
export class JobApiError extends Error {
  statusCode: number;
  details?: unknown;

  constructor(message: string, statusCode: number, details?: unknown) {
    super(message);
    this.name = 'JobApiError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

/**
 * Create extraction job with markdown pipeline support
 */
export async function createExtractionJob(
  documentId: string,
  request: ExtractionJobCreate
): Promise<Job> {
  const response = await apiFetch(`${API_BASE_URL}/documents/${documentId}/parse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      extraction_schema: request.extraction_schema,
      custom_prompt: request.custom_prompt,
      model_provider_config: {
        provider: request.model_provider,
        model: request.model_name,
      },
      processing_mode: request.processing_mode,
      markdown_converter: request.markdown_converter,
      markdown_format: request.markdown_format,
      enable_thinking: request.enable_thinking,
      thinking_budget: request.thinking_budget,
      callback_url: request.callback_url,
    }),
  });
  return handleApiResponse<Job>(response);
}

/**
 * Get document pages with markdown content
 */
export async function getDocumentPages(documentId: string): Promise<DocumentPage[]> {
  const response = await apiFetch(`${API_BASE_URL}/documents/${documentId}/pages`);
  return handleApiResponse<DocumentPage[]>(response);
}

/**
 * Get job details
 */
export async function getJob(jobId: string): Promise<Job> {
  const response = await apiFetch(`${API_BASE_URL}/jobs/${jobId}`);
  return handleApiResponse<Job>(response);
}

/**
 * Get job status
 */
export async function getJobStatus(jobId: string): Promise<Job> {
  const response = await apiFetch(`${API_BASE_URL}/jobs/${jobId}/status`);
  return handleApiResponse<Job>(response);
}

/**
 * List jobs with optional filtering
 */
export async function listJobs(params?: {
  limit?: number;
  offset?: number;
  status?: string;
}): Promise<{ jobs: Job[]; total: number; limit: number; offset: number }> {
  const queryParams = new URLSearchParams();
  if (params?.limit) queryParams.set('limit', params.limit.toString());
  if (params?.offset) queryParams.set('offset', params.offset.toString());
  if (params?.status) queryParams.set('status', params.status);

  const url = `${API_BASE_URL}/jobs${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
  const response = await apiFetch(url);
  return handleApiResponse(response);
}
