"""Document and DocumentPage models."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Document(Base):
    """Document model - represents uploaded files."""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    file_path = Column(Text, nullable=False)  # S3 key or local path
    status = Column(
        String(50), nullable=False, default="uploaded"
    )  # uploaded, processing, ready_for_extraction, completed, failed
    page_count = Column(Integer, nullable=True)  # for PDFs
    document_metadata = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    extraction_jobs = relationship(
        "ExtractionJob", back_populates="document", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_documents_status", "status"),
        Index("idx_documents_created_at", "created_at"),
    )


class DocumentPage(Base):
    """DocumentPage model - represents individual pages from PDFs."""

    __tablename__ = "document_pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    image_path = Column(Text, nullable=False)  # S3 key or local path
    status = Column(String(50), nullable=False, default="pending")  # pending, ready, processed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="pages")
    extraction_results = relationship(
        "ExtractionResult", back_populates="document_page", cascade="all, delete-orphan"
    )

    # Indexes and constraints
    __table_args__ = (
        Index("idx_document_pages_document_id", "document_id"),
        Index("idx_document_pages_unique", "document_id", "page_number", unique=True),
    )
