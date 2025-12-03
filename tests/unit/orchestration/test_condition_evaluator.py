"""
Unit tests for the Condition Worker (Condition Evaluator).

Tests cover:
- Equality and comparison operators
- Logical operators (and, or, not)
- Membership operators (in, not in)
- String operations (contains, startswith, endswith)
- Complex expressions
- Value resolution (literals, variables, dot notation)
- Security (no eval injection)
- Input validation
"""

import pytest
from app.orchestration.workers.condition_worker import ConditionWorker


class TestConditionWorkerEquality:
    """Tests for equality operators (==, !=)."""

    @pytest.fixture
    def worker(self):
        return ConditionWorker()

    def test_evaluate_equality_true(self, worker):
        """
        GIVEN condition 'status == "completed"' with status = "completed"
        WHEN evaluating
        THEN returns True
        """
        result = worker._evaluate_condition(
            'status == "completed"',
            {"status": "completed"}
        )

        assert result is True

    def test_evaluate_equality_false(self, worker):
        """
        GIVEN condition 'status == "completed"' with status = "pending"
        WHEN evaluating
        THEN returns False
        """
        result = worker._evaluate_condition(
            'status == "completed"',
            {"status": "pending"}
        )

        assert result is False

    def test_evaluate_inequality_true(self, worker):
        """
        GIVEN condition 'status != "failed"' with status = "completed"
        WHEN evaluating
        THEN returns True
        """
        result = worker._evaluate_condition(
            'status != "failed"',
            {"status": "completed"}
        )

        assert result is True

    def test_evaluate_inequality_false(self, worker):
        """
        GIVEN condition 'status != "failed"' with status = "failed"
        WHEN evaluating
        THEN returns False
        """
        result = worker._evaluate_condition(
            'status != "failed"',
            {"status": "failed"}
        )

        assert result is False

    def test_evaluate_number_equality(self, worker):
        """
        GIVEN numeric equality condition
        WHEN evaluating
        THEN correctly compares numbers
        """
        result = worker._evaluate_condition(
            "count == 10",
            {"count": 10}
        )

        assert result is True


class TestConditionWorkerComparison:
    """Tests for comparison operators (<, <=, >, >=)."""

    @pytest.fixture
    def worker(self):
        return ConditionWorker()

    def test_evaluate_greater_than_true(self, worker):
        """
        GIVEN condition 'score > 0.7' with score = 0.85
        WHEN evaluating
        THEN returns True
        """
        result = worker._evaluate_condition(
            "score > 0.7",
            {"score": 0.85}
        )

        assert result is True

    def test_evaluate_greater_than_false(self, worker):
        """
        GIVEN condition 'score > 0.7' with score = 0.65
        WHEN evaluating
        THEN returns False
        """
        result = worker._evaluate_condition(
            "score > 0.7",
            {"score": 0.65}
        )

        assert result is False

    def test_evaluate_greater_than_or_equal(self, worker):
        """
        GIVEN condition 'score >= 0.7' with score = 0.7
        WHEN evaluating
        THEN returns True (edge case)
        """
        result = worker._evaluate_condition(
            "score >= 0.7",
            {"score": 0.7}
        )

        assert result is True

    def test_evaluate_less_than(self, worker):
        """
        GIVEN condition 'confidence < 0.5'
        WHEN evaluating with confidence = 0.3
        THEN returns True
        """
        result = worker._evaluate_condition(
            "confidence < 0.5",
            {"confidence": 0.3}
        )

        assert result is True

    def test_evaluate_less_than_or_equal(self, worker):
        """
        GIVEN condition 'age <= 18'
        WHEN evaluating with age = 18
        THEN returns True
        """
        result = worker._evaluate_condition(
            "age <= 18",
            {"age": 18}
        )

        assert result is True

    def test_evaluate_comparison_with_integer_literal(self, worker):
        """
        GIVEN condition 'count > 100'
        WHEN evaluating with count = 150
        THEN returns True
        """
        result = worker._evaluate_condition(
            "count > 100",
            {"count": 150}
        )

        assert result is True


