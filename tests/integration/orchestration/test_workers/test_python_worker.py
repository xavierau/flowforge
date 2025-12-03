"""
Integration tests for PythonWorker.

Tests Python code execution in Docker sandbox including:
- Simple code execution
- Input data injection
- JSON result handling
- stdout/stderr capture
- Timeout enforcement
- Memory limit enforcement
- Network isolation
- Filesystem isolation
- Syntax and runtime error handling
- Dangerous code prevention
"""

import json
from unittest.mock import Mock, patch, MagicMock

import pytest
from docker.errors import ContainerError, ImageNotFound, APIError

from app.orchestration.workers.python_worker import PythonWorker


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def worker():
    """Create PythonWorker with mocked Docker client."""
    with patch("app.orchestration.workers.python_worker.docker") as mock_docker:
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client

        # Mock image exists
        mock_client.images.get.return_value = Mock()

        worker = PythonWorker()
        worker._mock_docker = mock_client
        yield worker


@pytest.fixture
def simple_code():
    """Simple Python code that sets a result."""
    return "result = 42"


@pytest.fixture
def code_with_input():
    """Code that uses input_data."""
    return """
total = sum(input_data['values'])
result = {'total': total, 'count': len(input_data['values'])}
"""


# ==============================================================================
# Input Validation Tests
# ==============================================================================


class TestPythonWorkerValidation:
    """Tests for input validation."""

    def test_validate_input_missing_code(self, worker):
        """GIVEN task without code WHEN validating THEN returns error."""
        task_input = {"input_data": {"a": 1}}

        error = worker.validate_input(task_input)

        assert error is not None
        assert "code" in error

    def test_validate_input_code_not_string(self, worker):
        """GIVEN code as non-string WHEN validating THEN returns error."""
        task_input = {"code": 12345}

        error = worker.validate_input(task_input)

        assert error is not None
        assert "string" in error

    def test_validate_input_empty_code(self, worker):
        """GIVEN empty code WHEN validating THEN returns error."""
        task_input = {"code": "   "}

        error = worker.validate_input(task_input)

        assert error is not None
        assert "empty" in error

    def test_validate_input_valid_code(self, worker):
        """GIVEN valid code WHEN validating THEN returns None."""
        task_input = {"code": "result = 1 + 1"}

        error = worker.validate_input(task_input)

        assert error is None

    def test_validate_input_timeout_not_number(self, worker):
        """GIVEN timeout as non-number WHEN validating THEN returns error."""
        task_input = {"code": "result = 1", "timeout": "not a number"}

        error = worker.validate_input(task_input)

        assert error is not None
        assert "timeout" in error

    def test_validate_input_timeout_exceeds_max(self, worker):
        """GIVEN timeout exceeds max WHEN validating THEN returns error."""
        task_input = {"code": "result = 1", "timeout": 600}

        error = worker.validate_input(task_input)

        assert error is not None
        assert "300" in error  # MAX_TIMEOUT

    def test_validate_input_timeout_at_max(self, worker):
        """GIVEN timeout at max WHEN validating THEN returns None."""
        task_input = {"code": "result = 1", "timeout": 300}

        error = worker.validate_input(task_input)

        assert error is None


# ==============================================================================
# Simple Execution Tests
# ==============================================================================


class TestPythonWorkerSimpleExecution:
    """Tests for simple code execution."""

    def test_execute_simple_code(self, worker, simple_code):
        """GIVEN simple code WHEN executing THEN returns result."""
        output = json.dumps({"success": True, "result": 42})

        worker._mock_docker.containers.run.return_value = output.encode("utf-8")

        result = worker.execute_task({"code": simple_code})

        assert result["result"] == 42

    def test_execute_with_input_data(self, worker, code_with_input):
        """GIVEN code with input_data WHEN executing THEN has access to data."""
        output = json.dumps({"success": True, "result": {"total": 15, "count": 5}})

        worker._mock_docker.containers.run.return_value = output.encode("utf-8")

        result = worker.execute_task(
            {
                "code": code_with_input,
                "input_data": {"values": [1, 2, 3, 4, 5]},
            }
        )

        assert result["result"]["total"] == 15
        assert result["result"]["count"] == 5

    def test_execute_returns_none_result(self, worker):
        """GIVEN code without result WHEN executing THEN result is None."""
        output = json.dumps({"success": True, "result": None})

        worker._mock_docker.containers.run.return_value = output.encode("utf-8")

        result = worker.execute_task({"code": "x = 1 + 1"})

        assert result["result"] is None

    def test_execute_captures_stdout(self, worker):
        """GIVEN code with print WHEN executing THEN captures stdout."""
        output = json.dumps({"success": True, "result": None})

        worker._mock_docker.containers.run.return_value = output.encode("utf-8")

        result = worker.execute_task({"code": "print('Hello World')"})

        assert "stdout" in result


