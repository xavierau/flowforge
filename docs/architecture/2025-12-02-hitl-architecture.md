# Human-in-the-Loop (HITL) Service Architecture

**Document Version:** 1.0
**Created:** 2025-12-02
**Status:** Design Complete - Ready for Implementation
**Author:** Solution Architect

---

## Executive Summary

This document provides a comprehensive technical design for implementing a Human-in-the-Loop (HITL) review system for the AI Document Processing platform. The HITL service enables human reviewers to validate, correct, and improve AI-extracted data, creating a feedback loop that enhances extraction accuracy over time.

### Key Architectural Decisions

1. **Conductor HUMAN Task Integration**: Leverage Netflix Conductor's built-in HUMAN task type for workflow orchestration
2. **Dual Routing Mechanisms**: Support both threshold-based auto-routing and manual review requests
3. **Multi-Tenant Queue Management**: Tenant-isolated review queues with role-based access control
4. **Correction Feedback Loop**: Store human corrections to improve future extraction accuracy
5. **SLA Tracking**: Monitor review completion times with escalation policies
6. **Confidence Scoring**: Populate VLLM confidence scores to enable intelligent routing

### Integration Points

- **Existing Models**: ExtractionJob, ExtractionResult (confidence_score field)
- **Conductor Workflows**: Extend workflow builder with HUMAN task node type
- **VLLM Service**: Add confidence score calculation to all providers
- **Credit System**: Track review costs separately from extraction costs
- **API Layer**: New `/reviews` endpoints for review queue management

---

## 1. Database Schema Design

### 1.1 New Tables

#### ReviewRequest Table
Tracks human review requests for extraction jobs.

```python
# app/models/review_request.py
"""ReviewRequest model for HITL workflow."""

from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, ForeignKey, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
import uuid

from app.database import Base
from app.models.enums import ReviewRequestStatus, ReviewPriority


class ReviewRequest(Base):
    """
    ReviewRequest model - represents a human review request for an extraction job.

    Lifecycle:
    pending → assigned → in_review → completed
                ↓            ↓
            cancelled    escalated
    """

    __tablename__ = "review_requests"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
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
        unique=True,  # One review request per extraction job
        index=True
    )

    # Review Routing Information
    trigger_reason = Column(String(100), nullable=False)  # "low_confidence", "manual_request", "validation_error"
    confidence_score = Column(Float, nullable=True)  # Original AI confidence score (0.0-1.0)
    priority = Column(String(50), nullable=False, default=ReviewPriority.NORMAL.value)  # low, normal, high, critical

    # Assignment Information
    status = Column(
        String(50),
        nullable=False,
        default=ReviewRequestStatus.PENDING.value,
        index=True
    )
    assigned_to_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    assigned_at = Column(DateTime, nullable=True)

    # SLA Tracking
    sla_minutes = Column(Integer, nullable=False, default=240)  # 4 hours default
    sla_deadline = Column(DateTime, nullable=True, index=True)  # Calculated: created_at + sla_minutes
    escalated = Column(Boolean, nullable=False, default=False)
    escalated_at = Column(DateTime, nullable=True)
    escalated_to_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Review Completion
    completed_at = Column(DateTime, nullable=True)
    review_time_minutes = Column(Integer, nullable=True)  # Actual time taken

    # Metadata
    metadata = Column(JSONB, nullable=False, default=dict)  # Additional context
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="review_requests")
    extraction_job = relationship("ExtractionJob", back_populates="review_request")
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id], backref="assigned_reviews")
    escalated_to = relationship("User", foreign_keys=[escalated_to_user_id], backref="escalated_reviews")
    corrections = relationship("ReviewCorrection", back_populates="review_request", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_review_requests_tenant_id", "tenant_id"),
        Index("idx_review_requests_status", "status"),
        Index("idx_review_requests_assigned_to", "assigned_to_user_id"),
        Index("idx_review_requests_sla_deadline", "sla_deadline"),
        Index("idx_review_requests_priority", "priority"),
        Index("idx_review_requests_created_at", "created_at"),
        # Composite index for queue queries
        Index("idx_review_queue", "tenant_id", "status", "priority", "created_at"),
    )

    @validates("status")
    def validate_status(self, key, value):
        """Validate review request status is valid enum value."""
        if isinstance(value, ReviewRequestStatus):
            return value.value
        if value not in [s.value for s in ReviewRequestStatus]:
            raise ValueError(f"Invalid review request status: {value}")
        return value

    @validates("priority")
    def validate_priority(self, key, value):
        """Validate priority is valid enum value."""
        if isinstance(value, ReviewPriority):
            return value.value
        if value not in [p.value for p in ReviewPriority]:
            raise ValueError(f"Invalid priority: {value}")
        return value

    @validates("confidence_score")
    def validate_confidence_score(self, key, value):
        """Validate confidence score is between 0 and 1."""
        if value is not None and (value < 0.0 or value > 1.0):
            raise ValueError(f"Confidence score must be between 0.0 and 1.0, got {value}")
        return value

    def __repr__(self):
        return f"<ReviewRequest(id={self.id}, job_id={self.extraction_job_id}, status={self.status})>"
```

#### ReviewCorrection Table
Stores human corrections to extraction results.

```python
# app/models/review_correction.py
"""ReviewCorrection model for tracking human corrections."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class ReviewCorrection(Base):
    """
    ReviewCorrection model - tracks individual field corrections made by reviewers.

    This data is used for:
    1. Immediate correction: Override AI-extracted data with human-verified values
    2. Training feedback: Identify patterns where AI extracts incorrectly
    3. Prompt tuning: Improve extraction prompts based on common errors
    4. Quality metrics: Track extraction accuracy per schema field
    """

    __tablename__ = "review_corrections"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
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

    # Correction Details
    field_path = Column(String(500), nullable=False)  # JSONPath to corrected field (e.g., "invoice.line_items[0].amount")
    original_value = Column(JSONB, nullable=True)  # AI-extracted value (can be null if field was missing)
    corrected_value = Column(JSONB, nullable=False)  # Human-corrected value
    correction_type = Column(String(50), nullable=False)  # "value_change", "field_addition", "field_removal"

    # Context
    corrected_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    correction_notes = Column(Text, nullable=True)  # Reviewer's explanation

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    review_request = relationship("ReviewRequest", back_populates="corrections")
    extraction_result = relationship("ExtractionResult", backref="corrections")
    corrected_by = relationship("User", backref="corrections_made")

    # Indexes
    __table_args__ = (
        Index("idx_review_corrections_review_request_id", "review_request_id"),
        Index("idx_review_corrections_field_path", "field_path"),
        Index("idx_review_corrections_correction_type", "correction_type"),
        Index("idx_review_corrections_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<ReviewCorrection(id={self.id}, field={self.field_path}, type={self.correction_type})>"
```

### 1.2 Enum Extensions

```python
# app/models/enums.py (additions)

class ReviewRequestStatus(str, Enum):
    """
    Review request lifecycle states.

    State machine:
    pending → assigned → in_review → completed
        ↓          ↓           ↓
    cancelled  escalated   escalated
    """
    PENDING = "pending"          # Waiting for assignment
    ASSIGNED = "assigned"        # Assigned to reviewer but not started
    IN_REVIEW = "in_review"     # Reviewer actively working on it
    COMPLETED = "completed"      # Review finished with corrections submitted
    CANCELLED = "cancelled"      # Review request cancelled (e.g., job failed)
    ESCALATED = "escalated"      # SLA breached, escalated to senior reviewer


class ReviewPriority(str, Enum):
    """Review request priority levels."""
    LOW = "low"            # Confidence 0.60-0.70
    NORMAL = "normal"      # Confidence 0.50-0.60
    HIGH = "high"          # Confidence 0.30-0.50
    CRITICAL = "critical"  # Confidence < 0.30 or validation errors


class CorrectionType(str, Enum):
    """Types of human corrections."""
    VALUE_CHANGE = "value_change"      # Existing field value corrected
    FIELD_ADDITION = "field_addition"  # Missing field added by human
    FIELD_REMOVAL = "field_removal"    # Incorrect field removed
    STRUCTURE_CHANGE = "structure_change"  # Schema structure modified
```

### 1.3 Model Modifications

#### ExtractionJob Model
Add relationship to ReviewRequest.

```python
# app/models/extraction_job.py (addition)

# Add to ExtractionJob class
review_request = relationship("ReviewRequest", back_populates="extraction_job", uselist=False)
```

#### Tenant Model
Add relationship to ReviewRequests.

```python
# app/models/tenant.py (addition)

# Add to Tenant class
review_requests = relationship("ReviewRequest", back_populates="tenant", cascade="all, delete-orphan")
```

### 1.4 Alembic Migration Script

```python
# alembic/versions/2025-12-02_add_hitl_tables.py
"""Add HITL review tables

Revision ID: a1b2c3d4e5f6
Revises: previous_revision_id
Create Date: 2025-12-02 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'a1b2c3d4e5f6'
down_revision = 'previous_revision_id'
branch_labels = None
depends_on = None


def upgrade():
    # Create review_requests table
    op.create_table(
        'review_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('extraction_job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('trigger_reason', sa.String(100), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('priority', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('assigned_to_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.Column('sla_minutes', sa.Integer(), nullable=False),
        sa.Column('sla_deadline', sa.DateTime(), nullable=True),
        sa.Column('escalated', sa.Boolean(), nullable=False),
        sa.Column('escalated_at', sa.DateTime(), nullable=True),
        sa.Column('escalated_to_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('review_time_minutes', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['extraction_job_id'], ['extraction_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_to_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['escalated_to_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('extraction_job_id')
    )

    # Create indexes for review_requests
    op.create_index('idx_review_requests_tenant_id', 'review_requests', ['tenant_id'])
    op.create_index('idx_review_requests_status', 'review_requests', ['status'])
    op.create_index('idx_review_requests_assigned_to', 'review_requests', ['assigned_to_user_id'])
    op.create_index('idx_review_requests_sla_deadline', 'review_requests', ['sla_deadline'])
    op.create_index('idx_review_requests_priority', 'review_requests', ['priority'])
    op.create_index('idx_review_requests_created_at', 'review_requests', ['created_at'])
    op.create_index('idx_review_queue', 'review_requests', ['tenant_id', 'status', 'priority', 'created_at'])

    # Create review_corrections table
    op.create_table(
        'review_corrections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('review_request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('extraction_result_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('field_path', sa.String(500), nullable=False),
        sa.Column('original_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('corrected_value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('correction_type', sa.String(50), nullable=False),
        sa.Column('corrected_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('correction_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['review_request_id'], ['review_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['extraction_result_id'], ['extraction_results.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['corrected_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for review_corrections
    op.create_index('idx_review_corrections_review_request_id', 'review_corrections', ['review_request_id'])
    op.create_index('idx_review_corrections_field_path', 'review_corrections', ['field_path'])
    op.create_index('idx_review_corrections_correction_type', 'review_corrections', ['correction_type'])
    op.create_index('idx_review_corrections_created_at', 'review_corrections', ['created_at'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_review_corrections_created_at', 'review_corrections')
    op.drop_index('idx_review_corrections_correction_type', 'review_corrections')
    op.drop_index('idx_review_corrections_field_path', 'review_corrections')
    op.drop_index('idx_review_corrections_review_request_id', 'review_corrections')

    op.drop_index('idx_review_queue', 'review_requests')
    op.drop_index('idx_review_requests_created_at', 'review_requests')
    op.drop_index('idx_review_requests_priority', 'review_requests')
    op.drop_index('idx_review_requests_sla_deadline', 'review_requests')
    op.drop_index('idx_review_requests_assigned_to', 'review_requests')
    op.drop_index('idx_review_requests_status', 'review_requests')
    op.drop_index('idx_review_requests_tenant_id', 'review_requests')

    # Drop tables
    op.drop_table('review_corrections')
    op.drop_table('review_requests')
```

---

## 2. Service Layer Design

### 2.1 HITLService

