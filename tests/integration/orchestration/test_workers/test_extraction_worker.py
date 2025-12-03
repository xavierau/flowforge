"""
Integration tests for ExtractionWorker.

Tests document extraction execution including:
- Single and multi-page extraction
- Different VLLM providers
- Input validation
- Error handling for missing documents
- Output format structure
- Token count tracking
"""

import uuid
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock

import pytest
from sqlalchemy.orm import Session

from app.orchestration.workers.extraction_worker import ExtractionWorker
from app.models.document import Document, DocumentPage
from app.models.tenant import Tenant
from app.models.enums import DocumentStatus


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def worker():
    """Create ExtractionWorker with mocked dependencies."""
    with patch(
        "app.orchestration.workers.extraction_worker.StorageService"
    ) as mock_storage, patch(
        "app.orchestration.workers.extraction_worker.VLLMService"
    ) as mock_vllm:
        mock_storage_instance = Mock()
        mock_storage.return_value = mock_storage_instance

        mock_vllm_instance = Mock()
        mock_vllm.return_value = mock_vllm_instance

        worker = ExtractionWorker()
        worker._mock_storage = mock_storage_instance
        worker._mock_vllm = mock_vllm_instance
        yield worker


@pytest.fixture
def extraction_schema():
    """Sample extraction schema."""
    return {
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string"},
            "total_amount": {"type": "number"},
            "vendor_name": {"type": "string"},
        },
        "required": ["invoice_number", "total_amount"],
    }


@pytest.fixture
def document_with_pages(db_session: Session, test_tenant: Tenant):
    """Create a document with pages ready for extraction."""
    document = Document(
        id=str(uuid.uuid4()),
        tenant_id=test_tenant.id,
        filename="test_invoice.pdf",
        status=DocumentStatus.READY_FOR_EXTRACTION.value,
        file_path="/storage/test_invoice.pdf",
        size_bytes=1024,
        mime_type="application/pdf",
        page_count=2,
    )
    db_session.add(document)
    db_session.flush()

    # Add pages
    for i in range(2):
        page = DocumentPage(
            id=str(uuid.uuid4()),
            document_id=document.id,
            page_number=i + 1,
            image_path=f"/storage/pages/page_{i + 1}.png",
            status="ready",
        )
        db_session.add(page)

    db_session.commit()
    db_session.refresh(document)
    return document


@pytest.fixture
def document_not_ready(db_session: Session, test_tenant: Tenant):
    """Create a document that's not ready for extraction."""
    document = Document(
        id=str(uuid.uuid4()),
        tenant_id=test_tenant.id,
        filename="processing_doc.pdf",
        status=DocumentStatus.PROCESSING.value,
        file_path="/storage/processing_doc.pdf",
        size_bytes=1024,
        mime_type="application/pdf",
    )
    db_session.add(document)
    db_session.commit()
    return document


# ==============================================================================
# Input Validation Tests
# ==============================================================================


class TestExtractionWorkerValidation:
    """Tests for input validation."""

    def test_validate_input_missing_document_id(self, worker):
        """GIVEN task without document_id WHEN validating THEN returns error."""
        task_input = {"schema": {"type": "object"}}

        error = worker.validate_input(task_input)

        assert error is not None
        assert "document_id" in error

    def test_validate_input_missing_schema(self, worker):
        """GIVEN task without schema WHEN validating THEN returns error."""
        task_input = {"document_id": "doc-123"}

        error = worker.validate_input(task_input)

        assert error is not None
        assert "schema" in error

    def test_validate_input_invalid_schema_type(self, worker):
        """GIVEN schema as non-dict WHEN validating THEN returns error."""
        task_input = {
            "document_id": "doc-123",
            "schema": "not a dict",
        }

        error = worker.validate_input(task_input)

        assert error is not None
        assert "dictionary" in error

    def test_validate_input_invalid_provider(self, worker):
        """GIVEN invalid provider WHEN validating THEN returns error."""
        task_input = {
            "document_id": "doc-123",
            "schema": {"type": "object"},
            "provider": "unknown_provider",
        }

        error = worker.validate_input(task_input)

        assert error is not None
        assert "provider" in error.lower()

    @pytest.mark.parametrize("provider", ["google", "openai", "deepseek"])
    def test_validate_input_valid_providers(self, worker, provider):
        """GIVEN valid provider WHEN validating THEN returns None."""
        task_input = {
            "document_id": "doc-123",
            "schema": {"type": "object"},
            "provider": provider,
        }

        error = worker.validate_input(task_input)

        assert error is None

    def test_validate_input_default_provider(self, worker):
        """GIVEN no provider WHEN validating THEN uses default (google)."""
        task_input = {
            "document_id": "doc-123",
            "schema": {"type": "object"},
        }

        error = worker.validate_input(task_input)

        assert error is None


