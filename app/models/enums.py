"""
Domain enums for type-safe constant values.

These enums use str inheritance to maintain backward compatibility with existing
database string values while providing type safety and IDE support.
"""
from enum import Enum


class CreditTransactionType(str, Enum):
    """
    Credit transaction types (matches current database schema).

    Controls how credits flow in the system:
    - DEDUCTION: Credits consumed (negative amount) - used for extraction jobs
    - TOPUP: Manual credit purchase (positive amount)
    - REFUND: Credits returned (positive)
    - ADMIN_ADJUSTMENT: Manual correction (positive or negative)
    - TRIAL_SIGNUP: Initial free credits (positive)
    - MIGRATION_BALANCE_IMPORT: Data migration (positive)
    """
    DEDUCTION = "deduction"
    TOPUP = "topup"
    REFUND = "refund"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    TRIAL_SIGNUP = "trial_signup"
    MIGRATION_BALANCE_IMPORT = "migration_balance_import"


class ReferenceType(str, Enum):
    """
    Reference types for linking transactions to source entities (matches current database schema).

    Used with reference_id to create foreign key relationships.
    """
    EXTRACTION_JOB = "extraction_job"
    PAYMENT = "payment"
    TENANT_REGISTRATION = "tenant_registration"
    ADMIN_MANUAL_ADJUSTMENT = "admin_manual_adjustment"
    MANUAL = "manual"


class JobStatus(str, Enum):
    """
    Extraction job status lifecycle.

    State machine:
    queued → processing → completed
                ↓
              failed
    """
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentStatus(str, Enum):
    """
    Document processing status lifecycle.

    State machine:
    uploaded → processing → ready_for_extraction → completed
                  ↓
                failed
    """
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY_FOR_EXTRACTION = "ready_for_extraction"
    COMPLETED = "completed"
    FAILED = "failed"


class UserRole(str, Enum):
    """User roles for RBAC"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class SubscriptionStatus(str, Enum):
    """Subscription lifecycle states"""
    ACTIVE = "active"
    TRIAL = "trial"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"


class NodeType(str, Enum):
    """
    Workflow node types.

    These match the frontend NodeType enum exactly:
    - HTTP_TRIGGER: Entry point for workflow (webhook)
    - EXTRACTION: VLLM-based document extraction
    - PYTHON_RUNNER: Execute Python code
    - HTTP_REQUEST: Make HTTP requests
    - IF: Conditional branching
    - JOIN: Synchronization barrier for parallel branches
    - LOOP: n8n-style array iteration (for each item)
    - LLM: General-purpose LLM prompt/response
    - HUMAN_REVIEW: Human-in-the-loop review node
    """
    HTTP_TRIGGER = "httpTrigger"
    EXTRACTION = "extraction"
    PYTHON_RUNNER = "pythonRunner"
    HTTP_REQUEST = "httpRequest"
    IF = "if"
    JOIN = "join"
    LOOP = "loop"
    LLM = "llm"
    HUMAN_REVIEW = "humanReview"


class HttpMethod(str, Enum):
    """HTTP methods for HttpRequest nodes"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class WorkflowExecutionStatus(str, Enum):
    """
    Workflow execution status lifecycle.

    State machine:
    pending → running → completed
               ↓
             failed

    Also supports:
    - paused: Execution paused by user
    - cancelled: Execution cancelled by user
    - timeout: Execution exceeded timeout
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class WorkflowNodeExecutionStatus(str, Enum):
    """
    Individual node execution status.

    State machine:
    pending → running → completed
               ↓
             failed/skipped
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"  # For conditional branches not taken


class ProcessingMode(str, Enum):
    """
    Extraction processing modes.

    Controls how document extraction is performed:
    - DIRECT: Per-page vision → JSON (legacy, deprecated)
    - BATCH: All pages vision → JSON in single call (current default)
    - MARKDOWN: Vision → Markdown → JSON (new two-stage pipeline)
    """
    DIRECT = "direct"
    BATCH = "batch"
    MARKDOWN = "markdown"


class MarkdownConverter(str, Enum):
    """
    Markdown converter types for image-to-markdown conversion.

    These converters use vision models to generate markdown from images:
    - GEMINI_VISION: Google Gemini 2.5 Flash vision model
    - GPT4V: OpenAI GPT-4 Vision model
    """
    GEMINI_VISION = "gemini_vision"
    GPT4V = "gpt4v"


class MarkdownFormat(str, Enum):
    """
    Markdown format styles for conversion output.

    Controls how the markdown converter formats the output:
    - STANDARD: Standard markdown with basic formatting
    - TABLE_HEAVY: Emphasis on converting tabular data to markdown tables
    - LAYOUT_PRESERVED: Preserve original document layout structure
    """
    STANDARD = "standard"
    TABLE_HEAVY = "table_heavy"
    LAYOUT_PRESERVED = "layout_preserved"


class ReviewRequestStatus(str, Enum):
    """
    Review request status lifecycle.

    State machine:
    pending → assigned → in_review → completed
                ↓
            cancelled/escalated
    """
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"


class ReviewPriority(str, Enum):
    """
    Review priority levels based on confidence scores.

    Priority determines SLA deadlines:
    - CRITICAL: < 0.30 confidence (1 hour SLA)
    - HIGH: 0.30-0.50 confidence (2 hour SLA)
    - NORMAL: 0.50-0.60 confidence (4 hour SLA)
    - LOW: 0.60-0.70 confidence (8 hour SLA)
    """
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class CorrectionType(str, Enum):
    """
    Types of corrections made during human review.

    - VALUE_CHANGE: Field value was corrected
    - FIELD_ADDITION: New field was added
    - FIELD_REMOVAL: Field was removed (incorrect extraction)
    - TYPE_CORRECTION: Data type was corrected
    """
    VALUE_CHANGE = "value_change"
    FIELD_ADDITION = "field_addition"
    FIELD_REMOVAL = "field_removal"
    TYPE_CORRECTION = "type_correction"
