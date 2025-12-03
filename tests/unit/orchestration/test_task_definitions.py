"""
Unit tests for the Task Definition Builder.

Tests cover:
- Building individual task definitions
- Timeout configuration
- Retry policy configuration
- Rate limit configuration
- Task validation
- HITL task definitions
"""

import pytest
from app.orchestration.conductor.task_definitions import TaskDefinitionBuilder


class TestTaskDefinitionBuilderExtraction:
    """Tests for extraction task definition."""

    def test_build_extraction_task_name(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building extraction task
        THEN name is 'document_extraction'
        """
        task = TaskDefinitionBuilder.build_extraction_task()

        assert task["name"] == "document_extraction"

    def test_build_extraction_task_has_description(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building extraction task
        THEN has meaningful description
        """
        task = TaskDefinitionBuilder.build_extraction_task()

        assert "description" in task
        assert len(task["description"]) > 0
        assert "VLLM" in task["description"] or "document" in task["description"].lower()

    def test_build_extraction_task_retry_config(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building extraction task
        THEN has appropriate retry configuration
        """
        task = TaskDefinitionBuilder.build_extraction_task()

        assert task["retryCount"] == 3
        assert task["retryLogic"] == "FIXED"
        assert task["retryDelaySeconds"] == 5

    def test_build_extraction_task_timeout_config(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building extraction task
        THEN has 5 minute timeout
        """
        task = TaskDefinitionBuilder.build_extraction_task()

        assert task["timeoutSeconds"] == 300
        assert task["responseTimeoutSeconds"] == 240
        assert task["pollTimeoutSeconds"] == 300

    def test_build_extraction_task_concurrency_limits(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building extraction task
        THEN has concurrency limits
        """
        task = TaskDefinitionBuilder.build_extraction_task()

        assert task["concurrentExecLimit"] == 10
        assert task["rateLimitPerFrequency"] == 100


class TestTaskDefinitionBuilderPythonRunner:
    """Tests for Python runner task definition."""

    def test_build_python_runner_task_name(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building Python runner task
        THEN name is 'python_runner'
        """
        task = TaskDefinitionBuilder.build_python_runner_task()

        assert task["name"] == "python_runner"

    def test_build_python_runner_task_docker_description(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building Python runner task
        THEN description mentions Docker sandbox
        """
        task = TaskDefinitionBuilder.build_python_runner_task()

        assert "Docker" in task["description"] or "sandbox" in task["description"].lower()

    def test_build_python_runner_task_limited_concurrency(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building Python runner task
        THEN has limited concurrency (Docker container limits)
        """
        task = TaskDefinitionBuilder.build_python_runner_task()

        # Should be lower than extraction due to Docker overhead
        assert task["concurrentExecLimit"] <= 10
        assert task["concurrentExecLimit"] == 5

    def test_build_python_runner_task_timeout(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building Python runner task
        THEN timeout accounts for script execution (5 min max)
        """
        task = TaskDefinitionBuilder.build_python_runner_task()

        # Should be slightly more than max script timeout
        assert task["timeoutSeconds"] >= 300
        assert task["responseTimeoutSeconds"] == 300


class TestTaskDefinitionBuilderHttpRequest:
    """Tests for HTTP request task definition."""

    def test_build_http_request_task_name(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building HTTP request task
        THEN name is 'http_request'
        """
        task = TaskDefinitionBuilder.build_http_request_task()

        assert task["name"] == "http_request"

    def test_build_http_request_task_exponential_backoff(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building HTTP request task
        THEN uses exponential backoff for retries
        """
        task = TaskDefinitionBuilder.build_http_request_task()

        assert task["retryLogic"] == "EXPONENTIAL_BACKOFF"
        assert task["backoffScaleFactor"] == 2

    def test_build_http_request_task_reasonable_timeout(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building HTTP request task
        THEN has reasonable timeout for HTTP operations
        """
        task = TaskDefinitionBuilder.build_http_request_task()

        assert task["timeoutSeconds"] == 120
        assert task["responseTimeoutSeconds"] == 90

    def test_build_http_request_task_high_concurrency(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building HTTP request task
        THEN allows high concurrency (HTTP is fast)
        """
        task = TaskDefinitionBuilder.build_http_request_task()

        assert task["concurrentExecLimit"] >= 50


class TestTaskDefinitionBuilderConditionEvaluator:
    """Tests for condition evaluator task definition."""

    def test_build_condition_evaluator_task_name(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building condition evaluator task
        THEN name is 'condition_evaluator'
        """
        task = TaskDefinitionBuilder.build_condition_evaluator_task()

        assert task["name"] == "condition_evaluator"

    def test_build_condition_evaluator_task_fast_timeout(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building condition evaluator task
        THEN has very fast timeout (condition eval is quick)
        """
        task = TaskDefinitionBuilder.build_condition_evaluator_task()

        assert task["timeoutSeconds"] == 10
        assert task["responseTimeoutSeconds"] == 5

    def test_build_condition_evaluator_task_minimal_retries(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building condition evaluator task
        THEN has minimal retries (deterministic operation)
        """
        task = TaskDefinitionBuilder.build_condition_evaluator_task()

        assert task["retryCount"] <= 2

    def test_build_condition_evaluator_task_high_rate_limit(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building condition evaluator task
        THEN allows high rate limit (lightweight operation)
        """
        task = TaskDefinitionBuilder.build_condition_evaluator_task()

        assert task["rateLimitPerFrequency"] >= 500


class TestTaskDefinitionBuilderHumanReview:
    """Tests for human review task definition."""

    def test_build_human_review_task_name(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building human review task
        THEN name is 'HUMAN_REVIEW'
        """
        task = TaskDefinitionBuilder.build_human_review_task()

        assert task["name"] == "HUMAN_REVIEW"

    def test_build_human_review_task_no_retries(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building human review task
        THEN has no retries (human tasks shouldn't retry)
        """
        task = TaskDefinitionBuilder.build_human_review_task()

        assert task["retryCount"] == 0

    def test_build_human_review_task_long_timeout(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building human review task
        THEN has long timeout (4 hours default)
        """
        task = TaskDefinitionBuilder.build_human_review_task()

        assert task["timeoutSeconds"] == 14400  # 4 hours
        assert task["responseTimeoutSeconds"] == 14400

    def test_build_human_review_task_alert_only_timeout_policy(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building human review task
        THEN timeout policy is ALERT_ONLY (don't fail workflow)
        """
        task = TaskDefinitionBuilder.build_human_review_task()

        assert task["timeoutPolicy"] == "ALERT_ONLY"

    def test_build_human_review_task_input_keys(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building human review task
        THEN has required input keys
        """
        task = TaskDefinitionBuilder.build_human_review_task()

        expected_keys = [
            "extraction_job_id",
            "confidence_score",
            "priority"
        ]

        for key in expected_keys:
            assert key in task["inputKeys"]

    def test_build_human_review_task_output_keys(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building human review task
        THEN has expected output keys
        """
        task = TaskDefinitionBuilder.build_human_review_task()

        expected_keys = [
            "review_request_id",
            "corrected_data",
            "corrections_count",
            "quality_score"
        ]

        for key in expected_keys:
            assert key in task["outputKeys"]


class TestTaskDefinitionBuilderAutoApprove:
    """Tests for auto-approve task definition."""

    def test_build_auto_approve_task_name(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building auto-approve task
        THEN name is 'auto_approve'
        """
        task = TaskDefinitionBuilder.build_auto_approve_task()

        assert task["name"] == "auto_approve"

    def test_build_auto_approve_task_fast_timeout(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building auto-approve task
        THEN has short timeout (auto-operation)
        """
        task = TaskDefinitionBuilder.build_auto_approve_task()

        assert task["timeoutSeconds"] == 60
        assert task["responseTimeoutSeconds"] == 30

    def test_build_auto_approve_task_retries(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building auto-approve task
        THEN has retries (should succeed on retry)
        """
        task = TaskDefinitionBuilder.build_auto_approve_task()

        assert task["retryCount"] >= 2

    def test_build_auto_approve_task_input_keys(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building auto-approve task
        THEN has required input keys
        """
        task = TaskDefinitionBuilder.build_auto_approve_task()

        assert "extraction_job_id" in task["inputKeys"]
        assert "confidence_score" in task["inputKeys"]


class TestTaskDefinitionBuilderFinalizeCorrections:
    """Tests for finalize corrections task definition."""

    def test_build_finalize_corrections_task_name(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building finalize corrections task
        THEN name is 'finalize_with_corrections'
        """
        task = TaskDefinitionBuilder.build_finalize_corrections_task()

        assert task["name"] == "finalize_with_corrections"

    def test_build_finalize_corrections_task_input_keys(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building finalize corrections task
        THEN has required input keys
        """
        task = TaskDefinitionBuilder.build_finalize_corrections_task()

        expected_keys = [
            "extraction_job_id",
            "corrected_data",
            "corrections_count"
        ]

        for key in expected_keys:
            assert key in task["inputKeys"]

    def test_build_finalize_corrections_task_output_keys(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building finalize corrections task
        THEN has expected output keys
        """
        task = TaskDefinitionBuilder.build_finalize_corrections_task()

        assert "finalization_status" in task["outputKeys"]
        assert "final_data" in task["outputKeys"]


class TestTaskDefinitionBuilderAllTasks:
    """Tests for building all task definitions."""

    def test_build_all_task_definitions_count(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building all tasks
        THEN returns 7 task definitions
        """
        tasks = TaskDefinitionBuilder.build_all_task_definitions()

        assert len(tasks) == 7

    def test_build_all_task_definitions_unique_names(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building all tasks
        THEN all task names are unique
        """
        tasks = TaskDefinitionBuilder.build_all_task_definitions()
        names = [t["name"] for t in tasks]

        assert len(names) == len(set(names))

    def test_build_all_task_definitions_includes_core_tasks(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building all tasks
        THEN includes all core task types
        """
        tasks = TaskDefinitionBuilder.build_all_task_definitions()
        names = [t["name"] for t in tasks]

        expected_names = [
            "document_extraction",
            "python_runner",
            "http_request",
            "condition_evaluator"
        ]

        for name in expected_names:
            assert name in names

    def test_build_all_task_definitions_includes_hitl_tasks(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building all tasks
        THEN includes HITL task types
        """
        tasks = TaskDefinitionBuilder.build_all_task_definitions()
        names = [t["name"] for t in tasks]

        hitl_names = [
            "HUMAN_REVIEW",
            "auto_approve",
            "finalize_with_corrections"
        ]

        for name in hitl_names:
            assert name in names


class TestTaskDefinitionBuilderHitlTasks:
    """Tests for building HITL-only task definitions."""

    def test_build_hitl_task_definitions_count(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building HITL tasks only
        THEN returns 3 task definitions
        """
        tasks = TaskDefinitionBuilder.build_hitl_task_definitions()

        assert len(tasks) == 3

    def test_build_hitl_task_definitions_names(self):
        """
        GIVEN TaskDefinitionBuilder
        WHEN building HITL tasks only
        THEN includes only HITL-related tasks
        """
        tasks = TaskDefinitionBuilder.build_hitl_task_definitions()
        names = [t["name"] for t in tasks]

        assert "HUMAN_REVIEW" in names
        assert "auto_approve" in names
        assert "finalize_with_corrections" in names

        # Should not include core tasks
        assert "document_extraction" not in names
        assert "python_runner" not in names


class TestTaskDefinitionBuilderValidation:
    """Tests for task definition validation."""

    def test_validate_valid_task_definition(self):
        """
        GIVEN a valid task definition
        WHEN validating
        THEN returns (True, '')
        """
        task = TaskDefinitionBuilder.build_extraction_task()

        is_valid, error = TaskDefinitionBuilder.validate_task_definition(task)

        assert is_valid is True
        assert error == ""

    def test_validate_missing_name(self):
        """
        GIVEN task definition missing name
        WHEN validating
        THEN returns (False, error message)
        """
        task = {
            "timeoutSeconds": 300,
            "responseTimeoutSeconds": 240
        }

        is_valid, error = TaskDefinitionBuilder.validate_task_definition(task)

        assert is_valid is False
        assert "name" in error

    def test_validate_missing_timeout_seconds(self):
        """
        GIVEN task definition missing timeoutSeconds
        WHEN validating
        THEN returns (False, error message)
        """
        task = {
            "name": "test_task",
            "responseTimeoutSeconds": 240
        }

        is_valid, error = TaskDefinitionBuilder.validate_task_definition(task)

        assert is_valid is False
        assert "timeoutSeconds" in error

    def test_validate_missing_response_timeout(self):
        """
        GIVEN task definition missing responseTimeoutSeconds
        WHEN validating
        THEN returns (False, error message)
        """
        task = {
            "name": "test_task",
            "timeoutSeconds": 300
        }

        is_valid, error = TaskDefinitionBuilder.validate_task_definition(task)

        assert is_valid is False
        assert "responseTimeoutSeconds" in error

    def test_validate_zero_timeout(self):
        """
        GIVEN task definition with zero timeout
        WHEN validating
        THEN returns (False, error message)
        """
        task = {
            "name": "test_task",
            "timeoutSeconds": 0,
            "responseTimeoutSeconds": 0
        }

        is_valid, error = TaskDefinitionBuilder.validate_task_definition(task)

        assert is_valid is False
        assert "positive" in error.lower()

    def test_validate_negative_timeout(self):
        """
        GIVEN task definition with negative timeout
        WHEN validating
        THEN returns (False, error message)
        """
        task = {
            "name": "test_task",
            "timeoutSeconds": -100,
            "responseTimeoutSeconds": 50
        }

        is_valid, error = TaskDefinitionBuilder.validate_task_definition(task)

        assert is_valid is False
        assert "positive" in error.lower()

    def test_validate_response_timeout_exceeds_timeout(self):
        """
        GIVEN responseTimeoutSeconds > timeoutSeconds
        WHEN validating
        THEN returns (False, error message)
        """
        task = {
            "name": "test_task",
            "timeoutSeconds": 100,
            "responseTimeoutSeconds": 200
        }

        is_valid, error = TaskDefinitionBuilder.validate_task_definition(task)

        assert is_valid is False
        assert "exceed" in error.lower()

    def test_validate_all_built_tasks_are_valid(self):
        """
        GIVEN all built task definitions
        WHEN validating each
        THEN all are valid
        """
        tasks = TaskDefinitionBuilder.build_all_task_definitions()

        for task in tasks:
            is_valid, error = TaskDefinitionBuilder.validate_task_definition(task)
            assert is_valid, f"Task '{task['name']}' is invalid: {error}"


class TestTaskDefinitionBuilderCommonFields:
    """Tests for common fields across all task definitions."""

    def test_all_tasks_have_owner_email(self):
        """
        GIVEN all task definitions
        WHEN checking for ownerEmail
        THEN all have ownerEmail set
        """
        tasks = TaskDefinitionBuilder.build_all_task_definitions()

        for task in tasks:
            assert "ownerEmail" in task
            assert "@" in task["ownerEmail"]

    def test_all_tasks_have_timeout_policy(self):
        """
        GIVEN all task definitions
        WHEN checking for timeoutPolicy
        THEN all have timeoutPolicy set
        """
        tasks = TaskDefinitionBuilder.build_all_task_definitions()

        for task in tasks:
            assert "timeoutPolicy" in task
            assert task["timeoutPolicy"] in ["TIME_OUT_WF", "ALERT_ONLY"]

    def test_all_tasks_have_rate_limits(self):
        """
        GIVEN all task definitions
        WHEN checking for rate limits
        THEN all have rate limit configuration
        """
        tasks = TaskDefinitionBuilder.build_all_task_definitions()

        for task in tasks:
            assert "rateLimitFrequencyInSeconds" in task
            assert "rateLimitPerFrequency" in task
            assert task["rateLimitPerFrequency"] > 0

    def test_all_tasks_have_concurrent_exec_limit(self):
        """
        GIVEN all task definitions
        WHEN checking for concurrency limit
        THEN all have concurrentExecLimit
        """
        tasks = TaskDefinitionBuilder.build_all_task_definitions()

        for task in tasks:
            assert "concurrentExecLimit" in task
            assert task["concurrentExecLimit"] > 0
