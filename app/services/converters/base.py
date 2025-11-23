"""Base interfaces for markdown conversion pipeline.

This module defines abstract interfaces for the two-stage markdown extraction pipeline:
1. Image to Markdown conversion
2. Markdown to JSON extraction
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class MarkdownConversionResult:
    """Result from image-to-markdown conversion.

    Attributes:
        markdown_content: Generated markdown content
        input_tokens: Number of input tokens consumed (aggregated total)
        output_tokens: Number of output tokens generated (aggregated total)
        processing_time_ms: Processing time in milliseconds
        provider: Provider used (gemini_vision, gpt4v)
        model: Specific model used
        page_results: Optional per-page breakdown with individual metrics.
                     Each dict contains: {markdown: str, page: int, input_tokens: int, output_tokens: int}
    """

    markdown_content: str
    input_tokens: int
    output_tokens: int
    processing_time_ms: int
    provider: str
    model: str
    page_results: Optional[List[Dict[str, Any]]] = None


@dataclass
class MarkdownExtractionResult:
    """Result from markdown-to-JSON extraction.

    Attributes:
        extracted_data: Extracted structured data as dictionary
        input_tokens: Number of input tokens consumed
        output_tokens: Number of output tokens generated
        processing_time_ms: Processing time in milliseconds
        provider: Provider used (google, openai)
        model: Specific model used
        is_valid: Whether extracted data validates against schema
        validation_errors: List of validation errors if not valid
    """

    extracted_data: Dict[str, Any]
    input_tokens: int
    output_tokens: int
    processing_time_ms: int
    provider: str
    model: str
    is_valid: bool
    validation_errors: List[str]


class IImageToMarkdownConverter(ABC):
    """Abstract interface for image-to-markdown conversion.

    Implementations must support both single-image and batch conversion modes.
    """

    @abstractmethod
    async def convert_single(
        self,
        image_base64: str,
        format_style: str = "standard",
        page_number: int = 1,
    ) -> MarkdownConversionResult:
        """Convert a single image to markdown.

        Args:
            image_base64: Base64 encoded image
            format_style: Markdown format style (standard, table_heavy, layout_preserved)
            page_number: Page number for markdown marker

        Returns:
            MarkdownConversionResult with generated markdown and metadata

        Raises:
            ValueError: If conversion fails or produces invalid output
        """
        pass

    @abstractmethod
    async def convert_batch(
        self,
        images_base64: List[str],
        format_style: str = "standard",
    ) -> MarkdownConversionResult:
        """Convert multiple images to markdown in a single call.

        Args:
            images_base64: List of base64 encoded images (one per page)
            format_style: Markdown format style (standard, table_heavy, layout_preserved)

        Returns:
            MarkdownConversionResult with combined markdown and metadata.
            Markdown content includes page markers (<!-- PAGE N -->).

        Raises:
            ValueError: If conversion fails or produces invalid output
        """
        pass


class IMarkdownToJsonExtractor(ABC):
    """Abstract interface for markdown-to-JSON extraction.

    Extracts structured data from markdown content using text-only models.
    This is cheaper than vision models since it processes text instead of images.
    """

    @abstractmethod
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
            MarkdownExtractionResult with extracted data and metadata

        Raises:
            ValueError: If extraction fails or produces invalid JSON
        """
        pass
