"""Unit tests for converter factory.

Tests converter registration, retrieval, and dependency injection based on API keys.
"""

import pytest
from unittest.mock import Mock, patch

from app.services.converters.converter_factory import (
    ConverterFactory,
    get_converter_factory,
)
from app.services.converters.base import (
    IImageToMarkdownConverter,
    IMarkdownToJsonExtractor,
)


# ============================================================================
# Factory Initialization Tests
# ============================================================================


class TestConverterFactoryInitialization:
    """Tests for factory initialization and singleton pattern."""

    @pytest.mark.unit
    def test_factory_singleton_pattern(self, reset_factory_singleton):
        """Test that get_converter_factory returns singleton instance."""
        factory1 = get_converter_factory()
        factory2 = get_converter_factory()

        assert factory1 is factory2

    @pytest.mark.unit
    def test_factory_direct_instantiation(self, mock_both_api_keys):
        """Test direct factory instantiation."""
        factory = ConverterFactory()
        assert factory is not None
        assert hasattr(factory, "_markdown_converters")
        assert hasattr(factory, "_json_extractors")


# ============================================================================
# Converter Registration Tests
# ============================================================================


class TestConverterRegistration:
    """Tests for converter registration based on API keys."""

    @pytest.mark.unit
    def test_register_gemini_with_google_api_key(
        self, mock_google_api_key, reset_factory_singleton
    ):
        """Test Gemini converters registered when Google API key present."""
        factory = get_converter_factory()
        available = factory.list_available_converters()

        assert "gemini_vision" in available["markdown_converters"]
        assert "gemini" in available["json_extractors"]

    @pytest.mark.unit
    def test_register_gpt4v_with_openai_api_key(
        self, mock_openai_api_key, reset_factory_singleton
    ):
        """Test GPT-4V converters registered when OpenAI API key present."""
        factory = get_converter_factory()
        available = factory.list_available_converters()

        assert "gpt4v" in available["markdown_converters"]
        assert "openai" in available["json_extractors"]

    @pytest.mark.unit
    def test_register_both_providers_with_both_keys(
        self, mock_both_api_keys, reset_factory_singleton
    ):
        """Test all converters registered when both API keys present."""
        factory = get_converter_factory()
        available = factory.list_available_converters()

        # Markdown converters
        assert "gemini_vision" in available["markdown_converters"]
        assert "gpt4v" in available["markdown_converters"]
        assert len(available["markdown_converters"]) == 2

        # JSON extractors
        assert "gemini" in available["json_extractors"]
        assert "openai" in available["json_extractors"]
        assert len(available["json_extractors"]) == 2

    @pytest.mark.unit
    def test_skip_registration_without_api_keys(
        self, monkeypatch, reset_factory_singleton
    ):
        """Test converters not registered when API keys missing."""
        # Clear API keys
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        from app.config import settings

        settings.google_api_key = ""
        settings.openai_api_key = ""

        factory = get_converter_factory()
        available = factory.list_available_converters()

        assert len(available["markdown_converters"]) == 0
        assert len(available["json_extractors"]) == 0

    @pytest.mark.unit
    @patch("app.services.converters.converter_factory.GeminiMarkdownConverter")
    def test_handle_registration_error(
        self, mock_gemini_class, mock_google_api_key, reset_factory_singleton, caplog
    ):
        """Test graceful handling of converter initialization errors."""
        # Make Gemini converter initialization fail
        mock_gemini_class.side_effect = Exception("Initialization failed")

        factory = get_converter_factory()
        available = factory.list_available_converters()

        # Gemini vision should not be registered
        assert "gemini_vision" not in available["markdown_converters"]

        # Error should be logged
        assert "Failed to register Gemini markdown converter" in caplog.text


# ============================================================================
# Converter Retrieval Tests
# ============================================================================


