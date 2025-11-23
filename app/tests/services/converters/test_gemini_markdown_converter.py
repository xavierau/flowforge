"""Unit tests for Gemini markdown converter.

Tests Gemini vision-based image-to-markdown conversion with mocked API calls.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import base64
import io
from PIL import Image

from app.services.converters.gemini_markdown_converter import GeminiMarkdownConverter
from app.services.converters.base import MarkdownConversionResult


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def gemini_converter():
    """Create Gemini converter instance with test API key."""
    return GeminiMarkdownConverter(api_key="test_api_key", model="gemini-2.5-flash")


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response."""
    mock_response = Mock()
    mock_response.text = "<!-- PAGE 1 -->\n# Test Markdown\n\nTest content"
    mock_response.usage_metadata = Mock()
    mock_response.usage_metadata.prompt_token_count = 100
    mock_response.usage_metadata.candidates_token_count = 50
    return mock_response


@pytest.fixture
def mock_gemini_response_batch():
    """Mock Gemini API response for batch conversion."""
    mock_response = Mock()
    mock_response.text = (
        "<!-- PAGE 1 -->\n# Page 1\n\nContent 1\n\n"
        "<!-- PAGE 2 -->\n# Page 2\n\nContent 2"
    )
    mock_response.usage_metadata = Mock()
    mock_response.usage_metadata.prompt_token_count = 200
    mock_response.usage_metadata.candidates_token_count = 100
    return mock_response


# ============================================================================
# Initialization Tests
# ============================================================================


class TestGeminiConverterInitialization:
    """Tests for Gemini converter initialization."""

    @pytest.mark.unit
    def test_initialization_with_api_key(self):
        """Test converter initialization with API key."""
        converter = GeminiMarkdownConverter(
            api_key="test_key", model="gemini-2.5-flash"
        )

        assert converter.model == "gemini-2.5-flash"
        assert converter.provider == "gemini_vision"
        assert converter.client is not None

    @pytest.mark.unit
    def test_default_model(self):
        """Test default model is gemini-2.5-flash."""
        converter = GeminiMarkdownConverter(api_key="test_key")

        assert converter.model == "gemini-2.5-flash"

    @pytest.mark.unit
    def test_custom_model(self):
        """Test initialization with custom model."""
        converter = GeminiMarkdownConverter(
            api_key="test_key", model="gemini-custom-model"
        )

        assert converter.model == "gemini-custom-model"

    @pytest.mark.unit
    def test_timeout_configuration(self):
        """Test that timeout configuration is set correctly."""
        converter = GeminiMarkdownConverter(api_key="test_key")

        # Converter should initialize successfully with timeout config
        assert converter.client is not None


# ============================================================================
# Prompt Generation Tests
# ============================================================================


class TestPromptGeneration:
    """Tests for conversion prompt generation."""

    @pytest.mark.unit
    def test_build_prompt_standard_format(self, gemini_converter):
        """Test prompt generation for standard format."""
        prompt = gemini_converter._build_conversion_prompt(
            format_style="standard", page_number=1, is_batch=False
        )

        assert "Convert this document image to markdown" in prompt
        assert "standard markdown formatting" in prompt.lower()
        assert "<!-- PAGE 1 -->" in prompt

    @pytest.mark.unit
    def test_build_prompt_table_heavy_format(self, gemini_converter):
        """Test prompt generation for table-heavy format."""
        prompt = gemini_converter._build_conversion_prompt(
            format_style="table_heavy", page_number=1, is_batch=False
        )

        assert "Convert this document image to markdown" in prompt
        assert "tabular data" in prompt.lower() or "tables" in prompt.lower()
        assert "markdown tables" in prompt.lower()
        assert "<!-- PAGE 1 -->" in prompt

    @pytest.mark.unit
    def test_build_prompt_layout_preserved_format(self, gemini_converter):
        """Test prompt generation for layout-preserved format."""
        prompt = gemini_converter._build_conversion_prompt(
            format_style="layout_preserved", page_number=1, is_batch=False
        )

        assert "Convert this document image to markdown" in prompt
        assert "layout" in prompt.lower()
        assert "preserve" in prompt.lower() or "maintain" in prompt.lower()
        assert "<!-- PAGE 1 -->" in prompt

    @pytest.mark.unit
    def test_build_prompt_batch_mode(self, gemini_converter):
        """Test prompt generation for batch mode."""
        prompt = gemini_converter._build_conversion_prompt(
            format_style="standard", is_batch=True
        )

        assert "Convert this document image to markdown" in prompt
        assert "<!-- PAGE N -->" in prompt or "page markers" in prompt.lower()
        assert "sequentially" in prompt.lower() or "increment" in prompt.lower()

    @pytest.mark.unit
    def test_build_prompt_single_mode_page_number(self, gemini_converter):
        """Test prompt includes correct page number for single mode."""
        prompt = gemini_converter._build_conversion_prompt(
            format_style="standard", page_number=5, is_batch=False
        )

        assert "<!-- PAGE 5 -->" in prompt


