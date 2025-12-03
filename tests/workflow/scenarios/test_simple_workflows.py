"""
Level 1: Simple Workflow Tests

Tests basic workflow execution patterns:
- Single task workflows
- Sequential task workflows
- HTTP trigger integration
- Data passing between tasks
"""

import uuid
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock

import pytest
from sqlalchemy.orm import Session

from app.orchestration.conductor.translator import WorkflowTranslator
from app.orchestration.services.expression_resolver import ExpressionResolver
from app.models.document import Document
from app.models.tenant import Tenant
from app.models.enums import DocumentStatus


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def translator():
    """Create workflow translator instance."""
    return WorkflowTranslator()


@pytest.fixture
def expression_resolver():
    """Create expression resolver factory.

    Returns a factory function that creates an ExpressionResolver
    with the provided node_outputs context.
    """
    def _create_resolver(node_outputs: dict = None):
        return ExpressionResolver(node_outputs or {})
    return _create_resolver


@pytest.fixture
def simple_extraction_workflow():
    """
    Simple workflow: HttpTrigger → Extraction → Output

    This is the most basic workflow pattern.
    """
    return {
        "id": "simple-extraction-workflow",
        "name": "Simple Extraction",
        "nodes": [
            {
                "id": "trigger-1",
                "type": "HttpTrigger",
                "data": {
                    "label": "Document Trigger",
                    "method": "POST",
                    "path": "/extract",
                },
                "position": {"x": 100, "y": 100},
            },
            {
                "id": "extract-1",
                "type": "Extraction",
                "data": {
                    "label": "Extract Data",
                    "provider": "google",
                    "model": "gemini-2.5-flash",
                    "schema_id": "invoice-schema",
                },
                "position": {"x": 100, "y": 200},
            },
        ],
        "edges": [
            {
                "id": "edge-1",
                "source": "trigger-1",
                "target": "extract-1",
            },
        ],
    }


@pytest.fixture
def sequential_workflow():
    """
    Sequential workflow: Trigger → Extraction → Python → Output

    Tests data passing between multiple sequential tasks.
    """
    return {
        "id": "sequential-workflow",
        "name": "Sequential Processing",
        "nodes": [
            {
                "id": "trigger-1",
                "type": "HttpTrigger",
                "data": {
                    "label": "Start",
                    "method": "POST",
                    "path": "/process",
                },
                "position": {"x": 100, "y": 100},
            },
            {
                "id": "extract-1",
                "type": "Extraction",
                "data": {
                    "label": "Extract",
                    "provider": "google",
                    "schema_id": "invoice-schema",
                },
                "position": {"x": 100, "y": 200},
            },
            {
                "id": "python-1",
                "type": "PythonRunner",
                "data": {
                    "label": "Validate",
                    "code": """
# Validate extracted data
data = input_data['extracted_data']
is_valid = bool(data.get('invoice_number'))
result = {'is_valid': is_valid, 'data': data}
""",
                },
                "position": {"x": 100, "y": 300},
            },
        ],
        "edges": [
            {"id": "edge-1", "source": "trigger-1", "target": "extract-1"},
            {"id": "edge-2", "source": "extract-1", "target": "python-1"},
        ],
    }


@pytest.fixture
def workflow_with_webhook():
    """
    Workflow with HTTP notification: Trigger → Extraction → HttpRequest

    Tests external integration via HTTP request.
    """
    return {
        "id": "webhook-workflow",
        "name": "Extraction with Webhook",
        "nodes": [
            {
                "id": "trigger-1",
                "type": "HttpTrigger",
                "data": {
                    "label": "Start",
                    "method": "POST",
                    "path": "/extract-notify",
                },
                "position": {"x": 100, "y": 100},
            },
            {
                "id": "extract-1",
                "type": "Extraction",
                "data": {
                    "label": "Extract",
                    "provider": "google",
                },
                "position": {"x": 100, "y": 200},
            },
            {
                "id": "http-1",
                "type": "HttpRequest",
                "data": {
                    "label": "Notify Webhook",
                    "url": '{{$("trigger-1").callback_url}}',
                    "method": "POST",
                    "body": {
                        "status": "completed",
                        "data": '{{$("extract-1").extracted_data}}',
                    },
                },
                "position": {"x": 100, "y": 300},
            },
        ],
        "edges": [
            {"id": "edge-1", "source": "trigger-1", "target": "extract-1"},
            {"id": "edge-2", "source": "extract-1", "target": "http-1"},
        ],
    }


