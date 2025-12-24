"""Unit tests for LlamaExtract schema converter."""

import json

import pytest

from app.services.llamaextract_schema_converter import (
    LlamaExtractSchemaConversionError,
    LlamaExtractSchemaConverter,
)


class TestLlamaExtractSchemaConverterInit:
    """Tests for LlamaExtractSchemaConverter initialization."""

    def test_init_creates_instance(self):
        """Test that converter can be instantiated."""
        converter = LlamaExtractSchemaConverter()
        assert converter is not None

    def test_has_max_nesting_depth_constant(self):
        """Test that MAX_NESTING_DEPTH constant is defined."""
        assert LlamaExtractSchemaConverter.MAX_NESTING_DEPTH == 7

    def test_has_max_properties_constant(self):
        """Test that MAX_PROPERTIES constant is defined."""
        assert LlamaExtractSchemaConverter.MAX_PROPERTIES == 5000

    def test_has_max_json_size_constant(self):
        """Test that MAX_JSON_SIZE constant is defined."""
        assert LlamaExtractSchemaConverter.MAX_JSON_SIZE == 150000


class TestBasicSchemaConversion:
    """Tests for basic schema conversion."""

    @pytest.fixture
    def converter(self):
        """Create a converter instance."""
        return LlamaExtractSchemaConverter()

    def test_convert_returns_tuple(self, converter):
        """Test that convert returns tuple of (schema, warnings)."""
        schema = {"type": "object", "properties": {}}
        result = converter.convert(schema)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_convert_returns_converted_schema(self, converter):
        """Test that first element is the converted schema."""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        converted, _ = converter.convert(schema)
        assert isinstance(converted, dict)
        assert "type" in converted
        assert converted["type"] == "object"

    def test_convert_returns_warnings_list(self, converter):
        """Test that second element is a list of warnings."""
        schema = {"type": "object", "properties": {}}
        _, warnings = converter.convert(schema)
        assert isinstance(warnings, list)

    def test_convert_does_not_modify_original(self, converter):
        """Test that conversion does not modify the original schema."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {"name": {"type": "string", "format": "email"}},
        }
        original_copy = json.loads(json.dumps(schema))
        converter.convert(schema)
        assert schema == original_copy


class TestMetadataStripping:
    """Tests for stripping unsupported metadata fields."""

    @pytest.fixture
    def converter(self):
        """Create a converter instance."""
        return LlamaExtractSchemaConverter()

    def test_strips_schema_field(self, converter):
        """Test that $schema field is stripped."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {},
        }
        converted, _ = converter.convert(schema)
        assert "$schema" not in converted

    def test_strips_id_field(self, converter):
        """Test that $id field is stripped."""
        schema = {
            "$id": "https://example.com/schema",
            "type": "object",
            "properties": {},
        }
        converted, _ = converter.convert(schema)
        assert "$id" not in converted

    def test_strips_ref_field(self, converter):
        """Test that $ref field is stripped."""
        schema = {
            "$ref": "#/definitions/test",
            "type": "object",
            "properties": {},
        }
        converted, _ = converter.convert(schema)
        assert "$ref" not in converted

    def test_strips_comment_field(self, converter):
        """Test that $comment field is stripped."""
        schema = {
            "$comment": "This is a comment",
            "type": "object",
            "properties": {},
        }
        converted, _ = converter.convert(schema)
        assert "$comment" not in converted

    def test_strips_multiple_metadata_fields(self, converter):
        """Test that multiple metadata fields are stripped together."""
        schema = {
            "$schema": "draft-07",
            "$id": "test-id",
            "$ref": "#/ref",
            "$comment": "comment",
            "type": "object",
            "properties": {},
        }
        converted, _ = converter.convert(schema)
        assert "$schema" not in converted
        assert "$id" not in converted
        assert "$ref" not in converted
        assert "$comment" not in converted


