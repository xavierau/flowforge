"""Gemini vision-based markdown converter implementation.

Uses Google Gemini 2.5 Flash vision model to convert document images to markdown.
Supports both single-page and multi-page batch conversion.
"""

import asyncio
import base64
import time
from typing import List
import logging

from google import genai
from google.genai import types

from app.services.converters.base import (
    IImageToMarkdownConverter,
    MarkdownConversionResult,
)

logger = logging.getLogger(__name__)


class GeminiMarkdownConverter(IImageToMarkdownConverter):
    """Gemini vision-based markdown converter.

    Uses Google Gemini 3 Flash vision model for high-quality markdown conversion.
    Configured with extended timeouts to handle large preprocessed images.
    """

    def __init__(self, api_key: str, model: str = "gemini-3-flash-preview"):
        """Initialize Gemini converter with timeout configuration.

        Args:
            api_key: Google API key
            model: Model name (default: gemini-3-flash-preview)
        """
        import httpx

        # Configure extended timeouts for large image processing
        # Preprocessed RGBA images can be 2-3MB per page
        # Batch mode may send multiple pages at once
        timeout_config = httpx.Timeout(
            connect=30.0,  # Connection: 30 seconds
            read=300.0,  # Reading response: 5 minutes
            write=300.0,  # Writing request: 5 minutes (large uploads)
            pool=30.0,  # Pool: 30 seconds
        )

        http_options = types.HttpOptions(
            client_args={"timeout": timeout_config},
            async_client_args={"timeout": timeout_config},
        )

        self.client = genai.Client(api_key=api_key, http_options=http_options)
        self.model = model
        self.provider = "gemini_vision"

    def _build_conversion_prompt(
        self, format_style: str, page_number: int = 1, is_batch: bool = False
    ) -> str:
        """Build conversion prompt based on format style.

        Args:
            format_style: Markdown format style (standard, table_heavy, layout_preserved)
            page_number: Page number for marker (single page only)
            is_batch: Whether this is a batch conversion

        Returns:
            Formatted conversion prompt
        """
        # Base requirements common to all formats
        base_requirements = """Convert this document image to markdown format.

CRITICAL REQUIREMENTS:
1. Preserve exact layout and structure
2. Include all text content exactly as shown
3. Use proper markdown syntax
4. Maintain document hierarchy with headers"""

        # Format-specific instructions
        if format_style == "table_heavy":
            format_specific = """
5. Convert ALL tabular data to markdown tables
6. Use markdown tables for any structured data
7. Ensure proper column alignment (use |---|---|)
8. Preserve header rows in tables
9. Include all cells and values accurately

FOCUS ON TABLES:
- Prioritize converting tables to proper markdown format
- Use | (pipe) for column separators
- Use | --- | for header separators
- Align columns properly for readability"""

        elif format_style == "layout_preserved":
            format_specific = """
5. Preserve the exact visual layout of the document
6. Use spacing and indentation to match original
7. Maintain alignment of elements
8. Preserve visual groupings and sections
9. Use markdown features to replicate layout structure

FOCUS ON LAYOUT:
- Keep text alignment as close to original as possible
- Preserve visual spacing between sections
- Maintain the document's visual hierarchy"""

        else:  # standard
            format_specific = """
5. Use standard markdown formatting for headers, lists, emphasis
6. Convert tables to markdown tables where appropriate
7. Maintain clear section separation
8. Use proper list formatting (numbered/bulleted)

FOCUS ON READABILITY:
- Clean, standard markdown formatting
- Clear hierarchy with headers
- Proper list and table formatting"""

        # Page marker instruction
        if is_batch:
            marker_instruction = """
Insert page markers in the format: <!-- PAGE N -->
- Place marker at the START of each page's content
- Page numbers start from 1 and increment sequentially
- This helps identify which page each section came from"""
        else:
            marker_instruction = (
                f"\nInsert this marker at the START: <!-- PAGE {page_number} -->"
            )

        return f"{base_requirements}\n{format_specific}\n{marker_instruction}"

    async def convert_single(
        self,
        image_base64: str,
        format_style: str = "standard",
        page_number: int = 1,
    ) -> MarkdownConversionResult:
        """Convert a single image to markdown.

        Args:
            image_base64: Base64 encoded image
            format_style: Markdown format style
            page_number: Page number for marker

        Returns:
            MarkdownConversionResult with generated markdown

        Raises:
            Exception: If conversion fails
        """
        start_time = time.time()

        try:
            # Decode image and convert to PIL
            import PIL.Image
            import io

            image_data = base64.b64decode(image_base64)
            image_pil = PIL.Image.open(io.BytesIO(image_data))

            # Build conversion prompt
            prompt = self._build_conversion_prompt(
                format_style=format_style, page_number=page_number, is_batch=False
            )

            # Generate markdown using Gemini
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt, image_pil],
                config=types.GenerateContentConfig(
                    system_instruction=[
                        types.Part.from_text(
                            text="""You are an expert document-to-markdown converter.
Convert document images to high-quality markdown with perfect accuracy.
Preserve all information, structure, and formatting from the original document.
Pay special attention to tables, lists, and hierarchical structure."""
                        )
                    ],
                ),
            )

            # Extract markdown from response
            markdown_content = response.text

            # Get token usage
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, "usage_metadata"):
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count

            processing_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Converted page {page_number} to markdown "
                f"(tokens: {input_tokens}+{output_tokens}, "
                f"time: {processing_time_ms}ms)"
            )

            # Log the markdown output for debugging
            logger.debug(
                f"Page {page_number} markdown output:\n"
                f"{'=' * 80}\n"
                f"{markdown_content}\n"
                f"{'=' * 80}"
            )

            return MarkdownConversionResult(
                markdown_content=markdown_content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                processing_time_ms=processing_time_ms,
                provider=self.provider,
                model=self.model,
            )

        except Exception as e:
            logger.error(
                f"Gemini markdown conversion failed: {type(e).__name__}: {e}",
                exc_info=True  # Include full stack trace
            )
            raise Exception(f"Gemini markdown conversion error: {type(e).__name__}: {e}")

    async def _convert_single_with_retry(
        self,
        image_base64: str,
        format_style: str,
        page_number: int,
        max_retries: int = 3,
    ) -> MarkdownConversionResult:
        """Convert a single page with exponential backoff retry strategy.

        Args:
            image_base64: Base64 encoded image
            format_style: Markdown format style
            page_number: Page number for marker
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            MarkdownConversionResult with generated markdown

        Raises:
            Exception: If all retries are exhausted
        """
        for attempt in range(max_retries):
            try:
                return await self.convert_single(
                    image_base64=image_base64,
                    format_style=format_style,
                    page_number=page_number,
                )
            except Exception as e:
                error_msg = str(e)
                is_rate_limit = "503" in error_msg or "overloaded" in error_msg.lower()

                if attempt < max_retries - 1:
                    # Calculate exponential backoff: 5 * (2^attempt) seconds
                    # This gives: 5s, 10s, 20s for attempts 1, 2, 3
                    delay = 5 * (2 ** attempt)
                    logger.warning(
                        f"Page {page_number} conversion failed (attempt {attempt + 1}/{max_retries}): {error_msg}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    # Final attempt failed
                    logger.error(
                        f"Page {page_number} conversion failed after {max_retries} attempts: {error_msg}"
                    )
                    raise

    async def convert_batch(
        self,
        images_base64: List[str],
        format_style: str = "standard",
    ) -> MarkdownConversionResult:
        """Convert multiple images to markdown using parallel processing with retry.

        Each page is processed concurrently with its own API call for maximum speed.
        Individual page failures are retried with exponential backoff (1s, 2s, 4s).
        Results are combined into a single MarkdownConversionResult with per-page metrics.

        Args:
            images_base64: List of base64 encoded images (one per page)
            format_style: Markdown format style

        Returns:
            MarkdownConversionResult with:
                - Combined markdown with page markers
                - Aggregated token counts
                - Per-page breakdown in page_results field

        Raises:
            Exception: If conversion fails after all retries
        """
        start_time = time.time()

        try:
            # Create concurrent tasks for each page with retry wrapper
            tasks = [
                self._convert_single_with_retry(
                    image_base64=img_b64,
                    format_style=format_style,
                    page_number=page_num,
                    max_retries=3,
                )
                for page_num, img_b64 in enumerate(images_base64, start=1)
            ]

            # Execute all tasks in parallel using asyncio.gather
            logger.info(
                f"Starting parallel conversion of {len(images_base64)} pages with retry..."
            )
            results: List[MarkdownConversionResult] = await asyncio.gather(*tasks)

            # Combine markdown from all pages
            combined_markdown = "\n\n".join([r.markdown_content for r in results])

            # Aggregate token counts
            total_input_tokens = sum(r.input_tokens for r in results)
            total_output_tokens = sum(r.output_tokens for r in results)

            # Build per-page breakdown
            page_results = [
                {
                    "markdown": result.markdown_content,
                    "page": page_num,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                }
                for page_num, result in enumerate(results, start=1)
            ]

            # Log per-page markdown outputs
            for page_num, result in enumerate(results, start=1):
                logger.debug(
                    f"Batch Page {page_num} markdown output:\n"
                    f"{'=' * 80}\n"
                    f"{result.markdown_content}\n"
                    f"{'=' * 80}\n"
                    f"Tokens: {result.input_tokens} input + {result.output_tokens} output"
                )

            processing_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Parallel batch converted {len(images_base64)} pages to markdown "
                f"(total tokens: {total_input_tokens}+{total_output_tokens}, "
                f"time: {processing_time_ms}ms, "
                f"avg per page: {processing_time_ms // len(images_base64)}ms)"
            )

            return MarkdownConversionResult(
                markdown_content=combined_markdown,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                processing_time_ms=processing_time_ms,
                provider=self.provider,
                model=self.model,
                page_results=page_results,
            )

        except Exception as e:
            logger.error(
                f"Gemini parallel batch markdown conversion failed: {type(e).__name__}: {e}",
                exc_info=True  # Include full stack trace
            )
            raise Exception(f"Gemini parallel batch markdown conversion error: {type(e).__name__}: {e}")
