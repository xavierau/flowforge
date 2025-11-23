"""GPT-4 Vision-based markdown converter implementation.

Uses OpenAI GPT-4 Vision model to convert document images to markdown.
Supports both single-page and multi-page batch conversion.
"""

import asyncio
import base64
import time
from typing import List
import logging

from openai import OpenAI

from app.services.converters.base import (
    IImageToMarkdownConverter,
    MarkdownConversionResult,
)

logger = logging.getLogger(__name__)


class GPT4VMarkdownConverter(IImageToMarkdownConverter):
    """GPT-4 Vision-based markdown converter.

    Uses OpenAI GPT-4 Vision model for high-quality markdown conversion.
    """

    def __init__(self, api_key: str, model: str = "gpt-4-vision-preview"):
        """Initialize GPT-4V converter.

        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-4-vision-preview)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.provider = "gpt4v"

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
            # Build conversion prompt
            prompt = self._build_conversion_prompt(
                format_style=format_style, page_number=page_number, is_batch=False
            )

            # Build messages with system instruction and image
            messages = [
                {
                    "role": "system",
                    "content": """You are an expert document-to-markdown converter.
Convert document images to high-quality markdown with perfect accuracy.
Preserve all information, structure, and formatting from the original document.
Pay special attention to tables, lists, and hierarchical structure.""",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            },
                        },
                    ],
                },
            ]

            # Generate markdown using GPT-4V
            response = self.client.chat.completions.create(
                model=self.model, messages=messages, max_tokens=4096
            )

            # Extract markdown from response
            markdown_content = response.choices[0].message.content

            # Strip markdown code blocks if present
            if "```markdown" in markdown_content:
                markdown_content = (
                    markdown_content.split("```markdown")[1].split("```")[0].strip()
                )
            elif "```" in markdown_content:
                markdown_content = (
                    markdown_content.split("```")[1].split("```")[0].strip()
                )

            # Get token usage
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0

            processing_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Converted page {page_number} to markdown "
                f"(tokens: {input_tokens}+{output_tokens}, "
                f"time: {processing_time_ms}ms)"
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
            logger.error(f"GPT-4V markdown conversion failed: {e}")
            raise Exception(f"GPT-4V markdown conversion error: {e}")

    async def convert_batch(
        self,
        images_base64: List[str],
        format_style: str = "standard",
    ) -> MarkdownConversionResult:
        """Convert multiple images to markdown using parallel processing.

        Each page is processed concurrently with its own API call for maximum speed.
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
            Exception: If conversion fails
        """
        start_time = time.time()

        try:
            # Create concurrent tasks for each page
            tasks = [
                self.convert_single(
                    image_base64=img_b64,
                    format_style=format_style,
                    page_number=page_num,
                )
                for page_num, img_b64 in enumerate(images_base64, start=1)
            ]

            # Execute all tasks in parallel using asyncio.gather
            logger.info(
                f"Starting parallel conversion of {len(images_base64)} pages..."
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
            logger.error(f"GPT-4V parallel batch markdown conversion failed: {e}")
            raise Exception(f"GPT-4V parallel batch markdown conversion error: {e}")
