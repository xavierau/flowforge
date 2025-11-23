"""
Base Worker for Conductor Tasks

Provides common functionality for all workflow workers including:
- Error handling
- Logging
- Input validation
- Output formatting
- Retry logic
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
from datetime import datetime

from conductor.client.worker.worker_interface import WorkerInterface
from conductor.client.worker.worker_task import WorkerTask

logger = logging.getLogger(__name__)


class BaseWorker(WorkerInterface, ABC):
    """
    Abstract base class for all Conductor workers.

    Subclasses must implement:
    - execute_task(task_input: Dict[str, Any]) -> Dict[str, Any]
    """

    def __init__(self, task_definition_name: str, poll_interval: int = 1000):
        """
        Initialize base worker.

        Args:
            task_definition_name: Name of the Conductor task this worker handles
            poll_interval: Polling interval in milliseconds (default: 1000ms)
        """
        self.task_definition_name = task_definition_name
        self.poll_interval = poll_interval
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get_task_definition_name(self) -> str:
        """Return the task definition name this worker handles."""
        return self.task_definition_name

    def get_polling_interval_in_seconds(self) -> float:
        """Return polling interval in seconds."""
        return self.poll_interval / 1000.0

    def execute(self, task: WorkerTask) -> Any:
        """
        Execute the task (called by Conductor framework).

        This method handles common operations:
        - Input extraction
        - Error handling
        - Logging
        - Result formatting

        Args:
            task: Conductor task object

        Returns:
            TaskResult with status and output data
        """
        task_result = self.get_task_result_from_task(task)
        task_id = task.task_id
        execution_start = datetime.utcnow()

        try:
            self._logger.info(
                f"Executing task {self.task_definition_name} (ID: {task_id})"
            )

            # Extract input data
            task_input = task.input_data or {}
            self._logger.debug(f"Task input: {task_input}")

            # Validate input
            validation_error = self.validate_input(task_input)
            if validation_error:
                self._logger.error(f"Input validation failed: {validation_error}")
                task_result.status = "FAILED"
                task_result.reason_for_incompletion = validation_error
                task_result.add_output_data("error", validation_error)
                return task_result

            # Execute the actual task logic
            output = self.execute_task(task_input)

            # Mark as completed
            task_result.status = "COMPLETED"
            task_result.add_output_data("data", output)
            task_result.add_output_data("success", True)

            execution_time = (datetime.utcnow() - execution_start).total_seconds()
            self._logger.info(
                f"Task {self.task_definition_name} completed successfully "
                f"in {execution_time:.2f}s (ID: {task_id})"
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - execution_start).total_seconds()
            error_msg = f"Task execution failed: {str(e)}"
            self._logger.error(
                f"Task {self.task_definition_name} failed after {execution_time:.2f}s "
                f"(ID: {task_id}): {error_msg}",
                exc_info=True
            )

            task_result.status = "FAILED"
            task_result.reason_for_incompletion = error_msg
            task_result.add_output_data("error", error_msg)
            task_result.add_output_data("success", False)

        return task_result

    @abstractmethod
    def execute_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the core task logic (implemented by subclasses).

        Args:
            task_input: Input data for the task

        Returns:
            Output data from task execution

        Raises:
            Exception: Any error during execution
        """
        pass

    def validate_input(self, task_input: Dict[str, Any]) -> Optional[str]:
        """
        Validate task input (can be overridden by subclasses).

        Args:
            task_input: Input data to validate

        Returns:
            Error message if validation fails, None if valid
        """
        return None

    def log_info(self, message: str):
        """Log info message."""
        self._logger.info(message)

    def log_debug(self, message: str):
        """Log debug message."""
        self._logger.debug(message)

    def log_warning(self, message: str):
        """Log warning message."""
        self._logger.warning(message)

    def log_error(self, message: str, exc_info: bool = False):
        """Log error message."""
        self._logger.error(message, exc_info=exc_info)
