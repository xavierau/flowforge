"""Converters package for markdown extraction pipeline.

This package provides interfaces and implementations for the markdown
extraction pipeline:
1. Image -> Markdown conversion (using vision models)
2. Document -> Markdown conversion (using LlamaParse, etc.)
3. Markdown -> JSON extraction (using text models)
"""

from app.services.converters.base import (
    IImageToMarkdownConverter,
    IDocumentToMarkdownConverter,
    IMarkdownToJsonExtractor,
    MarkdownConversionResult,
    MarkdownExtractionResult,
    DocumentConversionResult,
    PageMarkdown,
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
    "IDocumentToMarkdownConverter",
    "IMarkdownToJsonExtractor",
    # Result types
    "MarkdownConversionResult",
    "MarkdownExtractionResult",
    "DocumentConversionResult",
    "PageMarkdown",
    # Implementations
    "GeminiMarkdownConverter",
    "GPT4VMarkdownConverter",
    "MarkdownJsonExtractor",
    # Factory
    "ConverterFactory",
    "get_converter_factory",
]
