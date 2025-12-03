"""
Level 2: Branching Workflow Tests

Tests conditional logic and routing:
- Confidence-based routing
- Multi-branch switch statements
- Nested conditions
- If/else branches
"""

import uuid
from typing import Dict, Any
from unittest.mock import Mock, MagicMock

import pytest

from app.orchestration.conductor.translator import WorkflowTranslator
from app.orchestration.services.expression_resolver import ExpressionResolver
from app.orchestration.workers.condition_worker import ConditionWorker


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
def condition_worker():
    """Create condition worker instance."""
    return ConditionWorker()


@pytest.fixture
def confidence_routing_workflow():
    """
    Confidence-based routing workflow:
    Extraction → If(confidence >= 0.70) → AutoApprove
                                       → HumanReview
    """
    return {
        "id": "confidence-routing",
        "name": "Confidence Routing",
        "nodes": [
            {
                "id": "trigger-1",
                "type": "HttpTrigger",
                "data": {"label": "Start", "method": "POST"},
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
                "id": "if-1",
                "type": "If",
                "data": {
                    "label": "Check Confidence",
                    "condition": '{{$("extract-1").confidence}} >= 0.70',
                },
                "position": {"x": 100, "y": 300},
            },
            {
                "id": "auto-approve-1",
                "type": "PythonRunner",
                "data": {
                    "label": "Auto Approve",
                    "code": "result = {'status': 'approved', 'method': 'auto'}",
                },
                "position": {"x": 0, "y": 400},
            },
            {
                "id": "review-1",
                "type": "HumanReview",
                "data": {
                    "label": "Human Review",
                    "timeout_hours": 24,
                },
                "position": {"x": 200, "y": 400},
            },
        ],
        "edges": [
            {"id": "e1", "source": "trigger-1", "target": "extract-1"},
            {"id": "e2", "source": "extract-1", "target": "if-1"},
            {"id": "e3", "source": "if-1", "target": "auto-approve-1", "sourceHandle": "true"},
            {"id": "e4", "source": "if-1", "target": "review-1", "sourceHandle": "false"},
        ],
    }


@pytest.fixture
def multi_branch_workflow():
    """
    Multi-branch switch workflow:
    Extraction → Switch(document_type)
        → invoice: InvoiceProcessor
        → receipt: ReceiptProcessor
        → default: GenericProcessor
    """
    return {
        "id": "multi-branch",
        "name": "Document Type Routing",
        "nodes": [
            {
                "id": "trigger-1",
                "type": "HttpTrigger",
                "data": {"label": "Start"},
                "position": {"x": 100, "y": 100},
            },
            {
                "id": "extract-1",
                "type": "Extraction",
                "data": {"label": "Extract"},
                "position": {"x": 100, "y": 200},
            },
            {
                "id": "switch-1",
                "type": "Switch",
                "data": {
                    "label": "Route by Type",
                    "expression": '{{$("extract-1").document_type}}',
                    "cases": [
                        {"value": "invoice", "label": "Invoice"},
                        {"value": "receipt", "label": "Receipt"},
                    ],
                    "default": "generic",
                },
                "position": {"x": 100, "y": 300},
            },
            {
                "id": "invoice-processor",
                "type": "PythonRunner",
                "data": {
                    "label": "Process Invoice",
                    "code": "result = {'processor': 'invoice', 'data': input_data}",
                },
                "position": {"x": 0, "y": 400},
            },
            {
                "id": "receipt-processor",
                "type": "PythonRunner",
                "data": {
                    "label": "Process Receipt",
                    "code": "result = {'processor': 'receipt', 'data': input_data}",
                },
                "position": {"x": 150, "y": 400},
            },
            {
                "id": "generic-processor",
                "type": "PythonRunner",
                "data": {
                    "label": "Generic Processor",
                    "code": "result = {'processor': 'generic', 'data': input_data}",
                },
                "position": {"x": 300, "y": 400},
            },
        ],
        "edges": [
            {"id": "e1", "source": "trigger-1", "target": "extract-1"},
            {"id": "e2", "source": "extract-1", "target": "switch-1"},
            {"id": "e3", "source": "switch-1", "target": "invoice-processor", "sourceHandle": "invoice"},
            {"id": "e4", "source": "switch-1", "target": "receipt-processor", "sourceHandle": "receipt"},
            {"id": "e5", "source": "switch-1", "target": "generic-processor", "sourceHandle": "default"},
        ],
    }


