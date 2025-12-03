"""
Condition Worker

Evaluates conditional expressions for If nodes in workflows.
Uses safe expression evaluation without eval() to prevent code injection.
"""

from typing import Any, Dict, Optional
import operator
import re

from .base_worker import BaseWorker


class ConditionWorker(BaseWorker):
    """
    Worker that evaluates conditional expressions.

    Input Parameters:
    - condition (str): Condition expression to evaluate
    - context (dict): Variables available for the condition

    Supported operators:
    - Comparison: ==, !=, <, <=, >, >=
    - Logical: and, or, not
    - Membership: in, not in
    - String: contains, startswith, endswith

    Example conditions:
    - "status == 'completed'"
    - "count > 10"
    - "name in ['Alice', 'Bob']"
    - "message contains 'error'"

    Output:
    - result (bool): True or False
    - condition: The evaluated condition
    """

    # Safe comparison operators (ordered by length - longer operators first)
    OPERATORS = {
        "<=": operator.le,
        ">=": operator.ge,
        "!=": operator.ne,
        "==": operator.eq,
        "<": operator.lt,
        ">": operator.gt,
    }

    def __init__(self):
        super().__init__(task_definition_name="condition_evaluator")

    def validate_input(self, task_input: Dict[str, Any]) -> Optional[str]:
        """Validate condition worker input."""
        if "condition" not in task_input:
            return "Missing required parameter: 'condition'"

        if not isinstance(task_input["condition"], str):
            return "Parameter 'condition' must be a string"

        if not task_input["condition"].strip():
            return "Parameter 'condition' cannot be empty"

        return None

    def execute_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate conditional expression.

        Args:
            task_input: Contains condition and context

        Returns:
            Dictionary with result (bool) and condition
        """
        condition = task_input["condition"]
        context = task_input.get("context", {})

        self.log_info(f"Evaluating condition: {condition}")
        self.log_debug(f"Context: {context}")

        result = self._evaluate_condition(condition, context)

        self.log_info(f"Condition result: {result}")

        return {
            "result": result,
            "condition": condition,
        }

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """
        Safely evaluate condition without eval().

        Args:
            condition: Condition string
            context: Variables for evaluation

        Returns:
            Boolean result
        """
        condition = condition.strip()

        # Handle logical operators
        if " or " in condition.lower():
            parts = re.split(r'\s+or\s+', condition, flags=re.IGNORECASE)
            return any(self._evaluate_condition(part, context) for part in parts)

        if " and " in condition.lower():
            parts = re.split(r'\s+and\s+', condition, flags=re.IGNORECASE)
            return all(self._evaluate_condition(part, context) for part in parts)

        if condition.lower().startswith("not "):
            inner = condition[4:].strip()
            return not self._evaluate_condition(inner, context)

        # Handle string operations
        if " contains " in condition.lower():
            return self._evaluate_contains(condition, context)

        if " startswith " in condition.lower():
            return self._evaluate_startswith(condition, context)

        if " endswith " in condition.lower():
            return self._evaluate_endswith(condition, context)

        # Handle membership
        if " not in " in condition.lower():
            return self._evaluate_not_in(condition, context)

        if " in " in condition.lower():
            return self._evaluate_in(condition, context)

        # Handle comparison operators
        for op_str, op_func in self.OPERATORS.items():
            if op_str in condition:
                return self._evaluate_comparison(condition, op_str, op_func, context)

        # If no operator found, treat as boolean variable
        value = self._resolve_value(condition, context)
        return bool(value)

    def _evaluate_comparison(
        self, condition: str, op_str: str, op_func: Any, context: Dict[str, Any]
    ) -> bool:
        """Evaluate comparison expression."""
        parts = condition.split(op_str, 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid comparison: {condition}")

        left_str = parts[0].strip()
        right_str = parts[1].strip()

        # Check for invalid syntax (e.g., "a == == b")
        if not left_str or not right_str:
            raise ValueError(f"Invalid comparison: {condition}")

        # Check if right side starts with another operator
        for op in self.OPERATORS.keys():
            if right_str.startswith(op):
                raise ValueError(f"Invalid comparison syntax: {condition}")

        left = self._resolve_value(left_str, context)
        right = self._resolve_value(right_str, context)

        return op_func(left, right)

    def _evaluate_contains(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate 'contains' expression."""
        parts = re.split(r'\s+contains\s+', condition, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) != 2:
            raise ValueError(f"Invalid contains expression: {condition}")

        left = str(self._resolve_value(parts[0].strip(), context))
        right = str(self._resolve_value(parts[1].strip(), context))

        return right in left

    def _evaluate_startswith(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate 'startswith' expression."""
        parts = re.split(r'\s+startswith\s+', condition, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) != 2:
            raise ValueError(f"Invalid startswith expression: {condition}")

        left = str(self._resolve_value(parts[0].strip(), context))
        right = str(self._resolve_value(parts[1].strip(), context))

        return left.startswith(right)

    def _evaluate_endswith(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate 'endswith' expression."""
        parts = re.split(r'\s+endswith\s+', condition, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) != 2:
            raise ValueError(f"Invalid endswith expression: {condition}")

        left = str(self._resolve_value(parts[0].strip(), context))
        right = str(self._resolve_value(parts[1].strip(), context))

        return left.endswith(right)

    def _evaluate_in(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate 'in' expression."""
        parts = re.split(r'\s+in\s+', condition, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) != 2:
            raise ValueError(f"Invalid 'in' expression: {condition}")

        left = self._resolve_value(parts[0].strip(), context)
        right = self._resolve_value(parts[1].strip(), context)

        return left in right

    def _evaluate_not_in(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate 'not in' expression."""
        parts = re.split(r'\s+not\s+in\s+', condition, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) != 2:
            raise ValueError(f"Invalid 'not in' expression: {condition}")

        left = self._resolve_value(parts[0].strip(), context)
        right = self._resolve_value(parts[1].strip(), context)

        return left not in right

    def _resolve_value(self, value_str: str, context: Dict[str, Any]) -> Any:
        """
        Resolve a value from string representation.

        Handles:
        - String literals: 'value' or "value"
        - Numbers: 123, 45.67
        - Booleans: true, false
        - Variables: variable_name
        - Dot notation: object.field
        - Lists: [1, 2, 3]

        Args:
            value_str: String representation of value
            context: Context variables

        Returns:
            Resolved value
        """
        value_str = value_str.strip()

        # String literal
        if (value_str.startswith("'") and value_str.endswith("'")) or \
           (value_str.startswith('"') and value_str.endswith('"')):
            return value_str[1:-1]

        # Boolean
        if value_str.lower() == "true":
            return True
        if value_str.lower() == "false":
            return False

        # Number
        try:
            if "." in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            pass

        # List literal
        if value_str.startswith("[") and value_str.endswith("]"):
            # Simple list parsing
            items_str = value_str[1:-1]
            if not items_str.strip():
                return []
            items = [self._resolve_value(item.strip(), context) for item in items_str.split(",")]
            return items

        # Variable with dot notation
        if "." in value_str:
            parts = value_str.split(".")
            current = context.get(parts[0])
            for part in parts[1:]:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None
            return current

        # Simple variable
        return context.get(value_str)
