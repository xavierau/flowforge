/**
 * Inbound Email Types
 * Corresponds to app/schemas/inbound_email.py
 */

import type {
  SplitMode,
  ExtractionMode,
  MarkdownConverter,
  MarkdownFormat,
  LlamaExtractMode,
  LlamaExtractTarget,
} from './enums';

// ============================================================================
// ENUMS / STATUS TYPES
// ============================================================================

/**
 * Inbound email log status
 * CRITICAL: Values MUST match backend app/schemas/inbound_email.py
 */
export type InboundEmailLogStatus =
  | 'received'
  | 'processing'
  | 'processed'
  | 'failed'
  | 'rejected';

// ============================================================================
// REQUEST INTERFACES
// ============================================================================

/**
 * Request payload for creating a new inbound email address
 * Corresponds to InboundEmailAddressCreate in backend
 */
export interface InboundEmailAddressCreate {
  /** User-friendly name for this email address (max 255 chars) */
  name: string;
  /** Optional description of this email address purpose (max 1000 chars) */
  description?: string;
  /** Optional list of allowed sender patterns (email or *@domain.com) */
  allowed_senders?: string[];

  // Job configuration
  /** ID of saved schema definition to use for extraction */
  schema_definition_id?: string;
  /** Custom JSON schema for extraction (used if schema_definition_id not provided) */
  extraction_schema?: Record<string, unknown>;
  /** Custom extraction instructions (max 5000 chars) */
  custom_prompt?: string;
  /** VLLM provider for extraction (default: "google") */
  model_provider?: string;
  /** Model name for extraction (default: "gemini-2.5-flash") */
  model_name?: string;
  /** Split mode: 'per_page', 'batch', or 'auto' (default: "batch") */
  split_mode?: SplitMode | string;
  /** Extraction mode: 'vllm' or 'markdown' (default: "vllm") */
  extraction_mode?: ExtractionMode | string;
  /** Markdown converter (only for extraction_mode='markdown') */
  markdown_converter?: MarkdownConverter | string;
  /** Markdown format style (only for extraction_mode='markdown') */
  markdown_format?: MarkdownFormat | string;
  /** LlamaExtract extraction mode: 'standard' or 'premium' */
  llamaextract_mode?: LlamaExtractMode | string;
  /** LlamaExtract extraction target: 'per_doc' or 'per_page' */
  llamaextract_target?: LlamaExtractTarget | string;
  /** Optional webhook URL to POST results to when job completes (max 1024 chars) */
  callback_url?: string;
}

/**
 * Request payload for updating an inbound email address
 * Corresponds to InboundEmailAddressUpdate in backend
 * All fields are optional - only provided fields will be updated
 */
export interface InboundEmailAddressUpdate {
  /** Updated name for this email address (max 255 chars) */
  name?: string;
  /** Updated description (max 1000 chars) */
  description?: string;
  /** Whether this email address is active */
  is_active?: boolean;
  /** Updated list of allowed sender patterns */
  allowed_senders?: string[];

  // Job configuration
  /** Updated schema definition ID */
  schema_definition_id?: string;
  /** Updated custom JSON schema for extraction */
  extraction_schema?: Record<string, unknown>;
  /** Updated custom extraction instructions (max 5000 chars) */
  custom_prompt?: string;
  /** Updated VLLM provider */
  model_provider?: string;
  /** Updated model name */
  model_name?: string;
  /** Updated split mode */
  split_mode?: SplitMode | string;
  /** Updated extraction mode */
  extraction_mode?: ExtractionMode | string;
  /** Updated markdown converter */
  markdown_converter?: MarkdownConverter | string;
  /** Updated markdown format style */
  markdown_format?: MarkdownFormat | string;
  /** Updated LlamaExtract extraction mode */
  llamaextract_mode?: LlamaExtractMode | string;
  /** Updated LlamaExtract extraction target */
  llamaextract_target?: LlamaExtractTarget | string;
  /** Updated webhook URL (max 1024 chars) */
  callback_url?: string;
}

// ============================================================================
// RESPONSE INTERFACES
// ============================================================================

/**
 * Response for an inbound email address
 * Corresponds to InboundEmailAddressResponse in backend
 */
export interface InboundEmailAddressResponse {
  /** Unique email address identifier (UUID) */
  id: string;
  /** Full email address (uuid@domain) e.g., "abc123@parse.phbsolution.com" */
  email_address: string;
  /** User-friendly name */
  name: string;
  /** Description of purpose */
  description?: string;
  /** Whether this address is active */
  is_active: boolean;
  /** List of allowed sender patterns */
  allowed_senders?: string[];

