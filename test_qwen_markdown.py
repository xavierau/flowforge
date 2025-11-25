"""Test script for Qwen markdown converter.

Tests all format styles:
- qwenvl_markdown (markdown with coordinates)
- qwenvl_html (HTML with bbox attributes)
- standard (clean markdown)

Both single-page and batch conversion modes.
"""

import asyncio
import base64
import logging
import sys
from pathlib import Path

from app.services.converters.converter_factory import get_converter_factory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def encode_image_to_base64(image_path: str) -> str:
    """Encode image file to base64 string.

    Args:
        image_path: Path to image file

    Returns:
        Base64 encoded string
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


async def test_single_conversion(converter, image_path: str, format_style: str):
    """Test single image conversion.

    Args:
        converter: Qwen markdown converter instance
        image_path: Path to test image
        format_style: Format style to test
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"Testing SINGLE conversion with format: {format_style}")
    logger.info(f"{'='*80}")

    try:
        # Encode image
        image_base64 = encode_image_to_base64(image_path)
        logger.info(f"Loaded image: {image_path}")

        # Convert
        result = await converter.convert_single(
            image_base64=image_base64,
            format_style=format_style,
            page_number=1,
        )

        # Display results
        logger.info(f"\nConversion Results:")
        logger.info(f"  Provider: {result.provider}")
        logger.info(f"  Model: {result.model}")
        logger.info(f"  Input tokens: {result.input_tokens}")
        logger.info(f"  Output tokens: {result.output_tokens}")
        logger.info(f"  Total tokens: {result.input_tokens + result.output_tokens}")
        logger.info(f"  Processing time: {result.processing_time_ms}ms")
        logger.info(f"  Markdown length: {len(result.markdown_content)} chars")

        # Save to file
        output_file = f"test_output_single_{format_style}.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result.markdown_content)
        logger.info(f"\n✓ Saved output to: {output_file}")

        # Show preview
        preview_lines = result.markdown_content.split("\n")[:10]
        logger.info(f"\nMarkdown Preview (first 10 lines):")
        for line in preview_lines:
            logger.info(f"  {line}")
        if len(result.markdown_content.split("\n")) > 10:
            logger.info(f"  ... ({len(result.markdown_content.split('\n')) - 10} more lines)")

        return True

    except Exception as e:
        logger.error(f"✗ Single conversion failed: {e}", exc_info=True)
        return False


