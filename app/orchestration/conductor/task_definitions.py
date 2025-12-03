"""
Task Definition Templates

Provides template definitions for Conductor tasks.
Used when registering tasks with Conductor server.

Task Types Supported:
- document_extraction: VLLM-based document extraction
- python_runner: Python code execution in Docker sandbox
- http_request: HTTP requests with retry logic
- condition_evaluator: Conditional expression evaluation
- HUMAN_REVIEW: Human-in-the-loop review tasks

HUMAN_REVIEW Task:
The HUMAN_REVIEW task is a special task type for human intervention.
Unlike other tasks that are executed by workers and return COMPLETED,
HUMAN_REVIEW tasks:
1. Are picked up by HumanReviewWorker
2. Create a ReviewRequest in the database
3. Return IN_PROGRESS status (workflow pauses)
4. Are completed via ConductorHITLService when review is submitted
5. Resume workflow with corrected_data in output
"""

from typing import Dict, Any, List


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
    def build_human_review_task() -> Dict[str, Any]:
        """
        Build task definition for HUMAN_REVIEW tasks.

        HUMAN_REVIEW is a special task type for human-in-the-loop workflows:
        - Worker creates ReviewRequest, returns IN_PROGRESS
        - Workflow pauses until human submits review
        - ConductorHITLService completes task with corrected_data
        - Workflow resumes with review output

        Input Parameters:
        - extraction_job_id (required): ID of extraction job to review
        - confidence_score (required): AI confidence score (0.0-1.0)
        - trigger_reason (optional): Why review is needed
        - conductor_task_id: Auto-populated by workflow
        - conductor_workflow_id: Auto-populated by workflow

        Output Parameters (after human review):
        - review_request_id: Created review request ID
        - corrected_data: Human-corrected extraction data
        - corrections_count: Number of corrections made
        - quality_score: Quality score based on corrections
        - review_notes: Notes from reviewer

        Returns:
            Task definition dictionary
        """
        return {
            "name": "HUMAN_REVIEW",
            "description": "Human-in-the-loop review task for document extraction verification",
            "retryCount": 0,  # No retries - human tasks should not be retried
            "timeoutSeconds": 14400,  # 4 hours default timeout
            "responseTimeoutSeconds": 14400,
            "pollTimeoutSeconds": 14400,
            "timeoutPolicy": "ALERT_ONLY",  # Don't fail workflow on timeout, just alert
            "concurrentExecLimit": 100,  # Many reviews can be pending
            "rateLimitFrequencyInSeconds": 1,
            "rateLimitPerFrequency": 50,
            "ownerEmail": "workflow@ai-document-processing.com",
            "inputKeys": [
                "extraction_job_id",
                "confidence_score",
                "trigger_reason",
                "priority",
                "instructions",
                "assignment_strategy",
                "reviewer_pool",
            ],
            "outputKeys": [
                "review_request_id",
                "corrected_data",
                "corrections_count",
                "quality_score",
                "review_notes",
                "completed_at",
                "corrections",
            ],
        }

    @staticmethod
    def build_auto_approve_task() -> Dict[str, Any]:
        """
        Build task definition for auto-approving high-confidence extractions.

        This task is used in confidence-based routing workflows when the
        extraction confidence is above the threshold and no human review
        is needed.

        Returns:
            Task definition dictionary
        """
        return {
            "name": "auto_approve",
            "description": "Auto-approve high-confidence extraction without human review",
            "retryCount": 3,
            "retryLogic": "FIXED",
            "retryDelaySeconds": 5,
            "timeoutSeconds": 60,
            "responseTimeoutSeconds": 30,
            "pollTimeoutSeconds": 60,
            "timeoutPolicy": "TIME_OUT_WF",
            "concurrentExecLimit": 100,
            "rateLimitFrequencyInSeconds": 1,
            "rateLimitPerFrequency": 200,
            "ownerEmail": "workflow@ai-document-processing.com",
            "inputKeys": [
                "extraction_job_id",
                "approval_reason",
                "confidence_score",
            ],
            "outputKeys": [
                "approval_status",
                "approved_at",
                "final_data",
            ],
        }

    @staticmethod
    def build_finalize_corrections_task() -> Dict[str, Any]:
        """
        Build task definition for finalizing extraction with corrections.

        This task is called after human review to apply corrections
        and finalize the extraction job.

        Returns:
            Task definition dictionary
        """
        return {
            "name": "finalize_with_corrections",
            "description": "Finalize extraction job with human corrections applied",
            "retryCount": 3,
            "retryLogic": "FIXED",
            "retryDelaySeconds": 5,
            "timeoutSeconds": 120,
            "responseTimeoutSeconds": 60,
            "pollTimeoutSeconds": 120,
            "timeoutPolicy": "TIME_OUT_WF",
            "concurrentExecLimit": 50,
            "rateLimitFrequencyInSeconds": 1,
            "rateLimitPerFrequency": 100,
            "ownerEmail": "workflow@ai-document-processing.com",
            "inputKeys": [
                "extraction_job_id",
                "corrected_data",
                "corrections_count",
                "review_request_id",
            ],
            "outputKeys": [
                "finalization_status",
                "finalized_at",
                "final_data",
            ],
        }

    @staticmethod
    def build_all_task_definitions() -> List[Dict[str, Any]]:
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
            # HITL-related task definitions
            TaskDefinitionBuilder.build_human_review_task(),
            TaskDefinitionBuilder.build_auto_approve_task(),
            TaskDefinitionBuilder.build_finalize_corrections_task(),
        ]

    @staticmethod
    def build_hitl_task_definitions() -> List[Dict[str, Any]]:
        """
        Build only HITL-related task definitions.

        Returns:
            List of HITL task definitions for registration
        """
        return [
            TaskDefinitionBuilder.build_human_review_task(),
            TaskDefinitionBuilder.build_auto_approve_task(),
            TaskDefinitionBuilder.build_finalize_corrections_task(),
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