class TestConditionWorkerLogicalAnd:
    """Tests for logical AND operator."""

    @pytest.fixture
    def worker(self):
        return ConditionWorker()

    def test_evaluate_and_both_true(self, worker):
        """
        GIVEN 'a > 5 and b > 5' with a=10, b=10
        WHEN evaluating
        THEN returns True
        """
        result = worker._evaluate_condition(
            "a > 5 and b > 5",
            {"a": 10, "b": 10}
        )

        assert result is True

    def test_evaluate_and_first_false(self, worker):
        """
        GIVEN 'a > 5 and b > 5' with a=3, b=10
        WHEN evaluating
        THEN returns False
        """
        result = worker._evaluate_condition(
            "a > 5 and b > 5",
            {"a": 3, "b": 10}
        )

        assert result is False

    def test_evaluate_and_second_false(self, worker):
        """
        GIVEN 'a > 5 and b > 5' with a=10, b=3
        WHEN evaluating
        THEN returns False
        """
        result = worker._evaluate_condition(
            "a > 5 and b > 5",
            {"a": 10, "b": 3}
        )

        assert result is False

    def test_evaluate_and_case_insensitive(self, worker):
        """
        GIVEN 'a > 5 AND b > 5' (uppercase)
        WHEN evaluating
        THEN works correctly
        """
        result = worker._evaluate_condition(
            "a > 5 AND b > 5",
            {"a": 10, "b": 10}
        )

        assert result is True


class TestConditionWorkerLogicalOr:
    """Tests for logical OR operator."""

    @pytest.fixture
    def worker(self):
        return ConditionWorker()

    def test_evaluate_or_both_true(self, worker):
        """
        GIVEN 'a > 5 or b > 5' with a=10, b=10
        WHEN evaluating
        THEN returns True
        """
        result = worker._evaluate_condition(
            "a > 5 or b > 5",
            {"a": 10, "b": 10}
        )

        assert result is True

    def test_evaluate_or_first_true(self, worker):
        """
        GIVEN 'a > 5 or b > 5' with a=10, b=3
        WHEN evaluating
        THEN returns True
        """
        result = worker._evaluate_condition(
            "a > 5 or b > 5",
            {"a": 10, "b": 3}
        )

        assert result is True

    def test_evaluate_or_second_true(self, worker):
        """
        GIVEN 'a > 5 or b > 5' with a=3, b=10
        WHEN evaluating
        THEN returns True
        """
        result = worker._evaluate_condition(
            "a > 5 or b > 5",
            {"a": 3, "b": 10}
        )

        assert result is True

    def test_evaluate_or_both_false(self, worker):
        """
        GIVEN 'a > 5 or b > 5' with a=3, b=3
        WHEN evaluating
        THEN returns False
        """
        result = worker._evaluate_condition(
            "a > 5 or b > 5",
            {"a": 3, "b": 3}
        )

        assert result is False

    def test_evaluate_or_case_insensitive(self, worker):
        """
        GIVEN 'a > 5 OR b > 5' (uppercase)
        WHEN evaluating
        THEN works correctly
        """
        result = worker._evaluate_condition(
            "a > 5 OR b > 5",
            {"a": 3, "b": 10}
        )

        assert result is True


class TestConditionWorkerLogicalNot:
    """Tests for logical NOT operator."""

    @pytest.fixture
    def worker(self):
        return ConditionWorker()

    def test_evaluate_not_true(self, worker):
        """
        GIVEN 'not is_error' with is_error = False
        WHEN evaluating
        THEN returns True
        """
        result = worker._evaluate_condition(
            "not is_error",
            {"is_error": False}
        )

        assert result is True

    def test_evaluate_not_false(self, worker):
        """
        GIVEN 'not is_success' with is_success = True
        WHEN evaluating
        THEN returns False
        """
        result = worker._evaluate_condition(
            "not is_success",
            {"is_success": True}
        )

        assert result is False

    def test_evaluate_not_with_comparison(self, worker):
        """
        GIVEN 'not count > 10' with count = 5
        WHEN evaluating
        THEN returns True
        """
        result = worker._evaluate_condition(
            "not count > 10",
            {"count": 5}
        )

        assert result is True


