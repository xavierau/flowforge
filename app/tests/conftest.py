"""Pytest configuration and fixtures for markdown pipeline tests.

Provides common test fixtures for database, API clients, mocks, and sample data.
"""

import base64
import io
import json
import os
from datetime import datetime
from typing import Generator, Dict, Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import (
    Document,
    DocumentPage,
    ExtractionJob,
    Tenant,
    User,
)
from app.models.enums import (
    DocumentStatus,
    JobStatus,
    MarkdownFormat,
    ProcessingMode,
)


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def db_engine():
    """Create in-memory SQLite database engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create database session for testing."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=db_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def test_client(db_session) -> TestClient:
    """Create FastAPI test client with test database."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ============================================================================
# Test Data Factories
# ============================================================================


@pytest.fixture
def create_test_tenant(db_session) -> callable:
    """Factory for creating test tenants."""

    def _create_tenant(
        name: str = "Test Tenant",
        credits: int = 1000,
    ) -> Tenant:
        tenant = Tenant(
            id=uuid4(),
            name=name,
            credits=credits,
            created_at=datetime.utcnow(),
        )
        db_session.add(tenant)
        db_session.commit()
        db_session.refresh(tenant)
        return tenant

    return _create_tenant


@pytest.fixture
def create_test_user(db_session) -> callable:
    """Factory for creating test users."""

    def _create_user(
        tenant_id: str,
        email: str = "test@example.com",
        is_active: bool = True,
    ) -> User:
        user = User(
            id=uuid4(),
            tenant_id=tenant_id,
            email=email,
            hashed_password="hashed_password_here",
            is_active=is_active,
            created_at=datetime.utcnow(),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _create_user


@pytest.fixture
def create_test_document(db_session) -> callable:
    """Factory for creating test documents."""

    def _create_document(
        tenant_id: str,
        filename: str = "test_invoice.pdf",
        status: str = DocumentStatus.READY_FOR_EXTRACTION.value,
        num_pages: int = 2,
    ) -> Document:
        document = Document(
            id=uuid4(),
            tenant_id=tenant_id,
            filename=filename,
            file_path=f"documents/{uuid4()}/test_invoice.pdf",
            status=status,
            num_pages=num_pages,
            created_at=datetime.utcnow(),
        )
        db_session.add(document)
        db_session.commit()
        db_session.refresh(document)

        # Create pages
        for page_num in range(1, num_pages + 1):
            page = DocumentPage(
                id=uuid4(),
                document_id=document.id,
                page_number=page_num,
                image_path=f"documents/{document.id}/page_{page_num}.png",
                preprocessed_image_path=f"documents/{document.id}/page_{page_num}_preprocessed.png",
            )
            db_session.add(page)

        db_session.commit()
        db_session.refresh(document)
        return document

    return _create_document


@pytest.fixture
def create_test_extraction_job(db_session) -> callable:
    """Factory for creating test extraction jobs."""

    def _create_job(
        document_id: str,
        tenant_id: str,
        status: str = JobStatus.QUEUED.value,
        processing_mode: str = ProcessingMode.MARKDOWN.value,
        markdown_converter: str = "gemini_vision",
        markdown_format: str = MarkdownFormat.STANDARD.value,
        extraction_schema: Dict[str, Any] = None,
    ) -> ExtractionJob:
        if extraction_schema is None:
            extraction_schema = {
                "type": "object",
                "properties": {
                    "invoice_number": {"type": "string"},
                    "total": {"type": "number"},
                },
            }

        job = ExtractionJob(
            id=uuid4(),
            document_id=document_id,
            tenant_id=tenant_id,
            status=status,
            processing_mode=processing_mode,
            markdown_converter=markdown_converter,
            markdown_format=markdown_format,
            extraction_schema=extraction_schema,
            model_provider="google",
            model_name="gemini-2.0-flash-001",
            created_at=datetime.utcnow(),
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        return job

    return _create_job


# ============================================================================
# Sample Data Fixtures
# ============================================================================


@pytest.fixture
def sample_invoice_image_base64() -> str:
    """Generate base64-encoded sample invoice image."""
    # Create a simple test image
    img = Image.new("RGB", (800, 1000), color=(255, 255, 255))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


@pytest.fixture
def sample_receipt_image_base64() -> str:
    """Generate base64-encoded sample receipt image."""
    img = Image.new("RGB", (600, 800), color=(240, 240, 240))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


@pytest.fixture
def sample_invoice_schema() -> Dict[str, Any]:
    """Sample invoice extraction schema."""
    return {
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string"},
            "date": {"type": "string"},
            "vendor_name": {"type": "string"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "quantity": {"type": "number"},
                        "unit_price": {"type": "number"},
                        "total": {"type": "number"},
                    },
                    "required": ["description", "quantity", "unit_price", "total"],
                },
            },
            "subtotal": {"type": "number"},
            "tax": {"type": "number"},
            "total": {"type": "number"},
        },
        "required": ["invoice_number", "date", "vendor_name", "total"],
    }