async def test_batch_conversion(converter, image_paths: list[str], format_style: str):
    """Test batch image conversion.

    Args:
        converter: Qwen markdown converter instance
        image_paths: List of paths to test images
        format_style: Format style to test
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"Testing BATCH conversion with format: {format_style}")
    logger.info(f"{'='*80}")

    try:
        # Encode images
        images_base64 = []
        for path in image_paths:
            image_base64 = encode_image_to_base64(path)
            images_base64.append(image_base64)
            logger.info(f"Loaded image: {path}")

        # Convert batch
        result = await converter.convert_batch(
            images_base64=images_base64,
            format_style=format_style,
        )

        # Display results
        logger.info(f"\nBatch Conversion Results:")
        logger.info(f"  Provider: {result.provider}")
        logger.info(f"  Model: {result.model}")
        logger.info(f"  Pages processed: {len(image_paths)}")
        logger.info(f"  Total input tokens: {result.input_tokens}")
        logger.info(f"  Total output tokens: {result.output_tokens}")
        logger.info(f"  Total tokens: {result.input_tokens + result.output_tokens}")
        logger.info(f"  Processing time: {result.processing_time_ms}ms")
        logger.info(f"  Avg time per page: {result.processing_time_ms // len(image_paths)}ms")
        logger.info(f"  Combined markdown length: {len(result.markdown_content)} chars")

        # Per-page breakdown
        if result.page_results:
            logger.info(f"\nPer-Page Breakdown:")
            for page_data in result.page_results:
                logger.info(
                    f"  Page {page_data['page']}: "
                    f"{page_data['input_tokens']}+{page_data['output_tokens']} tokens, "
                    f"{len(page_data['markdown'])} chars"
                )

        # Save to file
        output_file = f"test_output_batch_{format_style}.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result.markdown_content)
        logger.info(f"\n✓ Saved output to: {output_file}")

        # Show preview
        preview_lines = result.markdown_content.split("\n")[:15]
        logger.info(f"\nMarkdown Preview (first 15 lines):")
        for line in preview_lines:
            logger.info(f"  {line}")
        if len(result.markdown_content.split("\n")) > 15:
            logger.info(f"  ... ({len(result.markdown_content.split('\n')) - 15} more lines)")

        return True

    except Exception as e:
        logger.error(f"✗ Batch conversion failed: {e}", exc_info=True)
        return False


async def main():
    """Main test function."""
    logger.info("="*80)
    logger.info("Qwen Markdown Converter Test Suite")
    logger.info("="*80)

    # Check for test images
    test_images = []
    if len(sys.argv) > 1:
        # Use command-line arguments
        test_images = sys.argv[1:]
        logger.info(f"\nUsing {len(test_images)} image(s) from command line")
    else:
        # Look for default test images
        default_paths = [
            "test_invoice.jpg",
            "test_document.png",
            "invoice_1.jpg",
            "sample.png",
        ]
        for path in default_paths:
            if Path(path).exists():
                test_images.append(path)

        if not test_images:
            logger.error(
                "\n✗ No test images found. Please provide image path(s) as argument:"
                "\n  python test_qwen_markdown.py /path/to/image.jpg"
                "\n  python test_qwen_markdown.py image1.jpg image2.png"
            )
            return

        logger.info(f"\nFound {len(test_images)} test image(s): {test_images}")

    # Get converter factory
    try:
        factory = get_converter_factory()
        available = factory.list_available_converters()
        logger.info(f"\nAvailable converters: {available}")

        # Get Qwen converter
        converter = factory.get_markdown_converter("qwen_vision")
        logger.info("✓ Successfully loaded Qwen vision converter")

    except Exception as e:
        logger.error(f"✗ Failed to initialize converter: {e}")
        logger.error(
            "\nMake sure DASHSCOPE_API_KEY is set in your .env file:"
            "\n  DASHSCOPE_API_KEY=your_api_key_here"
        )
        return

    # Test formats
    formats_to_test = ["qwenvl_markdown", "qwenvl_html", "standard"]
    results = {}

    # Test single conversion with first image
    logger.info(f"\n{'#'*80}")
    logger.info("SINGLE IMAGE CONVERSION TESTS")
    logger.info(f"{'#'*80}")

    first_image = test_images[0]
    for format_style in formats_to_test:
        success = await test_single_conversion(converter, first_image, format_style)
        results[f"single_{format_style}"] = success

    # Test batch conversion if multiple images
    if len(test_images) > 1:
        logger.info(f"\n{'#'*80}")
        logger.info("BATCH CONVERSION TESTS")
        logger.info(f"{'#'*80}")

        for format_style in formats_to_test:
            success = await test_batch_conversion(converter, test_images, format_style)
            results[f"batch_{format_style}"] = success

    # Summary
    logger.info(f"\n{'='*80}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*80}")

    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)
    failed_tests = total_tests - passed_tests

    for test_name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"  {status}: {test_name}")

    logger.info(f"\nTotal: {total_tests} tests, {passed_tests} passed, {failed_tests} failed")

    if failed_tests == 0:
        logger.info("\n🎉 All tests passed!")
    else:
        logger.warning(f"\n⚠️  {failed_tests} test(s) failed")

    logger.info(f"\nOutput files:")
    for format_style in formats_to_test:
        logger.info(f"  - test_output_single_{format_style}.md")
        if len(test_images) > 1:
            logger.info(f"  - test_output_batch_{format_style}.md")


if __name__ == "__main__":
    asyncio.run(main())