class TestConditionWorkerMembership:
    """Tests for membership operators (in, not in)."""

    @pytest.fixture
    def worker(self):
        return ConditionWorker()

    def test_evaluate_in_list_true(self, worker):
        """
        GIVEN 'status in ["pending", "processing", "completed"]'
        WHEN evaluating with status = "pending"
        THEN returns True
        """
        result = worker._evaluate_condition(
            'status in ["pending", "processing", "completed"]',
            {"status": "pending"}
        )

        assert result is True

    def test_evaluate_in_list_false(self, worker):
        """
        GIVEN 'status in ["pending", "processing"]'
        WHEN evaluating with status = "failed"
        THEN returns False
        """
        result = worker._evaluate_condition(
            'status in ["pending", "processing"]',
            {"status": "failed"}
        )

        assert result is False

    def test_evaluate_not_in_list_true(self, worker):
        """
        GIVEN 'priority not in ["low", "normal"]'
        WHEN evaluating with priority = "critical"
        THEN returns True
        """
        result = worker._evaluate_condition(
            'priority not in ["low", "normal"]',
            {"priority": "critical"}
        )

        assert result is True

    def test_evaluate_not_in_list_false(self, worker):
        """
        GIVEN 'priority not in ["low", "normal"]'
        WHEN evaluating with priority = "low"
        THEN returns False
        """
        result = worker._evaluate_condition(
            'priority not in ["low", "normal"]',
            {"priority": "low"}
        )

        assert result is False

    def test_evaluate_in_variable_list(self, worker):
        """
        GIVEN 'item in allowed_items'
        WHEN evaluating with context containing allowed_items
        THEN correctly checks membership
        """
        result = worker._evaluate_condition(
            "item in allowed_items",
            {"item": "apple", "allowed_items": ["apple", "banana", "orange"]}
        )

        assert result is True


class TestConditionWorkerStringOperations:
    """Tests for string operations (contains, startswith, endswith)."""

    @pytest.fixture
    def worker(self):
        return ConditionWorker()

    def test_evaluate_contains_true(self, worker):
        """
        GIVEN 'message contains "error"'
        WHEN evaluating with message = "An error occurred"
        THEN returns True
        """
        result = worker._evaluate_condition(
            'message contains "error"',
            {"message": "An error occurred"}
        )

        assert result is True

    def test_evaluate_contains_false(self, worker):
        """
        GIVEN 'message contains "error"'
        WHEN evaluating with message = "Success!"
        THEN returns False
        """
        result = worker._evaluate_condition(
            'message contains "error"',
            {"message": "Success!"}
        )

        assert result is False

    def test_evaluate_startswith_true(self, worker):
        """
        GIVEN 'filename startswith "invoice"'
        WHEN evaluating with filename = "invoice_2024.pdf"
        THEN returns True
        """
        result = worker._evaluate_condition(
            'filename startswith "invoice"',
            {"filename": "invoice_2024.pdf"}
        )

        assert result is True

    def test_evaluate_startswith_false(self, worker):
        """
        GIVEN 'filename startswith "invoice"'
        WHEN evaluating with filename = "receipt_2024.pdf"
        THEN returns False
        """
        result = worker._evaluate_condition(
            'filename startswith "invoice"',
            {"filename": "receipt_2024.pdf"}
        )

        assert result is False

    def test_evaluate_endswith_true(self, worker):
        """
        GIVEN 'filename endswith ".pdf"'
        WHEN evaluating with filename = "document.pdf"
        THEN returns True
        """
        result = worker._evaluate_condition(
            'filename endswith ".pdf"',
            {"filename": "document.pdf"}
        )

        assert result is True

    def test_evaluate_endswith_false(self, worker):
        """
        GIVEN 'filename endswith ".pdf"'
        WHEN evaluating with filename = "document.docx"
        THEN returns False
        """
        result = worker._evaluate_condition(
            'filename endswith ".pdf"',
            {"filename": "document.docx"}
        )

        assert result is False


