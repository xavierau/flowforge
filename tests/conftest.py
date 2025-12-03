"""Pytest configuration and fixtures for testing."""

import os
import pytest
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import User, Tenant, Role, Permission, RolePermission
from app.services.auth_service import auth_service


# Test database URLs
# SQLite for fast tests (limited - no JSONB support)
SQLITE_TEST_URL = "sqlite:///:memory:"
# PostgreSQL for tests requiring JSONB columns
# Uses the same database as development but manages tables separately per test
POSTGRES_TEST_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:password@localhost:5432/doc_processing"
)


def _check_postgres_available():
    """Check if PostgreSQL is available for testing."""
    try:
        from sqlalchemy import text
        engine = create_engine(POSTGRES_TEST_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# Cache the result
_POSTGRES_AVAILABLE = None


def postgres_available():
    """Check if PostgreSQL is available (cached)."""
    global _POSTGRES_AVAILABLE
    if _POSTGRES_AVAILABLE is None:
        _POSTGRES_AVAILABLE = _check_postgres_available()
    return _POSTGRES_AVAILABLE


@pytest.fixture(scope="function")
def db_engine():
    """
    Create a test database engine.
    Uses PostgreSQL if available (for JSONB support), otherwise SQLite.
    """
    if postgres_available():
        engine = create_engine(POSTGRES_TEST_URL)
        # Clean up any existing tables and recreate
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        yield engine
        Base.metadata.drop_all(bind=engine)
    else:
        # SQLite fallback (limited functionality)
        engine = create_engine(
            SQLITE_TEST_URL,
            connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=engine)
        yield engine
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database session override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def seed_roles(db_session: Session) -> dict[str, Role]:
    """Seed default roles for testing."""
    roles = {
        "admin": Role(
            name="admin",
            display_name="Administrator",
            description="Full system access",
            is_system=True
        ),
        "member": Role(
            name="member",
            display_name="Member",
            description="Standard user access",
            is_system=True
        ),
        "viewer": Role(
            name="viewer",
            display_name="Viewer",
            description="Read-only access",
            is_system=True
        )
    }

    for role in roles.values():
        db_session.add(role)

    db_session.commit()

    for role in roles.values():
        db_session.refresh(role)

    return roles


@pytest.fixture(scope="function")
def seed_permissions(db_session: Session) -> dict[str, Permission]:
    """Seed default permissions for testing."""
    permissions_data = [
        ("documents:create", "documents", "create", "Create documents"),
        ("documents:read", "documents", "read", "Read documents"),
        ("documents:update", "documents", "update", "Update documents"),
        ("documents:delete", "documents", "delete", "Delete documents"),
        ("schemas:create", "schemas", "create", "Create schemas"),
        ("schemas:read", "schemas", "read", "Read schemas"),
        ("schemas:update", "schemas", "update", "Update schemas"),
        ("schemas:delete", "schemas", "delete", "Delete schemas"),
        ("users:invite", "users", "invite", "Invite users"),
        ("users:read", "users", "read", "Read users"),
        ("users:update", "users", "update", "Update users"),
        ("users:delete", "users", "delete", "Delete users"),
    ]

    permissions = {}
    for name, resource, action, description in permissions_data:
        perm = Permission(
            name=name,
            resource=resource,
            action=action,
            description=description
        )
        db_session.add(perm)
        permissions[name] = perm

    db_session.commit()

    for perm in permissions.values():
        db_session.refresh(perm)

    return permissions


@pytest.fixture(scope="function")
def seed_role_permissions(
    db_session: Session,
    seed_roles: dict[str, Role],
    seed_permissions: dict[str, Permission]
) -> None:
    """Assign permissions to roles."""
    # Admin gets all permissions
    for perm in seed_permissions.values():
        role_perm = RolePermission(
            role_id=seed_roles["admin"].id,
            permission_id=perm.id
        )
        db_session.add(role_perm)

    # Member gets read/create permissions
    member_perms = [
        "documents:create", "documents:read",
        "schemas:create", "schemas:read"
    ]
    for perm_name in member_perms:
        role_perm = RolePermission(
            role_id=seed_roles["member"].id,
            permission_id=seed_permissions[perm_name].id
        )
        db_session.add(role_perm)

    # Viewer gets only read permissions
    viewer_perms = ["documents:read", "schemas:read"]
    for perm_name in viewer_perms:
        role_perm = RolePermission(
            role_id=seed_roles["viewer"].id,
            permission_id=seed_permissions[perm_name].id
        )
        db_session.add(role_perm)

    db_session.commit()


@pytest.fixture(scope="function")
def test_tenant(db_session: Session) -> Tenant:
    """Create a test tenant."""
    tenant = Tenant(
        name="Test Organization",
        slug="test-org",
        status="active",
        subscription_plan="free",
        tenant_metadata={}
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture(scope="function")
def tenant(db_session: Session) -> Tenant:
    """Create a tenant for credit tests (alias for test_tenant)."""
    tenant = Tenant(
        name="Credit Test Tenant",
        slug="credit-test-tenant",
        status="active",
        subscription_plan="pro",
        tenant_metadata={}
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture(scope="function")
def document(db_session: Session, tenant: Tenant) -> "Document":
    """Create a test document."""
    from app.models.document import Document
    doc = Document(
        tenant_id=tenant.id,
        filename="test-document.pdf",
        file_path="/test/path/document.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        status="ready_for_extraction",
        page_count=5,
        document_metadata={}
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


@pytest.fixture(scope="function")
def extraction_job(db_session: Session, document: "Document") -> "ExtractionJob":
    """Create a test extraction job."""
    from app.models.extraction_job import ExtractionJob
    job = ExtractionJob(
        document_id=document.id,
        extraction_schema={"type": "object", "properties": {}},
        model_provider="google",
        model_name="gemini-2.5-flash",
        processing_mode="batch",
        status="queued",
        credits_cost=0,
        credits_deducted=False
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture(scope="function")
def test_user(
    db_session: Session,
    test_tenant: Tenant,
    seed_roles: dict[str, Role]
) -> User:
    """Create a test user."""
    user = User(
        email="testuser@example.com",
        hashed_password=auth_service.hash_password("TestPass123"),
        full_name="Test User",
        tenant_id=test_tenant.id,
        role_id=seed_roles["member"].id,
        is_active=True,
        is_verified=True,
        locale="en"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_admin_user(
    db_session: Session,
    test_tenant: Tenant,
    seed_roles: dict[str, Role]
) -> User:
    """Create a test admin user."""
    user = User(
        email="admin@example.com",
        hashed_password=auth_service.hash_password("AdminPass123"),
        full_name="Admin User",
        tenant_id=test_tenant.id,
        role_id=seed_roles["admin"].id,
        is_active=True,
        is_verified=True,
        locale="en"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user: User, test_tenant: Tenant) -> dict[str, str]:
    """Generate auth headers with valid access token."""
    access_token = auth_service.create_access_token(
        user_id=str(test_user.id),
        tenant_id=str(test_tenant.id)
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(scope="function")
def admin_auth_headers(test_admin_user: User, test_tenant: Tenant) -> dict[str, str]:
    """Generate auth headers for admin user."""
    access_token = auth_service.create_access_token(
        user_id=str(test_admin_user.id),
        tenant_id=str(test_tenant.id)
    )
    return {"Authorization": f"Bearer {access_token}"}


# ============================================================================
# Workflow Engine Test Fixtures
# ============================================================================

import json
import os
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, MagicMock, AsyncMock
from uuid import uuid4


@pytest.fixture(scope="function")
def mock_conductor_client():
    """
    Mock Conductor API client for unit tests.
    Provides a mock that simulates Conductor API responses.
    """
    mock_client = Mock()

    # Mock workflow methods
    mock_client.start_workflow = Mock(return_value="test-workflow-execution-id")
    mock_client.get_workflow = Mock(return_value={
        "workflowId": "test-workflow-execution-id",
        "status": "RUNNING",
        "workflowType": "test_workflow",
        "version": 1,
        "startTime": datetime.utcnow().isoformat(),
        "tasks": []
    })
    mock_client.terminate_workflow = Mock(return_value=None)
    mock_client.pause_workflow = Mock(return_value=None)
    mock_client.resume_workflow = Mock(return_value=None)
    mock_client.restart_workflow = Mock(return_value=None)

    # Mock task methods
    mock_client.get_task = Mock(return_value={
        "taskId": "test-task-id",
        "taskType": "SIMPLE",
        "status": "IN_PROGRESS",
        "workflowInstanceId": "test-workflow-execution-id"
    })
    mock_client.update_task = Mock(return_value={"taskId": "test-task-id"})
    mock_client.poll_task = Mock(return_value=None)

    # Mock metadata methods
    mock_client.register_workflow_def = Mock(return_value=None)
    mock_client.register_task_def = Mock(return_value=None)
    mock_client.get_workflow_def = Mock(return_value=None)
    mock_client.get_task_def = Mock(return_value=None)

    return mock_client


@pytest.fixture(scope="session")
def conductor_test_server():
    """
    Real Conductor instance for integration tests via Docker.
    Requires docker-compose.test.yml to be running.

    Usage:
        pytest --conductor-integration
    """
    conductor_url = os.environ.get("TEST_CONDUCTOR_URL", "http://localhost:8090/api")

    # Check if Conductor is available
    import requests
    try:
        response = requests.get(f"{conductor_url}/health", timeout=5)
        if response.status_code == 200:
            yield {"url": conductor_url, "available": True}
        else:
            yield {"url": conductor_url, "available": False}
    except requests.exceptions.RequestException:
        yield {"url": conductor_url, "available": False}


@pytest.fixture(scope="function")
def sample_workflows() -> dict:
    """Load pre-built workflow definitions for testing."""
    workflows = {}
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures", "workflows")

    workflow_files = [
        "simple_extraction.json",
        "confidence_routing.json",
        "hitl_workflow.json"
    ]

    for filename in workflow_files:
        filepath = os.path.join(fixtures_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                workflow_name = filename.replace('.json', '')
                workflows[workflow_name] = json.load(f)

    return workflows


@pytest.fixture(scope="function")
def sample_schemas() -> dict:
    """Load sample JSON schemas for testing."""
    schemas = {}
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures", "schemas")

    schema_files = ["invoice_schema.json"]

    for filename in schema_files:
        filepath = os.path.join(fixtures_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                schema_name = filename.replace('.json', '')
                schemas[schema_name] = json.load(f)

    return schemas


@pytest.fixture(scope="function")
def workflow_execution_context() -> dict:
    """
    Simulated workflow execution context with node outputs.
    Used for testing expression resolution and data flow.
    """
    return {
        "workflow": {
            "workflowId": str(uuid4()),
            "input": {
                "document_id": str(uuid4()),
                "tenant_id": str(uuid4()),
                "schema": {"type": "object", "properties": {}},
                "confidence_threshold": 0.70
            }
        },
        "nodes": {
            "extract_document": {
                "output": {
                    "extracted_data": {
                        "invoice_number": "INV-2024-0001",
                        "total": 357.50,
                        "vendor": {"name": "Test Vendor Inc."}
                    },
                    "confidence_score": 0.85,
                    "pages_processed": 3,
                    "total_tokens": 1500
                }
            },
            "human_review": {
                "output": {
                    "corrected_data": {
                        "invoice_number": "INV-2024-0001",
                        "total": 360.00,
                        "vendor": {"name": "Test Vendor Inc."}
                    },
                    "corrections": [
                        {"field_path": "total", "original_value": 357.50, "corrected_value": 360.00}
                    ],
                    "review_status": "completed",
                    "quality_score": 0.90
                }
            }
        }
    }


@pytest.fixture(scope="function")
def extraction_result_factory(db_session: Session):
    """
    Factory for creating extraction results with configurable confidence.
    """
    from app.models.extraction_result import ExtractionResult

    def _create_extraction_result(
        extraction_job_id: str,
        confidence_score: float = 0.85,
        extracted_data: dict = None,
        page_number: int = 1
    ) -> ExtractionResult:
        if extracted_data is None:
            extracted_data = {
                "invoice_number": "INV-2024-0001",
                "total": 357.50,
                "currency": "USD"
            }

        result = ExtractionResult(
            extraction_job_id=extraction_job_id,
            page_number=page_number,
            extracted_data=extracted_data,
            confidence_score=confidence_score,
            tokens_used=500,
            processing_time_ms=1200
        )
        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)
        return result

    return _create_extraction_result


@pytest.fixture(scope="function")
def review_request_factory(db_session: Session, test_tenant: Tenant):
    """
    Factory for creating review requests with various states.
    """
    def _create_review_request(
        extraction_job_id: str,
        status: str = "pending",
        priority: str = "normal",
        confidence_score: float = 0.65,
        assigned_user_id: str = None,
        conductor_task_id: str = None,
        conductor_workflow_id: str = None,
        sla_hours: int = 4
    ):
        # Import here to avoid circular imports
        try:
            from app.models.review_request import ReviewRequest
        except ImportError:
            # Return a mock if model doesn't exist yet
            return Mock(
                id=str(uuid4()),
                extraction_job_id=extraction_job_id,
                status=status,
                priority=priority
            )

        review = ReviewRequest(
            id=uuid4(),
            tenant_id=test_tenant.id,
            extraction_job_id=extraction_job_id,
            status=status,
            priority=priority,
            confidence_score=confidence_score,
            assigned_user_id=assigned_user_id,
            conductor_task_id=conductor_task_id,
            conductor_workflow_id=conductor_workflow_id,
            sla_deadline=datetime.utcnow() + timedelta(hours=sla_hours),
            created_at=datetime.utcnow()
        )
        db_session.add(review)
        db_session.commit()
        db_session.refresh(review)
        return review

    return _create_review_request


@pytest.fixture(scope="function")
def time_machine():
    """
    Utility for testing time-based features (SLA, timeouts).
    Uses freezegun if available, otherwise provides a mock.
    """
    try:
        from freezegun import freeze_time
        return freeze_time
    except ImportError:
        # Fallback mock for when freezegun is not installed
        from contextlib import contextmanager

        @contextmanager
        def mock_freeze_time(target_time):
            """Mock freeze_time that doesn't actually freeze time."""
            yield
        return mock_freeze_time


@pytest.fixture(scope="function")
def mock_vllm_service():
    """Mock VLLM service for testing extraction without real API calls."""
    mock_service = AsyncMock()

    mock_service.extract_from_image = AsyncMock(return_value=(
        {
            "invoice_number": "INV-2024-0001",
            "invoice_date": "2024-01-15",
            "total": 357.50,
            "currency": "USD",
            "vendor": {"name": "Test Vendor Inc."},
            "line_items": [
                {"description": "Product A", "quantity": 2, "amount": 100.00}
            ]
        },
        500,  # input_tokens
        200   # output_tokens
    ))

    mock_service.get_available_providers = Mock(return_value=["google", "openai"])
    mock_service.get_provider = Mock(return_value=Mock())

    return mock_service


@pytest.fixture(scope="function")
def mock_http_response():
    """Mock HTTP response for testing HTTP request worker."""
    def _create_response(
        status_code: int = 200,
        json_data: dict = None,
        text: str = None,
        headers: dict = None
    ):
        response = Mock()
        response.status_code = status_code
        response.headers = headers or {"Content-Type": "application/json"}

        if json_data is not None:
            response.json = Mock(return_value=json_data)
            response.text = json.dumps(json_data)
        else:
            response.json = Mock(side_effect=ValueError("No JSON"))
            response.text = text or ""

        return response

    return _create_response


@pytest.fixture(scope="function")
def completed_extraction_job(
    db_session: Session,
    document: "Document",
    extraction_result_factory
) -> "ExtractionJob":
    """Create a completed extraction job with results for HITL testing."""
    from app.models.extraction_job import ExtractionJob

    job = ExtractionJob(
        document_id=document.id,
        extraction_schema={"type": "object", "properties": {}},
        model_provider="google",
        model_name="gemini-2.5-flash",
        processing_mode="batch",
        status="completed",
        credits_cost=5,
        credits_deducted=True,
        confidence_score=0.65,  # Low enough to trigger review
        started_at=datetime.utcnow() - timedelta(minutes=5),
        completed_at=datetime.utcnow()
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    # Create extraction result
    extraction_result_factory(
        extraction_job_id=str(job.id),
        confidence_score=0.65,
        extracted_data={
            "invoice_number": "INV-2024-0001",
            "total": 357.50,
            "vendor": {"name": "Test Vendor Inc."}
        }
    )

    return job


@pytest.fixture(scope="function")
def high_confidence_extraction_job(
    db_session: Session,
    document: "Document",
    extraction_result_factory
) -> "ExtractionJob":
    """Create a high-confidence extraction job for auto-approve testing."""
    from app.models.extraction_job import ExtractionJob

    job = ExtractionJob(
        document_id=document.id,
        extraction_schema={"type": "object", "properties": {}},
        model_provider="google",
        model_name="gemini-2.5-flash",
        processing_mode="batch",
        status="completed",
        credits_cost=5,
        credits_deducted=True,
        confidence_score=0.92,  # High enough for auto-approve
        started_at=datetime.utcnow() - timedelta(minutes=5),
        completed_at=datetime.utcnow()
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    # Create extraction result
    extraction_result_factory(
        extraction_job_id=str(job.id),
        confidence_score=0.92,
        extracted_data={
            "invoice_number": "INV-2024-0001",
            "total": 357.50,
            "vendor": {"name": "Test Vendor Inc."}
        }
    )

    return job


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (may require external services)"
    )
    config.addinivalue_line(
        "markers", "workflow: Workflow engine tests"
    )
    config.addinivalue_line(
        "markers", "hitl: Human-in-the-loop tests"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow-running tests"
    )
    config.addinivalue_line(
        "markers", "conductor: Tests requiring real Conductor instance"
    )
    config.addinivalue_line(
        "markers", "postgres: Tests requiring PostgreSQL (JSONB support)"
    )


def pytest_collection_modifyitems(config, items):
    """
    Skip tests based on available infrastructure.
    """
    skip_conductor = pytest.mark.skip(reason="Conductor not available")
    skip_postgres = pytest.mark.skip(reason="PostgreSQL not available (required for JSONB)")

    for item in items:
        # Skip Conductor tests if not explicitly enabled
        if "conductor" in item.keywords:
            if not config.getoption("--conductor-integration", default=False):
                item.add_marker(skip_conductor)

        # Skip PostgreSQL tests if PostgreSQL is not available
        if "postgres" in item.keywords:
            if not postgres_available():
                item.add_marker(skip_postgres)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--conductor-integration",
        action="store_true",
        default=False,
        help="Run tests that require a real Conductor instance"
    )
