"""
Unit tests for the Expression Resolver service.

Tests cover:
- Simple variable resolution
- Nested path resolution
- Array indexing
- Multiple expressions in one string
- Missing node handling
- Invalid path handling
- Dependency extraction
- Security (no eval/exec)
"""

import pytest
from app.orchestration.services.expression_resolver import ExpressionResolver


class TestExpressionResolverSimpleVariables:
    """Tests for simple variable resolution."""

    def test_resolve_simple_variable(self):
        """
        GIVEN a resolver with node outputs
        WHEN resolving {{$("Node1").field}}
        THEN returns the field value
        """
        node_outputs = {
            "Node1": {"field": "test_value"}
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve('{{$("Node1").field}}')

        assert result == "test_value"

    def test_resolve_simple_number(self):
        """
        GIVEN a resolver with numeric output
        WHEN resolving an expression pointing to a number
        THEN returns the numeric value (not string)
        """
        node_outputs = {
            "ExtractNode": {"confidence_score": 0.85}
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve('{{$("ExtractNode").confidence_score}}')

        assert result == 0.85
        assert isinstance(result, float)

    def test_resolve_simple_boolean(self):
        """
        GIVEN a resolver with boolean output
        WHEN resolving an expression pointing to a boolean
        THEN returns the boolean value
        """
        node_outputs = {
            "ValidateNode": {"is_valid": True}
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve('{{$("ValidateNode").is_valid}}')

        assert result is True
        assert isinstance(result, bool)

    def test_resolve_returns_dict(self):
        """
        GIVEN a resolver with dict output
        WHEN resolving an expression pointing to a dict
        THEN returns the entire dict
        """
        node_outputs = {
            "DataNode": {"data": {"name": "Test", "value": 123}}
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve('{{$("DataNode").data}}')

        assert result == {"name": "Test", "value": 123}
        assert isinstance(result, dict)

    def test_resolve_returns_list(self):
        """
        GIVEN a resolver with list output
        WHEN resolving an expression pointing to a list
        THEN returns the entire list
        """
        node_outputs = {
            "ItemsNode": {"items": [1, 2, 3, 4, 5]}
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve('{{$("ItemsNode").items}}')

        assert result == [1, 2, 3, 4, 5]
        assert isinstance(result, list)


class TestExpressionResolverNestedPaths:
    """Tests for nested path resolution."""

    def test_resolve_nested_path(self):
        """
        GIVEN a resolver with nested output
        WHEN resolving {{$("Node1").data.nested.field}}
        THEN returns the deeply nested value
        """
        node_outputs = {
            "Node1": {
                "data": {
                    "nested": {
                        "field": "deep_value"
                    }
                }
            }
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve('{{$("Node1").data.nested.field}}')

        assert result == "deep_value"

    def test_resolve_three_level_nesting(self):
        """
        GIVEN a resolver with three-level nested output
        WHEN resolving a three-level path
        THEN returns the correct value
        """
        node_outputs = {
            "InvoiceExtract": {
                "output": {
                    "extracted_data": {
                        "vendor": {
                            "name": "Acme Corp",
                            "address": "123 Main St"
                        }
                    }
                }
            }
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve('{{$("InvoiceExtract").output.extracted_data.vendor.name}}')

        assert result == "Acme Corp"


class TestExpressionResolverArrayIndexing:
    """Tests for array indexing in paths."""

    def test_resolve_array_index(self):
        """
        GIVEN a resolver with array output
        WHEN resolving {{$("Node1").items[0].name}}
        THEN returns the indexed item's field
        """
        node_outputs = {
            "Node1": {
                "items": [
                    {"name": "First", "value": 1},
                    {"name": "Second", "value": 2}
                ]
            }
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve('{{$("Node1").items[0].name}}')

        assert result == "First"

    def test_resolve_array_second_index(self):
        """
        GIVEN a resolver with array output
        WHEN resolving items[1]
        THEN returns the second item
        """
        node_outputs = {
            "ListNode": {
                "data": [
                    {"id": "a"},
                    {"id": "b"},
                    {"id": "c"}
                ]
            }
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve('{{$("ListNode").data[1].id}}')

        assert result == "b"

    def test_resolve_array_nested_in_object(self):
        """
        GIVEN a resolver with deeply nested array
        WHEN resolving path with array index in the middle
        THEN returns the correct value
        """
        node_outputs = {
            "ComplexNode": {
                "response": {
                    "results": [
                        {"category": "A", "scores": [90, 85, 88]},
                        {"category": "B", "scores": [75, 80, 82]}
                    ]
                }
            }
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve('{{$("ComplexNode").response.results[0].category}}')

        assert result == "A"


class TestExpressionResolverMultipleExpressions:
    """Tests for strings with multiple expressions."""

    def test_resolve_multiple_expressions(self):
        """
        GIVEN a string with multiple expressions
        WHEN resolving
        THEN replaces all expressions with string values
        """
        node_outputs = {
            "Node1": {"name": "John"},
            "Node2": {"age": 30}
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve(
            'Name: {{$("Node1").name}}, Age: {{$("Node2").age}}'
        )

        assert result == "Name: John, Age: 30"

    def test_resolve_expression_with_surrounding_text(self):
        """
        GIVEN a string with an expression and surrounding text
        WHEN resolving
        THEN returns string with expression replaced
        """
        node_outputs = {
            "OrderNode": {"order_id": "ORD-12345"}
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve(
            'Processing order: {{$("OrderNode").order_id}} now.'
        )

        assert result == "Processing order: ORD-12345 now."
        assert isinstance(result, str)

    def test_resolve_three_expressions_in_string(self):
        """
        GIVEN a string with three expressions
        WHEN resolving
        THEN replaces all correctly
        """
        node_outputs = {
            "A": {"x": 1},
            "B": {"y": 2},
            "C": {"z": 3}
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve(
            '{{$("A").x}} + {{$("B").y}} = {{$("C").z}}'
        )

        assert result == "1 + 2 = 3"


class TestExpressionResolverMissingNodes:
    """Tests for handling missing nodes and paths."""

    def test_resolve_missing_node_returns_none(self):
        """
        GIVEN a resolver without the referenced node
        WHEN resolving an expression to that node
        THEN returns None (and logs warning)
        """
        node_outputs = {
            "ExistingNode": {"data": "value"}
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve('{{$("MissingNode").data}}')

        assert result is None

    def test_resolve_invalid_path_returns_none(self):
        """
        GIVEN a resolver with a node
        WHEN resolving an invalid path
        THEN returns None
        """
        node_outputs = {
            "Node1": {"data": {"existing": "value"}}
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve('{{$("Node1").data.nonexistent.path}}')

        assert result is None

    def test_resolve_invalid_array_index_returns_none(self):
        """
        GIVEN a resolver with an array
        WHEN resolving an out-of-bounds index
        THEN returns None
        """
        node_outputs = {
            "Node1": {"items": [{"name": "only_item"}]}
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve('{{$("Node1").items[5].name}}')

        assert result is None

    def test_resolve_non_dict_traversal_returns_none(self):
        """
        GIVEN a resolver with a primitive value
        WHEN trying to traverse into it
        THEN returns None
        """
        node_outputs = {
            "Node1": {"value": "string_value"}
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve('{{$("Node1").value.inner}}')

        assert result is None


class TestExpressionResolverDictInputs:
    """Tests for resolving expressions in dict structures."""

    def test_resolve_dict_with_expressions(self):
        """
        GIVEN a dict with expression values
        WHEN resolving
        THEN returns dict with all expressions resolved
        """
        node_outputs = {
            "Source": {"id": "123", "name": "Test"}
        }
        resolver = ExpressionResolver(node_outputs)

        input_dict = {
            "entity_id": '{{$("Source").id}}',
            "entity_name": '{{$("Source").name}}',
            "static_value": "unchanged"
        }

        result = resolver.resolve(input_dict)

        assert result == {
            "entity_id": "123",
            "entity_name": "Test",
            "static_value": "unchanged"
        }

    def test_resolve_nested_dict_with_expressions(self):
        """
        GIVEN a nested dict with expressions
        WHEN resolving
        THEN resolves all nested expressions
        """
        node_outputs = {
            "Config": {"host": "localhost", "port": 8080}
        }
        resolver = ExpressionResolver(node_outputs)

        input_dict = {
            "server": {
                "host": '{{$("Config").host}}',
                "port": '{{$("Config").port}}'
            },
            "metadata": {
                "label": "test"
            }
        }

        result = resolver.resolve(input_dict)

        assert result["server"]["host"] == "localhost"
        assert result["server"]["port"] == 8080
        assert result["metadata"]["label"] == "test"


class TestExpressionResolverListInputs:
    """Tests for resolving expressions in list structures."""

    def test_resolve_list_with_expressions(self):
        """
        GIVEN a list with expression items
        WHEN resolving
        THEN resolves all list items
        """
        node_outputs = {
            "A": {"val": 1},
            "B": {"val": 2},
            "C": {"val": 3}
        }
        resolver = ExpressionResolver(node_outputs)

        input_list = [
            '{{$("A").val}}',
            '{{$("B").val}}',
            '{{$("C").val}}'
        ]

        result = resolver.resolve(input_list)

        assert result == [1, 2, 3]


class TestExpressionResolverDependencyExtraction:
    """Tests for extracting dependencies from node configs."""

    def test_extract_dependencies_single(self):
        """
        GIVEN a node config with one expression
        WHEN extracting dependencies
        THEN returns the referenced node name
        """
        node_config = {
            "inputs": {
                "data": '{{$("SourceNode").output}}'
            }
        }

        deps = ExpressionResolver.extract_dependencies(node_config)

        assert deps == ["SourceNode"]

    def test_extract_dependencies_multiple(self):
        """
        GIVEN a node config with multiple expressions
        WHEN extracting dependencies
        THEN returns all referenced node names
        """
        node_config = {
            "inputs": {
                "field1": '{{$("NodeA").data}}',
                "field2": '{{$("NodeB").result}}',
                "field3": '{{$("NodeC").value}}'
            }
        }

        deps = ExpressionResolver.extract_dependencies(node_config)

        assert set(deps) == {"NodeA", "NodeB", "NodeC"}

    def test_extract_dependencies_deduplication(self):
        """
        GIVEN a node config with duplicate references
        WHEN extracting dependencies
        THEN returns unique node names only
        """
        node_config = {
            "inputs": {
                "field1": '{{$("SameNode").a}}',
                "field2": '{{$("SameNode").b}}',
                "field3": '{{$("SameNode").c}}'
            }
        }

        deps = ExpressionResolver.extract_dependencies(node_config)

        assert deps == ["SameNode"]

    def test_extract_dependencies_nested_inputs(self):
        """
        GIVEN a node config with nested input structure
        WHEN extracting dependencies
        THEN finds expressions in nested structures
        """
        node_config = {
            "inputs": {
                "outer": {
                    "inner": {
                        "value": '{{$("DeepNode").data}}'
                    }
                }
            }
        }

        deps = ExpressionResolver.extract_dependencies(node_config)

        assert deps == ["DeepNode"]

    def test_extract_dependencies_in_list(self):
        """
        GIVEN a node config with expressions in lists
        WHEN extracting dependencies
        THEN finds expressions in list items
        """
        node_config = {
            "inputs": {
                "items": [
                    '{{$("ListNode1").item}}',
                    '{{$("ListNode2").item}}'
                ]
            }
        }

        deps = ExpressionResolver.extract_dependencies(node_config)

        assert set(deps) == {"ListNode1", "ListNode2"}

    def test_extract_dependencies_no_inputs(self):
        """
        GIVEN a node config without inputs
        WHEN extracting dependencies
        THEN returns empty list
        """
        node_config = {
            "type": "SimpleNode",
            "name": "test"
        }

        deps = ExpressionResolver.extract_dependencies(node_config)

        assert deps == []


class TestExpressionResolverSecurity:
    """Tests for security - ensuring no code execution."""

    def test_no_eval_injection_with_code(self):
        """
        GIVEN malicious input attempting code injection
        WHEN resolving
        THEN does NOT execute the code (returns string as-is)
        """
        node_outputs = {
            "Node1": {"data": "safe_value"}
        }
        resolver = ExpressionResolver(node_outputs)

        # Attempting to inject Python code
        malicious_input = '__import__("os").system("echo hacked")'

        # Should return the string as-is (no expression pattern match)
        # The key test is that it returns the string unchanged,
        # NOT that it executes the code
        result = resolver.resolve(malicious_input)

        assert result == malicious_input
        # Verify the malicious code was NOT executed (it's returned as a string)
        assert isinstance(result, str)

    def test_no_eval_in_expression_path(self):
        """
        GIVEN a path that looks like code
        WHEN resolving
        THEN treats it as literal path (returns None for invalid path)
        """
        node_outputs = {
            "Node1": {"data": {"__class__": "should_not_access"}}
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve('{{$("Node1").data.__class__.__bases__}}')

        # Should safely return None as this path doesn't exist properly
        # The key is it doesn't execute anything
        assert result is None or isinstance(result, str)

    def test_expression_pattern_strict(self):
        """
        GIVEN various malformed expressions
        WHEN resolving
        THEN returns them unchanged (no partial matching)
        """
        resolver = ExpressionResolver({"Node": {"val": "test"}})

        # These should not match the expression pattern
        test_cases = [
            '${Node.val}',           # Wrong syntax
            '{{Node.val}}',          # Missing $()
            '{{$("Node")}}',         # Missing path
            '{$("Node").val}',       # Single braces
            '{{$("Node"}.val}}',     # Malformed
        ]

        for test_input in test_cases:
            result = resolver.resolve(test_input)
            assert result == test_input, f"Failed for input: {test_input}"


class TestExpressionResolverResolveAllInputs:
    """Tests for the resolve_all_inputs method."""

    def test_resolve_all_inputs(self):
        """
        GIVEN a node config with inputs containing expressions
        WHEN calling resolve_all_inputs
        THEN returns config with resolved inputs
        """
        node_outputs = {
            "PreviousNode": {"result": "computed_value"}
        }
        resolver = ExpressionResolver(node_outputs)

        node_config = {
            "name": "CurrentNode",
            "type": "Processor",
            "inputs": {
                "data": '{{$("PreviousNode").result}}',
                "static": "unchanged"
            }
        }

        result = resolver.resolve_all_inputs(node_config)

        assert result["name"] == "CurrentNode"
        assert result["type"] == "Processor"
        assert result["inputs"]["data"] == "computed_value"
        assert result["inputs"]["static"] == "unchanged"

    def test_resolve_all_inputs_no_inputs_key(self):
        """
        GIVEN a node config without inputs key
        WHEN calling resolve_all_inputs
        THEN returns config unchanged
        """
        resolver = ExpressionResolver({})

        node_config = {
            "name": "SimpleNode",
            "type": "Trigger"
        }

        result = resolver.resolve_all_inputs(node_config)

        assert result == node_config


class TestExpressionResolverEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_resolve_empty_string(self):
        """
        GIVEN an empty string
        WHEN resolving
        THEN returns empty string
        """
        resolver = ExpressionResolver({})
        assert resolver.resolve("") == ""

    def test_resolve_none_value(self):
        """
        GIVEN None value
        WHEN resolving
        THEN returns None
        """
        resolver = ExpressionResolver({})
        assert resolver.resolve(None) is None

    def test_resolve_primitive_types(self):
        """
        GIVEN primitive types (int, float, bool)
        WHEN resolving
        THEN returns unchanged
        """
        resolver = ExpressionResolver({})

        assert resolver.resolve(42) == 42
        assert resolver.resolve(3.14) == 3.14
        assert resolver.resolve(True) is True
        assert resolver.resolve(False) is False

    def test_resolve_special_characters_in_node_name(self):
        """
        GIVEN a node name with underscores and numbers
        WHEN resolving
        THEN works correctly
        """
        node_outputs = {
            "Extract_Node_1": {"data": "value"}
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve('{{$("Extract_Node_1").data}}')

        assert result == "value"

    def test_resolve_null_value_in_output(self):
        """
        GIVEN a node output with null value
        WHEN resolving
        THEN returns None
        """
        node_outputs = {
            "Node1": {"nullable_field": None}
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve('{{$("Node1").nullable_field}}')

        assert result is None

    def test_resolve_expression_with_spaces(self):
        """
        GIVEN an expression with proper formatting
        WHEN resolving
        THEN works correctly
        """
        node_outputs = {
            "Node With Space": {"data": "value"}  # Spaces in node name
        }
        resolver = ExpressionResolver(node_outputs)

        result = resolver.resolve('{{$("Node With Space").data}}')

        assert result == "value"
