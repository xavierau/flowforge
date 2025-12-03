"""
Workflow State Machine Tests

Tests for workflow and task state transitions:
- Workflow states: PENDING, RUNNING, COMPLETED, FAILED, PAUSED
- Task states: QUEUED, IN_PROGRESS, COMPLETED, FAILED
- HITL pause/resume transitions
- Invalid state transition rejection
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from unittest.mock import Mock, MagicMock

import pytest


# ==============================================================================
# State Definitions (for testing)
# ==============================================================================


class WorkflowStatus(str, Enum):
    """Workflow execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    TERMINATED = "terminated"


class TaskStatus(str, Enum):
    """Task execution states."""
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    FAILED_WITH_TERMINAL_ERROR = "failed_with_terminal_error"
    TIMED_OUT = "timed_out"
    SKIPPED = "skipped"


# ==============================================================================
# State Machine Implementation (for testing)
# ==============================================================================


class WorkflowStateMachine:
    """
    Validates workflow state transitions.
    """

    VALID_TRANSITIONS = {
        WorkflowStatus.PENDING: [WorkflowStatus.RUNNING, WorkflowStatus.TERMINATED],
        WorkflowStatus.RUNNING: [
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.PAUSED,
            WorkflowStatus.TERMINATED,
        ],
        WorkflowStatus.PAUSED: [WorkflowStatus.RUNNING, WorkflowStatus.TERMINATED],
        WorkflowStatus.COMPLETED: [],  # Terminal state
        WorkflowStatus.FAILED: [WorkflowStatus.RUNNING],  # Can restart
        WorkflowStatus.TERMINATED: [],  # Terminal state
    }

    @classmethod
    def can_transition(
        cls, from_status: WorkflowStatus, to_status: WorkflowStatus
    ) -> bool:
        """Check if transition is valid."""
        valid_targets = cls.VALID_TRANSITIONS.get(from_status, [])
        return to_status in valid_targets

    @classmethod
    def transition(
        cls, current: WorkflowStatus, target: WorkflowStatus
    ) -> WorkflowStatus:
        """Attempt state transition."""
        if not cls.can_transition(current, target):
            raise InvalidStateTransitionError(
                f"Cannot transition from {current} to {target}"
            )
        return target


class TaskStateMachine:
    """
    Validates task state transitions.
    """

    VALID_TRANSITIONS = {
        TaskStatus.QUEUED: [TaskStatus.SCHEDULED, TaskStatus.IN_PROGRESS, TaskStatus.SKIPPED],
        TaskStatus.SCHEDULED: [TaskStatus.IN_PROGRESS, TaskStatus.QUEUED],
        TaskStatus.IN_PROGRESS: [
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.FAILED_WITH_TERMINAL_ERROR,
            TaskStatus.TIMED_OUT,
        ],
        TaskStatus.COMPLETED: [],  # Terminal state
        TaskStatus.FAILED: [TaskStatus.SCHEDULED, TaskStatus.QUEUED],  # Can retry
        TaskStatus.FAILED_WITH_TERMINAL_ERROR: [],  # Terminal state
        TaskStatus.TIMED_OUT: [TaskStatus.SCHEDULED, TaskStatus.QUEUED],  # Can retry
        TaskStatus.SKIPPED: [],  # Terminal state
    }

    @classmethod
    def can_transition(cls, from_status: TaskStatus, to_status: TaskStatus) -> bool:
        """Check if transition is valid."""
        valid_targets = cls.VALID_TRANSITIONS.get(from_status, [])
        return to_status in valid_targets

    @classmethod
    def transition(cls, current: TaskStatus, target: TaskStatus) -> TaskStatus:
        """Attempt state transition."""
        if not cls.can_transition(current, target):
            raise InvalidStateTransitionError(
                f"Cannot transition from {current} to {target}"
            )
        return target


class InvalidStateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def workflow_state_machine():
    """Create workflow state machine."""
    return WorkflowStateMachine()


@pytest.fixture
def task_state_machine():
    """Create task state machine."""
    return TaskStateMachine()


