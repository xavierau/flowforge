"""VLLM service for document understanding using Vision Language Models."""

import base64
import json
import time
from typing import Any, Optional
from abc import ABC, abstractmethod

try:
    import dspy
except ImportError:
    dspy = None

from openai import OpenAI
from google import genai
from google.genai import types

from app.config import settings
from app.services.schema_validator import SchemaValidator


class VLLMProvider(ABC):
    """Abstract base class for VLLM providers."""

    @abstractmethod
    async def extract(
        self,
        image_base64: str,
        schema: dict[str, Any],
        prompt: str,
    ) -> tuple[dict[str, Any], int, int, int]:
        """
        Extract structured data from image.

        Args:
            image_base64: Base64 encoded image
            schema: JSON schema for extraction
            prompt: Custom extraction prompt

        Returns:
            Tuple of (extracted_data, input_tokens, output_tokens, processing_time_ms)
        """
        pass

    @abstractmethod
    async def extract_batch(
        self,
        images_base64: list[str],
        schema: dict[str, Any],
        prompt: str,
    ) -> tuple[dict[str, Any], int, int, int]:
        """
        Extract structured data from multiple images in one call.

        Args:
            images_base64: List of base64 encoded images
            schema: JSON schema for extraction
            prompt: Custom extraction prompt

        Returns:
            Tuple of (extracted_data, input_tokens, output_tokens, processing_time_ms)
        """
        pass


class OpenAIVLLMProvider(VLLMProvider):
    """OpenAI GPT-4 Vision provider."""

    def __init__(self, api_key: str, model: str = "gpt-4-vision-preview"):
        """Initialize OpenAI provider."""
        self.client = OpenAI(api_key=api_key)
        self.model = model

    async def extract(
        self,
        image_base64: str,
        schema: dict[str, Any],
        prompt: str,
    ) -> tuple[dict[str, Any], int, int, int]:
        """Extract using OpenAI GPT-4V."""
        start_time = time.time()

        # Build the system prompt
        system_prompt = f"""You are a document data extraction expert.
Extract information from the provided document image according to this JSON schema:

{json.dumps(schema, indent=2)}

Additional instructions: {prompt}

Return ONLY valid JSON matching the schema. Do not include any explanation."""

        try:
            # Make API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": system_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=4096,
            )

            # Extract response and token usage
            content = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0

            # Parse JSON response
            # Try to extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            extracted_data = json.loads(content)

            processing_time = int((time.time() - start_time) * 1000)

            return extracted_data, input_tokens, output_tokens, processing_time

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}")
        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")

    async def extract_batch(
        self,
        images_base64: list[str],
        schema: dict[str, Any],
        prompt: str,
    ) -> tuple[dict[str, Any], int, int, int]:
        """Extract using OpenAI GPT-4V with multiple images."""
        start_time = time.time()

        # Build the system prompt
        system_prompt = f"""You are a document data extraction expert.
Extract information from the provided multi-page document images according to this JSON schema:

{json.dumps(schema, indent=2)}

Additional instructions: {prompt}

IMPORTANT: The images represent pages of a single document. Combine all information across all pages into a single coherent JSON object.

Return ONLY valid JSON matching the schema. Do not include any explanation."""

        try:
            # Build content array with text prompt + all images
            content = [{"type": "text", "text": system_prompt}]

            for img_b64 in images_base64:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_b64}"}
                })

            # Make API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                max_tokens=4096,
            )

            # Extract response and token usage
            response_content = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0

            # Parse JSON response
            if "```json" in response_content:
                response_content = response_content.split("```json")[1].split("```")[0].strip()
            elif "```" in response_content:
                response_content = response_content.split("```")[1].split("```")[0].strip()

            extracted_data = json.loads(response_content)

            processing_time = int((time.time() - start_time) * 1000)

            return extracted_data, input_tokens, output_tokens, processing_time

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}")
        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")


