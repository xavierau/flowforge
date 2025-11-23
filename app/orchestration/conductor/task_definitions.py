"""
Task Definition Templates

Provides template definitions for Conductor tasks.
Used when registering tasks with Conductor server.
"""

from typing import Dict, Any


class TaskDefinitionBuilder:
    """
    Builder for Conductor task definitions.

    Provides templates and builders for all supported task types.
    """

    @staticmethod
    def build_extraction_task() -> Dict[str, Any]:
        """Build task definition for document extraction."""
        return {
            "name": "document_extraction",
            "description": "Extracts structured data from documents using VLLM",
            "retryCount": 3,
            "retryLogic": "FIXED",
            "retryDelaySeconds": 5,
            "timeoutSeconds": 300,  # 5 minutes
            "responseTimeoutSeconds": 240,
            "pollTimeoutSeconds": 300,
            "timeoutPolicy": "TIME_OUT_WF",
            "concurrentExecLimit": 10,
            "rateLimitFrequencyInSeconds": 1,
            "rateLimitPerFrequency": 100,
            "ownerEmail": "workflow@ai-document-processing.com",
        }

    @staticmethod
    def build_python_runner_task() -> Dict[str, Any]:
        """Build task definition for Python code execution."""
        return {
            "name": "python_runner",
            "description": "Executes Python code in secure Docker sandbox",
            "retryCount": 2,
            "retryLogic": "FIXED",
            "retryDelaySeconds": 3,
            "timeoutSeconds": 360,  # 6 minutes (max script timeout is 5 min)
            "responseTimeoutSeconds": 300,
            "pollTimeoutSeconds": 360,
            "timeoutPolicy": "TIME_OUT_WF",
            "concurrentExecLimit": 5,  # Limit concurrent Docker containers
            "rateLimitFrequencyInSeconds": 1,
            "rateLimitPerFrequency": 20,
            "ownerEmail": "workflow@ai-document-processing.com",
        }

    @staticmethod
    def build_http_request_task() -> Dict[str, Any]:
        """Build task definition for HTTP requests."""
        return {
            "name": "http_request",
            "description": "Executes HTTP requests with retry logic",
            "retryCount": 3,
            "retryLogic": "EXPONENTIAL_BACKOFF",
            "retryDelaySeconds": 2,
            "backoffScaleFactor": 2,
            "timeoutSeconds": 120,  # 2 minutes
            "responseTimeoutSeconds": 90,
            "pollTimeoutSeconds": 120,
            "timeoutPolicy": "TIME_OUT_WF",
            "concurrentExecLimit": 50,
            "rateLimitFrequencyInSeconds": 1,
            "rateLimitPerFrequency": 100,
            "ownerEmail": "workflow@ai-document-processing.com",
        }

    @staticmethod
    def build_condition_evaluator_task() -> Dict[str, Any]:
        """Build task definition for condition evaluation."""
        return {
            "name": "condition_evaluator",
            "description": "Evaluates conditional expressions for workflow branching",
            "retryCount": 1,
            "retryLogic": "FIXED",
            "retryDelaySeconds": 1,
            "timeoutSeconds": 10,
            "responseTimeoutSeconds": 5,
            "pollTimeoutSeconds": 10,
            "timeoutPolicy": "TIME_OUT_WF",
            "concurrentExecLimit": 100,
            "rateLimitFrequencyInSeconds": 1,
            "rateLimitPerFrequency": 500,
            "ownerEmail": "workflow@ai-document-processing.com",
        }

    @staticmethod
    def build_all_task_definitions() -> list[Dict[str, Any]]:
        """
        Build all task definitions.

        Returns:
            List of all task definitions for registration
        """
        return [
            TaskDefinitionBuilder.build_extraction_task(),
            TaskDefinitionBuilder.build_python_runner_task(),
            TaskDefinitionBuilder.build_http_request_task(),
            TaskDefinitionBuilder.build_condition_evaluator_task(),
        ]

    @staticmethod
    def validate_task_definition(task_def: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate a task definition.

        Args:
            task_def: Task definition to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ["name", "timeoutSeconds", "responseTimeoutSeconds"]

        for field in required_fields:
            if field not in task_def:
                return False, f"Missing required field: {field}"

        # Validate timeout values
        if task_def["timeoutSeconds"] <= 0:
            return False, "timeoutSeconds must be positive"

        if task_def["responseTimeoutSeconds"] <= 0:
            return False, "responseTimeoutSeconds must be positive"

        if task_def["responseTimeoutSeconds"] > task_def["timeoutSeconds"]:
            return False, "responseTimeoutSeconds cannot exceed timeoutSeconds"

        return True, ""