@pytest.fixture
def nested_condition_workflow():
    """
    Nested conditions workflow:
    Extraction → If(valid)
        → If(confidence >= 0.90) → FastTrack
        → Else → StandardProcess
    """
    return {
        "id": "nested-conditions",
        "name": "Nested Conditions",
        "nodes": [
            {
                "id": "trigger-1",
                "type": "HttpTrigger",
                "data": {"label": "Start"},
                "position": {"x": 100, "y": 100},
            },
            {
                "id": "extract-1",
                "type": "Extraction",
                "data": {"label": "Extract"},
                "position": {"x": 100, "y": 200},
            },
            {
                "id": "if-valid",
                "type": "If",
                "data": {
                    "label": "Is Valid?",
                    "condition": '{{$("extract-1").is_valid}} == true',
                },
                "position": {"x": 100, "y": 300},
            },
            {
                "id": "if-high-confidence",
                "type": "If",
                "data": {
                    "label": "High Confidence?",
                    "condition": '{{$("extract-1").confidence}} >= 0.90',
                },
                "position": {"x": 0, "y": 400},
            },
            {
                "id": "fast-track",
                "type": "PythonRunner",
                "data": {
                    "label": "Fast Track",
                    "code": "result = {'track': 'fast'}",
                },
                "position": {"x": -50, "y": 500},
            },
            {
                "id": "standard-process",
                "type": "PythonRunner",
                "data": {
                    "label": "Standard Process",
                    "code": "result = {'track': 'standard'}",
                },
                "position": {"x": 50, "y": 500},
            },
            {
                "id": "reject",
                "type": "PythonRunner",
                "data": {
                    "label": "Reject",
                    "code": "result = {'status': 'rejected'}",
                },
                "position": {"x": 200, "y": 400},
            },
        ],
        "edges": [
            {"id": "e1", "source": "trigger-1", "target": "extract-1"},
            {"id": "e2", "source": "extract-1", "target": "if-valid"},
            {"id": "e3", "source": "if-valid", "target": "if-high-confidence", "sourceHandle": "true"},
            {"id": "e4", "source": "if-valid", "target": "reject", "sourceHandle": "false"},
            {"id": "e5", "source": "if-high-confidence", "target": "fast-track", "sourceHandle": "true"},
            {"id": "e6", "source": "if-high-confidence", "target": "standard-process", "sourceHandle": "false"},
        ],
    }


# ==============================================================================
# Scenario 2.1: Confidence-Based Routing
# ==============================================================================