# ==============================================================================
# Execution Tests - Single Page
# ==============================================================================


class TestExtractionWorkerSinglePage:
    """Tests for single page extraction."""

    def test_execute_single_page_extraction(
        self, worker, document_with_pages, extraction_schema, db_session
    ):
        """GIVEN single page document WHEN executing THEN returns extracted data."""
        # Remove second page for single-page test
        document_with_pages.pages = [document_with_pages.pages[0]]
        db_session.commit()

        # Configure mocks
        worker._mock_storage.get_file.return_value = b"fake_image_data"
        worker._mock_vllm.extract_from_image.return_value = (
            {"invoice_number": "INV-001", "total_amount": 100.00},
            500,  # input tokens
            100,  # output tokens
        )

        task_input = {
            "document_id": document_with_pages.id,
            "schema": extraction_schema,
            "provider": "google",
        }

        with patch(
            "app.orchestration.workers.extraction_worker.SessionLocal"
        ) as mock_session:
            mock_session.return_value = db_session
            result = worker.execute_task(task_input)

        assert result["extracted_data"]["invoice_number"] == "INV-001"
        assert result["extracted_data"]["total_amount"] == 100.00
        assert result["pages_processed"] == 1
        assert result["total_tokens"] == 600

    def test_execute_with_custom_model(
        self, worker, document_with_pages, extraction_schema, db_session
    ):
        """GIVEN custom model WHEN executing THEN passes model to VLLM service."""
        document_with_pages.pages = [document_with_pages.pages[0]]
        db_session.commit()

        worker._mock_storage.get_file.return_value = b"fake_image_data"
        worker._mock_vllm.extract_from_image.return_value = (
            {"invoice_number": "INV-001"},
            100,
            50,
        )

        task_input = {
            "document_id": document_with_pages.id,
            "schema": extraction_schema,
            "provider": "google",
            "model": "gemini-2.5-pro",
        }

        with patch(
            "app.orchestration.workers.extraction_worker.SessionLocal"
        ) as mock_session:
            mock_session.return_value = db_session
            worker.execute_task(task_input)

        worker._mock_vllm.extract_from_image.assert_called_once()
        call_kwargs = worker._mock_vllm.extract_from_image.call_args
        assert call_kwargs.kwargs.get("model_name") == "gemini-2.5-pro"


# ==============================================================================
# Execution Tests - Multi Page
# ==============================================================================


class TestExtractionWorkerMultiPage:
    """Tests for multi-page extraction."""

    def test_execute_multi_page_extraction(
        self, worker, document_with_pages, extraction_schema, db_session
    ):
        """GIVEN multi-page document WHEN executing THEN processes all pages."""
        worker._mock_storage.get_file.return_value = b"fake_image_data"
        worker._mock_vllm.extract_from_image.side_effect = [
            ({"invoice_number": "INV-001", "line_items": [{"item": "A"}]}, 500, 100),
            ({"line_items": [{"item": "B"}]}, 500, 100),
        ]

        task_input = {
            "document_id": document_with_pages.id,
            "schema": extraction_schema,
            "provider": "google",
        }

        with patch(
            "app.orchestration.workers.extraction_worker.SessionLocal"
        ) as mock_session:
            mock_session.return_value = db_session
            result = worker.execute_task(task_input)

        assert result["pages_processed"] == 2
        assert result["total_tokens"] == 1200
        assert result["input_tokens"] == 1000
        assert result["output_tokens"] == 200
        # Arrays should be combined
        assert len(result["extracted_data"]["line_items"]) == 2

    def test_execute_combines_array_fields(
        self, worker, document_with_pages, extraction_schema, db_session
    ):
        """GIVEN multi-page with arrays WHEN executing THEN combines arrays."""
        worker._mock_storage.get_file.return_value = b"fake_image_data"
        worker._mock_vllm.extract_from_image.side_effect = [
            ({"items": [1, 2], "header": "Invoice"}, 100, 50),
            ({"items": [3, 4], "header": "Different"}, 100, 50),
        ]

        task_input = {
            "document_id": document_with_pages.id,
            "schema": extraction_schema,
        }

        with patch(
            "app.orchestration.workers.extraction_worker.SessionLocal"
        ) as mock_session:
            mock_session.return_value = db_session
            result = worker.execute_task(task_input)

        # Arrays are combined
        assert result["extracted_data"]["items"] == [1, 2, 3, 4]
        # Non-arrays keep first value
        assert result["extracted_data"]["header"] == "Invoice"


