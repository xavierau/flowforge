"""Converter factory for managing markdown pipeline converters.

Provides centralized access to converter instances with dependency injection
based on available API keys from application settings.

Supports two types of converters:
1. Image-to-Markdown (vision models): Process individual page images
2. Document-to-Markdown (LlamaParse, etc.): Process entire documents directly
"""

from typing import Any, Dict, List, Optional, Set
import logging

from app.config import settings
from app.services.converters.base import (
    IImageToMarkdownConverter,
    IDocumentToMarkdownConverter,
    IMarkdownToJsonExtractor,
)
from app.services.converters.gemini_markdown_converter import GeminiMarkdownConverter
from app.services.converters.gpt4v_markdown_converter import GPT4VMarkdownConverter
from app.services.converters.qwen_markdown_converter import QwenMarkdownConverter
from app.services.converters.markdown_json_extractor import MarkdownJsonExtractor

logger = logging.getLogger(__name__)

# Global singleton instance
_factory_instance: Optional["ConverterFactory"] = None

# Valid image-to-markdown converter names
VALID_MARKDOWN_CONVERTERS = {"gemini_vision", "gpt4v", "qwen_vision"}

# Valid document-to-markdown converter names
VALID_DOCUMENT_CONVERTERS = {"llamaparse"}

# Fallback default models when DB lookup fails (loaded from settings)
def _get_fallback_default_models() -> Dict[str, str]:
    """Get fallback default models from settings.

    Returns a mapping of converter names to default model names.
    This allows default models to be configured via environment variables.
    """
    return {
        "gemini_vision": settings.default_gemini_vision_model,
        "gpt4v": settings.default_gpt4v_model,
        "qwen_vision": settings.default_qwen_vision_model,
    }

# Map converter names to providers
CONVERTER_TO_PROVIDER = {
    "gemini_vision": "google",
    "gpt4v": "openai",
    "qwen_vision": "qwen",
}

# Map document converter names to providers
DOCUMENT_CONVERTER_TO_PROVIDER = {
    "llamaparse": "llamaindex",
}


