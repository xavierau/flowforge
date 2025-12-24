"""Unit tests for LlamaExtract VLLM provider."""

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.enums import LlamaExtractMode, LlamaExtractTarget
from app.services.llamaextract_provider import (
    LlamaExtractVLLMProvider,
    LlamaExtractAgentError,
    LlamaExtractJobError,
    LlamaExtractTimeoutError,
    _compute_schema_hash,
    _convert_schema_for_llamaextract,
    _map_mode_to_extraction_mode,
    _map_target_to_extraction_target,
    get_llamaextract_provider,
)
from app.services.vllm_service import VLLMProvider


class TestSchemaHashComputation:
    """Tests for schema hash computation."""

    def test_compute_hash_is_deterministic(self):
        """Same schema should produce same hash."""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        hash1 = _compute_schema_hash(schema)
        hash2 = _compute_schema_hash(schema)
        assert hash1 == hash2

    def test_compute_hash_ignores_key_order(self):
        """Hash should be same regardless of key order."""
        schema1 = {"type": "object", "properties": {"name": {"type": "string"}}}
        schema2 = {"properties": {"name": {"type": "string"}}, "type": "object"}
        assert _compute_schema_hash(schema1) == _compute_schema_hash(schema2)

    def test_compute_hash_different_for_different_schemas(self):
        """Different schemas should produce different hashes."""
        schema1 = {"type": "object", "properties": {"name": {"type": "string"}}}
        schema2 = {"type": "object", "properties": {"id": {"type": "integer"}}}
        assert _compute_schema_hash(schema1) != _compute_schema_hash(schema2)

    def test_compute_hash_returns_16_char_string(self):
        """Hash should be 16 character hex string."""
        schema = {"type": "object"}
        hash_value = _compute_schema_hash(schema)
        assert len(hash_value) == 16
        assert all(c in "0123456789abcdef" for c in hash_value)


class TestSchemaConversion:
    """Tests for schema conversion to LlamaExtract format."""

    def test_removes_schema_metadata(self):
        """Should remove $schema field."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
        }
        result = _convert_schema_for_llamaextract(schema)
        assert "$schema" not in result
        assert result["type"] == "object"

    def test_removes_id_metadata(self):
        """Should remove $id field."""
        schema = {"$id": "https://example.com/schema", "type": "object"}
        result = _convert_schema_for_llamaextract(schema)
        assert "$id" not in result

    def test_removes_all_dollar_prefixed_fields(self):
        """Should remove all $-prefixed metadata fields."""
        schema = {
            "$schema": "draft-07",
            "$id": "test",
            "$ref": "#/definitions/test",
            "type": "object",
        }
        result = _convert_schema_for_llamaextract(schema)
        assert not any(k.startswith("$") for k in result.keys())

    def test_recursively_cleans_nested_objects(self):
        """Should clean nested objects."""
        schema = {
            "type": "object",
            "properties": {
                "nested": {
                    "$ref": "#/definitions/nested",
                    "type": "object",
                }
            },
        }
        result = _convert_schema_for_llamaextract(schema)
        assert "$ref" not in result["properties"]["nested"]

    def test_recursively_cleans_arrays(self):
        """Should clean objects inside arrays."""
        schema = {
            "type": "array",
            "items": [{"$ref": "test", "type": "string"}],
        }
        result = _convert_schema_for_llamaextract(schema)
        assert "$ref" not in result["items"][0]

    def test_preserves_non_metadata_fields(self):
        """Should preserve normal schema fields."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        result = _convert_schema_for_llamaextract(schema)
        assert result == schema

    def test_handles_non_dict_input(self):
        """Should return non-dict inputs unchanged."""
        assert _convert_schema_for_llamaextract("string") == "string"
        assert _convert_schema_for_llamaextract(123) == 123
        assert _convert_schema_for_llamaextract(None) is None


class TestModeMapping:
    """Tests for mode mapping functions."""

    def test_standard_maps_to_balanced(self):
        """STANDARD mode should map to BALANCED."""
        assert _map_mode_to_extraction_mode(LlamaExtractMode.STANDARD) == "BALANCED"

    def test_premium_maps_to_premium(self):
        """PREMIUM mode should map to PREMIUM."""
        assert _map_mode_to_extraction_mode(LlamaExtractMode.PREMIUM) == "PREMIUM"


class TestTargetMapping:
    """Tests for target mapping functions."""

    def test_per_doc_maps_correctly(self):
        """PER_DOC should map to PER_DOC."""
        assert _map_target_to_extraction_target(LlamaExtractTarget.PER_DOC) == "PER_DOC"

    def test_per_page_maps_correctly(self):
        """PER_PAGE should map to PER_PAGE."""
        assert _map_target_to_extraction_target(LlamaExtractTarget.PER_PAGE) == "PER_PAGE"