```python
# app/services/hitl_service.py
"""
HITL (Human-in-the-Loop) Service

Handles all human review request lifecycle operations:
- Creating review requests (threshold-based or manual)
- Managing review queue
- Processing corrections
- Triggering re-extraction with human feedback
- Tracking accuracy improvements
"""

from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException
import logging

from app.models.review_request import ReviewRequest
from app.models.review_correction import ReviewCorrection
from app.models.extraction_job import ExtractionJob
from app.models.extraction_result import ExtractionResult
from app.models.user import User
from app.models.enums import (
    ReviewRequestStatus,
    ReviewPriority,
    CorrectionType,
    JobStatus
)

logger = logging.getLogger(__name__)


class HITLService:
    """
    Application service for Human-in-the-Loop review workflow.

    SOLID Principles:
    - SRP: Single responsibility - HITL review lifecycle management
    - OCP: Open for extension (subclass for custom review policies)
    - DIP: Depends on abstractions (database session, not concrete implementations)

    Clean Architecture:
    - Application layer service
    - Uses domain models (ReviewRequest, ReviewCorrection)
    - Called by API layer (controllers)
    - Calls infrastructure layer (database, Conductor client)
    """

    # Confidence threshold configuration
    CONFIDENCE_THRESHOLDS = {
        ReviewPriority.CRITICAL: 0.30,  # < 0.30 = critical priority
        ReviewPriority.HIGH: 0.50,      # 0.30-0.50 = high priority
        ReviewPriority.NORMAL: 0.60,    # 0.50-0.60 = normal priority
        ReviewPriority.LOW: 0.70,       # 0.60-0.70 = low priority
        # > 0.70 = no review needed (auto-approve)
    }

    # SLA configuration by priority
    SLA_MINUTES = {
        ReviewPriority.CRITICAL: 60,   # 1 hour
        ReviewPriority.HIGH: 120,      # 2 hours
        ReviewPriority.NORMAL: 240,    # 4 hours
        ReviewPriority.LOW: 480,       # 8 hours
    }

    def __init__(self, db: Session):
        """
        Initialize HITL service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def should_request_review(
        self,
        confidence_score: float,
        validation_errors: List[str],
        manual_request: bool = False
    ) -> Tuple[bool, Optional[str], Optional[ReviewPriority]]:
        """
        Determine if extraction requires human review.

        Decision logic:
        1. Manual request → always review (NORMAL priority)
        2. Validation errors → always review (HIGH priority)
        3. Low confidence → review based on threshold
        4. High confidence (>0.70) → auto-approve

        Args:
            confidence_score: AI confidence score (0.0-1.0)
            validation_errors: Schema validation errors
            manual_request: User manually requested review

        Returns:
            Tuple of (needs_review, trigger_reason, priority)
        """
        # Manual request always requires review
        if manual_request:
            return True, "manual_request", ReviewPriority.NORMAL

        # Validation errors always require review
        if validation_errors:
            return True, "validation_error", ReviewPriority.HIGH

        # Check confidence thresholds
        if confidence_score < self.CONFIDENCE_THRESHOLDS[ReviewPriority.CRITICAL]:
            return True, "low_confidence", ReviewPriority.CRITICAL
        elif confidence_score < self.CONFIDENCE_THRESHOLDS[ReviewPriority.HIGH]:
            return True, "low_confidence", ReviewPriority.HIGH
        elif confidence_score < self.CONFIDENCE_THRESHOLDS[ReviewPriority.NORMAL]:
            return True, "low_confidence", ReviewPriority.NORMAL
        elif confidence_score < self.CONFIDENCE_THRESHOLDS[ReviewPriority.LOW]:
            return True, "low_confidence", ReviewPriority.LOW

        # High confidence - auto-approve
        return False, None, None

    def create_review_request(
        self,
        extraction_job_id: UUID,
        trigger_reason: str,
        confidence_score: Optional[float],
        priority: ReviewPriority,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ReviewRequest:
        """
        Create a new review request for an extraction job.

        Args:
            extraction_job_id: ExtractionJob UUID
            trigger_reason: Why review is needed ("low_confidence", "manual_request", "validation_error")
            confidence_score: AI confidence score
            priority: Review priority level
            metadata: Additional context

        Returns:
            Created ReviewRequest

        Raises:
            HTTPException(404): Extraction job not found
            HTTPException(400): Review request already exists for this job
        """
        # Get extraction job
        job = self.db.query(ExtractionJob).filter(
            ExtractionJob.id == extraction_job_id
        ).first()

        if not job:
            raise HTTPException(status_code=404, detail="Extraction job not found")

        # Check if review request already exists
        existing = self.db.query(ReviewRequest).filter(
            ReviewRequest.extraction_job_id == extraction_job_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Review request already exists for job {extraction_job_id}"
            )

        # Calculate SLA deadline
        sla_minutes = self.SLA_MINUTES[priority]
        sla_deadline = datetime.utcnow() + timedelta(minutes=sla_minutes)

        # Create review request
        review_request = ReviewRequest(
            tenant_id=job.tenant_id,
            extraction_job_id=extraction_job_id,
            trigger_reason=trigger_reason,
            confidence_score=confidence_score,
            priority=priority.value,
            status=ReviewRequestStatus.PENDING.value,
            sla_minutes=sla_minutes,
            sla_deadline=sla_deadline,
            metadata=metadata or {}
        )

        self.db.add(review_request)
        self.db.commit()
        self.db.refresh(review_request)

        logger.info(
            f"Created review request {review_request.id} for job {extraction_job_id}",
            extra={
                "review_request_id": str(review_request.id),
                "extraction_job_id": str(extraction_job_id),
                "priority": priority.value,
                "trigger_reason": trigger_reason,
                "sla_deadline": sla_deadline.isoformat()
            }
        )

        return review_request

    def get_review_queue(
        self,
        tenant_id: UUID,
        assignee_user_id: Optional[UUID] = None,
        status_filter: Optional[List[ReviewRequestStatus]] = None,
        priority_filter: Optional[List[ReviewPriority]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[ReviewRequest], int]:
        """
        Get review queue with filtering and pagination.

        Args:
            tenant_id: Tenant UUID (for isolation)
            assignee_user_id: Filter by assigned user (None = all unassigned)
            status_filter: Filter by status
            priority_filter: Filter by priority
            limit: Results per page
            offset: Pagination offset

        Returns:
            Tuple of (review_requests, total_count)
        """
        # Build base query with tenant isolation
        query = self.db.query(ReviewRequest).filter(
            ReviewRequest.tenant_id == tenant_id
        )

        # Filter by assignee
        if assignee_user_id is not None:
            query = query.filter(ReviewRequest.assigned_to_user_id == assignee_user_id)

        # Filter by status
        if status_filter:
            status_values = [s.value for s in status_filter]
            query = query.filter(ReviewRequest.status.in_(status_values))

        # Filter by priority
        if priority_filter:
            priority_values = [p.value for p in priority_filter]
            query = query.filter(ReviewRequest.priority.in_(priority_values))

        # Get total count
        total = query.count()

        # Get paginated results, ordered by priority (critical first) then created_at
        review_requests = (
            query
            .order_by(
                ReviewRequest.priority.desc(),  # CRITICAL, HIGH, NORMAL, LOW
                ReviewRequest.created_at.asc()   # Oldest first within same priority
            )
            .limit(limit)
            .offset(offset)
            .all()
        )

        return review_requests, total

    def assign_review(
        self,
        review_request_id: UUID,
        assignee_user_id: UUID,
        tenant_id: UUID
    ) -> ReviewRequest:
        """
        Assign a review request to a user.

        Args:
            review_request_id: ReviewRequest UUID
            assignee_user_id: User UUID to assign to
            tenant_id: Tenant UUID (for isolation)

        Returns:
            Updated ReviewRequest

        Raises:
            HTTPException(404): Review request not found
            HTTPException(400): Review request not in assignable state
        """
        # Get review request with tenant isolation
        review_request = self.db.query(ReviewRequest).filter(
            and_(
                ReviewRequest.id == review_request_id,
                ReviewRequest.tenant_id == tenant_id
            )
        ).first()

        if not review_request:
            raise HTTPException(status_code=404, detail="Review request not found")

        # Validate status (can only assign pending or escalated requests)
        if review_request.status not in [
            ReviewRequestStatus.PENDING.value,
            ReviewRequestStatus.ESCALATED.value
        ]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot assign review in status: {review_request.status}"
            )

        # Verify assignee exists and belongs to tenant
        assignee = self.db.query(User).filter(
            and_(
                User.id == assignee_user_id,
                User.tenant_id == tenant_id
            )
        ).first()

        if not assignee:
            raise HTTPException(status_code=404, detail="Assignee not found")

        # Assign review
        review_request.assigned_to_user_id = assignee_user_id
        review_request.assigned_at = datetime.utcnow()
        review_request.status = ReviewRequestStatus.ASSIGNED.value
        review_request.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(review_request)

        logger.info(
            f"Assigned review {review_request_id} to user {assignee_user_id}",
            extra={
                "review_request_id": str(review_request_id),
                "assignee_user_id": str(assignee_user_id)
            }
        )

        return review_request

    def start_review(
        self,
        review_request_id: UUID,
        user_id: UUID,
        tenant_id: UUID
    ) -> ReviewRequest:
        """
        Mark review as in-progress.

        Args:
            review_request_id: ReviewRequest UUID
            user_id: User starting the review
            tenant_id: Tenant UUID (for isolation)

        Returns:
            Updated ReviewRequest

        Raises:
            HTTPException(404): Review request not found
            HTTPException(403): User not assigned to this review
            HTTPException(400): Review not in correct state
        """
        # Get review request with tenant isolation
        review_request = self.db.query(ReviewRequest).filter(
            and_(
                ReviewRequest.id == review_request_id,
                ReviewRequest.tenant_id == tenant_id
            )
        ).first()

        if not review_request:
            raise HTTPException(status_code=404, detail="Review request not found")

        # Verify user is assigned to this review
        if review_request.assigned_to_user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="User not assigned to this review"
            )

        # Validate status
        if review_request.status != ReviewRequestStatus.ASSIGNED.value:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot start review in status: {review_request.status}"
            )

        # Start review
        review_request.status = ReviewRequestStatus.IN_REVIEW.value
        review_request.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(review_request)

        return review_request

    def submit_corrections(
        self,
        review_request_id: UUID,
        corrections: List[Dict[str, Any]],
        user_id: UUID,
        tenant_id: UUID
    ) -> Tuple[ReviewRequest, List[ReviewCorrection]]:
        """
        Submit human corrections for a review.

        Args:
            review_request_id: ReviewRequest UUID
            corrections: List of correction dicts with:
                - extraction_result_id: UUID
                - field_path: str (JSONPath)
                - original_value: Any (can be None)
                - corrected_value: Any
                - correction_type: str
                - correction_notes: str (optional)
            user_id: User submitting corrections
            tenant_id: Tenant UUID (for isolation)

        Returns:
            Tuple of (updated_review_request, created_corrections)

        Raises:
            HTTPException(404): Review request not found
            HTTPException(403): User not assigned to this review
            HTTPException(400): Invalid correction data
        """
        # Get review request with tenant isolation
        review_request = self.db.query(ReviewRequest).filter(
            and_(
                ReviewRequest.id == review_request_id,
                ReviewRequest.tenant_id == tenant_id
            )
        ).first()

        if not review_request:
            raise HTTPException(status_code=404, detail="Review request not found")

        # Verify user is assigned
        if review_request.assigned_to_user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="User not assigned to this review"
            )

        # Validate status
        if review_request.status != ReviewRequestStatus.IN_REVIEW.value:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot submit corrections in status: {review_request.status}"
            )

        # Create correction records
        created_corrections = []
        for corr_data in corrections:
            correction = ReviewCorrection(
                review_request_id=review_request_id,
                extraction_result_id=corr_data["extraction_result_id"],
                field_path=corr_data["field_path"],
                original_value=corr_data.get("original_value"),
                corrected_value=corr_data["corrected_value"],
                correction_type=corr_data["correction_type"],
                corrected_by_user_id=user_id,
                correction_notes=corr_data.get("correction_notes")
            )
            self.db.add(correction)
            created_corrections.append(correction)

        # Complete review request
        review_request.status = ReviewRequestStatus.COMPLETED.value
        review_request.completed_at = datetime.utcnow()

        # Calculate actual review time
        if review_request.assigned_at:
            review_time = (datetime.utcnow() - review_request.assigned_at).total_seconds() / 60
            review_request.review_time_minutes = int(review_time)

        review_request.updated_at = datetime.utcnow()

        self.db.commit()

        # Refresh all objects
        self.db.refresh(review_request)
        for correction in created_corrections:
            self.db.refresh(correction)

        logger.info(
            f"Submitted {len(created_corrections)} corrections for review {review_request_id}",
            extra={
                "review_request_id": str(review_request_id),
                "corrections_count": len(created_corrections),
                "user_id": str(user_id)
            }
        )

        return review_request, created_corrections

    def apply_corrections_to_result(
        self,
        extraction_result_id: UUID,
        corrections: List[ReviewCorrection]
    ) -> Dict[str, Any]:
        """
        Apply human corrections to extraction result data.

        This creates a new corrected version of the extracted data
        without modifying the original AI extraction.

        Args:
            extraction_result_id: ExtractionResult UUID
            corrections: List of ReviewCorrection objects

        Returns:
            Corrected extracted_data dict
        """
        # Get extraction result
        result = self.db.query(ExtractionResult).filter(
            ExtractionResult.id == extraction_result_id
        ).first()

        if not result:
            raise HTTPException(status_code=404, detail="Extraction result not found")

        # Start with original extracted data
        corrected_data = result.extracted_data.copy()

        # Apply each correction
        for correction in corrections:
            field_path = correction.field_path
            corrected_value = correction.corrected_value

            # Apply correction using JSONPath-like logic
            self._apply_field_correction(corrected_data, field_path, corrected_value)

        return corrected_data

    def _apply_field_correction(
        self,
        data: Dict[str, Any],
        field_path: str,
        corrected_value: Any
    ) -> None:
        """
        Apply a single field correction to data dict in-place.

        Args:
            data: Data dict to modify
            field_path: JSONPath to field (e.g., "invoice.line_items[0].amount")
            corrected_value: New value to set
        """
        # Simple JSONPath implementation (handles . and [index])
        # For production, consider using jsonpath-ng library
        parts = field_path.replace('[', '.').replace(']', '').split('.')

        # Navigate to parent of target field
        current = data
        for part in parts[:-1]:
            if part.isdigit():
                current = current[int(part)]
            else:
                current = current.setdefault(part, {})

        # Set the final value
        final_key = parts[-1]
        if final_key.isdigit():
            current[int(final_key)] = corrected_value
        else:
            current[final_key] = corrected_value

    def check_sla_breaches(self) -> List[ReviewRequest]:
        """
        Check for SLA breaches and escalate reviews.

        This should be called periodically (e.g., every 5 minutes via cron).

        Returns:
            List of escalated ReviewRequests
        """
        now = datetime.utcnow()

        # Find reviews past SLA deadline that haven't been escalated
        breached_reviews = self.db.query(ReviewRequest).filter(
            and_(
                ReviewRequest.sla_deadline < now,
                ReviewRequest.escalated == False,
                ReviewRequest.status.in_([
                    ReviewRequestStatus.PENDING.value,
                    ReviewRequestStatus.ASSIGNED.value,
                    ReviewRequestStatus.IN_REVIEW.value
                ])
            )
        ).all()

        escalated = []
        for review in breached_reviews:
            # Mark as escalated
            review.escalated = True
            review.escalated_at = now
            review.status = ReviewRequestStatus.ESCALATED.value
            review.updated_at = now

            # TODO: Implement escalation policy (e.g., reassign to senior reviewer)
            # For now, just mark as escalated

            escalated.append(review)

            logger.warning(
                f"SLA breach detected for review {review.id}",
                extra={
                    "review_request_id": str(review.id),
                    "sla_deadline": review.sla_deadline.isoformat(),
                    "created_at": review.created_at.isoformat(),
                    "priority": review.priority
                }
            )

        if escalated:
            self.db.commit()

        return escalated

    def get_accuracy_metrics(
        self,
        tenant_id: UUID,
        schema_definition_id: Optional[UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate accuracy metrics from human corrections.

        Metrics:
        - Total reviews completed
        - Average corrections per review
        - Most frequently corrected fields
        - Accuracy improvement trend

        Args:
            tenant_id: Tenant UUID
            schema_definition_id: Filter by schema (optional)
            date_from: Start date for metrics (optional)
            date_to: End date for metrics (optional)

        Returns:
            Dict with accuracy metrics
        """
        # Build base query
        query = self.db.query(ReviewRequest).filter(
            and_(
                ReviewRequest.tenant_id == tenant_id,
                ReviewRequest.status == ReviewRequestStatus.COMPLETED.value
            )
        )

        # Filter by schema
        if schema_definition_id:
            query = query.join(ExtractionJob).filter(
                ExtractionJob.schema_definition_id == schema_definition_id
            )

        # Filter by date range
        if date_from:
            query = query.filter(ReviewRequest.completed_at >= date_from)
        if date_to:
            query = query.filter(ReviewRequest.completed_at <= date_to)

        completed_reviews = query.all()

        # Calculate metrics
        total_reviews = len(completed_reviews)

        if total_reviews == 0:
            return {
                "total_reviews": 0,
                "average_corrections_per_review": 0.0,
                "most_corrected_fields": [],
                "accuracy_rate": 0.0
            }

        # Count corrections
        total_corrections = sum(len(r.corrections) for r in completed_reviews)
        avg_corrections = total_corrections / total_reviews

        # Find most frequently corrected fields
        field_correction_counts = {}
        for review in completed_reviews:
            for correction in review.corrections:
                field_path = correction.field_path
                field_correction_counts[field_path] = field_correction_counts.get(field_path, 0) + 1

        most_corrected = sorted(
            field_correction_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]  # Top 10

        # Calculate accuracy rate (1 - correction_rate)
        # If every field was correct, corrections = 0, accuracy = 100%
        # If every field was wrong, corrections = field_count, accuracy = 0%
        # Simplified: accuracy = 1 - (avg_corrections / expected_fields)
        # For now, use inverse of correction rate as proxy
        accuracy_rate = max(0.0, 1.0 - (avg_corrections / 10.0))  # Assume ~10 fields per schema

        return {
            "total_reviews": total_reviews,
            "average_corrections_per_review": round(avg_corrections, 2),
            "most_corrected_fields": [
                {"field_path": field, "correction_count": count}
                for field, count in most_corrected
            ],
            "accuracy_rate": round(accuracy_rate * 100, 2)  # Percentage
        }
```

