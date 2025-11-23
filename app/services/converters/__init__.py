"""Converters package for markdown extraction pipeline.

This package provides interfaces and implementations for the two-stage
markdown extraction pipeline:
1. Image → Markdown conversion (using vision models)
2. Markdown → JSON extraction (using text models)
"""

from app.services.converters.base import (
    IImageToMarkdownConverter,
    IMarkdownToJsonExtractor,
    MarkdownConversionResult,
    MarkdownExtractionResult,
)
from app.services.converters.gemini_markdown_converter import GeminiMarkdownConverter
from app.services.converters.gpt4v_markdown_converter import GPT4VMarkdownConverter
from app.services.converters.markdown_json_extractor import MarkdownJsonExtractor
from app.services.converters.converter_factory import (
    ConverterFactory,
    get_converter_factory,
)

__all__ = [
    # Base interfaces
    "IImageToMarkdownConverter",
    "IMarkdownToJsonExtractor",
    "MarkdownConversionResult",
    "MarkdownExtractionResult",
    # Implementations
    "GeminiMarkdownConverter",
    "GPT4VMarkdownConverter",
    "MarkdownJsonExtractor",
    # Factory
    "ConverterFactory",
    "get_converter_factory",
]