class TestLlamaExtractProviderInit:
    """Tests for provider initialization."""

    def test_requires_api_key(self):
        """Should raise ValueError if no API key provided."""
        with pytest.raises(ValueError, match="API key is required"):
            LlamaExtractVLLMProvider(api_key="")

    def test_accepts_valid_api_key(self):
        """Should accept valid API key."""
        provider = LlamaExtractVLLMProvider(api_key="test_key")
        assert provider._api_key == "test_key"

    def test_default_mode_is_standard(self):
        """Default mode should be STANDARD."""
        provider = LlamaExtractVLLMProvider(api_key="test_key")
        assert provider._mode == LlamaExtractMode.STANDARD

    def test_default_target_is_per_doc(self):
        """Default target should be PER_DOC."""
        provider = LlamaExtractVLLMProvider(api_key="test_key")
        assert provider._target == LlamaExtractTarget.PER_DOC

    def test_custom_poll_settings(self):
        """Should accept custom poll settings."""
        provider = LlamaExtractVLLMProvider(
            api_key="test_key",
            poll_interval=5.0,
            max_poll_attempts=100,
        )
        assert provider._poll_interval == 5.0
        assert provider._max_poll_attempts == 100


class TestLlamaExtractProviderInheritance:
    """Tests for VLLMProvider inheritance."""

    def test_inherits_from_vllm_provider(self):
        """Should inherit from VLLMProvider ABC."""
        provider = LlamaExtractVLLMProvider(api_key="test_key")
        assert isinstance(provider, VLLMProvider)

    def test_has_extract_method(self):
        """Should have extract method."""
        provider = LlamaExtractVLLMProvider(api_key="test_key")
        assert hasattr(provider, "extract")
        assert callable(provider.extract)

    def test_has_extract_batch_method(self):
        """Should have extract_batch method."""
        provider = LlamaExtractVLLMProvider(api_key="test_key")
        assert hasattr(provider, "extract_batch")
        assert callable(provider.extract_batch)


class TestLlamaExtractProviderProperties:
    """Tests for provider properties."""

    def test_provider_name(self):
        """Provider name should be llamaextract."""
        provider = LlamaExtractVLLMProvider(api_key="test_key")
        assert provider.provider_name == "llamaextract"

    def test_model_name_standard(self):
        """Model name should include mode."""
        provider = LlamaExtractVLLMProvider(
            api_key="test_key", mode=LlamaExtractMode.STANDARD
        )
        assert provider.model_name == "llamaextract-standard"

    def test_model_name_premium(self):
        """Model name should reflect premium mode."""
        provider = LlamaExtractVLLMProvider(
            api_key="test_key", mode=LlamaExtractMode.PREMIUM
        )
        assert provider.model_name == "llamaextract-premium"


class TestAgentCache:
    """Tests for agent caching functionality."""

    def test_cache_starts_empty(self):
        """Agent cache should start empty."""
        provider = LlamaExtractVLLMProvider(api_key="test_key")
        assert len(provider._agent_cache) == 0

    def test_clear_cache(self):
        """Clear cache should empty the cache."""
        provider = LlamaExtractVLLMProvider(api_key="test_key")
        provider._agent_cache["hash1"] = "agent1"
        provider._agent_cache["hash2"] = "agent2"
        provider.clear_agent_cache()
        assert len(provider._agent_cache) == 0


class TestGetHeaders:
    """Tests for HTTP header generation."""

    def test_includes_authorization(self):
        """Headers should include Bearer token."""
        provider = LlamaExtractVLLMProvider(api_key="my_secret_key")
        headers = provider._get_headers()
        assert headers["Authorization"] == "Bearer my_secret_key"

    def test_includes_content_type(self):
        """Headers should include Content-Type."""
        provider = LlamaExtractVLLMProvider(api_key="test_key")
        headers = provider._get_headers()
        assert headers["Content-Type"] == "application/json"

    def test_includes_accept(self):
        """Headers should include Accept."""
        provider = LlamaExtractVLLMProvider(api_key="test_key")
        headers = provider._get_headers()
        assert headers["Accept"] == "application/json"


class TestResultParsing:
    """Tests for result parsing."""

    def test_parse_result_extracts_data_field(self):
        """Should extract data field from result."""
        provider = LlamaExtractVLLMProvider(api_key="test_key")
        result = {"data": {"name": "test"}, "status": "completed"}
        parsed = provider._parse_result(result)
        assert parsed == {"name": "test"}

    def test_parse_result_handles_list_for_per_doc(self):
        """For PER_DOC mode, should take first item from list."""
        provider = LlamaExtractVLLMProvider(
            api_key="test_key", target=LlamaExtractTarget.PER_DOC
        )
        result = {"data": [{"name": "first"}, {"name": "second"}]}
        parsed = provider._parse_result(result)
        assert parsed == {"name": "first"}

    def test_parse_result_returns_list_for_per_page(self):
        """For PER_PAGE mode, should return full list."""
        provider = LlamaExtractVLLMProvider(
            api_key="test_key", target=LlamaExtractTarget.PER_PAGE
        )
        result = {"data": [{"page": 1}, {"page": 2}]}
        parsed = provider._parse_result(result)
        assert parsed == [{"page": 1}, {"page": 2}]

    def test_parse_result_handles_empty_list(self):
        """Should return empty dict for empty list in PER_DOC mode."""
        provider = LlamaExtractVLLMProvider(
            api_key="test_key", target=LlamaExtractTarget.PER_DOC
        )
        result = {"data": []}
        parsed = provider._parse_result(result)
        assert parsed == {}

    def test_parse_result_fallback_returns_result(self):
        """Should return result as-is if no data field."""
        provider = LlamaExtractVLLMProvider(api_key="test_key")
        result = {"extracted": {"name": "test"}}
        parsed = provider._parse_result(result)
        assert parsed == result


