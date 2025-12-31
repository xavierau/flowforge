"""SplitJob and SplitResult models for document splitting feature."""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
import uuid

from app.database import Base
from app.models.enums import SplitJobStatus, BoundaryConfidence, RotationConfidence


class SplitJob(Base):
    """SplitJob model - represents a document splitting task."""

    __tablename__ = "split_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Status tracking
    status = Column(String(50), nullable=False, default=SplitJobStatus.QUEUED.value)

    # Configuration
    apply_rotation = Column(Boolean, nullable=False, default=True)
    dspy_model = Column(String(100), nullable=True)  # Model used for analysis

    # Statistics
    pages_analyzed = Column(Integer, nullable=False, default=0)
    documents_created = Column(Integer, nullable=False, default=0)
    pages_rotated = Column(Integer, nullable=False, default=0)

    # Token tracking
    total_input_tokens = Column(Integer, nullable=False, default=0)
    total_output_tokens = Column(Integer, nullable=False, default=0)

    # Error handling
    error_message = Column(Text, nullable=True)

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    tenant = relationship("Tenant")
    source_document = relationship(
        "Document",
        foreign_keys=[source_document_id],
        backref="split_jobs_as_source",
    )
    split_results = relationship(
        "SplitResult",
        back_populates="split_job",
        cascade="all, delete-orphan",
    )
    child_documents = relationship(
        "Document",
        foreign_keys="Document.split_job_id",
        backref="originating_split_job",
    )

    # Indexes
    __table_args__ = (
        Index("idx_split_jobs_tenant_id", "tenant_id"),
        Index("idx_split_jobs_source_document_id", "source_document_id"),
        Index("idx_split_jobs_status", "status"),
        Index("idx_split_jobs_created_at", "created_at"),
    )

    @validates("status")
    def validate_status(self, key, value):
        """Validate status field against SplitJobStatus enum."""
        if isinstance(value, SplitJobStatus):
            return value.value
        if value not in [s.value for s in SplitJobStatus]:
            raise ValueError(
                f"Invalid status: {value}. Must be one of: {[s.value for s in SplitJobStatus]}"
            )
        return value


class SplitResult(Base):
    """SplitResult model - represents analysis result for a single page."""

    __tablename__ = "split_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    split_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("split_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_page_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_number = Column(Integer, nullable=False)

    # Boundary detection (order matters for LLM autoregression - reasoning first!)
    boundary_reason = Column(Text, nullable=True)  # Reasoning for the decision
    detected_document_type = Column(
        String(100), nullable=True
    )  # What type of document detected
    is_starting_page = Column(Boolean, nullable=False, default=False)
    boundary_confidence = Column(
        String(20), nullable=True
    )  # Uses BoundaryConfidence enum

    # Rotation detection
    rotation_needed = Column(
        Integer, nullable=False, default=0
    )  # 0, 90, 180, 270 degrees
    rotation_confidence = Column(
        String(20), nullable=True
    )  # Uses RotationConfidence enum
    rotation_method = Column(
        String(50), nullable=True
    )  # "tesseract_osd" or "none"

    # Token tracking
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)

    # Child document reference (which child doc this page ended up in)
    child_document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    split_job = relationship("SplitJob", back_populates="split_results")
    document_page = relationship("DocumentPage")
    child_document = relationship(
        "Document",
        foreign_keys=[child_document_id],
    )

    # Indexes
    __table_args__ = (
        Index("idx_split_results_split_job_id", "split_job_id"),
        Index("idx_split_results_document_page_id", "document_page_id"),
        Index("idx_split_results_child_document_id", "child_document_id"),
        Index(
            "idx_split_results_job_page",
            "split_job_id",
            "page_number",
            unique=True,
        ),
    )

    @validates("boundary_confidence")
    def validate_boundary_confidence(self, key, value):
        """Validate boundary_confidence field against BoundaryConfidence enum."""
        if value is None:
            return value
        if isinstance(value, BoundaryConfidence):
            return value.value
        if value not in [c.value for c in BoundaryConfidence]:
            raise ValueError(
                f"Invalid boundary_confidence: {value}. Must be one of: {[c.value for c in BoundaryConfidence]}"
            )
        return value

    @validates("rotation_confidence")
    def validate_rotation_confidence(self, key, value):
        """Validate rotation_confidence field against RotationConfidence enum."""
        if value is None:
            return value
        if isinstance(value, RotationConfidence):
            return value.value
        if value not in [c.value for c in RotationConfidence]:
            raise ValueError(
                f"Invalid rotation_confidence: {value}. Must be one of: {[c.value for c in RotationConfidence]}"
            )
        return value

    @validates("rotation_needed")
    def validate_rotation_needed(self, key, value):
        """Validate rotation_needed is a valid rotation angle."""
        valid_rotations = [0, 90, 180, 270]
        if value not in valid_rotations:
            raise ValueError(
                f"Invalid rotation_needed: {value}. Must be one of: {valid_rotations}"
            )
        return value
