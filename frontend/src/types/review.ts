/**
 * Review System Type Definitions
 *
 * CRITICAL: These types MUST match backend models exactly:
 * - app/models/review_request.py
 * - app/models/review_correction.py
 * - app/models/enums.py (ReviewRequestStatus, ReviewPriority)
 */

/**
 * Review request status lifecycle
 * pending → assigned → in_review → completed
 *             ↓            ↓
 *         cancelled    escalated
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
 * Review priority levels
 */
export enum ReviewPriority {
  CRITICAL = "critical",
  HIGH = "high",
  NORMAL = "normal",
  LOW = "low",
}

/**
 * Correction types for tracking changes
 * MUST match backend: app/models/enums.py CorrectionType
 */
export enum CorrectionType {
  VALUE_CHANGE = "value_change",
  FIELD_ADDITION = "field_addition",
  FIELD_REMOVAL = "field_removal",
  TYPE_CORRECTION = "type_correction",
}

/**
 * Review request model (matches backend ReviewRequest)
 */
export interface ReviewRequest {
  id: string;
  tenant_id: string;
  extraction_job_id: string;
  document_id?: string; // Populated via join

  // Routing information
  trigger_reason: string;
  confidence_score: number | null;
  priority: ReviewPriority;

  // Assignment information
  status: ReviewRequestStatus;
  assigned_to_user_id: string | null;
  assigned_to_user_name?: string; // Populated via join
  assigned_at: string | null;

  // SLA tracking
  sla_minutes: number;
  sla_deadline: string | null;
  escalated: boolean;
  escalated_at: string | null;
  escalated_to_user_id: string | null;
  escalated_to_user_name?: string; // Populated via join

  // Completion tracking
  completed_at: string | null;
  review_time_minutes: number | null;

  // Metadata
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;

  // Joined data (from API response)
  extraction_job?: {
    id: string;
    document_id: string;
    schema_name?: string;
    status: string;
  };
  document?: {
    id: string;
    filename: string;
    page_count: number;
  };
  extracted_data?: Record<string, unknown>; // Current extraction result
}

/**
 * Review correction model (matches backend ReviewCorrection)
 */
export interface ReviewCorrection {
  id?: string; // Optional for new corrections
  review_request_id?: string;
  extraction_result_id: string;

  // Field information
  field_path: string; // JSONPath to field (e.g., "invoice.total")
  original_value: unknown;
  corrected_value: unknown;

  // Correction metadata
  correction_type: CorrectionType;
  correction_notes: string | null;
  reviewer_confidence: number | null; // 0.0-1.0

  // Timestamps
  created_at?: string;
}

/**
 * Queue filter parameters
 */
