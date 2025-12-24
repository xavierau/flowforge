"""Unit tests for LlamaExtract handling in extraction tasks."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4

from app.tasks.extractor import (
    _is_llamaextract_provider,
    _create_llamaextract_provider,
    _extract_with_llamaextract,
)
from app.models.enums import LlamaExtractMode, LlamaExtractTarget


class TestIsLlamaextractProvider:
    """Tests for _is_llamaextract_provider helper."""

    def test_returns_true_for_llamaextract_provider(self):
        """Should return True when model_provider is 'llamaextract'."""
        job = Mock()
        job.model_provider = "llamaextract"

        result = _is_llamaextract_provider(job)

        assert result is True

    def test_returns_false_for_google_provider(self):
        """Should return False when model_provider is 'google'."""
        job = Mock()
        job.model_provider = "google"

        result = _is_llamaextract_provider(job)

        assert result is False

    def test_returns_false_for_openai_provider(self):
        """Should return False when model_provider is 'openai'."""
        job = Mock()
        job.model_provider = "openai"

        result = _is_llamaextract_provider(job)

        assert result is False


class TestCreateLlamaextractProvider:
    """Tests for _create_llamaextract_provider helper."""

    @patch("app.tasks.extractor.settings")
    @patch("app.services.llamaextract_provider.LlamaExtractVLLMProvider")
    def test_creates_provider_with_default_mode_and_target(
        self, MockProvider, mock_settings
    ):
        """Should create provider with default mode and target when not specified."""
        mock_settings.llamaextract_api_key = "test-api-key"
        MockProvider.return_value = Mock()

        job = Mock()
        job.llamaextract_mode = None
        job.llamaextract_target = None

        _create_llamaextract_provider(job)

        MockProvider.assert_called_once_with(
            api_key="test-api-key",
            mode=LlamaExtractMode.STANDARD,
            target=LlamaExtractTarget.PER_DOC,
        )

    @patch("app.tasks.extractor.settings")
    @patch("app.services.llamaextract_provider.LlamaExtractVLLMProvider")
    def test_creates_provider_with_premium_mode(self, MockProvider, mock_settings):
        """Should create provider with premium mode when specified."""
        mock_settings.llamaextract_api_key = "test-api-key"
        MockProvider.return_value = Mock()

        job = Mock()
        job.llamaextract_mode = "premium"
        job.llamaextract_target = "per_page"

        _create_llamaextract_provider(job)

        MockProvider.assert_called_once_with(
            api_key="test-api-key",
            mode=LlamaExtractMode.PREMIUM,
            target=LlamaExtractTarget.PER_PAGE,
        )

    @patch("app.tasks.extractor.settings")
    def test_raises_error_when_api_key_not_configured(self, mock_settings):
        """Should raise ValueError when API key is not configured."""
        mock_settings.llamaextract_api_key = ""

        job = Mock()
        job.llamaextract_mode = "standard"
        job.llamaextract_target = "per_doc"

        with pytest.raises(ValueError, match="LlamaExtract API key not configured"):
            _create_llamaextract_provider(job)


class TestExtractWithLlamaextract:
    """Tests for _extract_with_llamaextract async function."""

    @pytest.mark.asyncio
    @patch("app.tasks.extractor._create_llamaextract_provider")
    async def test_uses_pdf_extraction_for_pdf_documents(
        self, mock_create_provider
    ):
        """Should use extract_from_pdf for PDF documents."""
        mock_provider = Mock()
        mock_provider.model_name = "llamaextract-standard"
        mock_provider.extract_from_pdf = AsyncMock(
            return_value=({"invoice_number": "123"}, 0, 0, 1500)
        )
        mock_create_provider.return_value = mock_provider

        job = Mock()
        job.extraction_schema = {"type": "object"}
        job.custom_prompt = "Extract invoice data"

        document = Mock()
        document.id = uuid4()
        document.mime_type = "application/pdf"
        document.file_path = "/path/to/file.pdf"

        storage_svc = Mock()
        storage_svc.download_file_sync.return_value = b"%PDF-1.4 content"

        result = await _extract_with_llamaextract(job, document, storage_svc)

        mock_provider.extract_from_pdf.assert_called_once_with(
            pdf_bytes=b"%PDF-1.4 content",
            schema={"type": "object"},
            prompt="Extract invoice data",
        )
        assert result["extracted_data"] == {"invoice_number": "123"}
        assert result["model_used"] == "llamaextract-standard"
        assert result["processing_time_ms"] == 1500

    @pytest.mark.asyncio
    @patch("app.tasks.extractor._create_llamaextract_provider")
    async def test_uses_image_extraction_for_image_documents(
        self, mock_create_provider
    ):
        """Should use extract for image documents."""
        mock_provider = Mock()
        mock_provider.model_name = "llamaextract-premium"
        mock_provider.extract = AsyncMock(
            return_value=({"total": 100.50}, 0, 0, 2000)
        )
        mock_create_provider.return_value = mock_provider

        job = Mock()
        job.extraction_schema = {"type": "object"}
        job.custom_prompt = ""

        document = Mock()
        document.id = uuid4()
        document.mime_type = "image/png"
        document.file_path = "/path/to/file.png"

        storage_svc = Mock()
        storage_svc.download_file_sync.return_value = b"\x89PNG image content"

        result = await _extract_with_llamaextract(job, document, storage_svc)

        mock_provider.extract.assert_called_once()
        call_kwargs = mock_provider.extract.call_args.kwargs
        assert call_kwargs["schema"] == {"type": "object"}
        assert call_kwargs["prompt"] == ""
        assert "image_base64" in call_kwargs

        assert result["extracted_data"] == {"total": 100.50}
        assert result["model_used"] == "llamaextract-premium"

    @pytest.mark.asyncio
    @patch("app.tasks.extractor._create_llamaextract_provider")
    async def test_returns_correct_result_structure(self, mock_create_provider):
        """Should return result with all required fields."""
        mock_provider = Mock()
        mock_provider.model_name = "llamaextract-standard"
        mock_provider.extract_from_pdf = AsyncMock(
            return_value=({"data": "value"}, 100, 50, 3000)
        )
        mock_create_provider.return_value = mock_provider

        job = Mock()
        job.extraction_schema = {}
        job.custom_prompt = None

        document = Mock()
        document.id = uuid4()
        document.mime_type = "application/pdf"
        document.file_path = "/path/to/file.pdf"

        storage_svc = Mock()
        storage_svc.download_file_sync.return_value = b"%PDF"

        result = await _extract_with_llamaextract(job, document, storage_svc)

        assert "extracted_data" in result
        assert "confidence_score" in result
        assert "model_used" in result
        assert "input_tokens" in result
        assert "output_tokens" in result
        assert "tokens_used" in result
        assert "processing_time_ms" in result

        assert result["confidence_score"] == 1.0
        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 50
        assert result["tokens_used"] == 150

    @pytest.mark.asyncio
    @patch("app.tasks.extractor._create_llamaextract_provider")
    async def test_handles_none_custom_prompt(self, mock_create_provider):
        """Should handle None custom_prompt by using empty string."""
        mock_provider = Mock()
        mock_provider.model_name = "llamaextract-standard"
        mock_provider.extract_from_pdf = AsyncMock(
            return_value=({}, 0, 0, 1000)
        )
        mock_create_provider.return_value = mock_provider

        job = Mock()
        job.extraction_schema = {}
        job.custom_prompt = None

        document = Mock()
        document.id = uuid4()
        document.mime_type = "application/pdf"
        document.file_path = "/path/to/file.pdf"

        storage_svc = Mock()
        storage_svc.download_file_sync.return_value = b"%PDF"

        await _extract_with_llamaextract(job, document, storage_svc)

        mock_provider.extract_from_pdf.assert_called_once_with(
            pdf_bytes=b"%PDF",
            schema={},
            prompt="",
        )