### 2.2 Confidence Scoring in VLLM Service

```python
# app/services/vllm_service.py (modifications)

class GeminiVLLMProvider(VLLMProvider):
    """Google Gemini Vision provider."""

    async def extract(
        self,
        image_base64: str,
        schema: dict[str, Any],
        prompt: str,
        thinking_budget: int = 0,
    ) -> tuple[dict[str, Any], int, int, int, float]:  # ADD confidence_score to return
        """Extract using Google Gemini with structured output and confidence scoring."""
        start_time = time.time()

        # ... existing extraction logic ...

        # ADDITION: Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            response=response,
            extracted_data=extracted_data,
            schema=schema
        )

        processing_time = int((time.time() - start_time) * 1000)

        return extracted_data, input_tokens, output_tokens, processing_time, confidence_score

    def _calculate_confidence_score(
        self,
        response: Any,
        extracted_data: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> float:
        """
        Calculate confidence score for extraction.

        Factors:
        1. Schema coverage: What % of required fields were extracted?
        2. Data completeness: Are extracted values non-null and non-empty?
        3. Model confidence: If model provides logprobs, use them

        Args:
            response: Raw model response
            extracted_data: Extracted JSON data
            schema: JSON schema

        Returns:
            Confidence score between 0.0 and 1.0
        """
        scores = []

        # Factor 1: Schema coverage (required fields present)
        if "required" in schema and "properties" in schema:
            required_fields = schema["required"]
            present_count = sum(
                1 for field in required_fields
                if field in extracted_data and extracted_data[field] is not None
            )
            coverage_score = present_count / len(required_fields) if required_fields else 1.0
            scores.append(coverage_score)

        # Factor 2: Data completeness (non-empty values)
        if "properties" in schema:
            total_fields = len(schema["properties"])
            non_empty_count = sum(
                1 for field, value in extracted_data.items()
                if value is not None and value != "" and value != []
            )
            completeness_score = non_empty_count / total_fields if total_fields else 1.0
            scores.append(completeness_score)

        # Factor 3: Model confidence (if available)
        # Gemini doesn't provide per-token logprobs in structured output mode
        # For now, we'll rely on schema coverage and completeness
        # Future: Use safety_ratings or custom confidence metrics

        # Average all scores
        final_score = sum(scores) / len(scores) if scores else 0.5

        return round(final_score, 2)


class OpenAIVLLMProvider(VLLMProvider):
    """OpenAI GPT-4 Vision provider."""

    async def extract(
        self,
        image_base64: str,
        schema: dict[str, Any],
        prompt: str,
    ) -> tuple[dict[str, Any], int, int, int, float]:  # ADD confidence_score
        """Extract using OpenAI GPT-4V with confidence scoring."""
        start_time = time.time()

        # ... existing extraction logic ...

        # ADDITION: Calculate confidence score
        # OpenAI provides logprobs in response if requested
        confidence_score = self._calculate_confidence_score(
            response=response,
            extracted_data=extracted_data,
            schema=schema
        )

        processing_time = int((time.time() - start_time) * 1000)

        return extracted_data, input_tokens, output_tokens, processing_time, confidence_score

    def _calculate_confidence_score(
        self,
        response: Any,
        extracted_data: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> float:
        """Calculate confidence score (same logic as Gemini for now)."""
        # Same implementation as GeminiVLLMProvider._calculate_confidence_score
        # Future: Use OpenAI's logprobs if available
        scores = []

        if "required" in schema and "properties" in schema:
            required_fields = schema["required"]
            present_count = sum(
                1 for field in required_fields
                if field in extracted_data and extracted_data[field] is not None
            )
            coverage_score = present_count / len(required_fields) if required_fields else 1.0
            scores.append(coverage_score)

        if "properties" in schema:
            total_fields = len(schema["properties"])
            non_empty_count = sum(
                1 for field, value in extracted_data.items()
                if value is not None and value != "" and value != []
            )
            completeness_score = non_empty_count / total_fields if total_fields else 1.0
            scores.append(completeness_score)

        final_score = sum(scores) / len(scores) if scores else 0.5
        return round(final_score, 2)


class VLLMService:
    """High-level VLLM service for document extraction."""

    async def extract_from_image(
        self,
        image_base64: str,
        schema: dict[str, Any],
        custom_prompt: str = "",
        provider: str = "google",
        model: str = "gemini-pro-vision",
        thinking_budget: int = 0,
    ) -> dict[str, Any]:
        """
        Extract structured data from an image with confidence scoring.

        Returns dict with confidence_score field populated.
        """
        # ... existing validation ...

        # Extract data WITH confidence score
        extracted_data, input_tokens, output_tokens, processing_time_ms, confidence_score = (
            await vllm_provider.extract(
                image_base64=image_base64,
                schema=schema,
                prompt=custom_prompt,
                thinking_budget=thinking_budget,
            )
        )

        # ... existing validation ...

        return {
            "extracted_data": extracted_data,
            "is_valid": is_valid,
            "validation_errors": validation_errors,
            "confidence_score": confidence_score,  # NOW POPULATED
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "tokens_used": input_tokens + output_tokens,
            "processing_time_ms": processing_time_ms,
            "model_used": f"{provider}/{model}",
        }
```

---