class TestConverterRetrieval:
    """Tests for getting converters by name."""

    @pytest.mark.unit
    def test_get_markdown_converter_valid_name(
        self, mock_both_api_keys, reset_factory_singleton
    ):
        """Test retrieving markdown converter with valid name."""
        factory = get_converter_factory()

        gemini_converter = factory.get_markdown_converter("gemini_vision")
        assert gemini_converter is not None
        assert isinstance(gemini_converter, IImageToMarkdownConverter)

        gpt4v_converter = factory.get_markdown_converter("gpt4v")
        assert gpt4v_converter is not None
        assert isinstance(gpt4v_converter, IImageToMarkdownConverter)

    @pytest.mark.unit
    def test_get_markdown_converter_invalid_name(
        self, mock_both_api_keys, reset_factory_singleton
    ):
        """Test error when requesting non-existent markdown converter."""
        factory = get_converter_factory()

        with pytest.raises(ValueError) as exc_info:
            factory.get_markdown_converter("nonexistent")

        error_message = str(exc_info.value)
        assert "not available" in error_message
        assert "nonexistent" in error_message
        assert "gemini_vision" in error_message  # Shows available options
        assert "gpt4v" in error_message

    @pytest.mark.unit
    def test_get_markdown_converter_missing_api_key(
        self, monkeypatch, reset_factory_singleton
    ):
        """Test error message includes API key hint."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        from app.config import settings

        settings.google_api_key = ""
        settings.openai_api_key = ""

        factory = get_converter_factory()

        with pytest.raises(ValueError) as exc_info:
            factory.get_markdown_converter("gemini_vision")

        error_message = str(exc_info.value)
        assert "Check API keys in settings" in error_message

    @pytest.mark.unit
    def test_get_json_extractor_valid_name(
        self, mock_both_api_keys, reset_factory_singleton
    ):
        """Test retrieving JSON extractor with valid name."""
        factory = get_converter_factory()

        gemini_extractor = factory.get_json_extractor("gemini")
        assert gemini_extractor is not None
        assert isinstance(gemini_extractor, IMarkdownToJsonExtractor)

        openai_extractor = factory.get_json_extractor("openai")
        assert openai_extractor is not None
        assert isinstance(openai_extractor, IMarkdownToJsonExtractor)

    @pytest.mark.unit
    def test_get_json_extractor_invalid_name(
        self, mock_both_api_keys, reset_factory_singleton
    ):
        """Test error when requesting non-existent JSON extractor."""
        factory = get_converter_factory()

        with pytest.raises(ValueError) as exc_info:
            factory.get_json_extractor("nonexistent")

        error_message = str(exc_info.value)
        assert "not available" in error_message
        assert "nonexistent" in error_message
        assert "gemini" in error_message  # Shows available options
        assert "openai" in error_message

    @pytest.mark.unit
    def test_get_same_converter_instance_multiple_calls(
        self, mock_both_api_keys, reset_factory_singleton
    ):
        """Test that same converter instance returned on multiple calls."""
        factory = get_converter_factory()

        converter1 = factory.get_markdown_converter("gemini_vision")
        converter2 = factory.get_markdown_converter("gemini_vision")

        assert converter1 is converter2


# ============================================================================
# List Available Converters Tests
# ============================================================================


class TestListAvailableConverters:
    """Tests for listing available converters."""

    @pytest.mark.unit
    def test_list_all_converters(self, mock_both_api_keys, reset_factory_singleton):
        """Test listing all available converters."""
        factory = get_converter_factory()
        available = factory.list_available_converters()

        assert "markdown_converters" in available
        assert "json_extractors" in available
        assert isinstance(available["markdown_converters"], list)
        assert isinstance(available["json_extractors"], list)

    @pytest.mark.unit
    def test_list_converters_empty_when_no_keys(
        self, monkeypatch, reset_factory_singleton
    ):
        """Test empty lists when no API keys configured."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        from app.config import settings

        settings.google_api_key = ""
        settings.openai_api_key = ""

        factory = get_converter_factory()
        available = factory.list_available_converters()

        assert available["markdown_converters"] == []
        assert available["json_extractors"] == []

    @pytest.mark.unit
    def test_list_converters_partial_registration(
        self, mock_google_api_key, reset_factory_singleton
    ):
        """Test listing when only some converters registered."""
        factory = get_converter_factory()
        available = factory.list_available_converters()

        # Only Gemini should be registered
        assert "gemini_vision" in available["markdown_converters"]
        assert "gpt4v" not in available["markdown_converters"]

        assert "gemini" in available["json_extractors"]
        assert "openai" not in available["json_extractors"]


# ============================================================================
# Integration Tests
# ============================================================================


class TestFactoryIntegration:
    """Integration tests for factory with real converters."""

    @pytest.mark.unit
    @pytest.mark.slow
    async def test_get_and_use_gemini_converter(
        self, mock_google_api_key, reset_factory_singleton
    ):
        """Test retrieving and using Gemini converter (mocked API)."""
        factory = get_converter_factory()
        converter = factory.get_markdown_converter("gemini_vision")

        # Just verify we can get the converter
        # Actual conversion tested in converter-specific tests
        assert converter is not None
        assert hasattr(converter, "convert_single")
        assert hasattr(converter, "convert_batch")

    @pytest.mark.unit
    async def test_get_and_use_json_extractor(
        self, mock_google_api_key, reset_factory_singleton
    ):
        """Test retrieving and using JSON extractor (mocked API)."""
        factory = get_converter_factory()
        extractor = factory.get_json_extractor("gemini")

        # Just verify we can get the extractor
        # Actual extraction tested in extractor-specific tests
        assert extractor is not None
        assert hasattr(extractor, "extract")
