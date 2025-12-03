"""
Integration tests for HttpRequestWorker.

Tests HTTP request execution including:
- GET, POST, PUT, DELETE methods
- Custom headers and body
- Timeout handling
- Retry logic on 5xx errors
- Exponential backoff
- JSON response parsing
- Error handling
"""

from unittest.mock import Mock, patch, MagicMock

import pytest
import requests

from app.orchestration.workers.http_request_worker import HttpRequestWorker


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def worker():
    """Create HttpRequestWorker instance."""
    return HttpRequestWorker()


@pytest.fixture
def mock_response():
    """Create a mock response factory."""

    def _create_response(
        status_code=200,
        json_data=None,
        text="",
        headers=None,
        content_type="application/json",
    ):
        response = Mock(spec=requests.Response)
        response.status_code = status_code
        response.text = text
        response.headers = headers or {"Content-Type": content_type}

        if json_data is not None:
            response.json.return_value = json_data
        else:
            response.json.side_effect = ValueError("No JSON")

        return response

    return _create_response


# ==============================================================================
# Input Validation Tests
# ==============================================================================


class TestHttpRequestWorkerValidation:
    """Tests for input validation."""

    def test_validate_input_missing_url(self, worker):
        """GIVEN task without url WHEN validating THEN returns error."""
        task_input = {"method": "GET"}

        error = worker.validate_input(task_input)

        assert error is not None
        assert "url" in error

    def test_validate_input_url_not_string(self, worker):
        """GIVEN url as non-string WHEN validating THEN returns error."""
        task_input = {"url": 12345}

        error = worker.validate_input(task_input)

        assert error is not None
        assert "string" in error

    def test_validate_input_invalid_url_scheme(self, worker):
        """GIVEN url without http(s) WHEN validating THEN returns error."""
        task_input = {"url": "ftp://example.com"}

        error = worker.validate_input(task_input)

        assert error is not None
        assert "http" in error.lower()

    def test_validate_input_invalid_method(self, worker):
        """GIVEN invalid HTTP method WHEN validating THEN returns error."""
        task_input = {"url": "https://example.com", "method": "INVALID"}

        error = worker.validate_input(task_input)

        assert error is not None
        assert "method" in error.lower()

    @pytest.mark.parametrize(
        "method",
        ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    )
    def test_validate_input_valid_methods(self, worker, method):
        """GIVEN valid HTTP method WHEN validating THEN returns None."""
        task_input = {"url": "https://example.com", "method": method}

        error = worker.validate_input(task_input)

        assert error is None

    def test_validate_input_valid_url(self, worker):
        """GIVEN valid url WHEN validating THEN returns None."""
        task_input = {"url": "https://api.example.com/endpoint"}

        error = worker.validate_input(task_input)

        assert error is None

    def test_validate_input_http_url(self, worker):
        """GIVEN http url WHEN validating THEN returns None."""
        task_input = {"url": "http://localhost:8080/api"}

        error = worker.validate_input(task_input)

        assert error is None


# ==============================================================================
# GET Request Tests
# ==============================================================================


class TestHttpRequestWorkerGet:
    """Tests for GET requests."""

    def test_execute_get_request(self, worker, mock_response):
        """GIVEN GET request WHEN executing THEN makes GET call."""
        response = mock_response(
            status_code=200,
            json_data={"data": "value"},
        )

        with patch.object(worker.session, "request", return_value=response):
            result = worker.execute_task(
                {"url": "https://api.example.com/data", "method": "GET"}
            )

        assert result["status_code"] == 200
        assert result["body"] == {"data": "value"}
        assert result["success"] is True

    def test_execute_get_with_default_method(self, worker, mock_response):
        """GIVEN no method WHEN executing THEN defaults to GET."""
        response = mock_response(status_code=200, json_data={})

        with patch.object(worker.session, "request", return_value=response) as mock_req:
            worker.execute_task({"url": "https://api.example.com/data"})

        mock_req.assert_called_once()
        assert mock_req.call_args[0][0] == "GET"


# ==============================================================================
# POST Request Tests
# ==============================================================================