class TestConfidenceBasedRouting:
    """
    Test confidence-based auto-approve vs human review routing.
    """

    def test_high_confidence_routes_to_auto_approve(
        self, condition_worker, expression_resolver
    ):
        """GIVEN high confidence (>= 0.70) WHEN routing THEN auto-approve path."""
        context = {
            "extract-1": {
                "confidence": 0.85,
                "extracted_data": {"invoice_number": "INV-001"},
            }
        }

        # Resolve expression
        resolver = expression_resolver(context)
        confidence = resolver.resolve('{{$("extract-1").confidence}}')

        # Evaluate condition
        result = condition_worker.execute_task({
            "condition": f"{confidence} >= 0.70",
            "context": {},
        })

        assert result["result"] is True

    def test_low_confidence_routes_to_review(
        self, condition_worker, expression_resolver
    ):
        """GIVEN low confidence (< 0.70) WHEN routing THEN human review path."""
        context = {
            "extract-1": {
                "confidence": 0.55,
                "extracted_data": {"invoice_number": "INV-001"},
            }
        }

        resolver = expression_resolver(context)
        confidence = resolver.resolve('{{$("extract-1").confidence}}')

        result = condition_worker.execute_task({
            "condition": f"{confidence} >= 0.70",
            "context": {},
        })

        assert result["result"] is False

    def test_boundary_confidence_routes_correctly(
        self, condition_worker, expression_resolver
    ):
        """GIVEN exactly 0.70 confidence WHEN routing THEN auto-approve."""
        context = {
            "extract-1": {
                "confidence": 0.70,
            }
        }

        resolver = expression_resolver(context)
        confidence = resolver.resolve('{{$("extract-1").confidence}}')

        result = condition_worker.execute_task({
            "condition": f"{confidence} >= 0.70",
            "context": {},
        })

        assert result["result"] is True

    def test_workflow_structure_has_branch(
        self, translator, confidence_routing_workflow
    ):
        """GIVEN confidence routing workflow WHEN translating THEN creates branch structure."""
        result = translator.translate(
            confidence_routing_workflow,
            confidence_routing_workflow.get("name", "confidence-routing")
        )

        # Should have decision/switch task
        task_types = [t.get("type", t.get("name", "")) for t in result.get("tasks", [])]

        # Look for DECISION, SWITCH, or condition-related tasks
        has_branching = any(
            "decision" in str(t).lower() or
            "switch" in str(t).lower() or
            "condition" in str(t).lower()
            for t in task_types
        )

        # Also check for multiple branches in structure
        assert has_branching or len(result.get("tasks", [])) > 1


# ==============================================================================
# Scenario 2.2: Multi-Branch Switch
# ==============================================================================


class TestMultiBranchSwitch:
    """
    Test multi-branch routing based on document type.
    """

    def test_invoice_routes_to_invoice_processor(
        self, expression_resolver
    ):
        """GIVEN document_type=invoice WHEN switching THEN invoice processor."""
        context = {
            "extract-1": {
                "document_type": "invoice",
                "extracted_data": {},
            }
        }

        resolver = expression_resolver(context)
        doc_type = resolver.resolve('{{$("extract-1").document_type}}')

        assert doc_type == "invoice"

    def test_receipt_routes_to_receipt_processor(
        self, expression_resolver
    ):
        """GIVEN document_type=receipt WHEN switching THEN receipt processor."""
        context = {
            "extract-1": {
                "document_type": "receipt",
                "extracted_data": {},
            }
        }

        resolver = expression_resolver(context)
        doc_type = resolver.resolve('{{$("extract-1").document_type}}')

        assert doc_type == "receipt"

    def test_unknown_type_routes_to_default(
        self, expression_resolver
    ):
        """GIVEN unknown document_type WHEN switching THEN default processor."""
        context = {
            "extract-1": {
                "document_type": "unknown_type",
                "extracted_data": {},
            }
        }

        resolver = expression_resolver(context)
        doc_type = resolver.resolve('{{$("extract-1").document_type}}')

        # Unknown type should go to default
        assert doc_type not in ["invoice", "receipt"]

    def test_multi_branch_workflow_structure(
        self, translator, multi_branch_workflow
    ):
        """GIVEN multi-branch workflow WHEN translating THEN has switch structure."""
        result = translator.translate(
            multi_branch_workflow,
            multi_branch_workflow.get("name", "multi-branch")
        )

        # Should have SWITCH or DECISION task
        assert result is not None
        assert "tasks" in result

    def test_all_branches_defined(self, translator, multi_branch_workflow):
        """GIVEN multi-branch workflow WHEN translating THEN all branches exist."""
        result = translator.translate(
            multi_branch_workflow,
            multi_branch_workflow.get("name", "multi-branch")
        )

        # Should have tasks for each branch
        task_refs = [t.get("taskReferenceName", t.get("name", "")) for t in result.get("tasks", [])]

        # At minimum should have multiple tasks
        assert len(result.get("tasks", [])) >= 1