class TestFactoryFunction:
    """Tests for get_llamaextract_provider factory."""

    def test_returns_none_without_api_key(self):
        """Should return None if no API key configured."""
        with patch("app.services.llamaextract_provider.settings") as mock_settings:
            mock_settings.llamaextract_api_key = ""
            result = get_llamaextract_provider()
            assert result is None

    def test_returns_provider_with_api_key(self):
        """Should return provider if API key is configured."""
        with patch("app.services.llamaextract_provider.settings") as mock_settings:
            mock_settings.llamaextract_api_key = "test_api_key"
            result = get_llamaextract_provider()
            assert result is not None
            assert isinstance(result, LlamaExtractVLLMProvider)

    def test_accepts_custom_mode(self):
        """Should create provider with custom mode."""
        with patch("app.services.llamaextract_provider.settings") as mock_settings:
            mock_settings.llamaextract_api_key = "test_api_key"
            result = get_llamaextract_provider(mode=LlamaExtractMode.PREMIUM)
            assert result._mode == LlamaExtractMode.PREMIUM

    def test_accepts_custom_target(self):
        """Should create provider with custom target."""
        with patch("app.services.llamaextract_provider.settings") as mock_settings:
            mock_settings.llamaextract_api_key = "test_api_key"
            result = get_llamaextract_provider(target=LlamaExtractTarget.PER_PAGE)
            assert result._target == LlamaExtractTarget.PER_PAGE


class TestCreatePdfFromImages:
    """Tests for PDF creation from images."""

    @pytest.mark.asyncio
    async def test_creates_pdf_from_single_image(self):
        """Should create PDF from single image."""
        provider = LlamaExtractVLLMProvider(api_key="test_key")

        # Create a simple 1x1 red PNG image
        from PIL import Image
        import io

        img = Image.new("RGB", (10, 10), color="red")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_b64 = base64.b64encode(buffer.getvalue()).decode()

        pdf_bytes = await provider._create_pdf_from_images([img_b64])

        # Check it's a valid PDF (starts with %PDF)
        assert pdf_bytes[:4] == b"%PDF"

    @pytest.mark.asyncio
    async def test_creates_pdf_from_multiple_images(self):
        """Should create multi-page PDF from multiple images."""
        provider = LlamaExtractVLLMProvider(api_key="test_key")

        from PIL import Image
        import io

        images_b64 = []
        for color in ["red", "green", "blue"]:
            img = Image.new("RGB", (10, 10), color=color)
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            images_b64.append(base64.b64encode(buffer.getvalue()).decode())

        pdf_bytes = await provider._create_pdf_from_images(images_b64)

        assert pdf_bytes[:4] == b"%PDF"

    @pytest.mark.asyncio
    async def test_handles_rgba_images(self):
        """Should convert RGBA to RGB for PDF compatibility."""
        provider = LlamaExtractVLLMProvider(api_key="test_key")

        from PIL import Image
        import io

        # Create RGBA image with transparency
        img = Image.new("RGBA", (10, 10), color=(255, 0, 0, 128))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_b64 = base64.b64encode(buffer.getvalue()).decode()

        pdf_bytes = await provider._create_pdf_from_images([img_b64])

        assert pdf_bytes[:4] == b"%PDF"

    @pytest.mark.asyncio
    async def test_raises_on_empty_list(self):
        """Should raise ValueError for empty image list."""
        provider = LlamaExtractVLLMProvider(api_key="test_key")

        with pytest.raises(ValueError, match="No valid images"):
            await provider._create_pdf_from_images([])


class TestExceptionClasses:
    """Tests for custom exception classes."""

    def test_llamaextract_error_is_exception(self):
        """LlamaExtractError should be an Exception."""
        from app.services.llamaextract_provider import LlamaExtractError

        assert issubclass(LlamaExtractError, Exception)

    def test_agent_error_inherits_from_base(self):
        """LlamaExtractAgentError should inherit from LlamaExtractError."""
        from app.services.llamaextract_provider import (
            LlamaExtractError,
            LlamaExtractAgentError,
        )

        assert issubclass(LlamaExtractAgentError, LlamaExtractError)

    def test_job_error_inherits_from_base(self):
        """LlamaExtractJobError should inherit from LlamaExtractError."""
        from app.services.llamaextract_provider import (
            LlamaExtractError,
            LlamaExtractJobError,
        )

        assert issubclass(LlamaExtractJobError, LlamaExtractError)

    def test_timeout_error_inherits_from_base(self):
        """LlamaExtractTimeoutError should inherit from LlamaExtractError."""
        from app.services.llamaextract_provider import (
            LlamaExtractError,
            LlamaExtractTimeoutError,
        )

        assert issubclass(LlamaExtractTimeoutError, LlamaExtractError)
