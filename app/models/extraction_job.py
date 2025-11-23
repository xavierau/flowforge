"""ExtractionJob model."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


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
    )  # batch (all pages in one call) or per_page (individual page processing) or markdown (vision → markdown → JSON)
    enable_thinking = Column(Boolean, nullable=False, default=False)  # Enable AI thinking mode
    thinking_budget = Column(Integer, nullable=False, default=0)  # Token budget for thinking (0=disabled)

    # Markdown pipeline fields
    markdown_converter = Column(String(50), nullable=True)  # Converter used (gemini_vision, gpt4v)
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

    # Relationships
    document = relationship("Document", back_populates="extraction_jobs")
    schema_definition = relationship("SchemaDefinition", backref="extraction_jobs")
    extraction_results = relationship(
        "ExtractionResult", back_populates="extraction_job", cascade="all, delete-orphan"
    )
    credit_transaction = relationship("CreditTransaction")

    # Indexes
    __table_args__ = (
        Index("idx_extraction_jobs_tenant_id", "tenant_id"),
        Index("idx_extraction_jobs_document_id", "document_id"),
        Index("idx_extraction_jobs_schema_definition_id", "schema_definition_id"),
        Index("idx_extraction_jobs_status", "status"),
        Index("idx_extraction_jobs_celery_task_id", "celery_task_id"),
    )
