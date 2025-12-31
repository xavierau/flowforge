"""PDF utility functions."""

import io
import logging
from typing import Dict, List, Optional

from pdf2image import convert_from_bytes
from pypdf import PdfReader, PdfWriter

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


def split_pdf_by_indices(
    pdf_bytes: bytes,
    starting_indices: List[int],
    rotation_map: Optional[Dict[int, int]] = None,
    apply_rotation: bool = True,
) -> List[bytes]:
    """
    Split PDF into multiple PDFs based on starting page indices.

    Each sub-document starts at a starting_index and continues until
    the next starting_index (or end of document).

    Args:
        pdf_bytes: Original PDF file as bytes
        starting_indices: List of page indices where new documents start (0-indexed)
                         Example: [0, 3, 7] means docs are pages 0-2, 3-6, 7-end
        rotation_map: Dict mapping page_index -> clockwise degrees (0, 90, 180, 270)
        apply_rotation: Whether to apply rotation corrections

    Returns:
        List of PDF bytes, one for each split document

    Raises:
        ValueError: If starting_indices is empty or invalid
    """
    if not starting_indices:
        raise ValueError("starting_indices cannot be empty")

    reader = PdfReader(io.BytesIO(pdf_bytes))
    total_pages = len(reader.pages)

    sorted_indices = sorted(starting_indices)

    for idx in sorted_indices:
        if idx < 0 or idx >= total_pages:
            raise ValueError(
                f"Invalid starting index {idx}: "
                f"PDF has {total_pages} pages (indices 0-{total_pages - 1})"
            )

    if rotation_map is None:
        rotation_map = {}

    output_pdfs: List[bytes] = []

    for i, start_idx in enumerate(sorted_indices):
        if i + 1 < len(sorted_indices):
            end_idx = sorted_indices[i + 1]
        else:
            end_idx = total_pages

        writer = PdfWriter()

        for page_idx in range(start_idx, end_idx):
            page = reader.pages[page_idx]

            rotation = rotation_map.get(page_idx, 0)
            if apply_rotation and rotation != 0:
                page.rotate(rotation)

            writer.add_page(page)

        buffer = io.BytesIO()
        writer.write(buffer)
        buffer.seek(0)
        output_pdfs.append(buffer.read())

    return output_pdfs