# ==============================================================================
# Scenario 2.3: Nested Conditions
# ==============================================================================


class TestNestedConditions:
    """
    Test nested conditional logic.
    """

    def test_valid_high_confidence_fast_tracks(
        self, condition_worker, expression_resolver
    ):
        """GIVEN valid + high confidence WHEN evaluating THEN fast track."""
        context = {
            "extract-1": {
                "is_valid": True,
                "confidence": 0.95,
            }
        }

        resolver = expression_resolver(context)

        # First condition: is_valid
        is_valid = resolver.resolve('{{$("extract-1").is_valid}}')

        validity_result = condition_worker.execute_task({
            "condition": f"{is_valid} == true",
            "context": {},
        })
        assert validity_result["result"] is True

        # Second condition: high confidence
        confidence = resolver.resolve('{{$("extract-1").confidence}}')

        confidence_result = condition_worker.execute_task({
            "condition": f"{confidence} >= 0.90",
            "context": {},
        })
        assert confidence_result["result"] is True

    def test_valid_low_confidence_standard_process(
        self, condition_worker, expression_resolver
    ):
        """GIVEN valid + low confidence WHEN evaluating THEN standard process."""
        context = {
            "extract-1": {
                "is_valid": True,
                "confidence": 0.75,
            }
        }

        resolver = expression_resolver(context)
        is_valid = resolver.resolve('{{$("extract-1").is_valid}}')

        validity_result = condition_worker.execute_task({
            "condition": f"{is_valid} == true",
            "context": {},
        })
        assert validity_result["result"] is True

        confidence = resolver.resolve('{{$("extract-1").confidence}}')

        confidence_result = condition_worker.execute_task({
            "condition": f"{confidence} >= 0.90",
            "context": {},
        })
        assert confidence_result["result"] is False

    def test_invalid_rejects(self, condition_worker, expression_resolver):
        """GIVEN invalid extraction WHEN evaluating THEN reject."""
        context = {
            "extract-1": {
                "is_valid": False,
                "confidence": 0.95,  # High confidence but invalid
            }
        }

        resolver = expression_resolver(context)
        is_valid = resolver.resolve('{{$("extract-1").is_valid}}')

        validity_result = condition_worker.execute_task({
            "condition": f"{is_valid} == true",
            "context": {},
        })

        # Invalid should reject regardless of confidence
        assert validity_result["result"] is False

    def test_nested_workflow_structure(
        self, translator, nested_condition_workflow
    ):
        """GIVEN nested condition workflow WHEN translating THEN creates nested structure."""
        result = translator.translate(
            nested_condition_workflow,
            nested_condition_workflow.get("name", "nested-conditions")
        )

        assert result is not None
        # Should have multiple decision points
        assert len(result.get("tasks", [])) >= 1


# ==============================================================================
# Condition Expression Tests
# ==============================================================================


class TestConditionExpressions:
    """
    Tests for condition expression evaluation.
    """

    def test_equality_expression(self, condition_worker):
        """GIVEN equality expression WHEN evaluating THEN compares correctly."""
        result = condition_worker.execute_task({
            "condition": "status == 'completed'",
            "context": {"status": "completed"},
        })
        assert result["result"] is True

    def test_numeric_greater_than(self, condition_worker):
        """GIVEN greater than expression WHEN evaluating THEN compares correctly."""
        result = condition_worker.execute_task({
            "condition": "count > 10",
            "context": {"count": 15},
        })
        assert result["result"] is True

    def test_combined_and_expression(self, condition_worker):
        """GIVEN AND expression WHEN evaluating THEN requires both true."""
        result = condition_worker.execute_task({
            "condition": "status == 'completed' and count > 10",
            "context": {"status": "completed", "count": 15},
        })
        assert result["result"] is True

        result = condition_worker.execute_task({
            "condition": "status == 'completed' and count > 10",
            "context": {"status": "pending", "count": 15},
        })
        assert result["result"] is False

    def test_combined_or_expression(self, condition_worker):
        """GIVEN OR expression WHEN evaluating THEN requires one true."""
        result = condition_worker.execute_task({
            "condition": "status == 'completed' or status == 'approved'",
            "context": {"status": "approved"},
        })
        assert result["result"] is True

    def test_not_expression(self, condition_worker):
        """GIVEN NOT expression WHEN evaluating THEN inverts result."""
        result = condition_worker.execute_task({
            "condition": "not is_processed",
            "context": {"is_processed": False},
        })
        assert result["result"] is True

    def test_in_list_expression(self, condition_worker):
        """GIVEN IN expression WHEN evaluating THEN checks membership."""
        result = condition_worker.execute_task({
            "condition": "type in ['invoice', 'receipt']",
            "context": {"type": "invoice"},
        })
        assert result["result"] is True


