"""
Integration tests for ConditionWorker.

Tests conditional expression evaluation including:
- True and false conditions
- Context data evaluation
- Numeric and string comparisons
- Invalid condition handling
- Missing context variables
- Output format
"""

from unittest.mock import Mock

import pytest

from app.orchestration.workers.condition_worker import ConditionWorker


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def worker():
    """Create ConditionWorker instance."""
    return ConditionWorker()


@pytest.fixture
def sample_context():
    """Sample context data for condition evaluation."""
    return {
        "status": "completed",
        "count": 42,
        "confidence": 0.85,
        "name": "test_document",
        "tags": ["invoice", "urgent"],
        "metadata": {
            "type": "invoice",
            "pages": 5,
        },
        "is_valid": True,
        "is_processed": False,
    }


# ==============================================================================
# Input Validation Tests
# ==============================================================================


class TestConditionWorkerValidation:
    """Tests for input validation."""

    def test_validate_input_missing_condition(self, worker):
        """GIVEN task without condition WHEN validating THEN returns error."""
        task_input = {"context": {"a": 1}}

        error = worker.validate_input(task_input)

        assert error is not None
        assert "condition" in error

    def test_validate_input_condition_not_string(self, worker):
        """GIVEN condition as non-string WHEN validating THEN returns error."""
        task_input = {"condition": 123}

        error = worker.validate_input(task_input)

        assert error is not None
        assert "string" in error

    def test_validate_input_empty_condition(self, worker):
        """GIVEN empty condition WHEN validating THEN returns error."""
        task_input = {"condition": "   "}

        error = worker.validate_input(task_input)

        assert error is not None
        assert "empty" in error

    def test_validate_input_valid_condition(self, worker):
        """GIVEN valid condition WHEN validating THEN returns None."""
        task_input = {"condition": "status == 'completed'"}

        error = worker.validate_input(task_input)

        assert error is None

    def test_validate_input_context_optional(self, worker):
        """GIVEN condition without context WHEN validating THEN returns None."""
        task_input = {"condition": "true"}

        error = worker.validate_input(task_input)

        assert error is None


# ==============================================================================
# True Condition Tests
# ==============================================================================