class TestConstraintToDescription:
    """Tests for converting constraints to description."""

    @pytest.fixture
    def converter(self):
        """Create a converter instance."""
        return LlamaExtractSchemaConverter()

    def test_format_date_to_description(self, converter):
        """Test that date format is added to description."""
        schema = {
            "type": "object",
            "properties": {"date": {"type": "string", "format": "date"}},
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["date"]["description"]
        assert "Format: YYYY-MM-DD" in desc

    def test_format_datetime_to_description(self, converter):
        """Test that date-time format is added to description."""
        schema = {
            "type": "object",
            "properties": {"timestamp": {"type": "string", "format": "date-time"}},
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["timestamp"]["description"]
        assert "Format: ISO 8601 datetime" in desc

    def test_format_email_to_description(self, converter):
        """Test that email format is added to description."""
        schema = {
            "type": "object",
            "properties": {"email": {"type": "string", "format": "email"}},
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["email"]["description"]
        assert "Format: email address" in desc

    def test_format_uri_to_description(self, converter):
        """Test that uri format is added to description."""
        schema = {
            "type": "object",
            "properties": {"url": {"type": "string", "format": "uri"}},
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["url"]["description"]
        assert "Format: URL" in desc

    def test_format_uuid_to_description(self, converter):
        """Test that uuid format is added to description."""
        schema = {
            "type": "object",
            "properties": {"id": {"type": "string", "format": "uuid"}},
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["id"]["description"]
        assert "Format: UUID format" in desc

    def test_format_unknown_to_description(self, converter):
        """Test that unknown format is used as-is in description."""
        schema = {
            "type": "object",
            "properties": {"custom": {"type": "string", "format": "custom-format"}},
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["custom"]["description"]
        assert "Format: custom-format" in desc

    def test_pattern_to_description(self, converter):
        """Test that pattern is added to description."""
        schema = {
            "type": "object",
            "properties": {"code": {"type": "string", "pattern": "^[A-Z]{3}$"}},
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["code"]["description"]
        assert "Pattern: ^[A-Z]{3}$" in desc

    def test_minlength_to_description(self, converter):
        """Test that minLength is added to description."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string", "minLength": 3}},
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["name"]["description"]
        assert "Min length: 3" in desc

    def test_maxlength_to_description(self, converter):
        """Test that maxLength is added to description."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string", "maxLength": 100}},
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["name"]["description"]
        assert "Max length: 100" in desc

    def test_minimum_to_description(self, converter):
        """Test that minimum is added to description."""
        schema = {
            "type": "object",
            "properties": {"age": {"type": "integer", "minimum": 0}},
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["age"]["description"]
        assert "Min: 0" in desc

    def test_maximum_to_description(self, converter):
        """Test that maximum is added to description."""
        schema = {
            "type": "object",
            "properties": {"age": {"type": "integer", "maximum": 150}},
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["age"]["description"]
        assert "Max: 150" in desc

    def test_exclusive_minimum_to_description(self, converter):
        """Test that exclusiveMinimum is added to description."""
        schema = {
            "type": "object",
            "properties": {"price": {"type": "number", "exclusiveMinimum": 0}},
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["price"]["description"]
        assert "Min (exclusive): 0" in desc

    def test_exclusive_maximum_to_description(self, converter):
        """Test that exclusiveMaximum is added to description."""
        schema = {
            "type": "object",
            "properties": {"discount": {"type": "number", "exclusiveMaximum": 100}},
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["discount"]["description"]
        assert "Max (exclusive): 100" in desc

    def test_enum_to_description(self, converter):
        """Test that enum values are added to description."""
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "inactive", "pending"]}
            },
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["status"]["description"]
        assert "Allowed values: active, inactive, pending" in desc

    def test_default_to_description(self, converter):
        """Test that default value is added to description."""
        schema = {
            "type": "object",
            "properties": {"count": {"type": "integer", "default": 10}},
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["count"]["description"]
        assert "Default: 10" in desc

    def test_preserves_existing_description(self, converter):
        """Test that existing description is preserved with constraints appended."""
        schema = {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "User email address",
                    "format": "email",
                }
            },
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["email"]["description"]
        assert "User email address" in desc
        assert "Format: email address" in desc

    def test_multiple_constraints_joined(self, converter):
        """Test that multiple constraints are joined with periods."""
        schema = {
            "type": "object",
            "properties": {
                "age": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 150,
                    "default": 18,
                }
            },
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["age"]["description"]
        assert "Min: 0" in desc
        assert "Max: 150" in desc
        assert "Default: 18" in desc

    def test_constraint_fields_stripped_from_property(self, converter):
        """Test that constraint fields are stripped from converted property."""
        schema = {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "format": "email",
                    "pattern": ".*@.*",
                    "minLength": 5,
                    "maxLength": 100,
                }
            },
        }
        converted, _ = converter.convert(schema)
        prop = converted["properties"]["email"]
        assert "format" not in prop
        assert "pattern" not in prop
        assert "minLength" not in prop
        assert "maxLength" not in prop


class TestNestedObjectHandling:
    """Tests for handling nested objects in schema."""

    @pytest.fixture
    def converter(self):
        """Create a converter instance."""
        return LlamaExtractSchemaConverter()

    def test_converts_nested_object_properties(self, converter):
        """Test that nested object properties are converted."""
        schema = {
            "type": "object",
            "properties": {
                "address": {
                    "type": "object",
                    "properties": {
                        "zip": {"type": "string", "pattern": "^[0-9]{5}$"}
                    },
                }
            },
        }
        converted, _ = converter.convert(schema)
        nested_prop = converted["properties"]["address"]["properties"]["zip"]
        assert "description" in nested_prop
        assert "Pattern: ^[0-9]{5}$" in nested_prop["description"]

    def test_converts_deeply_nested_properties(self, converter):
        """Test that deeply nested properties are converted."""
        schema = {
            "type": "object",
            "properties": {
                "level1": {
                    "type": "object",
                    "properties": {
                        "level2": {
                            "type": "object",
                            "properties": {
                                "level3": {"type": "string", "format": "date"}
                            },
                        }
                    },
                }
            },
        }
        converted, _ = converter.convert(schema)
        deep_prop = converted["properties"]["level1"]["properties"]["level2"][
            "properties"
        ]["level3"]
        assert "description" in deep_prop
        assert "Format: YYYY-MM-DD" in deep_prop["description"]

    def test_preserves_nested_type_field(self, converter):
        """Test that type field is preserved in nested objects."""
        schema = {
            "type": "object",
            "properties": {
                "person": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            },
        }
        converted, _ = converter.convert(schema)
        assert converted["properties"]["person"]["type"] == "object"
        assert converted["properties"]["person"]["properties"]["name"]["type"] == "string"


class TestArrayItemsHandling:
    """Tests for handling array items in schema."""

    @pytest.fixture
    def converter(self):
        """Create a converter instance."""
        return LlamaExtractSchemaConverter()

    def test_converts_array_items_constraints(self, converter):
        """Test that array items constraints are converted."""
        schema = {
            "type": "object",
            "properties": {
                "emails": {
                    "type": "array",
                    "items": {"type": "string", "format": "email"},
                }
            },
        }
        converted, _ = converter.convert(schema)
        items = converted["properties"]["emails"]["items"]
        assert "description" in items
        assert "Format: email address" in items["description"]

    def test_converts_array_of_objects(self, converter):
        """Test that array of objects is converted correctly."""
        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "quantity": {"type": "integer", "minimum": 1}
                        },
                    },
                }
            },
        }
        converted, _ = converter.convert(schema)
        nested_prop = converted["properties"]["items"]["items"]["properties"]["quantity"]
        assert "description" in nested_prop
        assert "Min: 1" in nested_prop["description"]

    def test_preserves_array_type(self, converter):
        """Test that array type is preserved."""
        schema = {
            "type": "object",
            "properties": {
                "tags": {"type": "array", "items": {"type": "string"}}
            },
        }
        converted, _ = converter.convert(schema)
        assert converted["properties"]["tags"]["type"] == "array"


