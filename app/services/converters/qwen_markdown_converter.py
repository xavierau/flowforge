"""Qwen vision-based markdown converter implementation.

Uses Qwen3-VL-8B-Instruct via Dashscope API to convert document images to markdown.
Supports QwenVL special formats (markdown with coordinates, HTML with bbox) and standard markdown.
"""

import asyncio
import base64
import io
import time
from typing import List
import logging

import PIL.Image
from openai import AsyncOpenAI
import httpx

from app.services.converters.base import (
    IImageToMarkdownConverter,
    MarkdownConversionResult,
)

logger = logging.getLogger(__name__)


class QwenMarkdownConverter(IImageToMarkdownConverter):
    """Qwen vision-based markdown converter.

    Uses Qwen3-VL-8B-Instruct via Dashscope OpenAI-compatible API.
    Supports special QwenVL formats with positional information and standard markdown.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "qwen3-vl-8b-instruct",
        min_pixels: int = 512 * 32 * 32,
        max_pixels: int = 2048 * 32 * 32,
    ):
        """Initialize Qwen converter with timeout configuration.

        Args:
            api_key: Dashscope API key
            model: Model name (default: qwen3-vl-8b-instruct)
            min_pixels: Minimum pixel threshold for image processing
            max_pixels: Maximum pixel threshold for image processing
        """
        # Configure extended timeouts for large image processing
        timeout_config = httpx.Timeout(
            connect=30.0,  # Connection: 30 seconds
            read=300.0,  # Reading response: 5 minutes
            write=300.0,  # Writing request: 5 minutes (large uploads)
            pool=30.0,  # Pool: 30 seconds
        )

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            timeout=timeout_config,
        )
        self.model = model
        self.provider = "qwen_vision"
        self.min_pixels = min_pixels
        self.max_pixels = max_pixels

    def _detect_mime_type(self, image_base64: str) -> str:
        """Detect MIME type from base64 encoded image.

        Args:
            image_base64: Base64 encoded image

        Returns:
            MIME type string (e.g., "image/jpeg", "image/png")
        """
        try:
            image_data = base64.b64decode(image_base64)
            image_pil = PIL.Image.open(io.BytesIO(image_data))

            # Map PIL format to MIME type
            format_to_mime = {
                "JPEG": "image/jpeg",
                "PNG": "image/png",
                "WEBP": "image/webp",
                "GIF": "image/gif",
                "BMP": "image/bmp",
                "TIFF": "image/tiff",
            }

            mime_type = format_to_mime.get(image_pil.format, "image/jpeg")
            logger.debug(f"Detected MIME type: {mime_type} (PIL format: {image_pil.format})")
            return mime_type

        except Exception as e:
            logger.warning(f"Failed to detect MIME type, defaulting to image/jpeg: {e}")
            return "image/jpeg"

    def _build_conversion_prompt(
        self, format_style: str, page_number: int = 1, is_batch: bool = False
    ) -> str:
        """Build conversion prompt based on format style.

        Args:
            format_style: Markdown format style (qwenvl_markdown, qwenvl_html, standard)
            page_number: Page number for marker (single page only)
            is_batch: Whether this is a batch conversion

        Returns:
            Formatted conversion prompt
        """
        # QwenVL special formats use specific prompts
        if format_style == "qwenvl_markdown":
            prompt = "qwenvl markdown"
        elif format_style == "qwenvl_html":
            prompt = "qwenvl html"
        else:  # standard
            prompt = """Convert this document image to clean markdown format.

REQUIREMENTS:
1. Preserve exact layout and structure
2. Include all text content exactly as shown
3. Use proper markdown syntax
4. Maintain document hierarchy with headers
5. Convert tables to markdown tables where appropriate
6. Use standard markdown formatting for headers, lists, emphasis
7. Maintain clear section separation"""

        # Add page marker instruction for standard format
        if format_style == "standard":
            if is_batch:
                marker_instruction = """

Insert page markers in the format: <!-- PAGE N -->
- Place marker at the START of each page's content
- Page numbers start from 1 and increment sequentially"""
                prompt += marker_instruction
            else:
                prompt += f"\n\nInsert this marker at the START: <!-- PAGE {page_number} -->"

        return prompt

    async def convert_single(
        self,
        image_base64: str,
        format_style: str = "standard",
        page_number: int = 1,
    ) -> MarkdownConversionResult:
        """Convert a single image to markdown.

        Args:
            image_base64: Base64 encoded image
            format_style: Markdown format style (qwenvl_markdown, qwenvl_html, standard)
            page_number: Page number for marker

        Returns:
            MarkdownConversionResult with generated markdown

        Raises:
            Exception: If conversion fails
        """
        start_time = time.time()

        try:
            # Detect MIME type and build data URI
            mime_type = self._detect_mime_type(image_base64)
            data_uri = f"data:{mime_type};base64,{image_base64}"

            # Build conversion prompt
            prompt = self._build_conversion_prompt(
                format_style=format_style, page_number=page_number, is_batch=False
            )

            # Call Qwen API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": data_uri}},
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                extra_body={
                    "min_pixels": self.min_pixels,
                    "max_pixels": self.max_pixels,
                },
            )

            # Extract markdown from response
            markdown_content = response.choices[0].message.content

            # Get token usage
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0

            processing_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Converted page {page_number} to markdown (format: {format_style}) "
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
                f"Qwen markdown conversion failed: {type(e).__name__}: {e}",
                exc_info=True,  # Include full stack trace
            )
            raise Exception(f"Qwen markdown conversion error: {type(e).__name__}: {e}")

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
                    delay = 5 * (2**attempt)
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
        Individual page failures are retried with exponential backoff (5s, 10s, 20s).
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
                f"Parallel batch converted {len(images_base64)} pages to markdown (format: {format_style}) "
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
                f"Qwen parallel batch markdown conversion failed: {type(e).__name__}: {e}",
                exc_info=True,  # Include full stack trace
            )
            raise Exception(
                f"Qwen parallel batch markdown conversion error: {type(e).__name__}: {e}"
            )