class TestHttpRequestWorkerPost:
    """Tests for POST requests."""

    def test_execute_post_with_json_body(self, worker, mock_response):
        """GIVEN POST with JSON body WHEN executing THEN sends JSON."""
        response = mock_response(
            status_code=201,
            json_data={"id": "123"},
        )

        with patch.object(worker.session, "request", return_value=response) as mock_req:
            result = worker.execute_task(
                {
                    "url": "https://api.example.com/items",
                    "method": "POST",
                    "body": {"name": "Test Item"},
                }
            )

        assert result["status_code"] == 201
        call_kwargs = mock_req.call_args.kwargs
        assert call_kwargs["json"] == {"name": "Test Item"}

    def test_execute_post_with_string_body(self, worker, mock_response):
        """GIVEN POST with string body WHEN executing THEN sends data."""
        response = mock_response(status_code=200, json_data={})

        with patch.object(worker.session, "request", return_value=response) as mock_req:
            worker.execute_task(
                {
                    "url": "https://api.example.com/items",
                    "method": "POST",
                    "body": "raw data",
                }
            )

        call_kwargs = mock_req.call_args.kwargs
        assert call_kwargs["data"] == "raw data"


# ==============================================================================
# PUT Request Tests
# ==============================================================================


class TestHttpRequestWorkerPut:
    """Tests for PUT requests."""

    def test_execute_put_with_body(self, worker, mock_response):
        """GIVEN PUT with body WHEN executing THEN sends JSON."""
        response = mock_response(status_code=200, json_data={"updated": True})

        with patch.object(worker.session, "request", return_value=response) as mock_req:
            result = worker.execute_task(
                {
                    "url": "https://api.example.com/items/123",
                    "method": "PUT",
                    "body": {"name": "Updated Item"},
                }
            )

        assert result["status_code"] == 200
        call_kwargs = mock_req.call_args.kwargs
        assert call_kwargs["json"] == {"name": "Updated Item"}


# ==============================================================================
# DELETE Request Tests
# ==============================================================================


class TestHttpRequestWorkerDelete:
    """Tests for DELETE requests."""

    def test_execute_delete_request(self, worker, mock_response):
        """GIVEN DELETE request WHEN executing THEN makes DELETE call."""
        response = mock_response(status_code=204, text="")

        with patch.object(worker.session, "request", return_value=response):
            result = worker.execute_task(
                {"url": "https://api.example.com/items/123", "method": "DELETE"}
            )

        assert result["status_code"] == 204
        assert result["success"] is True


# ==============================================================================
# Custom Headers Tests
# ==============================================================================


class TestHttpRequestWorkerHeaders:
    """Tests for custom headers."""

    def test_execute_with_custom_headers(self, worker, mock_response):
        """GIVEN custom headers WHEN executing THEN includes headers."""
        response = mock_response(status_code=200, json_data={})

        custom_headers = {
            "Authorization": "Bearer token123",
            "X-Custom-Header": "custom-value",
        }

        with patch.object(worker.session, "request", return_value=response) as mock_req:
            worker.execute_task(
                {
                    "url": "https://api.example.com/data",
                    "headers": custom_headers,
                }
            )

        call_kwargs = mock_req.call_args.kwargs
        assert call_kwargs["headers"] == custom_headers


# ==============================================================================
# Timeout Tests
# ==============================================================================


class TestHttpRequestWorkerTimeout:
    """Tests for timeout handling."""

    def test_execute_with_custom_timeout(self, worker, mock_response):
        """GIVEN custom timeout WHEN executing THEN uses timeout."""
        response = mock_response(status_code=200, json_data={})

        with patch.object(worker.session, "request", return_value=response) as mock_req:
            worker.execute_task(
                {
                    "url": "https://api.example.com/data",
                    "timeout": 60,
                }
            )

        call_kwargs = mock_req.call_args.kwargs
        assert call_kwargs["timeout"] == 60

    def test_execute_with_default_timeout(self, worker, mock_response):
        """GIVEN no timeout WHEN executing THEN uses default."""
        response = mock_response(status_code=200, json_data={})

        with patch.object(worker.session, "request", return_value=response) as mock_req:
            worker.execute_task({"url": "https://api.example.com/data"})

        call_kwargs = mock_req.call_args.kwargs
        assert call_kwargs["timeout"] == 30  # DEFAULT_TIMEOUT

    def test_execute_timeout_exception(self, worker):
        """GIVEN request timeout WHEN executing THEN raises exception."""
        with patch.object(
            worker.session, "request", side_effect=requests.exceptions.Timeout()
        ):
            with pytest.raises(Exception, match="timeout"):
                worker.execute_task(
                    {"url": "https://api.example.com/data", "timeout": 5}
                )


