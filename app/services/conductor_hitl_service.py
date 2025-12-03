"""
Conductor HITL Service

Provides integration between the HITL review system and Netflix Conductor workflows.
Handles completing HUMAN tasks when reviews are submitted, with retry logic and
comprehensive error handling.

Key Responsibilities:
1. Complete Conductor HUMAN tasks when reviews are submitted
2. Pass corrected data back to the workflow
3. Handle Conductor unavailability gracefully
4. Provide retry logic with exponential backoff
5. Track task completion status for monitoring

Integration Flow:
1. HumanReviewWorker creates ReviewRequest, returns IN_PROGRESS
2. Human submits review via Review API
3. Review API calls HITLService.submit_corrections()
4. HITLService calls ConductorHITLService.complete_conductor_task()
5. ConductorHITLService updates Conductor task status to COMPLETED
6. Workflow resumes with corrected_data in task output
"""

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from sqlalchemy.orm import Session

from app.models.review_request import ReviewRequest
from app.models.review_correction import ReviewCorrection
from app.models.extraction_result import ExtractionResult
from app.models.extraction_job import ExtractionJob
from app.models.enums import ReviewRequestStatus

logger = logging.getLogger(__name__)


class ConductorTaskStatus(str, Enum):
    """Conductor task status values."""
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    FAILED_WITH_TERMINAL_ERROR = "FAILED_WITH_TERMINAL_ERROR"
    TIMED_OUT = "TIMED_OUT"


@dataclass
class TaskCompletionResult:
    """Result of task completion attempt."""
    success: bool
    task_id: str
    workflow_id: str
    status: str
    error_message: Optional[str] = None
    retry_count: int = 0
    response_code: Optional[int] = None


