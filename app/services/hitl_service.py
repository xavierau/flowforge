"""
HITL (Human-in-the-Loop) Service for review management.

This service implements the core business logic for the human review system:
- Threshold-based routing
- Review request creation and management
- Correction application
- SLA monitoring

SECURITY: All methods enforce tenant isolation. Never bypass tenant_id checks.
"""

import logging
import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple, Set
from uuid import UUID

from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session
import jsonpath_ng

from app.models.review_request import ReviewRequest
from app.models.review_correction import ReviewCorrection
from app.models.extraction_job import ExtractionJob
from app.models.extraction_result import ExtractionResult
from app.models.tenant import Tenant
from app.models.schema_definition import SchemaDefinition
from app.models.enums import (
    ReviewRequestStatus,
    ReviewPriority,
    CorrectionType,
    JobStatus
)
from app.services.conductor_hitl_service import ConductorHITLService

logger = logging.getLogger(__name__)

# JSONPath validation pattern - allows alphanumeric, dots, brackets with numbers/strings
SAFE_JSONPATH_PATTERN = re.compile(
    r'^[a-zA-Z_$][a-zA-Z0-9_$]*(\.[a-zA-Z_$][a-zA-Z0-9_$]*|\[\d+\]|\[\'[a-zA-Z0-9_$]+\'\]|\[\"[a-zA-Z0-9_$]+\"\])*$'
)