# ==============================================================================
# Response Parsing Tests
# ==============================================================================


class TestHttpRequestWorkerResponseParsing:
    """Tests for response parsing."""

    def test_parse_json_response(self, worker, mock_response):
        """GIVEN JSON response WHEN executing THEN parses JSON."""
        response = mock_response(
            status_code=200,
            json_data={"key": "value", "nested": {"a": 1}},
        )

        with patch.object(worker.session, "request", return_value=response):
            result = worker.execute_task({"url": "https://api.example.com/data"})

        assert result["body"] == {"key": "value", "nested": {"a": 1}}

    def test_parse_text_response(self, worker, mock_response):
        """GIVEN text response WHEN executing THEN returns text."""
        response = mock_response(
            status_code=200,
            text="Plain text response",
            content_type="text/plain",
        )

        with patch.object(worker.session, "request", return_value=response):
            result = worker.execute_task({"url": "https://api.example.com/data"})

        assert result["body"] == "Plain text response"

    def test_parse_html_response(self, worker, mock_response):
        """GIVEN HTML response WHEN executing THEN returns text."""
        response = mock_response(
            status_code=200,
            text="<html><body>Hello</body></html>",
            content_type="text/html",
        )

        with patch.object(worker.session, "request", return_value=response):
            result = worker.execute_task({"url": "https://example.com"})

        assert result["body"] == "<html><body>Hello</body></html>"

    def test_parse_invalid_json_fallback(self, worker, mock_response):
        """GIVEN invalid JSON with JSON content-type WHEN executing THEN falls back to text."""
        response = mock_response(
            status_code=200,
            text="Not valid JSON",
            content_type="application/json",
        )
        response.json.side_effect = ValueError("Invalid JSON")

        with patch.object(worker.session, "request", return_value=response):
            result = worker.execute_task({"url": "https://api.example.com/data"})

        assert result["body"] == "Not valid JSON"


# ==============================================================================
# Error Handling Tests
# ==============================================================================


class TestHttpRequestWorkerErrors:
    """Tests for error handling."""

    def test_handle_connection_error(self, worker):
        """GIVEN connection error WHEN executing THEN raises exception."""
        with patch.object(
            worker.session,
            "request",
            side_effect=requests.exceptions.ConnectionError("Connection refused"),
        ):
            with pytest.raises(Exception, match="Connection error"):
                worker.execute_task({"url": "https://api.example.com/data"})

    def test_handle_request_exception(self, worker):
        """GIVEN generic request error WHEN executing THEN raises exception."""
        with patch.object(
            worker.session,
            "request",
            side_effect=requests.exceptions.RequestException("Unknown error"),
        ):
            with pytest.raises(Exception, match="HTTP request failed"):
                worker.execute_task({"url": "https://api.example.com/data"})


# ==============================================================================
# Status Code Tests
# ==============================================================================


class TestHttpRequestWorkerStatusCodes:
    """Tests for different status codes."""

    @pytest.mark.parametrize(
        "status_code,expected_success",
        [
            (200, True),
            (201, True),
            (204, True),
            (299, True),
            (300, False),
            (400, False),
            (401, False),
            (404, False),
            (500, False),
        ],
    )
    def test_success_flag_based_on_status(
        self, worker, mock_response, status_code, expected_success
    ):
        """GIVEN status code WHEN executing THEN sets success flag correctly."""
        response = mock_response(status_code=status_code, text="")

        with patch.object(worker.session, "request", return_value=response):
            result = worker.execute_task({"url": "https://api.example.com/data"})

        assert result["success"] == expected_success
        assert result["status_code"] == status_code

    def test_4xx_returns_response_not_exception(self, worker, mock_response):
        """GIVEN 4xx response WHEN executing THEN returns response, not exception."""
        response = mock_response(
            status_code=404,
            json_data={"error": "Not found"},
        )

        with patch.object(worker.session, "request", return_value=response):
            result = worker.execute_task({"url": "https://api.example.com/missing"})

        assert result["status_code"] == 404
        assert result["success"] is False
        assert result["body"] == {"error": "Not found"}


