"""Converter factory for managing markdown pipeline converters.

Provides centralized access to converter instances with dependency injection
based on available API keys from application settings.
"""

from typing import Dict, List, Optional
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


class ConverterFactory:
    """Factory for creating and managing converter instances.

    Implements singleton pattern to ensure only one factory instance exists.
    Automatically registers converters based on available API keys.
    """

    def __init__(self):
        """Initialize factory and register available converters."""
        self._markdown_converters: Dict[str, IImageToMarkdownConverter] = {}
        self._json_extractors: Dict[str, IMarkdownToJsonExtractor] = {}
        self._register_converters()

    def _register_converters(self) -> None:
        """Register converters based on available API keys from settings.

        Markdown Converters:
        - gemini_vision: Requires GOOGLE_API_KEY
        - gpt4v: Requires OPENAI_API_KEY
        - qwen_vision: Requires DASHSCOPE_API_KEY

        JSON Extractors:
        - gemini: Requires GOOGLE_API_KEY (uses Gemini 2.0 Flash text model)
        - openai: Requires OPENAI_API_KEY (uses GPT-4o-mini text model)
        """
        # Register markdown converters (vision models)
        if settings.google_api_key:
            try:
                self._markdown_converters["gemini_vision"] = GeminiMarkdownConverter(
                    api_key=settings.google_api_key, model="gemini-2.5-flash"
                )
                logger.info("Registered Gemini vision markdown converter")
            except Exception as e:
                logger.error(f"Failed to register Gemini markdown converter: {e}")

        if settings.openai_api_key:
            try:
                self._markdown_converters["gpt4v"] = GPT4VMarkdownConverter(
                    api_key=settings.openai_api_key, model="gpt-4-vision-preview"
                )
                logger.info("Registered GPT-4V markdown converter")
            except Exception as e:
                logger.error(f"Failed to register GPT-4V markdown converter: {e}")

        if settings.dashscope_api_key:
            try:
                self._markdown_converters["qwen_vision"] = QwenMarkdownConverter(
                    api_key=settings.dashscope_api_key, model="qwen3-vl-8b-instruct"
                )
                logger.info("Registered Qwen vision markdown converter")
            except Exception as e:
                logger.error(f"Failed to register Qwen markdown converter: {e}")

        # Register JSON extractors (text models)
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
            f"{len(self._markdown_converters)} markdown converters, "
            f"{len(self._json_extractors)} JSON extractors"
        )

    def get_markdown_converter(self, name: str) -> IImageToMarkdownConverter:
        """Get a markdown converter by name.

        Args:
            name: Converter name (gemini_vision, gpt4v, or qwen_vision)

        Returns:
            IImageToMarkdownConverter instance

        Raises:
            ValueError: If converter not available or not configured
        """
        if name not in self._markdown_converters:
            available = list(self._markdown_converters.keys())
            raise ValueError(
                f"Markdown converter '{name}' not available. "
                f"Available: {available}. "
                f"Check API keys in settings."
            )
        return self._markdown_converters[name]

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
            "markdown_converters": list(self._markdown_converters.keys()),
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
