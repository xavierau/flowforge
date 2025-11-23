"""Unit tests for converter base interfaces and dataclasses.

Tests the abstract interfaces and dataclass contracts for the markdown pipeline.
"""

import pytest
from abc import ABC

from app.services.converters.base import (
    IImageToMarkdownConverter,
    IMarkdownToJsonExtractor,
    MarkdownConversionResult,
    MarkdownExtractionResult,
)


# ============================================================================
# Dataclass Tests
# ============================================================================


class TestMarkdownConversionResult:
    """Tests for MarkdownConversionResult dataclass."""

    @pytest.mark.unit
    def test_creation_with_valid_data(self):
        """Test creating result with all required fields."""
        result = MarkdownConversionResult(
            markdown_content="# Test Markdown",
            input_tokens=100,
            output_tokens=50,
            processing_time_ms=1500,
            provider="gemini_vision",
            model="gemini-2.5-flash",
        )

        assert result.markdown_content == "# Test Markdown"
        assert result.input_tokens == 100
        assert result.output_tokens == 50
        assert result.processing_time_ms == 1500
        assert result.provider == "gemini_vision"
        assert result.model == "gemini-2.5-flash"

    @pytest.mark.unit
    def test_field_types(self):
        """Test that field types are enforced."""
        result = MarkdownConversionResult(
            markdown_content="test",
            input_tokens=10,
            output_tokens=5,
            processing_time_ms=100,
            provider="gemini_vision",
            model="gemini-2.5-flash",
        )

        assert isinstance(result.markdown_content, str)
        assert isinstance(result.input_tokens, int)
        assert isinstance(result.output_tokens, int)
        assert isinstance(result.processing_time_ms, int)
        assert isinstance(result.provider, str)
        assert isinstance(result.model, str)

    @pytest.mark.unit
    def test_empty_markdown_content_allowed(self):
        """Test that empty markdown content is allowed."""
        result = MarkdownConversionResult(
            markdown_content="",
            input_tokens=0,
            output_tokens=0,
            processing_time_ms=0,
            provider="test",
            model="test",
        )

        assert result.markdown_content == ""

    @pytest.mark.unit
    def test_equality(self):
        """Test dataclass equality comparison."""
        result1 = MarkdownConversionResult(
            markdown_content="test",
            input_tokens=10,
            output_tokens=5,
            processing_time_ms=100,
            provider="gemini_vision",
            model="gemini-2.5-flash",
        )
        result2 = MarkdownConversionResult(
            markdown_content="test",
            input_tokens=10,
            output_tokens=5,
            processing_time_ms=100,
            provider="gemini_vision",
            model="gemini-2.5-flash",
        )

        assert result1 == result2


class TestMarkdownExtractionResult:
    """Tests for MarkdownExtractionResult dataclass."""

    @pytest.mark.unit
    def test_creation_with_valid_data(self):
        """Test creating result with all required fields."""
        result = MarkdownExtractionResult(
            extracted_data={"invoice_number": "INV-001", "total": 100.0},
            input_tokens=200,
            output_tokens=50,
            processing_time_ms=2000,
            provider="google",
            model="gemini-2.0-flash-001",
            is_valid=True,
            validation_errors=[],
        )

        assert result.extracted_data == {"invoice_number": "INV-001", "total": 100.0}
        assert result.input_tokens == 200
        assert result.output_tokens == 50
        assert result.processing_time_ms == 2000
        assert result.provider == "google"
        assert result.model == "gemini-2.0-flash-001"
        assert result.is_valid is True
        assert result.validation_errors == []

    @pytest.mark.unit
    def test_creation_with_validation_errors(self):
        """Test creating result with validation errors."""
        result = MarkdownExtractionResult(
            extracted_data={},
            input_tokens=100,
            output_tokens=20,
            processing_time_ms=1000,
            provider="google",
            model="gemini-2.0-flash-001",
            is_valid=False,
            validation_errors=["Missing required field: invoice_number"],
        )

        assert result.is_valid is False
        assert len(result.validation_errors) == 1
        assert "invoice_number" in result.validation_errors[0]

    @pytest.mark.unit
    def test_field_types(self):
        """Test that field types are enforced."""
        result = MarkdownExtractionResult(
            extracted_data={"test": "value"},
            input_tokens=10,
            output_tokens=5,
            processing_time_ms=100,
            provider="google",
            model="test",
            is_valid=True,
            validation_errors=[],
        )

        assert isinstance(result.extracted_data, dict)
        assert isinstance(result.input_tokens, int)
        assert isinstance(result.output_tokens, int)
        assert isinstance(result.processing_time_ms, int)
        assert isinstance(result.provider, str)
        assert isinstance(result.model, str)
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.validation_errors, list)

    @pytest.mark.unit
    def test_empty_extracted_data_allowed(self):
        """Test that empty extracted data is allowed."""
        result = MarkdownExtractionResult(
            extracted_data={},
            input_tokens=0,
            output_tokens=0,
            processing_time_ms=0,
            provider="test",
            model="test",
            is_valid=False,
            validation_errors=["Empty extraction"],
        )

        assert result.extracted_data == {}
        assert not result.is_valid