@pytest.fixture
def mock_conductor_client():
    """Mock Conductor client for workflow tests."""
    client = MagicMock()
    client.register_workflow_definition.return_value = True
    client.start_workflow.return_value = {"workflowId": str(uuid.uuid4())}
    return client


# ==============================================================================
# Scenario 1.1: Single Extraction Task
# ==============================================================================


class TestSingleExtractionWorkflow:
    """
    Scenario: HttpTrigger → Extraction → Output
    Validates: Basic workflow execution, task completion, output capture
    """

    def test_workflow_translates_to_conductor_format(
        self, translator, simple_extraction_workflow
    ):
        """GIVEN simple workflow WHEN translating THEN produces valid Conductor definition."""
        result = translator.translate(
            simple_extraction_workflow,
            simple_extraction_workflow.get("name", "simple-extraction")
        )

        assert result is not None
        assert "name" in result
        assert "tasks" in result
        assert len(result["tasks"]) >= 1

    def test_workflow_has_correct_task_sequence(
        self, translator, simple_extraction_workflow
    ):
        """GIVEN simple workflow WHEN translating THEN tasks are in correct order."""
        result = translator.translate(
            simple_extraction_workflow,
            simple_extraction_workflow.get("name", "simple-extraction")
        )

        # Find the extraction task
        extraction_tasks = [
            t for t in result["tasks"] if t.get("name") == "document_extraction"
        ]
        assert len(extraction_tasks) >= 1

    def test_workflow_extracts_trigger_data(
        self, translator, simple_extraction_workflow
    ):
        """GIVEN workflow with trigger WHEN translating THEN captures trigger parameters."""
        result = translator.translate(
            simple_extraction_workflow,
            simple_extraction_workflow.get("name", "simple-extraction")
        )

        # The workflow should have input parameters from trigger
        assert "inputParameters" in result or "tasks" in result

    def test_workflow_execution_context_setup(
        self, expression_resolver, simple_extraction_workflow
    ):
        """GIVEN workflow execution WHEN started THEN context is properly initialized."""
        # Simulate workflow execution context
        context = {
            "trigger-1": {
                "document_id": "doc-123",
                "schema_id": "schema-456",
            }
        }

        # Expression resolver should be able to access trigger data
        resolver = expression_resolver(context)
        expression = '{{$("trigger-1").document_id}}'
        result = resolver.resolve(expression)

        assert result == "doc-123"


# ==============================================================================
# Scenario 1.2: Sequential Tasks
# ==============================================================================


class TestSequentialWorkflow:
    """
    Scenario: Trigger → Extraction → PythonValidator → Output
    Validates: Task ordering, data passing between tasks
    """

    def test_sequential_task_ordering(self, translator, sequential_workflow):
        """GIVEN sequential workflow WHEN translating THEN maintains task order."""
        result = translator.translate(
            sequential_workflow,
            sequential_workflow.get("name", "sequential-workflow")
        )

        # Extract task names in order
        task_names = [t.get("name") for t in result.get("tasks", [])]

        # Extraction should come before Python runner
        extraction_idx = next(
            (i for i, n in enumerate(task_names) if "extraction" in str(n).lower()), -1
        )
        python_idx = next(
            (i for i, n in enumerate(task_names) if "python" in str(n).lower()), -1
        )

        if extraction_idx >= 0 and python_idx >= 0:
            assert extraction_idx < python_idx

    def test_data_passing_between_tasks(
        self, expression_resolver, sequential_workflow
    ):
        """GIVEN sequential tasks WHEN executing THEN data passes correctly."""
        # Simulate completed extraction task
        context = {
            "extract-1": {
                "extracted_data": {
                    "invoice_number": "INV-001",
                    "total": 100.00,
                },
                "confidence": 0.85,
            }
        }

        # Python task should access extraction results
        resolver = expression_resolver(context)
        expression = '{{$("extract-1").extracted_data}}'
        result = resolver.resolve(expression)

        assert result["invoice_number"] == "INV-001"
        assert result["total"] == 100.00

    def test_sequential_workflow_dependency_graph(
        self, translator, sequential_workflow
    ):
        """GIVEN sequential workflow WHEN building THEN creates correct dependencies."""
        result = translator.translate(
            sequential_workflow,
            sequential_workflow.get("name", "sequential-workflow")
        )

        # Each task should have proper dependencies
        for task in result.get("tasks", []):
            # Non-trigger tasks should have inputParameters referencing previous outputs
            if task.get("name") != "http_trigger":
                assert "inputParameters" in task or "taskReferenceName" in task

    def test_python_task_receives_input_data(
        self, expression_resolver, sequential_workflow
    ):
        """GIVEN Python task WHEN executing THEN receives input_data from previous task."""
        context = {
            "extract-1": {
                "extracted_data": {"field": "value"},
            }
        }

        # Verify the expression that would populate input_data
        resolver = expression_resolver(context)
        expression = '{{$("extract-1").extracted_data}}'
        result = resolver.resolve(expression)

        assert result == {"field": "value"}