## 3. Conductor HUMAN Task Integration

### 3.1 Conductor HUMAN Task Worker

```python
# app/orchestration/workers/human_review_worker.py
"""
Human Review Worker for Conductor HUMAN tasks.

This worker handles the lifecycle of HUMAN tasks in Conductor workflows:
1. Poll for HUMAN tasks from Conductor
2. Create ReviewRequest in our database
3. Wait for human completion (via API)
4. Update Conductor task with corrections
"""

from typing import Any, Dict, Optional
from conductor.client.worker.worker_task import WorkerTask
from conductor.client.worker.worker import Worker
from conductor.client.configuration import Configuration
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.hitl_service import HITLService
from app.models.enums import ReviewRequestStatus
from app.models.review_request import ReviewRequest
import logging

logger = logging.getLogger(__name__)


class HumanReviewWorker(Worker):
    """
    Conductor worker for HUMAN tasks.

    Conductor's HUMAN task type pauses workflow execution until
    external input is provided. This worker:
    1. Creates ReviewRequest when HUMAN task starts
    2. Monitors ReviewRequest status
    3. Completes Conductor task when review is done
    """

    def __init__(self, configuration: Configuration):
        """Initialize human review worker."""
        super().__init__(
            task_definition_name="HUMAN_REVIEW",
            configuration=configuration,
            domain=None,  # No specific domain
            poll_interval=10.0  # Poll every 10 seconds
        )

    def execute(self, task: WorkerTask) -> Dict[str, Any]:
        """
        Execute HUMAN task by creating a ReviewRequest.

        Input Parameters:
        - extraction_job_id: UUID of ExtractionJob
        - trigger_reason: Why review is needed
        - confidence_score: AI confidence
        - priority: Review priority

        Output:
        - review_request_id: UUID of created ReviewRequest
        - status: "pending_review"

        Args:
            task: Conductor task

        Returns:
            Task output dict
        """
        db = SessionLocal()
        try:
            # Get task input
            extraction_job_id = task.input_data.get("extraction_job_id")
            trigger_reason = task.input_data.get("trigger_reason", "manual_request")
            confidence_score = task.input_data.get("confidence_score")
            priority = task.input_data.get("priority", "normal")

            if not extraction_job_id:
                raise ValueError("Missing required input: extraction_job_id")

            # Create review request
            hitl_service = HITLService(db)
            review_request = hitl_service.create_review_request(
                extraction_job_id=extraction_job_id,
                trigger_reason=trigger_reason,
                confidence_score=confidence_score,
                priority=priority,
                metadata={
                    "conductor_task_id": task.task_id,
                    "conductor_workflow_id": task.workflow_instance_id
                }
            )

            logger.info(
                f"Created review request {review_request.id} for Conductor task {task.task_id}"
            )

            # Return task output
            # NOTE: Conductor HUMAN tasks are IN_PROGRESS until completed via API
            return {
                "review_request_id": str(review_request.id),
                "status": "pending_review",
                "sla_deadline": review_request.sla_deadline.isoformat()
            }

        except Exception as e:
            logger.error(f"Error in human review worker: {e}", exc_info=True)
            raise
        finally:
            db.close()
```

### 3.2 Conductor Task Completion Helper

```python
# app/services/conductor_hitl_service.py
"""
Service for completing Conductor HUMAN tasks when reviews finish.
"""

from typing import Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
import logging

from app.services.conductor_client import ConductorClient
from app.models.review_request import ReviewRequest
from app.models.review_correction import ReviewCorrection
from app.config import settings

logger = logging.getLogger(__name__)


class ConductorHITLService:
    """
    Service for integrating HITL with Conductor workflows.

    Handles completion of Conductor HUMAN tasks when reviews finish.
    """

    def __init__(self, db: Session):
        """Initialize service."""
        self.db = db
        self.conductor_client = ConductorClient(
            conductor_url=settings.conductor_url
        )

    async def complete_conductor_task(
        self,
        review_request: ReviewRequest,
        corrections: list[ReviewCorrection]
    ) -> bool:
        """
        Complete Conductor HUMAN task with review corrections.

        Args:
            review_request: Completed ReviewRequest
            corrections: List of ReviewCorrection objects

        Returns:
            True if Conductor task completed successfully
        """
        # Get Conductor task ID from review request metadata
        conductor_task_id = review_request.metadata.get("conductor_task_id")

        if not conductor_task_id:
            logger.warning(
                f"Review request {review_request.id} has no conductor_task_id in metadata"
            )
            return False

        try:
            # Build task output with corrections
            task_output = {
                "review_completed": True,
                "review_request_id": str(review_request.id),
                "corrections_count": len(corrections),
                "corrections": [
                    {
                        "field_path": c.field_path,
                        "original_value": c.original_value,
                        "corrected_value": c.corrected_value,
                        "correction_type": c.correction_type,
                        "notes": c.correction_notes
                    }
                    for c in corrections
                ]
            }

            # Complete Conductor task via API
            # POST /api/tasks with taskId, status=COMPLETED, output
            success = await self._update_conductor_task(
                task_id=conductor_task_id,
                status="COMPLETED",
                output_data=task_output
            )

            if success:
                logger.info(
                    f"Completed Conductor task {conductor_task_id} "
                    f"for review {review_request.id}"
                )

            return success

        except Exception as e:
            logger.error(
                f"Failed to complete Conductor task {conductor_task_id}: {e}",
                exc_info=True
            )
            return False

    async def _update_conductor_task(
        self,
        task_id: str,
        status: str,
        output_data: Dict[str, Any]
    ) -> bool:
        """
        Update Conductor task status via API.

        Args:
            task_id: Conductor task ID
            status: New status (COMPLETED, FAILED)
            output_data: Task output dict

        Returns:
            True if update succeeded
        """
        try:
            # Conductor API: POST /api/tasks
            url = f"{self.conductor_client.conductor_url}/api/tasks"
            payload = {
                "taskId": task_id,
                "status": status,
                "outputData": output_data
            }

            response = await self.conductor_client.client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code in (200, 204):
                return True
            else:
                logger.error(
                    f"Failed to update Conductor task {task_id}: "
                    f"{response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error updating Conductor task {task_id}: {e}")
            return False
```

### 3.3 Workflow Definition with HUMAN Task

```json
{
  "name": "document_extraction_with_review",
  "description": "Extract document data with optional human review",
  "version": 1,
  "tasks": [
    {
      "name": "extract_document",
      "taskReferenceName": "extract_ref",
      "inputParameters": {
        "document_id": "${workflow.input.document_id}",
        "schema": "${workflow.input.schema}",
        "provider": "${workflow.input.provider}"
      },
      "type": "SIMPLE"
    },
    {
      "name": "check_confidence",
      "taskReferenceName": "check_confidence_ref",
      "inputParameters": {
        "confidence_score": "${extract_ref.output.confidence_score}",
        "threshold": 0.70
      },
      "type": "SWITCH",
      "evaluatorType": "javascript",
      "expression": "$.check_confidence_ref.inputParameters.confidence_score < $.check_confidence_ref.inputParameters.threshold",
      "decisionCases": {
        "true": [
          {
            "name": "human_review",
            "taskReferenceName": "human_review_ref",
            "inputParameters": {
              "extraction_job_id": "${workflow.input.extraction_job_id}",
              "trigger_reason": "low_confidence",
              "confidence_score": "${extract_ref.output.confidence_score}",
              "priority": "normal"
            },
            "type": "HUMAN"
          }
        ]
      },
      "defaultCase": []
    },
    {
      "name": "finalize_extraction",
      "taskReferenceName": "finalize_ref",
      "inputParameters": {
        "extraction_result": "${extract_ref.output}",
        "review_corrections": "${human_review_ref.output.corrections}"
      },
      "type": "SIMPLE"
    }
  ],
  "schemaVersion": 2
}
```

---

## 4. API Endpoints

### 4.1 Pydantic Schemas

```python
# app/schemas/review.py
"""Pydantic schemas for HITL review API."""

from typing import Optional, List, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, validator
from uuid import UUID

from app.models.enums import ReviewRequestStatus, ReviewPriority, CorrectionType


class ReviewRequestCreate(BaseModel):
    """Create review request."""
    extraction_job_id: UUID
    trigger_reason: str = Field(..., min_length=1, max_length=100)
    priority: ReviewPriority = ReviewPriority.NORMAL
    metadata: Optional[Dict[str, Any]] = None


class ReviewAssignment(BaseModel):
    """Assign review to user."""
    assignee_user_id: UUID


class CorrectionCreate(BaseModel):
    """Create correction entry."""
    extraction_result_id: UUID
    field_path: str = Field(..., min_length=1, max_length=500)
    original_value: Optional[Any] = None
    corrected_value: Any
    correction_type: CorrectionType
    correction_notes: Optional[str] = None


class ReviewSubmission(BaseModel):
    """Submit review corrections."""
    corrections: List[CorrectionCreate]


class ReviewRequestResponse(BaseModel):
    """Review request response."""
    id: UUID
    tenant_id: UUID
    extraction_job_id: UUID
    trigger_reason: str
    confidence_score: Optional[float]
    priority: str
    status: str
    assigned_to_user_id: Optional[UUID]
    assigned_at: Optional[datetime]
    sla_minutes: int
    sla_deadline: Optional[datetime]
    escalated: bool
    escalated_at: Optional[datetime]
    completed_at: Optional[datetime]
    review_time_minutes: Optional[int]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    # Related data
    extraction_job: Optional[Dict[str, Any]] = None  # Included if requested
    corrections_count: Optional[int] = None

    class Config:
        from_attributes = True


class ReviewCorrectionResponse(BaseModel):
    """Review correction response."""
    id: UUID
    review_request_id: UUID
    extraction_result_id: UUID
    field_path: str
    original_value: Optional[Any]
    corrected_value: Any
    correction_type: str
    corrected_by_user_id: Optional[UUID]
    correction_notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewQueueResponse(BaseModel):
    """Review queue response."""
    reviews: List[ReviewRequestResponse]
    total: int
    limit: int
    offset: int


class ReviewMetricsResponse(BaseModel):
    """Review accuracy metrics."""
    total_reviews: int
    average_corrections_per_review: float
    most_corrected_fields: List[Dict[str, Any]]
    accuracy_rate: float  # Percentage
```

### 4.2 API Routes

