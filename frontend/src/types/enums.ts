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