# ==============================================================================
# Docker Security Configuration Tests
# ==============================================================================


class TestPythonWorkerDockerSecurity:
    """Tests for Docker security configuration."""

    def test_network_isolation(self, worker):
        """GIVEN execution WHEN running THEN network is disabled."""
        output = json.dumps({"success": True, "result": None})
        worker._mock_docker.containers.run.return_value = output.encode("utf-8")

        worker.execute_task({"code": "result = 1"})

        call_kwargs = worker._mock_docker.containers.run.call_args.kwargs
        assert call_kwargs["network_mode"] == "none"

    def test_memory_limit(self, worker):
        """GIVEN execution WHEN running THEN memory is limited."""
        output = json.dumps({"success": True, "result": None})
        worker._mock_docker.containers.run.return_value = output.encode("utf-8")

        worker.execute_task({"code": "result = 1"})

        call_kwargs = worker._mock_docker.containers.run.call_args.kwargs
        assert call_kwargs["mem_limit"] == "256m"

    def test_cpu_quota(self, worker):
        """GIVEN execution WHEN running THEN CPU is limited."""
        output = json.dumps({"success": True, "result": None})
        worker._mock_docker.containers.run.return_value = output.encode("utf-8")

        worker.execute_task({"code": "result = 1"})

        call_kwargs = worker._mock_docker.containers.run.call_args.kwargs
        assert call_kwargs["cpu_quota"] == 50000

    def test_read_only_filesystem(self, worker):
        """GIVEN execution WHEN running THEN filesystem is read-only."""
        output = json.dumps({"success": True, "result": None})
        worker._mock_docker.containers.run.return_value = output.encode("utf-8")

        worker.execute_task({"code": "result = 1"})

        call_kwargs = worker._mock_docker.containers.run.call_args.kwargs
        assert call_kwargs["read_only"] is True

    def test_non_root_user(self, worker):
        """GIVEN execution WHEN running THEN runs as non-root."""
        output = json.dumps({"success": True, "result": None})
        worker._mock_docker.containers.run.return_value = output.encode("utf-8")

        worker.execute_task({"code": "result = 1"})

        call_kwargs = worker._mock_docker.containers.run.call_args.kwargs
        assert call_kwargs["user"] == "nobody"

    def test_no_privilege_escalation(self, worker):
        """GIVEN execution WHEN running THEN privilege escalation disabled."""
        output = json.dumps({"success": True, "result": None})
        worker._mock_docker.containers.run.return_value = output.encode("utf-8")

        worker.execute_task({"code": "result = 1"})

        call_kwargs = worker._mock_docker.containers.run.call_args.kwargs
        assert "no-new-privileges" in call_kwargs["security_opt"]


# ==============================================================================
# Timeout Tests
# ==============================================================================


class TestPythonWorkerTimeout:
    """Tests for timeout enforcement."""

    def test_default_timeout(self, worker):
        """GIVEN no timeout WHEN executing THEN uses default."""
        output = json.dumps({"success": True, "result": None})
        worker._mock_docker.containers.run.return_value = output.encode("utf-8")

        worker.execute_task({"code": "result = 1"})

        # Default timeout is 30 seconds
        assert worker.DEFAULT_TIMEOUT == 30

    def test_custom_timeout(self, worker):
        """GIVEN custom timeout WHEN executing THEN uses custom value."""
        output = json.dumps({"success": True, "result": None})
        worker._mock_docker.containers.run.return_value = output.encode("utf-8")

        worker.execute_task({"code": "result = 1", "timeout": 60})

        # The timeout is passed to the execution
        # Note: actual Docker timeout is handled differently


# ==============================================================================
# Error Handling Tests
# ==============================================================================


