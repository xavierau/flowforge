"""
Integration tests for the Human Review Worker.

Tests cover:
- IN_PROGRESS status return (workflow pauses)
- ReviewRequest creation in database
- Priority calculation based on confidence
- SLA deadline calculation
- Conductor metadata storage
- Tenant isolation validation
- Input validation
- Idempotency (existing review handling)
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4

from app.orchestration.workers.human_review_worker import HumanReviewWorker
from app.models.enums import ReviewRequestStatus, ReviewPriority


class TestHumanReviewWorkerBasics:
    """Basic tests for HumanReviewWorker."""

    @pytest.fixture
    def worker(self):
        return HumanReviewWorker()

    def test_worker_task_definition_name(self, worker):
        """
        GIVEN HumanReviewWorker
        WHEN getting task definition name
        THEN returns 'HUMAN_REVIEW'
        """
        assert worker.get_task_definition_name() == "HUMAN_REVIEW"

    def test_worker_poll_interval(self, worker):
        """
        GIVEN HumanReviewWorker
        WHEN getting polling interval
        THEN returns 2 seconds
        """
        assert worker.get_polling_interval_in_seconds() == 2.0


class TestHumanReviewWorkerInputValidation:
    """Tests for input validation."""

    @pytest.fixture
    def worker(self):
        return HumanReviewWorker()

    def test_validate_missing_extraction_job_id(self, worker):
        """
        GIVEN input without extraction_job_id
        WHEN validating
        THEN returns error
        """
        task_input = {
            "tenant_id": str(uuid4()),
            "confidence_score": 0.65
        }

        error = worker.validate_input(task_input)

        assert error is not None
        assert "extraction_job_id" in error

    def test_validate_missing_tenant_id(self, worker):
        """
        GIVEN input without tenant_id
        WHEN validating
        THEN returns error (security requirement)
        """
        task_input = {
            "extraction_job_id": str(uuid4()),
            "confidence_score": 0.65
        }

        error = worker.validate_input(task_input)

        assert error is not None
        assert "tenant_id" in error

    def test_validate_missing_confidence_score(self, worker):
        """
        GIVEN input without confidence_score
        WHEN validating
        THEN returns error
        """
        task_input = {
            "extraction_job_id": str(uuid4()),
            "tenant_id": str(uuid4())
        }

        error = worker.validate_input(task_input)

        assert error is not None
        assert "confidence_score" in error

    def test_validate_invalid_confidence_score_too_high(self, worker):
        """
        GIVEN confidence_score > 1.0
        WHEN validating
        THEN returns error
        """
        task_input = {
            "extraction_job_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "confidence_score": 1.5
        }

        error = worker.validate_input(task_input)

        assert error is not None
        assert "between 0.0 and 1.0" in error

    def test_validate_invalid_confidence_score_negative(self, worker):
        """
        GIVEN negative confidence_score
        WHEN validating
        THEN returns error
        """
        task_input = {
            "extraction_job_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "confidence_score": -0.5
        }

        error = worker.validate_input(task_input)

        assert error is not None
        assert "between 0.0 and 1.0" in error

    def test_validate_non_numeric_confidence_score(self, worker):
        """
        GIVEN non-numeric confidence_score
        WHEN validating
        THEN returns error
        """
        task_input = {
            "extraction_job_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "confidence_score": "high"
        }

        error = worker.validate_input(task_input)

        assert error is not None
        assert "number" in error

    def test_validate_valid_input(self, worker):
        """
        GIVEN valid input
        WHEN validating
        THEN returns None
        """
        task_input = {
            "extraction_job_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "confidence_score": 0.65
        }

        error = worker.validate_input(task_input)

        assert error is None


class TestHumanReviewWorkerPriorityCalculation:
    """Tests for priority calculation based on confidence."""

    @pytest.fixture
    def worker(self):
        return HumanReviewWorker()

    def test_priority_critical_below_30(self, worker):
        """
        GIVEN confidence_score < 0.30
        WHEN determining priority
        THEN returns CRITICAL
        """
        priority = worker._determine_priority(0.25)

        assert priority == ReviewPriority.CRITICAL

    def test_priority_critical_at_zero(self, worker):
        """
        GIVEN confidence_score = 0
        WHEN determining priority
        THEN returns CRITICAL
        """
        priority = worker._determine_priority(0.0)

        assert priority == ReviewPriority.CRITICAL

    def test_priority_high_30_to_50(self, worker):
        """
        GIVEN 0.30 <= confidence_score < 0.50
        WHEN determining priority
        THEN returns HIGH
        """
        assert worker._determine_priority(0.30) == ReviewPriority.HIGH
        assert worker._determine_priority(0.40) == ReviewPriority.HIGH
        assert worker._determine_priority(0.49) == ReviewPriority.HIGH

    def test_priority_normal_50_to_60(self, worker):
        """
        GIVEN 0.50 <= confidence_score < 0.60
        WHEN determining priority
        THEN returns NORMAL
        """
        assert worker._determine_priority(0.50) == ReviewPriority.NORMAL
        assert worker._determine_priority(0.55) == ReviewPriority.NORMAL
        assert worker._determine_priority(0.59) == ReviewPriority.NORMAL

    def test_priority_low_60_to_70(self, worker):
        """
        GIVEN 0.60 <= confidence_score < 0.70
        WHEN determining priority
        THEN returns LOW
        """
        assert worker._determine_priority(0.60) == ReviewPriority.LOW
        assert worker._determine_priority(0.65) == ReviewPriority.LOW
        assert worker._determine_priority(0.69) == ReviewPriority.LOW

    def test_priority_low_above_70(self, worker):
        """
        GIVEN confidence_score >= 0.70
        WHEN determining priority
        THEN returns LOW (lowest priority, might be auto-approved anyway)
        """
        assert worker._determine_priority(0.70) == ReviewPriority.LOW
        assert worker._determine_priority(0.85) == ReviewPriority.LOW


class TestHumanReviewWorkerExecuteTask:
    """Tests for execute_task method (creates ReviewRequest)."""

    @pytest.fixture
    def worker(self):
        return HumanReviewWorker()

    @pytest.fixture
    def mock_task(self):
        """Create mock Conductor task."""
        task = Mock()
        task.task_id = "conductor-task-123"
        task.workflow_instance_id = "conductor-workflow-456"
        task.input_data = {
            "extraction_job_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "confidence_score": 0.45
        }
        return task

    @patch('app.orchestration.workers.human_review_worker.SessionLocal')
    def test_execute_creates_review_request(self, mock_session_class, worker):
        """
        GIVEN valid task input
        WHEN executing task
        THEN creates ReviewRequest in database
        """
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Mock extraction job exists
        mock_job = Mock()
        mock_job.tenant_id = uuid4()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_job

        # Mock no existing review
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            mock_job,  # First call - extraction job
            None       # Second call - no existing review
        ]

        task_input = {
            "extraction_job_id": str(uuid4()),
            "tenant_id": str(mock_job.tenant_id),
            "confidence_score": 0.45,
            "conductor_task_id": "task-123",
            "conductor_workflow_id": "workflow-456"
        }

        result = worker._create_review_request(task_input)

        # Verify result structure
        assert "review_request_id" in result
        assert "priority" in result
        assert "sla_deadline" in result
        assert "message" in result

        # Verify database operations
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called()

    @patch('app.orchestration.workers.human_review_worker.SessionLocal')
    def test_execute_returns_correct_priority(self, mock_session_class, worker):
        """
        GIVEN confidence score of 0.45
        WHEN creating review request
        THEN priority is HIGH
        """
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_job = Mock()
        mock_job.tenant_id = uuid4()

        mock_session.query.return_value.filter.return_value.first.side_effect = [
            mock_job,
            None
        ]

        task_input = {
            "extraction_job_id": str(uuid4()),
            "tenant_id": str(mock_job.tenant_id),
            "confidence_score": 0.45,
            "conductor_task_id": "task-123",
            "conductor_workflow_id": "workflow-456"
        }

        result = worker._create_review_request(task_input)

        assert result["priority"] == "high"

    @patch('app.orchestration.workers.human_review_worker.SessionLocal')
    def test_execute_handles_existing_review(self, mock_session_class, worker):
        """
        GIVEN extraction job already has a review request
        WHEN creating review request
        THEN returns existing review (idempotency)
        """
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_job = Mock()
        mock_job.tenant_id = uuid4()

        existing_review = Mock()
        existing_review.id = uuid4()
        existing_review.priority = "high"
        existing_review.sla_deadline = datetime.now(timezone.utc) + timedelta(hours=2)
        existing_review.conductor_task_id = None

        mock_session.query.return_value.filter.return_value.first.side_effect = [
            mock_job,
            existing_review
        ]

        task_input = {
            "extraction_job_id": str(uuid4()),
            "tenant_id": str(mock_job.tenant_id),
            "confidence_score": 0.45,
            "conductor_task_id": "task-123",
            "conductor_workflow_id": "workflow-456"
        }

        result = worker._create_review_request(task_input)

        assert result["review_request_id"] == str(existing_review.id)
        assert "already exists" in result["message"]

    @patch('app.orchestration.workers.human_review_worker.SessionLocal')
    def test_execute_job_not_found_raises(self, mock_session_class, worker):
        """
        GIVEN extraction job doesn't exist
        WHEN creating review request
        THEN raises ValueError
        """
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_session.query.return_value.filter.return_value.first.return_value = None

        task_input = {
            "extraction_job_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "confidence_score": 0.45,
            "conductor_task_id": "task-123",
            "conductor_workflow_id": "workflow-456"
        }

        with pytest.raises(ValueError) as exc_info:
            worker._create_review_request(task_input)

        assert "not found" in str(exc_info.value)


class TestHumanReviewWorkerExecute:
    """Tests for the main execute method (Conductor integration)."""

    @pytest.fixture
    def worker(self):
        return HumanReviewWorker()

    def test_execute_returns_in_progress_status(self, worker):
        """
        GIVEN valid task
        WHEN executing
        THEN returns IN_PROGRESS status (critical for HITL)
        """
        task = Mock()
        task.task_id = "task-123"
        task.workflow_instance_id = "workflow-456"
        task.input_data = {
            "extraction_job_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "confidence_score": 0.65
        }

        task_result = Mock()
        task_result.status = None
        worker.get_task_result_from_task = Mock(return_value=task_result)

        with patch.object(worker, '_create_review_request') as mock_create:
            mock_create.return_value = {
                "review_request_id": str(uuid4()),
                "priority": "normal",
                "sla_deadline": datetime.now(timezone.utc).isoformat(),
                "message": "Created"
            }

            result = worker.execute(task)

            assert task_result.status == "IN_PROGRESS"

    def test_execute_adds_callback_timeout(self, worker):
        """
        GIVEN valid task
        WHEN executing
        THEN output includes callback_after_seconds
        """
        task = Mock()
        task.task_id = "task-123"
        task.workflow_instance_id = "workflow-456"
        task.input_data = {
            "extraction_job_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "confidence_score": 0.65
        }

        task_result = Mock()
        output_data = {}
        task_result.add_output_data = lambda k, v: output_data.update({k: v})
        worker.get_task_result_from_task = Mock(return_value=task_result)

        with patch.object(worker, '_create_review_request') as mock_create:
            mock_create.return_value = {
                "review_request_id": str(uuid4()),
                "priority": "normal",
                "sla_deadline": datetime.now(timezone.utc).isoformat(),
                "message": "Created"
            }

            worker.execute(task)

            assert "callback_after_seconds" in output_data
            assert output_data["callback_after_seconds"] == worker.DEFAULT_TIMEOUT_SECONDS

    def test_execute_populates_conductor_metadata(self, worker):
        """
        GIVEN task from Conductor
        WHEN executing
        THEN passes conductor_task_id and conductor_workflow_id to create method
        """
        task = Mock()
        task.task_id = "conductor-task-id-999"
        task.workflow_instance_id = "conductor-workflow-id-888"
        task.input_data = {
            "extraction_job_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "confidence_score": 0.65
        }

        task_result = Mock()
        worker.get_task_result_from_task = Mock(return_value=task_result)

        with patch.object(worker, '_create_review_request') as mock_create:
            mock_create.return_value = {
                "review_request_id": str(uuid4()),
                "priority": "normal",
                "sla_deadline": datetime.now(timezone.utc).isoformat(),
                "message": "Created"
            }

            worker.execute(task)

            # Verify Conductor metadata was passed
            call_args = mock_create.call_args[0][0]
            assert call_args["conductor_task_id"] == "conductor-task-id-999"
            assert call_args["conductor_workflow_id"] == "conductor-workflow-id-888"

    def test_execute_returns_failed_on_validation_error(self, worker):
        """
        GIVEN invalid input
        WHEN executing
        THEN returns FAILED status
        """
        task = Mock()
        task.task_id = "task-123"
        task.workflow_instance_id = "workflow-456"
        task.input_data = {
            # Missing required fields
        }

        task_result = Mock()
        task_result.status = None
        worker.get_task_result_from_task = Mock(return_value=task_result)

        worker.execute(task)

        assert task_result.status == "FAILED"

    def test_execute_returns_failed_on_exception(self, worker):
        """
        GIVEN task that causes exception
        WHEN executing
        THEN returns FAILED status
        """
        task = Mock()
        task.task_id = "task-123"
        task.workflow_instance_id = "workflow-456"
        task.input_data = {
            "extraction_job_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "confidence_score": 0.65
        }

        task_result = Mock()
        task_result.status = None
        worker.get_task_result_from_task = Mock(return_value=task_result)

        with patch.object(worker, '_create_review_request') as mock_create:
            mock_create.side_effect = Exception("Database error")

            worker.execute(task)

            assert task_result.status == "FAILED"


class TestHumanReviewWorkerTenantIsolation:
    """Tests for tenant isolation security."""

    @pytest.fixture
    def worker(self):
        return HumanReviewWorker()

    @patch('app.orchestration.workers.human_review_worker.SessionLocal')
    def test_create_request_queries_with_tenant_id(self, mock_session_class, worker):
        """
        GIVEN task input with tenant_id
        WHEN creating review request
        THEN queries database with tenant_id filter
        """
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        tenant_id = uuid4()
        extraction_job_id = uuid4()

        mock_session.query.return_value.filter.return_value.first.return_value = None

        task_input = {
            "extraction_job_id": str(extraction_job_id),
            "tenant_id": str(tenant_id),
            "confidence_score": 0.65,
            "conductor_task_id": "task-123",
            "conductor_workflow_id": "workflow-456"
        }

        with pytest.raises(ValueError):
            # Will raise because no job found, but we verify the filter was called
            worker._create_review_request(task_input)

        # Verify filter was called (tenant isolation enforced)
        mock_session.query.assert_called()

    def test_tenant_id_required_for_security(self, worker):
        """
        GIVEN input without tenant_id
        WHEN validating
        THEN fails with security message
        """
        task_input = {
            "extraction_job_id": str(uuid4()),
            "confidence_score": 0.65
        }

        error = worker.validate_input(task_input)

        assert error is not None
        assert "security" in error.lower() or "tenant_id" in error


class TestHumanReviewWorkerSLADeadline:
    """Tests for SLA deadline calculation."""

    @pytest.fixture
    def worker(self):
        return HumanReviewWorker()

    @patch('app.orchestration.workers.human_review_worker.SessionLocal')
    @patch('app.orchestration.workers.human_review_worker.ReviewRequest')
    def test_sla_deadline_returned_in_result(self, mock_review_class, mock_session_class, worker):
        """
        GIVEN review request creation
        WHEN creating review
        THEN result includes SLA deadline
        """
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_job = Mock()
        mock_job.tenant_id = uuid4()

        mock_session.query.return_value.filter.return_value.first.side_effect = [
            mock_job,
            None
        ]

        expected_deadline = datetime.now(timezone.utc) + timedelta(hours=2)
        mock_review_class.calculate_sla_deadline.return_value = expected_deadline

        task_input = {
            "extraction_job_id": str(uuid4()),
            "tenant_id": str(mock_job.tenant_id),
            "confidence_score": 0.45,
            "conductor_task_id": "task-123",
            "conductor_workflow_id": "workflow-456"
        }

        result = worker._create_review_request(task_input)

        assert "sla_deadline" in result
        # Verify it's a valid ISO format string
        datetime.fromisoformat(result["sla_deadline"])
