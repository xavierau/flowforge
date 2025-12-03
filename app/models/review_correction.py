"""ReviewCorrection model for storing human corrections."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
import uuid

from app.database import Base
from app.models.enums import CorrectionType


class ReviewCorrection(Base):
    """
    ReviewCorrection model - represents a field-level correction made during human review.

    Each correction captures:
    - Which field was corrected (JSONPath)
    - Original AI-extracted value
    - Human-corrected value
    - Type of correction
    - Notes explaining the correction

    Used for:
    1. Immediate correction of extraction results
    2. Long-term analysis of AI accuracy
    3. Future: Active learning and model improvement
    """

    __tablename__ = "review_corrections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("review_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    extraction_result_id = Column(
        UUID(as_uuid=True),
        ForeignKey("extraction_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    corrected_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Field correction details
    field_path = Column(
        String(500),
        nullable=False,
        index=True
    )  # JSONPath (e.g., "invoice.total", "invoice.line_items[0].amount")
    original_value = Column(JSONB, nullable=True)  # Original AI-extracted value
    corrected_value = Column(JSONB, nullable=True)  # Human-corrected value
    correction_type = Column(
        String(50),
        nullable=False,
        default=CorrectionType.VALUE_CHANGE.value
    )
    correction_notes = Column(Text, nullable=True)  # Explanation from reviewer

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    review_request = relationship("ReviewRequest", back_populates="corrections")
    extraction_result = relationship("ExtractionResult")
    corrected_by = relationship("User", foreign_keys=[corrected_by_user_id])

    # Indexes
    __table_args__ = (
        # Find corrections by field path (for analytics)
        Index("idx_review_corrections_field_path", "field_path"),
        # Find all corrections for a review
        Index("idx_review_corrections_review_id", "review_request_id"),
        # Find all corrections by user (for reviewer metrics)
        Index("idx_review_corrections_user_id", "corrected_by_user_id"),
    )

    @validates("correction_type")
    def validate_correction_type(self, key, value):
        """Validate correction type using enum."""
        if isinstance(value, CorrectionType):
            return value.value
        if value not in [c.value for c in CorrectionType]:
            raise ValueError(f"Invalid correction_type: {value}")
        return value

    def __repr__(self):
        return (
            f"<ReviewCorrection(id={self.id}, field_path={self.field_path}, "
            f"type={self.correction_type})>"
        )