class ConductorHITLService:
    """
    Service for integrating HITL reviews with Conductor workflows.

    This service handles:
    1. Completing Conductor HUMAN tasks when reviews are submitted
    2. Updating task status via Conductor REST API with retry logic
    3. Passing corrected data back to the workflow
    4. Error handling when Conductor is unavailable
    5. Workflow status monitoring
    6. Task timeout handling

    SOLID Principles:
    - SRP: Single responsibility - Conductor task completion
    - DIP: Depends on abstractions (Session, not concrete DB implementations)
    """

    # Default configuration
    DEFAULT_TIMEOUT_SECONDS = 30
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_BACKOFF_FACTOR = 0.5  # 0.5s, 1s, 2s backoff
    DEFAULT_RETRY_STATUS_CODES = [500, 502, 503, 504]

    def __init__(
        self,
        conductor_url: Optional[str] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_backoff_factor: float = DEFAULT_RETRY_BACKOFF_FACTOR,
    ):
        """
        Initialize Conductor HITL service.

        Args:
            conductor_url: Conductor server URL (default: from env or localhost:8080)
            timeout_seconds: Request timeout in seconds
            max_retries: Maximum retry attempts
            retry_backoff_factor: Exponential backoff factor
        """
        self.conductor_url = conductor_url or os.getenv(
            "CONDUCTOR_SERVER_URL",
            "http://localhost:8080/api"
        )
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor

        # Configure session with retry logic
        self._session = self._create_session_with_retries()

        # API endpoints
        self.task_update_endpoint = f"{self.conductor_url}/tasks"
        self.workflow_endpoint = f"{self.conductor_url}/workflow"

        logger.info(
            f"ConductorHITLService initialized "
            f"(URL: {self.conductor_url}, timeout: {timeout_seconds}s, "
            f"max_retries: {max_retries})"
        )

    def _create_session_with_retries(self) -> requests.Session:
        """
        Create requests session with automatic retry logic.

        Returns:
            Configured requests.Session
        """
        session = requests.Session()

        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.retry_backoff_factor,
            status_forcelist=self.DEFAULT_RETRY_STATUS_CODES,
            allowed_methods=["GET", "POST", "PUT"],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def complete_conductor_task(
        self,
        review_id: UUID,
        db: Session,
        fail_workflow_on_error: bool = False,
    ) -> TaskCompletionResult:
        """
        Complete Conductor HUMAN task after review is submitted.

        This method is called when a human submits review corrections.
        It updates the Conductor task status to COMPLETED and passes the
        corrected data back to the workflow.

        Args:
            review_id: ID of the completed review request
            db: Database session
            fail_workflow_on_error: If True, fail the task on error; else keep IN_PROGRESS

        Returns:
            TaskCompletionResult with success status and details

        Raises:
            ValueError: If review request not found or missing Conductor metadata
        """
        # Query review request with corrections
        review_request = db.query(ReviewRequest).filter(
            ReviewRequest.id == review_id
        ).first()

        if not review_request:
            raise ValueError(f"Review request not found: {review_id}")

        # Check if review is Conductor-initiated
        if not review_request.conductor_task_id:
            logger.info(
                f"Review {review_id} is not Conductor-initiated, skipping task update"
            )
            return TaskCompletionResult(
                success=True,
                task_id="",
                workflow_id="",
                status="NOT_CONDUCTOR_TASK",
                error_message="Review is not Conductor-initiated",
            )

        if not review_request.conductor_workflow_id:
            raise ValueError(
                f"Review {review_id} has conductor_task_id but missing conductor_workflow_id"
            )

        task_id = review_request.conductor_task_id
        workflow_id = review_request.conductor_workflow_id

        # Prepare task update payload
        task_update = self._prepare_task_update(review_request, db)

        # Update Conductor task with retry logic
        result = self._update_conductor_task_with_retry(
            task_update=task_update,
            task_id=task_id,
            workflow_id=workflow_id,
        )

        if result.success:
            logger.info(
                f"Successfully completed Conductor task {task_id} "
                f"for review {review_id} (retries: {result.retry_count})"
            )
        else:
            logger.error(
                f"Failed to complete Conductor task {task_id} "
                f"for review {review_id}: {result.error_message}"
            )

            # Optionally fail the task in Conductor
            if fail_workflow_on_error:
                self._fail_conductor_task(
                    task_id=task_id,
                    workflow_id=workflow_id,
                    reason=result.error_message or "Task completion failed",
                )

        return result

    def _prepare_task_update(
        self,
        review_request: ReviewRequest,
        db: Session
    ) -> Dict[str, Any]:
        """
        Prepare task update payload for Conductor.

        Args:
            review_request: ReviewRequest with completed review
            db: Database session

        Returns:
            Dictionary with task update data
        """
        # Query corrections for this review
        corrections = db.query(ReviewCorrection).filter(
            ReviewCorrection.review_request_id == review_request.id
        ).all()

        # Query extraction result to get corrected data
        extraction_result = None
        corrected_data = None

        if corrections:
            extraction_result = db.query(ExtractionResult).filter(
                ExtractionResult.id == corrections[0].extraction_result_id
            ).first()

            if extraction_result:
                # Use the updated extracted_data which contains corrections
                corrected_data = extraction_result.extracted_data

        # Calculate quality score based on corrections
        quality_score = self._calculate_quality_score(
            corrections_count=len(corrections),
            confidence_score=review_request.confidence_score,
        )

        # Prepare output data
        output_data = {
            "review_request_id": str(review_request.id),
            "review_status": review_request.status,
            "corrections_count": len(corrections),
            "review_notes": review_request.review_notes,
            "completed_at": (
                review_request.completed_at.isoformat()
                if review_request.completed_at else None
            ),
            "quality_score": quality_score,
            "corrected_data": corrected_data,
        }

        # Add extraction result ID if available
        if extraction_result:
            output_data["extraction_result_id"] = str(extraction_result.id)

        # Add correction details for downstream processing
        if corrections:
            output_data["corrections"] = [
                {
                    "field_path": c.field_path,
                    "original_value": c.original_value,
                    "corrected_value": c.corrected_value,
                    "correction_type": c.correction_type,
                    "correction_notes": c.correction_notes,
                }
                for c in corrections
            ]

        # Build task update payload
        task_update = {
            "workflowInstanceId": review_request.conductor_workflow_id,
            "taskId": review_request.conductor_task_id,
            "status": ConductorTaskStatus.COMPLETED.value,
            "outputData": output_data,
        }

        return task_update

    def _calculate_quality_score(
        self,
        corrections_count: int,
        confidence_score: Optional[float],
    ) -> float:
        """
        Calculate quality score based on review metrics.

        The quality score indicates extraction accuracy:
        - 1.0 = No corrections needed
        - Lower scores indicate more corrections

        Args:
            corrections_count: Number of corrections made
            confidence_score: Original AI confidence score

        Returns:
            Quality score between 0.0 and 1.0
        """
        if corrections_count == 0:
            return 1.0

        # Base quality on original confidence and correction count
        base_confidence = confidence_score or 0.5

        # Each correction reduces quality (diminishing returns)
        # Formula: quality = confidence * (1 - corrections_penalty)
        # where penalty approaches 0.5 as corrections increase
        corrections_penalty = min(0.5, corrections_count * 0.05)
        quality = base_confidence * (1 - corrections_penalty)

        return round(max(0.0, min(1.0, quality)), 3)

    def _update_conductor_task_with_retry(
        self,
        task_update: Dict[str, Any],
        task_id: str,
        workflow_id: str,
    ) -> TaskCompletionResult:
        """
        Update Conductor task via REST API with retry logic.

        Args:
            task_update: Task update payload
            task_id: Conductor task ID
            workflow_id: Conductor workflow ID

        Returns:
            TaskCompletionResult with success status
        """
        retry_count = 0
        last_error = None
        last_response_code = None

        while retry_count <= self.max_retries:
            try:
                logger.debug(
                    f"Updating Conductor task {task_id} "
                    f"(attempt {retry_count + 1}/{self.max_retries + 1})"
                )

                response = self._session.post(
                    self.task_update_endpoint,
                    json=task_update,
                    headers={"Content-Type": "application/json"},
                    timeout=self.timeout_seconds,
                )

                last_response_code = response.status_code

                if response.status_code == 200:
                    logger.info(
                        f"Conductor task {task_id} updated successfully "
                        f"(attempts: {retry_count + 1})"
                    )
                    return TaskCompletionResult(
                        success=True,
                        task_id=task_id,
                        workflow_id=workflow_id,
                        status=ConductorTaskStatus.COMPLETED.value,
                        retry_count=retry_count,
                        response_code=response.status_code,
                    )
                elif response.status_code == 404:
                    # Task not found - could be already completed or workflow finished
                    logger.warning(
                        f"Conductor task {task_id} not found (404). "
                        f"Task may be already completed or workflow finished."
                    )
                    return TaskCompletionResult(
                        success=False,
                        task_id=task_id,
                        workflow_id=workflow_id,
                        status="NOT_FOUND",
                        error_message="Task not found in Conductor",
                        retry_count=retry_count,
                        response_code=response.status_code,
                    )
                else:
                    last_error = f"HTTP {response.status_code}: {response.text}"
                    logger.warning(
                        f"Conductor API returned error: {last_error}"
                    )

            except requests.exceptions.Timeout:
                last_error = "Request timed out"
                logger.warning(
                    f"Conductor API request timed out "
                    f"(attempt {retry_count + 1}/{self.max_retries + 1})"
                )
            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error: {str(e)}"
                logger.warning(
                    f"Failed to connect to Conductor API "
                    f"(attempt {retry_count + 1}/{self.max_retries + 1}): {last_error}"
                )
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.error(
                    f"Unexpected error updating Conductor task: {last_error}",
                    exc_info=True
                )

            retry_count += 1

            # Exponential backoff before retry
            if retry_count <= self.max_retries:
                sleep_time = self.retry_backoff_factor * (2 ** (retry_count - 1))
                logger.debug(f"Retrying in {sleep_time:.1f}s...")
                time.sleep(sleep_time)

        # All retries exhausted
        return TaskCompletionResult(
            success=False,
            task_id=task_id,
            workflow_id=workflow_id,
            status="FAILED",
            error_message=last_error,
            retry_count=retry_count - 1,
            response_code=last_response_code,
        )

    def _fail_conductor_task(
        self,
        task_id: str,
        workflow_id: str,
        reason: str,
    ) -> bool:
        """
        Mark a Conductor task as failed.

        Args:
            task_id: Conductor task ID
            workflow_id: Conductor workflow ID
            reason: Reason for failure

        Returns:
            True if successful, False otherwise
        """
        try:
            task_update = {
                "workflowInstanceId": workflow_id,
                "taskId": task_id,
                "status": ConductorTaskStatus.FAILED.value,
                "reasonForIncompletion": reason,
                "outputData": {
                    "error": reason,
                    "failed_at": datetime.utcnow().isoformat(),
                },
            }

            response = self._session.post(
                self.task_update_endpoint,
                json=task_update,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout_seconds,
            )

            if response.status_code == 200:
                logger.info(f"Conductor task {task_id} marked as failed: {reason}")
                return True
            else:
                logger.error(
                    f"Failed to mark task {task_id} as failed: "
                    f"{response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(
                f"Error marking Conductor task {task_id} as failed: {str(e)}",
                exc_info=True
            )
            return False

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get workflow execution status from Conductor.

        Args:
            workflow_id: Conductor workflow execution ID

        Returns:
            Workflow status dictionary, or None if error
        """
        try:
            url = f"{self.workflow_endpoint}/{workflow_id}"
            response = self._session.get(url, timeout=self.timeout_seconds)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    f"Failed to get workflow status: "
                    f"{response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error getting workflow status: {str(e)}", exc_info=True)
            return None

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status from Conductor.

        Args:
            task_id: Conductor task ID

        Returns:
            Task status dictionary, or None if error
        """
        try:
            url = f"{self.task_update_endpoint}/{task_id}"
            response = self._session.get(url, timeout=self.timeout_seconds)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    f"Failed to get task status: "
                    f"{response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error getting task status: {str(e)}", exc_info=True)
            return None

    def get_pending_human_tasks(self, workflow_id: str) -> List[Dict[str, Any]]:
        """
        Get all pending HUMAN tasks for a workflow.

        Args:
            workflow_id: Conductor workflow execution ID

        Returns:
            List of pending HUMAN task details
        """
        workflow_status = self.get_workflow_status(workflow_id)
        if not workflow_status:
            return []

        pending_tasks = []
        tasks = workflow_status.get("tasks", [])

        for task in tasks:
            if (
                task.get("taskType") == "HUMAN"
                and task.get("status") == ConductorTaskStatus.IN_PROGRESS.value
            ):
                pending_tasks.append({
                    "task_id": task.get("taskId"),
                    "task_type": task.get("taskType"),
                    "task_def_name": task.get("taskDefName"),
                    "status": task.get("status"),
                    "input_data": task.get("inputData"),
                    "start_time": task.get("startTime"),
                    "scheduled_time": task.get("scheduledTime"),
                })

        return pending_tasks

    def is_conductor_available(self) -> bool:
        """
        Check if Conductor server is available.

        Returns:
            True if Conductor is reachable, False otherwise
        """
        try:
            health_url = self.conductor_url.replace("/api", "/health")
            response = self._session.get(health_url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def get_conductor_health(self) -> Optional[Dict[str, Any]]:
        """
        Get detailed Conductor health status.

        Returns:
            Health status dictionary, or None if unavailable
        """
        try:
            health_url = self.conductor_url.replace("/api", "/health")
            response = self._session.get(health_url, timeout=5)

            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "unhealthy", "code": response.status_code}

        except Exception as e:
            return {"status": "unreachable", "error": str(e)}

    def terminate_workflow(
        self,
        workflow_id: str,
        reason: str = "Terminated by HITL service",
    ) -> bool:
        """
        Terminate a running workflow.

        Args:
            workflow_id: Conductor workflow execution ID
            reason: Termination reason

        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.workflow_endpoint}/{workflow_id}"
            response = self._session.delete(
                url,
                params={"reason": reason},
                timeout=self.timeout_seconds,
            )

            if response.status_code in [200, 204]:
                logger.info(f"Workflow {workflow_id} terminated: {reason}")
                return True
            else:
                logger.error(
                    f"Failed to terminate workflow {workflow_id}: "
                    f"{response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(
                f"Error terminating workflow {workflow_id}: {str(e)}",
                exc_info=True
            )
            return False

    def restart_workflow(
        self,
        workflow_id: str,
        use_latest_definition: bool = True,
    ) -> Optional[str]:
        """
        Restart a completed or failed workflow.

        Args:
            workflow_id: Conductor workflow execution ID
            use_latest_definition: Use latest workflow definition version

        Returns:
            New workflow execution ID, or None if failed
        """
        try:
            url = f"{self.workflow_endpoint}/{workflow_id}/restart"
            response = self._session.post(
                url,
                params={"useLatestDefinitions": str(use_latest_definition).lower()},
                timeout=self.timeout_seconds,
            )

            if response.status_code == 200:
                new_workflow_id = response.text.strip().strip('"')
                logger.info(
                    f"Workflow {workflow_id} restarted as {new_workflow_id}"
                )
                return new_workflow_id
            else:
                logger.error(
                    f"Failed to restart workflow {workflow_id}: "
                    f"{response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            logger.error(
                f"Error restarting workflow {workflow_id}: {str(e)}",
                exc_info=True
            )
            return None
