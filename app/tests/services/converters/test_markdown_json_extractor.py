"""Unit tests for markdown-to-JSON extractor.

Tests text-based extraction from markdown content with mocked API calls.
"""

import pytest
from unittest.mock import Mock, patch
import json

from app.services.converters.markdown_json_extractor import MarkdownJsonExtractor
from app.services.converters.base import MarkdownExtractionResult


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def gemini_extractor():
    """Create Gemini JSON extractor."""
    return MarkdownJsonExtractor(
        provider="google", model="gemini-2.0-flash-001", api_key="test_api_key"
    )


@pytest.fixture
def openai_extractor():
    """Create OpenAI JSON extractor."""
    return MarkdownJsonExtractor(
        provider="openai", model="gpt-4o-mini", api_key="test_api_key"
    )


@pytest.fixture
def mock_gemini_extraction_response(sample_extracted_invoice_data):
    """Mock Gemini extraction response."""
    mock_response = Mock()
    mock_response.text = json.dumps(sample_extracted_invoice_data)
    mock_response.usage_metadata = Mock()
    mock_response.usage_metadata.prompt_token_count = 500
    mock_response.usage_metadata.candidates_token_count = 100
    return mock_response


# ============================================================================
# Extraction Tests
# ============================================================================


class TestMarkdownJsonExtraction:
    """Tests for markdown-to-JSON extraction."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.markdown_json_extractor.genai.Client")
    async def test_extract_with_valid_schema(
        self,
        mock_client_class,
        gemini_extractor,
        sample_markdown_single_page,
        sample_invoice_schema,
        mock_gemini_extraction_response,
    ):
        """Test successful extraction with valid schema."""
        # Setup mock
        mock_client = Mock()
        mock_client.models.generate_content.return_value = (
            mock_gemini_extraction_response
        )
        gemini_extractor.client = mock_client

        # Extract
        result = await gemini_extractor.extract(
            markdown_content=sample_markdown_single_page,
            schema=sample_invoice_schema,
            custom_prompt="",
        )

        # Assertions
        assert isinstance(result, MarkdownExtractionResult)
        assert result.extracted_data is not None
        assert "invoice_number" in result.extracted_data
        assert result.input_tokens == 500
        assert result.output_tokens == 100
        assert result.processing_time_ms > 0
        assert result.provider == "google"
        assert result.model == "gemini-2.0-flash-001"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.markdown_json_extractor.genai.Client")
    async def test_extract_with_custom_prompt(
        self,
        mock_client_class,
        gemini_extractor,
        sample_markdown_single_page,
        sample_invoice_schema,
        mock_gemini_extraction_response,
    ):
        """Test extraction with custom prompt."""
        mock_client = Mock()
        mock_client.models.generate_content.return_value = (
            mock_gemini_extraction_response
        )
        gemini_extractor.client = mock_client

        custom_prompt = "Extract only the invoice number and total"

        result = await gemini_extractor.extract(
            markdown_content=sample_markdown_single_page,
            schema=sample_invoice_schema,
            custom_prompt=custom_prompt,
        )

        assert isinstance(result, MarkdownExtractionResult)
        # Verify API was called with custom prompt
        assert mock_client.models.generate_content.called

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.markdown_json_extractor.genai.Client")
    async def test_extract_with_page_markers(
        self,
        mock_client_class,
        gemini_extractor,
        sample_markdown_multi_page,
        sample_invoice_schema,
        mock_gemini_extraction_response,
    ):
        """Test extraction handles multi-page markdown with markers."""
        mock_client = Mock()
        mock_client.models.generate_content.return_value = (
            mock_gemini_extraction_response
        )
        gemini_extractor.client = mock_client

        result = await gemini_extractor.extract(
            markdown_content=sample_markdown_multi_page,
            schema=sample_invoice_schema,
            custom_prompt="",
        )

        assert isinstance(result, MarkdownExtractionResult)
        assert result.extracted_data is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.markdown_json_extractor.genai.Client")
    async def test_extract_schema_validation_pass(
        self,
        mock_client_class,
        gemini_extractor,
        sample_markdown_single_page,
        sample_invoice_schema,
        mock_gemini_extraction_response,
    ):
        """Test that valid JSON passes schema validation."""
        mock_client = Mock()
        mock_client.models.generate_content.return_value = (
            mock_gemini_extraction_response
        )
        gemini_extractor.client = mock_client

        result = await gemini_extractor.extract(
            markdown_content=sample_markdown_single_page,
            schema=sample_invoice_schema,
            custom_prompt="",
        )

        # Mock response should pass validation
        assert result.is_valid is True
        assert len(result.validation_errors) == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.markdown_json_extractor.genai.Client")
    async def test_extract_schema_validation_fail(
        self, mock_client_class, gemini_extractor, sample_markdown_single_page
    ):
        """Test that invalid JSON fails schema validation."""
        # Mock response with missing required fields
        mock_response = Mock()
        mock_response.text = json.dumps({"incomplete": "data"})
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 20

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        gemini_extractor.client = mock_client

        schema = {
            "type": "object",
            "properties": {"invoice_number": {"type": "string"}},
            "required": ["invoice_number"],
        }

        result = await gemini_extractor.extract(
            markdown_content=sample_markdown_single_page,
            schema=schema,
            custom_prompt="",
        )

        # Should fail validation due to missing required field
        assert result.is_valid is False
        assert len(result.validation_errors) > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.markdown_json_extractor.genai.Client")
    async def test_extract_malformed_json(
        self,
        mock_client_class,
        gemini_extractor,
        sample_markdown_single_page,
        sample_invoice_schema,
    ):
        """Test handling of malformed JSON response."""
        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.text = "This is not valid JSON"
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 20

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        gemini_extractor.client = mock_client

        with pytest.raises(Exception) as exc_info:
            await gemini_extractor.extract(
                markdown_content=sample_markdown_single_page,
                schema=sample_invoice_schema,
                custom_prompt="",
            )

        assert "json" in str(exc_info.value).lower() or "parse" in str(
            exc_info.value
        ).lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.markdown_json_extractor.genai.Client")
    async def test_extract_empty_markdown(
        self, mock_client_class, gemini_extractor, sample_invoice_schema
    ):
        """Test extraction from empty markdown."""
        mock_response = Mock()
        mock_response.text = "{}"
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 5

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        gemini_extractor.client = mock_client

        result = await gemini_extractor.extract(
            markdown_content="", schema=sample_invoice_schema, custom_prompt=""
        )

        assert isinstance(result, MarkdownExtractionResult)
        assert result.extracted_data == {}


# ============================================================================
# Provider-Specific Tests
# ============================================================================


class TestProviderSpecific:
    """Tests for different provider implementations."""

    @pytest.mark.unit
    def test_gemini_provider_initialization(self):
        """Test Gemini provider initialization."""
        extractor = MarkdownJsonExtractor(
            provider="google", model="gemini-2.0-flash-001", api_key="test_key"
        )

        assert extractor.provider == "google"
        assert extractor.model == "gemini-2.0-flash-001"

    @pytest.mark.unit
    def test_openai_provider_initialization(self):
        """Test OpenAI provider initialization."""
        extractor = MarkdownJsonExtractor(
            provider="openai", model="gpt-4o-mini", api_key="test_key"
        )

        assert extractor.provider == "openai"
        assert extractor.model == "gpt-4o-mini"

    @pytest.mark.unit
    def test_invalid_provider(self):
        """Test error on invalid provider."""
        with pytest.raises(ValueError) as exc_info:
            MarkdownJsonExtractor(
                provider="invalid", model="test", api_key="test_key"
            )

        assert "unsupported provider" in str(exc_info.value).lower()


# ============================================================================
# Token Counting Tests
# ============================================================================


class TestTokenCounting:
    """Tests for token usage tracking."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.markdown_json_extractor.genai.Client")
    async def test_token_counting(
        self,
        mock_client_class,
        gemini_extractor,
        sample_markdown_single_page,
        sample_invoice_schema,
        mock_gemini_extraction_response,
    ):
        """Test accurate token counting."""
        mock_client = Mock()
        mock_client.models.generate_content.return_value = (
            mock_gemini_extraction_response
        )
        gemini_extractor.client = mock_client

        result = await gemini_extractor.extract(
            markdown_content=sample_markdown_single_page,
            schema=sample_invoice_schema,
            custom_prompt="",
        )

        assert result.input_tokens == 500
        assert result.output_tokens == 100

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.converters.markdown_json_extractor.genai.Client")
    async def test_processing_time_tracking(
        self,
        mock_client_class,
        gemini_extractor,
        sample_markdown_single_page,
        sample_invoice_schema,
        mock_gemini_extraction_response,
    ):
        """Test processing time tracking."""
        mock_client = Mock()
        mock_client.models.generate_content.return_value = (
            mock_gemini_extraction_response
        )
        gemini_extractor.client = mock_client

        result = await gemini_extractor.extract(
            markdown_content=sample_markdown_single_page,
            schema=sample_invoice_schema,
            custom_prompt="",
        )

        assert result.processing_time_ms > 0
        assert result.processing_time_ms < 60000  # Less than 1 minute
