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
 * Processing mode for extraction jobs (DEPRECATED)
 * CRITICAL: Values MUST match backend validation in app/api/jobs.py
 * @deprecated Use SplitMode and ExtractionMode instead
 */
export enum ProcessingMode {
  PER_PAGE = "per_page",  // Direct: Per-page vision→JSON
  BATCH = "batch",         // Batch: All pages vision→JSON (faster)
  MARKDOWN = "markdown",   // Two-stage: Vision→Markdown→JSON (reusable)
}

/**
 * Split mode - how document pages are grouped for extraction
 * CRITICAL: Values MUST match backend app/models/enums.py SplitMode
 */
export enum SplitMode {
  PER_PAGE = "per_page",   // Each page processed individually (N API calls)
  BATCH = "batch",          // All pages processed together (1 API call, recommended)
  AUTO = "auto",            // LLM detects document boundaries, separate jobs per child
}

/**
 * Extraction mode - how extraction is performed
 * CRITICAL: Values MUST match backend app/models/enums.py ExtractionMode
 */
export enum ExtractionMode {
  VLLM = "vllm",            // Vision LLM extracts directly from images
  MARKDOWN = "markdown",    // Convert to markdown first, then extract (better for tables)
}

/**
 * Markdown converter types for image-to-markdown conversion.
 * CRITICAL: Values MUST match backend app/models/enums.py MarkdownConverter exactly.
 *
 * These converters use vision models to generate markdown from images:
 * - GEMINI_VISION: Google Gemini 2.5 Flash vision model
 * - GPT4V: OpenAI GPT-4 Vision model
 */
