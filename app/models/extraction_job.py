"""ExtractionJob model."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Index, Float, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
import uuid

from app.database import Base
from app.models.enums import JobSource, SplitMode, ExtractionMode


class ExtractionJob(Base):
    """ExtractionJob model - represents a document extraction task."""

    __tablename__ = "extraction_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    schema_definition_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schema_definitions.id", ondelete="SET NULL"),
        nullable=True
    )  # Reference to saved schema (if used), NULL if custom schema
    extraction_schema = Column(JSONB, nullable=False)  # The actual schema used (resolved)
    custom_prompt = Column(Text, nullable=True)
    model_provider = Column(String(50), nullable=False)  # google, openai
    model_name = Column(String(100), nullable=False)
    processing_mode = Column(
        String(50), nullable=False, default="batch"
    )  # DEPRECATED: Use split_mode + extraction_mode instead

    # New granular mode fields (replace processing_mode)
    split_mode = Column(
        String(20), nullable=False, default="batch"
    )  # per_page, batch, auto - how pages are grouped
    extraction_mode = Column(
        String(20), nullable=False, default="vllm"
    )  # vllm, markdown - how extraction is performed

    # Link to parent split job when using auto split mode
    parent_split_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("split_jobs.id", ondelete="SET NULL"),
        nullable=True
    )

    # Link to parent extraction job for child jobs created during auto-split
    # This enables tracking child job completion to update parent job status
    parent_extraction_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("extraction_jobs.id", ondelete="SET NULL"),
        nullable=True
    )

    enable_thinking = Column(Boolean, nullable=False, default=False)  # Enable AI thinking mode
    thinking_budget = Column(Integer, nullable=False, default=0)  # Token budget for thinking (0=disabled)

    # Markdown pipeline fields
    markdown_converter = Column(String(50), nullable=True)  # Converter used (gemini_vision, gpt4v)
    markdown_converter_model = Column(String(100), nullable=True)  # Model used for markdown conversion step
    markdown_format = Column(String(50), nullable=True)  # Format style (standard, table_heavy, layout_preserved)

    status = Column(
        String(50), nullable=False, default="queued"
    )  # queued, processing, completed, failed
    celery_task_id = Column(String(255), nullable=True)  # Celery task ID for tracking
    callback_url = Column(String(1024), nullable=True)  # Optional webhook callback URL
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Credit tracking
    credits_cost = Column(Integer, nullable=True)  # Number of credits consumed (page_count)
    credits_deducted = Column(Boolean, nullable=False, default=False)  # Deduction completed flag
    credit_transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("credit_transactions.id", ondelete="SET NULL"),
        nullable=True
    )

    # HITL (Human-in-the-Loop) tracking
    confidence_score = Column(Float, nullable=True)  # AI confidence score (0.0-1.0)

    # Job source tracking
    source = Column(String(20), nullable=False, default="api")  # webui or api

    # Cost tracking (immutable at completion)
    estimated_cost_usd = Column(Numeric(10, 6), nullable=True)  # Total estimated cost in USD
    pricing_snapshot = Column(JSONB, nullable=True)  # Pricing details at time of calculation

    # LlamaExtract-specific fields
    llamaextract_mode = Column(String(20), nullable=True)  # standard or premium
    llamaextract_target = Column(String(20), nullable=True)  # per_doc or per_page
    llamaextract_job_id = Column(String(100), nullable=True)  # External job ID for tracking

    # Relationships
    document = relationship("Document", back_populates="extraction_jobs")
    schema_definition = relationship("SchemaDefinition", backref="extraction_jobs")
    extraction_results = relationship(
        "ExtractionResult", back_populates="extraction_job", cascade="all, delete-orphan"
    )
    credit_transaction = relationship("CreditTransaction")
    review_request = relationship(
        "ReviewRequest",
        back_populates="extraction_job",
        uselist=False,
        cascade="all, delete-orphan"
    )
    parent_split_job = relationship("SplitJob", foreign_keys=[parent_split_job_id])
    parent_extraction_job = relationship(
        "ExtractionJob",
        remote_side=[id],
        foreign_keys=[parent_extraction_job_id],
        backref="child_extraction_jobs"
    )

    # Indexes
    __table_args__ = (
        Index("idx_extraction_jobs_tenant_id", "tenant_id"),
        Index("idx_extraction_jobs_document_id", "document_id"),
        Index("idx_extraction_jobs_schema_definition_id", "schema_definition_id"),
        Index("idx_extraction_jobs_status", "status"),
        Index("idx_extraction_jobs_celery_task_id", "celery_task_id"),
        Index("idx_extraction_jobs_source", "source"),
        Index("idx_extraction_jobs_parent_split_job_id", "parent_split_job_id"),
        Index("idx_extraction_jobs_split_mode", "split_mode"),
        Index("idx_extraction_jobs_extraction_mode", "extraction_mode"),
        Index("idx_extraction_jobs_parent_extraction_job_id", "parent_extraction_job_id"),
    )

    @validates('source')
    def validate_source(self, key, value):
        """Validate source field against JobSource enum."""
        if isinstance(value, JobSource):
            return value.value
        if value not in [s.value for s in JobSource]:
            raise ValueError(f"Invalid source: {value}. Must be one of: {[s.value for s in JobSource]}")
        return value

    @validates('split_mode')
    def validate_split_mode(self, key, value):
        """Validate split_mode field against SplitMode enum."""
        if isinstance(value, SplitMode):
            return value.value
        if value not in [m.value for m in SplitMode]:
            raise ValueError(f"Invalid split_mode: {value}. Must be one of: {[m.value for m in SplitMode]}")
        return value

    @validates('extraction_mode')
    def validate_extraction_mode(self, key, value):
        """Validate extraction_mode field against ExtractionMode enum."""
        if isinstance(value, ExtractionMode):
            return value.value
        if value not in [m.value for m in ExtractionMode]:
            raise ValueError(f"Invalid extraction_mode: {value}. Must be one of: {[m.value for m in ExtractionMode]}")
        return value