class ConverterFactory:
    """Factory for creating and managing converter instances.

    Implements singleton pattern to ensure only one factory instance exists.
    Tracks available providers based on API keys and creates converters on-demand.

    Supports two types of markdown converters:
    1. Image-to-Markdown: Vision models that process page images
    2. Document-to-Markdown: Services like LlamaParse that process documents directly
    """

    def __init__(self):
        """Initialize factory and register available providers."""
        self._available_markdown_converters: Set[str] = set()
        self._available_document_converters: Set[str] = set()
        self._json_extractors: Dict[str, IMarkdownToJsonExtractor] = {}
        self._register_converters()

    def _register_converters(self) -> None:
        """Register available providers based on API keys from settings.

        Tracks which markdown converters are available (based on API keys)
        but does NOT pre-create converter instances. Converters are created
        on-demand in get_markdown_converter() with the specified model.

        Image-to-Markdown Converters (on-demand):
        - gemini_vision: Requires GOOGLE_API_KEY
        - gpt4v: Requires OPENAI_API_KEY
        - qwen_vision: Requires DASHSCOPE_API_KEY

        Document-to-Markdown Converters (on-demand):
        - llamaparse: Requires LLAMAPARSE_API_KEY

        JSON Extractors (pre-created):
        - gemini: Requires GOOGLE_API_KEY (model configured via DEFAULT_GEMINI_JSON_MODEL env var)
        - openai: Requires OPENAI_API_KEY (model configured via DEFAULT_OPENAI_JSON_MODEL env var)
        """
        # Track available image-to-markdown converters (vision models) - created on-demand
        if settings.google_api_key:
            self._available_markdown_converters.add("gemini_vision")
            logger.info("Gemini vision markdown converter available")

        if settings.openai_api_key:
            self._available_markdown_converters.add("gpt4v")
            logger.info("GPT-4V markdown converter available")

        if settings.dashscope_api_key:
            self._available_markdown_converters.add("qwen_vision")
            logger.info("Qwen vision markdown converter available")

        # Track available document-to-markdown converters - created on-demand
        if settings.llamaparse_api_key:
            self._available_document_converters.add("llamaparse")
            logger.info("LlamaParse document converter available")

        # Register JSON extractors (text models) - pre-created with configured default models
        if settings.google_api_key:
            try:
                self._json_extractors["gemini"] = MarkdownJsonExtractor(
                    provider="google",
                    model=settings.default_gemini_json_model,
                    api_key=settings.google_api_key,
                )
                logger.info(f"Registered Gemini JSON extractor (model: {settings.default_gemini_json_model})")
            except Exception as e:
                logger.error(f"Failed to register Gemini JSON extractor: {e}")

        if settings.openai_api_key:
            try:
                self._json_extractors["openai"] = MarkdownJsonExtractor(
                    provider="openai",
                    model=settings.default_openai_json_model,
                    api_key=settings.openai_api_key,
                )
                logger.info(f"Registered OpenAI JSON extractor (model: {settings.default_openai_json_model})")
            except Exception as e:
                logger.error(f"Failed to register OpenAI JSON extractor: {e}")

        # Log registration summary
        logger.info(
            f"Converter factory initialized: "
            f"{len(self._available_markdown_converters)} image converters, "
            f"{len(self._available_document_converters)} document converters, "
            f"{len(self._json_extractors)} JSON extractors"
        )

    def _get_default_model_for_converter(self, converter_name: str) -> str:
        """Get default model for a converter from database or fallback.

        Queries the ModelPricing table to find the default markdown model
        for the given converter's provider. Falls back to configured defaults
        from settings if database lookup fails.

        Args:
            converter_name: Name of the converter (gemini_vision, gpt4v, qwen_vision)

        Returns:
            Model name string (e.g., "gemini-3-flash")
        """
        provider = CONVERTER_TO_PROVIDER.get(converter_name)
        fallback_models = _get_fallback_default_models()
        fallback = fallback_models.get(converter_name, settings.default_gemini_vision_model)

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

    def get_document_converter(
        self, name: str, options: Optional[Dict[str, Any]] = None
    ) -> IDocumentToMarkdownConverter:
        """Get a document-to-markdown converter by name.

        Document converters process entire documents (PDF, DOCX, etc.) directly
        rather than individual images. They typically charge per page or per document.

        Args:
            name: Converter name (currently only "llamaparse")
            options: Optional converter-specific options:
                - For llamaparse: num_workers, language, verbose, result_type

        Returns:
            IDocumentToMarkdownConverter instance

        Raises:
            ValueError: If converter not available or not configured
        """
        # Validate converter name
        if name not in VALID_DOCUMENT_CONVERTERS:
            raise ValueError(
                f"Unknown document converter '{name}'. "
                f"Valid options: {sorted(VALID_DOCUMENT_CONVERTERS)}"
            )

        # Check if API key is available
        if name not in self._available_document_converters:
            available = sorted(self._available_document_converters)
            raise ValueError(
                f"Document converter '{name}' not available. "
                f"Available: {available}. "
                f"Check API keys in settings."
            )

        options = options or {}

        # Create and return converter
        if name == "llamaparse":
            from app.services.converters.llamaparse_converter import LlamaParseConverter
            return LlamaParseConverter(
                api_key=settings.llamaparse_api_key,
                num_workers=options.get("num_workers", 4),
                language=options.get("language", "en"),
                verbose=options.get("verbose", False),
                result_type=options.get("result_type", "markdown"),
            )

        # Should not reach here, but handle gracefully
        raise ValueError(f"Document converter '{name}' is not implemented")

    def is_document_converter_available(self, name: str) -> bool:
        """Check if a document converter is available.

        Args:
            name: Converter name to check

        Returns:
            True if converter is available, False otherwise
        """
        return name in self._available_document_converters

    def list_available_converters(self) -> Dict[str, List[str]]:
        """List all available converters and extractors.

        Returns:
            Dictionary with lists of available converter names:
            {
                "markdown_converters": ["gemini_vision", "gpt4v"],
                "document_converters": ["llamaparse"],
                "json_extractors": ["gemini", "openai"]
            }
        """
        return {
            "markdown_converters": sorted(self._available_markdown_converters),
            "document_converters": sorted(self._available_document_converters),
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