  // Job configuration
  /** Schema definition ID for extraction */
  schema_definition_id?: string;
  /** Custom JSON schema for extraction */
  extraction_schema?: Record<string, unknown>;
  /** VLLM provider */
  model_provider: string;
  /** Model name */
  model_name: string;
  /** Split mode for processing */
  split_mode: string;
  /** Extraction mode */
  extraction_mode: string;
  /** Webhook URL for results */
  callback_url?: string;

  // Stats
  /** Total number of emails received */
  emails_received_count: number;
  /** Total number of documents processed from emails */
  documents_processed_count: number;
  /** Timestamp of last received email (ISO 8601 string) */
  last_email_at?: string;

  // Timestamps
  /** Creation timestamp (ISO 8601 string) */
  created_at: string;
  /** Last update timestamp (ISO 8601 string) */
  updated_at: string;
}

/**
 * Paginated response for listing inbound email addresses
 * Corresponds to InboundEmailAddressListResponse in backend
 */
export interface InboundEmailAddressListResponse {
  /** List of inbound email addresses */
  addresses: InboundEmailAddressResponse[];
  /** Total number of addresses */
  total: number;
  /** Results per page */
  limit: number;
  /** Offset for pagination */
  offset: number;
}

/**
 * Response for an inbound email log entry
 * Corresponds to InboundEmailLogResponse in backend
 */
export interface InboundEmailLogResponse {
  /** Unique log entry identifier (UUID) */
  id: string;
  /** Email address of the sender */
  sender_email: string;
  /** Display name of the sender */
  sender_name?: string;
  /** Email subject line */
  subject?: string;
  /** Processing status */
  status: InboundEmailLogStatus;
  /** Error message if processing failed */
  error_message?: string;
  /** Number of attachments in the email */
  attachment_count: number;
  /** List of attachment filenames */
  attachment_names?: string[];
  /** List of created document IDs (UUIDs) */
  document_ids?: string[];
  /** List of created extraction job IDs (UUIDs) */
  extraction_job_ids?: string[];
  /** When the email was received (ISO 8601 string) */
  received_at: string;
  /** When processing completed (ISO 8601 string) */
  processed_at?: string;
}

/**
 * Paginated response for listing inbound email logs
 * Corresponds to InboundEmailLogListResponse in backend
 */
export interface InboundEmailLogListResponse {
  /** List of inbound email log entries */
  logs: InboundEmailLogResponse[];
  /** Total number of log entries */
  total: number;
  /** Results per page */
  limit: number;
  /** Offset for pagination */
  offset: number;
}

// ============================================================================
// HELPER TYPES
// ============================================================================

/**
 * Query parameters for listing inbound email addresses
 */
export interface InboundEmailAddressListParams {
  /** Number of results to return */
  limit?: number;
  /** Offset for pagination */
  offset?: number;
  /** Filter by active status */
  is_active?: boolean;
}

/**
 * Query parameters for listing inbound email logs
 */
export interface InboundEmailLogListParams {
  /** Number of results to return */
  limit?: number;
  /** Offset for pagination */
  offset?: number;
  /** Filter by status */
  status?: InboundEmailLogStatus;
  /** Filter by sender email (partial match) */
  sender_email?: string;
}

// ============================================================================
// TYPE GUARDS
// ============================================================================

/**
 * Type guard for InboundEmailLogStatus
 */
export function isInboundEmailLogStatus(value: string): value is InboundEmailLogStatus {
  return ['received', 'processing', 'processed', 'failed', 'rejected'].includes(value);
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Get human-readable label for inbound email log status
 */
export function getInboundEmailLogStatusLabel(status: InboundEmailLogStatus): string {
  const labels: Record<InboundEmailLogStatus, string> = {
    received: 'Received',
    processing: 'Processing',
    processed: 'Processed',
    failed: 'Failed',
    rejected: 'Rejected',
  };
  return labels[status];
}

/**
 * Get color class for inbound email log status
 */
export function getInboundEmailLogStatusColor(status: InboundEmailLogStatus): string {
  const colors: Record<InboundEmailLogStatus, string> = {
    received: 'text-blue-600',
    processing: 'text-yellow-600',
    processed: 'text-green-600',
    failed: 'text-red-600',
    rejected: 'text-orange-600',
  };
  return colors[status];
}

/**
 * Get badge variant for inbound email log status
 * Useful for UI components that use variant props
 */
export function getInboundEmailLogStatusVariant(
  status: InboundEmailLogStatus
): 'default' | 'secondary' | 'destructive' | 'outline' {
  const variants: Record<InboundEmailLogStatus, 'default' | 'secondary' | 'destructive' | 'outline'> = {
    received: 'secondary',
    processing: 'outline',
    processed: 'default',
    failed: 'destructive',
    rejected: 'destructive',
  };
  return variants[status];
}
