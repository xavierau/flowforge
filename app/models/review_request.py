"""ReviewRequest model for Human-in-the-Loop review system."""

from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
import uuid

from app.database import Base
from app.models.enums import ReviewRequestStatus, ReviewPriority


class ReviewRequest(Base):
    """
    ReviewRequest model - represents a human review request for an extraction job.

    Lifecycle:
    1. Created when extraction confidence is below threshold
    2. Assigned to a reviewer (status: assigned)
    3. Reviewer starts review (status: in_review)
    4. Reviewer submits corrections (status: completed)
    5. Can be cancelled or escalated if SLA breached
    """

    __tablename__ = "review_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    extraction_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("extraction_jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One review per extraction job
        index=True
    )
    assigned_to_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Status and priority
    status = Column(
        String(50),
        nullable=False,
        default=ReviewRequestStatus.PENDING.value,
        index=True
    )
    priority = Column(
        String(50),
        nullable=False,
        default=ReviewPriority.NORMAL.value,
        index=True
    )

    # Metadata
    confidence_score = Column(Float, nullable=False)  # Original AI confidence (0.0-1.0)
    trigger_reason = Column(String(255), nullable=True)  # "low_confidence", "manual_request", etc.
    review_notes = Column(Text, nullable=True)  # Notes from reviewer

    # Conductor integration (optional - only populated when workflow-initiated)
    conductor_task_id = Column(
        String(255),
        nullable=True,
        index=True
    )  # Conductor HUMAN task ID
    conductor_workflow_id = Column(
        String(255),
        nullable=True,
        index=True
    )  # Conductor workflow execution ID

    # SLA tracking
    sla_deadline = Column(DateTime, nullable=False, index=True)  # Calculated based on priority
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    assigned_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="review_requests")
    extraction_job = relationship(
        "ExtractionJob",
        back_populates="review_request"
    )
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])
    corrections = relationship(
        "ReviewCorrection",
        back_populates="review_request",
        cascade="all, delete-orphan"
    )

    # Indexes for performance
    __table_args__ = (
        # Critical index for queue queries (tenant + status + priority + created_at)
        Index(
            "idx_review_queue",
            "tenant_id",
            "status",
            "priority",
            "created_at"
        ),
        # SLA monitoring (find breached reviews)
        Index("idx_review_sla_deadline", "sla_deadline"),
        # Find reviews by assignee
        Index("idx_review_assigned_to", "assigned_to_user_id", "status"),
    )

    @validates("status")
    def validate_status(self, key, value):
        """Validate status transitions using enum."""
        if isinstance(value, ReviewRequestStatus):
            return value.value
        if value not in [s.value for s in ReviewRequestStatus]:
            raise ValueError(f"Invalid status: {value}")
        return value

    @validates("priority")
    def validate_priority(self, key, value):
        """Validate priority using enum."""
        if isinstance(value, ReviewPriority):
            return value.value
        if value not in [p.value for p in ReviewPriority]:
            raise ValueError(f"Invalid priority: {value}")
        return value

    @classmethod
    def calculate_sla_deadline(cls, priority: ReviewPriority) -> datetime:
        """
        Calculate SLA deadline based on priority.

        Returns:
            datetime: Deadline timestamp
        """
        sla_hours = {
            ReviewPriority.CRITICAL: 1,
            ReviewPriority.HIGH: 2,
            ReviewPriority.NORMAL: 4,
            ReviewPriority.LOW: 8,
        }
        hours = sla_hours.get(priority, 4)
        return datetime.utcnow() + timedelta(hours=hours)

    def is_sla_breached(self) -> bool:
        """Check if SLA deadline has been breached."""
        return (
            self.status not in [
                ReviewRequestStatus.COMPLETED.value,
                ReviewRequestStatus.CANCELLED.value
            ]
            and datetime.utcnow() > self.sla_deadline
        )

    def __repr__(self):
        return (
            f"<ReviewRequest(id={self.id}, job_id={self.extraction_job_id}, "
            f"status={self.status}, priority={self.priority})>"
        )