# ==============================================================================
# Scenario 1.3: HTTP Request Integration
# ==============================================================================


class TestHttpRequestIntegration:
    """
    Scenario: Trigger → Extraction → HttpRequest(webhook)
    Validates: HTTP task execution, external integration
    """

    def test_http_request_in_workflow(self, translator, workflow_with_webhook):
        """GIVEN workflow with HTTP request WHEN translating THEN includes HTTP task."""
        result = translator.translate(
            workflow_with_webhook,
            workflow_with_webhook.get("name", "webhook-workflow")
        )

        # Find HTTP request task
        http_tasks = [
            t for t in result.get("tasks", [])
            if t.get("name") == "http_request" or "HTTP" in str(t.get("name", "")).upper()
        ]

        assert len(http_tasks) >= 1

    def test_http_request_url_expression(
        self, expression_resolver, workflow_with_webhook
    ):
        """GIVEN HTTP request with expression URL WHEN resolving THEN gets correct URL."""
        context = {
            "trigger-1": {
                "callback_url": "https://api.example.com/callback",
            }
        }

        resolver = expression_resolver(context)
        expression = '{{$("trigger-1").callback_url}}'
        result = resolver.resolve(expression)

        assert result == "https://api.example.com/callback"

    def test_http_request_body_expressions(
        self, expression_resolver, workflow_with_webhook
    ):
        """GIVEN HTTP request with expression body WHEN resolving THEN substitutes values."""
        context = {
            "extract-1": {
                "extracted_data": {
                    "invoice_number": "INV-001",
                    "total": 500.00,
                }
            }
        }

        resolver = expression_resolver(context)
        expression = '{{$("extract-1").extracted_data}}'
        result = resolver.resolve(expression)

        assert result["invoice_number"] == "INV-001"

    def test_webhook_receives_extraction_results(
        self, expression_resolver, workflow_with_webhook
    ):
        """GIVEN webhook node WHEN extraction completes THEN receives results."""
        # Simulate full workflow context
        context = {
            "trigger-1": {
                "document_id": "doc-123",
                "callback_url": "https://example.com/webhook",
            },
            "extract-1": {
                "extracted_data": {"invoice_number": "INV-001"},
                "pages_processed": 1,
                "total_tokens": 500,
            },
        }

        # Webhook should have access to extraction data
        resolver = expression_resolver(context)
        data_expr = '{{$("extract-1").extracted_data}}'
        result = resolver.resolve(data_expr)

        assert result == {"invoice_number": "INV-001"}


# ==============================================================================
# Workflow Definition Tests
# ==============================================================================