export interface QueueFilters {
  status?: ReviewRequestStatus | ReviewRequestStatus[];
  priority?: ReviewPriority | ReviewPriority[];
  assigned_to_me?: boolean;
  unassigned?: boolean;
  escalated?: boolean;
  sort_by?: "priority" | "age" | "confidence" | "sla_deadline";
  sort_order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

/**
 * Review queue response
 */
export interface ReviewQueueResponse {
  items: ReviewRequest[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/**
 * Review metrics for dashboard
 */
export interface ReviewMetrics {
  pending_count: number;
  assigned_count: number;
  in_review_count: number;
  completed_today: number;
  avg_review_time_minutes: number;
  sla_breach_count: number;
  accuracy_rate: number; // % of reviews with corrections
  my_queue_count: number;
  escalated_count: number;
}

/**
 * Submit review request
 */
export interface SubmitReviewRequest {
  corrections: ReviewCorrection[];
  review_notes?: string;
  action: "approve" | "reject" | "escalate";
}

/**
 * Assign review request
 */
export interface AssignReviewRequest {
  user_id: string;
}

/**
 * Type guards for runtime validation
 */
export function isReviewRequestStatus(value: string): value is ReviewRequestStatus {
  return Object.values(ReviewRequestStatus).includes(value as ReviewRequestStatus);
}

export function isReviewPriority(value: string): value is ReviewPriority {
  return Object.values(ReviewPriority).includes(value as ReviewPriority);
}

/**
 * Helper functions for display
 */
export function getReviewStatusLabel(status: ReviewRequestStatus): string {
  const labels: Record<ReviewRequestStatus, string> = {
    [ReviewRequestStatus.PENDING]: "Pending",
    [ReviewRequestStatus.ASSIGNED]: "Assigned",
    [ReviewRequestStatus.IN_REVIEW]: "In Review",
    [ReviewRequestStatus.COMPLETED]: "Completed",
    [ReviewRequestStatus.CANCELLED]: "Cancelled",
    [ReviewRequestStatus.ESCALATED]: "Escalated",
  };
  return labels[status];
}

export function getReviewStatusColor(status: ReviewRequestStatus): string {
  const colors: Record<ReviewRequestStatus, string> = {
    [ReviewRequestStatus.PENDING]: "text-gray-600",
    [ReviewRequestStatus.ASSIGNED]: "text-blue-600",
    [ReviewRequestStatus.IN_REVIEW]: "text-yellow-600",
    [ReviewRequestStatus.COMPLETED]: "text-green-600",
    [ReviewRequestStatus.CANCELLED]: "text-gray-400",
    [ReviewRequestStatus.ESCALATED]: "text-red-600",
  };
  return colors[status];
}

export function getReviewPriorityLabel(priority: ReviewPriority): string {
  const labels: Record<ReviewPriority, string> = {
    [ReviewPriority.CRITICAL]: "Critical",
    [ReviewPriority.HIGH]: "High",
    [ReviewPriority.NORMAL]: "Normal",
    [ReviewPriority.LOW]: "Low",
  };
  return labels[priority];
}

export function getReviewPriorityColor(priority: ReviewPriority): string {
  const colors: Record<ReviewPriority, string> = {
    [ReviewPriority.CRITICAL]: "text-red-600",
    [ReviewPriority.HIGH]: "text-orange-600",
    [ReviewPriority.NORMAL]: "text-blue-600",
    [ReviewPriority.LOW]: "text-gray-600",
  };
  return colors[priority];
}

export function getReviewPriorityIcon(priority: ReviewPriority): string {
  const icons: Record<ReviewPriority, string> = {
    [ReviewPriority.CRITICAL]: "⚡",
    [ReviewPriority.HIGH]: "🔶",
    [ReviewPriority.NORMAL]: "🟢",
    [ReviewPriority.LOW]: "⚪",
  };
  return icons[priority];
}

/**
 * Calculate confidence level from score
 */
export function getConfidenceLevel(
  score: number | null
): "high" | "medium" | "low" | "unknown" {
  if (score === null) return "unknown";
  if (score >= 0.8) return "high";
  if (score >= 0.5) return "medium";
  return "low";
}

export function getConfidenceBadgeProps(score: number | null): {
  label: string;
  color: string;
  icon: string;
} {
  const level = getConfidenceLevel(score);

  const props = {
    high: { label: "High Confidence", color: "text-green-600", icon: "✓" },
    medium: { label: "Medium Confidence", color: "text-orange-600", icon: "⚠️" },
    low: { label: "Low Confidence", color: "text-red-600", icon: "❌" },
    unknown: { label: "Unknown", color: "text-gray-600", icon: "?" },
  };

  return props[level];
}

/**
 * Calculate SLA status
 */
export function getSLAStatus(
  slaDeadline: string | null,
  status: ReviewRequestStatus
): "ok" | "warning" | "breached" | "completed" {
  if (status === ReviewRequestStatus.COMPLETED || status === ReviewRequestStatus.CANCELLED) {
    return "completed";
  }

  if (!slaDeadline) return "ok";

  const deadline = new Date(slaDeadline);
  const now = new Date();
  const hoursRemaining = (deadline.getTime() - now.getTime()) / (1000 * 60 * 60);

  if (hoursRemaining < 0) return "breached";
  if (hoursRemaining < 1) return "warning";
  return "ok";
}

export function getSLAStatusColor(slaStatus: "ok" | "warning" | "breached" | "completed"): string {
  const colors = {
    ok: "text-green-600",
    warning: "text-orange-600",
    breached: "text-red-600",
    completed: "text-gray-400",
  };
  return colors[slaStatus];
}