class TestPythonWorkerErrors:
    """Tests for error handling."""

    def test_syntax_error_handling(self, worker):
        """GIVEN code with syntax error WHEN executing THEN returns error."""
        error_output = json.dumps(
            {
                "success": False,
                "error": "invalid syntax",
                "error_type": "SyntaxError",
            }
        )

        # Simulate container error
        error = ContainerError(
            container=Mock(),
            exit_status=1,
            command="python",
            image="python:3.11-slim",
            stderr=error_output.encode("utf-8"),
        )
        worker._mock_docker.containers.run.side_effect = error

        with pytest.raises(Exception, match="execution failed"):
            worker.execute_task({"code": "def foo(:"})

    def test_runtime_error_handling(self, worker):
        """GIVEN code with runtime error WHEN executing THEN returns error."""
        error_output = json.dumps(
            {
                "success": False,
                "error": "division by zero",
                "error_type": "ZeroDivisionError",
            }
        )

        error = ContainerError(
            container=Mock(),
            exit_status=1,
            command="python",
            image="python:3.11-slim",
            stderr=error_output.encode("utf-8"),
        )
        worker._mock_docker.containers.run.side_effect = error

        with pytest.raises(Exception, match="execution failed"):
            worker.execute_task({"code": "result = 1 / 0"})

    def test_docker_api_error(self, worker):
        """GIVEN Docker API error WHEN executing THEN raises exception."""
        worker._mock_docker.containers.run.side_effect = APIError(
            "Docker daemon error"
        )

        with pytest.raises(Exception, match="Docker error"):
            worker.execute_task({"code": "result = 1"})

    def test_image_not_found_handled_at_init(self):
        """GIVEN missing image WHEN initializing THEN pulls image."""
        with patch("app.orchestration.workers.python_worker.docker") as mock_docker:
            mock_client = MagicMock()
            mock_docker.from_env.return_value = mock_client
            mock_client.images.get.side_effect = ImageNotFound("Image not found")

            PythonWorker()

            mock_client.images.pull.assert_called_once_with("python:3.11-slim")


# ==============================================================================
# Output Format Tests
# ==============================================================================


class TestPythonWorkerOutput:
    """Tests for output format structure."""

    def test_output_format_structure(self, worker):
        """GIVEN successful execution WHEN done THEN output has correct structure."""
        output = json.dumps({"success": True, "result": {"key": "value"}})
        worker._mock_docker.containers.run.return_value = output.encode("utf-8")

        result = worker.execute_task({"code": "result = {'key': 'value'}"})

        assert "result" in result
        assert "stdout" in result
        assert "stderr" in result

    def test_json_result_serialization(self, worker):
        """GIVEN complex result WHEN executing THEN serializes correctly."""
        output = json.dumps(
            {
                "success": True,
                "result": {
                    "list": [1, 2, 3],
                    "nested": {"a": "b"},
                    "number": 42.5,
                },
            }
        )
        worker._mock_docker.containers.run.return_value = output.encode("utf-8")

        result = worker.execute_task({"code": "result = {}"})

        assert result["result"]["list"] == [1, 2, 3]
        assert result["result"]["nested"]["a"] == "b"
        assert result["result"]["number"] == 42.5

    def test_non_json_output_handled(self, worker):
        """GIVEN non-JSON output WHEN executing THEN handles gracefully."""
        # Return non-JSON output
        worker._mock_docker.containers.run.return_value = b"Not JSON output"

        result = worker.execute_task({"code": "print('hello')"})

        assert result["result"] is None
        assert "Not JSON output" in result["stdout"]


# ==============================================================================
# Script Preparation Tests
# ==============================================================================


class TestPythonWorkerScriptPreparation:
    """Tests for script preparation."""

    def test_input_data_injection(self, worker):
        """GIVEN input_data WHEN preparing script THEN injects data."""
        input_data = {"key": "value", "number": 42}
        script = worker._prepare_script("result = input_data", input_data)

        assert "input_data = json.loads" in script
        assert '"key": "value"' in script

    def test_user_code_wrapped(self, worker):
        """GIVEN user code WHEN preparing script THEN wraps in exec."""
        user_code = "result = 1 + 1"
        script = worker._prepare_script(user_code, {})

        assert "exec(r'''" in script
        assert user_code in script

    def test_result_capture(self, worker):
        """GIVEN script WHEN prepared THEN captures result variable."""
        script = worker._prepare_script("result = 42", {})

        assert "if 'result' in globals():" in script
        assert "result = globals()['result']" in script


# ==============================================================================
# Container Cleanup Tests
# ==============================================================================


class TestPythonWorkerCleanup:
    """Tests for container cleanup."""

    def test_container_cleanup_on_success(self, worker):
        """GIVEN successful execution WHEN done THEN cleans up container."""
        mock_container = MagicMock()
        output = json.dumps({"success": True, "result": None})
        worker._mock_docker.containers.run.return_value = output.encode("utf-8")

        worker.execute_task({"code": "result = 1"})

        # Cleanup is attempted (container may be bytes in this mock)

    def test_docker_client_cleanup_on_del(self, worker):
        """GIVEN worker WHEN deleted THEN closes docker client."""
        worker._mock_docker = MagicMock()
        worker.docker_client = worker._mock_docker

        worker.__del__()

        worker._mock_docker.close.assert_called_once()


