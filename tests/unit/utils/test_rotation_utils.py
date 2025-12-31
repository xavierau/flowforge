"""Unit tests for rotation_utils module."""

import base64
import io
import pytest
from PIL import Image
from unittest.mock import patch, MagicMock


class TestDetectRotationTesseract:
    """Tests for detect_rotation_tesseract function."""

    def test_returns_dict_with_required_keys(self):
        """Should return a dict with rotation_needed, confidence, script, method."""
        from app.utils.rotation_utils import detect_rotation_tesseract

        # Create a simple test image
        image = Image.new("RGB", (100, 100), color="white")

        with patch("pytesseract.image_to_osd") as mock_osd:
            mock_osd.return_value = {
                "rotate": 0,
                "orientation_conf": 10.5,
                "script": "Latin",
            }

            result = detect_rotation_tesseract(image)

            assert "rotation_needed" in result
            assert "confidence" in result
            assert "script" in result
            assert "method" in result
            assert result["method"] == "tesseract_osd"

    def test_returns_correct_rotation_value(self):
        """Should return the rotation value from tesseract OSD."""
        from app.utils.rotation_utils import detect_rotation_tesseract

        image = Image.new("RGB", (100, 100), color="white")

        with patch("pytesseract.image_to_osd") as mock_osd:
            mock_osd.return_value = {
                "rotate": 90,
                "orientation_conf": 8.0,
                "script": "Latin",
            }

            result = detect_rotation_tesseract(image)

            assert result["rotation_needed"] == 90

    def test_returns_high_confidence_when_above_threshold(self):
        """Should return 'high' confidence when OSD confidence > 5.0."""
        from app.utils.rotation_utils import detect_rotation_tesseract

        image = Image.new("RGB", (100, 100), color="white")

        with patch("pytesseract.image_to_osd") as mock_osd:
            mock_osd.return_value = {
                "rotate": 0,
                "orientation_conf": 8.5,
                "script": "Latin",
            }

            result = detect_rotation_tesseract(image)

            assert result["confidence"] == "high"

    def test_returns_medium_confidence_when_in_middle_range(self):
        """Should return 'medium' confidence when OSD confidence between 1.0 and 5.0."""
        from app.utils.rotation_utils import detect_rotation_tesseract

        image = Image.new("RGB", (100, 100), color="white")

        with patch("pytesseract.image_to_osd") as mock_osd:
            mock_osd.return_value = {
                "rotate": 0,
                "orientation_conf": 3.0,
                "script": "Latin",
            }

            result = detect_rotation_tesseract(image)

            assert result["confidence"] == "medium"

    def test_returns_low_confidence_when_below_threshold(self):
        """Should return 'low' confidence when OSD confidence <= 1.0."""
        from app.utils.rotation_utils import detect_rotation_tesseract

        image = Image.new("RGB", (100, 100), color="white")

        with patch("pytesseract.image_to_osd") as mock_osd:
            mock_osd.return_value = {
                "rotate": 0,
                "orientation_conf": 0.5,
                "script": "Latin",
            }

            result = detect_rotation_tesseract(image)

            assert result["confidence"] == "low"

    def test_handles_osd_error_gracefully(self):
        """Should return 0 rotation when tesseract OSD fails."""
        from app.utils.rotation_utils import detect_rotation_tesseract

        image = Image.new("RGB", (100, 100), color="white")

        with patch("pytesseract.image_to_osd") as mock_osd:
            mock_osd.side_effect = Exception("Too few characters")

            result = detect_rotation_tesseract(image)

            assert result["rotation_needed"] == 0
            assert result["confidence"] == "low"
            assert "error" in result


class TestRotateImage:
    """Tests for rotate_image function."""

    def test_returns_same_image_when_rotation_is_zero(self):
        """Should return original image when rotation is 0."""
        from app.utils.rotation_utils import rotate_image

        image = Image.new("RGB", (100, 200), color="red")

        result = rotate_image(image, 0)

        assert result.size == image.size

    def test_rotates_image_90_degrees_clockwise(self):
        """Should rotate image 90 degrees clockwise (width/height swapped)."""
        from app.utils.rotation_utils import rotate_image

        image = Image.new("RGB", (100, 200), color="red")

        result = rotate_image(image, 90)

        # 90 degrees clockwise: (100, 200) -> (200, 100)
        assert result.size == (200, 100)

    def test_rotates_image_180_degrees(self):
        """Should rotate image 180 degrees (same dimensions)."""
        from app.utils.rotation_utils import rotate_image

        image = Image.new("RGB", (100, 200), color="red")

        result = rotate_image(image, 180)

        assert result.size == (100, 200)

    def test_rotates_image_270_degrees_clockwise(self):
        """Should rotate image 270 degrees clockwise (width/height swapped)."""
        from app.utils.rotation_utils import rotate_image

        image = Image.new("RGB", (100, 200), color="red")

        result = rotate_image(image, 270)

        # 270 degrees clockwise: (100, 200) -> (200, 100)
        assert result.size == (200, 100)