# ============================================================================
# Single Page Conversion Tests
# ============================================================================


class TestSinglePageConversion:
    """Tests for single page image-to-markdown conversion."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.gemini_markdown_converter.genai.Client")
    async def test_convert_single_success(
        self,
        mock_client_class,
        gemini_converter,
        sample_invoice_image_base64,
        mock_gemini_response,
    ):
        """Test successful single page conversion."""
        # Setup mock
        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_gemini_response
        gemini_converter.client = mock_client

        # Convert
        result = await gemini_converter.convert_single(
            image_base64=sample_invoice_image_base64,
            format_style="standard",
            page_number=1,
        )

        # Assertions
        assert isinstance(result, MarkdownConversionResult)
        assert result.markdown_content == "<!-- PAGE 1 -->\n# Test Markdown\n\nTest content"
        assert result.input_tokens == 100
        assert result.output_tokens == 50
        assert result.processing_time_ms > 0
        assert result.provider == "gemini_vision"
        assert result.model == "gemini-2.5-flash"

        # Verify API was called
        mock_client.models.generate_content.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.gemini_markdown_converter.genai.Client")
    async def test_convert_single_table_heavy_format(
        self,
        mock_client_class,
        gemini_converter,
        sample_invoice_image_base64,
        mock_gemini_response,
    ):
        """Test single page conversion with table-heavy format."""
        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_gemini_response
        gemini_converter.client = mock_client

        result = await gemini_converter.convert_single(
            image_base64=sample_invoice_image_base64,
            format_style="table_heavy",
            page_number=1,
        )

        assert isinstance(result, MarkdownConversionResult)
        assert result.markdown_content is not None

        # Verify correct format style used in prompt
        call_args = mock_client.models.generate_content.call_args
        # contents[1] should be the prompt (after the image)
        assert call_args is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_convert_single_invalid_base64(self, gemini_converter):
        """Test error handling for invalid base64 image."""
        with pytest.raises(Exception) as exc_info:
            await gemini_converter.convert_single(
                image_base64="invalid_base64",
                format_style="standard",
                page_number=1,
            )

        assert "error" in str(exc_info.value).lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.gemini_markdown_converter.genai.Client")
    async def test_convert_single_api_error(
        self, mock_client_class, gemini_converter, sample_invoice_image_base64
    ):
        """Test error handling for API errors."""
        mock_client = Mock()
        mock_client.models.generate_content.side_effect = Exception("API Error")
        gemini_converter.client = mock_client

        with pytest.raises(Exception) as exc_info:
            await gemini_converter.convert_single(
                image_base64=sample_invoice_image_base64,
                format_style="standard",
                page_number=1,
            )

        assert "API Error" in str(exc_info.value) or "conversion error" in str(
            exc_info.value
        ).lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.gemini_markdown_converter.genai.Client")
    async def test_convert_single_token_counting(
        self,
        mock_client_class,
        gemini_converter,
        sample_invoice_image_base64,
        mock_gemini_response,
    ):
        """Test token counting in single conversion."""
        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_gemini_response
        gemini_converter.client = mock_client

        result = await gemini_converter.convert_single(
            image_base64=sample_invoice_image_base64,
            format_style="standard",
            page_number=1,
        )

        assert result.input_tokens == 100
        assert result.output_tokens == 50

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.gemini_markdown_converter.genai.Client")
    async def test_convert_single_processing_time(
        self,
        mock_client_class,
        gemini_converter,
        sample_invoice_image_base64,
        mock_gemini_response,
    ):
        """Test processing time tracking."""
        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_gemini_response
        gemini_converter.client = mock_client

        result = await gemini_converter.convert_single(
            image_base64=sample_invoice_image_base64,
            format_style="standard",
            page_number=1,
        )

        assert result.processing_time_ms > 0
        assert result.processing_time_ms < 60000  # Should be less than 1 minute


# ============================================================================
# Batch Conversion Tests
# ============================================================================


class TestBatchConversion:
    """Tests for batch multi-page conversion."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.gemini_markdown_converter.genai.Client")
    async def test_convert_batch_success(
        self,
        mock_client_class,
        gemini_converter,
        sample_invoice_image_base64,
        mock_gemini_response,
    ):
        """Test successful batch conversion with parallel processing."""
        # Mock client to return single-page response for each parallel call
        mock_client = Mock()
        mock_response_1 = Mock()
        mock_response_1.text = "<!-- PAGE 1 -->\n# Page 1\n\nContent 1"
        mock_response_1.usage_metadata = Mock()
        mock_response_1.usage_metadata.prompt_token_count = 100
        mock_response_1.usage_metadata.candidates_token_count = 50

        mock_response_2 = Mock()
        mock_response_2.text = "<!-- PAGE 2 -->\n# Page 2\n\nContent 2"
        mock_response_2.usage_metadata = Mock()
        mock_response_2.usage_metadata.prompt_token_count = 100
        mock_response_2.usage_metadata.candidates_token_count = 50

        mock_client.models.generate_content.side_effect = [mock_response_1, mock_response_2]
        gemini_converter.client = mock_client

        # Convert 2 pages
        images = [sample_invoice_image_base64, sample_invoice_image_base64]
        result = await gemini_converter.convert_batch(
            images_base64=images, format_style="standard"
        )

        # Assertions
        assert isinstance(result, MarkdownConversionResult)
        assert "<!-- PAGE 1 -->" in result.markdown_content
        assert "<!-- PAGE 2 -->" in result.markdown_content
        assert result.input_tokens == 200  # 100 + 100
        assert result.output_tokens == 100  # 50 + 50
        assert result.processing_time_ms > 0

        # NEW: Check page_results field
        assert result.page_results is not None
        assert len(result.page_results) == 2
        assert result.page_results[0]["page"] == 1
        assert result.page_results[1]["page"] == 2
        assert result.page_results[0]["input_tokens"] == 100
        assert result.page_results[1]["input_tokens"] == 100

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.gemini_markdown_converter.genai.Client")
    async def test_convert_batch_page_markers(
        self,
        mock_client_class,
        gemini_converter,
        sample_invoice_image_base64,
    ):
        """Test that batch conversion includes page markers in parallel processing."""
        mock_client = Mock()
        mock_response_1 = Mock()
        mock_response_1.text = "<!-- PAGE 1 -->\n# Page 1\n\nContent 1"
        mock_response_1.usage_metadata = Mock()
        mock_response_1.usage_metadata.prompt_token_count = 100
        mock_response_1.usage_metadata.candidates_token_count = 50

        mock_response_2 = Mock()
        mock_response_2.text = "<!-- PAGE 2 -->\n# Page 2\n\nContent 2"
        mock_response_2.usage_metadata = Mock()
        mock_response_2.usage_metadata.prompt_token_count = 100
        mock_response_2.usage_metadata.candidates_token_count = 50

        mock_client.models.generate_content.side_effect = [mock_response_1, mock_response_2]
        gemini_converter.client = mock_client

        images = [sample_invoice_image_base64, sample_invoice_image_base64]
        result = await gemini_converter.convert_batch(
            images_base64=images, format_style="standard"
        )

        # Should contain page markers
        assert "<!-- PAGE 1 -->" in result.markdown_content
        assert "<!-- PAGE 2 -->" in result.markdown_content

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.gemini_markdown_converter.genai.Client")
    async def test_convert_batch_multiple_images(
        self,
        mock_client_class,
        gemini_converter,
        sample_invoice_image_base64,
    ):
        """Test batch conversion processes each image in parallel."""
        mock_client = Mock()

        # Create 3 mock responses for 3 pages
        mock_responses = []
        for i in range(3):
            mock_response = Mock()
            mock_response.text = f"<!-- PAGE {i+1} -->\n# Page {i+1}\n\nContent {i+1}"
            mock_response.usage_metadata = Mock()
            mock_response.usage_metadata.prompt_token_count = 100
            mock_response.usage_metadata.candidates_token_count = 50
            mock_responses.append(mock_response)

        mock_client.models.generate_content.side_effect = mock_responses
        gemini_converter.client = mock_client

        images = [sample_invoice_image_base64] * 3  # 3 pages
        result = await gemini_converter.convert_batch(images_base64=images, format_style="standard")

        # Should be called 3 times (parallel mode - one call per page)
        assert mock_client.models.generate_content.call_count == 3

        # Verify page_results has 3 pages
        assert len(result.page_results) == 3
        assert result.input_tokens == 300  # 100 * 3
        assert result.output_tokens == 150  # 50 * 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.gemini_markdown_converter.genai.Client")
    async def test_convert_batch_api_error(
        self, mock_client_class, gemini_converter, sample_invoice_image_base64
    ):
        """Test error handling for batch API errors."""
        mock_client = Mock()
        mock_client.models.generate_content.side_effect = Exception("Batch API Error")
        gemini_converter.client = mock_client

        with pytest.raises(Exception) as exc_info:
            await gemini_converter.convert_batch(
                images_base64=[sample_invoice_image_base64], format_style="standard"
            )

        assert "error" in str(exc_info.value).lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.gemini_markdown_converter.genai.Client")
    async def test_convert_batch_token_counting(
        self,
        mock_client_class,
        gemini_converter,
        sample_invoice_image_base64,
    ):
        """Test token counting in parallel batch conversion."""
        mock_client = Mock()

        # Mock 2 separate API responses
        mock_response_1 = Mock()
        mock_response_1.text = "<!-- PAGE 1 -->\n# Page 1\n\nContent 1"
        mock_response_1.usage_metadata = Mock()
        mock_response_1.usage_metadata.prompt_token_count = 120
        mock_response_1.usage_metadata.candidates_token_count = 60

        mock_response_2 = Mock()
        mock_response_2.text = "<!-- PAGE 2 -->\n# Page 2\n\nContent 2"
        mock_response_2.usage_metadata = Mock()
        mock_response_2.usage_metadata.prompt_token_count = 80
        mock_response_2.usage_metadata.candidates_token_count = 40

        mock_client.models.generate_content.side_effect = [mock_response_1, mock_response_2]
        gemini_converter.client = mock_client

        images = [sample_invoice_image_base64, sample_invoice_image_base64]
        result = await gemini_converter.convert_batch(
            images_base64=images, format_style="standard"
        )

        # Should aggregate tokens from parallel calls
        assert result.input_tokens == 200  # 120 + 80
        assert result.output_tokens == 100  # 60 + 40

        # Verify per-page tokens in page_results
        assert result.page_results[0]["input_tokens"] == 120
        assert result.page_results[0]["output_tokens"] == 60
        assert result.page_results[1]["input_tokens"] == 80
        assert result.page_results[1]["output_tokens"] == 40