export enum MarkdownConverter {
  GEMINI_VISION = "gemini_vision",
  GPT4V = "gpt4v",
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

/**
 * Split mode helper functions
 */
export function getSplitModeLabel(mode: SplitMode): string {
  const labels: Record<SplitMode, string> = {
    [SplitMode.PER_PAGE]: "Per Page",
    [SplitMode.BATCH]: "Batch",
    [SplitMode.AUTO]: "Auto (LLM Split)",
  };
  return labels[mode];
}

export function getSplitModeDescription(mode: SplitMode): string {
  const descriptions: Record<SplitMode, string> = {
    [SplitMode.PER_PAGE]: "Process each page individually (N API calls)",
    [SplitMode.BATCH]: "Process all pages together (1 API call, recommended)",
    [SplitMode.AUTO]: "LLM detects document boundaries, creates separate jobs per document (costs extra credits)",
  };
  return descriptions[mode];
}

export function getSplitModeColor(mode: SplitMode): string {
  const colors: Record<SplitMode, string> = {
    [SplitMode.PER_PAGE]: "text-purple-600",
    [SplitMode.BATCH]: "text-blue-600",
    [SplitMode.AUTO]: "text-orange-600",
  };
  return colors[mode];
}

export function isSplitMode(value: string): value is SplitMode {
  return Object.values(SplitMode).includes(value as SplitMode);
}

/**
 * Extraction mode helper functions
 */
export function getExtractionModeLabel(mode: ExtractionMode): string {
  const labels: Record<ExtractionMode, string> = {
    [ExtractionMode.VLLM]: "Vision LLM",
    [ExtractionMode.MARKDOWN]: "Markdown Pipeline",
  };
  return labels[mode];
}

export function getExtractionModeDescription(mode: ExtractionMode): string {
  const descriptions: Record<ExtractionMode, string> = {
    [ExtractionMode.VLLM]: "Direct extraction from page images using vision model",
    [ExtractionMode.MARKDOWN]: "Convert to markdown first, then extract (better for tables)",
  };
  return descriptions[mode];
}

export function getExtractionModeColor(mode: ExtractionMode): string {
  const colors: Record<ExtractionMode, string> = {
    [ExtractionMode.VLLM]: "text-blue-600",
    [ExtractionMode.MARKDOWN]: "text-green-600",
  };
  return colors[mode];
}

export function isExtractionMode(value: string): value is ExtractionMode {
  return Object.values(ExtractionMode).includes(value as ExtractionMode);
}

export function getMarkdownConverterLabel(converter: MarkdownConverter): string {
  const labels: Record<MarkdownConverter, string> = {
    [MarkdownConverter.GEMINI_VISION]: "Gemini Vision",
    [MarkdownConverter.GPT4V]: "GPT-4 Vision",
  };
  return labels[converter];
}

export function getMarkdownConverterDescription(converter: MarkdownConverter): string {
  const descriptions: Record<MarkdownConverter, string> = {
    [MarkdownConverter.GEMINI_VISION]: "Google Gemini 2.5 Flash - Fast, accurate, good for most documents",
    [MarkdownConverter.GPT4V]: "OpenAI GPT-4 Vision - High quality, higher cost",
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

/**
 * Review request status (HITL system)
 * CRITICAL: Values MUST match backend app/models/enums.py
 */
export enum ReviewRequestStatus {
  PENDING = "pending",
  ASSIGNED = "assigned",
  IN_REVIEW = "in_review",
  COMPLETED = "completed",
  CANCELLED = "cancelled",
  ESCALATED = "escalated",
}

/**
 * Review priority levels (HITL system)
 * CRITICAL: Values MUST match backend app/models/enums.py
 */
export enum ReviewPriority {
  CRITICAL = "critical",
  HIGH = "high",
  NORMAL = "normal",
  LOW = "low",
}

/**
 * Job source - tracks where the job was created from
 * CRITICAL: Values MUST match backend app/models/enums.py
 */
export enum JobSource {
  WEBUI = "webui",
  API = "api",
}

export function getJobSourceLabel(source: JobSource): string {
  const labels: Record<JobSource, string> = {
    [JobSource.WEBUI]: "Web UI",
    [JobSource.API]: "API",
  };
  return labels[source];
}

export function getJobSourceColor(source: JobSource): string {
  const colors: Record<JobSource, string> = {
    [JobSource.WEBUI]: "bg-blue-100 text-blue-800",
    [JobSource.API]: "bg-purple-100 text-purple-800",
  };
  return colors[source];
}

/**
 * Model pricing record status.
 * CRITICAL: Values MUST match backend app/models/enums.py exactly.
 */
export enum PricingStatus {
  ACTIVE = "active",
  SUPERSEDED = "superseded",
  DEACTIVATED = "deactivated",
}

/**
 * Pricing type for model/converter pricing.
 * CRITICAL: Values MUST match backend app/models/enums.py exactly.
 */
export enum PricingType {
  TOKEN = "token",
  PAGE = "page",
  DOCUMENT = "document",
}

/**
 * Converter types for document processing.
 * CRITICAL: Values MUST match backend app/models/enums.py exactly.
 */
export enum ConverterType {
  IMAGE_TO_MARKDOWN = "image_to_markdown",
  DOCUMENT_TO_MARKDOWN = "document_to_markdown",
}

/**
 * LlamaExtract extraction quality modes.
 * CRITICAL: Values MUST match backend app/models/enums.py exactly.
 */
export enum LlamaExtractMode {
  STANDARD = "standard",
  PREMIUM = "premium",
}

/**
 * LlamaExtract extraction target scope.
 * CRITICAL: Values MUST match backend app/models/enums.py exactly.
 */
export enum LlamaExtractTarget {
  PER_DOC = "per_doc",
  PER_PAGE = "per_page",
}

/**
 * Helper functions for new enums
 */

export function getPricingStatusLabel(status: PricingStatus): string {
  const labels: Record<PricingStatus, string> = {
    [PricingStatus.ACTIVE]: "Active",
    [PricingStatus.SUPERSEDED]: "Superseded",
    [PricingStatus.DEACTIVATED]: "Deactivated",
  };
  return labels[status];
}

export function getPricingTypeLabel(type: PricingType): string {
  const labels: Record<PricingType, string> = {
    [PricingType.TOKEN]: "Token-based",
    [PricingType.PAGE]: "Per Page",
    [PricingType.DOCUMENT]: "Per Document",
  };
  return labels[type];
}

export function getConverterTypeLabel(type: ConverterType): string {
  const labels: Record<ConverterType, string> = {
    [ConverterType.IMAGE_TO_MARKDOWN]: "Image to Markdown",
    [ConverterType.DOCUMENT_TO_MARKDOWN]: "Document to Markdown",
  };
  return labels[type];
}

export function getLlamaExtractModeLabel(mode: LlamaExtractMode): string {
  const labels: Record<LlamaExtractMode, string> = {
    [LlamaExtractMode.STANDARD]: "Standard (1 credit/page)",
    [LlamaExtractMode.PREMIUM]: "Premium (2 credits/page)",
  };
  return labels[mode];
}

export function getLlamaExtractTargetLabel(target: LlamaExtractTarget): string {
  const labels: Record<LlamaExtractTarget, string> = {
    [LlamaExtractTarget.PER_DOC]: "Per Document",
    [LlamaExtractTarget.PER_PAGE]: "Per Page",
  };
  return labels[target];
}