# ==============================================================================
# Workflow State Transition Tests
# ==============================================================================


class TestWorkflowPendingToRunning:
    """Tests for PENDING → RUNNING transition."""

    def test_pending_can_transition_to_running(self, workflow_state_machine):
        """GIVEN pending workflow WHEN starting THEN transitions to running."""
        result = workflow_state_machine.transition(
            WorkflowStatus.PENDING, WorkflowStatus.RUNNING
        )
        assert result == WorkflowStatus.RUNNING

    def test_pending_can_transition_to_terminated(self, workflow_state_machine):
        """GIVEN pending workflow WHEN terminated THEN transitions to terminated."""
        result = workflow_state_machine.transition(
            WorkflowStatus.PENDING, WorkflowStatus.TERMINATED
        )
        assert result == WorkflowStatus.TERMINATED


class TestWorkflowRunningToCompleted:
    """Tests for RUNNING → COMPLETED transition."""

    def test_running_can_transition_to_completed(self, workflow_state_machine):
        """GIVEN running workflow WHEN all tasks complete THEN transitions to completed."""
        result = workflow_state_machine.transition(
            WorkflowStatus.RUNNING, WorkflowStatus.COMPLETED
        )
        assert result == WorkflowStatus.COMPLETED


class TestWorkflowRunningToFailed:
    """Tests for RUNNING → FAILED transition."""

    def test_running_can_transition_to_failed(self, workflow_state_machine):
        """GIVEN running workflow WHEN task fails THEN transitions to failed."""
        result = workflow_state_machine.transition(
            WorkflowStatus.RUNNING, WorkflowStatus.FAILED
        )
        assert result == WorkflowStatus.FAILED


class TestWorkflowRunningToPaused:
    """Tests for RUNNING → PAUSED transition (HITL)."""

    def test_running_can_transition_to_paused(self, workflow_state_machine):
        """GIVEN running workflow WHEN HITL task starts THEN transitions to paused."""
        result = workflow_state_machine.transition(
            WorkflowStatus.RUNNING, WorkflowStatus.PAUSED
        )
        assert result == WorkflowStatus.PAUSED


class TestWorkflowPausedToRunning:
    """Tests for PAUSED → RUNNING transition (HITL resume)."""

    def test_paused_can_transition_to_running(self, workflow_state_machine):
        """GIVEN paused workflow WHEN HITL completes THEN transitions to running."""
        result = workflow_state_machine.transition(
            WorkflowStatus.PAUSED, WorkflowStatus.RUNNING
        )
        assert result == WorkflowStatus.RUNNING

    def test_paused_can_transition_to_terminated(self, workflow_state_machine):
        """GIVEN paused workflow WHEN terminated THEN transitions to terminated."""
        result = workflow_state_machine.transition(
            WorkflowStatus.PAUSED, WorkflowStatus.TERMINATED
        )
        assert result == WorkflowStatus.TERMINATED


class TestWorkflowFailedRestart:
    """Tests for FAILED → RUNNING transition (restart)."""

    def test_failed_can_restart(self, workflow_state_machine):
        """GIVEN failed workflow WHEN restarted THEN transitions to running."""
        result = workflow_state_machine.transition(
            WorkflowStatus.FAILED, WorkflowStatus.RUNNING
        )
        assert result == WorkflowStatus.RUNNING


