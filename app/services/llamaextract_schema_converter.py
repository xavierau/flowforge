"""
LlamaExtract schema converter.

Converts JSON Schema Draft-07 to LlamaExtract-compatible format by:
1. Stripping unsupported metadata ($schema, $id)
2. Moving constraints to field descriptions
3. Validating limits (nesting, size, properties)
"""

import copy
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class LlamaExtractSchemaConversionError(Exception):
    """Raised when schema conversion fails."""

    pass


class LlamaExtractSchemaConverter:
    """
    Converts JSON Schema Draft-07 to LlamaExtract-compatible format.

    LlamaExtract has limited schema support and doesn't support:
    - $schema, $id metadata
    - format (date, email, etc.)
    - pattern (regex)
    - minLength, maxLength
    - minimum, maximum
    - enum as keyword
    - default values

    These constraints are moved to field descriptions so the LLM understands them.
    """

    MAX_NESTING_DEPTH = 7
    MAX_PROPERTIES = 5000
    MAX_JSON_SIZE = 150000

    # Fields to strip from schema
    METADATA_FIELDS = {"$schema", "$id", "$ref", "$comment"}

    # Constraint fields to move to description
    CONSTRAINT_FIELDS = {
        "format",
        "pattern",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "enum",
        "default",
        "const",
    }

    # Format hints for human-readable descriptions
    FORMAT_HINTS = {
        "date": "YYYY-MM-DD",
        "date-time": "ISO 8601 datetime",
        "time": "HH:MM:SS",
        "email": "email address",
        "uri": "URL",
        "uuid": "UUID format",
    }

    def convert(self, schema: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        """
        Convert schema to LlamaExtract format.

        Args:
            schema: JSON Schema Draft-07 schema

        Returns:
            Tuple of (converted_schema, warnings)

        Raises:
            LlamaExtractSchemaConversionError: If schema exceeds limits
        """
        converted = copy.deepcopy(schema)
        warnings: list[str] = []

        self._validate_root_type(converted)
        converted = self._strip_metadata(converted)
        converted = self._convert_properties_recursive(converted, warnings)
        self._validate_limits(converted, warnings)

        return converted, warnings

    def _validate_root_type(self, schema: dict[str, Any]) -> None:
        """Validate root schema is object type."""
        if schema.get("type") != "object":
            raise LlamaExtractSchemaConversionError(
                "LlamaExtract requires root schema type to be 'object'"
            )

    def _strip_metadata(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Remove unsupported metadata fields from root."""
        return {k: v for k, v in schema.items() if k not in self.METADATA_FIELDS}

    def _convert_properties_recursive(
        self,
        schema: dict[str, Any],
        warnings: list[str],
        depth: int = 0,
    ) -> dict[str, Any]:
        """Recursively convert properties in schema."""
        if "properties" not in schema:
            return schema

        if depth > self.MAX_NESTING_DEPTH:
            warnings.append(
                f"Schema exceeds max nesting depth ({self.MAX_NESTING_DEPTH}). "
                "Deep properties may not extract correctly."
            )

        converted_props = {}
        for name, prop in schema["properties"].items():
            converted_props[name] = self._convert_property(prop, name, depth, warnings)

        schema["properties"] = converted_props
        return schema

    def _convert_property(
        self,
        prop: dict[str, Any],
        name: str,
        depth: int,
        warnings: list[str],
    ) -> dict[str, Any]:
        """Convert a single property, moving constraints to description."""
        converted: dict[str, Any] = {}

        self._handle_description(prop, converted)
        self._copy_allowed_fields(prop, converted, name, depth, warnings)

        return converted

    def _handle_description(
        self,
        prop: dict[str, Any],
        converted: dict[str, Any],
    ) -> None:
        """Build and set description with constraints."""
        original_desc = prop.get("description", "")
        constraint_desc = self._constraints_to_description(prop)

        if constraint_desc:
            if original_desc:
                converted["description"] = f"{original_desc} [{constraint_desc}]"
            else:
                converted["description"] = f"[{constraint_desc}]"
        elif original_desc:
            converted["description"] = original_desc

    def _copy_allowed_fields(
        self,
        prop: dict[str, Any],
        converted: dict[str, Any],
        name: str,
        depth: int,
        warnings: list[str],
    ) -> None:
        """Copy fields that are allowed in LlamaExtract schema."""
        skip_fields = self.METADATA_FIELDS | self.CONSTRAINT_FIELDS | {"description"}

        for key, value in prop.items():
            if key in skip_fields:
                continue

            if key == "properties" and isinstance(value, dict):
                converted["properties"] = self._convert_nested_properties(
                    value, depth, warnings
                )
            elif key == "items" and isinstance(value, dict):
                converted["items"] = self._convert_property(
                    value, f"{name}[]", depth + 1, warnings
                )
            else:
                converted[key] = value

    def _convert_nested_properties(
        self,
        properties: dict[str, Any],
        depth: int,
        warnings: list[str],
    ) -> dict[str, Any]:
        """Convert nested properties dict."""
        converted = {}
        for prop_name, prop_value in properties.items():
            converted[prop_name] = self._convert_property(
                prop_value, prop_name, depth + 1, warnings
            )
        return converted

    def _constraints_to_description(self, prop: dict[str, Any]) -> str:
        """Build description string from constraints."""
        parts: list[str] = []

        self._add_format_constraint(prop, parts)
        self._add_pattern_constraint(prop, parts)
        self._add_length_constraints(prop, parts)
        self._add_numeric_constraints(prop, parts)
        self._add_enum_constraint(prop, parts)
        self._add_default_constraint(prop, parts)

        return ". ".join(parts)

    def _add_format_constraint(self, prop: dict[str, Any], parts: list[str]) -> None:
        """Add format constraint to description parts."""
        if "format" not in prop:
            return
        fmt = prop["format"]
        hint = self.FORMAT_HINTS.get(fmt, fmt)
        parts.append(f"Format: {hint}")

    def _add_pattern_constraint(self, prop: dict[str, Any], parts: list[str]) -> None:
        """Add pattern constraint to description parts."""
        if "pattern" in prop:
            parts.append(f"Pattern: {prop['pattern']}")

    def _add_length_constraints(self, prop: dict[str, Any], parts: list[str]) -> None:
        """Add string length constraints to description parts."""
        if "minLength" in prop:
            parts.append(f"Min length: {prop['minLength']}")
        if "maxLength" in prop:
            parts.append(f"Max length: {prop['maxLength']}")

    def _add_numeric_constraints(self, prop: dict[str, Any], parts: list[str]) -> None:
        """Add numeric range constraints to description parts."""
        if "minimum" in prop:
            parts.append(f"Min: {prop['minimum']}")
        if "maximum" in prop:
            parts.append(f"Max: {prop['maximum']}")
        if "exclusiveMinimum" in prop:
            parts.append(f"Min (exclusive): {prop['exclusiveMinimum']}")
        if "exclusiveMaximum" in prop:
            parts.append(f"Max (exclusive): {prop['exclusiveMaximum']}")

    def _add_enum_constraint(self, prop: dict[str, Any], parts: list[str]) -> None:
        """Add enum constraint to description parts."""
        if "enum" not in prop:
            return
        values = ", ".join(str(v) for v in prop["enum"])
        parts.append(f"Allowed values: {values}")

    def _add_default_constraint(self, prop: dict[str, Any], parts: list[str]) -> None:
        """Add default value to description parts."""
        if "default" in prop:
            parts.append(f"Default: {prop['default']}")

    def _validate_limits(
        self,
        schema: dict[str, Any],
        warnings: list[str],
    ) -> None:
        """Validate schema against LlamaExtract limits."""
        self._validate_json_size(schema)
        self._validate_property_count(schema)
        self._validate_nesting_depth(schema, warnings)

    def _validate_json_size(self, schema: dict[str, Any]) -> None:
        """Validate schema JSON size is within limit."""
        json_size = len(json.dumps(schema))
        if json_size > self.MAX_JSON_SIZE:
            raise LlamaExtractSchemaConversionError(
                f"Schema size ({json_size} chars) exceeds LlamaExtract limit "
                f"({self.MAX_JSON_SIZE} chars)"
            )

    def _validate_property_count(self, schema: dict[str, Any]) -> None:
        """Validate total property count is within limit."""
        prop_count = self._count_properties(schema)
        if prop_count > self.MAX_PROPERTIES:
            raise LlamaExtractSchemaConversionError(
                f"Schema has {prop_count} properties, "
                f"exceeds limit of {self.MAX_PROPERTIES}"
            )

    def _validate_nesting_depth(
        self,
        schema: dict[str, Any],
        warnings: list[str],
    ) -> None:
        """Validate nesting depth and add warning if exceeded."""
        max_depth = self._get_max_depth(schema)
        if max_depth > self.MAX_NESTING_DEPTH:
            warnings.append(
                f"Schema has {max_depth} nesting levels. "
                f"LlamaExtract recommends max {self.MAX_NESTING_DEPTH}."
            )

    def _count_properties(self, schema: dict[str, Any]) -> int:
        """Recursively count total properties."""
        count = 0

        if "properties" in schema:
            for prop in schema["properties"].values():
                count += 1
                count += self._count_properties(prop)

        if "items" in schema and isinstance(schema["items"], dict):
            count += self._count_properties(schema["items"])

        return count

    def _get_max_depth(self, schema: dict[str, Any], current: int = 0) -> int:
        """Get maximum nesting depth."""
        max_depth = current

        if "properties" in schema:
            for prop in schema["properties"].values():
                depth = self._get_max_depth(prop, current + 1)
                max_depth = max(max_depth, depth)

        if "items" in schema and isinstance(schema["items"], dict):
            depth = self._get_max_depth(schema["items"], current + 1)
            max_depth = max(max_depth, depth)

        return max_depth
