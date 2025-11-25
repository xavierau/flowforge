/**
 * Type-safe enums matching backend domain enums.
 *
 * CRITICAL: These values MUST match app/models/enums.py exactly.
 * Any changes to backend enums require updating these definitions.
 */

/**
 * Credit transaction types (matches backend database schema)
 */
export enum CreditTransactionType {
  DEDUCTION = "deduction",
  TOPUP = "topup",
  REFUND = "refund",
  ADMIN_ADJUSTMENT = "admin_adjustment",
  TRIAL_SIGNUP = "trial_signup",
  MIGRATION_BALANCE_IMPORT = "migration_balance_import",
}

/**
 * Reference types for transactions (matches backend database schema)
 */
export enum ReferenceType {
  EXTRACTION_JOB = "extraction_job",
  PAYMENT = "payment",
  TENANT_REGISTRATION = "tenant_registration",
  ADMIN_MANUAL_ADJUSTMENT = "admin_manual_adjustment",
  MANUAL = "manual",
}

/**
 * Extraction job status lifecycle
 */
export enum JobStatus {
  QUEUED = "queued",
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed",
}

/**
 * Document processing status lifecycle
 */
export enum DocumentStatus {
  UPLOADED = "uploaded",
  PROCESSING = "processing",
  READY_FOR_EXTRACTION = "ready_for_extraction",
  COMPLETED = "completed",
  FAILED = "failed",
}

/**
 * User roles for RBAC
 */
export enum UserRole {
  OWNER = "owner",
  ADMIN = "admin",
  MEMBER = "member",
  VIEWER = "viewer",
}

/**
 * Subscription status
 */
export enum SubscriptionStatus {
  ACTIVE = "active",
  TRIAL = "trial",
  PAST_DUE = "past_due",
  CANCELED = "canceled",
  EXPIRED = "expired",
}

/**
 * Processing mode for extraction jobs
 * CRITICAL: Values MUST match backend validation in app/api/jobs.py
 */
export enum ProcessingMode {
  PER_PAGE = "per_page",  // Direct: Per-page vision→JSON
  BATCH = "batch",         // Batch: All pages vision→JSON (faster)
  MARKDOWN = "markdown",   // Two-stage: Vision→Markdown→JSON (reusable)
}

/**
 * Markdown converter providers
 * CRITICAL: Values MUST match backend converter_factory.py keys
 */
export enum MarkdownConverter {
  GEMINI_VISION = "gemini_vision",
  GPT4V = "gpt4v",
  QWEN_VISION = "qwen_vision",
}

/**
 * Markdown format styles
 */
export enum MarkdownFormat {
  STANDARD = "standard",
  TABLE_HEAVY = "table_heavy",
  LAYOUT_PRESERVED = "layout_preserved",
}

/**
 * Type guards for runtime validation
 */

export function isCreditTransactionType(value: string): value is CreditTransactionType {
  return Object.values(CreditTransactionType).includes(value as CreditTransactionType);
}

export function isJobStatus(value: string): value is JobStatus {
  return Object.values(JobStatus).includes(value as JobStatus);
}

export function isDocumentStatus(value: string): value is DocumentStatus {
  return Object.values(DocumentStatus).includes(value as DocumentStatus);
}

/**
 * Helper functions for display
 */

export function getJobStatusLabel(status: JobStatus): string {
  const labels: Record<JobStatus, string> = {
    [JobStatus.QUEUED]: "Queued",
    [JobStatus.PROCESSING]: "Processing",
    [JobStatus.COMPLETED]: "Completed",
    [JobStatus.FAILED]: "Failed",
  };
  return labels[status];
}

export function getJobStatusColor(status: JobStatus): string {
  const colors: Record<JobStatus, string> = {
    [JobStatus.QUEUED]: "text-blue-600",
    [JobStatus.PROCESSING]: "text-yellow-600",
    [JobStatus.COMPLETED]: "text-green-600",
    [JobStatus.FAILED]: "text-red-600",
  };
  return colors[status];
}

export function getCreditTransactionTypeLabel(type: CreditTransactionType): string {
  const labels: Record<CreditTransactionType, string> = {
    [CreditTransactionType.DEDUCTION]: "Deduction",
    [CreditTransactionType.TOPUP]: "Top Up",
    [CreditTransactionType.REFUND]: "Refund",
    [CreditTransactionType.ADMIN_ADJUSTMENT]: "Admin Adjustment",
    [CreditTransactionType.TRIAL_SIGNUP]: "Trial Credits",
    [CreditTransactionType.MIGRATION_BALANCE_IMPORT]: "Migration Import",
  };
  return labels[type];
}

export function getProcessingModeLabel(mode: ProcessingMode): string {
  const labels: Record<ProcessingMode, string> = {
    [ProcessingMode.PER_PAGE]: "Direct (Per Page)",
    [ProcessingMode.BATCH]: "Batch",
    [ProcessingMode.MARKDOWN]: "Markdown Pipeline",
  };
  return labels[mode];
}

export function getProcessingModeColor(mode: ProcessingMode): string {
  const colors: Record<ProcessingMode, string> = {
    [ProcessingMode.PER_PAGE]: "text-purple-600",
    [ProcessingMode.BATCH]: "text-blue-600",
    [ProcessingMode.MARKDOWN]: "text-green-600",
  };
  return colors[mode];
}

export function getMarkdownConverterLabel(converter: MarkdownConverter): string {
  const labels: Record<MarkdownConverter, string> = {
    [MarkdownConverter.GEMINI_VISION]: "Gemini Vision",
    [MarkdownConverter.GPT4V]: "GPT-4 Vision",
    [MarkdownConverter.QWEN_VISION]: "Qwen Vision",
  };
  return labels[converter];
}

export function getMarkdownConverterDescription(converter: MarkdownConverter): string {
  const descriptions: Record<MarkdownConverter, string> = {
    [MarkdownConverter.GEMINI_VISION]: "Google Gemini 2.5 Flash - Fast, accurate, good for most documents",
    [MarkdownConverter.GPT4V]: "OpenAI GPT-4 Vision - High quality, higher cost",
    [MarkdownConverter.QWEN_VISION]: "Qwen3-VL-8B - Cost-effective ($0.72/M tokens), supports special QwenVL formats",
  };
  return descriptions[converter];
}

export function getMarkdownFormatLabel(format: MarkdownFormat): string {
  const labels: Record<MarkdownFormat, string> = {
    [MarkdownFormat.STANDARD]: "Standard",
    [MarkdownFormat.TABLE_HEAVY]: "Table Heavy",
    [MarkdownFormat.LAYOUT_PRESERVED]: "Layout Preserved",
  };
  return labels[format];
}
