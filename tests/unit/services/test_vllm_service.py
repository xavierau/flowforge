"""Unit tests for VLLM Service.

Tests provider selection, confidence scoring, value meaningfulness,
and extraction functionality.
"""

import pytest
import json
import base64
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Any

from app.services.vllm_service import (
    VLLMService,
    VLLMProvider,
    GeminiVLLMProvider,
    OpenAIVLLMProvider,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_settings():
    """Mock settings with API keys configured."""
    with patch("app.services.vllm_service.settings") as mock:
        mock.openai_api_key = "test-openai-key"
        mock.google_api_key = "test-google-key"
        yield mock


@pytest.fixture
def mock_settings_no_keys():
    """Mock settings without any API keys configured."""
    with patch("app.services.vllm_service.settings") as mock:
        mock.openai_api_key = ""
        mock.google_api_key = ""
        yield mock


@pytest.fixture
def mock_settings_google_only():
    """Mock settings with only Google API key configured."""
    with patch("app.services.vllm_service.settings") as mock:
        mock.openai_api_key = ""
        mock.google_api_key = "test-google-key"
        yield mock


@pytest.fixture
def mock_settings_openai_only():
    """Mock settings with only OpenAI API key configured."""
    with patch("app.services.vllm_service.settings") as mock:
        mock.openai_api_key = "test-openai-key"
        mock.google_api_key = ""
        yield mock


@pytest.fixture
def valid_schema():
    """Valid JSON schema for testing."""
    return {
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string"},
            "date": {"type": "string"},
            "total": {"type": "number"},
            "vendor": {"type": "string"},
            "line_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "amount": {"type": "number"},
                    },
                },
            },
        },
        "required": ["invoice_number", "total"],
    }


@pytest.fixture
def valid_schema_with_metadata():
    """Valid JSON schema with $schema and $id metadata."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://example.com/invoice.schema.json",
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string"},
            "total": {"type": "number"},
        },
        "required": ["invoice_number"],
    }


@pytest.fixture
def sample_base64_image():
    """Create a minimal valid base64 encoded PNG image."""
    # Minimal 1x1 red PNG
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
        b"\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01"
        b"\x00\x05\xfeT\xdc\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return base64.b64encode(png_bytes).decode("utf-8")


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = '{"invoice_number": "INV-001", "total": 100.0}'
    mock_response.usage = Mock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = '{"invoice_number": "INV-001", "total": 100.0}'
    mock_response.usage_metadata = Mock()
    mock_response.usage_metadata.prompt_token_count = 100
    mock_response.usage_metadata.candidates_token_count = 50
    mock_client.models.generate_content.return_value = mock_response
    return mock_client


# =============================================================================
# TestProviderSelection
# =============================================================================


class TestProviderSelection:
    """Tests for VLLM provider initialization and selection."""

    def test_valid_provider_google(self, mock_settings_google_only):
        """Verify Google provider initializes correctly when API key is present."""
        with patch("app.services.vllm_service.genai"):
            service = VLLMService()
            assert "google" in service.providers
            assert isinstance(service.providers["google"], GeminiVLLMProvider)

    def test_valid_provider_openai(self, mock_settings_openai_only):
        """Verify OpenAI provider initializes correctly when API key is present."""
        with patch("app.services.vllm_service.OpenAI"):
            service = VLLMService()
            assert "openai" in service.providers
            assert isinstance(service.providers["openai"], OpenAIVLLMProvider)

    def test_invalid_provider(self, mock_settings):
        """Verify invalid provider raises appropriate error."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()
            with pytest.raises(ValueError) as exc_info:
                service.get_provider("invalid_provider")
            assert "Provider 'invalid_provider' not configured" in str(exc_info.value)
            assert "Available:" in str(exc_info.value)

    def test_provider_initialization_without_api_key(self, mock_settings_no_keys):
        """Verify behavior when no API keys are configured."""
        service = VLLMService()
        assert len(service.providers) == 0
        with pytest.raises(ValueError) as exc_info:
            service.get_provider("google")
        assert "not configured" in str(exc_info.value)

    def test_both_providers_initialized(self, mock_settings):
        """Verify both providers are initialized when both keys are present."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()
            assert "google" in service.providers
            assert "openai" in service.providers
            assert len(service.providers) == 2

    def test_get_provider_returns_correct_instance(self, mock_settings):
        """Verify get_provider returns the correct provider instance."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()
            google_provider = service.get_provider("google")
            openai_provider = service.get_provider("openai")
            assert isinstance(google_provider, GeminiVLLMProvider)
            assert isinstance(openai_provider, OpenAIVLLMProvider)