```python
# app/api/reviews.py
"""HITL Review API endpoints."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.review_request import ReviewRequest
from app.models.enums import ReviewRequestStatus, ReviewPriority
from app.services.hitl_service import HITLService
from app.services.conductor_hitl_service import ConductorHITLService
from app.dependencies.auth import require_permission, get_current_active_user
from app.schemas.review import (
    ReviewRequestCreate,
    ReviewRequestResponse,
    ReviewAssignment,
    ReviewSubmission,
    ReviewQueueResponse,
    ReviewCorrectionResponse,
    ReviewMetricsResponse
)

router = APIRouter()


@router.post("/jobs/{job_id}/request-review", response_model=ReviewRequestResponse, status_code=201)
async def request_review(
    job_id: UUID,
    current_user: User = Depends(require_permission("extraction:review")),
    db: Session = Depends(get_db)
) -> ReviewRequestResponse:
    """
    Manually request human review for an extraction job.

    Required Permission: extraction:review

    Args:
        job_id: ExtractionJob UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Created ReviewRequest

    Raises:
        404: Job not found or belongs to different tenant
        400: Review already requested for this job
    """
    hitl_service = HITLService(db)

    # Create review request with manual trigger
    review_request = hitl_service.create_review_request(
        extraction_job_id=job_id,
        trigger_reason="manual_request",
        confidence_score=None,
        priority=ReviewPriority.NORMAL,
        metadata={"requested_by_user_id": str(current_user.id)}
    )

    return ReviewRequestResponse.from_orm(review_request)


@router.get("/reviews/queue", response_model=ReviewQueueResponse)
async def get_review_queue(
    status: Optional[List[str]] = Query(None, description="Filter by status"),
    priority: Optional[List[str]] = Query(None, description="Filter by priority"),
    assigned_to_me: bool = Query(False, description="Show only reviews assigned to me"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("reviews:read")),
    db: Session = Depends(get_db)
) -> ReviewQueueResponse:
    """
    Get review queue with filtering and pagination.

    Required Permission: reviews:read

    Args:
        status: Filter by status (pending, assigned, in_review, etc.)
        priority: Filter by priority (low, normal, high, critical)
        assigned_to_me: Show only reviews assigned to current user
        limit: Results per page
        offset: Pagination offset
        current_user: Authenticated user
        db: Database session

    Returns:
        Paginated list of review requests
    """
    hitl_service = HITLService(db)

    # Convert string filters to enums
    status_filter = [ReviewRequestStatus(s) for s in status] if status else None
    priority_filter = [ReviewPriority(p) for p in priority] if priority else None

    # Get assignee filter
    assignee_user_id = current_user.id if assigned_to_me else None

    # Get queue
    reviews, total = hitl_service.get_review_queue(
        tenant_id=current_user.tenant_id,
        assignee_user_id=assignee_user_id,
        status_filter=status_filter,
        priority_filter=priority_filter,
        limit=limit,
        offset=offset
    )

    return ReviewQueueResponse(
        reviews=[ReviewRequestResponse.from_orm(r) for r in reviews],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/reviews/{review_id}", response_model=ReviewRequestResponse)
async def get_review_details(
    review_id: UUID,
    include_job: bool = Query(False, description="Include extraction job details"),
    current_user: User = Depends(require_permission("reviews:read")),
    db: Session = Depends(get_db)
) -> ReviewRequestResponse:
    """
    Get review request details.

    Required Permission: reviews:read

    Args:
        review_id: ReviewRequest UUID
        include_job: Include extraction job details
        current_user: Authenticated user
        db: Database session

    Returns:
        ReviewRequest details

    Raises:
        404: Review not found or belongs to different tenant
    """
    # Get review with tenant isolation
    review = db.query(ReviewRequest).filter(
        ReviewRequest.id == review_id,
        ReviewRequest.tenant_id == current_user.tenant_id
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    response = ReviewRequestResponse.from_orm(review)

    # Include job details if requested
    if include_job:
        response.extraction_job = {
            "id": str(review.extraction_job.id),
            "document_id": str(review.extraction_job.document_id),
            "model_provider": review.extraction_job.model_provider,
            "model_name": review.extraction_job.model_name,
            "status": review.extraction_job.status
        }

    # Include corrections count
    response.corrections_count = len(review.corrections)

    return response


@router.post("/reviews/{review_id}/assign", response_model=ReviewRequestResponse)
async def assign_review(
    review_id: UUID,
    assignment: ReviewAssignment,
    current_user: User = Depends(require_permission("reviews:assign")),
    db: Session = Depends(get_db)
) -> ReviewRequestResponse:
    """
    Assign review to a user.

    Required Permission: reviews:assign

    Args:
        review_id: ReviewRequest UUID
        assignment: Assignment data (assignee_user_id)
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated ReviewRequest

    Raises:
        404: Review or assignee not found
        400: Review not in assignable state
    """
    hitl_service = HITLService(db)

    review_request = hitl_service.assign_review(
        review_request_id=review_id,
        assignee_user_id=assignment.assignee_user_id,
        tenant_id=current_user.tenant_id
    )

    return ReviewRequestResponse.from_orm(review_request)


@router.post("/reviews/{review_id}/start", response_model=ReviewRequestResponse)
async def start_review(
    review_id: UUID,
    current_user: User = Depends(require_permission("reviews:update")),
    db: Session = Depends(get_db)
) -> ReviewRequestResponse:
    """
    Start working on a review.

    Required Permission: reviews:update

    Args:
        review_id: ReviewRequest UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated ReviewRequest (status=in_review)

    Raises:
        404: Review not found
        403: User not assigned to this review
        400: Review not in correct state
    """
    hitl_service = HITLService(db)

    review_request = hitl_service.start_review(
        review_request_id=review_id,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id
    )

    return ReviewRequestResponse.from_orm(review_request)


@router.post("/reviews/{review_id}/submit", response_model=ReviewRequestResponse)
async def submit_review(
    review_id: UUID,
    submission: ReviewSubmission,
    current_user: User = Depends(require_permission("reviews:update")),
    db: Session = Depends(get_db)
) -> ReviewRequestResponse:
    """
    Submit review corrections.

    Required Permission: reviews:update

    Args:
        review_id: ReviewRequest UUID
        submission: Corrections data
        current_user: Authenticated user
        db: Database session

    Returns:
        Completed ReviewRequest

    Raises:
        404: Review not found
        403: User not assigned to this review
        400: Invalid correction data
    """
    hitl_service = HITLService(db)
    conductor_service = ConductorHITLService(db)

    # Submit corrections
    corrections_data = [corr.dict() for corr in submission.corrections]
    review_request, corrections = hitl_service.submit_corrections(
        review_request_id=review_id,
        corrections=corrections_data,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id
    )

    # Complete Conductor task if this review came from a workflow
    await conductor_service.complete_conductor_task(
        review_request=review_request,
        corrections=corrections
    )

    return ReviewRequestResponse.from_orm(review_request)


@router.get("/reviews/{review_id}/corrections", response_model=List[ReviewCorrectionResponse])
async def get_review_corrections(
    review_id: UUID,
    current_user: User = Depends(require_permission("reviews:read")),
    db: Session = Depends(get_db)
) -> List[ReviewCorrectionResponse]:
    """
    Get corrections for a review.

    Required Permission: reviews:read

    Args:
        review_id: ReviewRequest UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        List of corrections

    Raises:
        404: Review not found or belongs to different tenant
    """
    # Get review with tenant isolation
    review = db.query(ReviewRequest).filter(
        ReviewRequest.id == review_id,
        ReviewRequest.tenant_id == current_user.tenant_id
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    return [ReviewCorrectionResponse.from_orm(c) for c in review.corrections]


@router.delete("/reviews/{review_id}", status_code=204)
async def cancel_review(
    review_id: UUID,
    current_user: User = Depends(require_permission("reviews:delete")),
    db: Session = Depends(get_db)
) -> None:
    """
    Cancel a review request.

    Required Permission: reviews:delete

    Args:
        review_id: ReviewRequest UUID
        current_user: Authenticated user
        db: Database session

    Raises:
        404: Review not found
        400: Review already completed
    """
    # Get review with tenant isolation
    review = db.query(ReviewRequest).filter(
        ReviewRequest.id == review_id,
        ReviewRequest.tenant_id == current_user.tenant_id
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.status == ReviewRequestStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Cannot cancel completed review")

    # Cancel review
    review.status = ReviewRequestStatus.CANCELLED.value
    review.updated_at = datetime.utcnow()
    db.commit()


@router.get("/reviews/metrics", response_model=ReviewMetricsResponse)
async def get_review_metrics(
    schema_definition_id: Optional[UUID] = Query(None, description="Filter by schema"),
    date_from: Optional[datetime] = Query(None, description="Start date"),
    date_to: Optional[datetime] = Query(None, description="End date"),
    current_user: User = Depends(require_permission("reviews:read")),
    db: Session = Depends(get_db)
) -> ReviewMetricsResponse:
    """
    Get review accuracy metrics.

    Required Permission: reviews:read

    Args:
        schema_definition_id: Filter by schema (optional)
        date_from: Start date for metrics (optional)
        date_to: End date for metrics (optional)
        current_user: Authenticated user
        db: Database session

    Returns:
        Accuracy metrics
    """
    hitl_service = HITLService(db)

    metrics = hitl_service.get_accuracy_metrics(
        tenant_id=current_user.tenant_id,
        schema_definition_id=schema_definition_id,
        date_from=date_from,
        date_to=date_to
    )

    return ReviewMetricsResponse(**metrics)
```

---

## 5. State Machine Diagram

```
ExtractionJob Lifecycle with HITL:

uploaded → processing → completed → [confidence check]
              ↓                            ↓
            failed                    Low Confidence
                                           ↓
                                    ReviewRequest Created
                                           ↓
                                        pending
                                           ↓
                                       assigned
                                           ↓
                                      in_review
                                           ↓
                                      completed
                                           ↓
                                 [Apply Corrections]
                                           ↓
                               ExtractionResult Updated


ReviewRequest Lifecycle:

pending → assigned → in_review → completed
   ↓          ↓           ↓
cancelled  escalated  escalated
```

---

## 6. Implementation Phases

### Phase 1: Database Foundation (Week 1)
- [ ] Create Alembic migration for review_requests and review_corrections tables
- [ ] Add enums: ReviewRequestStatus, ReviewPriority, CorrectionType
- [ ] Add model relationships (ExtractionJob.review_request, Tenant.review_requests)
- [ ] Run migration and verify schema
- [ ] Write unit tests for model validators

### Phase 2: VLLM Confidence Scoring (Week 1)
- [ ] Update VLLMProvider interface to return confidence_score
- [ ] Implement _calculate_confidence_score in GeminiVLLMProvider
- [ ] Implement _calculate_confidence_score in OpenAIVLLMProvider
- [ ] Update ExtractionResult.confidence_score population in extraction tasks
- [ ] Test confidence scoring with sample documents

### Phase 3: HITL Service Layer (Week 2)
- [ ] Implement HITLService.should_request_review()
- [ ] Implement HITLService.create_review_request()
- [ ] Implement HITLService.get_review_queue()
- [ ] Implement HITLService.assign_review()
- [ ] Implement HITLService.submit_corrections()
- [ ] Implement HITLService.apply_corrections_to_result()
- [ ] Write comprehensive unit tests for all methods

### Phase 4: API Endpoints (Week 2)
- [ ] Create Pydantic schemas (review.py)
- [ ] Implement POST /jobs/{job_id}/request-review
- [ ] Implement GET /reviews/queue
- [ ] Implement GET /reviews/{review_id}
- [ ] Implement POST /reviews/{review_id}/assign
- [ ] Implement POST /reviews/{review_id}/start
- [ ] Implement POST /reviews/{review_id}/submit
- [ ] Implement GET /reviews/{review_id}/corrections
- [ ] Implement DELETE /reviews/{review_id}
- [ ] Implement GET /reviews/metrics
- [ ] Write integration tests for all endpoints

### Phase 5: Conductor Integration (Week 3)
- [ ] Implement HumanReviewWorker for HUMAN tasks
- [ ] Implement ConductorHITLService.complete_conductor_task()
- [ ] Update workflow definitions to include HUMAN task nodes
- [ ] Test end-to-end workflow with HUMAN task
- [ ] Add HUMAN task node type to workflow builder UI

### Phase 6: Auto-Routing Logic (Week 3)
- [ ] Update extraction tasks to call HITLService.should_request_review()
- [ ] Auto-create ReviewRequest for low-confidence extractions
- [ ] Configure confidence thresholds per tenant/schema
- [ ] Test auto-routing with various confidence scores

### Phase 7: SLA Monitoring & Escalation (Week 4)
- [ ] Implement HITLService.check_sla_breaches()
- [ ] Create Celery periodic task for SLA monitoring (every 5 minutes)
- [ ] Implement escalation policy (reassign to senior reviewer)
- [ ] Add SLA breach notifications (email/webhook)
- [ ] Test escalation workflow

### Phase 8: Frontend Integration (Week 4)
- [ ] Create review queue UI component
- [ ] Create review details/correction UI
- [ ] Add review metrics dashboard
- [ ] Integrate with existing workflow builder
- [ ] End-to-end testing

---

## 7. Testing Strategy

