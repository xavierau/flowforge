"""JSON Schema validation service."""

from typing import Any
import jsonschema
from jsonschema import Draft7Validator, ValidationError


class SchemaValidator:
    """Service for validating JSON data against JSON schemas."""

    @staticmethod
    def validate(data: dict[str, Any], schema: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate data against a JSON schema.

        Args:
            data: Data to validate
            schema: JSON schema

        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            # Validate the schema itself first
            Draft7Validator.check_schema(schema)

            # Validate the data
            validator = Draft7Validator(schema)
            errors = list(validator.iter_errors(data))

            if errors:
                error_messages = [
                    f"{'.'.join(str(p) for p in error.path)}: {error.message}"
                    for error in errors
                ]
                return False, error_messages

            return True, []

        except jsonschema.SchemaError as e:
            return False, [f"Invalid schema: {e.message}"]
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]

    @staticmethod
    def is_valid_schema(schema: dict[str, Any]) -> bool:
        """
        Check if a JSON schema is valid.

        Args:
            schema: JSON schema to validate

        Returns:
            True if schema is valid
        """
        try:
            Draft7Validator.check_schema(schema)
            return True
        except jsonschema.SchemaError:
            return False
