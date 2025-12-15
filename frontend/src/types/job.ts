/**
 * Job Types
 * Corresponds to app/schemas/job.py
 */

import type { ProcessingMode, MarkdownConverter, MarkdownFormat, JobSource } from './enums';

export interface JobProgress {
  total_pages: number;
  completed_pages: number;
}

export interface JobStatusResponse {
  job_id: string;
  document_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress?: JobProgress;
  started_at?: string;
  updated_at: string;
  error?: string;
}

export interface ExtractionMetadata {
  model_used: string;
  input_tokens: number;
  output_tokens: number;
  tokens_used: number;
  processing_time_ms: number;
  confidence_score: number;
}

export interface JobResultResponse {
  job_id: string;
  document_id: string;
  schema_definition_id?: string;  // ID of saved schema definition used (null if custom schema)
  status: string;
  extracted_data: Record<string, any>;
  metadata: ExtractionMetadata;
  completed_at: string;
  // Job configuration used for this extraction
  extraction_schema: Record<string, any>;
  custom_prompt?: string;
  model_provider: string;
  model_name: string;
  callback_url?: string;
  enable_thinking?: boolean;  // Whether thinking mode was enabled
  thinking_budget?: number;   // Thinking budget in tokens
  processing_mode?: ProcessingMode;  // Processing mode used
  markdown_converter?: MarkdownConverter;  // Markdown converter if markdown mode
  markdown_format?: MarkdownFormat;  // Markdown format if markdown mode
}

// For list page display (combining status and metadata)
export interface Job {
  id: string;
  document_id: string;
  document_name?: string;
  schema_definition_id?: string;  // ID of saved schema definition used (null if custom schema)
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress?: JobProgress;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
  error?: string;
  // For display in list
  model_used?: string;
  processing_mode?: ProcessingMode;  // Processing mode used
  markdown_converter?: MarkdownConverter;  // Markdown converter if markdown mode
  markdown_format?: MarkdownFormat;  // Markdown format if markdown mode
  source?: JobSource;  // Job source - webui or api
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Extraction job creation request
 */
export interface ExtractionJobCreate {
  extraction_schema: Record<string, any>;
  custom_prompt?: string;
  model_provider: string;
  model_name: string;
  processing_mode: ProcessingMode;
  markdown_converter?: MarkdownConverter;
  markdown_format?: MarkdownFormat;
  enable_thinking: boolean;
  thinking_budget: number;
  callback_url?: string;
}