class TestInvalidWorkflowTransitions:
    """Tests for invalid workflow state transitions."""

    def test_completed_cannot_transition(self, workflow_state_machine):
        """GIVEN completed workflow WHEN transitioning THEN raises error."""
        with pytest.raises(InvalidStateTransitionError):
            workflow_state_machine.transition(
                WorkflowStatus.COMPLETED, WorkflowStatus.RUNNING
            )

    def test_terminated_cannot_transition(self, workflow_state_machine):
        """GIVEN terminated workflow WHEN transitioning THEN raises error."""
        with pytest.raises(InvalidStateTransitionError):
            workflow_state_machine.transition(
                WorkflowStatus.TERMINATED, WorkflowStatus.RUNNING
            )

    def test_pending_cannot_go_to_completed(self, workflow_state_machine):
        """GIVEN pending workflow WHEN directly completing THEN raises error."""
        with pytest.raises(InvalidStateTransitionError):
            workflow_state_machine.transition(
                WorkflowStatus.PENDING, WorkflowStatus.COMPLETED
            )

    def test_pending_cannot_go_to_paused(self, workflow_state_machine):
        """GIVEN pending workflow WHEN pausing THEN raises error."""
        with pytest.raises(InvalidStateTransitionError):
            workflow_state_machine.transition(
                WorkflowStatus.PENDING, WorkflowStatus.PAUSED
            )


# ==============================================================================
# Task State Transition Tests
# ==============================================================================


class TestTaskQueuedToInProgress:
    """Tests for QUEUED → IN_PROGRESS transition."""

    def test_queued_can_transition_to_in_progress(self, task_state_machine):
        """GIVEN queued task WHEN picked up THEN transitions to in_progress."""
        result = task_state_machine.transition(
            TaskStatus.QUEUED, TaskStatus.IN_PROGRESS
        )
        assert result == TaskStatus.IN_PROGRESS

    def test_queued_can_transition_to_scheduled(self, task_state_machine):
        """GIVEN queued task WHEN scheduled THEN transitions to scheduled."""
        result = task_state_machine.transition(
            TaskStatus.QUEUED, TaskStatus.SCHEDULED
        )
        assert result == TaskStatus.SCHEDULED

    def test_queued_can_be_skipped(self, task_state_machine):
        """GIVEN queued task WHEN condition not met THEN can be skipped."""
        result = task_state_machine.transition(
            TaskStatus.QUEUED, TaskStatus.SKIPPED
        )
        assert result == TaskStatus.SKIPPED


class TestTaskInProgressToCompleted:
    """Tests for IN_PROGRESS → COMPLETED transition."""

    def test_in_progress_can_complete(self, task_state_machine):
        """GIVEN in_progress task WHEN succeeds THEN transitions to completed."""
        result = task_state_machine.transition(
            TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED
        )
        assert result == TaskStatus.COMPLETED


class TestTaskInProgressToFailed:
    """Tests for IN_PROGRESS → FAILED transition."""

    def test_in_progress_can_fail(self, task_state_machine):
        """GIVEN in_progress task WHEN fails THEN transitions to failed."""
        result = task_state_machine.transition(
            TaskStatus.IN_PROGRESS, TaskStatus.FAILED
        )
        assert result == TaskStatus.FAILED

    def test_in_progress_can_fail_terminal(self, task_state_machine):
        """GIVEN in_progress task WHEN terminal failure THEN transitions."""
        result = task_state_machine.transition(
            TaskStatus.IN_PROGRESS, TaskStatus.FAILED_WITH_TERMINAL_ERROR
        )
        assert result == TaskStatus.FAILED_WITH_TERMINAL_ERROR

    def test_in_progress_can_timeout(self, task_state_machine):
        """GIVEN in_progress task WHEN timeout THEN transitions to timed_out."""
        result = task_state_machine.transition(
            TaskStatus.IN_PROGRESS, TaskStatus.TIMED_OUT
        )
        assert result == TaskStatus.TIMED_OUT


class TestTaskRetryTransitions:
    """Tests for task retry state transitions."""

    def test_failed_can_retry(self, task_state_machine):
        """GIVEN failed task WHEN retrying THEN transitions to scheduled."""
        result = task_state_machine.transition(
            TaskStatus.FAILED, TaskStatus.SCHEDULED
        )
        assert result == TaskStatus.SCHEDULED

    def test_failed_can_requeue(self, task_state_machine):
        """GIVEN failed task WHEN requeuing THEN transitions to queued."""
        result = task_state_machine.transition(
            TaskStatus.FAILED, TaskStatus.QUEUED
        )
        assert result == TaskStatus.QUEUED

    def test_timed_out_can_retry(self, task_state_machine):
        """GIVEN timed_out task WHEN retrying THEN transitions to scheduled."""
        result = task_state_machine.transition(
            TaskStatus.TIMED_OUT, TaskStatus.SCHEDULED
        )
        assert result == TaskStatus.SCHEDULED