# ==============================================================================
# Error Handling Tests
# ==============================================================================


class TestExtractionWorkerErrors:
    """Tests for error handling."""

    def test_execute_document_not_found(
        self, worker, extraction_schema, db_session
    ):
        """GIVEN non-existent document WHEN executing THEN raises error."""
        task_input = {
            "document_id": str(uuid.uuid4()),
            "schema": extraction_schema,
        }

        with patch(
            "app.orchestration.workers.extraction_worker.SessionLocal"
        ) as mock_session:
            mock_session.return_value = db_session

            with pytest.raises(ValueError, match="Document not found"):
                worker.execute_task(task_input)

    def test_execute_document_not_ready(
        self, worker, document_not_ready, extraction_schema, db_session
    ):
        """GIVEN document not ready WHEN executing THEN raises error."""
        task_input = {
            "document_id": document_not_ready.id,
            "schema": extraction_schema,
        }

        with patch(
            "app.orchestration.workers.extraction_worker.SessionLocal"
        ) as mock_session:
            mock_session.return_value = db_session

            with pytest.raises(ValueError, match="not ready for extraction"):
                worker.execute_task(task_input)

    def test_execute_document_no_pages(
        self, worker, document_with_pages, extraction_schema, db_session
    ):
        """GIVEN document without pages WHEN executing THEN raises error."""
        # Remove all pages
        for page in document_with_pages.pages:
            db_session.delete(page)
        document_with_pages.pages = []
        db_session.commit()

        task_input = {
            "document_id": document_with_pages.id,
            "schema": extraction_schema,
        }

        with patch(
            "app.orchestration.workers.extraction_worker.SessionLocal"
        ) as mock_session:
            mock_session.return_value = db_session

            with pytest.raises(ValueError, match="no pages"):
                worker.execute_task(task_input)

    def test_execute_vllm_api_error(
        self, worker, document_with_pages, extraction_schema, db_session
    ):
        """GIVEN VLLM API failure WHEN executing THEN raises exception."""
        document_with_pages.pages = [document_with_pages.pages[0]]
        db_session.commit()

        worker._mock_storage.get_file.return_value = b"fake_image_data"
        worker._mock_vllm.extract_from_image.side_effect = Exception(
            "API rate limit exceeded"
        )

        task_input = {
            "document_id": document_with_pages.id,
            "schema": extraction_schema,
        }

        with patch(
            "app.orchestration.workers.extraction_worker.SessionLocal"
        ) as mock_session:
            mock_session.return_value = db_session

            with pytest.raises(Exception, match="rate limit"):
                worker.execute_task(task_input)


# ==============================================================================
# Output Format Tests
# ==============================================================================


class TestExtractionWorkerOutput:
    """Tests for output format structure."""

    def test_output_format_structure(
        self, worker, document_with_pages, extraction_schema, db_session
    ):
        """GIVEN successful extraction WHEN executing THEN output has correct structure."""
        document_with_pages.pages = [document_with_pages.pages[0]]
        db_session.commit()

        worker._mock_storage.get_file.return_value = b"fake_image_data"
        worker._mock_vllm.extract_from_image.return_value = (
            {"invoice_number": "INV-001"},
            500,
            100,
        )

        task_input = {
            "document_id": document_with_pages.id,
            "schema": extraction_schema,
        }

        with patch(
            "app.orchestration.workers.extraction_worker.SessionLocal"
        ) as mock_session:
            mock_session.return_value = db_session
            result = worker.execute_task(task_input)

        # Verify all required fields present
        assert "extracted_data" in result
        assert "pages_processed" in result
        assert "total_tokens" in result
        assert "input_tokens" in result
        assert "output_tokens" in result

        # Verify types
        assert isinstance(result["extracted_data"], dict)
        assert isinstance(result["pages_processed"], int)
        assert isinstance(result["total_tokens"], int)

    def test_token_count_tracking(
        self, worker, document_with_pages, extraction_schema, db_session
    ):
        """GIVEN extraction WHEN executing THEN tracks token counts accurately."""
        worker._mock_storage.get_file.return_value = b"fake_image_data"
        worker._mock_vllm.extract_from_image.side_effect = [
            ({"data": "1"}, 100, 25),
            ({"data": "2"}, 150, 35),
        ]

        task_input = {
            "document_id": document_with_pages.id,
            "schema": extraction_schema,
        }

        with patch(
            "app.orchestration.workers.extraction_worker.SessionLocal"
        ) as mock_session:
            mock_session.return_value = db_session
            result = worker.execute_task(task_input)

        assert result["input_tokens"] == 250  # 100 + 150
        assert result["output_tokens"] == 60  # 25 + 35
        assert result["total_tokens"] == 310  # 250 + 60


