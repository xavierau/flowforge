"""Rotation detection and image utilities for document splitting."""

import base64
import io
import logging
from typing import Dict

import PIL.Image
import pytesseract

logger = logging.getLogger(__name__)


def detect_rotation_tesseract(image: PIL.Image.Image) -> Dict:
    """
    Detect page rotation using Tesseract OSD (Orientation and Script Detection).

    Args:
        image: PIL Image to analyze

    Returns:
        Dict with keys:
        - rotation_needed: int (0, 90, 180, 270) - clockwise rotation to fix
        - confidence: str ("high", "medium", "low")
        - script: str - detected script (e.g., "Latin")
        - method: str - always "tesseract_osd"
    """
    try:
        osd = pytesseract.image_to_osd(
            image, output_type=pytesseract.Output.DICT
        )

        detected_angle = osd.get("rotate", 0)
        osd_confidence = osd.get("orientation_conf", 0)

        confidence = _map_confidence_level(osd_confidence)

        return {
            "rotation_needed": detected_angle,
            "confidence": confidence,
            "script": osd.get("script", "unknown"),
            "method": "tesseract_osd",
        }

    except Exception as e:
        logger.warning(f"Tesseract OSD failed: {e}")
        return {
            "rotation_needed": 0,
            "confidence": "low",
            "script": "unknown",
            "method": "tesseract_osd",
            "error": str(e),
        }


def _map_confidence_level(osd_confidence: float) -> str:
    """Map numeric OSD confidence to string level."""
    if osd_confidence > 5.0:
        return "high"
    elif osd_confidence > 1.0:
        return "medium"
    else:
        return "low"


def rotate_image(image: PIL.Image.Image, degrees: int) -> PIL.Image.Image:
    """
    Rotate image by specified degrees (clockwise).

    Args:
        image: PIL Image to rotate
        degrees: Rotation in degrees (0, 90, 180, 270)

    Returns:
        Rotated PIL Image (or original if degrees=0)
    """
    if degrees == 0:
        return image

    degrees = degrees % 360

    if degrees == 90:
        return image.transpose(PIL.Image.Transpose.ROTATE_270)
    elif degrees == 180:
        return image.transpose(PIL.Image.Transpose.ROTATE_180)
    elif degrees == 270:
        return image.transpose(PIL.Image.Transpose.ROTATE_90)
    else:
        return image.rotate(-degrees, expand=True, fillcolor="white")


def resize_image_for_api(
    image: PIL.Image.Image,
    max_size: int = 2048,
) -> PIL.Image.Image:
    """
    Resize image maintaining aspect ratio for API calls.

    Args:
        image: PIL Image to resize
        max_size: Maximum dimension (width or height)

    Returns:
        Resized PIL Image
    """
    width, height = image.size

    if width <= max_size and height <= max_size:
        return image

    if width > height:
        new_width = max_size
        new_height = int(height * (max_size / width))
    else:
        new_height = max_size
        new_width = int(width * (max_size / height))

    return image.resize((new_width, new_height), PIL.Image.Resampling.LANCZOS)


def image_to_base64(image: PIL.Image.Image, format: str = "JPEG") -> str:
    """
    Convert PIL Image to base64 string.

    Args:
        image: PIL Image to convert
        format: Output format (JPEG, PNG)

    Returns:
        Base64 encoded string (without data URI prefix)
    """
    buffer = io.BytesIO()

    if format.upper() == "JPEG" and image.mode == "RGBA":
        image = image.convert("RGB")

    image.save(buffer, format=format.upper())
    buffer.seek(0)

    return base64.b64encode(buffer.read()).decode("utf-8")


def base64_to_image(base64_str: str) -> PIL.Image.Image:
    """
    Convert base64 string back to PIL Image.

    Args:
        base64_str: Base64 encoded image string

    Returns:
        PIL Image
    """
    image_bytes = base64.b64decode(base64_str)
    buffer = io.BytesIO(image_bytes)
    return PIL.Image.open(buffer)
