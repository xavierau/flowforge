"""Converter factory for managing markdown pipeline converters.

Provides centralized access to converter instances with dependency injection
based on available API keys from application settings.
"""

from typing import Dict, List, Optional, Set
import logging

from app.config import settings
from app.services.converters.base import (
    IImageToMarkdownConverter,
    IMarkdownToJsonExtractor,
)
from app.services.converters.gemini_markdown_converter import GeminiMarkdownConverter
from app.services.converters.gpt4v_markdown_converter import GPT4VMarkdownConverter
from app.services.converters.qwen_markdown_converter import QwenMarkdownConverter
from app.services.converters.markdown_json_extractor import MarkdownJsonExtractor

logger = logging.getLogger(__name__)

# Global singleton instance
_factory_instance: Optional["ConverterFactory"] = None

# Valid converter names
VALID_MARKDOWN_CONVERTERS = {"gemini_vision", "gpt4v", "qwen_vision"}

# Fallback default models when DB lookup fails
FALLBACK_DEFAULT_MODELS = {
    "gemini_vision": "gemini-2.5-flash",
    "gpt4v": "gpt-4-vision-preview",
    "qwen_vision": "qwen3-vl-8b-instruct",
}

# Map converter names to providers
CONVERTER_TO_PROVIDER = {
    "gemini_vision": "google",
    "gpt4v": "openai",
    "qwen_vision": "qwen",
}