class TestValidationLimits:
    """Tests for validation limits."""

    @pytest.fixture
    def converter(self):
        """Create a converter instance."""
        return LlamaExtractSchemaConverter()

    def test_warns_on_excessive_nesting_depth(self, converter):
        """Test that warning is added for deep nesting."""
        # Create schema with nesting depth > MAX_NESTING_DEPTH (7)
        deep_schema = {"type": "object", "properties": {}}
        current = deep_schema
        for i in range(10):  # Create 10 levels of nesting
            current["properties"]["level"] = {"type": "object", "properties": {}}
            current = current["properties"]["level"]
        current["properties"]["leaf"] = {"type": "string"}

        _, warnings = converter.convert(deep_schema)
        assert any("nesting" in w.lower() for w in warnings)

    def test_raises_on_schema_size_exceeded(self, converter):
        """Test that error is raised when schema size exceeds limit."""
        # Create a schema that exceeds MAX_JSON_SIZE (150000)
        large_schema = {"type": "object", "properties": {}}
        for i in range(3000):
            large_schema["properties"][f"prop_{i}"] = {
                "type": "string",
                "description": "A" * 50,  # Long description to increase size
            }

        with pytest.raises(LlamaExtractSchemaConversionError, match="size.*exceeds"):
            converter.convert(large_schema)

    def test_raises_on_property_count_exceeded(self, converter):
        """Test that error is raised when property count exceeds limit."""
        # Create a schema with more than MAX_PROPERTIES (5000)
        large_schema = {"type": "object", "properties": {}}
        for i in range(5100):
            large_schema["properties"][f"p{i}"] = {"type": "string"}

        with pytest.raises(
            LlamaExtractSchemaConversionError, match="properties.*exceeds"
        ):
            converter.convert(large_schema)

    def test_counts_nested_properties(self, converter):
        """Test that property count includes nested properties."""
        # Create schema with nested properties that exceed property limit
        # but stay under JSON size limit
        # Using short property names to minimize JSON size
        schema = {"type": "object", "properties": {}}
        for i in range(102):
            nested = {"type": "object", "properties": {}}
            for j in range(50):  # 50 nested per object
                nested["properties"][f"n{j}"] = {"type": "string"}
            schema["properties"][f"o{i}"] = nested

        # 102 top-level objects + 102*50 nested = 5202 properties > 5000 limit
        # Verify the count exceeds limit
        count = converter._count_properties(schema)
        assert count > converter.MAX_PROPERTIES

        # Verify JSON size is under limit (so we hit property limit first)
        json_size = len(json.dumps(schema))
        assert json_size < converter.MAX_JSON_SIZE

        with pytest.raises(
            LlamaExtractSchemaConversionError, match="properties.*exceeds"
        ):
            converter.convert(schema)


