"""
LLM Worker for Conductor Tasks.

Executes general-purpose LLM prompt/response using existing VLLM providers.
Supports both Google (Gemini) and OpenAI providers for text generation.

Unlike ExtractionWorker which uses vision models for document images,
LLMWorker is for general text-based LLM completions within workflows.
"""

import json
import time
from typing import Any, Dict, Optional

from openai import OpenAI
from google import genai
from google.genai import types

from .base_worker import BaseWorker
from app.config import settings


class LLMWorker(BaseWorker):
    """
    Worker that executes general-purpose LLM completions.

    Uses the same provider infrastructure as VLLMService but for
    text-only prompts (no vision/images).

    Input Parameters:
    - provider: "google" or "openai" (default: "google")
    - model: Model name (default based on provider)
      - Google: "gemini-2.5-flash", "gemini-2.5-pro"
      - OpenAI: "gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"
    - prompt: The prompt text (required)
    - system_prompt: Optional system prompt for context
    - temperature: 0.0-2.0 (default: 0.7)
    - max_tokens: Maximum output tokens (default: 1024)
    - response_format: Optional "json" for JSON output mode

    Output:
    - response: LLM response text
    - input_tokens: Token count for input
    - output_tokens: Token count for output
    - model_used: Actual model used
    - processing_time_ms: Processing time in milliseconds
    """

    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 1024

    # Default models per provider
    DEFAULT_MODELS = {
        "google": "gemini-2.5-flash",
        "openai": "gpt-4o",
    }

    def __init__(self):
        super().__init__(task_definition_name="llm_completion", poll_interval=1000)

        # Initialize clients lazily
        self._openai_client: Optional[OpenAI] = None
        self._gemini_client: Optional[genai.Client] = None

    @property
    def openai_client(self) -> OpenAI:
        """Lazy initialization of OpenAI client."""
        if self._openai_client is None:
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            self._openai_client = OpenAI(api_key=settings.openai_api_key)
        return self._openai_client

    @property
    def gemini_client(self) -> genai.Client:
        """Lazy initialization of Gemini client."""
        if self._gemini_client is None:
            if not settings.google_api_key:
                raise ValueError("Google API key not configured")
            self._gemini_client = genai.Client(api_key=settings.google_api_key)
        return self._gemini_client

    def validate_input(self, task_input: Dict[str, Any]) -> Optional[str]:
        """Validate LLM task input parameters."""
        if "prompt" not in task_input:
            return "Missing required parameter: 'prompt'"

        prompt = task_input.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            return "Parameter 'prompt' must be a non-empty string"

        provider = task_input.get("provider", "google")
        if provider not in ["google", "openai"]:
            return f"Invalid provider: {provider}. Allowed: google, openai"

        # Validate provider API key availability
        if provider == "openai" and not settings.openai_api_key:
            return "OpenAI provider selected but OPENAI_API_KEY not configured"
        if provider == "google" and not settings.google_api_key:
            return "Google provider selected but GOOGLE_API_KEY not configured"

        temperature = task_input.get("temperature", self.DEFAULT_TEMPERATURE)
        if not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 2:
            return "Parameter 'temperature' must be a number between 0.0 and 2.0"

        max_tokens = task_input.get("max_tokens", self.DEFAULT_MAX_TOKENS)
        if not isinstance(max_tokens, int) or max_tokens < 1:
            return "Parameter 'max_tokens' must be a positive integer"

        return None

    def execute_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute LLM completion.

        Args:
            task_input: Contains provider, model, prompt, system_prompt,
                        temperature, max_tokens, response_format

        Returns:
            Dictionary with response, token counts, model used
        """
        provider = task_input.get("provider", "google")
        model = task_input.get("model", self.DEFAULT_MODELS.get(provider))
        prompt = task_input["prompt"]
        system_prompt = task_input.get("system_prompt", "")
        temperature = task_input.get("temperature", self.DEFAULT_TEMPERATURE)
        max_tokens = task_input.get("max_tokens", self.DEFAULT_MAX_TOKENS)
        response_format = task_input.get("response_format")

        self.log_info(f"Executing LLM completion with {provider}/{model}")

        start_time = time.time()

        if provider == "google":
            result = self._execute_gemini(
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )
        else:  # openai
            result = self._execute_openai(
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )

        processing_time_ms = int((time.time() - start_time) * 1000)
        result["processing_time_ms"] = processing_time_ms
        result["model_used"] = f"{provider}/{model}"

        self.log_info(
            f"LLM completion finished in {processing_time_ms}ms "
            f"(tokens: {result['input_tokens']} in, {result['output_tokens']} out)"
        )

        return result

    def _execute_gemini(
        self,
        model: str,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
        response_format: Optional[str],
    ) -> Dict[str, Any]:
        """
        Execute completion using Google Gemini.

        Args:
            model: Gemini model name
            prompt: User prompt
            system_prompt: System instruction
            temperature: Temperature setting
            max_tokens: Max output tokens
            response_format: "json" for JSON mode

        Returns:
            Dictionary with response and token counts
        """
        try:
            # Build configuration
            config_params = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }

            # Add system instruction if provided
            if system_prompt:
                config_params["system_instruction"] = [
                    types.Part.from_text(text=system_prompt)
                ]

            # Configure JSON mode if requested
            if response_format == "json":
                config_params["response_mime_type"] = "application/json"

            config = types.GenerateContentConfig(**config_params)

            # Generate content
            response = self.gemini_client.models.generate_content(
                model=model,
                contents=[prompt],
                config=config,
            )

            # Extract response text
            response_text = response.text

            # Parse JSON if in JSON mode
            if response_format == "json":
                try:
                    response_text = json.loads(response_text)
                except json.JSONDecodeError:
                    self.log_warning("Failed to parse JSON response, returning raw text")

            # Get token usage
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, "usage_metadata"):
                input_tokens = response.usage_metadata.prompt_token_count or 0
                output_tokens = response.usage_metadata.candidates_token_count or 0

            return {
                "response": response_text,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }

        except Exception as e:
            self.log_error(f"Gemini API error: {e}", exc_info=True)
            raise Exception(f"Gemini API error: {str(e)}")

    def _execute_openai(
        self,
        model: str,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
        response_format: Optional[str],
    ) -> Dict[str, Any]:
        """
        Execute completion using OpenAI.

        Args:
            model: OpenAI model name
            prompt: User prompt
            system_prompt: System instruction
            temperature: Temperature setting
            max_tokens: Max output tokens
            response_format: "json" for JSON mode

        Returns:
            Dictionary with response and token counts
        """
        try:
            # Build messages
            messages = []

            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })

            messages.append({
                "role": "user",
                "content": prompt
            })

            # Build completion parameters
            completion_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Configure JSON mode if requested
            if response_format == "json":
                completion_params["response_format"] = {"type": "json_object"}

            # Create completion
            response = self.openai_client.chat.completions.create(**completion_params)

            # Extract response
            response_text = response.choices[0].message.content

            # Parse JSON if in JSON mode
            if response_format == "json":
                try:
                    response_text = json.loads(response_text)
                except json.JSONDecodeError:
                    self.log_warning("Failed to parse JSON response, returning raw text")

            # Get token usage
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0

            return {
                "response": response_text,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }

        except Exception as e:
            self.log_error(f"OpenAI API error: {e}", exc_info=True)
            raise Exception(f"OpenAI API error: {str(e)}")
