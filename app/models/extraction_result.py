"""ExtractionResult model."""

from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class ExtractionResult(Base):
    """ExtractionResult model - stores extracted JSON data."""

    __tablename__ = "extraction_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extraction_job_id = Column(
        UUID(as_uuid=True), ForeignKey("extraction_jobs.id", ondelete="CASCADE"), nullable=False
    )
    document_page_id = Column(
        UUID(as_uuid=True), ForeignKey("document_pages.id", ondelete="CASCADE"), nullable=True
    )
    extracted_data = Column(JSONB, nullable=False)
    confidence_score = Column(Float, nullable=True)
    model_used = Column(String(100), nullable=False)
    input_tokens = Column(Integer, nullable=True)  # Prompt tokens (image + text)
    output_tokens = Column(Integer, nullable=True)  # Completion/candidates tokens
    tokens_used = Column(Integer, nullable=True)  # Total tokens (input + output)
    processing_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    extraction_job = relationship("ExtractionJob", back_populates="extraction_results")
    document_page = relationship("DocumentPage", back_populates="extraction_results")

    # Indexes
    __table_args__ = (
        Index("idx_extraction_results_job_id", "extraction_job_id"),
        Index("idx_extraction_results_extracted_data", "extracted_data", postgresql_using="gin"),
        Index(
            "idx_extraction_results_unique",
            "extraction_job_id",
            "document_page_id",
            unique=True,
        ),
    )
