"""
HTTP Request Worker

Executes HTTP requests with configurable method, headers, body, and authentication.
Includes retry logic and timeout handling.
"""

from typing import Any, Dict, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .base_worker import BaseWorker


class HttpRequestWorker(BaseWorker):
    """
    Worker that executes HTTP requests.

    Input Parameters:
    - url (str): Target URL
    - method (str): HTTP method (GET, POST, PUT, DELETE, PATCH)
    - headers (dict): Request headers (optional)
    - body (dict): Request body for POST/PUT/PATCH (optional)
    - timeout (int): Request timeout in seconds (default: 30)
    - retry_count (int): Number of retries on failure (default: 3)

    Output:
    - status_code: HTTP status code
    - headers: Response headers
    - body: Response body (parsed JSON if possible, otherwise text)
    """

    ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
    DEFAULT_TIMEOUT = 30
    DEFAULT_RETRY_COUNT = 3

    def __init__(self):
        super().__init__(task_definition_name="http_request")

        # Configure session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.DEFAULT_RETRY_COUNT,
            backoff_factor=1,  # Exponential backoff: 1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def validate_input(self, task_input: Dict[str, Any]) -> Optional[str]:
        """Validate HTTP request input."""
        if "url" not in task_input:
            return "Missing required parameter: 'url'"

        if not isinstance(task_input["url"], str):
            return "Parameter 'url' must be a string"

        if not task_input["url"].startswith(("http://", "https://")):
            return "URL must start with http:// or https://"

        method = task_input.get("method", "GET").upper()
        if method not in self.ALLOWED_METHODS:
            return f"Invalid method: {method}. Allowed: {', '.join(self.ALLOWED_METHODS)}"

        return None

    def execute_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute HTTP request.

        Args:
            task_input: Contains url, method, headers, body, timeout

        Returns:
            Dictionary with status_code, headers, body
        """
        url = task_input["url"]
        method = task_input.get("method", "GET").upper()
        headers = task_input.get("headers", {})
        body = task_input.get("body")
        timeout = task_input.get("timeout", self.DEFAULT_TIMEOUT)

        self.log_info(f"Executing {method} request to {url}")

        try:
            # Prepare request kwargs
            request_kwargs = {
                "timeout": timeout,
                "headers": headers,
            }

            # Add body for methods that support it
            if method in ["POST", "PUT", "PATCH"] and body is not None:
                if isinstance(body, dict):
                    request_kwargs["json"] = body
                else:
                    request_kwargs["data"] = body

            # Execute request
            response = self.session.request(method, url, **request_kwargs)

            # Parse response body
            response_body = self._parse_response_body(response)

            self.log_info(
                f"Request completed: {method} {url} -> {response.status_code}"
            )

            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_body,
                "success": 200 <= response.status_code < 300,
            }

        except requests.exceptions.Timeout:
            self.log_error(f"Request timeout after {timeout}s: {method} {url}")
            raise Exception(f"Request timeout after {timeout} seconds")

        except requests.exceptions.ConnectionError as e:
            self.log_error(f"Connection error: {method} {url}: {e}")
            raise Exception(f"Connection error: {str(e)}")

        except requests.exceptions.RequestException as e:
            self.log_error(f"Request failed: {method} {url}: {e}")
            raise Exception(f"HTTP request failed: {str(e)}")

    def _parse_response_body(self, response: requests.Response) -> Any:
        """
        Parse response body as JSON if possible, otherwise return text.

        Args:
            response: Requests response object

        Returns:
            Parsed JSON dict/list or text string
        """
        content_type = response.headers.get("Content-Type", "")

        # Try to parse as JSON
        if "application/json" in content_type:
            try:
                return response.json()
            except ValueError:
                self.log_warning("Failed to parse JSON response, returning text")
                return response.text

        # Return text for other content types
        return response.text

    def __del__(self):
        """Cleanup session on worker destruction."""
        if hasattr(self, 'session'):
            try:
                self.session.close()
            except Exception:
                pass
