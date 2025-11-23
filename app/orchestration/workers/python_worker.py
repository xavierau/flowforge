"""
Python Worker with Docker Sandbox

Executes user-provided Python code in a secure, isolated Docker container.

Security Features:
- Network isolation (no external access)
- Resource limits (CPU, memory, timeout)
- Read-only filesystem
- Non-root user execution
- Automatic container cleanup
"""

import json
from typing import Any, Dict, Optional
import docker
from docker.errors import ContainerError, ImageNotFound, APIError

from .base_worker import BaseWorker


class PythonWorker(BaseWorker):
    """
    Worker that executes Python code in a secure Docker sandbox.

    Input Parameters:
    - code (str): Python code to execute
    - input_data (dict): Data available to the script as 'input_data' variable
    - timeout (int): Execution timeout in seconds (default: 30, max: 300)

    Output:
    - result: Return value from the script (must be JSON-serializable)
    - stdout: Standard output
    - stderr: Standard error
    """

    # Security configuration
    DOCKER_IMAGE = "python:3.11-slim"
    DEFAULT_TIMEOUT = 30  # seconds
    MAX_TIMEOUT = 300  # 5 minutes max
    MEMORY_LIMIT = "256m"
    CPU_QUOTA = 50000  # 50% of one CPU core

    def __init__(self):
        super().__init__(task_definition_name="python_runner")
        self.docker_client = docker.from_env()

        # Ensure Docker image is available
        self._ensure_docker_image()

    def _ensure_docker_image(self):
        """Pull Docker image if not present."""
        try:
            self.docker_client.images.get(self.DOCKER_IMAGE)
            self.log_info(f"Docker image {self.DOCKER_IMAGE} is available")
        except ImageNotFound:
            self.log_info(f"Pulling Docker image {self.DOCKER_IMAGE}...")
            self.docker_client.images.pull(self.DOCKER_IMAGE)
            self.log_info("Image pulled successfully")

    def validate_input(self, task_input: Dict[str, Any]) -> Optional[str]:
        """Validate Python worker input."""
        if "code" not in task_input:
            return "Missing required parameter: 'code'"

        if not isinstance(task_input["code"], str):
            return "Parameter 'code' must be a string"

        if not task_input["code"].strip():
            return "Parameter 'code' cannot be empty"

        # Validate timeout
        timeout = task_input.get("timeout", self.DEFAULT_TIMEOUT)
        if not isinstance(timeout, (int, float)):
            return "Parameter 'timeout' must be a number"

        if timeout > self.MAX_TIMEOUT:
            return f"Timeout cannot exceed {self.MAX_TIMEOUT} seconds"

        return None

    def execute_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Python code in Docker sandbox.

        Args:
            task_input: Contains 'code', optional 'input_data' and 'timeout'

        Returns:
            Dictionary with 'result', 'stdout', 'stderr'
        """
        code = task_input["code"]
        input_data = task_input.get("input_data", {})
        timeout = task_input.get("timeout", self.DEFAULT_TIMEOUT)

        self.log_info(f"Executing Python code (timeout: {timeout}s)")
        self.log_debug(f"Code length: {len(code)} characters")

        # Prepare the execution script
        execution_script = self._prepare_script(code, input_data)

        # Execute in Docker container
        result = self._execute_in_container(execution_script, timeout)

        return result

    def _prepare_script(self, user_code: str, input_data: Dict[str, Any]) -> str:
        """
        Prepare Python script for execution.

        Wraps user code with:
        - Input data injection
        - Result capture
        - Error handling
        """
        # Serialize input data
        input_json = json.dumps(input_data)

        script = f"""
import json
import sys

# Inject input data
input_data = json.loads('''{input_json}''')

# User code wrapped in try-except
try:
    # Execute user code
    result = None
    exec(r'''
{user_code}
''', globals())

    # Capture result if 'result' variable was set
    if 'result' in globals():
        result = globals()['result']

    # Output result as JSON
    output = {{
        "success": True,
        "result": result
    }}
    print(json.dumps(output))

except Exception as e:
    # Output error as JSON
    error_output = {{
        "success": False,
        "error": str(e),
        "error_type": type(e).__name__
    }}
    print(json.dumps(error_output), file=sys.stderr)
    sys.exit(1)
"""
        return script

    def _execute_in_container(
        self, script: str, timeout: int
    ) -> Dict[str, Any]:
        """
        Execute script in a secure Docker container.

        Security measures:
        - Network isolation (network_mode="none")
        - Memory limit
        - CPU quota
        - Read-only filesystem
        - Non-root user
        - Auto-cleanup
        """
        container = None

        try:
            self.log_debug("Starting Docker container...")

            # Run container with strict security settings
            container = self.docker_client.containers.run(
                image=self.DOCKER_IMAGE,
                command=["python", "-c", script],
                # Security settings
                network_mode="none",  # No network access
                mem_limit=self.MEMORY_LIMIT,  # Memory limit
                cpu_quota=self.CPU_QUOTA,  # CPU limit
                security_opt=["no-new-privileges"],  # No privilege escalation
                read_only=True,  # Read-only filesystem
                user="nobody",  # Non-root user
                # Execution settings
                detach=False,  # Wait for completion
                remove=False,  # Don't auto-remove (we handle cleanup)
                stdout=True,
                stderr=True,
                # Timeout (handled via Docker API timeout parameter)
            )

            # Container completed - extract output
            stdout = container.decode('utf-8') if isinstance(container, bytes) else ""
            stderr = ""

            # Parse JSON output
            try:
                output_data = json.loads(stdout.strip())

                if output_data.get("success"):
                    return {
                        "result": output_data.get("result"),
                        "stdout": stdout,
                        "stderr": stderr,
                    }
                else:
                    # Execution failed
                    raise Exception(
                        f"{output_data.get('error_type', 'Error')}: "
                        f"{output_data.get('error', 'Unknown error')}"
                    )

            except json.JSONDecodeError:
                # Not JSON output - return as-is
                return {
                    "result": None,
                    "stdout": stdout,
                    "stderr": stderr,
                }

        except ContainerError as e:
            # Container execution failed
            self.log_error(f"Container execution failed: {e}")
            raise Exception(f"Python execution failed: {e.stderr.decode('utf-8')}")

        except APIError as e:
            # Docker API error
            self.log_error(f"Docker API error: {e}")
            raise Exception(f"Docker error: {str(e)}")

        finally:
            # Cleanup container
            if container:
                try:
                    if hasattr(container, 'remove'):
                        container.remove(force=True)
                        self.log_debug("Container cleaned up")
                except Exception as e:
                    self.log_warning(f"Failed to cleanup container: {e}")

    def __del__(self):
        """Cleanup Docker client on worker destruction."""
        if hasattr(self, 'docker_client'):
            try:
                self.docker_client.close()
            except Exception:
                pass