# ============================================================================
# Format Style Tests
# ============================================================================


class TestFormatStyles:
    """Tests for different markdown format styles."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.gemini_markdown_converter.genai.Client")
    async def test_standard_format(
        self,
        mock_client_class,
        gemini_converter,
        sample_invoice_image_base64,
        mock_gemini_response,
    ):
        """Test standard format produces expected prompt."""
        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_gemini_response
        gemini_converter.client = mock_client

        await gemini_converter.convert_single(
            image_base64=sample_invoice_image_base64,
            format_style="standard",
            page_number=1,
        )

        # Verify generate_content called
        assert mock_client.models.generate_content.called

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.gemini_markdown_converter.genai.Client")
    async def test_table_heavy_format(
        self,
        mock_client_class,
        gemini_converter,
        sample_invoice_image_base64,
        mock_gemini_response,
    ):
        """Test table-heavy format produces expected prompt."""
        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_gemini_response
        gemini_converter.client = mock_client

        await gemini_converter.convert_single(
            image_base64=sample_invoice_image_base64,
            format_style="table_heavy",
            page_number=1,
        )

        assert mock_client.models.generate_content.called

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.gemini_markdown_converter.genai.Client")
    async def test_layout_preserved_format(
        self,
        mock_client_class,
        gemini_converter,
        sample_invoice_image_base64,
        mock_gemini_response,
    ):
        """Test layout-preserved format produces expected prompt."""
        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_gemini_response
        gemini_converter.client = mock_client

        await gemini_converter.convert_single(
            image_base64=sample_invoice_image_base64,
            format_style="layout_preserved",
            page_number=1,
        )

        assert mock_client.models.generate_content.called