class GeminiVLLMProvider(VLLMProvider):
    """Google Gemini Vision provider."""

    @staticmethod
    def _clean_schema_for_gemini(schema: dict[str, Any]) -> dict[str, Any]:
        """
        Clean JSON schema for Gemini API compatibility.

        Removes fields that are not permitted by the Gemini API:
        - $schema: JSON Schema version identifier
        - $id: Schema identifier
        - Other $ prefixed metadata fields

        Args:
            schema: Input JSON schema

        Returns:
            Cleaned schema without metadata fields
        """
        if not isinstance(schema, dict):
            return schema

        # Create a copy to avoid mutating the original
        cleaned = {}

        for key, value in schema.items():
            # Skip metadata fields that start with $
            if key.startswith('$'):
                continue

            # Recursively clean nested objects
            if isinstance(value, dict):
                cleaned[key] = GeminiVLLMProvider._clean_schema_for_gemini(value)
            elif isinstance(value, list):
                cleaned[key] = [
                    GeminiVLLMProvider._clean_schema_for_gemini(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                cleaned[key] = value

        return cleaned

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        """Initialize Gemini provider with timeout configuration."""
        # Configure client with longer timeout for large images
        # Default timeout is often too short for vision models processing large images
        import httpx
        from google.genai import types

        # Configure separate timeouts for different operations
        # Preprocessed RGBA images are large (~2-3MB per page)
        # Batch mode sends 4 pages at once (~8-12MB total)
        timeout_config = httpx.Timeout(
            connect=30.0,   # Connection establishment: 30 seconds
            read=300.0,     # Reading response: 5 minutes (for processing time)
            write=300.0,    # Writing request (upload): 5 minutes (for large images)
            pool=30.0       # Pool timeout: 30 seconds
        )

        # Pass timeout to underlying httpx client via client_args
        # Also configure async client with same timeout
        http_options = types.HttpOptions(
            client_args={'timeout': timeout_config},
            async_client_args={'timeout': timeout_config}
        )

        self.client = genai.Client(
            api_key=api_key,
            http_options=http_options
        )
        self.model = model

    async def extract(
        self,
        image_base64: str,
        schema: dict[str, Any],
        prompt: str,
        thinking_budget: int = 0,
    ) -> tuple[dict[str, Any], int, int]:
        """Extract using Google Gemini with structured output.

        Following Gemini API best practices:
        - Use response_mime_type='application/json' for JSON output
        - Pass schema via response_schema parameter, not in prompt
        - This guarantees syntactically valid JSON matching the schema

        Args:
            image_base64: Base64 encoded image
            schema: JSON schema for extraction
            prompt: Custom extraction instructions
            thinking_budget: Token budget for AI thinking (0=disabled, >0=enabled)
        """
        start_time = time.time()

        # Build the prompt focused on extraction instructions only
        # Schema is passed separately via config
        extraction_prompt = f"""Extract information from this document image.

Additional instructions: {prompt}

Extract all relevant information accurately from the document."""

        try:
            # Decode base64 image
            image_data = base64.b64decode(image_base64)

            # Generate content using new SDK with structured output
            # The SDK accepts PIL Image objects directly in contents
            import PIL.Image
            import io
            image_pil = PIL.Image.open(io.BytesIO(image_data))

            # Clean schema for Gemini API (remove $schema and other metadata fields)
            cleaned_schema = self._clean_schema_for_gemini(schema)

            # Use proper structured output configuration with system instruction
            response = self.client.models.generate_content(
                model=self.model,
                contents=[image_pil, extraction_prompt],
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    response_schema=cleaned_schema,
                    system_instruction=[
                        types.Part.from_text(
                            text="""You are the most advanced document data extraction system.
Extract data accurately from the provided document images according to the JSON schema.
Understand the holistic context of the document and make relevant decisions based on the document type and structure."""
                        )
                    ],
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=thinking_budget,
                    ),
                ),
            )

            # With structured output, response.text is guaranteed to be valid JSON
            # No need to strip markdown code blocks
            extracted_data = json.loads(response.text)

            # Get actual token usage from response metadata
            # Gemini provides: prompt_token_count, candidates_token_count, total_token_count
            if hasattr(response, 'usage_metadata'):
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count
            else:
                input_tokens = 0
                output_tokens = 0

            processing_time = int((time.time() - start_time) * 1000)

            return extracted_data, input_tokens, output_tokens, processing_time

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}")
        except Exception as e:
            raise Exception(f"Gemini API error: {e}")

    async def extract_batch(
        self,
        images_base64: list[str],
        schema: dict[str, Any],
        prompt: str,
        thinking_budget: int = 0,
    ) -> tuple[dict[str, Any], int, int, int]:
        """Extract using Google Gemini with multiple images in one call.

        Following Gemini API best practices:
        - Use response_mime_type='application/json' for JSON output
        - Pass schema via response_schema parameter, not in prompt
        - For multi-image document extraction, place the prompt FIRST
        - Then include all image parts in sequence
        - This guarantees syntactically valid JSON matching the schema

        Args:
            images_base64: List of base64 encoded images (one per page)
            schema: JSON schema for extraction
            prompt: Custom extraction instructions
            thinking_budget: Token budget for AI thinking (0=disabled, >0=enabled)
        """
        start_time = time.time()

        # Build the prompt focused on extraction instructions only
        # Schema is passed separately via config
        extraction_prompt = f"""Extract information from this multi-page document.

Additional instructions: {prompt}

IMPORTANT: These images represent pages of a SINGLE document. Combine all information across all pages into ONE coherent JSON object.
For example:
- If invoice header is on page 1 and totals are on page 3, include both in the same JSON
- If line items span multiple pages, combine them into a single array
- Do not create separate JSON objects for each page

Extract all relevant information accurately from all pages."""

        try:
            # Decode all images and convert to PIL
            import PIL.Image
            import io

            # Build contents list following Gemini best practices:
            # For multi-image comparison/extraction: [prompt, image1, image2, image3, ...]
            # This allows the model to understand the task before processing images
            contents = [extraction_prompt]

            for img_b64 in images_base64:
                image_data = base64.b64decode(img_b64)
                image_pil = PIL.Image.open(io.BytesIO(image_data))
                contents.append(image_pil)

            # Clean schema for Gemini API (remove $schema and other metadata fields)
            cleaned_schema = self._clean_schema_for_gemini(schema)

            # Make single API call with all images using structured output
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    response_schema=cleaned_schema,
                    system_instruction=[
                        types.Part.from_text(
                            text="""You are an advanced document data extraction system.
Extract data accurately from the provided multi-page document images according to the JSON schema.
Understand the holistic context of the document and make relevant decisions based on the document type and structure.
Combine information across all pages into a single coherent result."""
                        )
                    ],
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=thinking_budget,
                    ),
                ),
            )

            # With structured output, response.text is guaranteed to be valid JSON
            # No need to strip markdown code blocks
            extracted_data = json.loads(response.text)

            # Get actual token usage from response metadata
            if hasattr(response, 'usage_metadata'):
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count
            else:
                input_tokens = 0
                output_tokens = 0

            processing_time = int((time.time() - start_time) * 1000)

            return extracted_data, input_tokens, output_tokens, processing_time

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}")
        except Exception as e:
            raise Exception(f"Gemini API error: {e}")


