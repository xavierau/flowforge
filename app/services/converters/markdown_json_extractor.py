"""Markdown-to-JSON extractor implementation.

Uses text-only models (cheaper than vision) to extract structured data from markdown.
Supports both Google Gemini 2.0 Flash and OpenAI GPT-4o-mini.
"""

import json
import time
from typing import Any, Dict
import logging

from google import genai
from google.genai import types
from openai import OpenAI

from app.services.converters.base import (
    IMarkdownToJsonExtractor,
    MarkdownExtractionResult,
)
from app.services.schema_validator import SchemaValidator

logger = logging.getLogger(__name__)


class MarkdownJsonExtractor(IMarkdownToJsonExtractor):
    """Markdown-to-JSON extractor using text-only models.

    Extracts structured data from markdown content using cheaper text models
    instead of expensive vision models. Supports schema validation.
    """

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: str,
    ):
        """Initialize markdown-to-JSON extractor.

        Args:
            provider: Provider name (google or openai)
            model: Model name (gemini-2.0-flash or gpt-4o-mini)
            api_key: API key for the provider
        """
        self.provider = provider
        self.model = model
        self.validator = SchemaValidator()

        if provider == "google":
            self.client = genai.Client(api_key=api_key)
        elif provider == "openai":
            self.client = OpenAI(api_key=api_key)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _clean_schema_for_gemini(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Clean JSON schema for Gemini API compatibility.

        Removes $ prefixed metadata fields not permitted by Gemini.

        Args:
            schema: Input JSON schema

        Returns:
            Cleaned schema without metadata fields
        """
        if not isinstance(schema, dict):
            return schema

        cleaned = {}
        for key, value in schema.items():
            # Skip metadata fields that start with $
            if key.startswith("$"):
                continue

            # Recursively clean nested objects
            if isinstance(value, dict):
                cleaned[key] = self._clean_schema_for_gemini(value)
            elif isinstance(value, list):
                cleaned[key] = [
                    self._clean_schema_for_gemini(item)
                    if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                cleaned[key] = value

        return cleaned

    async def extract(
        self,
        markdown_content: str,
        schema: Dict[str, Any],
        custom_prompt: str = "",
    ) -> MarkdownExtractionResult:
        """Extract structured data from markdown content.

        Args:
            markdown_content: Markdown content (may include page markers)
            schema: JSON schema defining the structure to extract
            custom_prompt: Additional extraction instructions

        Returns:
            MarkdownExtractionResult with extracted data and validation

        Raises:
            ValueError: If extraction fails or produces invalid JSON
        """
        start_time = time.time()

        # Build extraction prompt
        extraction_prompt = f"""Extract structured data from the following markdown document.

JSON SCHEMA:
{json.dumps(schema, indent=2)}

MARKDOWN DOCUMENT:
{markdown_content}

ADDITIONAL INSTRUCTIONS:
{custom_prompt if custom_prompt else "Extract all relevant information accurately."}

REQUIREMENTS:
1. Return ONLY valid JSON matching the schema
2. Extract information from ALL pages (marked with <!-- PAGE N -->)
3. Combine information from multiple pages intelligently
4. Ensure all required fields are present
5. Use null for missing optional fields

Return the JSON now:"""

        try:
            if self.provider == "google":
                # Use Gemini with structured output
                cleaned_schema = self._clean_schema_for_gemini(schema)

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[extraction_prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=cleaned_schema,
                        system_instruction=[
                            types.Part.from_text(
                                text="""You are an expert data extraction system.
Extract structured data from markdown documents accurately according to the JSON schema.
Process all pages and combine information intelligently into a single coherent JSON object."""
                            )
                        ],
                    ),
                )

                # Parse JSON response
                extracted_data = json.loads(response.text)

                # Get token usage
                input_tokens = 0
                output_tokens = 0
                if hasattr(response, "usage_metadata"):
                    input_tokens = response.usage_metadata.prompt_token_count
                    output_tokens = response.usage_metadata.candidates_token_count

            elif self.provider == "openai":
                # Use OpenAI with JSON mode
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": """You are an expert data extraction system.
Extract structured data from markdown documents accurately according to the JSON schema.
Process all pages and combine information intelligently into a single coherent JSON object.
Return ONLY valid JSON, no explanations or markdown code blocks.""",
                        },
                        {"role": "user", "content": extraction_prompt},
                    ],
                    response_format={"type": "json_object"},
                )

                # Parse JSON response
                content = response.choices[0].message.content

                # Strip markdown code blocks if present (shouldn't happen with json_object mode)
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                extracted_data = json.loads(content)

                # Get token usage
                input_tokens = response.usage.prompt_tokens if response.usage else 0
                output_tokens = (
                    response.usage.completion_tokens if response.usage else 0
                )

            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            # Validate extracted data against schema
            is_valid, validation_errors = self.validator.validate(extracted_data, schema)

            processing_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Extracted JSON from markdown "
                f"(provider: {self.provider}, "
                f"tokens: {input_tokens}+{output_tokens}, "
                f"time: {processing_time_ms}ms, "
                f"valid: {is_valid})"
            )

            return MarkdownExtractionResult(
                extracted_data=extracted_data,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                processing_time_ms=processing_time_ms,
                provider=self.provider,
                model=self.model,
                is_valid=is_valid,
                validation_errors=validation_errors,
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError(f"Failed to parse JSON response: {e}")
        except Exception as e:
            logger.error(f"Markdown-to-JSON extraction failed: {e}")
            raise Exception(f"Markdown-to-JSON extraction error: {e}")
