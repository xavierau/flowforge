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
                  ↓              ↓
                failed         split (for auto-split parent documents)
    """
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY_FOR_EXTRACTION = "ready_for_extraction"
    COMPLETED = "completed"
    FAILED = "failed"
    SPLIT = "split"  # Parent document has been split into children


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
    Extraction processing modes (DEPRECATED - use SplitMode + ExtractionMode instead).

    Controls how document extraction is performed:
    - DIRECT: Per-page vision → JSON (legacy, deprecated)
    - BATCH: All pages vision → JSON in single call (current default)
    - MARKDOWN: Vision → Markdown → JSON (new two-stage pipeline)

    Migration mapping:
    - batch → SplitMode.BATCH + ExtractionMode.VLLM
    - direct/per_page → SplitMode.PER_PAGE + ExtractionMode.VLLM
    - markdown → SplitMode.BATCH + ExtractionMode.MARKDOWN
    """
    DIRECT = "direct"
    BATCH = "batch"
    MARKDOWN = "markdown"


class SplitMode(str, Enum):
    """
    Document split mode - how pages are grouped for extraction.

    Controls page grouping strategy:
    - PER_PAGE: Each page processed individually (N API calls)
    - BATCH: All pages processed together in one call (1 API call, default)
    - AUTO: LLM detects document boundaries and creates separate jobs per child document
            (costs extra credits for boundary detection)
    """
    PER_PAGE = "per_page"
    BATCH = "batch"
    AUTO = "auto"


class ExtractionMode(str, Enum):
    """
    Extraction mode - how extraction is performed.

    Controls the extraction pipeline:
    - VLLM: Vision LLM extracts directly from page images (default)
    - MARKDOWN: Convert to markdown first, then extract from text (better for tables)
    """
    VLLM = "vllm"
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


class JobSource(str, Enum):
    """
    Source of job creation - distinguishes between WebUI and API submissions.

    - WEBUI: Job created through the web user interface
    - API: Job created through direct API calls (programmatic access)
    """
    WEBUI = "webui"
    API = "api"


class PricingStatus(str, Enum):
    """
    Model pricing record status.

    Controls the lifecycle of pricing records:
    - ACTIVE: Currently active pricing record
    - SUPERSEDED: Replaced by a newer pricing record
    - DEACTIVATED: Manually deactivated by admin
    """
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DEACTIVATED = "deactivated"


class PricingType(str, Enum):
    """
    Pricing type for model/converter pricing.

    Controls how credits are calculated:
    - TOKEN: Charged based on input/output tokens (default for LLMs)
    - PAGE: Charged per page processed (for document converters like LlamaParse)
    - DOCUMENT: Charged per document (flat rate per document)
    """
    TOKEN = "token"
    PAGE = "page"
    DOCUMENT = "document"


class ConverterType(str, Enum):
    """
    Converter types for document processing.

    - IMAGE_TO_MARKDOWN: Converts images to markdown (vision models)
    - DOCUMENT_TO_MARKDOWN: Converts entire documents to markdown (LlamaParse, etc.)
    """
    IMAGE_TO_MARKDOWN = "image_to_markdown"
    DOCUMENT_TO_MARKDOWN = "document_to_markdown"


class LlamaExtractMode(str, Enum):
    """
    LlamaExtract extraction quality modes.

    Our simplified modes map to LlamaExtract internal modes:
    - STANDARD: Maps to BALANCED (10 LlamaExtract credits/page)
    - PREMIUM: Maps to PREMIUM (60 LlamaExtract credits/page)

    Credit pricing (our internal credits):
    - STANDARD: 1 credit per page
    - PREMIUM: 2 credits per page
    """
    STANDARD = "standard"
    PREMIUM = "premium"


class LlamaExtractTarget(str, Enum):
    """
    LlamaExtract extraction target scope.

    - PER_DOC: Schema applied to entire document, returns single JSON object
    - PER_PAGE: Schema applied to each page, returns array of JSON objects
    """
    PER_DOC = "per_doc"
    PER_PAGE = "per_page"


class Provider(str, Enum):
    """
    Valid model/service providers.

    Centralized enum for all provider names used across the system.
    This ensures type safety and consistent provider validation.
    """
    GOOGLE = "google"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    LLAMAINDEX = "llamaindex"  # For LlamaParse document conversion
    LLAMAEXTRACT = "llamaextract"  # For LlamaExtract structured extraction
    QWEN = "qwen"

    @classmethod
    def values(cls) -> set[str]:
        """Get all valid provider values as a set."""
        return {p.value for p in cls}


class SplitJobStatus(str, Enum):
    """
    Split job status lifecycle.

    State machine:
    queued → analyzing → splitting → completed
               ↓           ↓
             failed      failed
    """
    QUEUED = "queued"
    ANALYZING = "analyzing"  # Analyzing document boundaries
    SPLITTING = "splitting"  # Creating child documents
    COMPLETED = "completed"
    FAILED = "failed"


class BoundaryConfidence(str, Enum):
    """
    Confidence level for document boundary detection.

    Indicates how confident the model is that a page is the start of a new document:
    - HIGH: Clear indicators (headers, document numbers, new formatting)
    - MEDIUM: Some indicators but not definitive
    - LOW: Uncertain, may need manual review
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RotationConfidence(str, Enum):
    """
    Confidence level for page rotation detection.

    Based on Tesseract OSD (Orientation and Script Detection):
    - HIGH: Tesseract confident in orientation
    - MEDIUM: Some uncertainty in detection
    - LOW: Unable to determine reliably
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class InboundEmailLogStatus(str, Enum):
    """
    Status values for inbound email processing log.

    State machine:
    received -> processed (success)
             -> rejected_* (validation failed)
             -> failed (processing error)
    """
    RECEIVED = "received"
    PROCESSED = "processed"
    REJECTED_SENDER = "rejected_sender"
    REJECTED_NO_CREDITS = "rejected_no_credits"
    REJECTED_NO_ATTACHMENTS = "rejected_no_attachments"
    REJECTED_INACTIVE = "rejected_inactive"
    FAILED = "failed"