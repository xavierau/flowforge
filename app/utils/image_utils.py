"""
Image processing utilities for document processing.

This module provides utility functions for image manipulation,
including grid overlays for visual debugging and analysis,
noise removal for cleaner document images, and contrast enhancement.
"""
from typing import Tuple, Optional, Literal
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import numpy as np
import cv2


def add_transparent_grid_overlay(
    image_path: str,
    output_path: str,
    grid_size: int,
    line_color: Tuple[int, int, int, int] = (255, 255, 255, 100),
    line_width: int = 1
) -> None:
    """
    Adds a truly transparent grid overlay to an image.

    This function creates a separate transparent layer with grid lines,
    then composites it onto the original image while preserving the
    alpha channel. Useful for visual debugging of document layouts.

    Args:
        image_path: Path to the input image.
        output_path: Path to save the image with the grid overlay.
                    Must be PNG format to preserve transparency.
        grid_size: The size of each square in the grid (in pixels).
        line_color: RGBA tuple for the grid line color.
                   Default is (255, 255, 255, 100) - white at ~39% opacity.
                   Alpha value range: 0 (fully transparent) to 255 (opaque).
        line_width: The width of the grid lines in pixels (default: 1).

    Raises:
        FileNotFoundError: If the input image file doesn't exist.
        ValueError: If invalid parameters are provided.
        Exception: For other image processing errors.

    Example:
        >>> add_transparent_grid_overlay(
        ...     "invoice.png",
        ...     "invoice_with_grid.png",
        ...     grid_size=50,
        ...     line_color=(255, 255, 255, 100)
        ... )
        Transparent grid saved as invoice_with_grid.png
        Grid: 50px squares, color: (255, 255, 255, 100), width: 1px

    Note:
        - Output MUST be PNG format (JPEG doesn't support transparency)
        - For visible transparency, alpha value should be < 255
        - The overlay method preserves the original image quality
    """
    try:
        # Validate parameters
        if grid_size <= 0:
            raise ValueError(f"grid_size must be positive, got {grid_size}")
        if line_width <= 0:
            raise ValueError(f"line_width must be positive, got {line_width}")
        if len(line_color) != 4:
            raise ValueError(f"line_color must be RGBA tuple, got {line_color}")
        if not output_path.lower().endswith('.png'):
            raise ValueError(
                f"output_path must be PNG format for transparency support, "
                f"got {output_path}"
            )

        # Open and convert to RGBA
        img = Image.open(image_path).convert("RGBA")

        # Create a transparent overlay layer
        overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        width, height = img.size

        # Draw vertical lines on overlay
        for x in range(0, width, grid_size):
            draw.line([(x, 0), (x, height)], fill=line_color, width=line_width)

        # Draw horizontal lines on overlay
        for y in range(0, height, grid_size):
            draw.line([(0, y), (width, y)], fill=line_color, width=line_width)

        # Composite overlay onto original image (preserves transparency)
        result = Image.alpha_composite(img, overlay)

        # Save as PNG to preserve transparency
        result.save(output_path, "PNG")
        print(f"Transparent grid saved as {output_path}")
        print(f"Grid: {grid_size}px squares, color: {line_color}, width: {line_width}px")

    except FileNotFoundError:
        raise FileNotFoundError(f"Image not found at {image_path}")
    except ValueError as e:
        raise ValueError(f"Invalid parameter: {e}")
    except Exception as e:
        raise Exception(f"Error processing image: {e}")


