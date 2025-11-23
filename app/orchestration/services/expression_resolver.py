"""
Expression Resolver Service

Resolves workflow expressions like {{$("NodeName").data.field}} by fetching
values from previous node outputs. Supports nested paths and provides security
against code injection.
"""

import re
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ExpressionResolver:
    """
    Resolves expressions in workflow node inputs.

    Expression syntax: {{$("NodeName").path.to.field}}

    Security:
    - No eval() or exec() - pure string parsing
    - Whitelist-based path traversal
    - Input validation
    """

    # Pattern to match {{$("NodeName").path.to.field}}
    EXPRESSION_PATTERN = re.compile(
        r'\{\{\$\("([^"]+)"\)\.([^}]+)\}\}'
    )

    def __init__(self, node_outputs: Dict[str, Dict[str, Any]]):
        """
        Initialize resolver with node outputs.

        Args:
            node_outputs: Dictionary mapping node names to their output data
                         e.g., {"Node1": {"data": {"result": "value"}}}
        """
        self.node_outputs = node_outputs

    def resolve(self, value: Any) -> Any:
        """
        Resolve expressions in a value recursively.

        Args:
            value: Value to resolve (string, dict, list, or primitive)

        Returns:
            Value with all expressions resolved
        """
        if isinstance(value, str):
            return self._resolve_string(value)
        elif isinstance(value, dict):
            return {k: self.resolve(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.resolve(item) for item in value]
        else:
            return value

    def _resolve_string(self, text: str) -> Any:
        """
        Resolve expressions in a string.

        If the string is ONLY an expression, return the resolved value.
        If it contains multiple expressions or text, return a string with replacements.

        Args:
            text: String potentially containing expressions

        Returns:
            Resolved value (string or other type)
        """
        matches = list(self.EXPRESSION_PATTERN.finditer(text))

        if not matches:
            return text

        # If entire string is a single expression, return the actual value
        if len(matches) == 1 and matches[0].group(0) == text:
            node_name = matches[0].group(1)
            path = matches[0].group(2)
            return self._resolve_expression(node_name, path)

        # Multiple expressions or mixed with text - replace all with string values
        result = text
        for match in reversed(matches):  # Reverse to maintain positions
            node_name = match.group(1)
            path = match.group(2)
            value = self._resolve_expression(node_name, path)

            # Convert to string for replacement
            str_value = str(value) if value is not None else ""
            result = result[:match.start()] + str_value + result[match.end():]

        return result

    def _resolve_expression(self, node_name: str, path: str) -> Any:
        """
        Resolve a single expression to its value.

        Args:
            node_name: Name of the node to fetch output from
            path: Dot-separated path to the value (e.g., "data.field.nested")

        Returns:
            Resolved value or None if not found
        """
        # Validate node exists
        if node_name not in self.node_outputs:
            logger.warning(
                f"Expression references unknown node: {node_name}. "
                f"Available nodes: {list(self.node_outputs.keys())}"
            )
            return None

        # Traverse path
        current = self.node_outputs[node_name]
        path_parts = path.split('.')

        for part in path_parts:
            # Handle array indexing (e.g., "items[0]")
            array_match = re.match(r'(\w+)\[(\d+)\]', part)

            if array_match:
                field_name = array_match.group(1)
                index = int(array_match.group(2))

                if not isinstance(current, dict) or field_name not in current:
                    logger.warning(
                        f"Path '{path}' not found in node '{node_name}': "
                        f"missing field '{field_name}'"
                    )
                    return None

                current = current[field_name]

                if not isinstance(current, list) or index >= len(current):
                    logger.warning(
                        f"Path '{path}' not found in node '{node_name}': "
                        f"invalid index {index}"
                    )
                    return None

                current = current[index]
            else:
                # Regular field access
                if isinstance(current, dict):
                    if part not in current:
                        logger.warning(
                            f"Path '{path}' not found in node '{node_name}': "
                            f"missing field '{part}'"
                        )
                        return None
                    current = current[part]
                else:
                    logger.warning(
                        f"Path '{path}' not found in node '{node_name}': "
                        f"cannot traverse non-dict at '{part}'"
                    )
                    return None

        return current

    def resolve_all_inputs(self, node_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve all expressions in a node's input configuration.

        Args:
            node_config: Node configuration with potential expressions

        Returns:
            Configuration with all expressions resolved
        """
        if "inputs" not in node_config:
            return node_config

        resolved_config = node_config.copy()
        resolved_config["inputs"] = self.resolve(node_config["inputs"])

        return resolved_config

    @staticmethod
    def extract_dependencies(node_config: Dict[str, Any]) -> list[str]:
        """
        Extract node names that this node depends on (via expressions).

        Args:
            node_config: Node configuration to analyze

        Returns:
            List of node names referenced in expressions
        """
        dependencies = set()

        def scan_value(value: Any):
            if isinstance(value, str):
                matches = ExpressionResolver.EXPRESSION_PATTERN.finditer(value)
                for match in matches:
                    dependencies.add(match.group(1))
            elif isinstance(value, dict):
                for v in value.values():
                    scan_value(v)
            elif isinstance(value, list):
                for item in value:
                    scan_value(item)

        scan_value(node_config.get("inputs", {}))

        return list(dependencies)
