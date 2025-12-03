"""PDF utility functions."""

import logging
from typing import Optional
from pdf2image import convert_from_bytes

logger = logging.getLogger(__name__)


def get_pdf_page_count(pdf_bytes: bytes) -> int:
    """
    Extract page count from PDF without full processing.

    This is a lightweight operation that only counts pages
    without converting them to images or storing them.

    Args:
        pdf_bytes: PDF file content as bytes

    Returns:
        Number of pages in the PDF

    Raises:
        ValueError: If PDF is invalid or cannot be processed
    """
    try:
        # Use pdf2image to get page count
        # We use dpi=72 (minimal) since we only need count, not quality
        images = convert_from_bytes(
            pdf_bytes,
            dpi=72,  # Minimal DPI for counting
            fmt="png",
        )
        page_count = len(images)

        logger.info(f"PDF page count extraction successful: {page_count} pages")
        return page_count

    except Exception as e:
        logger.error(f"Failed to extract PDF page count: {str(e)}", exc_info=True)
        raise ValueError(f"Invalid PDF or cannot extract page count: {str(e)}")