# ==============================================================================
# Provider-Specific Tests
# ==============================================================================


class TestExtractionWorkerProviders:
    """Tests for different VLLM providers."""

    @pytest.mark.parametrize(
        "provider,expected_provider",
        [
            ("google", "google"),
            ("openai", "openai"),
            ("deepseek", "deepseek"),
        ],
    )
    def test_execute_with_different_providers(
        self,
        worker,
        document_with_pages,
        extraction_schema,
        db_session,
        provider,
        expected_provider,
    ):
        """GIVEN different providers WHEN executing THEN uses correct provider."""
        document_with_pages.pages = [document_with_pages.pages[0]]
        db_session.commit()

        worker._mock_storage.get_file.return_value = b"fake_image_data"
        worker._mock_vllm.extract_from_image.return_value = (
            {"data": "test"},
            100,
            50,
        )

        task_input = {
            "document_id": document_with_pages.id,
            "schema": extraction_schema,
            "provider": provider,
        }

        with patch(
            "app.orchestration.workers.extraction_worker.SessionLocal"
        ) as mock_session:
            mock_session.return_value = db_session
            worker.execute_task(task_input)

        call_kwargs = worker._mock_vllm.extract_from_image.call_args
        assert call_kwargs.kwargs.get("provider") == expected_provider


# ==============================================================================
# Base Worker Integration Tests
# ==============================================================================


class TestExtractionWorkerBaseIntegration:
    """Tests for base worker integration."""

    def test_task_definition_name(self, worker):
        """GIVEN worker WHEN checking THEN has correct task definition name."""
        assert worker.task_definition_name == "document_extraction"

    def test_execute_calls_validate_input(self, worker, extraction_schema):
        """GIVEN invalid input WHEN executing via base THEN validation runs."""
        task = Mock()
        task.input_data = {"schema": extraction_schema}  # Missing document_id
        task.task_id = "task-123"
        task.workflow_instance_id = "wf-123"

        result = worker.execute(task)

        assert result.status.name == "FAILED"
        assert "document_id" in result.output_data.get("error", "")

    def test_db_session_cleanup_on_success(
        self, worker, document_with_pages, extraction_schema, db_session
    ):
        """GIVEN successful execution WHEN done THEN db session is closed."""
        document_with_pages.pages = [document_with_pages.pages[0]]
        db_session.commit()

        worker._mock_storage.get_file.return_value = b"fake_image_data"
        worker._mock_vllm.extract_from_image.return_value = (
            {"data": "test"},
            100,
            50,
        )

        task_input = {
            "document_id": document_with_pages.id,
            "schema": extraction_schema,
        }

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = (
            document_with_pages
        )

        with patch(
            "app.orchestration.workers.extraction_worker.SessionLocal"
        ) as mock_session:
            mock_session.return_value = mock_db
            worker.execute_task(task_input)

        mock_db.close.assert_called_once()

    def test_db_session_cleanup_on_error(
        self, worker, extraction_schema, db_session
    ):
        """GIVEN execution error WHEN done THEN db session is still closed."""
        task_input = {
            "document_id": str(uuid.uuid4()),
            "schema": extraction_schema,
        }

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch(
            "app.orchestration.workers.extraction_worker.SessionLocal"
        ) as mock_session:
            mock_session.return_value = mock_db

            with pytest.raises(ValueError):
                worker.execute_task(task_input)

        mock_db.close.assert_called_once()