class VLLMService:
    """High-level VLLM service for document extraction."""

    def __init__(self):
        """Initialize VLLM service with configured providers."""
        self.providers: dict[str, VLLMProvider] = {}
        self.validator = SchemaValidator()

        # Initialize OpenAI if configured
        if settings.openai_api_key:
            self.providers["openai"] = OpenAIVLLMProvider(
                api_key=settings.openai_api_key,
                model="gpt-4-vision-preview",
            )

        # Initialize Gemini if configured
        if settings.google_api_key:
            self.providers["google"] = GeminiVLLMProvider(
                api_key=settings.google_api_key,
                model="gemini-2.5-flash",
            )

    def get_provider(self, provider_name: str) -> VLLMProvider:
        """
        Get a VLLM provider by name.

        Args:
            provider_name: Provider name ('openai' or 'google')

        Returns:
            VLLMProvider instance

        Raises:
            ValueError: If provider not configured
        """
        if provider_name not in self.providers:
            raise ValueError(
                f"Provider '{provider_name}' not configured. "
                f"Available: {list(self.providers.keys())}"
            )
        return self.providers[provider_name]

    async def extract_from_image(
        self,
        image_base64: str,
        schema: dict[str, Any],
        custom_prompt: str = "",
        provider: str = "google",
        model: str = "gemini-pro-vision",
        thinking_budget: int = 0,
    ) -> dict[str, Any]:
        """
        Extract structured data from an image.

        Args:
            image_base64: Base64 encoded image
            schema: JSON schema for extraction
            custom_prompt: Custom extraction instructions
            provider: VLLM provider ('google' or 'openai')
            model: Model name
            thinking_budget: Token budget for AI thinking (0=disabled, >0=enabled)

        Returns:
            Dictionary with extraction results:
            {
                "extracted_data": {...},
                "is_valid": bool,
                "validation_errors": [...],
                "confidence_score": float,
                "input_tokens": int,
                "output_tokens": int,
                "tokens_used": int,  # total tokens (input + output)
                "processing_time_ms": int,
                "model_used": str
            }
        """
        # Validate schema
        if not self.validator.is_valid_schema(schema):
            raise ValueError("Invalid JSON schema provided")

        # Get provider
        vllm_provider = self.get_provider(provider)

        # Extract data
        extracted_data, input_tokens, output_tokens, processing_time_ms = await vllm_provider.extract(
            image_base64=image_base64,
            schema=schema,
            prompt=custom_prompt,
            thinking_budget=thinking_budget,
        )

        # Validate extracted data against schema
        is_valid, validation_errors = self.validator.validate(extracted_data, schema)

        # Calculate confidence score based on schema coverage and data completeness
        confidence_score = self._calculate_confidence_score(
            extracted_data=extracted_data,
            schema=schema,
            is_valid=is_valid
        )

        return {
            "extracted_data": extracted_data,
            "is_valid": is_valid,
            "validation_errors": validation_errors,
            "confidence_score": confidence_score,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "tokens_used": input_tokens + output_tokens,  # total
            "processing_time_ms": processing_time_ms,
            "model_used": f"{provider}/{model}",
        }

    async def extract_from_images_batch(
        self,
        images_base64: list[str],
        schema: dict[str, Any],
        custom_prompt: str = "",
        provider: str = "google",
        model: str = "gemini-2.5-flash",
        thinking_budget: int = 0,
    ) -> dict[str, Any]:
        """
        Extract structured data from multiple images in a single API call.

        This is for multi-page documents where all pages belong to the same document.
        The VLLM will see all images and combine information across pages.

        Args:
            images_base64: List of base64 encoded images (pages of the same document)
            schema: JSON schema for extraction
            custom_prompt: Custom extraction instructions
            provider: VLLM provider ('google' or 'openai')
            model: Model name
            thinking_budget: Token budget for AI thinking (0=disabled, >0=enabled)

        Returns:
            Dictionary with extraction results (same format as extract_from_image)
        """
        # Validate schema
        if not self.validator.is_valid_schema(schema):
            raise ValueError("Invalid JSON schema provided")

        # Get provider
        vllm_provider = self.get_provider(provider)

        # Extract data from all images in one call
        extracted_data, input_tokens, output_tokens, processing_time_ms = await vllm_provider.extract_batch(
            images_base64=images_base64,
            schema=schema,
            prompt=custom_prompt,
            thinking_budget=thinking_budget,
        )

        # Validate extracted data against schema
        is_valid, validation_errors = self.validator.validate(extracted_data, schema)

        # Calculate confidence score based on schema coverage and data completeness
        confidence_score = self._calculate_confidence_score(
            extracted_data=extracted_data,
            schema=schema,
            is_valid=is_valid
        )

        return {
            "extracted_data": extracted_data,
            "is_valid": is_valid,
            "validation_errors": validation_errors,
            "confidence_score": confidence_score,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "tokens_used": input_tokens + output_tokens,
            "processing_time_ms": processing_time_ms,
            "model_used": f"{provider}/{model}",
        }

    def _calculate_confidence_score(
        self,
        extracted_data: dict[str, Any],
        schema: dict[str, Any],
        is_valid: bool
    ) -> float:
        """
        Calculate confidence score for extraction based on multiple factors.

        Factors:
        1. Schema validity: Does the data pass schema validation?
        2. Schema coverage: What percentage of required fields are present?
        3. Data completeness: What percentage of fields have non-null/non-empty values?

        The final score is a weighted average of these factors.

        Args:
            extracted_data: Extracted JSON data
            schema: JSON schema
            is_valid: Whether data passed schema validation

        Returns:
            Confidence score between 0.0 and 1.0
        """
        scores = []
        weights = []

        # Factor 1: Schema validity (weight: 0.3)
        # If invalid, heavily penalize the score
        validity_score = 1.0 if is_valid else 0.3
        scores.append(validity_score)
        weights.append(0.3)

        # Factor 2: Required fields coverage (weight: 0.4)
        coverage_score = self._calculate_coverage_score(extracted_data, schema)
        scores.append(coverage_score)
        weights.append(0.4)

        # Factor 3: Data completeness (weight: 0.3)
        completeness_score = self._calculate_completeness_score(extracted_data, schema)
        scores.append(completeness_score)
        weights.append(0.3)

        # Weighted average
        total_weight = sum(weights)
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        final_score = weighted_sum / total_weight if total_weight > 0 else 0.5

        return round(final_score, 3)

    def _calculate_coverage_score(
        self,
        extracted_data: dict[str, Any],
        schema: dict[str, Any]
    ) -> float:
        """
        Calculate what percentage of required fields are present in the extracted data.

        Args:
            extracted_data: Extracted data
            schema: JSON schema with 'required' field

        Returns:
            Coverage score between 0.0 and 1.0
        """
        required_fields = schema.get("required", [])
        if not required_fields:
            # If no required fields specified, check top-level properties
            properties = schema.get("properties", {})
            if not properties:
                return 1.0  # No fields to check
            required_fields = list(properties.keys())

        if not required_fields:
            return 1.0

        present_count = 0
        for field in required_fields:
            if field in extracted_data and extracted_data[field] is not None:
                present_count += 1

        return present_count / len(required_fields)

    def _calculate_completeness_score(
        self,
        extracted_data: dict[str, Any],
        schema: dict[str, Any]
    ) -> float:
        """
        Calculate what percentage of fields have meaningful (non-null/non-empty) values.

        Args:
            extracted_data: Extracted data
            schema: JSON schema

        Returns:
            Completeness score between 0.0 and 1.0
        """
        properties = schema.get("properties", {})
        if not properties:
            # Use actual extracted data keys if no schema properties
            if not extracted_data:
                return 0.5
            properties = {k: {} for k in extracted_data.keys()}

        if not properties:
            return 1.0

        total_fields = len(properties)
        non_empty_count = 0

        for field in properties.keys():
            value = extracted_data.get(field)
            if self._is_value_meaningful(value):
                non_empty_count += 1

        return non_empty_count / total_fields if total_fields > 0 else 1.0

    def _is_value_meaningful(self, value: Any) -> bool:
        """
        Check if a value is meaningful (non-null, non-empty).

        Args:
            value: Value to check

        Returns:
            True if value is meaningful
        """
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
        if isinstance(value, (list, dict)) and len(value) == 0:
            return False
        return True


def get_vllm_service() -> VLLMService:
    """
    Get VLLM service instance.

    Returns:
        VLLMService instance
    """
    return VLLMService()
