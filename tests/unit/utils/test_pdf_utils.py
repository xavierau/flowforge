"""Unit tests for pdf_utils module."""

import io
import pytest
from pypdf import PdfReader, PdfWriter


def create_test_pdf(num_pages: int) -> bytes:
    """Create a simple test PDF with specified number of pages."""
    writer = PdfWriter()

    for i in range(num_pages):
        page = writer.add_blank_page(width=612, height=792)

    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer.read()


class TestSplitPdfByIndices:
    """Tests for split_pdf_by_indices function."""

    def test_splits_pdf_at_single_boundary(self):
        """Should split PDF into 2 documents at index 3."""
        from app.utils.pdf_utils import split_pdf_by_indices

        pdf_bytes = create_test_pdf(6)
        starting_indices = [0, 3]

        result = split_pdf_by_indices(pdf_bytes, starting_indices)

        assert len(result) == 2
        reader1 = PdfReader(io.BytesIO(result[0]))
        reader2 = PdfReader(io.BytesIO(result[1]))
        assert len(reader1.pages) == 3  # pages 0, 1, 2
        assert len(reader2.pages) == 3  # pages 3, 4, 5

    def test_splits_pdf_at_multiple_boundaries(self):
        """Should split PDF into 3 documents at indices 0, 2, 5."""
        from app.utils.pdf_utils import split_pdf_by_indices

        pdf_bytes = create_test_pdf(8)
        starting_indices = [0, 2, 5]

        result = split_pdf_by_indices(pdf_bytes, starting_indices)

        assert len(result) == 3
        reader1 = PdfReader(io.BytesIO(result[0]))
        reader2 = PdfReader(io.BytesIO(result[1]))
        reader3 = PdfReader(io.BytesIO(result[2]))
        assert len(reader1.pages) == 2  # pages 0, 1
        assert len(reader2.pages) == 3  # pages 2, 3, 4
        assert len(reader3.pages) == 3  # pages 5, 6, 7

    def test_single_starting_index_returns_whole_pdf(self):
        """Should return single PDF when only starting index is 0."""
        from app.utils.pdf_utils import split_pdf_by_indices

        pdf_bytes = create_test_pdf(4)
        starting_indices = [0]

        result = split_pdf_by_indices(pdf_bytes, starting_indices)

        assert len(result) == 1
        reader = PdfReader(io.BytesIO(result[0]))
        assert len(reader.pages) == 4

    def test_raises_error_on_empty_starting_indices(self):
        """Should raise ValueError when starting_indices is empty."""
        from app.utils.pdf_utils import split_pdf_by_indices

        pdf_bytes = create_test_pdf(4)

        with pytest.raises(ValueError):
            split_pdf_by_indices(pdf_bytes, [])

    def test_raises_error_on_invalid_index(self):
        """Should raise ValueError when index exceeds page count."""
        from app.utils.pdf_utils import split_pdf_by_indices

        pdf_bytes = create_test_pdf(4)

        with pytest.raises(ValueError):
            split_pdf_by_indices(pdf_bytes, [0, 10])

    def test_applies_rotation_from_rotation_map(self):
        """Should apply rotation corrections from rotation_map."""
        from app.utils.pdf_utils import split_pdf_by_indices

        pdf_bytes = create_test_pdf(4)
        starting_indices = [0, 2]
        rotation_map = {1: 90, 3: 180}

        result = split_pdf_by_indices(
            pdf_bytes, starting_indices, rotation_map=rotation_map
        )

        assert len(result) == 2
        reader1 = PdfReader(io.BytesIO(result[0]))
        reader2 = PdfReader(io.BytesIO(result[1]))

        # Page 1 (index 1) should have 90 degree rotation applied
        # pypdf stores rotation in /Rotate attribute
        page1_rotation = reader1.pages[1].get("/Rotate", 0)
        assert page1_rotation == 90

        # Page 3 (index 3, now index 1 in second doc) should have 180 rotation
        page3_rotation = reader2.pages[1].get("/Rotate", 0)
        assert page3_rotation == 180

    def test_does_not_apply_rotation_when_disabled(self):
        """Should not apply rotation when apply_rotation is False."""
        from app.utils.pdf_utils import split_pdf_by_indices

        pdf_bytes = create_test_pdf(4)
        starting_indices = [0]
        rotation_map = {1: 90}

        result = split_pdf_by_indices(
            pdf_bytes,
            starting_indices,
            rotation_map=rotation_map,
            apply_rotation=False,
        )

        reader = PdfReader(io.BytesIO(result[0]))
        page1_rotation = reader.pages[1].get("/Rotate", 0)
        assert page1_rotation == 0

    def test_handles_non_starting_from_zero(self):
        """Should correctly split when first index is not 0."""
        from app.utils.pdf_utils import split_pdf_by_indices

        pdf_bytes = create_test_pdf(6)
        # Starting at page 2, not 0
        starting_indices = [2, 4]

        result = split_pdf_by_indices(pdf_bytes, starting_indices)

        assert len(result) == 2
        reader1 = PdfReader(io.BytesIO(result[0]))
        reader2 = PdfReader(io.BytesIO(result[1]))
        assert len(reader1.pages) == 2  # pages 2, 3
        assert len(reader2.pages) == 2  # pages 4, 5

    def test_returns_list_of_bytes(self):
        """Should return a list of bytes objects."""
        from app.utils.pdf_utils import split_pdf_by_indices

        pdf_bytes = create_test_pdf(4)
        starting_indices = [0, 2]

        result = split_pdf_by_indices(pdf_bytes, starting_indices)

        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, bytes)

    def test_each_output_is_valid_pdf(self):
        """Each output should be a valid PDF that can be read."""
        from app.utils.pdf_utils import split_pdf_by_indices

        pdf_bytes = create_test_pdf(6)
        starting_indices = [0, 2, 4]

        result = split_pdf_by_indices(pdf_bytes, starting_indices)

        for pdf_bytes_output in result:
            reader = PdfReader(io.BytesIO(pdf_bytes_output))
            assert len(reader.pages) > 0