# =============================================================================
# TestConfidenceScoring
# =============================================================================


class TestConfidenceScoring:
    """Tests for confidence score calculation."""

    def test_schema_validity_score_valid(self, mock_settings, valid_schema):
        """Test confidence calculation when data is valid against schema."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()
            extracted_data = {
                "invoice_number": "INV-001",
                "total": 100.0,
                "date": "2024-01-15",
                "vendor": "Test Corp",
            }
            score = service._calculate_confidence_score(
                extracted_data=extracted_data, schema=valid_schema, is_valid=True
            )
            # With is_valid=True, validity component contributes positively
            assert 0.0 <= score <= 1.0
            assert score > 0.5  # Should be reasonably high with valid data

    def test_schema_validity_score_invalid(self, mock_settings, valid_schema):
        """Test confidence score penalty when data is invalid against schema."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()
            extracted_data = {"invoice_number": "INV-001", "total": 100.0}
            score_invalid = service._calculate_confidence_score(
                extracted_data=extracted_data, schema=valid_schema, is_valid=False
            )
            score_valid = service._calculate_confidence_score(
                extracted_data=extracted_data, schema=valid_schema, is_valid=True
            )
            # Invalid data should have lower score than valid data
            assert score_invalid < score_valid

    def test_coverage_score_calculation(self, mock_settings, valid_schema):
        """Test field coverage scoring - required fields present."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()

            # All required fields present
            full_data = {"invoice_number": "INV-001", "total": 100.0}
            coverage_full = service._calculate_coverage_score(full_data, valid_schema)
            assert coverage_full == 1.0

            # Missing one required field
            partial_data = {"invoice_number": "INV-001"}
            coverage_partial = service._calculate_coverage_score(
                partial_data, valid_schema
            )
            assert coverage_partial == 0.5

            # Missing all required fields
            empty_data: dict[str, Any] = {}
            coverage_empty = service._calculate_coverage_score(empty_data, valid_schema)
            assert coverage_empty == 0.0

    def test_completeness_score(self, mock_settings, valid_schema):
        """Test data completeness evaluation."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()

            # All properties have meaningful values
            complete_data = {
                "invoice_number": "INV-001",
                "date": "2024-01-15",
                "total": 100.0,
                "vendor": "Test Corp",
                "line_items": [{"description": "Item 1", "amount": 100.0}],
            }
            completeness = service._calculate_completeness_score(
                complete_data, valid_schema
            )
            assert completeness == 1.0

            # Some properties are None or empty
            partial_data = {
                "invoice_number": "INV-001",
                "date": None,
                "total": 100.0,
                "vendor": "",
                "line_items": [],
            }
            completeness_partial = service._calculate_completeness_score(
                partial_data, valid_schema
            )
            assert completeness_partial < 1.0

    def test_confidence_with_empty_data(self, mock_settings, valid_schema):
        """Test score when extracted data is empty."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()
            empty_data: dict[str, Any] = {}
            score = service._calculate_confidence_score(
                extracted_data=empty_data, schema=valid_schema, is_valid=False
            )
            # Empty data should have low confidence
            assert score < 0.5

    def test_confidence_with_partial_data(self, mock_settings, valid_schema):
        """Test score with partially filled data."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()
            partial_data = {"invoice_number": "INV-001", "total": None}
            score = service._calculate_confidence_score(
                extracted_data=partial_data, schema=valid_schema, is_valid=False
            )
            # Partial data with None values should have moderate-low score
            assert 0.0 < score < 0.8

    def test_coverage_score_no_required_fields(self, mock_settings):
        """Test coverage score when schema has no required fields."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()
            schema_no_required = {
                "type": "object",
                "properties": {"field1": {"type": "string"}},
            }
            data = {"field1": "value"}
            coverage = service._calculate_coverage_score(data, schema_no_required)
            # When no required fields, it uses properties keys
            assert coverage == 1.0

    def test_coverage_score_no_properties(self, mock_settings):
        """Test coverage score when schema has no properties."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()
            schema_no_props: dict[str, Any] = {"type": "object"}
            data = {"any_field": "value"}
            coverage = service._calculate_coverage_score(data, schema_no_props)
            assert coverage == 1.0  # No fields to check means 100% coverage