class TestInvalidTaskTransitions:
    """Tests for invalid task state transitions."""

    def test_completed_cannot_transition(self, task_state_machine):
        """GIVEN completed task WHEN transitioning THEN raises error."""
        with pytest.raises(InvalidStateTransitionError):
            task_state_machine.transition(
                TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS
            )

    def test_skipped_cannot_transition(self, task_state_machine):
        """GIVEN skipped task WHEN transitioning THEN raises error."""
        with pytest.raises(InvalidStateTransitionError):
            task_state_machine.transition(
                TaskStatus.SKIPPED, TaskStatus.IN_PROGRESS
            )

    def test_terminal_error_cannot_retry(self, task_state_machine):
        """GIVEN terminal error task WHEN retrying THEN raises error."""
        with pytest.raises(InvalidStateTransitionError):
            task_state_machine.transition(
                TaskStatus.FAILED_WITH_TERMINAL_ERROR, TaskStatus.SCHEDULED
            )

    def test_queued_cannot_complete(self, task_state_machine):
        """GIVEN queued task WHEN directly completing THEN raises error."""
        with pytest.raises(InvalidStateTransitionError):
            task_state_machine.transition(
                TaskStatus.QUEUED, TaskStatus.COMPLETED
            )


# ==============================================================================
# HITL State Transition Tests
# ==============================================================================


class TestHITLStateTransitions:
    """Tests specific to HITL pause/resume cycle."""

    def test_hitl_pause_workflow(self, workflow_state_machine):
        """GIVEN running workflow WHEN HITL task starts THEN pauses."""
        # Start workflow
        state = WorkflowStatus.PENDING
        state = workflow_state_machine.transition(state, WorkflowStatus.RUNNING)
        assert state == WorkflowStatus.RUNNING

        # HITL task pauses workflow
        state = workflow_state_machine.transition(state, WorkflowStatus.PAUSED)
        assert state == WorkflowStatus.PAUSED

    def test_hitl_resume_workflow(self, workflow_state_machine):
        """GIVEN paused workflow WHEN HITL completes THEN resumes."""
        state = WorkflowStatus.PAUSED

        # HITL completes, workflow resumes
        state = workflow_state_machine.transition(state, WorkflowStatus.RUNNING)
        assert state == WorkflowStatus.RUNNING

    def test_full_hitl_cycle(self, workflow_state_machine):
        """GIVEN workflow WHEN going through HITL THEN completes cycle."""
        state = WorkflowStatus.PENDING

        # Start
        state = workflow_state_machine.transition(state, WorkflowStatus.RUNNING)
        assert state == WorkflowStatus.RUNNING

        # HITL pause
        state = workflow_state_machine.transition(state, WorkflowStatus.PAUSED)
        assert state == WorkflowStatus.PAUSED

        # HITL resume
        state = workflow_state_machine.transition(state, WorkflowStatus.RUNNING)
        assert state == WorkflowStatus.RUNNING

        # Complete
        state = workflow_state_machine.transition(state, WorkflowStatus.COMPLETED)
        assert state == WorkflowStatus.COMPLETED


# ==============================================================================
# State Transition Validation Helper Tests
# ==============================================================================


class TestStateTransitionValidation:
    """Tests for state transition validation helpers."""

    def test_can_transition_returns_true_for_valid(self, workflow_state_machine):
        """GIVEN valid transition WHEN checking THEN returns True."""
        assert workflow_state_machine.can_transition(
            WorkflowStatus.RUNNING, WorkflowStatus.COMPLETED
        ) is True

    def test_can_transition_returns_false_for_invalid(self, workflow_state_machine):
        """GIVEN invalid transition WHEN checking THEN returns False."""
        assert workflow_state_machine.can_transition(
            WorkflowStatus.COMPLETED, WorkflowStatus.RUNNING
        ) is False

    def test_task_can_transition_valid(self, task_state_machine):
        """GIVEN valid task transition WHEN checking THEN returns True."""
        assert task_state_machine.can_transition(
            TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED
        ) is True

    def test_task_can_transition_invalid(self, task_state_machine):
        """GIVEN invalid task transition WHEN checking THEN returns False."""
        assert task_state_machine.can_transition(
            TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS
        ) is False