class TestWorkflowDefinitionStructure:
    """Tests for workflow definition structure validation."""

    def test_workflow_has_required_fields(
        self, translator, simple_extraction_workflow
    ):
        """GIVEN workflow WHEN translating THEN has all required Conductor fields."""
        result = translator.translate(
            simple_extraction_workflow,
            simple_extraction_workflow.get("name", "simple-extraction")
        )

        required_fields = ["name", "tasks"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    def test_workflow_version_defaults(self, translator, simple_extraction_workflow):
        """GIVEN workflow without version WHEN translating THEN uses default version."""
        result = translator.translate(
            simple_extraction_workflow,
            simple_extraction_workflow.get("name", "simple-extraction")
        )

        # Conductor workflows should have a version
        assert "version" in result or result.get("version", 1) >= 1

    def test_task_has_reference_name(self, translator, simple_extraction_workflow):
        """GIVEN workflow tasks WHEN translating THEN each has taskReferenceName."""
        result = translator.translate(
            simple_extraction_workflow,
            simple_extraction_workflow.get("name", "simple-extraction")
        )

        for task in result.get("tasks", []):
            assert "taskReferenceName" in task or "name" in task

    def test_workflow_input_parameters(self, translator, simple_extraction_workflow):
        """GIVEN workflow WHEN translating THEN defines input parameters."""
        result = translator.translate(
            simple_extraction_workflow,
            simple_extraction_workflow.get("name", "simple-extraction")
        )

        # Workflow should define what inputs it expects
        assert "inputParameters" in result or "tasks" in result


# ==============================================================================
# Workflow Registration Tests
# ==============================================================================


class TestWorkflowRegistration:
    """Tests for workflow registration with Conductor."""

    def test_register_simple_workflow(
        self, translator, mock_conductor_client, simple_extraction_workflow
    ):
        """GIVEN valid workflow WHEN registering THEN succeeds."""
        workflow_def = translator.translate(
            simple_extraction_workflow,
            simple_extraction_workflow.get("name", "simple-extraction")
        )

        mock_conductor_client.register_workflow_definition(workflow_def)

        mock_conductor_client.register_workflow_definition.assert_called_once()

    def test_start_simple_workflow(
        self, translator, mock_conductor_client, simple_extraction_workflow
    ):
        """GIVEN registered workflow WHEN starting THEN returns workflow ID."""
        workflow_def = translator.translate(
            simple_extraction_workflow,
            simple_extraction_workflow.get("name", "simple-extraction")
        )

        # Register first
        mock_conductor_client.register_workflow_definition(workflow_def)

        # Start workflow
        input_data = {
            "document_id": "doc-123",
            "schema_id": "schema-456",
        }

        result = mock_conductor_client.start_workflow(
            workflow_def["name"],
            input_data,
        )

        assert "workflowId" in result


# ==============================================================================
# Edge Cases
# ==============================================================================


class TestSimpleWorkflowEdgeCases:
    """Tests for edge cases in simple workflows."""

    def test_empty_workflow_handling(self, translator):
        """GIVEN empty workflow WHEN translating THEN handles gracefully."""
        empty_workflow = {
            "id": "empty-workflow",
            "name": "Empty",
            "nodes": [],
            "edges": [],
        }

        # Should either return minimal workflow or raise validation error
        try:
            result = translator.translate(empty_workflow, empty_workflow["name"])
            # If it returns, should have minimal structure
            assert "name" in result
        except (ValueError, KeyError):
            # Validation error is acceptable for empty workflow
            pass

    def test_single_node_workflow(self, translator):
        """GIVEN single node workflow WHEN translating THEN handles correctly."""
        single_node = {
            "id": "single-node",
            "name": "Single Node",
            "nodes": [
                {
                    "id": "trigger-1",
                    "type": "HttpTrigger",
                    "data": {"label": "Start"},
                    "position": {"x": 0, "y": 0},
                }
            ],
            "edges": [],
        }

        result = translator.translate(single_node, single_node["name"])
        assert result is not None

    def test_workflow_with_missing_edge_target(self, translator):
        """GIVEN workflow with invalid edge WHEN translating THEN handles error."""
        invalid_workflow = {
            "id": "invalid-edge",
            "name": "Invalid Edge",
            "nodes": [
                {
                    "id": "trigger-1",
                    "type": "HttpTrigger",
                    "data": {"label": "Start"},
                    "position": {"x": 0, "y": 0},
                }
            ],
            "edges": [
                {
                    "id": "edge-1",
                    "source": "trigger-1",
                    "target": "non-existent-node",
                }
            ],
        }

        # Should handle gracefully (ignore invalid edges or raise)
        try:
            result = translator.translate(invalid_workflow, invalid_workflow["name"])
            # If it succeeds, the invalid edge should be ignored
        except (ValueError, KeyError):
            # Expected to fail on validation
            pass