@pytest.fixture
def sample_receipt_schema() -> Dict[str, Any]:
    """Sample receipt extraction schema."""
    return {
        "type": "object",
        "properties": {
            "merchant_name": {"type": "string"},
            "date": {"type": "string"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "price": {"type": "number"},
                    },
                },
            },
            "total": {"type": "number"},
            "payment_method": {"type": "string"},
        },
        "required": ["merchant_name", "date", "total"],
    }


@pytest.fixture
def sample_markdown_single_page() -> str:
    """Sample markdown content for single page."""
    return """<!-- PAGE 1 -->
# Invoice

**Invoice Number:** INV-2024-001
**Date:** January 15, 2024
**Vendor:** Acme Corporation

## Items

| Description | Quantity | Unit Price | Total |
|-------------|----------|------------|-------|
| Widget A    | 10       | $50.00     | $500.00 |
| Widget B    | 5        | $30.00     | $150.00 |

## Summary

**Subtotal:** $650.00
**Tax (10%):** $65.00
**Total:** $715.00
"""


@pytest.fixture
def sample_markdown_multi_page() -> str:
    """Sample markdown content for multiple pages."""
    return """<!-- PAGE 1 -->
# Invoice

**Invoice Number:** INV-2024-001
**Date:** January 15, 2024
**Vendor:** Acme Corporation

## Items

| Description | Quantity | Unit Price | Total |
|-------------|----------|------------|-------|
| Widget A    | 10       | $50.00     | $500.00 |
| Widget B    | 5        | $30.00     | $150.00 |

<!-- PAGE 2 -->
## Summary

**Subtotal:** $650.00
**Tax (10%):** $65.00
**Total:** $715.00

## Payment Terms

Payment due within 30 days.
Bank Transfer: Account 12345678
"""


@pytest.fixture
def sample_extracted_invoice_data() -> Dict[str, Any]:
    """Sample extracted invoice data."""
    return {
        "invoice_number": "INV-2024-001",
        "date": "January 15, 2024",
        "vendor_name": "Acme Corporation",
        "items": [
            {
                "description": "Widget A",
                "quantity": 10,
                "unit_price": 50.00,
                "total": 500.00,
            },
            {
                "description": "Widget B",
                "quantity": 5,
                "unit_price": 30.00,
                "total": 150.00,
            },
        ],
        "subtotal": 650.00,
        "tax": 65.00,
        "total": 715.00,
    }


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_google_api_key(monkeypatch):
    """Mock Google API key in settings."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test_google_api_key")
    from app.config import settings

    settings.google_api_key = "test_google_api_key"
    return settings


@pytest.fixture
def mock_openai_api_key(monkeypatch):
    """Mock OpenAI API key in settings."""
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_api_key")
    from app.config import settings

    settings.openai_api_key = "test_openai_api_key"
    return settings


@pytest.fixture
def mock_both_api_keys(monkeypatch):
    """Mock both Google and OpenAI API keys."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test_google_api_key")
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_api_key")
    from app.config import settings

    settings.google_api_key = "test_google_api_key"
    settings.openai_api_key = "test_openai_api_key"
    return settings


@pytest.fixture
def celery_eager_mode(monkeypatch):
    """Configure Celery to run tasks synchronously for testing."""
    from app.tasks.celery_app import celery_app

    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )
    yield celery_app
    celery_app.conf.update(
        task_always_eager=False,
        task_eager_propagates=False,
    )


# ============================================================================
# Cleanup Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_factory_singleton():
    """Reset converter factory singleton between tests."""
    yield
    # Reset factory singleton
    from app.services.converters import converter_factory

    converter_factory._factory_instance = None