# =============================================================================
# TestValueMeaningfulness
# =============================================================================


class TestValueMeaningfulness:
    """Tests for _is_value_meaningful helper method."""

    def test_none_value_not_meaningful(self, mock_settings):
        """None values should not be meaningful."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()
            assert service._is_value_meaningful(None) is False

    def test_empty_string_not_meaningful(self, mock_settings):
        """Empty strings should not be meaningful."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()
            assert service._is_value_meaningful("") is False
            assert service._is_value_meaningful("   ") is False

    def test_empty_collection_not_meaningful(self, mock_settings):
        """Empty lists and dicts should not be meaningful."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()
            assert service._is_value_meaningful([]) is False
            assert service._is_value_meaningful({}) is False

    def test_valid_string_meaningful(self, mock_settings):
        """Non-empty strings should be meaningful."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()
            assert service._is_value_meaningful("hello") is True
            assert service._is_value_meaningful("INV-001") is True
            assert service._is_value_meaningful("a") is True

    def test_valid_number_meaningful(self, mock_settings):
        """Numbers should be meaningful."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()
            assert service._is_value_meaningful(100) is True
            assert service._is_value_meaningful(99.99) is True
            assert service._is_value_meaningful(-50) is True

    def test_zero_is_meaningful(self, mock_settings):
        """Zero should be meaningful (it's a valid value, not missing data)."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()
            assert service._is_value_meaningful(0) is True
            assert service._is_value_meaningful(0.0) is True

    def test_boolean_meaningful(self, mock_settings):
        """Boolean values should be meaningful."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()
            assert service._is_value_meaningful(True) is True
            assert service._is_value_meaningful(False) is True

    def test_non_empty_collection_meaningful(self, mock_settings):
        """Non-empty lists and dicts should be meaningful."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()
            assert service._is_value_meaningful(["item"]) is True
            assert service._is_value_meaningful({"key": "value"}) is True


# =============================================================================
# TestExtraction
# =============================================================================


class TestExtraction:
    """Tests for extraction functionality."""

    @pytest.mark.asyncio
    async def test_extract_single_image_success(
        self, mock_settings, valid_schema, sample_base64_image
    ):
        """Mock successful single image extraction."""
        with patch("app.services.vllm_service.genai") as mock_genai, patch(
            "app.services.vllm_service.OpenAI"
        ), patch("PIL.Image.open") as mock_pil:
            # Setup mock Gemini response
            mock_response = Mock()
            mock_response.text = '{"invoice_number": "INV-001", "total": 250.0}'
            mock_response.usage_metadata = Mock()
            mock_response.usage_metadata.prompt_token_count = 150
            mock_response.usage_metadata.candidates_token_count = 75

            mock_client = Mock()
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client

            # Setup mock PIL
            mock_pil.return_value = Mock()

            service = VLLMService()
            result = await service.extract_from_image(
                image_base64=sample_base64_image,
                schema=valid_schema,
                custom_prompt="Extract invoice data",
                provider="google",
                model="gemini-2.5-flash",
            )

            assert result["extracted_data"]["invoice_number"] == "INV-001"
            assert result["extracted_data"]["total"] == 250.0
            assert result["input_tokens"] == 150
            assert result["output_tokens"] == 75
            assert result["tokens_used"] == 225
            assert "confidence_score" in result
            assert "is_valid" in result
            assert "model_used" in result
            assert result["model_used"] == "google/gemini-2.5-flash"

    @pytest.mark.asyncio
    async def test_extract_batch_success(
        self, mock_settings, valid_schema, sample_base64_image
    ):
        """Mock successful batch extraction with multiple images."""
        with patch("app.services.vllm_service.genai") as mock_genai, patch(
            "app.services.vllm_service.OpenAI"
        ), patch("PIL.Image.open") as mock_pil:
            # Setup mock Gemini response
            mock_response = Mock()
            mock_response.text = json.dumps(
                {
                    "invoice_number": "INV-BATCH-001",
                    "total": 500.0,
                    "vendor": "Multi-Page Corp",
                }
            )
            mock_response.usage_metadata = Mock()
            mock_response.usage_metadata.prompt_token_count = 500
            mock_response.usage_metadata.candidates_token_count = 100

            mock_client = Mock()
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client

            # Setup mock PIL
            mock_pil.return_value = Mock()

            service = VLLMService()
            images = [sample_base64_image, sample_base64_image, sample_base64_image]
            result = await service.extract_from_images_batch(
                images_base64=images,
                schema=valid_schema,
                custom_prompt="Extract from multi-page invoice",
                provider="google",
                model="gemini-2.5-flash",
            )

            assert result["extracted_data"]["invoice_number"] == "INV-BATCH-001"
            assert result["extracted_data"]["total"] == 500.0
            assert result["input_tokens"] == 500
            assert result["output_tokens"] == 100
            assert result["tokens_used"] == 600

    @pytest.mark.asyncio
    async def test_extract_with_invalid_schema(self, mock_settings, sample_base64_image):
        """Test error handling for invalid schema."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()
            invalid_schema = {"type": "invalid_type"}

            with pytest.raises(ValueError) as exc_info:
                await service.extract_from_image(
                    image_base64=sample_base64_image,
                    schema=invalid_schema,
                    provider="google",
                )
            assert "Invalid JSON schema" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_api_error_handling(
        self, mock_settings, valid_schema, sample_base64_image
    ):
        """Test handling of API errors from provider."""
        with patch("app.services.vllm_service.genai") as mock_genai, patch(
            "app.services.vllm_service.OpenAI"
        ), patch("PIL.Image.open"):
            # Setup mock to raise an exception
            mock_client = Mock()
            mock_client.models.generate_content.side_effect = Exception(
                "API rate limit exceeded"
            )
            mock_genai.Client.return_value = mock_client

            service = VLLMService()

            with pytest.raises(Exception) as exc_info:
                await service.extract_from_image(
                    image_base64=sample_base64_image,
                    schema=valid_schema,
                    provider="google",
                )
            assert "Gemini API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_json_parse_error_handling(
        self, mock_settings, valid_schema, sample_base64_image
    ):
        """Test handling of invalid JSON response from provider."""
        with patch("app.services.vllm_service.genai") as mock_genai, patch(
            "app.services.vllm_service.OpenAI"
        ), patch("PIL.Image.open"):
            # Setup mock to return invalid JSON
            mock_response = Mock()
            mock_response.text = "This is not valid JSON"
            mock_response.usage_metadata = Mock()
            mock_response.usage_metadata.prompt_token_count = 100
            mock_response.usage_metadata.candidates_token_count = 50

            mock_client = Mock()
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client

            service = VLLMService()

            with pytest.raises(ValueError) as exc_info:
                await service.extract_from_image(
                    image_base64=sample_base64_image,
                    schema=valid_schema,
                    provider="google",
                )
            assert "Failed to parse JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_provider_not_configured(
        self, mock_settings_google_only, valid_schema, sample_base64_image
    ):
        """Test error when requesting unconfigured provider."""
        with patch("app.services.vllm_service.genai"):
            service = VLLMService()

            with pytest.raises(ValueError) as exc_info:
                await service.extract_from_image(
                    image_base64=sample_base64_image,
                    schema=valid_schema,
                    provider="openai",  # Not configured
                )
            assert "not configured" in str(exc_info.value)


# =============================================================================
# TestGeminiSchemaCleanup
# =============================================================================


class TestGeminiSchemaCleanup:
    """Tests for Gemini schema cleanup functionality."""

    def test_clean_schema_removes_metadata(self, valid_schema_with_metadata):
        """Test that $schema and $id are removed."""
        cleaned = GeminiVLLMProvider._clean_schema_for_gemini(valid_schema_with_metadata)
        assert "$schema" not in cleaned
        assert "$id" not in cleaned
        assert "type" in cleaned
        assert "properties" in cleaned

    def test_clean_schema_preserves_other_fields(self):
        """Test that non-metadata fields are preserved."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": False,
        }
        cleaned = GeminiVLLMProvider._clean_schema_for_gemini(schema)
        assert cleaned["type"] == "object"
        assert cleaned["required"] == ["name"]
        assert cleaned["additionalProperties"] is False

    def test_clean_schema_recursively_cleans_nested(self):
        """Test that nested objects are also cleaned."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "nested": {
                    "$id": "nested-id",
                    "type": "object",
                    "properties": {"field": {"type": "string"}},
                }
            },
        }
        cleaned = GeminiVLLMProvider._clean_schema_for_gemini(schema)
        assert "$id" not in cleaned["properties"]["nested"]
        assert cleaned["properties"]["nested"]["type"] == "object"

    def test_clean_schema_handles_arrays(self):
        """Test that arrays with objects are cleaned."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "array",
            "items": {"$id": "item-id", "type": "string"},
        }
        cleaned = GeminiVLLMProvider._clean_schema_for_gemini(schema)
        assert "$id" not in cleaned["items"]
        assert cleaned["items"]["type"] == "string"

    def test_clean_schema_handles_non_dict(self):
        """Test that non-dict values are returned as-is."""
        assert GeminiVLLMProvider._clean_schema_for_gemini("string") == "string"
        assert GeminiVLLMProvider._clean_schema_for_gemini(123) == 123
        assert GeminiVLLMProvider._clean_schema_for_gemini(None) is None