class TestErrorCases:
    """Tests for error handling."""

    @pytest.fixture
    def converter(self):
        """Create a converter instance."""
        return LlamaExtractSchemaConverter()

    def test_raises_when_root_type_not_object(self, converter):
        """Test that error is raised when root type is not 'object'."""
        schema = {"type": "array", "items": {"type": "string"}}
        with pytest.raises(
            LlamaExtractSchemaConversionError,
            match="root schema type to be 'object'",
        ):
            converter.convert(schema)

    def test_raises_when_type_missing(self, converter):
        """Test that error is raised when type is missing."""
        schema = {"properties": {"name": {"type": "string"}}}
        with pytest.raises(
            LlamaExtractSchemaConversionError,
            match="root schema type to be 'object'",
        ):
            converter.convert(schema)

    def test_raises_for_string_root_type(self, converter):
        """Test that error is raised for string root type."""
        schema = {"type": "string"}
        with pytest.raises(LlamaExtractSchemaConversionError):
            converter.convert(schema)

    def test_raises_for_integer_root_type(self, converter):
        """Test that error is raised for integer root type."""
        schema = {"type": "integer"}
        with pytest.raises(LlamaExtractSchemaConversionError):
            converter.convert(schema)


class TestPreservesAllowedFields:
    """Tests for preserving allowed schema fields."""

    @pytest.fixture
    def converter(self):
        """Create a converter instance."""
        return LlamaExtractSchemaConverter()

    def test_preserves_type_field(self, converter):
        """Test that type field is preserved."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }
        converted, _ = converter.convert(schema)
        assert converted["properties"]["name"]["type"] == "string"

    def test_preserves_required_field(self, converter):
        """Test that required field is preserved."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        converted, _ = converter.convert(schema)
        assert converted["required"] == ["name"]

    def test_preserves_title_field(self, converter):
        """Test that title field is preserved."""
        schema = {
            "type": "object",
            "title": "Invoice",
            "properties": {},
        }
        converted, _ = converter.convert(schema)
        assert converted["title"] == "Invoice"

    def test_preserves_additional_properties(self, converter):
        """Test that additionalProperties field is preserved."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "additionalProperties": False,
        }
        converted, _ = converter.convert(schema)
        assert converted["additionalProperties"] is False


class TestPropertyCountAndDepthCalculation:
    """Tests for internal property counting and depth calculation."""

    @pytest.fixture
    def converter(self):
        """Create a converter instance."""
        return LlamaExtractSchemaConverter()

    def test_counts_flat_properties(self, converter):
        """Test counting properties in flat schema."""
        schema = {
            "type": "object",
            "properties": {
                "a": {"type": "string"},
                "b": {"type": "string"},
                "c": {"type": "string"},
            },
        }
        count = converter._count_properties(schema)
        assert count == 3

    def test_counts_nested_properties(self, converter):
        """Test counting properties in nested schema."""
        schema = {
            "type": "object",
            "properties": {
                "outer": {
                    "type": "object",
                    "properties": {
                        "inner1": {"type": "string"},
                        "inner2": {"type": "string"},
                    },
                }
            },
        }
        count = converter._count_properties(schema)
        # 1 (outer) + 2 (inner1, inner2) = 3
        assert count == 3

    def test_counts_array_items_properties(self, converter):
        """Test counting properties in array items."""
        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "value": {"type": "number"},
                        },
                    },
                }
            },
        }
        count = converter._count_properties(schema)
        # 1 (items array) + 2 (name, value in items) = 3
        assert count == 3

    def test_calculates_flat_depth(self, converter):
        """Test depth calculation for flat schema."""
        schema = {
            "type": "object",
            "properties": {"a": {"type": "string"}},
        }
        depth = converter._get_max_depth(schema)
        assert depth == 1  # properties level = 1

    def test_calculates_nested_depth(self, converter):
        """Test depth calculation for nested schema."""
        schema = {
            "type": "object",
            "properties": {
                "level1": {
                    "type": "object",
                    "properties": {
                        "level2": {
                            "type": "object",
                            "properties": {"level3": {"type": "string"}},
                        }
                    },
                }
            },
        }
        depth = converter._get_max_depth(schema)
        assert depth == 3

    def test_calculates_array_depth(self, converter):
        """Test depth calculation for array items."""
        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    },
                }
            },
        }
        depth = converter._get_max_depth(schema)
        # Level 1: "items" property
        # Level 2: array "items" (the items keyword)
        # Level 3: "name" property inside array item object
        assert depth == 3


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.fixture
    def converter(self):
        """Create a converter instance."""
        return LlamaExtractSchemaConverter()

    def test_handles_empty_properties(self, converter):
        """Test handling of empty properties object."""
        schema = {"type": "object", "properties": {}}
        converted, warnings = converter.convert(schema)
        assert converted["properties"] == {}
        assert warnings == []

    def test_handles_property_without_type(self, converter):
        """Test handling of property without type field."""
        schema = {
            "type": "object",
            "properties": {"data": {"description": "Some data"}},
        }
        converted, _ = converter.convert(schema)
        assert "description" in converted["properties"]["data"]

    def test_handles_enum_with_mixed_types(self, converter):
        """Test handling of enum with mixed value types."""
        schema = {
            "type": "object",
            "properties": {
                "value": {"enum": [1, "two", 3.0, True, None]}
            },
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["value"]["description"]
        assert "Allowed values:" in desc

    def test_handles_numeric_enum(self, converter):
        """Test handling of numeric enum values."""
        schema = {
            "type": "object",
            "properties": {
                "rating": {"type": "integer", "enum": [1, 2, 3, 4, 5]}
            },
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["rating"]["description"]
        assert "Allowed values: 1, 2, 3, 4, 5" in desc

    def test_handles_schema_without_properties_key(self, converter):
        """Test handling of object schema without properties key."""
        schema = {"type": "object"}
        converted, warnings = converter.convert(schema)
        assert converted["type"] == "object"
        assert "properties" not in converted

    def test_description_only_has_constraints_when_no_original(self, converter):
        """Test that description is only constraints when no original description."""
        schema = {
            "type": "object",
            "properties": {"age": {"type": "integer", "minimum": 0}},
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["age"]["description"]
        assert desc == "[Min: 0]"

    def test_description_appends_constraints_with_brackets(self, converter):
        """Test that constraints are appended in brackets."""
        schema = {
            "type": "object",
            "properties": {
                "age": {
                    "type": "integer",
                    "description": "Person's age",
                    "minimum": 0,
                }
            },
        }
        converted, _ = converter.convert(schema)
        desc = converted["properties"]["age"]["description"]
        assert desc == "Person's age [Min: 0]"