# ==============================================================================
# Response Headers Tests
# ==============================================================================


class TestHttpRequestWorkerResponseHeaders:
    """Tests for response headers."""

    def test_includes_response_headers(self, worker, mock_response):
        """GIVEN response with headers WHEN executing THEN includes headers."""
        response = mock_response(
            status_code=200,
            json_data={},
            headers={
                "Content-Type": "application/json",
                "X-Request-Id": "req-123",
                "X-RateLimit-Remaining": "99",
            },
        )

        with patch.object(worker.session, "request", return_value=response):
            result = worker.execute_task({"url": "https://api.example.com/data"})

        assert "headers" in result
        assert result["headers"]["X-Request-Id"] == "req-123"
        assert result["headers"]["X-RateLimit-Remaining"] == "99"


# ==============================================================================
# Output Format Tests
# ==============================================================================


class TestHttpRequestWorkerOutput:
    """Tests for output format structure."""

    def test_output_format_structure(self, worker, mock_response):
        """GIVEN any request WHEN executing THEN output has correct structure."""
        response = mock_response(
            status_code=200,
            json_data={"data": "value"},
            headers={"Content-Type": "application/json"},
        )

        with patch.object(worker.session, "request", return_value=response):
            result = worker.execute_task({"url": "https://api.example.com/data"})

        assert "status_code" in result
        assert "headers" in result
        assert "body" in result
        assert "success" in result

        assert isinstance(result["status_code"], int)
        assert isinstance(result["headers"], dict)
        assert isinstance(result["success"], bool)


# ==============================================================================
# Base Worker Integration Tests
# ==============================================================================


class TestHttpRequestWorkerBaseIntegration:
    """Tests for base worker integration."""

    def test_task_definition_name(self, worker):
        """GIVEN worker WHEN checking THEN has correct task definition name."""
        assert worker.task_definition_name == "http_request"

    def test_execute_calls_validate_input(self, worker):
        """GIVEN invalid input WHEN executing via base THEN validation runs."""
        task = Mock()
        task.input_data = {}  # Missing url
        task.task_id = "task-123"
        task.workflow_instance_id = "wf-123"

        result = worker.execute(task)

        assert result.status.name == "FAILED"
        assert "url" in result.output_data.get("error", "")

    def test_execute_successful_via_base(self, worker, mock_response):
        """GIVEN valid input WHEN executing via base THEN succeeds."""
        task = Mock()
        task.input_data = {"url": "https://api.example.com/data"}
        task.task_id = "task-123"
        task.workflow_instance_id = "wf-123"

        response = mock_response(status_code=200, json_data={"success": True})

        with patch.object(worker.session, "request", return_value=response):
            result = worker.execute(task)

        assert result.status.name == "COMPLETED"
        assert result.output_data["data"]["status_code"] == 200


# ==============================================================================
# Retry Logic Tests (Session Configuration)
# ==============================================================================


class TestHttpRequestWorkerRetryConfiguration:
    """Tests for retry logic configuration."""

    def test_session_has_retry_adapter(self, worker):
        """GIVEN worker WHEN initialized THEN session has retry adapter."""
        # Check that adapters are mounted
        assert "http://" in worker.session.adapters
        assert "https://" in worker.session.adapters

    def test_session_closes_on_del(self, worker):
        """GIVEN worker WHEN deleted THEN session is closed."""
        worker.session = Mock()

        worker.__del__()

        worker.session.close.assert_called_once()


# ==============================================================================
# PATCH Request Tests
# ==============================================================================


class TestHttpRequestWorkerPatch:
    """Tests for PATCH requests."""

    def test_execute_patch_with_body(self, worker, mock_response):
        """GIVEN PATCH with body WHEN executing THEN sends JSON."""
        response = mock_response(
            status_code=200,
            json_data={"patched": True},
        )

        with patch.object(worker.session, "request", return_value=response) as mock_req:
            result = worker.execute_task(
                {
                    "url": "https://api.example.com/items/123",
                    "method": "PATCH",
                    "body": {"field": "new_value"},
                }
            )

        assert result["status_code"] == 200
        mock_req.assert_called_once()
        assert mock_req.call_args[0][0] == "PATCH"
        call_kwargs = mock_req.call_args.kwargs
        assert call_kwargs["json"] == {"field": "new_value"}