class HITLService:
    """
    Human-in-the-Loop service for managing review requests and corrections.

    Follows SOLID principles:
    - Single Responsibility: Manages only HITL review lifecycle
    - Open/Closed: Extendable for new correction types without modification
    - Liskov Substitution: Can be mocked/stubbed for testing
    - Interface Segregation: Clean method signatures with clear contracts
    - Dependency Inversion: Depends on DB session abstraction
    """

    DEFAULT_AUTO_APPROVE_THRESHOLD = 0.70
    DEFAULT_CRITICAL_THRESHOLD = 0.30
    DEFAULT_HIGH_THRESHOLD = 0.50
    DEFAULT_NORMAL_THRESHOLD = 0.60
    DEFAULT_LOW_THRESHOLD = 0.70

    def __init__(self, db: Session):
        """
        Initialize HITL service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    @staticmethod
    def _validate_field_path(field_path: str) -> bool:
        """
        Validate that a field path is safe for JSONPath parsing.

        Prevents JSONPath injection attacks by only allowing safe characters.

        Args:
            field_path: The field path to validate

        Returns:
            bool: True if valid, False otherwise
        """
        if not field_path or len(field_path) > 500:
            return False
        return bool(SAFE_JSONPATH_PATTERN.match(field_path))

    def should_request_review(
        self,
        extraction_job: ExtractionJob,
        workflow_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Determine if an extraction job requires human review based on confidence threshold.

        Threshold resolution (cascading priority):
        1. Workflow node configuration (highest priority)
        2. Schema-specific threshold
        3. Tenant-specific threshold
        4. Global default threshold (0.70)

        Args:
            extraction_job: The extraction job to evaluate
            workflow_config: Optional workflow node configuration

        Returns:
            bool: True if review is needed, False if auto-approved
        """
        if extraction_job.confidence_score is None:
            logger.warning(
                f"Job {extraction_job.id} has no confidence score, requesting review"
            )
            return True

        # Resolve threshold using cascading configuration
        threshold = self._resolve_threshold(extraction_job, workflow_config)

        logger.info(
            f"Job {extraction_job.id}: confidence={extraction_job.confidence_score:.3f}, "
            f"threshold={threshold:.3f}"
        )

        return extraction_job.confidence_score < threshold

    def _resolve_threshold(
        self,
        extraction_job: ExtractionJob,
        workflow_config: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Resolve confidence threshold using cascading configuration.

        Priority: Workflow > Schema > Tenant > Default

        Args:
            extraction_job: The extraction job
            workflow_config: Optional workflow configuration

        Returns:
            float: Resolved threshold value (0.0-1.0)
        """
        # Priority 1: Workflow node configuration
        if workflow_config and "confidence_threshold" in workflow_config:
            threshold = workflow_config["confidence_threshold"]
            logger.debug(f"Using workflow threshold: {threshold}")
            return threshold

        # Priority 2: Schema-specific threshold
        if extraction_job.schema_definition_id:
            schema = self.db.query(SchemaDefinition).filter(
                SchemaDefinition.id == extraction_job.schema_definition_id
            ).first()
            if schema and schema.hitl_threshold is not None:
                logger.debug(f"Using schema threshold: {schema.hitl_threshold}")
                return schema.hitl_threshold

        # Priority 3: Tenant-specific threshold
        tenant = self.db.query(Tenant).filter(
            Tenant.id == extraction_job.tenant_id
        ).first()
        if tenant:
            threshold = tenant.hitl_auto_approve_threshold
            logger.debug(f"Using tenant threshold: {threshold}")
            return threshold

        # Priority 4: Global default
        logger.debug(f"Using default threshold: {self.DEFAULT_AUTO_APPROVE_THRESHOLD}")
        return self.DEFAULT_AUTO_APPROVE_THRESHOLD

    def create_review_request(
        self,
        extraction_job_id: UUID,
        tenant_id: UUID,
        trigger_reason: str = "low_confidence",
        conductor_task_id: Optional[str] = None,
        conductor_workflow_id: Optional[str] = None
    ) -> ReviewRequest:
        """
        Create a new review request for an extraction job.

        SECURITY: Enforces tenant isolation by requiring and validating tenant_id.

        Args:
            extraction_job_id: ID of the extraction job to review
            tenant_id: Tenant ID for isolation (REQUIRED)
            trigger_reason: Reason for review request
            conductor_task_id: Optional Conductor HUMAN task ID
            conductor_workflow_id: Optional Conductor workflow execution ID

        Returns:
            ReviewRequest: Created review request

        Raises:
            ValueError: If job not found, belongs to different tenant, or already has a review request
        """
        # Query current job state from DB with tenant isolation
        job = self.db.query(ExtractionJob).filter(
            ExtractionJob.id == extraction_job_id,
            ExtractionJob.tenant_id == tenant_id  # SECURITY: Tenant isolation
        ).first()

        if not job:
            raise ValueError(f"Extraction job {extraction_job_id} not found or access denied")

        # Check if review already exists
        existing_review = self.db.query(ReviewRequest).filter(
            ReviewRequest.extraction_job_id == extraction_job_id
        ).first()
        if existing_review:
            raise ValueError(
                f"Review request already exists for job {extraction_job_id}"
            )

        # Calculate priority based on confidence score
        priority = self._calculate_priority(job)

        # Calculate SLA deadline
        sla_deadline = ReviewRequest.calculate_sla_deadline(priority)

        # Create review request
        review_request = ReviewRequest(
            tenant_id=job.tenant_id,
            extraction_job_id=extraction_job_id,
            status=ReviewRequestStatus.PENDING.value,
            priority=priority.value,
            confidence_score=job.confidence_score or 0.0,
            trigger_reason=trigger_reason,
            conductor_task_id=conductor_task_id,
            conductor_workflow_id=conductor_workflow_id,
            sla_deadline=sla_deadline,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.db.add(review_request)
        self.db.commit()
        self.db.refresh(review_request)

        logger.info(
            f"Created review request {review_request.id} for job {extraction_job_id}, "
            f"priority={priority.value}, confidence={job.confidence_score}"
        )

        return review_request

    def _calculate_priority(self, extraction_job: ExtractionJob) -> ReviewPriority:
        """
        Calculate review priority based on confidence score and tenant thresholds.

        Args:
            extraction_job: The extraction job

        Returns:
            ReviewPriority: Calculated priority level
        """
        confidence = extraction_job.confidence_score or 0.0

        # Get tenant thresholds
        tenant = self.db.query(Tenant).filter(
            Tenant.id == extraction_job.tenant_id
        ).first()

        if not tenant:
            # Use defaults if tenant not found
            critical = self.DEFAULT_CRITICAL_THRESHOLD
            high = self.DEFAULT_HIGH_THRESHOLD
            normal = self.DEFAULT_NORMAL_THRESHOLD
            low = self.DEFAULT_LOW_THRESHOLD
        else:
            critical = tenant.hitl_critical_threshold
            high = tenant.hitl_high_threshold
            normal = tenant.hitl_normal_threshold
            low = tenant.hitl_low_threshold

        # Determine priority
        if confidence < critical:
            return ReviewPriority.CRITICAL
        elif confidence < high:
            return ReviewPriority.HIGH
        elif confidence < normal:
            return ReviewPriority.NORMAL
        else:
            return ReviewPriority.LOW

    def get_review_queue(
        self,
        tenant_id: UUID,
        status: Optional[ReviewRequestStatus] = None,
        priority: Optional[ReviewPriority] = None,
        assigned_to_user_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[ReviewRequest], int]:
        """
        Get paginated review queue with filters.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            status: Optional status filter
            priority: Optional priority filter
            assigned_to_user_id: Optional assignee filter
            page: Page number (1-indexed)
            page_size: Number of items per page (max 100)

        Returns:
            Tuple of (review_requests, total_count)
        """
        # Enforce tenant isolation
        query = self.db.query(ReviewRequest).filter(
            ReviewRequest.tenant_id == tenant_id
        )

        # Apply filters
        if status:
            query = query.filter(ReviewRequest.status == status.value)
        if priority:
            query = query.filter(ReviewRequest.priority == priority.value)
        if assigned_to_user_id:
            query = query.filter(
                ReviewRequest.assigned_to_user_id == assigned_to_user_id
            )

        # Get total count
        total_count = query.count()

        # Apply pagination and sorting
        page_size = min(page_size, 100)  # Max 100 per page
        offset = (page - 1) * page_size

        reviews = query.order_by(
            ReviewRequest.priority.desc(),  # Critical first
            ReviewRequest.created_at.asc()  # Oldest first (FIFO)
        ).offset(offset).limit(page_size).all()

        return reviews, total_count

    def assign_review(
        self,
        review_id: UUID,
        tenant_id: UUID,
        assigned_to_user_id: UUID,
        current_user_id: UUID
    ) -> ReviewRequest:
        """
        Assign a review request to a user.

        SECURITY: Enforces tenant isolation by requiring and validating tenant_id.

        Args:
            review_id: Review request ID
            tenant_id: Tenant ID for isolation (REQUIRED)
            assigned_to_user_id: User ID to assign to
            current_user_id: Current user performing the assignment

        Returns:
            ReviewRequest: Updated review request

        Raises:
            ValueError: If review not found, belongs to different tenant, or in invalid state
        """
        review = self.db.query(ReviewRequest).filter(
            ReviewRequest.id == review_id,
            ReviewRequest.tenant_id == tenant_id  # SECURITY: Tenant isolation
        ).first()

        if not review:
            raise ValueError(f"Review request {review_id} not found or access denied")

        if review.status not in [
            ReviewRequestStatus.PENDING.value,
            ReviewRequestStatus.ASSIGNED.value
        ]:
            raise ValueError(
                f"Cannot assign review in status {review.status}"
            )

        # Update assignment
        review.assigned_to_user_id = assigned_to_user_id
        review.status = ReviewRequestStatus.ASSIGNED.value
        review.assigned_at = datetime.utcnow()
        review.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(review)

        logger.info(
            f"Assigned review {review_id} to user {assigned_to_user_id} "
            f"by user {current_user_id}"
        )

        return review

    def start_review(
        self,
        review_id: UUID,
        tenant_id: UUID,
        current_user_id: UUID
    ) -> ReviewRequest:
        """
        Mark a review as started (in_review status).

        SECURITY: Enforces tenant isolation by requiring and validating tenant_id.

        Args:
            review_id: Review request ID
            tenant_id: Tenant ID for isolation (REQUIRED)
            current_user_id: User starting the review

        Returns:
            ReviewRequest: Updated review request

        Raises:
            ValueError: If review not found, belongs to different tenant, or in invalid state
        """
        review = self.db.query(ReviewRequest).filter(
            ReviewRequest.id == review_id,
            ReviewRequest.tenant_id == tenant_id  # SECURITY: Tenant isolation
        ).first()

        if not review:
            raise ValueError(f"Review request {review_id} not found or access denied")

        if review.status != ReviewRequestStatus.ASSIGNED.value:
            raise ValueError(
                f"Cannot start review in status {review.status}"
            )

        if review.assigned_to_user_id != current_user_id:
            raise ValueError(
                f"Review is assigned to another user"
            )

        # Update to in_review
        review.status = ReviewRequestStatus.IN_REVIEW.value
        review.started_at = datetime.utcnow()
        review.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(review)

        logger.info(f"Started review {review_id} by user {current_user_id}")

        return review

    def submit_corrections(
        self,
        review_id: UUID,
        tenant_id: UUID,
        corrections: List[Dict[str, Any]],
        corrected_by_user_id: UUID,
        review_notes: Optional[str] = None
    ) -> ReviewRequest:
        """
        Submit corrections for a review and mark as completed.

        SECURITY: Enforces tenant isolation and validates extraction_result ownership.

        Args:
            review_id: Review request ID
            tenant_id: Tenant ID for isolation (REQUIRED)
            corrections: List of correction dicts with keys:
                - extraction_result_id: UUID
                - field_path: str (JSONPath)
                - original_value: Any
                - corrected_value: Any
                - correction_type: CorrectionType
                - correction_notes: Optional[str]
            corrected_by_user_id: User submitting corrections
            review_notes: Optional overall review notes

        Returns:
            ReviewRequest: Completed review request

        Raises:
            ValueError: If review not found, belongs to different tenant, or in invalid state
            ValueError: If field_path contains invalid characters (JSONPath injection prevention)
            ValueError: If extraction_result_id belongs to different tenant
        """
        # Query current review state with tenant isolation
        review = self.db.query(ReviewRequest).filter(
            ReviewRequest.id == review_id,
            ReviewRequest.tenant_id == tenant_id  # SECURITY: Tenant isolation
        ).first()

        if not review:
            raise ValueError(f"Review request {review_id} not found or access denied")

        if review.status != ReviewRequestStatus.IN_REVIEW.value:
            raise ValueError(
                f"Cannot submit corrections for review in status {review.status}"
            )

        if review.assigned_to_user_id != corrected_by_user_id:
            raise ValueError(
                f"Review is assigned to another user"
            )

        # SECURITY: Validate all field_paths before processing
        for correction_data in corrections:
            field_path = correction_data.get("field_path", "")
            if not self._validate_field_path(field_path):
                raise ValueError(
                    f"Invalid field_path: {field_path}. Only alphanumeric characters, "
                    "dots, and bracket notation allowed."
                )

        # PERFORMANCE: Prefetch all extraction results to avoid N+1 queries
        result_ids: Set[UUID] = {
            correction_data["extraction_result_id"]
            for correction_data in corrections
            if correction_data.get("extraction_result_id")
        }

        # SECURITY: Validate all extraction_results belong to tenant
        valid_results = self.db.query(ExtractionResult).join(
            ExtractionJob,
            ExtractionResult.extraction_job_id == ExtractionJob.id
        ).filter(
            ExtractionResult.id.in_(result_ids),
            ExtractionJob.tenant_id == tenant_id  # SECURITY: Tenant isolation
        ).all()

        results_map = {str(r.id): r for r in valid_results}

        # Verify all result_ids are valid for this tenant
        invalid_ids = result_ids - {UUID(rid) for rid in results_map.keys()}
        if invalid_ids:
            raise ValueError(
                f"Invalid extraction_result_id(s): {invalid_ids}. "
                "Results not found or access denied."
            )

        try:
            # Create correction records
            for correction_data in corrections:
                result_id_str = str(correction_data["extraction_result_id"])
                result = results_map.get(result_id_str)

                correction = ReviewCorrection(
                    review_request_id=review_id,
                    extraction_result_id=correction_data["extraction_result_id"],
                    corrected_by_user_id=corrected_by_user_id,
                    field_path=correction_data["field_path"],
                    original_value=correction_data.get("original_value"),
                    corrected_value=correction_data.get("corrected_value"),
                    correction_type=correction_data["correction_type"],
                    correction_notes=correction_data.get("correction_notes"),
                    created_at=datetime.utcnow()
                )
                self.db.add(correction)

                # Apply correction to extraction result (already validated)
                if result:
                    self._apply_correction_to_result(result, correction)

            # Update review status
            review.status = ReviewRequestStatus.COMPLETED.value
            review.completed_at = datetime.utcnow()
            review.updated_at = datetime.utcnow()
            if review_notes:
                review.review_notes = review_notes

            # Update extraction job status
            job = self.db.query(ExtractionJob).filter(
                ExtractionJob.id == review.extraction_job_id
            ).first()
            if job and job.status != JobStatus.COMPLETED.value:
                job.status = JobStatus.COMPLETED.value
                job.completed_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(review)

            logger.info(
                f"Submitted {len(corrections)} corrections for review {review_id}"
            )

            # Complete Conductor HUMAN task if this review is Conductor-initiated
            if review.conductor_task_id:
                try:
                    conductor_service = ConductorHITLService()
                    result = conductor_service.complete_conductor_task(
                        review_id=review_id,
                        db=self.db,
                        fail_workflow_on_error=False
                    )
                    if result.success:
                        logger.info(
                            f"Conductor task {review.conductor_task_id} completed "
                            f"for review {review_id}"
                        )
                    else:
                        logger.warning(
                            f"Failed to complete Conductor task {review.conductor_task_id}: "
                            f"{result.error_message}. Review is still completed locally."
                        )
                except Exception as conductor_error:
                    # Log but don't fail - the review is already committed
                    logger.error(
                        f"Error completing Conductor task for review {review_id}: "
                        f"{conductor_error}. Review is still completed locally."
                    )

            return review

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to submit corrections for review {review_id}: {e}")
            raise

    def _apply_correction_to_result(
        self,
        extraction_result: ExtractionResult,
        correction: ReviewCorrection
    ) -> None:
        """
        Apply a correction to an extraction result using JSONPath.

        Args:
            extraction_result: The extraction result to modify
            correction: The correction to apply
        """
        if not extraction_result.extracted_data:
            extraction_result.extracted_data = {}

        data = extraction_result.extracted_data

        # Parse JSONPath
        try:
            # Use jsonpath_ng for robust JSONPath support
            path_expr = jsonpath_ng.parse(correction.field_path)

            if correction.correction_type == CorrectionType.VALUE_CHANGE.value:
                # Update existing field
                path_expr.update(data, correction.corrected_value)
            elif correction.correction_type == CorrectionType.FIELD_ADDITION.value:
                # Add new field
                path_expr.update(data, correction.corrected_value)
            elif correction.correction_type == CorrectionType.FIELD_REMOVAL.value:
                # Remove field (set to None or remove from dict)
                # This is a simplified approach - actual implementation may vary
                path_expr.update(data, None)
            elif correction.correction_type == CorrectionType.TYPE_CORRECTION.value:
                # Correct data type
                path_expr.update(data, correction.corrected_value)

            extraction_result.extracted_data = data
            extraction_result.updated_at = datetime.utcnow()

            logger.debug(
                f"Applied correction to field {correction.field_path} "
                f"in result {extraction_result.id}"
            )

        except Exception as e:
            logger.error(
                f"Failed to apply correction to field {correction.field_path}: {e}"
            )
            raise

    def check_sla_breaches(self) -> List[ReviewRequest]:
        """
        Find and escalate reviews that have breached their SLA deadlines.

        Returns:
            List[ReviewRequest]: Reviews that were escalated
        """
        now = datetime.utcnow()

        # Find breached reviews
        breached_reviews = self.db.query(ReviewRequest).filter(
            and_(
                ReviewRequest.status.in_([
                    ReviewRequestStatus.PENDING.value,
                    ReviewRequestStatus.ASSIGNED.value,
                    ReviewRequestStatus.IN_REVIEW.value
                ]),
                ReviewRequest.sla_deadline < now
            )
        ).all()

        escalated = []
        for review in breached_reviews:
            review.status = ReviewRequestStatus.ESCALATED.value
            review.updated_at = now
            escalated.append(review)

            logger.warning(
                f"SLA breach detected for review {review.id}, "
                f"deadline was {review.sla_deadline}"
            )

        if escalated:
            self.db.commit()
            logger.info(f"Escalated {len(escalated)} reviews due to SLA breach")

        return escalated

    def calculate_review_metrics(
        self,
        tenant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate review metrics for a tenant.

        Args:
            tenant_id: Tenant ID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict with metrics:
                - total_reviews: int
                - completed_reviews: int
                - avg_review_time_minutes: float
                - sla_breach_rate: float
                - top_corrected_fields: List[Tuple[str, int]]
                - accuracy_rate: float
        """
        query = self.db.query(ReviewRequest).filter(
            ReviewRequest.tenant_id == tenant_id
        )

        if start_date:
            query = query.filter(ReviewRequest.created_at >= start_date)
        if end_date:
            query = query.filter(ReviewRequest.created_at <= end_date)

        reviews = query.all()
        total_reviews = len(reviews)

        completed_reviews = [
            r for r in reviews
            if r.status == ReviewRequestStatus.COMPLETED.value
        ]
        completed_count = len(completed_reviews)

        # Calculate average review time
        review_times = []
        for review in completed_reviews:
            if review.started_at and review.completed_at:
                delta = review.completed_at - review.started_at
                review_times.append(delta.total_seconds() / 60)  # minutes

        avg_review_time = (
            sum(review_times) / len(review_times)
            if review_times else 0
        )

        # Calculate SLA breach rate
        breached = [r for r in reviews if r.status == ReviewRequestStatus.ESCALATED.value]
        sla_breach_rate = (
            len(breached) / total_reviews
            if total_reviews > 0 else 0
        )

        # Find most corrected fields
        corrections = self.db.query(ReviewCorrection).join(
            ReviewRequest
        ).filter(
            ReviewRequest.tenant_id == tenant_id
        ).all()

        field_counts: Dict[str, int] = {}
        for correction in corrections:
            field_counts[correction.field_path] = (
                field_counts.get(correction.field_path, 0) + 1
            )

        top_corrected_fields = sorted(
            field_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        # Calculate accuracy rate (inverse of correction rate)
        total_corrections = len(corrections)
        accuracy_rate = (
            1.0 - (total_corrections / (total_reviews * 10))  # Assume ~10 fields per review
            if total_reviews > 0 else 1.0
        )
        accuracy_rate = max(0.0, min(1.0, accuracy_rate))  # Clamp 0-1

        return {
            "total_reviews": total_reviews,
            "completed_reviews": completed_count,
            "avg_review_time_minutes": round(avg_review_time, 2),
            "sla_breach_rate": round(sla_breach_rate, 4),
            "top_corrected_fields": top_corrected_fields,
            "accuracy_rate": round(accuracy_rate, 4)
        }

    def cancel_review(
        self,
        review_id: UUID,
        tenant_id: UUID,
        current_user_id: UUID,
        reason: Optional[str] = None
    ) -> ReviewRequest:
        """
        Cancel a review request.

        SECURITY: Enforces tenant isolation by requiring and validating tenant_id.

        Args:
            review_id: Review request ID
            tenant_id: Tenant ID for isolation (REQUIRED)
            current_user_id: User cancelling the review
            reason: Optional cancellation reason

        Returns:
            ReviewRequest: Cancelled review request

        Raises:
            ValueError: If review not found, belongs to different tenant, or already completed
        """
        review = self.db.query(ReviewRequest).filter(
            ReviewRequest.id == review_id,
            ReviewRequest.tenant_id == tenant_id  # SECURITY: Tenant isolation
        ).first()

        if not review:
            raise ValueError(f"Review request {review_id} not found or access denied")

        if review.status == ReviewRequestStatus.COMPLETED.value:
            raise ValueError("Cannot cancel a completed review")

        review.status = ReviewRequestStatus.CANCELLED.value
        review.updated_at = datetime.utcnow()
        if reason:
            review.review_notes = f"Cancelled: {reason}"

        self.db.commit()
        self.db.refresh(review)

        logger.info(
            f"Cancelled review {review_id} by user {current_user_id}"
        )

        return review

    def escalate_review(
        self,
        review_id: UUID,
        tenant_id: UUID,
        current_user_id: UUID,
        reason: str
    ) -> ReviewRequest:
        """
        Manually escalate a review request.

        SECURITY: Enforces tenant isolation by requiring and validating tenant_id.

        Args:
            review_id: Review request ID
            tenant_id: Tenant ID for isolation (REQUIRED)
            current_user_id: User escalating the review
            reason: Escalation reason (REQUIRED)

        Returns:
            ReviewRequest: Escalated review request

        Raises:
            ValueError: If review not found, belongs to different tenant, or already completed
        """
        review = self.db.query(ReviewRequest).filter(
            ReviewRequest.id == review_id,
            ReviewRequest.tenant_id == tenant_id  # SECURITY: Tenant isolation
        ).first()

        if not review:
            raise ValueError(f"Review request {review_id} not found or access denied")

        if review.status == ReviewRequestStatus.COMPLETED.value:
            raise ValueError("Cannot escalate a completed review")

        if review.status == ReviewRequestStatus.CANCELLED.value:
            raise ValueError("Cannot escalate a cancelled review")

        # Update to escalated
        review.status = ReviewRequestStatus.ESCALATED.value
        review.updated_at = datetime.utcnow()
        review.escalation_count = (review.escalation_count or 0) + 1

        # Append escalation reason to notes
        existing_notes = review.review_notes or ""
        review.review_notes = f"{existing_notes}\n[ESCALATED by {current_user_id}]: {reason}".strip()

        self.db.commit()
        self.db.refresh(review)

        logger.warning(
            f"Escalated review {review_id} by user {current_user_id}: {reason}"
        )

        return review