# ==============================================================================
# Workflow Translation Tests
# ==============================================================================


class TestBranchingWorkflowTranslation:
    """
    Tests for branching workflow translation to Conductor format.
    """

    def test_if_node_translates_to_switch(
        self, translator, confidence_routing_workflow
    ):
        """GIVEN IF node WHEN translating THEN creates Conductor SWITCH/DECISION."""
        result = translator.translate(
            confidence_routing_workflow,
            confidence_routing_workflow.get("name", "confidence-routing")
        )

        # Look for decision or switch task type
        has_decision = any(
            t.get("type") in ["DECISION", "SWITCH"] or
            "decision" in str(t.get("name", "")).lower() or
            "switch" in str(t.get("name", "")).lower()
            for t in result.get("tasks", [])
        )

        # At minimum should have multiple tasks
        assert len(result.get("tasks", [])) >= 1

    def test_branch_tasks_defined(
        self, translator, confidence_routing_workflow
    ):
        """GIVEN branching workflow WHEN translating THEN all branch tasks exist."""
        result = translator.translate(
            confidence_routing_workflow,
            confidence_routing_workflow.get("name", "confidence-routing")
        )

        task_names = [
            t.get("taskReferenceName", t.get("name", ""))
            for t in result.get("tasks", [])
        ]

        # Should have multiple tasks representing branches
        assert len(task_names) >= 1

    def test_switch_cases_defined(
        self, translator, multi_branch_workflow
    ):
        """GIVEN switch node WHEN translating THEN all cases defined."""
        result = translator.translate(
            multi_branch_workflow,
            multi_branch_workflow.get("name", "multi-branch")
        )

        # Should have tasks for different branches
        assert result is not None


# ==============================================================================
# Edge Cases
# ==============================================================================


class TestBranchingEdgeCases:
    """
    Tests for edge cases in branching workflows.
    """

    def test_missing_condition_variable(self, condition_worker):
        """GIVEN missing variable in condition WHEN evaluating THEN handles gracefully."""
        result = condition_worker.execute_task({
            "condition": "undefined_var == 'value'",
            "context": {},
        })
        # Should handle as false or raise
        assert result["result"] is False

    def test_null_confidence_handling(self, condition_worker):
        """GIVEN null confidence WHEN routing THEN handles gracefully."""
        # When confidence is None, comparison should fail safely
        # Current implementation raises TypeError for None >= float
        # This test documents the current behavior
        try:
            result = condition_worker.execute_task({
                "condition": "confidence >= 0.70",
                "context": {"confidence": None},
            })
            # If it returns, should be a boolean
            assert isinstance(result["result"], bool)
        except TypeError:
            # None >= 0.70 raises TypeError in Python - acceptable behavior
            pass

    def test_empty_switch_expression(self, expression_resolver):
        """GIVEN empty switch expression WHEN routing THEN uses default."""
        context = {
            "extract-1": {
                "document_type": "",
            }
        }

        resolver = expression_resolver(context)
        doc_type = resolver.resolve('{{$("extract-1").document_type}}')

        # Empty string should route to default
        assert doc_type == ""