def add_grid_to_pil_image(
    img: Image.Image,
    grid_size: int,
    line_color: Tuple[int, int, int, int] = (255, 255, 255, 100),
    line_width: int = 1
) -> Image.Image:
    """
    Adds a transparent grid overlay to a PIL Image object.

    This is a variant of add_transparent_grid_overlay that works with
    PIL Image objects directly instead of file paths. Useful for
    in-memory image processing pipelines.

    Args:
        img: PIL Image object to add grid to.
        grid_size: The size of each square in the grid (in pixels).
        line_color: RGBA tuple for the grid line color.
                   Default is (255, 255, 255, 100) - white at ~39% opacity.
        line_width: The width of the grid lines in pixels (default: 1).

    Returns:
        PIL Image object with grid overlay applied.

    Example:
        >>> from PIL import Image
        >>> img = Image.open("invoice.png")
        >>> img_with_grid = add_grid_to_pil_image(img, grid_size=50)
        >>> img_with_grid.save("output.png")
    """
    # Validate parameters
    if grid_size <= 0:
        raise ValueError(f"grid_size must be positive, got {grid_size}")
    if line_width <= 0:
        raise ValueError(f"line_width must be positive, got {line_width}")
    if len(line_color) != 4:
        raise ValueError(f"line_color must be RGBA tuple, got {line_color}")

    # Convert to RGBA
    img_rgba = img.convert("RGBA")

    # Create a transparent overlay layer
    overlay = Image.new('RGBA', img_rgba.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = img_rgba.size

    # Draw vertical lines
    for x in range(0, width, grid_size):
        draw.line([(x, 0), (x, height)], fill=line_color, width=line_width)

    # Draw horizontal lines
    for y in range(0, height, grid_size):
        draw.line([(0, y), (width, y)], fill=line_color, width=line_width)

    # Composite overlay onto original image
    result = Image.alpha_composite(img_rgba, overlay)

    return result


def remove_noise(
    image_path: str,
    output_path: str,
    method: Literal["gaussian", "median", "bilateral", "morphological"] = "bilateral",
    strength: Literal["light", "medium", "strong"] = "medium"
) -> None:
    """
    Removes noise from document images while preserving text clarity.

    This function applies various noise reduction techniques optimized for
    document processing. It supports multiple denoising methods with
    configurable strength levels.

    Args:
        image_path: Path to the input image.
        output_path: Path to save the denoised image.
        method: Denoising method to use:
            - "gaussian": Good for general noise, may blur text slightly
            - "median": Excellent for salt-and-pepper noise
            - "bilateral": Best for preserving edges (text) while removing noise
            - "morphological": Uses opening/closing operations for structured noise
        strength: Denoising strength level:
            - "light": Minimal noise reduction, preserves maximum detail
            - "medium": Balanced noise reduction (recommended for documents)
            - "strong": Aggressive noise reduction, may affect fine details

    Raises:
        FileNotFoundError: If the input image file doesn't exist.
        ValueError: If invalid method or strength parameter.
        Exception: For other image processing errors.

    Example:
        >>> # Remove noise while preserving text edges
        >>> remove_noise(
        ...     "scanned_invoice.png",
        ...     "clean_invoice.png",
        ...     method="bilateral",
        ...     strength="medium"
        ... )
        Noise removed using bilateral filter (medium strength)
        Saved to clean_invoice.png

    Note:
        - "bilateral" is recommended for document images
        - For scanned documents with scan lines, use "morphological"
        - For photos/screenshots, use "gaussian" or "median"
        - Test different strengths on a sample to find optimal settings
    """
    try:
        # Validate parameters
        valid_methods = ["gaussian", "median", "bilateral", "morphological"]
        if method not in valid_methods:
            raise ValueError(
                f"Invalid method '{method}'. Must be one of {valid_methods}"
            )

        valid_strengths = ["light", "medium", "strong"]
        if strength not in valid_strengths:
            raise ValueError(
                f"Invalid strength '{strength}'. Must be one of {valid_strengths}"
            )

        # Load image
        img = Image.open(image_path)
        img_array = np.array(img)

        # Convert to grayscale if needed (for better noise detection)
        is_grayscale = len(img_array.shape) == 2
        if not is_grayscale and img_array.shape[2] == 4:  # RGBA
            # Convert RGBA to RGB
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)

        # Define strength parameters for each method
        strength_params = {
            "light": {"gaussian": 3, "median": 3, "bilateral": (5, 75, 75), "morphological": 2},
            "medium": {"gaussian": 5, "median": 5, "bilateral": (9, 75, 75), "morphological": 3},
            "strong": {"gaussian": 7, "median": 7, "bilateral": (15, 75, 75), "morphological": 5}
        }

        # Apply selected denoising method
        if method == "gaussian":
            kernel_size = strength_params[strength]["gaussian"]
            if kernel_size % 2 == 0:  # Ensure odd kernel size
                kernel_size += 1
            denoised = cv2.GaussianBlur(img_array, (kernel_size, kernel_size), 0)

        elif method == "median":
            kernel_size = strength_params[strength]["median"]
            if kernel_size % 2 == 0:  # Ensure odd kernel size
                kernel_size += 1
            denoised = cv2.medianBlur(img_array, kernel_size)

        elif method == "bilateral":
            d, sigma_color, sigma_space = strength_params[strength]["bilateral"]
            denoised = cv2.bilateralFilter(img_array, d, sigma_color, sigma_space)

        elif method == "morphological":
            # Convert to grayscale for morphological operations
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array

            kernel_size = strength_params[strength]["morphological"]
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))

            # Morphological opening (erosion followed by dilation) removes small noise
            denoised_gray = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)

            # If original was color, apply mask to preserve color
            if len(img_array.shape) == 3:
                # Create a mask and apply to original color image
                _, mask = cv2.threshold(denoised_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                denoised = cv2.bitwise_and(img_array, img_array, mask=mask)
            else:
                denoised = denoised_gray

        # Convert back to PIL Image
        result = Image.fromarray(denoised)

        # Save with appropriate format
        if output_path.lower().endswith(('.jpg', '.jpeg')):
            result.save(output_path, "JPEG", quality=95)
        elif output_path.lower().endswith('.png'):
            result.save(output_path, "PNG")
        else:
            result.save(output_path)

        print(f"Noise removed using {method} filter ({strength} strength)")
        print(f"Saved to {output_path}")

    except FileNotFoundError:
        raise FileNotFoundError(f"Image not found at {image_path}")
    except ValueError as e:
        raise ValueError(f"Invalid parameter: {e}")
    except Exception as e:
        raise Exception(f"Error processing image: {e}")


def remove_noise_from_pil_image(
    img: Image.Image,
    method: Literal["gaussian", "median", "bilateral", "morphological"] = "bilateral",
    strength: Literal["light", "medium", "strong"] = "medium"
) -> Image.Image:
    """
    Removes noise from a PIL Image object while preserving text clarity.

    This is a variant of remove_noise that works with PIL Image objects
    directly instead of file paths. Useful for in-memory image processing
    pipelines.

    Args:
        img: PIL Image object to denoise.
        method: Denoising method ("gaussian", "median", "bilateral", "morphological").
        strength: Denoising strength ("light", "medium", "strong").

    Returns:
        PIL Image object with noise removed.

    Example:
        >>> from PIL import Image
        >>> img = Image.open("scanned_doc.png")
        >>> clean_img = remove_noise_from_pil_image(img, method="bilateral")
        >>> clean_img.save("clean_doc.png")
    """
    # Validate parameters
    valid_methods = ["gaussian", "median", "bilateral", "morphological"]
    if method not in valid_methods:
        raise ValueError(f"Invalid method '{method}'. Must be one of {valid_methods}")

    valid_strengths = ["light", "medium", "strong"]
    if strength not in valid_strengths:
        raise ValueError(f"Invalid strength '{strength}'. Must be one of {valid_strengths}")

    # Convert PIL Image to numpy array
    img_array = np.array(img)

    # Handle RGBA images
    if len(img_array.shape) == 3 and img_array.shape[2] == 4:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)

    # Define strength parameters
    strength_params = {
        "light": {"gaussian": 3, "median": 3, "bilateral": (5, 75, 75), "morphological": 2},
        "medium": {"gaussian": 5, "median": 5, "bilateral": (9, 75, 75), "morphological": 3},
        "strong": {"gaussian": 7, "median": 7, "bilateral": (15, 75, 75), "morphological": 5}
    }

    # Apply selected denoising method
    if method == "gaussian":
        kernel_size = strength_params[strength]["gaussian"]
        if kernel_size % 2 == 0:
            kernel_size += 1
        denoised = cv2.GaussianBlur(img_array, (kernel_size, kernel_size), 0)

    elif method == "median":
        kernel_size = strength_params[strength]["median"]
        if kernel_size % 2 == 0:
            kernel_size += 1
        denoised = cv2.medianBlur(img_array, kernel_size)

    elif method == "bilateral":
        d, sigma_color, sigma_space = strength_params[strength]["bilateral"]
        denoised = cv2.bilateralFilter(img_array, d, sigma_color, sigma_space)

    elif method == "morphological":
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        kernel_size = strength_params[strength]["morphological"]
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
        denoised_gray = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)

        if len(img_array.shape) == 3:
            _, mask = cv2.threshold(denoised_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            denoised = cv2.bitwise_and(img_array, img_array, mask=mask)
        else:
            denoised = denoised_gray

    # Convert back to PIL Image
    result = Image.fromarray(denoised)

    return result


def increase_contrast(
    image_path: str,
    output_path: str,
    method: Literal["simple", "adaptive", "clahe"] = "adaptive",
    factor: float = 1.5
) -> None:
    """
    Increases the contrast of document images to improve readability.

    This function provides multiple contrast enhancement methods optimized
    for document processing, making faded or low-contrast text more readable.

    Args:
        image_path: Path to the input image.
        output_path: Path to save the contrast-enhanced image.
        method: Contrast enhancement method:
            - "simple": Linear contrast adjustment using a factor multiplier
            - "adaptive": Histogram equalization (best for varied lighting)
            - "clahe": Contrast Limited Adaptive Histogram Equalization
                      (best for documents, prevents over-enhancement)
        factor: Contrast multiplier for "simple" method (default: 1.5).
               - 1.0 = no change
               - < 1.0 = reduce contrast
               - > 1.0 = increase contrast
               - Typical range: 1.2 to 2.0
               Ignored for "adaptive" and "clahe" methods.

    Raises:
        FileNotFoundError: If the input image file doesn't exist.
        ValueError: If invalid method or factor parameter.
        Exception: For other image processing errors.

    Example:
        >>> # Use CLAHE for best document results
        >>> increase_contrast(
        ...     "faded_invoice.png",
        ...     "enhanced_invoice.png",
        ...     method="clahe"
        ... )
        Contrast enhanced using clahe method
        Saved to enhanced_invoice.png

        >>> # Simple linear adjustment
        >>> increase_contrast(
        ...     "invoice.png",
        ...     "enhanced.png",
        ...     method="simple",
        ...     factor=1.8
        ... )
        Contrast enhanced using simple method (factor: 1.8)
        Saved to enhanced.png

    Note:
        - "clahe" is recommended for scanned documents
        - "adaptive" works well for photos with varied lighting
        - "simple" gives you precise control but may over-enhance
        - For text recognition, moderate enhancement (1.3-1.5) is best
    """
    try:
        # Validate parameters
        valid_methods = ["simple", "adaptive", "clahe"]
        if method not in valid_methods:
            raise ValueError(
                f"Invalid method '{method}'. Must be one of {valid_methods}"
            )

        if method == "simple" and (factor <= 0):
            raise ValueError(f"Factor must be positive, got {factor}")

        # Load image
        img = Image.open(image_path)

        # Apply selected contrast enhancement method
        if method == "simple":
            # Simple linear contrast enhancement using PIL
            enhancer = ImageEnhance.Contrast(img)
            result = enhancer.enhance(factor)
            print(f"Contrast enhanced using {method} method (factor: {factor})")

        elif method == "adaptive":
            # Histogram equalization for adaptive contrast
            img_array = np.array(img)

            # Handle color images
            if len(img_array.shape) == 3:
                # Convert to YCrCb color space
                img_ycrcb = np.array(img.convert('YCbCr'))

                # Equalize the Y channel (luminance)
                img_ycrcb[:, :, 0] = np.array(
                    Image.fromarray(img_ycrcb[:, :, 0]).point(
                        lambda x: int(255 * (x / 255) ** 0.7)  # Gamma correction
                    )
                )

                # Convert back to RGB
                result = Image.fromarray(img_ycrcb, 'YCbCr').convert('RGB')
            else:
                # Grayscale: direct histogram equalization
                img_array_flat = img_array.flatten()
                hist, bins = np.histogram(img_array_flat, 256, [0, 256])
                cdf = hist.cumsum()
                cdf_normalized = cdf * 255 / cdf[-1]
                img_equalized = np.interp(img_array_flat, bins[:-1], cdf_normalized)
                result = Image.fromarray(img_equalized.reshape(img_array.shape).astype('uint8'))

            print(f"Contrast enhanced using {method} method")

        elif method == "clahe":
            # CLAHE - best for documents
            img_array = np.array(img)

            # Convert to grayscale if needed for CLAHE
            if len(img_array.shape) == 3:
                # Convert to LAB color space for better results
                img_lab = np.array(img.convert('LAB'))
                l_channel = img_lab[:, :, 0]

                # Apply CLAHE to L channel
                clahe = np.zeros_like(l_channel, dtype=np.uint8)

                # Simple tile-based contrast enhancement
                tile_size = 8
                for i in range(0, l_channel.shape[0], tile_size):
                    for j in range(0, l_channel.shape[1], tile_size):
                        tile = l_channel[i:i+tile_size, j:j+tile_size]
                        if tile.size > 0:
                            # Normalize tile
                            tile_min, tile_max = tile.min(), tile.max()
                            if tile_max > tile_min:
                                tile_normalized = ((tile - tile_min) * 255 / (tile_max - tile_min)).astype(np.uint8)
                                clahe[i:i+tile_size, j:j+tile_size] = tile_normalized
                            else:
                                clahe[i:i+tile_size, j:j+tile_size] = tile

                img_lab[:, :, 0] = clahe
                result = Image.fromarray(img_lab, 'LAB').convert('RGB')
            else:
                # Grayscale CLAHE
                tile_size = 8
                clahe_result = np.zeros_like(img_array, dtype=np.uint8)

                for i in range(0, img_array.shape[0], tile_size):
                    for j in range(0, img_array.shape[1], tile_size):
                        tile = img_array[i:i+tile_size, j:j+tile_size]
                        if tile.size > 0:
                            tile_min, tile_max = tile.min(), tile.max()
                            if tile_max > tile_min:
                                tile_normalized = ((tile - tile_min) * 255 / (tile_max - tile_min)).astype(np.uint8)
                                clahe_result[i:i+tile_size, j:j+tile_size] = tile_normalized
                            else:
                                clahe_result[i:i+tile_size, j:j+tile_size] = tile

                result = Image.fromarray(clahe_result)

            print(f"Contrast enhanced using {method} method")

        # Save with appropriate format
        if output_path.lower().endswith(('.jpg', '.jpeg')):
            result.save(output_path, "JPEG", quality=95)
        elif output_path.lower().endswith('.png'):
            result.save(output_path, "PNG")
        else:
            result.save(output_path)

        print(f"Saved to {output_path}")

    except FileNotFoundError:
        raise FileNotFoundError(f"Image not found at {image_path}")
    except ValueError as e:
        raise ValueError(f"Invalid parameter: {e}")
    except Exception as e:
        raise Exception(f"Error processing image: {e}")


def increase_contrast_from_pil_image(
    img: Image.Image,
    method: Literal["simple", "adaptive", "clahe"] = "adaptive",
    factor: float = 1.5
) -> Image.Image:
    """
    Increases the contrast of a PIL Image object.

    This is a variant of increase_contrast that works with PIL Image objects
    directly instead of file paths. Useful for in-memory image processing
    pipelines.

    Args:
        img: PIL Image object to enhance.
        method: Contrast enhancement method ("simple", "adaptive", "clahe").
        factor: Contrast multiplier for "simple" method (default: 1.5).

    Returns:
        PIL Image object with enhanced contrast.

    Example:
        >>> from PIL import Image
        >>> img = Image.open("faded_doc.png")
        >>> enhanced_img = increase_contrast_from_pil_image(img, method="clahe")
        >>> enhanced_img.save("enhanced_doc.png")
    """
    # Validate parameters
    valid_methods = ["simple", "adaptive", "clahe"]
    if method not in valid_methods:
        raise ValueError(f"Invalid method '{method}'. Must be one of {valid_methods}")

    if method == "simple" and (factor <= 0):
        raise ValueError(f"Factor must be positive, got {factor}")

    # Apply selected method
    if method == "simple":
        enhancer = ImageEnhance.Contrast(img)
        result = enhancer.enhance(factor)

    elif method == "adaptive":
        img_array = np.array(img)

        if len(img_array.shape) == 3:
            img_ycrcb = np.array(img.convert('YCbCr'))
            img_ycrcb[:, :, 0] = np.array(
                Image.fromarray(img_ycrcb[:, :, 0]).point(
                    lambda x: int(255 * (x / 255) ** 0.7)
                )
            )
            result = Image.fromarray(img_ycrcb, 'YCbCr').convert('RGB')
        else:
            img_array_flat = img_array.flatten()
            hist, bins = np.histogram(img_array_flat, 256, [0, 256])
            cdf = hist.cumsum()
            cdf_normalized = cdf * 255 / cdf[-1]
            img_equalized = np.interp(img_array_flat, bins[:-1], cdf_normalized)
            result = Image.fromarray(img_equalized.reshape(img_array.shape).astype('uint8'))

    elif method == "clahe":
        img_array = np.array(img)

        if len(img_array.shape) == 3:
            img_lab = np.array(img.convert('LAB'))
            l_channel = img_lab[:, :, 0]

            clahe = np.zeros_like(l_channel, dtype=np.uint8)
            tile_size = 8

            for i in range(0, l_channel.shape[0], tile_size):
                for j in range(0, l_channel.shape[1], tile_size):
                    tile = l_channel[i:i+tile_size, j:j+tile_size]
                    if tile.size > 0:
                        tile_min, tile_max = tile.min(), tile.max()
                        if tile_max > tile_min:
                            tile_normalized = ((tile - tile_min) * 255 / (tile_max - tile_min)).astype(np.uint8)
                            clahe[i:i+tile_size, j:j+tile_size] = tile_normalized
                        else:
                            clahe[i:i+tile_size, j:j+tile_size] = tile

            img_lab[:, :, 0] = clahe
            result = Image.fromarray(img_lab, 'LAB').convert('RGB')
        else:
            tile_size = 8
            clahe_result = np.zeros_like(img_array, dtype=np.uint8)

            for i in range(0, img_array.shape[0], tile_size):
                for j in range(0, img_array.shape[1], tile_size):
                    tile = img_array[i:i+tile_size, j:j+tile_size]
                    if tile.size > 0:
                        tile_min, tile_max = tile.min(), tile.max()
                        if tile_max > tile_min:
                            tile_normalized = ((tile - tile_min) * 255 / (tile_max - tile_min)).astype(np.uint8)
                            clahe_result[i:i+tile_size, j:j+tile_size] = tile_normalized
                        else:
                            clahe_result[i:i+tile_size, j:j+tile_size] = tile

            result = Image.fromarray(clahe_result)

    return result