class TestConditionWorkerTrueConditions:
    """Tests for conditions that evaluate to true."""

    def test_evaluate_true_equality(self, worker, sample_context):
        """GIVEN equality condition WHEN matches THEN returns true."""
        task_input = {
            "condition": "status == 'completed'",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True
        assert result["condition"] == "status == 'completed'"

    def test_evaluate_true_numeric_comparison(self, worker, sample_context):
        """GIVEN numeric comparison WHEN matches THEN returns true."""
        task_input = {
            "condition": "count > 40",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True

    def test_evaluate_true_less_than_equal(self, worker, sample_context):
        """GIVEN <= comparison WHEN matches THEN returns true."""
        task_input = {
            "condition": "confidence <= 0.90",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True

    def test_evaluate_true_in_list(self, worker, sample_context):
        """GIVEN 'in' operator WHEN value in list THEN returns true."""
        task_input = {
            "condition": "'invoice' in tags",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True

    def test_evaluate_true_boolean_variable(self, worker, sample_context):
        """GIVEN boolean variable WHEN true THEN returns true."""
        task_input = {
            "condition": "is_valid",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True

    def test_evaluate_true_literal(self, worker):
        """GIVEN 'true' literal WHEN evaluating THEN returns true."""
        task_input = {
            "condition": "true",
            "context": {},
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True


# ==============================================================================
# False Condition Tests
# ==============================================================================


class TestConditionWorkerFalseConditions:
    """Tests for conditions that evaluate to false."""

    def test_evaluate_false_equality(self, worker, sample_context):
        """GIVEN equality condition WHEN not matches THEN returns false."""
        task_input = {
            "condition": "status == 'pending'",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is False

    def test_evaluate_false_numeric_comparison(self, worker, sample_context):
        """GIVEN numeric comparison WHEN not matches THEN returns false."""
        task_input = {
            "condition": "count < 40",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is False

    def test_evaluate_false_not_in_list(self, worker, sample_context):
        """GIVEN 'in' operator WHEN value not in list THEN returns false."""
        task_input = {
            "condition": "'receipt' in tags",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is False

    def test_evaluate_false_boolean_variable(self, worker, sample_context):
        """GIVEN boolean variable WHEN false THEN returns false."""
        task_input = {
            "condition": "is_processed",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is False

    def test_evaluate_false_literal(self, worker):
        """GIVEN 'false' literal WHEN evaluating THEN returns false."""
        task_input = {
            "condition": "false",
            "context": {},
        }

        result = worker.execute_task(task_input)

        assert result["result"] is False


# ==============================================================================
# Logical Operator Tests
# ==============================================================================


class TestConditionWorkerLogicalOperators:
    """Tests for logical operators (and, or, not)."""

    def test_evaluate_and_both_true(self, worker, sample_context):
        """GIVEN AND with both true WHEN evaluating THEN returns true."""
        task_input = {
            "condition": "status == 'completed' and count > 40",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True

    def test_evaluate_and_one_false(self, worker, sample_context):
        """GIVEN AND with one false WHEN evaluating THEN returns false."""
        task_input = {
            "condition": "status == 'completed' and count < 40",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is False

    def test_evaluate_or_both_true(self, worker, sample_context):
        """GIVEN OR with both true WHEN evaluating THEN returns true."""
        task_input = {
            "condition": "status == 'completed' or count > 40",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True

    def test_evaluate_or_one_true(self, worker, sample_context):
        """GIVEN OR with one true WHEN evaluating THEN returns true."""
        task_input = {
            "condition": "status == 'pending' or count > 40",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True

    def test_evaluate_or_both_false(self, worker, sample_context):
        """GIVEN OR with both false WHEN evaluating THEN returns false."""
        task_input = {
            "condition": "status == 'pending' or count < 40",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is False

    def test_evaluate_not_true(self, worker, sample_context):
        """GIVEN NOT with true condition WHEN evaluating THEN returns false."""
        task_input = {
            "condition": "not is_valid",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is False

    def test_evaluate_not_false(self, worker, sample_context):
        """GIVEN NOT with false condition WHEN evaluating THEN returns true."""
        task_input = {
            "condition": "not is_processed",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True


# ==============================================================================
# String Operation Tests
# ==============================================================================


class TestConditionWorkerStringOperations:
    """Tests for string operations (contains, startswith, endswith)."""

    def test_evaluate_contains_true(self, worker, sample_context):
        """GIVEN contains with match WHEN evaluating THEN returns true."""
        task_input = {
            "condition": "name contains 'document'",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True

    def test_evaluate_contains_false(self, worker, sample_context):
        """GIVEN contains without match WHEN evaluating THEN returns false."""
        task_input = {
            "condition": "name contains 'invoice'",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is False

    def test_evaluate_startswith_true(self, worker, sample_context):
        """GIVEN startswith with match WHEN evaluating THEN returns true."""
        task_input = {
            "condition": "name startswith 'test'",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True

    def test_evaluate_startswith_false(self, worker, sample_context):
        """GIVEN startswith without match WHEN evaluating THEN returns false."""
        task_input = {
            "condition": "name startswith 'document'",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is False

    def test_evaluate_endswith_true(self, worker, sample_context):
        """GIVEN endswith with match WHEN evaluating THEN returns true."""
        task_input = {
            "condition": "name endswith 'document'",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True

    def test_evaluate_endswith_false(self, worker, sample_context):
        """GIVEN endswith without match WHEN evaluating THEN returns false."""
        task_input = {
            "condition": "name endswith 'test'",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is False


# ==============================================================================
# Membership Operator Tests
# ==============================================================================


class TestConditionWorkerMembershipOperators:
    """Tests for membership operators (in, not in)."""

    def test_evaluate_in_list_true(self, worker, sample_context):
        """GIVEN 'in' with value in list WHEN evaluating THEN returns true."""
        task_input = {
            "condition": "'urgent' in tags",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True

    def test_evaluate_in_literal_list(self, worker, sample_context):
        """GIVEN 'in' with literal list WHEN evaluating THEN returns correctly."""
        task_input = {
            "condition": "status in ['completed', 'approved']",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True

    def test_evaluate_not_in_true(self, worker, sample_context):
        """GIVEN 'not in' with value not in list WHEN evaluating THEN returns true."""
        task_input = {
            "condition": "status not in ['pending', 'failed']",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True

    def test_evaluate_not_in_false(self, worker, sample_context):
        """GIVEN 'not in' with value in list WHEN evaluating THEN returns false."""
        task_input = {
            "condition": "status not in ['completed', 'approved']",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is False


# ==============================================================================
# Dot Notation Tests
# ==============================================================================


class TestConditionWorkerDotNotation:
    """Tests for dot notation access."""

    def test_evaluate_nested_property(self, worker, sample_context):
        """GIVEN nested property access WHEN evaluating THEN resolves correctly."""
        task_input = {
            "condition": "metadata.type == 'invoice'",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True

    def test_evaluate_nested_numeric(self, worker, sample_context):
        """GIVEN nested numeric property WHEN evaluating THEN compares correctly."""
        task_input = {
            "condition": "metadata.pages >= 5",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True


# ==============================================================================
# Error Handling Tests
# ==============================================================================


class TestConditionWorkerErrors:
    """Tests for error handling."""

    def test_evaluate_missing_variable(self, worker):
        """GIVEN missing context variable WHEN evaluating THEN handles gracefully."""
        task_input = {
            "condition": "undefined_var == 'value'",
            "context": {},
        }

        result = worker.execute_task(task_input)

        # Missing variable returns None, which doesn't equal 'value'
        assert result["result"] is False

    def test_evaluate_missing_variable_boolean(self, worker):
        """GIVEN missing variable as boolean WHEN evaluating THEN returns false."""
        task_input = {
            "condition": "undefined_var",
            "context": {},
        }

        result = worker.execute_task(task_input)

        # None is falsy
        assert result["result"] is False

    def test_evaluate_invalid_comparison_syntax(self, worker):
        """GIVEN invalid comparison syntax WHEN evaluating THEN raises error."""
        task_input = {
            "condition": "a == == b",
            "context": {"a": 1, "b": 2},
        }

        with pytest.raises(ValueError):
            worker.execute_task(task_input)


# ==============================================================================
# Output Format Tests
# ==============================================================================


class TestConditionWorkerOutput:
    """Tests for output format structure."""

    def test_output_format_structure(self, worker, sample_context):
        """GIVEN any condition WHEN executing THEN output has correct structure."""
        task_input = {
            "condition": "count > 0",
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert "result" in result
        assert "condition" in result
        assert isinstance(result["result"], bool)
        assert isinstance(result["condition"], str)

    def test_output_includes_original_condition(self, worker, sample_context):
        """GIVEN condition WHEN executing THEN output includes original condition."""
        condition = "status == 'completed' and count > 10"
        task_input = {
            "condition": condition,
            "context": sample_context,
        }

        result = worker.execute_task(task_input)

        assert result["condition"] == condition


# ==============================================================================
# Base Worker Integration Tests
# ==============================================================================


class TestConditionWorkerBaseIntegration:
    """Tests for base worker integration."""

    def test_task_definition_name(self, worker):
        """GIVEN worker WHEN checking THEN has correct task definition name."""
        assert worker.task_definition_name == "condition_evaluator"

    def test_execute_calls_validate_input(self, worker):
        """GIVEN invalid input WHEN executing via base THEN validation runs."""
        task = Mock()
        task.input_data = {}  # Missing condition
        task.task_id = "task-123"
        task.workflow_instance_id = "wf-123"

        result = worker.execute(task)

        assert result.status.name == "FAILED"
        assert "condition" in result.output_data.get("error", "")

    def test_execute_successful_via_base(self, worker):
        """GIVEN valid input WHEN executing via base THEN succeeds."""
        task = Mock()
        task.input_data = {
            "condition": "value > 5",
            "context": {"value": 10},
        }
        task.task_id = "task-123"
        task.workflow_instance_id = "wf-123"

        result = worker.execute(task)

        assert result.status.name == "COMPLETED"
        assert result.output_data["data"]["result"] is True


# ==============================================================================
# Complex Expression Tests
# ==============================================================================


class TestConditionWorkerComplexExpressions:
    """Tests for complex conditional expressions."""

    def test_evaluate_complex_confidence_routing(self, worker):
        """GIVEN confidence routing expression WHEN evaluating THEN works correctly."""
        context = {"confidence": 0.65, "is_valid": True}

        # Low confidence needs review
        task_input = {
            "condition": "confidence < 0.70 and is_valid",
            "context": context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True

    def test_evaluate_complex_document_classification(self, worker):
        """GIVEN document classification expression WHEN evaluating THEN works correctly."""
        context = {
            "doc_type": "invoice",
            "page_count": 3,
            "has_signature": True,
        }

        task_input = {
            "condition": "doc_type == 'invoice' and page_count <= 5 and has_signature",
            "context": context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True

    def test_evaluate_multiple_or_conditions(self, worker):
        """GIVEN multiple OR conditions WHEN evaluating THEN handles correctly."""
        context = {"status": "pending"}

        task_input = {
            "condition": "status == 'completed' or status == 'approved' or status == 'pending'",
            "context": context,
        }

        result = worker.execute_task(task_input)

        assert result["result"] is True