class TestConditionWorkerComplexExpressions:
    """Tests for complex expressions combining operators."""

    @pytest.fixture
    def worker(self):
        return ConditionWorker()

    def test_evaluate_and_or_combined(self, worker):
        """
        GIVEN complex condition with and/or
        WHEN evaluating
        THEN evaluates correctly (or has lower precedence)
        """
        # Note: 'or' is evaluated first due to split order
        result = worker._evaluate_condition(
            "a > 5 and b > 5 or c > 5",
            {"a": 10, "b": 10, "c": 3}
        )

        assert result is True

    def test_evaluate_multiple_ors(self, worker):
        """
        GIVEN condition with multiple ORs
        WHEN evaluating
        THEN any true makes result true
        """
        result = worker._evaluate_condition(
            "a > 100 or b > 100 or c > 100",
            {"a": 5, "b": 5, "c": 150}
        )

        assert result is True

    def test_evaluate_multiple_ands(self, worker):
        """
        GIVEN condition with multiple ANDs
        WHEN evaluating
        THEN all must be true
        """
        result = worker._evaluate_condition(
            "a > 0 and b > 0 and c > 0",
            {"a": 10, "b": 20, "c": 30}
        )

        assert result is True


class TestConditionWorkerValueResolution:
    """Tests for value resolution from strings."""

    @pytest.fixture
    def worker(self):
        return ConditionWorker()

    def test_resolve_string_single_quotes(self, worker):
        """
        GIVEN string literal with single quotes
        WHEN resolving
        THEN returns the string value
        """
        result = worker._resolve_value("'hello world'", {})

        assert result == "hello world"

    def test_resolve_string_double_quotes(self, worker):
        """
        GIVEN string literal with double quotes
        WHEN resolving
        THEN returns the string value
        """
        result = worker._resolve_value('"hello world"', {})

        assert result == "hello world"

    def test_resolve_integer(self, worker):
        """
        GIVEN integer string
        WHEN resolving
        THEN returns int
        """
        result = worker._resolve_value("42", {})

        assert result == 42
        assert isinstance(result, int)

    def test_resolve_float(self, worker):
        """
        GIVEN float string
        WHEN resolving
        THEN returns float
        """
        result = worker._resolve_value("3.14", {})

        assert result == 3.14
        assert isinstance(result, float)

    def test_resolve_boolean_true(self, worker):
        """
        GIVEN 'true' string
        WHEN resolving
        THEN returns True boolean
        """
        result = worker._resolve_value("true", {})

        assert result is True

    def test_resolve_boolean_false(self, worker):
        """
        GIVEN 'false' string
        WHEN resolving
        THEN returns False boolean
        """
        result = worker._resolve_value("false", {})

        assert result is False

    def test_resolve_boolean_case_insensitive(self, worker):
        """
        GIVEN 'TRUE' or 'FALSE' string
        WHEN resolving
        THEN returns correct boolean
        """
        assert worker._resolve_value("TRUE", {}) is True
        assert worker._resolve_value("FALSE", {}) is False

    def test_resolve_variable(self, worker):
        """
        GIVEN variable name
        WHEN resolving with context
        THEN returns context value
        """
        result = worker._resolve_value("my_var", {"my_var": "my_value"})

        assert result == "my_value"

    def test_resolve_dot_notation(self, worker):
        """
        GIVEN dot notation variable
        WHEN resolving with nested context
        THEN returns nested value
        """
        context = {
            "data": {
                "result": {
                    "score": 0.95
                }
            }
        }

        result = worker._resolve_value("data.result.score", context)

        assert result == 0.95

    def test_resolve_list_literal(self, worker):
        """
        GIVEN list literal string
        WHEN resolving
        THEN returns list
        """
        result = worker._resolve_value("[1, 2, 3]", {})

        assert result == [1, 2, 3]

    def test_resolve_empty_list(self, worker):
        """
        GIVEN empty list literal
        WHEN resolving
        THEN returns empty list
        """
        result = worker._resolve_value("[]", {})

        assert result == []

    def test_resolve_list_with_strings(self, worker):
        """
        GIVEN list with string literals
        WHEN resolving
        THEN returns list of strings
        """
        result = worker._resolve_value('["a", "b", "c"]', {})

        assert result == ["a", "b", "c"]