# =============================================================================
# TestOpenAIProvider
# =============================================================================


class TestOpenAIProvider:
    """Tests for OpenAI provider functionality."""

    @pytest.mark.asyncio
    async def test_openai_extract_success(self, valid_schema, sample_base64_image):
        """Test successful extraction with OpenAI provider."""
        with patch("app.services.vllm_service.OpenAI") as mock_openai_class:
            # Setup mock response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = (
                '{"invoice_number": "INV-OAI-001", "total": 350.0}'
            )
            mock_response.usage = Mock()
            mock_response.usage.prompt_tokens = 200
            mock_response.usage.completion_tokens = 80

            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            provider = OpenAIVLLMProvider(
                api_key="test-key", model="gpt-4-vision-preview"
            )
            result = await provider.extract(
                image_base64=sample_base64_image,
                schema=valid_schema,
                prompt="Extract invoice data",
            )

            extracted_data, input_tokens, output_tokens, processing_time = result
            assert extracted_data["invoice_number"] == "INV-OAI-001"
            assert extracted_data["total"] == 350.0
            assert input_tokens == 200
            assert output_tokens == 80

    @pytest.mark.asyncio
    async def test_openai_extract_strips_markdown(self, valid_schema, sample_base64_image):
        """Test that OpenAI provider strips markdown code blocks."""
        with patch("app.services.vllm_service.OpenAI") as mock_openai_class:
            # Response with markdown code block
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[
                0
            ].message.content = '```json\n{"invoice_number": "INV-MD-001", "total": 400.0}\n```'
            mock_response.usage = Mock()
            mock_response.usage.prompt_tokens = 150
            mock_response.usage.completion_tokens = 60

            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            provider = OpenAIVLLMProvider(api_key="test-key")
            result = await provider.extract(
                image_base64=sample_base64_image,
                schema=valid_schema,
                prompt="Extract",
            )

            extracted_data, _, _, _ = result
            assert extracted_data["invoice_number"] == "INV-MD-001"

    @pytest.mark.asyncio
    async def test_openai_batch_extract(self, valid_schema, sample_base64_image):
        """Test batch extraction with OpenAI provider."""
        with patch("app.services.vllm_service.OpenAI") as mock_openai_class:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps(
                {"invoice_number": "INV-BATCH-OAI", "total": 750.0}
            )
            mock_response.usage = Mock()
            mock_response.usage.prompt_tokens = 400
            mock_response.usage.completion_tokens = 100

            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            provider = OpenAIVLLMProvider(api_key="test-key")
            images = [sample_base64_image, sample_base64_image]
            result = await provider.extract_batch(
                images_base64=images, schema=valid_schema, prompt="Extract multi-page"
            )

            extracted_data, input_tokens, output_tokens, _ = result
            assert extracted_data["invoice_number"] == "INV-BATCH-OAI"
            assert input_tokens == 400
            assert output_tokens == 100