class TestResizeImageForApi:
    """Tests for resize_image_for_api function."""

    def test_returns_same_image_when_within_max_size(self):
        """Should return original image when both dimensions are within max_size."""
        from app.utils.rotation_utils import resize_image_for_api

        image = Image.new("RGB", (500, 400), color="blue")

        result = resize_image_for_api(image, max_size=2048)

        assert result.size == (500, 400)

    def test_resizes_width_when_width_exceeds_max_size(self):
        """Should resize maintaining aspect ratio when width exceeds max_size."""
        from app.utils.rotation_utils import resize_image_for_api

        image = Image.new("RGB", (4000, 2000), color="blue")

        result = resize_image_for_api(image, max_size=2000)

        # Width 4000 -> 2000, height scales: 2000 * (2000/4000) = 1000
        assert result.size[0] == 2000
        assert result.size[1] == 1000

    def test_resizes_height_when_height_exceeds_max_size(self):
        """Should resize maintaining aspect ratio when height exceeds max_size."""
        from app.utils.rotation_utils import resize_image_for_api

        image = Image.new("RGB", (1000, 3000), color="blue")

        result = resize_image_for_api(image, max_size=1500)

        # Height 3000 -> 1500, width scales: 1000 * (1500/3000) = 500
        assert result.size[0] == 500
        assert result.size[1] == 1500

    def test_uses_default_max_size_of_2048(self):
        """Should use 2048 as default max_size."""
        from app.utils.rotation_utils import resize_image_for_api

        image = Image.new("RGB", (4096, 2048), color="blue")

        result = resize_image_for_api(image)

        assert max(result.size) <= 2048


class TestImageToBase64:
    """Tests for image_to_base64 function."""

    def test_returns_base64_encoded_string(self):
        """Should return a valid base64 encoded string."""
        from app.utils.rotation_utils import image_to_base64

        image = Image.new("RGB", (100, 100), color="green")

        result = image_to_base64(image)

        # Should be decodable
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_does_not_include_data_uri_prefix(self):
        """Should not include data:image/... prefix."""
        from app.utils.rotation_utils import image_to_base64

        image = Image.new("RGB", (100, 100), color="green")

        result = image_to_base64(image)

        assert not result.startswith("data:")

    def test_uses_jpeg_format_by_default(self):
        """Should use JPEG format by default."""
        from app.utils.rotation_utils import image_to_base64

        image = Image.new("RGB", (100, 100), color="green")

        result = image_to_base64(image)
        decoded = base64.b64decode(result)

        # JPEG magic bytes: 0xFF 0xD8
        assert decoded[:2] == b"\xff\xd8"

    def test_uses_png_format_when_specified(self):
        """Should use PNG format when specified."""
        from app.utils.rotation_utils import image_to_base64

        image = Image.new("RGB", (100, 100), color="green")

        result = image_to_base64(image, format="PNG")
        decoded = base64.b64decode(result)

        # PNG magic bytes: 0x89 P N G
        assert decoded[:4] == b"\x89PNG"


class TestBase64ToImage:
    """Tests for base64_to_image function."""

    def test_converts_base64_string_to_pil_image(self):
        """Should convert base64 string back to PIL Image."""
        from app.utils.rotation_utils import base64_to_image, image_to_base64

        original = Image.new("RGB", (100, 100), color="yellow")
        encoded = image_to_base64(original)

        result = base64_to_image(encoded)

        assert isinstance(result, Image.Image)
        assert result.size == original.size

    def test_preserves_image_dimensions(self):
        """Should preserve image dimensions through encode/decode cycle."""
        from app.utils.rotation_utils import base64_to_image, image_to_base64

        original = Image.new("RGB", (250, 175), color="purple")
        encoded = image_to_base64(original, format="PNG")

        result = base64_to_image(encoded)

        assert result.size == (250, 175)