class TestConditionWorkerSecurity:
    """Tests for security - ensuring no code execution."""

    @pytest.fixture
    def worker(self):
        return ConditionWorker()

    def test_no_eval_injection(self, worker):
        """
        GIVEN malicious code in condition
        WHEN evaluating
        THEN does NOT execute (returns False or error)
        """
        # Attempting to inject __import__
        result = worker._evaluate_condition(
            '__import__("os").system("echo hacked")',
            {}
        )

        # Should just return False (variable not found) or raise error
        # NOT execute the code
        assert result is False or result is None

    def test_no_eval_in_string_literal(self, worker):
        """
        GIVEN string containing code
        WHEN evaluating
        THEN treats as literal string
        """
        result = worker._resolve_value(
            '"__import__(\'os\')"',
            {}
        )

        # Should return the string literal, not execute
        assert result == "__import__('os')"

    def test_comparison_with_suspicious_string(self, worker):
        """
        GIVEN comparison with suspicious content
        WHEN evaluating
        THEN safely compares strings
        """
        result = worker._evaluate_condition(
            'code == "__import__"',
            {"code": "safe_value"}
        )

        assert result is False


class TestConditionWorkerInputValidation:
    """Tests for input validation."""

    @pytest.fixture
    def worker(self):
        return ConditionWorker()

    def test_validate_missing_condition(self, worker):
        """
        GIVEN input without condition
        WHEN validating
        THEN returns error
        """
        error = worker.validate_input({"context": {}})

        assert error is not None
        assert "condition" in error

    def test_validate_non_string_condition(self, worker):
        """
        GIVEN condition that is not a string
        WHEN validating
        THEN returns error
        """
        error = worker.validate_input({"condition": 123})

        assert error is not None
        assert "string" in error

    def test_validate_empty_condition(self, worker):
        """
        GIVEN empty condition string
        WHEN validating
        THEN returns error
        """
        error = worker.validate_input({"condition": "   "})

        assert error is not None
        assert "empty" in error

    def test_validate_valid_input(self, worker):
        """
        GIVEN valid input
        WHEN validating
        THEN returns None
        """
        error = worker.validate_input({
            "condition": "score > 0.7",
            "context": {"score": 0.85}
        })

        assert error is None


class TestConditionWorkerExecuteTask:
    """Tests for the execute_task method."""

    @pytest.fixture
    def worker(self):
        return ConditionWorker()

    def test_execute_task_returns_result(self, worker):
        """
        GIVEN valid task input
        WHEN executing task
        THEN returns dict with result and condition
        """
        result = worker.execute_task({
            "condition": "value > 10",
            "context": {"value": 20}
        })

        assert "result" in result
        assert "condition" in result
        assert result["result"] is True
        assert result["condition"] == "value > 10"

    def test_execute_task_false_result(self, worker):
        """
        GIVEN condition that evaluates to false
        WHEN executing task
        THEN result is False
        """
        result = worker.execute_task({
            "condition": "value > 100",
            "context": {"value": 20}
        })

        assert result["result"] is False

    def test_execute_task_with_empty_context(self, worker):
        """
        GIVEN task with no context
        WHEN executing
        THEN handles gracefully
        """
        result = worker.execute_task({
            "condition": "true"
        })

        assert result["result"] is True


class TestConditionWorkerBooleanVariables:
    """Tests for evaluating simple boolean variables."""

    @pytest.fixture
    def worker(self):
        return ConditionWorker()

    def test_evaluate_boolean_variable_true(self, worker):
        """
        GIVEN boolean variable name
        WHEN evaluating with true value
        THEN returns True
        """
        result = worker._evaluate_condition(
            "is_valid",
            {"is_valid": True}
        )

        assert result is True

    def test_evaluate_boolean_variable_false(self, worker):
        """
        GIVEN boolean variable name
        WHEN evaluating with false value
        THEN returns False
        """
        result = worker._evaluate_condition(
            "is_valid",
            {"is_valid": False}
        )

        assert result is False

    def test_evaluate_truthy_value(self, worker):
        """
        GIVEN variable with truthy value
        WHEN evaluating
        THEN returns True
        """
        result = worker._evaluate_condition(
            "count",
            {"count": 5}
        )

        assert result is True

    def test_evaluate_falsy_value(self, worker):
        """
        GIVEN variable with falsy value (0)
        WHEN evaluating
        THEN returns False
        """
        result = worker._evaluate_condition(
            "count",
            {"count": 0}
        )

        assert result is False

    def test_evaluate_missing_variable_falsy(self, worker):
        """
        GIVEN variable not in context
        WHEN evaluating
        THEN returns False (None is falsy)
        """
        result = worker._evaluate_condition(
            "missing_var",
            {"other_var": "value"}
        )

        assert result is False