class ConverterFactory:
    """Factory for creating and managing converter instances.

    Implements singleton pattern to ensure only one factory instance exists.
    Tracks available providers based on API keys and creates converters on-demand.
    """

    def __init__(self):
        """Initialize factory and register available providers."""
        self._available_markdown_converters: Set[str] = set()
        self._json_extractors: Dict[str, IMarkdownToJsonExtractor] = {}
        self._register_converters()

    def _register_converters(self) -> None:
        """Register available providers based on API keys from settings.

        Tracks which markdown converters are available (based on API keys)
        but does NOT pre-create converter instances. Converters are created
        on-demand in get_markdown_converter() with the specified model.

        Markdown Converters (on-demand):
        - gemini_vision: Requires GOOGLE_API_KEY
        - gpt4v: Requires OPENAI_API_KEY
        - qwen_vision: Requires DASHSCOPE_API_KEY

        JSON Extractors (pre-created):
        - gemini: Requires GOOGLE_API_KEY (uses Gemini 2.0 Flash text model)
        - openai: Requires OPENAI_API_KEY (uses GPT-4o-mini text model)
        """
        # Track available markdown converters (vision models) - created on-demand
        if settings.google_api_key:
            self._available_markdown_converters.add("gemini_vision")
            logger.info("Gemini vision markdown converter available")

        if settings.openai_api_key:
            self._available_markdown_converters.add("gpt4v")
            logger.info("GPT-4V markdown converter available")

        if settings.dashscope_api_key:
            self._available_markdown_converters.add("qwen_vision")
            logger.info("Qwen vision markdown converter available")

        # Register JSON extractors (text models) - pre-created with default models
        if settings.google_api_key:
            try:
                self._json_extractors["gemini"] = MarkdownJsonExtractor(
                    provider="google",
                    model="gemini-2.5-flash",
                    api_key=settings.google_api_key,
                )
                logger.info("Registered Gemini JSON extractor")
            except Exception as e:
                logger.error(f"Failed to register Gemini JSON extractor: {e}")

        if settings.openai_api_key:
            try:
                self._json_extractors["openai"] = MarkdownJsonExtractor(
                    provider="openai",
                    model="gpt-4o-mini",
                    api_key=settings.openai_api_key,
                )
                logger.info("Registered OpenAI JSON extractor")
            except Exception as e:
                logger.error(f"Failed to register OpenAI JSON extractor: {e}")

        # Log registration summary
        logger.info(
            f"Converter factory initialized: "
            f"{len(self._available_markdown_converters)} markdown converters available, "
            f"{len(self._json_extractors)} JSON extractors"
        )

    def _get_default_model_for_converter(self, converter_name: str) -> str:
        """Get default model for a converter from database or fallback.

        Queries the ModelPricing table to find the default markdown model
        for the given converter's provider. Falls back to hardcoded defaults
        if database lookup fails.

        Args:
            converter_name: Name of the converter (gemini_vision, gpt4v, qwen_vision)

        Returns:
            Model name string (e.g., "gemini-2.5-flash")
        """
        provider = CONVERTER_TO_PROVIDER.get(converter_name)
        fallback = FALLBACK_DEFAULT_MODELS.get(converter_name, "gemini-2.5-flash")

        if not provider:
            logger.warning(
                f"Unknown converter '{converter_name}', using fallback: {fallback}"
            )
            return fallback

        # Try to get default model from database
        try:
            from app.db.session import SessionLocal
            from app.models.model_pricing import ModelPricing

            db = SessionLocal()
            try:
                model = (
                    db.query(ModelPricing)
                    .filter(ModelPricing.is_active == True)
                    .filter(ModelPricing.provider == provider)
                    .filter(ModelPricing.supports_markdown_conversion == True)
                    .filter(ModelPricing.is_default_markdown == True)
                    .first()
                )
                if model:
                    logger.debug(
                        f"Using default model from DB for {converter_name}: {model.model_name}"
                    )
                    return model.model_name
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Failed to get default model from DB: {e}")

        logger.debug(f"Using fallback default for {converter_name}: {fallback}")
        return fallback

    def get_markdown_converter(
        self, name: str, model: Optional[str] = None
    ) -> IImageToMarkdownConverter:
        """Get a markdown converter by name with optional model override.

        Creates a new converter instance with the specified model, or looks up
        the default model from ModelPricing if not specified.

        Args:
            name: Converter name (gemini_vision, gpt4v, or qwen_vision)
            model: Optional model override. If None, uses default from ModelPricing.

        Returns:
            IImageToMarkdownConverter instance

        Raises:
            ValueError: If converter not available or not configured
        """
        # Validate converter name
        if name not in VALID_MARKDOWN_CONVERTERS:
            raise ValueError(
                f"Unknown markdown converter '{name}'. "
                f"Valid options: {sorted(VALID_MARKDOWN_CONVERTERS)}"
            )

        # Check if API key is available
        if name not in self._available_markdown_converters:
            available = sorted(self._available_markdown_converters)
            raise ValueError(
                f"Markdown converter '{name}' not available. "
                f"Available: {available}. "
                f"Check API keys in settings."
            )

        # Get effective model (passed param or lookup default)
        effective_model = model or self._get_default_model_for_converter(name)

        # Create and return converter
        if name == "gemini_vision":
            return GeminiMarkdownConverter(
                api_key=settings.google_api_key,
                model=effective_model,
            )
        elif name == "gpt4v":
            return GPT4VMarkdownConverter(
                api_key=settings.openai_api_key,
                model=effective_model,
            )
        elif name == "qwen_vision":
            return QwenMarkdownConverter(
                api_key=settings.dashscope_api_key,
                model=effective_model,
            )

    def get_json_extractor(self, name: str) -> IMarkdownToJsonExtractor:
        """Get a JSON extractor by name.

        Args:
            name: Extractor name (gemini or openai)

        Returns:
            IMarkdownToJsonExtractor instance

        Raises:
            ValueError: If extractor not available or not configured
        """
        if name not in self._json_extractors:
            available = list(self._json_extractors.keys())
            raise ValueError(
                f"JSON extractor '{name}' not available. "
                f"Available: {available}. "
                f"Check API keys in settings."
            )
        return self._json_extractors[name]

    def list_available_converters(self) -> Dict[str, List[str]]:
        """List all available converters and extractors.

        Returns:
            Dictionary with lists of available converter names:
            {
                "markdown_converters": ["gemini_vision", "gpt4v"],
                "json_extractors": ["gemini", "openai"]
            }
        """
        return {
            "markdown_converters": sorted(self._available_markdown_converters),
            "json_extractors": list(self._json_extractors.keys()),
        }


def get_converter_factory() -> ConverterFactory:
    """Get singleton converter factory instance.

    Returns:
        ConverterFactory singleton instance
    """
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = ConverterFactory()
    return _factory_instance
