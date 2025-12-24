"""Base interfaces for markdown conversion pipeline.

This module defines abstract interfaces for the markdown extraction pipeline:
1. Image to Markdown conversion (vision models)
2. Document to Markdown conversion (LlamaParse, etc.)
3. Markdown to JSON extraction (text models)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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


@dataclass
class PageMarkdown:
    """Markdown content for a single page.

    Attributes:
        page_number: 1-indexed page number
        markdown: Markdown content for this page
        raw_text: Optional raw text without markdown formatting
    """
    page_number: int
    markdown: str
    raw_text: Optional[str] = None


@dataclass
class DocumentConversionResult:
    """Result from document-to-markdown conversion.

    Used by document converters like LlamaParse that process entire documents
    (PDF, DOCX, etc.) directly rather than individual images.

    Attributes:
        markdown_content: Combined markdown content from all pages
        pages_processed: Actual number of pages processed (for billing)
        provider: Provider name (e.g., "llamaparse")
        model: Model/parser used (e.g., "llamaparse-v2")
        page_results: Per-page markdown content
        processing_time_seconds: Total processing time in seconds
        raw_response: Optional raw API response for debugging
        job_id: Optional provider job ID for tracking
    """
    markdown_content: str
    pages_processed: int
    provider: str
    model: str
    page_results: List[PageMarkdown] = field(default_factory=list)
    processing_time_seconds: float = 0.0
    raw_response: Optional[Dict[str, Any]] = None
    job_id: Optional[str] = None

    @property
    def processing_time_ms(self) -> int:
        """Get processing time in milliseconds for compatibility."""
        return int(self.processing_time_seconds * 1000)


class IDocumentToMarkdownConverter(ABC):
    """Abstract interface for document-to-markdown conversion.

    Unlike IImageToMarkdownConverter which processes individual images,
    this interface is for converters that process entire documents (PDF, DOCX, etc.)
    directly. Examples include LlamaParse, which uploads the original document
    and returns markdown without requiring image conversion.

    These converters typically:
    - Accept file paths or bytes rather than base64 images
    - Charge per page or per document rather than per token
    - Handle multi-page documents natively
    - May use async processing (upload, poll, retrieve)
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the provider name (e.g., 'llamaparse')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the model/parser name used."""
        pass

    @abstractmethod
    async def convert_document(
        self,
        document_path: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> DocumentConversionResult:
        """Convert a document file to markdown.

        Args:
            document_path: Path to the document file (PDF, DOCX, etc.)
            options: Optional conversion options (format style, language, etc.)

        Returns:
            DocumentConversionResult with markdown content and page count

        Raises:
            FileNotFoundError: If document file does not exist
            ValueError: If document format is not supported
            Exception: If conversion fails
        """
        pass

    @abstractmethod
    async def convert_document_bytes(
        self,
        document_bytes: bytes,
        filename: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> DocumentConversionResult:
        """Convert document bytes to markdown.

        Args:
            document_bytes: Raw document bytes
            filename: Original filename (used to determine format)
            options: Optional conversion options

        Returns:
            DocumentConversionResult with markdown content and page count

        Raises:
            ValueError: If document format is not supported
            Exception: If conversion fails
        """
        pass

    def supports_format(self, filename: str) -> bool:
        """Check if the converter supports the given file format.

        Default implementation checks common document formats.
        Subclasses can override for format-specific support.

        Args:
            filename: Filename to check

        Returns:
            True if format is supported, False otherwise
        """
        supported_extensions = {'.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls', '.html'}
        ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
        return f'.{ext}' in supported_extensions