### Unit Tests
```python
# tests/unit/services/test_hitl_service.py

def test_should_request_review_manual():
    """Manual request always requires review."""
    hitl_service = HITLService(db)
    needs_review, reason, priority = hitl_service.should_request_review(
        confidence_score=0.95,
        validation_errors=[],
        manual_request=True
    )
    assert needs_review == True
    assert reason == "manual_request"
    assert priority == ReviewPriority.NORMAL


def test_should_request_review_low_confidence():
    """Low confidence triggers review."""
    hitl_service = HITLService(db)
    needs_review, reason, priority = hitl_service.should_request_review(
        confidence_score=0.25,  # Below CRITICAL threshold (0.30)
        validation_errors=[],
        manual_request=False
    )
    assert needs_review == True
    assert reason == "low_confidence"
    assert priority == ReviewPriority.CRITICAL


def test_should_request_review_high_confidence():
    """High confidence auto-approves."""
    hitl_service = HITLService(db)
    needs_review, reason, priority = hitl_service.should_request_review(
        confidence_score=0.85,  # Above all thresholds
        validation_errors=[],
        manual_request=False
    )
    assert needs_review == False
    assert reason is None
    assert priority is None
```

### Integration Tests
```python
# tests/integration/api/test_reviews_api.py

def test_create_review_request(client, auth_headers, extraction_job):
    """Test creating a manual review request."""
    response = client.post(
        f"/api/v1/jobs/{extraction_job.id}/request-review",
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["extraction_job_id"] == str(extraction_job.id)
    assert data["status"] == "pending"
    assert data["trigger_reason"] == "manual_request"


def test_get_review_queue(client, auth_headers, review_requests):
    """Test getting review queue with filters."""
    response = client.get(
        "/api/v1/reviews/queue?status=pending&priority=high",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert all(r["status"] == "pending" for r in data["reviews"])
```

---

## 8. Architectural Decisions (ADRs)

### ADR-1: Use Conductor's HUMAN Task Type
**Decision**: Leverage Netflix Conductor's built-in HUMAN task type rather than building custom workflow pausing logic.

**Rationale**:
- Conductor provides battle-tested HUMAN task implementation
- Automatic workflow suspension/resumption
- Built-in task lifecycle management
- Reduces custom code complexity

**Consequences**:
- Tight coupling with Conductor for HITL workflows
- Must follow Conductor's task completion API
- Benefit: Faster implementation, more reliable

### ADR-2: Separate ReviewRequest from ExtractionJob
**Decision**: Create a separate `review_requests` table rather than adding review fields to `extraction_jobs`.

**Rationale**:
- Single Responsibility Principle: ReviewRequest handles review lifecycle
- Not all extractions require review
- Clearer data model and queries
- Easier to extend with review-specific features

**Consequences**:
- Additional join required to get review status
- Benefit: Cleaner separation of concerns

### ADR-3: Track Individual Field Corrections
**Decision**: Store corrections at field-level granularity in `review_corrections` table.

**Rationale**:
- Enables detailed accuracy analysis per field
- Supports targeted prompt improvement
- Provides audit trail of specific changes
- Allows partial corrections (not all-or-nothing)

**Consequences**:
- More complex data model
- Benefit: Rich feedback data for AI improvement

### ADR-4: Confidence Score Calculation in VLLM Providers
**Decision**: Calculate confidence scores within VLLM provider classes (GeminiVLLMProvider, OpenAIVLLMProvider).

**Rationale**:
- Provider-specific confidence signals (logprobs, safety ratings)
- Encapsulates confidence logic with extraction logic
- Allows per-provider tuning of confidence algorithms

**Consequences**:
- Confidence calculation duplicated across providers
- Benefit: More accurate provider-specific confidence

### ADR-5: SLA-Based Priority Levels
**Decision**: Map review priorities to SLA deadlines (CRITICAL=1h, HIGH=2h, NORMAL=4h, LOW=8h).

**Rationale**:
- Clear urgency signaling to reviewers
- Enables automatic escalation based on time
- Aligns with industry best practices

**Consequences**:
- Must monitor SLA breaches actively
- Benefit: Ensures timely review completion

---

## 9. Security Considerations

### Multi-Tenancy Isolation
- All review queries MUST filter by `tenant_id`
- Reviewers can only see reviews for their tenant
- API endpoints enforce tenant isolation via JWT authentication

### Permission Model
```
reviews:read    - View review queue and details
reviews:assign  - Assign reviews to users
reviews:update  - Start reviews and submit corrections
reviews:delete  - Cancel review requests
extraction:review - Request review for extraction jobs
```

### Audit Trail
- All corrections tracked with `corrected_by_user_id`
- Timestamps on assignment, start, completion
- Original AI values preserved for comparison

### Data Privacy
- PII in extraction results subject to same access controls
- Review corrections inherit tenant isolation
- Conductor task output sanitized before storage

---

## 10. Performance Considerations

### Database Indexes
```sql
-- Critical indexes for review queue queries
CREATE INDEX idx_review_queue ON review_requests(tenant_id, status, priority, created_at);
CREATE INDEX idx_review_requests_sla_deadline ON review_requests(sla_deadline);
CREATE INDEX idx_review_corrections_field_path ON review_corrections(field_path);
```

### Query Optimization
- Use composite index for queue queries (tenant + status + priority + created_at)
- Paginate review queue (default 50, max 100 per page)
- Cache review metrics for dashboard (refresh every 5 minutes)

### Scalability
- Review requests are independent (no locks between reviews)
- SLA monitoring uses bulk queries (process 1000s of reviews efficiently)
- Conductor HUMAN tasks scale horizontally with worker pool

---

## 11. Monitoring & Observability

### Key Metrics
```python
# Prometheus metrics
review_requests_created_total
review_requests_completed_total
review_time_seconds (histogram)
sla_breaches_total
corrections_per_review (histogram)
accuracy_rate_by_schema (gauge)
```

### Logging
```python
logger.info("review_request_created", extra={
    "review_request_id": str(review_request.id),
    "extraction_job_id": str(job_id),
    "priority": priority.value,
    "trigger_reason": trigger_reason
})

logger.warning("sla_breach", extra={
    "review_request_id": str(review_id),
    "sla_deadline": deadline.isoformat(),
    "elapsed_minutes": elapsed
})
```

---

## 12. Future Enhancements

### Phase 2 Features
1. **Active Learning**: Use corrections to retrain/fine-tune VLLM models
2. **Review Templates**: Pre-filled correction templates for common errors
3. **Batch Review**: Review multiple similar extractions at once
4. **Inter-Reviewer Agreement**: Track consistency between reviewers
5. **Smart Assignment**: ML-based reviewer assignment (expertise matching)
6. **Review Sampling**: Randomly sample high-confidence extractions for quality checks

---

## 13. Validation & Testing Strategy

This section provides comprehensive validation steps to confirm the HITL implementation is working correctly and aligns with the specification.

### 13.1 Database Schema Validation

#### Validation Steps

**Step 1: Verify Tables Created**
```sql
-- Check that new tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('review_requests', 'review_corrections');

-- Expected: 2 rows
```

**Step 2: Verify Column Types**
```sql
-- Check ReviewRequest schema
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'review_requests'
ORDER BY ordinal_position;

-- Verify key columns:
-- - id: UUID, NOT NULL
-- - tenant_id: UUID, NOT NULL
-- - extraction_job_id: UUID, NOT NULL
-- - confidence_score: NUMERIC/FLOAT, NULL
-- - priority: VARCHAR(50), NOT NULL
-- - status: VARCHAR(50), NOT NULL
-- - sla_deadline: TIMESTAMP, NULL
```

**Step 3: Verify Indexes**
```sql
-- Check critical indexes exist
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('review_requests', 'review_corrections')
ORDER BY tablename, indexname;

-- Must have:
-- - idx_review_queue (tenant_id, status, priority, created_at)
-- - idx_review_requests_sla_deadline (sla_deadline)
-- - idx_review_corrections_field_path (field_path)
```

**Step 4: Verify Foreign Key Constraints**
```sql
-- Check foreign key relationships
SELECT
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name IN ('review_requests', 'review_corrections');

-- Expected foreign keys:
-- - review_requests.tenant_id → tenants.id
-- - review_requests.extraction_job_id → extraction_jobs.id
-- - review_requests.assigned_to_user_id → users.id
-- - review_corrections.review_request_id → review_requests.id
-- - review_corrections.extraction_result_id → extraction_results.id
```

**Step 5: Verify Enum Values**
```python
# Test that enums are properly defined
from app.models.enums import ReviewRequestStatus, ReviewPriority, CorrectionType

# Check ReviewRequestStatus
assert ReviewRequestStatus.PENDING.value == "pending"
assert ReviewRequestStatus.ASSIGNED.value == "assigned"
assert ReviewRequestStatus.IN_REVIEW.value == "in_review"
assert ReviewRequestStatus.COMPLETED.value == "completed"
assert ReviewRequestStatus.CANCELLED.value == "cancelled"
assert ReviewRequestStatus.ESCALATED.value == "escalated"

# Check ReviewPriority
assert ReviewPriority.CRITICAL.value == "critical"
assert ReviewPriority.HIGH.value == "high"
assert ReviewPriority.NORMAL.value == "normal"
assert ReviewPriority.LOW.value == "low"

# Check CorrectionType
assert CorrectionType.VALUE_CHANGE.value == "value_change"
assert CorrectionType.FIELD_ADDITION.value == "field_addition"
assert CorrectionType.FIELD_REMOVAL.value == "field_removal"
assert CorrectionType.TYPE_CORRECTION.value == "type_correction"
```

**Expected Result:** ✅ All assertions pass, no errors

---

### 13.2 Confidence Scoring Validation

#### Validation Steps

**Step 1: Verify VLLM Provider Returns Confidence Score**
```python
# Test GeminiVLLMProvider
from app.services.vllm_service import GeminiVLLMProvider

provider = GeminiVLLMProvider()
result = await provider.extract_from_image(
    image_bytes=test_image,
    schema=test_schema
)

# Verify return signature
assert len(result) == 5, "Should return 5 values: (data, tokens_in, tokens_out, time_ms, confidence)"
data, tokens_in, tokens_out, time_ms, confidence_score = result

# Verify confidence score bounds
assert 0.0 <= confidence_score <= 1.0, f"Confidence must be [0-1], got {confidence_score}"
assert isinstance(confidence_score, float), "Confidence must be float"
```

**Step 2: Test Confidence Calculation Components**
```python
# Test schema coverage calculation
from app.services.vllm_service import GeminiVLLMProvider

provider = GeminiVLLMProvider()

# Test schema with 5 required fields
test_schema = {
    "type": "object",
    "required": ["field1", "field2", "field3", "field4", "field5"],
    "properties": {...}
}

# Test with all fields present
extracted_data = {
    "field1": "value1",
    "field2": "value2",
    "field3": "value3",
    "field4": "value4",
    "field5": "value5"
}
coverage = provider._calculate_schema_coverage(extracted_data, test_schema)
assert coverage == 1.0, "All required fields present should give 1.0"

# Test with missing fields
extracted_data_partial = {
    "field1": "value1",
    "field2": "value2",
    "field3": "value3"
}
coverage = provider._calculate_schema_coverage(extracted_data_partial, test_schema)
assert coverage == 0.6, "3 of 5 fields = 0.6"
```

**Step 3: Verify Confidence Score Persisted**
```python
# Create extraction job with confidence
job = await extraction_service.create_extraction_job(
    document_id=doc_id,
    schema=test_schema
)

# Process extraction
await extraction_task.delay(job.id)

# Verify confidence score saved
result = db.query(ExtractionResult).filter(
    ExtractionResult.extraction_job_id == job.id
).first()

assert result.confidence_score is not None, "Confidence score should be populated"
assert 0.0 <= result.confidence_score <= 1.0
```

**Expected Result:** ✅ Confidence scores calculated and persisted correctly

---

### 13.3 Threshold Configuration Validation

#### Validation Steps

**Step 1: Test Global Default Threshold**
```python
from app.services.hitl_service import HITLService

hitl_service = HITLService(db)

# Create mock job with no tenant/schema overrides
job = create_test_job(confidence_score=0.65)

# Should use global default (0.70)
should_review = hitl_service.should_request_review(
    job=job,
    workflow_config=None
)

assert should_review is True, "0.65 < 0.70 (default) should trigger review"

# Test above threshold
job.confidence_score = 0.75
should_review = hitl_service.should_request_review(job=job, workflow_config=None)
assert should_review is False, "0.75 > 0.70 should auto-approve"
```

