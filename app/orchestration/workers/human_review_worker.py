"""
Human Review Worker for Conductor HUMAN Tasks.

This worker handles HUMAN tasks from Conductor workflows. When a workflow
reaches a HUMAN_REVIEW task, this worker:

1. Polls Conductor for HUMAN_REVIEW tasks
2. Creates a ReviewRequest in the database linking to Conductor task/workflow IDs
3. Returns IN_PROGRESS status (workflow pauses at this task)
4. When human completes review via API, ConductorHITLService updates the task
   to COMPLETED and the workflow resumes with corrected data

Key Behavior:
- Unlike other workers that return COMPLETED, this worker returns IN_PROGRESS
- The task remains open until explicitly completed via ConductorHITLService
- This implements the "callback" pattern for human-in-the-loop workflows

Conductor HUMAN Task Documentation:
- HUMAN tasks are a special task type for human intervention
- Worker creates the task context, returns IN_PROGRESS
- External system (our Review API) completes the task via Conductor API
- Workflow resumes with output data from the completion call
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone
from uuid import UUID

from conductor.client.worker.worker_task import WorkerTask

from .base_worker import BaseWorker
from app.database import SessionLocal
from app.models.review_request import ReviewRequest
from app.models.extraction_job import ExtractionJob
from app.models.enums import ReviewRequestStatus, ReviewPriority
import logging

logger = logging.getLogger(__name__)


class HumanReviewWorker(BaseWorker):
    """
    Worker that handles HUMAN tasks for document review.

    This worker implements the "callback" pattern for human-in-the-loop workflows:
    1. Creates ReviewRequest in database with Conductor task/workflow IDs
    2. Returns IN_PROGRESS status (workflow pauses)
    3. ConductorHITLService completes the task when review is submitted

    Input Parameters (from Conductor workflow):
    - extraction_job_id (str): ID of the extraction job requiring review
    - confidence_score (float): AI confidence score (0.0-1.0)
    - trigger_reason (str, optional): Reason for review request
    - conductor_task_id (str): Conductor task ID (auto-populated by workflow)
    - conductor_workflow_id (str): Conductor workflow ID (auto-populated by workflow)

    Output (when completed via ConductorHITLService):
    - review_request_id: ID of the created review request
    - corrected_data: Human-corrected extraction data
    - corrections_count: Number of corrections made
    - review_notes: Notes from reviewer
    - quality_score: Quality score from review

    Task remains IN_PROGRESS until human submits corrections.
    """

    # Default timeout for human review (4 hours)
    DEFAULT_TIMEOUT_SECONDS = 14400

    def __init__(self):
        super().__init__(task_definition_name="HUMAN_REVIEW", poll_interval=2000)

    def validate_input(self, task_input: Dict[str, Any]) -> Optional[str]:
        """
        Validate HUMAN task input parameters.

        SECURITY: tenant_id is required to enforce tenant isolation.
        """
        if "extraction_job_id" not in task_input:
            return "Missing required parameter: 'extraction_job_id'"

        # SECURITY: tenant_id is required for tenant isolation
        if "tenant_id" not in task_input:
            return "Missing required parameter: 'tenant_id' (required for security)"

        if "confidence_score" not in task_input:
            return "Missing required parameter: 'confidence_score'"

        try:
            confidence = float(task_input["confidence_score"])
            if not 0.0 <= confidence <= 1.0:
                return "Parameter 'confidence_score' must be between 0.0 and 1.0"
        except (ValueError, TypeError):
            return "Parameter 'confidence_score' must be a number"

        return None

    def execute(self, task: WorkerTask) -> Any:
        """
        Override execute to return IN_PROGRESS status for HUMAN tasks.

        This is the key difference from regular workers:
        - Regular workers return COMPLETED after execute_task()
        - HUMAN workers return IN_PROGRESS and wait for callback

        The workflow will pause at this task until ConductorHITLService
        calls the Conductor API to complete the task with review results.

        Args:
            task: Conductor WorkerTask object

        Returns:
            TaskResult with IN_PROGRESS status
        """
        task_result = self.get_task_result_from_task(task)
        task_id = task.task_id
        workflow_id = task.workflow_instance_id
        execution_start = datetime.now(timezone.utc)

        try:
            self._logger.info(
                f"Executing HUMAN_REVIEW task (task_id: {task_id}, workflow_id: {workflow_id})"
            )

            # Extract input data and add Conductor metadata
            task_input = task.input_data or {}
            task_input["conductor_task_id"] = task_id
            task_input["conductor_workflow_id"] = workflow_id

            self._logger.debug(f"Task input: {task_input}")

            # Validate input
            validation_error = self.validate_input(task_input)
            if validation_error:
                self._logger.error(f"Input validation failed: {validation_error}")
                task_result.status = "FAILED"
                task_result.reason_for_incompletion = validation_error
                task_result.add_output_data("error", validation_error)
                return task_result

            # Execute the task logic (creates ReviewRequest)
            output = self._create_review_request(task_input)

            # KEY: Return IN_PROGRESS instead of COMPLETED
            # This tells Conductor to keep the task open and wait for callback
            task_result.status = "IN_PROGRESS"
            task_result.add_output_data("review_request_id", output["review_request_id"])
            task_result.add_output_data("priority", output["priority"])
            task_result.add_output_data("sla_deadline", output["sla_deadline"])
            task_result.add_output_data("message", output["message"])
            task_result.add_output_data("callback_after_seconds", self.DEFAULT_TIMEOUT_SECONDS)

            execution_time = (datetime.now(timezone.utc) - execution_start).total_seconds()
            self._logger.info(
                f"HUMAN_REVIEW task initialized in {execution_time:.2f}s "
                f"(task_id: {task_id}, review_request_id: {output['review_request_id']})"
            )

        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - execution_start).total_seconds()
            error_msg = f"HUMAN_REVIEW task failed: {str(e)}"
            self._logger.error(
                f"HUMAN_REVIEW task failed after {execution_time:.2f}s "
                f"(task_id: {task_id}): {error_msg}",
                exc_info=True
            )

            task_result.status = "FAILED"
            task_result.reason_for_incompletion = error_msg
            task_result.add_output_data("error", error_msg)
            task_result.add_output_data("success", False)

        return task_result

    def execute_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delegate to _create_review_request for compatibility with base class.

        Note: For HUMAN tasks, we override execute() directly, so this method
        is only called if someone uses the base class pattern.
        """
        return self._create_review_request(task_input)

    def _create_review_request(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create ReviewRequest in database and return task output.

        This method creates a ReviewRequest record that links to the Conductor
        task and workflow IDs. When the human review is completed via the
        Review API, ConductorHITLService uses these IDs to complete the task.

        Args:
            task_input: Contains extraction_job_id, confidence_score, and Conductor metadata

        Returns:
            Dictionary with review_request_id, priority, sla_deadline, message

        Raises:
            ValueError: If extraction job not found
        """
        extraction_job_id = task_input["extraction_job_id"]
        tenant_id = task_input["tenant_id"]  # SECURITY: Required for tenant isolation
        confidence_score = float(task_input["confidence_score"])
        trigger_reason = task_input.get("trigger_reason", "low_confidence")
        conductor_task_id = task_input.get("conductor_task_id")
        conductor_workflow_id = task_input.get("conductor_workflow_id")

        self.log_info(
            f"Creating human review request for extraction job {extraction_job_id} "
            f"(tenant: {tenant_id}, confidence: {confidence_score:.2f}, task_id: {conductor_task_id})"
        )

        db = SessionLocal()
        try:
            # SECURITY: Query extraction job with tenant isolation
            extraction_job = db.query(ExtractionJob).filter(
                ExtractionJob.id == extraction_job_id,
                ExtractionJob.tenant_id == tenant_id  # CRITICAL: Tenant isolation
            ).first()

            if not extraction_job:
                raise ValueError(f"Extraction job not found: {extraction_job_id}")

            # SECURITY: Check if review request already exists (with tenant isolation)
            existing_review = db.query(ReviewRequest).filter(
                ReviewRequest.extraction_job_id == extraction_job_id,
                ReviewRequest.tenant_id == tenant_id  # CRITICAL: Tenant isolation
            ).first()

            if existing_review:
                self.log_warning(
                    f"Review request already exists for job {extraction_job_id}: "
                    f"{existing_review.id}"
                )
                # Update Conductor IDs if not set (idempotency)
                if not existing_review.conductor_task_id and conductor_task_id:
                    existing_review.conductor_task_id = conductor_task_id
                    existing_review.conductor_workflow_id = conductor_workflow_id
                    existing_review.updated_at = datetime.now(timezone.utc)
                    db.commit()
                    db.refresh(existing_review)

                return {
                    "review_request_id": str(existing_review.id),
                    "priority": existing_review.priority,
                    "sla_deadline": existing_review.sla_deadline.isoformat(),
                    "message": "Review request already exists, linked to Conductor task",
                }

            # Determine priority based on confidence score
            priority = self._determine_priority(confidence_score)

            # Calculate SLA deadline
            sla_deadline = ReviewRequest.calculate_sla_deadline(priority)

            # Create review request with Conductor metadata
            review_request = ReviewRequest(
                tenant_id=extraction_job.tenant_id,
                extraction_job_id=extraction_job_id,
                status=ReviewRequestStatus.PENDING.value,
                priority=priority.value,
                confidence_score=confidence_score,
                trigger_reason=trigger_reason,
                conductor_task_id=conductor_task_id,
                conductor_workflow_id=conductor_workflow_id,
                sla_deadline=sla_deadline,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            db.add(review_request)
            db.commit()
            db.refresh(review_request)

            self.log_info(
                f"Review request created: {review_request.id} "
                f"(priority: {priority.value}, SLA: {sla_deadline}, "
                f"conductor_task_id: {conductor_task_id})"
            )

            return {
                "review_request_id": str(review_request.id),
                "priority": priority.value,
                "sla_deadline": sla_deadline.isoformat(),
                "message": "Review request created, awaiting human input",
            }

        except Exception as e:
            db.rollback()
            self.log_error(f"Failed to create review request: {str(e)}", exc_info=True)
            raise
        finally:
            db.close()

    def _determine_priority(self, confidence_score: float) -> ReviewPriority:
        """
        Determine review priority based on confidence score.

        Priority thresholds (configurable via tenant settings in future):
        - CRITICAL: < 0.30
        - HIGH: 0.30-0.50
        - NORMAL: 0.50-0.60
        - LOW: 0.60-0.70

        Args:
            confidence_score: AI confidence score (0.0-1.0)

        Returns:
            ReviewPriority enum value
        """
        if confidence_score < 0.30:
            return ReviewPriority.CRITICAL
        elif confidence_score < 0.50:
            return ReviewPriority.HIGH
        elif confidence_score < 0.60:
            return ReviewPriority.NORMAL
        else:
            return ReviewPriority.LOW