# ============================================================================
# Interface Tests
# ============================================================================


class TestImageToMarkdownConverterInterface:
    """Tests for IImageToMarkdownConverter abstract interface."""

    @pytest.mark.unit
    def test_cannot_instantiate_interface(self):
        """Test that abstract interface cannot be instantiated."""
        with pytest.raises(TypeError) as exc_info:
            IImageToMarkdownConverter()

        assert "abstract" in str(exc_info.value).lower()

    @pytest.mark.unit
    def test_interface_is_abstract_base_class(self):
        """Test that interface inherits from ABC."""
        assert issubclass(IImageToMarkdownConverter, ABC)

    @pytest.mark.unit
    def test_interface_defines_convert_single(self):
        """Test that interface defines convert_single method."""
        assert hasattr(IImageToMarkdownConverter, "convert_single")

    @pytest.mark.unit
    def test_interface_defines_convert_batch(self):
        """Test that interface defines convert_batch method."""
        assert hasattr(IImageToMarkdownConverter, "convert_batch")

    @pytest.mark.unit
    def test_concrete_implementation_must_implement_all_methods(self):
        """Test that concrete implementations must implement all abstract methods."""

        # Missing convert_single
        class IncompleteConverter1(IImageToMarkdownConverter):
            async def convert_batch(self, images_base64, format_style="standard"):
                pass

        with pytest.raises(TypeError):
            IncompleteConverter1()

        # Missing convert_batch
        class IncompleteConverter2(IImageToMarkdownConverter):
            async def convert_single(
                self, image_base64, format_style="standard", page_number=1
            ):
                pass

        with pytest.raises(TypeError):
            IncompleteConverter2()

    @pytest.mark.unit
    def test_concrete_implementation_works_when_complete(self):
        """Test that concrete implementation can be instantiated when complete."""

        class CompleteConverter(IImageToMarkdownConverter):
            async def convert_single(
                self, image_base64, format_style="standard", page_number=1
            ):
                return MarkdownConversionResult(
                    markdown_content="test",
                    input_tokens=10,
                    output_tokens=5,
                    processing_time_ms=100,
                    provider="test",
                    model="test",
                )

            async def convert_batch(self, images_base64, format_style="standard"):
                return MarkdownConversionResult(
                    markdown_content="test",
                    input_tokens=20,
                    output_tokens=10,
                    processing_time_ms=200,
                    provider="test",
                    model="test",
                )

        # Should not raise
        converter = CompleteConverter()
        assert converter is not None


class TestMarkdownToJsonExtractorInterface:
    """Tests for IMarkdownToJsonExtractor abstract interface."""

    @pytest.mark.unit
    def test_cannot_instantiate_interface(self):
        """Test that abstract interface cannot be instantiated."""
        with pytest.raises(TypeError) as exc_info:
            IMarkdownToJsonExtractor()

        assert "abstract" in str(exc_info.value).lower()

    @pytest.mark.unit
    def test_interface_is_abstract_base_class(self):
        """Test that interface inherits from ABC."""
        assert issubclass(IMarkdownToJsonExtractor, ABC)

    @pytest.mark.unit
    def test_interface_defines_extract(self):
        """Test that interface defines extract method."""
        assert hasattr(IMarkdownToJsonExtractor, "extract")

    @pytest.mark.unit
    def test_concrete_implementation_must_implement_extract(self):
        """Test that concrete implementations must implement extract method."""

        class IncompleteExtractor(IMarkdownToJsonExtractor):
            pass

        with pytest.raises(TypeError):
            IncompleteExtractor()

    @pytest.mark.unit
    def test_concrete_implementation_works_when_complete(self):
        """Test that concrete implementation can be instantiated when complete."""

        class CompleteExtractor(IMarkdownToJsonExtractor):
            async def extract(self, markdown_content, schema, custom_prompt=""):
                return MarkdownExtractionResult(
                    extracted_data={},
                    input_tokens=10,
                    output_tokens=5,
                    processing_time_ms=100,
                    provider="test",
                    model="test",
                    is_valid=True,
                    validation_errors=[],
                )

        # Should not raise
        extractor = CompleteExtractor()
        assert extractor is not None