**Step 2: Test Tenant-Level Threshold Override**
```python
# Set tenant threshold
tenant = db.query(Tenant).filter(Tenant.id == test_tenant_id).first()
tenant.hitl_auto_approve_threshold = 0.80  # More conservative
db.commit()

# Test with job from this tenant
job = create_test_job(
    tenant_id=test_tenant_id,
    confidence_score=0.75
)

should_review = hitl_service.should_request_review(job=job, workflow_config=None)
assert should_review is True, "0.75 < 0.80 (tenant override) should trigger review"

# Test above tenant threshold
job.confidence_score = 0.85
should_review = hitl_service.should_request_review(job=job, workflow_config=None)
assert should_review is False, "0.85 > 0.80 should auto-approve"
```

**Step 3: Test Schema-Level Threshold Override**
```python
# Create schema with custom threshold
schema = create_test_schema(
    tenant_id=test_tenant_id,
    hitl_threshold=0.90  # High-stakes documents
)

job = create_test_job(
    tenant_id=test_tenant_id,
    schema_id=schema.id,
    confidence_score=0.85
)

should_review = hitl_service.should_request_review(job=job, workflow_config=None)
assert should_review is True, "0.85 < 0.90 (schema override) should trigger review"
```

**Step 4: Test Workflow-Level Threshold Override (Highest Priority)**
```python
# Workflow config overrides everything
workflow_config = {
    "confidence_threshold": 0.95
}

job = create_test_job(
    tenant_id=test_tenant_id,
    schema_id=schema.id,  # has threshold 0.90
    confidence_score=0.92
)

should_review = hitl_service.should_request_review(
    job=job,
    workflow_config=workflow_config
)
assert should_review is True, "0.92 < 0.95 (workflow override wins) should trigger review"
```

**Step 5: Verify Threshold Resolution Priority**
```python
# Test full cascading logic
tenant.hitl_auto_approve_threshold = 0.75
schema.hitl_threshold = 0.85
workflow_config = {"confidence_threshold": 0.95}

# Get resolved threshold
resolved = hitl_service._resolve_threshold(
    tenant=tenant,
    schema=schema,
    workflow_config=workflow_config
)

assert resolved == 0.95, "Workflow config (0.95) should win over schema (0.85) and tenant (0.75)"

# Test without workflow config
resolved = hitl_service._resolve_threshold(
    tenant=tenant,
    schema=schema,
    workflow_config=None
)
assert resolved == 0.85, "Schema (0.85) should win over tenant (0.75)"

# Test with schema.hitl_threshold = None
schema.hitl_threshold = None
resolved = hitl_service._resolve_threshold(
    tenant=tenant,
    schema=schema,
    workflow_config=None
)
assert resolved == 0.75, "Tenant (0.75) should win when schema not set"
```

**Expected Result:** ✅ Threshold resolution follows priority: Workflow > Schema > Tenant > Default

---

### 13.4 API Endpoint Validation

#### Validation Steps

**Step 1: Test Manual Review Request**
```bash
# Create manual review request
curl -X POST http://localhost:8000/api/v1/jobs/{job_id}/request-review \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "priority": "high",
    "notes": "Unclear vendor name"
  }'

# Expected: 201 Created
# Response: {"review_request_id": "...", "status": "pending"}

# Verify in database
SELECT * FROM review_requests WHERE extraction_job_id = '{job_id}';
# Should have 1 row with status='pending', priority='high'
```

**Step 2: Test Get Review Queue**
```bash
# Get all pending reviews
curl http://localhost:8000/api/v1/reviews/queue?status=pending \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 OK
# Response: {
#   "items": [...],
#   "total": N,
#   "page": 1,
#   "page_size": 50
# }

# Verify tenant isolation
# Login as different tenant, should see different queue
```

**Step 3: Test Assign Review**
```bash
# Assign review to specific user
curl -X POST http://localhost:8000/api/v1/reviews/{review_id}/assign \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "assigned_to_user_id": "{user_id}"
  }'

# Expected: 200 OK
# Verify: status changed from 'pending' to 'assigned'
# Verify: assigned_to_user_id set, assigned_at timestamp set
```

**Step 4: Test Start Review**
```bash
# Start review
curl -X POST http://localhost:8000/api/v1/reviews/{review_id}/start \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 OK
# Verify: status changed to 'in_review'
# Verify: started_at timestamp set
```

**Step 5: Test Submit Corrections**
```bash
# Submit corrections
curl -X POST http://localhost:8000/api/v1/reviews/{review_id}/submit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "corrections": [
      {
        "extraction_result_id": "...",
        "field_path": "invoice.vendor_name",
        "original_value": "Acme Corp",
        "corrected_value": "Acme Corporation",
        "correction_type": "value_change",
        "correction_notes": "Official legal name"
      }
    ]
  }'

# Expected: 200 OK
# Verify: status changed to 'completed'
# Verify: completed_at timestamp set
# Verify: review_corrections table has 1 row
# Verify: extraction_result updated with corrected value
```

**Step 6: Test Get Metrics**
```bash
# Get review metrics
curl http://localhost:8000/api/v1/reviews/metrics \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 OK
# Response should include:
# - total_reviews_completed
# - average_review_time_seconds
# - corrections_per_review
# - accuracy_rate_by_schema
# - most_corrected_fields
```

**Step 7: Test Permissions**
```python
# Test that users without 'reviews:read' permission get 403
response = client.get(
    "/api/v1/reviews/queue",
    headers={"Authorization": f"Bearer {token_without_permission}"}
)
assert response.status_code == 403

# Test that users can only assign to users in their tenant
response = client.post(
    f"/api/v1/reviews/{review_id}/assign",
    json={"assigned_to_user_id": str(other_tenant_user_id)},
    headers={"Authorization": f"Bearer {token}"}
)
assert response.status_code == 403  # Cannot assign to other tenant
```

**Expected Result:** ✅ All endpoints respond correctly with proper auth and tenant isolation

---

### 13.5 Conductor Integration Validation

#### Validation Steps

**Step 1: Verify HumanReviewWorker Registration**
```python
# Check worker is registered with Conductor
from app.orchestration.workers.human_review_worker import HumanReviewWorker
from conductor.client.http.api_client import ApiClient

worker = HumanReviewWorker(hitl_service)
assert worker.get_task_definition_name() == "HUMAN_REVIEW"

# Start worker (in test mode)
worker.start()

# Verify polling
# Worker should poll Conductor for HUMAN_REVIEW tasks
```

**Step 2: Test Workflow with HUMAN Task**
```python
# Create workflow definition with HUMAN task
workflow_def = {
    "name": "test_extraction_with_review",
    "version": 1,
    "tasks": [
        {
            "name": "extract_document",
            "taskReferenceName": "extract_task",
            "type": "SIMPLE"
        },
        {
            "name": "check_confidence",
            "taskReferenceName": "confidence_check",
            "type": "SWITCH",
            "evaluatorType": "javascript",
            "expression": "$.extract_task.output.confidence < 0.70 ? 'low' : 'high'",
            "decisionCases": {
                "low": [
                    {
                        "name": "HUMAN_REVIEW",
                        "taskReferenceName": "human_review",
                        "type": "HUMAN",
                        "inputParameters": {
                            "document_id": "${workflow.input.document_id}",
                            "extraction_result": "${extract_task.output.result}",
                            "confidence_scores": "${extract_task.output.confidence}"
                        }
                    }
                ],
                "high": [
                    {
                        "name": "auto_approve",
                        "taskReferenceName": "approve_task",
                        "type": "SIMPLE"
                    }
                ]
            }
        }
    ]
}

# Register workflow
conductor_client.register_workflow_def(workflow_def)

# Start workflow with low confidence result
workflow_id = conductor_client.start_workflow(
    name="test_extraction_with_review",
    version=1,
    input={"document_id": str(test_doc_id)}
)

# Verify workflow status
status = conductor_client.get_workflow(workflow_id)
assert status["status"] == "RUNNING"

# Find HUMAN task
human_task = next(t for t in status["tasks"] if t["taskType"] == "HUMAN")
assert human_task["status"] == "IN_PROGRESS"
```

**Step 3: Verify ReviewRequest Created by Worker**
```python
# Check that worker created ReviewRequest in database
review_request = db.query(ReviewRequest).filter(
    ReviewRequest.conductor_task_id == human_task["taskId"]
).first()

assert review_request is not None, "Worker should create ReviewRequest"
assert review_request.status == ReviewRequestStatus.PENDING.value
assert review_request.conductor_workflow_id == workflow_id
```

**Step 4: Test Review Completion Updates Conductor**
```python
# Submit review via API
response = client.post(
    f"/api/v1/reviews/{review_request.id}/submit",
    json={
        "corrections": [
            {
                "extraction_result_id": str(result_id),
                "field_path": "invoice.total",
                "original_value": "100.00",
                "corrected_value": "150.00",
                "correction_type": "value_change"
            }
        ]
    },
    headers={"Authorization": f"Bearer {token}"}
)

assert response.status_code == 200

# Verify Conductor task updated to COMPLETED
conductor_task = conductor_client.get_task(human_task["taskId"])
assert conductor_task["status"] == "COMPLETED"
assert conductor_task["outputData"]["corrected_data"] is not None

# Verify workflow continues
time.sleep(2)  # Allow workflow to progress
final_status = conductor_client.get_workflow(workflow_id)
assert final_status["status"] == "COMPLETED"
```

**Expected Result:** ✅ Conductor workflows pause at HUMAN task, resume after review completion

---

### 13.6 End-to-End Workflow Validation

#### Complete E2E Test

```python
async def test_hitl_end_to_end():
    """
    Complete end-to-end test of HITL workflow.

    Flow:
    1. Upload document
    2. Create extraction job
    3. Process extraction (low confidence)
    4. Auto-create review request
    5. Assign to reviewer
    6. Submit corrections
    7. Verify extraction updated
    8. Verify job completed
    """

    # Step 1: Upload document
    doc = await document_service.upload_document(
        tenant_id=tenant_id,
        file_bytes=test_pdf_bytes,
        filename="test_invoice.pdf"
    )
    assert doc.status == DocumentStatus.UPLOADED

    # Step 2: Create extraction job
    job = await extraction_service.create_extraction_job(
        document_id=doc.id,
        schema=test_schema,
        tenant_id=tenant_id
    )

    # Step 3: Process extraction
    # Mock VLLM to return low confidence
    with patch.object(GeminiVLLMProvider, 'extract_from_image') as mock_extract:
        mock_extract.return_value = (
            {"vendor": "Acme Corp", "total": "100.00"},  # data
            1000,  # tokens_in
            500,   # tokens_out
            2000,  # time_ms
            0.45   # confidence_score (low!)
        )

        await extraction_task.apply_async(args=[str(job.id)])

    # Step 4: Verify review request auto-created
    review_request = db.query(ReviewRequest).filter(
        ReviewRequest.extraction_job_id == job.id
    ).first()

    assert review_request is not None, "Review should auto-create for low confidence"
    assert review_request.status == ReviewRequestStatus.PENDING.value
    assert review_request.confidence_score == 0.45
    assert review_request.priority == ReviewPriority.HIGH.value  # 0.30-0.50 = HIGH

    # Step 5: Assign to reviewer
    hitl_service.assign_review(
        review_id=review_request.id,
        assigned_to_user_id=reviewer_user_id
    )

    review_request = db.query(ReviewRequest).get(review_request.id)
    assert review_request.status == ReviewRequestStatus.ASSIGNED.value
    assert review_request.assigned_to_user_id == reviewer_user_id

    # Step 6: Start review
    hitl_service.start_review(review_id=review_request.id)
    review_request = db.query(ReviewRequest).get(review_request.id)
    assert review_request.status == ReviewRequestStatus.IN_REVIEW.value
    assert review_request.started_at is not None

    # Step 7: Submit corrections
    result = db.query(ExtractionResult).filter(
        ExtractionResult.extraction_job_id == job.id
    ).first()

    corrections = [
        ReviewCorrectionCreate(
            extraction_result_id=result.id,
            field_path="vendor",
            original_value="Acme Corp",
            corrected_value="Acme Corporation",
            correction_type=CorrectionType.VALUE_CHANGE,
            correction_notes="Official legal name"
        )
    ]

    hitl_service.submit_corrections(
        review_id=review_request.id,
        corrections=corrections,
        corrected_by_user_id=reviewer_user_id
    )

    # Step 8: Verify corrections applied
    review_request = db.query(ReviewRequest).get(review_request.id)
    assert review_request.status == ReviewRequestStatus.COMPLETED.value
    assert review_request.completed_at is not None

    # Step 9: Verify extraction result updated
    result = db.query(ExtractionResult).get(result.id)
    assert result.extracted_data["vendor"] == "Acme Corporation"  # Corrected!

    # Step 10: Verify correction tracked
    correction = db.query(ReviewCorrection).filter(
        ReviewCorrection.review_request_id == review_request.id
    ).first()
    assert correction.field_path == "vendor"
    assert correction.original_value == "Acme Corp"
    assert correction.corrected_value == "Acme Corporation"

    # Step 11: Verify job completed
    job = db.query(ExtractionJob).get(job.id)
    assert job.status == ExtractionJobStatus.COMPLETED.value
```