# ==============================================================================
# Full Workflow Lifecycle Tests
# ==============================================================================


class TestWorkflowLifecycle:
    """Tests for complete workflow state lifecycles."""

    def test_successful_workflow_lifecycle(self, workflow_state_machine):
        """GIVEN workflow WHEN successful THEN follows expected path."""
        state = WorkflowStatus.PENDING

        # Full successful path
        state = workflow_state_machine.transition(state, WorkflowStatus.RUNNING)
        state = workflow_state_machine.transition(state, WorkflowStatus.COMPLETED)

        assert state == WorkflowStatus.COMPLETED

    def test_failed_and_restart_lifecycle(self, workflow_state_machine):
        """GIVEN workflow WHEN fails and restarts THEN follows expected path."""
        state = WorkflowStatus.PENDING

        # Start and fail
        state = workflow_state_machine.transition(state, WorkflowStatus.RUNNING)
        state = workflow_state_machine.transition(state, WorkflowStatus.FAILED)
        assert state == WorkflowStatus.FAILED

        # Restart and complete
        state = workflow_state_machine.transition(state, WorkflowStatus.RUNNING)
        state = workflow_state_machine.transition(state, WorkflowStatus.COMPLETED)
        assert state == WorkflowStatus.COMPLETED

    def test_terminated_workflow_lifecycle(self, workflow_state_machine):
        """GIVEN workflow WHEN terminated THEN ends."""
        state = WorkflowStatus.RUNNING

        state = workflow_state_machine.transition(state, WorkflowStatus.TERMINATED)
        assert state == WorkflowStatus.TERMINATED

        # Cannot transition further
        assert not workflow_state_machine.can_transition(state, WorkflowStatus.RUNNING)


class TestTaskLifecycle:
    """Tests for complete task state lifecycles."""

    def test_successful_task_lifecycle(self, task_state_machine):
        """GIVEN task WHEN successful THEN follows expected path."""
        state = TaskStatus.QUEUED

        # Full successful path
        state = task_state_machine.transition(state, TaskStatus.IN_PROGRESS)
        state = task_state_machine.transition(state, TaskStatus.COMPLETED)

        assert state == TaskStatus.COMPLETED

    def test_retry_task_lifecycle(self, task_state_machine):
        """GIVEN task WHEN fails and retries THEN follows expected path."""
        state = TaskStatus.QUEUED

        # First attempt fails
        state = task_state_machine.transition(state, TaskStatus.IN_PROGRESS)
        state = task_state_machine.transition(state, TaskStatus.FAILED)
        assert state == TaskStatus.FAILED

        # Retry succeeds
        state = task_state_machine.transition(state, TaskStatus.SCHEDULED)
        state = task_state_machine.transition(state, TaskStatus.IN_PROGRESS)
        state = task_state_machine.transition(state, TaskStatus.COMPLETED)
        assert state == TaskStatus.COMPLETED

    def test_multiple_retry_lifecycle(self, task_state_machine):
        """GIVEN task WHEN fails multiple times THEN can retry each time."""
        state = TaskStatus.QUEUED

        for attempt in range(3):
            state = task_state_machine.transition(state, TaskStatus.IN_PROGRESS)
            if attempt < 2:
                state = task_state_machine.transition(state, TaskStatus.FAILED)
                state = task_state_machine.transition(state, TaskStatus.QUEUED)

        # Final attempt succeeds
        state = task_state_machine.transition(state, TaskStatus.COMPLETED)
        assert state == TaskStatus.COMPLETED
