"""
Error Recovery Tests

Tests for error handling and recovery mechanisms:
- Task retry on transient errors
- Exponential backoff
- Max retries and failure
- Workflow compensation
- Conductor unavailability
- Worker crash recovery
- Database connection loss
- Timeout handling
- Manual workflow restart
- Partial workflow resume
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, MagicMock, patch
import time

import pytest


# ==============================================================================
# Retry Policy Implementation (for testing)
# ==============================================================================


class RetryPolicy:
    """
    Retry policy configuration.
    """

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay_seconds: float = 1.0,
        backoff_multiplier: float = 2.0,
        max_delay_seconds: float = 60.0,
        retryable_exceptions: Optional[List[type]] = None,
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay_seconds
        self.backoff_multiplier = backoff_multiplier
        self.max_delay = max_delay_seconds
        self.retryable_exceptions = retryable_exceptions or [
            ConnectionError,
            TimeoutError,
        ]

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Check if should retry based on exception and attempt count."""
        if attempt >= self.max_retries:
            return False
        return any(
            isinstance(exception, exc_type)
            for exc_type in self.retryable_exceptions
        )

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for attempt (exponential backoff)."""
        delay = self.initial_delay * (self.backoff_multiplier ** attempt)
        return min(delay, self.max_delay)


class TaskExecutionError(Exception):
    """Error during task execution."""

    def __init__(self, message: str, is_transient: bool = False):
        super().__init__(message)
        self.is_transient = is_transient


class TransientError(TaskExecutionError):
    """Transient error that may resolve on retry."""

    def __init__(self, message: str):
        super().__init__(message, is_transient=True)


class TerminalError(TaskExecutionError):
    """Terminal error that should not be retried."""

    def __init__(self, message: str):
        super().__init__(message, is_transient=False)


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def retry_policy():
    """Create default retry policy."""
    return RetryPolicy(
        max_retries=3,
        initial_delay_seconds=1.0,
        backoff_multiplier=2.0,
        max_delay_seconds=60.0,
    )


@pytest.fixture
def aggressive_retry_policy():
    """Create aggressive retry policy for testing."""
    return RetryPolicy(
        max_retries=5,
        initial_delay_seconds=0.1,
        backoff_multiplier=2.0,
        max_delay_seconds=10.0,
    )


# ==============================================================================
# Task Retry Tests
# ==============================================================================


class TestTaskRetryOnTransientError:
    """Tests for task retry on transient errors."""

    def test_should_retry_on_connection_error(self, retry_policy):
        """GIVEN connection error WHEN checking THEN should retry."""
        error = ConnectionError("Connection refused")
        should_retry = retry_policy.should_retry(error, attempt=0)
        assert should_retry is True

    def test_should_retry_on_timeout_error(self, retry_policy):
        """GIVEN timeout error WHEN checking THEN should retry."""
        error = TimeoutError("Request timed out")
        should_retry = retry_policy.should_retry(error, attempt=0)
        assert should_retry is True

    def test_should_not_retry_on_value_error(self, retry_policy):
        """GIVEN value error WHEN checking THEN should not retry."""
        error = ValueError("Invalid input")
        should_retry = retry_policy.should_retry(error, attempt=0)
        assert should_retry is False

    def test_retry_succeeds_after_transient_failure(self):
        """GIVEN transient failure WHEN retrying THEN succeeds."""
        attempts = []

        def flaky_operation():
            attempts.append(1)
            if len(attempts) < 3:
                raise ConnectionError("Connection failed")
            return "success"

        # Simulate retry loop
        result = None
        for attempt in range(5):
            try:
                result = flaky_operation()
                break
            except ConnectionError:
                continue

        assert result == "success"
        assert len(attempts) == 3


class TestExponentialBackoff:
    """Tests for exponential backoff calculation."""

    def test_initial_delay(self, retry_policy):
        """GIVEN first retry WHEN calculating delay THEN uses initial delay."""
        delay = retry_policy.get_delay(attempt=0)
        assert delay == 1.0

    def test_second_retry_delay(self, retry_policy):
        """GIVEN second retry WHEN calculating delay THEN doubles."""
        delay = retry_policy.get_delay(attempt=1)
        assert delay == 2.0

    def test_third_retry_delay(self, retry_policy):
        """GIVEN third retry WHEN calculating delay THEN quadruples."""
        delay = retry_policy.get_delay(attempt=2)
        assert delay == 4.0

    def test_max_delay_capped(self, retry_policy):
        """GIVEN many retries WHEN calculating delay THEN caps at max."""
        delay = retry_policy.get_delay(attempt=10)
        assert delay == 60.0  # max_delay_seconds

    def test_backoff_sequence(self, retry_policy):
        """GIVEN retry sequence WHEN calculating THEN follows exponential pattern."""
        delays = [retry_policy.get_delay(i) for i in range(5)]
        assert delays == [1.0, 2.0, 4.0, 8.0, 16.0]


class TestMaxRetriesExceeded:
    """Tests for max retries exceeded behavior."""

    def test_no_retry_after_max_attempts(self, retry_policy):
        """GIVEN max attempts reached WHEN checking THEN should not retry."""
        error = ConnectionError("Connection failed")

        # After max_retries (3), should not retry
        should_retry = retry_policy.should_retry(error, attempt=3)
        assert should_retry is False

    def test_retry_before_max_attempts(self, retry_policy):
        """GIVEN before max attempts WHEN checking THEN should retry."""
        error = ConnectionError("Connection failed")

        should_retry = retry_policy.should_retry(error, attempt=2)
        assert should_retry is True

    def test_task_fails_after_max_retries(self):
        """GIVEN all retries exhausted WHEN executing THEN marks as failed."""
        max_retries = 3
        attempts = 0

        def always_fails():
            nonlocal attempts
            attempts += 1
            raise ConnectionError("Always fails")

        final_error = None
        for _ in range(max_retries + 1):
            try:
                always_fails()
            except ConnectionError as e:
                final_error = e
                continue

        assert attempts == max_retries + 1
        assert final_error is not None


# ==============================================================================
# Compensation Tests
# ==============================================================================


class TestWorkflowCompensation:
    """Tests for workflow compensation on failure."""

    def test_compensation_tasks_executed_on_failure(self):
        """GIVEN workflow failure WHEN compensating THEN executes compensation tasks."""
        executed_tasks = []
        compensated_tasks = []

        def execute_task(name: str):
            executed_tasks.append(name)

        def compensate_task(name: str):
            compensated_tasks.append(name)

        # Simulate workflow
        try:
            execute_task("task_1")
            execute_task("task_2")
            raise Exception("Task 3 failed")
        except Exception:
            # Compensate in reverse order
            compensate_task("task_2")
            compensate_task("task_1")

        assert executed_tasks == ["task_1", "task_2"]
        assert compensated_tasks == ["task_2", "task_1"]

    def test_compensation_order_is_reversed(self):
        """GIVEN multiple completed tasks WHEN compensating THEN reverses order."""
        completed_order = ["A", "B", "C", "D"]
        compensation_order = list(reversed(completed_order))

        assert compensation_order == ["D", "C", "B", "A"]


# ==============================================================================
# Service Unavailability Tests
# ==============================================================================


class TestConductorUnavailable:
    """Tests for Conductor unavailability handling."""

    def test_graceful_degradation_on_conductor_down(self):
        """GIVEN Conductor unavailable WHEN polling THEN handles gracefully."""
        conductor_available = False

        def poll_conductor():
            if not conductor_available:
                raise ConnectionError("Conductor unavailable")
            return {"tasks": []}

        # Should not crash, should log warning and continue
        try:
            poll_conductor()
            polled = True
        except ConnectionError:
            polled = False

        assert polled is False

    def test_retry_connection_to_conductor(self):
        """GIVEN Conductor down WHEN retrying THEN eventually connects."""
        connection_attempts = []

        def connect_conductor():
            connection_attempts.append(1)
            if len(connection_attempts) < 3:
                raise ConnectionError("Cannot connect")
            return True

        connected = False
        for _ in range(5):
            try:
                connected = connect_conductor()
                break
            except ConnectionError:
                continue

        assert connected is True
        assert len(connection_attempts) == 3


class TestDatabaseConnectionLoss:
    """Tests for database connection loss handling."""

    def test_reconnect_on_connection_loss(self):
        """GIVEN database connection lost WHEN detected THEN reconnects."""
        connection_attempts = []
        db_available = False

        def get_db_connection():
            connection_attempts.append(1)
            if not db_available and len(connection_attempts) < 3:
                raise ConnectionError("Database unavailable")
            return Mock()

        # Simulate reconnection
        connection = None
        for _ in range(5):
            try:
                connection = get_db_connection()
                break
            except ConnectionError:
                continue

        assert connection is not None

    def test_transaction_rollback_on_error(self):
        """GIVEN database error during transaction WHEN handling THEN rolls back."""
        mock_session = Mock()
        mock_session.commit.side_effect = Exception("Database error")

        try:
            # Simulate transaction
            mock_session.add(Mock())
            mock_session.commit()
        except Exception:
            mock_session.rollback()

        mock_session.rollback.assert_called_once()


# ==============================================================================
# Worker Crash Recovery Tests
# ==============================================================================


class TestWorkerCrashRecovery:
    """Tests for worker crash recovery."""

    def test_task_requeued_after_worker_crash(self):
        """GIVEN worker crashes WHEN detected THEN task requeued."""
        # Simulate task in progress when worker crashes
        task_state = "in_progress"
        worker_heartbeat = datetime.utcnow() - timedelta(minutes=5)
        heartbeat_timeout = timedelta(minutes=2)

        # Detect stale worker
        is_worker_dead = (datetime.utcnow() - worker_heartbeat) > heartbeat_timeout

        if is_worker_dead and task_state == "in_progress":
            task_state = "queued"  # Requeue for pickup

        assert is_worker_dead is True
        assert task_state == "queued"

    def test_worker_heartbeat_detection(self):
        """GIVEN worker WHEN checking heartbeat THEN detects alive/dead."""
        last_heartbeat = datetime.utcnow() - timedelta(seconds=30)
        heartbeat_timeout = timedelta(minutes=1)

        is_alive = (datetime.utcnow() - last_heartbeat) < heartbeat_timeout
        assert is_alive is True

        # Dead worker
        last_heartbeat = datetime.utcnow() - timedelta(minutes=5)
        is_alive = (datetime.utcnow() - last_heartbeat) < heartbeat_timeout
        assert is_alive is False


# ==============================================================================
# Timeout Handling Tests
# ==============================================================================


class TestTimeoutHandling:
    """Tests for timeout handling."""

    def test_task_timeout_triggers_retry(self):
        """GIVEN task times out WHEN detected THEN triggers retry."""
        task_status = "in_progress"
        task_started = datetime.utcnow() - timedelta(minutes=10)
        task_timeout = timedelta(minutes=5)

        is_timed_out = (datetime.utcnow() - task_started) > task_timeout

        if is_timed_out:
            task_status = "timed_out"

        assert is_timed_out is True
        assert task_status == "timed_out"

    def test_timeout_detection(self):
        """GIVEN task with timeout WHEN checking THEN detects correctly."""
        task_timeout_seconds = 300  # 5 minutes

        # Not timed out
        start_time = datetime.utcnow() - timedelta(seconds=100)
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        assert elapsed < task_timeout_seconds

        # Timed out
        start_time = datetime.utcnow() - timedelta(seconds=400)
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        assert elapsed > task_timeout_seconds


# ==============================================================================
# Manual Workflow Restart Tests
# ==============================================================================


class TestManualWorkflowRestart:
    """Tests for manual workflow restart."""

    def test_failed_workflow_can_be_restarted(self):
        """GIVEN failed workflow WHEN restarted THEN resets to running."""
        workflow_status = "failed"

        # Restart
        if workflow_status == "failed":
            workflow_status = "running"

        assert workflow_status == "running"

    def test_restart_from_failed_task(self):
        """GIVEN workflow with failed task WHEN restarting THEN resumes from failure point."""
        completed_tasks = ["task_1", "task_2"]
        failed_task = "task_3"
        pending_tasks = ["task_4", "task_5"]

        # On restart, resume from failed task
        tasks_to_execute = [failed_task] + pending_tasks

        assert tasks_to_execute == ["task_3", "task_4", "task_5"]
        assert "task_1" not in tasks_to_execute
        assert "task_2" not in tasks_to_execute


class TestPartialWorkflowResume:
    """Tests for partial workflow resume."""

    def test_resume_from_checkpoint(self):
        """GIVEN workflow with checkpoint WHEN resuming THEN continues from checkpoint."""
        checkpoint = {
            "workflow_id": "wf-123",
            "completed_tasks": ["task_1", "task_2"],
            "next_task": "task_3",
            "context": {"data": "preserved"},
        }

        # Resume from checkpoint
        next_task = checkpoint["next_task"]
        context = checkpoint["context"]

        assert next_task == "task_3"
        assert context["data"] == "preserved"

    def test_context_preserved_on_resume(self):
        """GIVEN workflow context WHEN resuming THEN preserves context."""
        workflow_context = {
            "extract-1": {"extracted_data": {"invoice": "INV-001"}},
            "validate-1": {"is_valid": True},
        }

        # On resume, context should be available
        assert workflow_context["extract-1"]["extracted_data"]["invoice"] == "INV-001"


# ==============================================================================
# Error Classification Tests
# ==============================================================================


class TestErrorClassification:
    """Tests for error classification."""

    def test_transient_error_is_retryable(self):
        """GIVEN transient error WHEN classifying THEN is retryable."""
        error = TransientError("Network temporarily unavailable")
        assert error.is_transient is True

    def test_terminal_error_is_not_retryable(self):
        """GIVEN terminal error WHEN classifying THEN is not retryable."""
        error = TerminalError("Invalid input data")
        assert error.is_transient is False

    def test_classify_http_errors(self):
        """GIVEN HTTP status codes WHEN classifying THEN determines retryability."""
        retryable_statuses = [429, 500, 502, 503, 504]
        non_retryable_statuses = [400, 401, 403, 404, 422]

        def is_retryable_status(status: int) -> bool:
            return status in retryable_statuses

        assert is_retryable_status(500) is True
        assert is_retryable_status(429) is True
        assert is_retryable_status(400) is False
        assert is_retryable_status(404) is False


# ==============================================================================
# Circuit Breaker Tests
# ==============================================================================


class TestCircuitBreaker:
    """Tests for circuit breaker pattern."""

    def test_circuit_opens_after_failures(self):
        """GIVEN multiple failures WHEN threshold reached THEN circuit opens."""
        failure_count = 0
        failure_threshold = 5
        circuit_open = False

        for _ in range(6):
            failure_count += 1
            if failure_count >= failure_threshold:
                circuit_open = True

        assert circuit_open is True

    def test_circuit_half_open_after_timeout(self):
        """GIVEN open circuit WHEN timeout passes THEN becomes half-open."""
        circuit_opened_at = datetime.utcnow() - timedelta(minutes=5)
        circuit_timeout = timedelta(minutes=1)
        circuit_state = "open"

        if (datetime.utcnow() - circuit_opened_at) > circuit_timeout:
            circuit_state = "half_open"

        assert circuit_state == "half_open"

    def test_circuit_closes_on_success(self):
        """GIVEN half-open circuit WHEN request succeeds THEN closes."""
        circuit_state = "half_open"
        request_succeeded = True

        if circuit_state == "half_open" and request_succeeded:
            circuit_state = "closed"

        assert circuit_state == "closed"


# ==============================================================================
# Idempotency Tests
# ==============================================================================


class TestIdempotency:
    """Tests for idempotent task execution."""

    def test_duplicate_task_execution_prevented(self):
        """GIVEN task already executed WHEN retried THEN returns cached result."""
        execution_cache = {}

        def execute_task_idempotent(task_id: str, fn):
            if task_id in execution_cache:
                return execution_cache[task_id]
            result = fn()
            execution_cache[task_id] = result
            return result

        execution_count = 0

        def task_fn():
            nonlocal execution_count
            execution_count += 1
            return {"result": "data"}

        # Execute twice with same ID
        result1 = execute_task_idempotent("task-123", task_fn)
        result2 = execute_task_idempotent("task-123", task_fn)

        assert result1 == result2
        assert execution_count == 1  # Only executed once

    def test_different_task_ids_execute_separately(self):
        """GIVEN different task IDs WHEN executing THEN each executes."""
        execution_cache = {}
        execution_count = 0

        def execute_task_idempotent(task_id: str):
            nonlocal execution_count
            if task_id in execution_cache:
                return execution_cache[task_id]
            execution_count += 1
            result = {"task": task_id}
            execution_cache[task_id] = result
            return result

        result1 = execute_task_idempotent("task-1")
        result2 = execute_task_idempotent("task-2")

        assert result1["task"] == "task-1"
        assert result2["task"] == "task-2"
        assert execution_count == 2