**Expected Result:** ✅ Complete flow works end-to-end without errors

---

### 13.7 Multi-Tenancy Validation

#### Validation Steps

**Step 1: Verify Tenant Isolation in Review Queue**
```python
# Create reviews for two different tenants
tenant1_review = create_review_request(tenant_id=tenant1_id)
tenant2_review = create_review_request(tenant_id=tenant2_id)

# Query as tenant 1
tenant1_queue = hitl_service.get_review_queue(
    tenant_id=tenant1_id,
    status=ReviewRequestStatus.PENDING
)

# Should only see tenant 1's reviews
assert len(tenant1_queue) == 1
assert tenant1_queue[0].id == tenant1_review.id
assert tenant2_review.id not in [r.id for r in tenant1_queue]
```

**Step 2: Verify Cross-Tenant Assignment Prevention**
```python
# Try to assign tenant 1's review to tenant 2's user
with pytest.raises(HTTPException) as exc:
    hitl_service.assign_review(
        review_id=tenant1_review.id,
        assigned_to_user_id=tenant2_user_id,
        requesting_user_tenant_id=tenant1_id
    )

assert exc.value.status_code == 403
assert "different tenant" in str(exc.value.detail).lower()
```

**Step 3: Verify API Token Tenant Isolation**
```python
# Create API token for tenant 1
api_token = create_api_token(tenant_id=tenant1_id, scopes=["reviews:read"])

# Try to access tenant 2's review
response = client.get(
    f"/api/v1/reviews/{tenant2_review.id}",
    headers={"Authorization": f"Bearer {api_token}"}
)

assert response.status_code == 404  # Not 403, to avoid leaking existence
```

**Expected Result:** ✅ Complete tenant isolation, no cross-tenant access

---

### 13.8 SLA Tracking Validation

#### Validation Steps

**Step 1: Verify SLA Deadline Calculation**
```python
# Create review with CRITICAL priority
review = hitl_service.create_review_request(
    extraction_job_id=job_id,
    priority=ReviewPriority.CRITICAL,
    trigger_reason="low_confidence"
)

# Verify SLA deadline
expected_deadline = review.created_at + timedelta(hours=1)  # CRITICAL = 1 hour
assert abs((review.sla_deadline - expected_deadline).total_seconds()) < 60  # Within 1 min
```

**Step 2: Test SLA Breach Detection**
```python
# Create review in the past
review = create_review_request(priority=ReviewPriority.NORMAL)
review.created_at = datetime.utcnow() - timedelta(hours=5)
review.sla_deadline = datetime.utcnow() - timedelta(hours=1)  # Breached!
db.commit()

# Run SLA check
breaches = hitl_service.check_sla_breaches()

# Verify breach detected
assert review.id in [b.id for b in breaches]
assert review.status == ReviewRequestStatus.ESCALATED.value
```

**Step 3: Test Escalation Policy**
```python
# Configure escalation pool
tenant.escalation_user_pool = [senior_reviewer_id]
db.commit()

# Trigger SLA breach
breached_review = create_sla_breached_review()
hitl_service.handle_sla_breach(breached_review.id)

# Verify escalation
review = db.query(ReviewRequest).get(breached_review.id)
assert review.status == ReviewRequestStatus.ESCALATED.value
assert review.assigned_to_user_id == senior_reviewer_id  # Reassigned
assert review.escalation_count == 1
```

**Expected Result:** ✅ SLA tracking works, breaches escalate correctly

---

### 13.9 Security & Permissions Validation

#### Validation Steps

**Step 1: Test Permission Enforcement**
```python
# User WITHOUT 'reviews:read' permission
user_no_perms = create_user(tenant_id=tenant_id, role="basic_user")

response = client.get(
    "/api/v1/reviews/queue",
    headers={"Authorization": f"Bearer {get_token(user_no_perms)}"}
)
assert response.status_code == 403

# User WITH 'reviews:read' permission
user_with_perms = create_user(tenant_id=tenant_id, role="reviewer")

response = client.get(
    "/api/v1/reviews/queue",
    headers={"Authorization": f"Bearer {get_token(user_with_perms)}"}
)
assert response.status_code == 200
```

**Step 2: Test Data Privacy**
```python
# Verify PII in extraction results not leaked in logs
with capture_logs() as logs:
    await extraction_task.apply_async(args=[str(job_id)])

# Check logs don't contain sensitive data
for log_entry in logs:
    assert "credit_card_number" not in log_entry
    assert "ssn" not in log_entry
```

**Step 3: Test Audit Trail**
```python
# Perform correction
hitl_service.submit_corrections(
    review_id=review_id,
    corrections=[...],
    corrected_by_user_id=reviewer_id
)

# Verify audit log
correction = db.query(ReviewCorrection).filter(
    ReviewCorrection.review_request_id == review_id
).first()

assert correction.corrected_by_user_id == reviewer_id
assert correction.corrected_at is not None
assert correction.original_value != correction.corrected_value
```

**Expected Result:** ✅ Permissions enforced, audit trail complete, PII protected

---

### 13.10 Performance Validation

#### Validation Steps

**Step 1: Test Review Queue Query Performance**
```python
# Create 10,000 review requests
for i in range(10000):
    create_review_request(tenant_id=tenant_id)

# Query with composite index
import time
start = time.time()
queue = hitl_service.get_review_queue(
    tenant_id=tenant_id,
    status=ReviewRequestStatus.PENDING,
    page=1,
    page_size=50
)
elapsed = time.time() - start

# Should be fast due to idx_review_queue index
assert elapsed < 0.1, f"Query took {elapsed}s, expected < 0.1s"
assert len(queue) == 50  # Paginated correctly
```

**Step 2: Test SLA Monitoring Bulk Query**
```python
# Create 5,000 reviews with various deadlines
for i in range(5000):
    create_review_request(
        sla_deadline=datetime.utcnow() + timedelta(hours=random.randint(-2, 10))
    )

# Run SLA check
start = time.time()
breaches = hitl_service.check_sla_breaches()
elapsed = time.time() - start

# Should process all reviews efficiently
assert elapsed < 1.0, f"SLA check took {elapsed}s, expected < 1s"
```

**Step 3: Test Concurrent Review Submissions**
```python
# Create 100 reviews
reviews = [create_review_request() for _ in range(100)]

# Submit all concurrently
import asyncio
async def submit_review(review_id):
    return await hitl_service.submit_corrections(
        review_id=review_id,
        corrections=[...],
        corrected_by_user_id=reviewer_id
    )

start = time.time()
await asyncio.gather(*[submit_review(r.id) for r in reviews])
elapsed = time.time() - start

# Should handle concurrency without deadlocks
assert elapsed < 10.0, "100 concurrent submissions should complete quickly"

# Verify all completed
completed = db.query(ReviewRequest).filter(
    ReviewRequest.status == ReviewRequestStatus.COMPLETED.value
).count()
assert completed == 100
```

**Expected Result:** ✅ Queries fast (<100ms), no deadlocks under concurrency

---

### 13.11 Validation Checklist Summary

Use this checklist to track validation progress:

#### Database & Schema
- [ ] Tables created (review_requests, review_corrections)
- [ ] Columns have correct types and nullability
- [ ] Indexes created (idx_review_queue, idx_sla_deadline, idx_field_path)
- [ ] Foreign keys configured with correct ON DELETE behavior
- [ ] Enums defined (ReviewRequestStatus, ReviewPriority, CorrectionType)

#### Confidence Scoring
- [ ] VLLM providers return confidence score (5-tuple)
- [ ] Confidence calculation uses schema coverage
- [ ] Confidence score persisted to ExtractionResult
- [ ] Confidence scores bounded [0.0, 1.0]

#### Threshold Configuration
- [ ] Global default threshold works (0.70)
- [ ] Tenant-level override works
- [ ] Schema-level override works
- [ ] Workflow-level override works (highest priority)
- [ ] Threshold resolution follows priority hierarchy

#### API Endpoints
- [ ] POST /jobs/{id}/request-review creates review
- [ ] GET /reviews/queue returns paginated, filtered results
- [ ] POST /reviews/{id}/assign updates assignment
- [ ] POST /reviews/{id}/start updates status to in_review
- [ ] POST /reviews/{id}/submit applies corrections
- [ ] GET /reviews/metrics returns accuracy metrics
- [ ] Permissions enforced (403 for unauthorized)
- [ ] Tenant isolation enforced (404 for cross-tenant access)

#### Conductor Integration
- [ ] HumanReviewWorker registered with Conductor
- [ ] Workflow with HUMAN task pauses at review
- [ ] Worker creates ReviewRequest in database
- [ ] Review completion updates Conductor task to COMPLETED
- [ ] Workflow resumes after review completion

#### End-to-End Flow
- [ ] Low confidence extraction triggers review
- [ ] Review assigned to user
- [ ] Corrections submitted and applied
- [ ] Extraction result updated with corrected data
- [ ] ReviewCorrection record created
- [ ] Extraction job marked completed

#### Multi-Tenancy
- [ ] Review queue filtered by tenant_id
- [ ] Cross-tenant assignment blocked (403)
- [ ] API tokens enforce tenant isolation
- [ ] Metrics scoped to tenant

#### SLA Tracking
- [ ] SLA deadline calculated based on priority
- [ ] Breached reviews detected by periodic task
- [ ] Breaches escalate to senior reviewers
- [ ] Escalation count tracked

#### Security & Audit
- [ ] Permissions enforced (reviews:read, reviews:update, etc.)
- [ ] PII not leaked in logs
- [ ] Audit trail complete (corrected_by_user_id, timestamps)
- [ ] Conductor task output sanitized

#### Performance
- [ ] Review queue query < 100ms (10K reviews)
- [ ] SLA check processes 5K+ reviews < 1s
- [ ] Concurrent submissions (100+) no deadlocks
- [ ] Indexes used (verify with EXPLAIN)

---

**Validation Complete:** All checkboxes ✅ means HITL implementation is production-ready!

---

## Appendix: File Locations

```
/Users/xavierau/Code/python/ai_document_processing/

# Models
app/models/review_request.py
app/models/review_correction.py
app/models/enums.py (additions)

# Services
app/services/hitl_service.py
app/services/conductor_hitl_service.py
app/services/vllm_service.py (modifications)

# API
app/api/reviews.py
app/schemas/review.py

# Workers
app/orchestration/workers/human_review_worker.py

# Migrations
alembic/versions/2025-12-02_add_hitl_tables.py

# Tests
tests/unit/services/test_hitl_service.py
tests/integration/api/test_reviews_api.py
```

---

**End of Document**