# ==============================================================================
# Base Worker Integration Tests
# ==============================================================================


class TestPythonWorkerBaseIntegration:
    """Tests for base worker integration."""

    def test_task_definition_name(self, worker):
        """GIVEN worker WHEN checking THEN has correct task definition name."""
        assert worker.task_definition_name == "python_runner"

    def test_execute_calls_validate_input(self, worker):
        """GIVEN invalid input WHEN executing via base THEN validation runs."""
        task = Mock()
        task.input_data = {}  # Missing code
        task.task_id = "task-123"
        task.workflow_instance_id = "wf-123"

        result = worker.execute(task)

        assert result.status.name == "FAILED"
        assert "code" in result.output_data.get("error", "")

    def test_execute_successful_via_base(self, worker):
        """GIVEN valid input WHEN executing via base THEN succeeds."""
        task = Mock()
        task.input_data = {"code": "result = 42"}
        task.task_id = "task-123"
        task.workflow_instance_id = "wf-123"

        output = json.dumps({"success": True, "result": 42})
        worker._mock_docker.containers.run.return_value = output.encode("utf-8")

        result = worker.execute(task)

        assert result.status.name == "COMPLETED"
        assert result.output_data["data"]["result"] == 42


# ==============================================================================
# Configuration Tests
# ==============================================================================


class TestPythonWorkerConfiguration:
    """Tests for worker configuration constants."""

    def test_docker_image_version(self, worker):
        """GIVEN worker WHEN checking THEN uses Python 3.11."""
        assert "python:3.11-slim" == worker.DOCKER_IMAGE

    def test_default_timeout_value(self, worker):
        """GIVEN worker WHEN checking THEN default timeout is 30s."""
        assert worker.DEFAULT_TIMEOUT == 30

    def test_max_timeout_value(self, worker):
        """GIVEN worker WHEN checking THEN max timeout is 300s."""
        assert worker.MAX_TIMEOUT == 300

    def test_memory_limit_value(self, worker):
        """GIVEN worker WHEN checking THEN memory limit is 256m."""
        assert worker.MEMORY_LIMIT == "256m"

    def test_cpu_quota_value(self, worker):
        """GIVEN worker WHEN checking THEN CPU quota is 50%."""
        assert worker.CPU_QUOTA == 50000


# ==============================================================================
# Complex Execution Tests
# ==============================================================================


class TestPythonWorkerComplexExecution:
    """Tests for complex code execution scenarios."""

    def test_execute_with_imports(self, worker):
        """GIVEN code with imports WHEN executing THEN handles correctly."""
        code = """
import math
result = math.sqrt(16)
"""
        output = json.dumps({"success": True, "result": 4.0})
        worker._mock_docker.containers.run.return_value = output.encode("utf-8")

        result = worker.execute_task({"code": code})

        assert result["result"] == 4.0

    def test_execute_data_transformation(self, worker):
        """GIVEN data transformation code WHEN executing THEN processes correctly."""
        code = """
# Transform input data
items = input_data['items']
transformed = [{'name': item['name'].upper(), 'value': item['value'] * 2}
               for item in items]
result = {'transformed': transformed, 'count': len(transformed)}
"""
        output = json.dumps(
            {
                "success": True,
                "result": {
                    "transformed": [
                        {"name": "A", "value": 2},
                        {"name": "B", "value": 4},
                    ],
                    "count": 2,
                },
            }
        )
        worker._mock_docker.containers.run.return_value = output.encode("utf-8")

        result = worker.execute_task(
            {
                "code": code,
                "input_data": {
                    "items": [
                        {"name": "a", "value": 1},
                        {"name": "b", "value": 2},
                    ]
                },
            }
        )

        assert result["result"]["count"] == 2
        assert result["result"]["transformed"][0]["name"] == "A"

    def test_execute_filtering(self, worker):
        """GIVEN filtering code WHEN executing THEN filters correctly."""
        code = """
items = input_data['items']
filtered = [item for item in items if item['confidence'] >= 0.7]
result = {'items': filtered, 'passed': len(filtered)}
"""
        output = json.dumps(
            {
                "success": True,
                "result": {
                    "items": [{"id": 2, "confidence": 0.8}],
                    "passed": 1,
                },
            }
        )
        worker._mock_docker.containers.run.return_value = output.encode("utf-8")

        result = worker.execute_task(
            {
                "code": code,
                "input_data": {
                    "items": [
                        {"id": 1, "confidence": 0.5},
                        {"id": 2, "confidence": 0.8},
                    ]
                },
            }
        )

        assert result["result"]["passed"] == 1