# =============================================================================
# TestVLLMServiceIntegration
# =============================================================================


class TestVLLMServiceIntegration:
    """Integration-style tests for VLLMService."""

    def test_service_has_validator(self, mock_settings):
        """Test that VLLMService initializes with SchemaValidator."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()
            assert hasattr(service, "validator")
            assert service.validator is not None

    def test_weighted_score_calculation(self, mock_settings, valid_schema):
        """Test that confidence score uses weighted average correctly."""
        with patch("app.services.vllm_service.genai"), patch(
            "app.services.vllm_service.OpenAI"
        ):
            service = VLLMService()

            # Full data, valid
            full_data = {
                "invoice_number": "INV-001",
                "total": 100.0,
                "date": "2024-01-15",
                "vendor": "Test Corp",
                "line_items": [{"description": "Item", "amount": 100.0}],
            }
            score_full = service._calculate_confidence_score(
                full_data, valid_schema, True
            )

            # Partial data, invalid
            partial_data = {"invoice_number": "INV-001", "total": None}
            score_partial = service._calculate_confidence_score(
                partial_data, valid_schema, False
            )

            # Full valid data should have higher score
            assert score_full > score_partial
            assert score_full > 0.8  # Should be high
            assert score_partial < score_full

    @pytest.mark.asyncio
    async def test_extract_returns_all_required_fields(
        self, mock_settings, valid_schema, sample_base64_image
    ):
        """Test that extraction result contains all required fields."""
        with patch("app.services.vllm_service.genai") as mock_genai, patch(
            "app.services.vllm_service.OpenAI"
        ), patch("PIL.Image.open"):
            mock_response = Mock()
            mock_response.text = '{"invoice_number": "INV-001", "total": 100.0}'
            mock_response.usage_metadata = Mock()
            mock_response.usage_metadata.prompt_token_count = 100
            mock_response.usage_metadata.candidates_token_count = 50

            mock_client = Mock()
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client

            service = VLLMService()
            result = await service.extract_from_image(
                image_base64=sample_base64_image,
                schema=valid_schema,
                provider="google",
            )

            # Check all required fields are present
            required_fields = [
                "extracted_data",
                "is_valid",
                "validation_errors",
                "confidence_score",
                "input_tokens",
                "output_tokens",
                "tokens_used",
                "processing_time_ms",
                "model_used",
            ]
            for field in required_fields:
                assert field in result, f"Missing required field: {field}"
