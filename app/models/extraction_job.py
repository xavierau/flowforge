"""ExtractionJob model."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class ExtractionJob(Base):
    """ExtractionJob model - represents a document extraction task."""

    __tablename__ = "extraction_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    extraction_schema = Column(JSONB, nullable=False)
    custom_prompt = Column(Text, nullable=True)
    model_provider = Column(String(50), nullable=False)  # google, openai
    model_name = Column(String(100), nullable=False)
    processing_mode = Column(
        String(50), nullable=False, default="batch"
    )  # batch (all pages in one call) or per_page (individual page processing)
    status = Column(
        String(50), nullable=False, default="queued"
    )  # queued, processing, completed, failed
    celery_task_id = Column(String(255), nullable=True)  # Celery task ID for tracking
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="extraction_jobs")
    extraction_results = relationship(
        "ExtractionResult", back_populates="extraction_job", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_extraction_jobs_document_id", "document_id"),
        Index("idx_extraction_jobs_status", "status"),
        Index("idx_extraction_jobs_celery_task_id", "celery_task_id"),
    )
