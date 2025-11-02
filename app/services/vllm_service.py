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

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        """Initialize Gemini provider."""
        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def extract(
        self,
        image_base64: str,
        schema: dict[str, Any],
        prompt: str,
    ) -> tuple[dict[str, Any], int, int]:
        """Extract using Google Gemini."""
        start_time = time.time()

        # Build the prompt
        full_prompt = f"""Extract information from this document image according to this JSON schema:

{json.dumps(schema, indent=2)}

Additional instructions: {prompt}

Return ONLY valid JSON matching the schema. Do not include any explanation or markdown formatting."""

        try:
            # Decode base64 image
            image_data = base64.b64decode(image_base64)

            # Generate content using new SDK
            # The SDK accepts PIL Image objects directly in contents
            import PIL.Image
            import io
            image_pil = PIL.Image.open(io.BytesIO(image_data))

            response = self.client.models.generate_content(
                model=self.model,
                contents=[image_pil, full_prompt],
            )

            # Extract text
            content = response.text

            # Try to extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            extracted_data = json.loads(content)

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
    ) -> tuple[dict[str, Any], int, int, int]:
        """Extract using Google Gemini with multiple images in one call."""
        start_time = time.time()

        # Build the prompt
        full_prompt = f"""Extract information from this multi-page document according to this JSON schema:

{json.dumps(schema, indent=2)}

Additional instructions: {prompt}

IMPORTANT: These images represent pages of a SINGLE document. Combine all information across all pages into ONE coherent JSON object.
For example:
- If invoice header is on page 1 and totals are on page 3, include both in the same JSON
- If line items span multiple pages, combine them into a single array
- Do not create separate JSON objects for each page

Return ONLY valid JSON matching the schema. Do not include any explanation or markdown formatting."""

        try:
            # Decode all images and convert to PIL
            import PIL.Image
            import io

            # Build contents list: [image1, image2, image3, ..., prompt]
            contents = []

            for img_b64 in images_base64:
                image_data = base64.b64decode(img_b64)
                image_pil = PIL.Image.open(io.BytesIO(image_data))
                contents.append(image_pil)

            # Add prompt at the end
            contents.append(full_prompt)

            # Make single API call with all images
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
            )

            # Extract text
            content = response.text

            # Try to extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            extracted_data = json.loads(content)

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
    ) -> dict[str, Any]:
        """
        Extract structured data from an image.

        Args:
            image_base64: Base64 encoded image
            schema: JSON schema for extraction
            custom_prompt: Custom extraction instructions
            provider: VLLM provider ('google' or 'openai')
            model: Model name

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
        )

        # Validate extracted data against schema
        is_valid, validation_errors = self.validator.validate(extracted_data, schema)

        # Calculate confidence score (simplified)
        # In production, this could be based on VLLM response confidence
        confidence_score = 1.0 if is_valid else 0.5

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
        )

        # Validate extracted data against schema
        is_valid, validation_errors = self.validator.validate(extracted_data, schema)

        # Calculate confidence score
        confidence_score = 1.0 if is_valid else 0.5

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


def get_vllm_service() -> VLLMService:
    """
    Get VLLM service instance.

    Returns:
        VLLMService instance
    """
    return VLLMService()
