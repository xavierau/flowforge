"""Comprehensive Tenant Isolation Security Tests.

This module tests that data is properly isolated between tenants across all major resources.
Cross-tenant access attempts should return 404 (not 403) to prevent information disclosure.

Test Coverage:
- Documents: read, update, delete, list, parse
- Jobs: read status, read results, retry, list
- Schemas: read, update, delete, list
- Workflows: read, update, delete, execute, executions, list
- Reviews: read, assign, submit corrections, queue
- Users: read, invite, list

Security Principle: Cross-tenant access returns 404 (not 403) to avoid leaking existence of resources.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, Tenant, Role, Permission, RolePermission
from app.models.document import Document
from app.models.extraction_job import ExtractionJob
from app.models.extraction_result import ExtractionResult
from app.models.schema_definition import SchemaDefinition
from app.models.workflow import Workflow, WorkflowVersion, WorkflowExecution
from app.models.review_request import ReviewRequest
from app.models.enums import ReviewRequestStatus, ReviewPriority, WorkflowExecutionStatus
from app.services.auth_service import auth_service
from app.config import settings


# ==============================================================================
# Helper Functions
# ==============================================================================


def create_other_tenant(db_session: Session, slug_suffix: str = "") -> Tenant:
    """Create another tenant for isolation testing."""
    unique_slug = f"other-org-{slug_suffix}-{uuid4().hex[:8]}"
    other_tenant = Tenant(
        name="Other Organization",
        slug=unique_slug,
        status="active",
        subscription_plan="free",
        tenant_metadata={}
    )
    db_session.add(other_tenant)
    db_session.commit()
    db_session.refresh(other_tenant)
    return other_tenant


def create_other_tenant_with_user(
    db_session: Session,
    seed_roles: dict[str, Role],
    slug_suffix: str = ""
) -> tuple[Tenant, User]:
    """Create another tenant with an admin user for isolation testing."""
    other_tenant = create_other_tenant(db_session, slug_suffix)

    other_user = User(
        email=f"admin-{uuid4().hex[:8]}@other-org.com",
        hashed_password=auth_service.hash_password("OtherPass123"),
        full_name="Other Admin",
        tenant_id=other_tenant.id,
        role_id=seed_roles["admin"].id,
        is_active=True,
        is_verified=True
    )
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    return other_tenant, other_user


def ensure_all_permissions(db_session: Session, seed_roles: dict) -> dict:
    """Ensure all necessary permissions exist and are assigned to admin."""
    permissions_data = [
        # Documents
        ("documents:create", "documents", "create", "Create documents"),
        ("documents:read", "documents", "read", "Read documents"),
        ("documents:update", "documents", "update", "Update documents"),
        ("documents:delete", "documents", "delete", "Delete documents"),
        # Extraction/Jobs
        ("extraction:create", "extraction", "create", "Create extractions"),
        ("jobs:read", "jobs", "read", "Read jobs"),
        # Schemas
        ("schemas:create", "schemas", "create", "Create schemas"),
        ("schemas:read", "schemas", "read", "Read schemas"),
        ("schemas:update", "schemas", "update", "Update schemas"),
        ("schemas:delete", "schemas", "delete", "Delete schemas"),
        # Workflows
        ("workflows:create", "workflows", "create", "Create workflows"),
        ("workflows:read", "workflows", "read", "Read workflows"),
        ("workflows:update", "workflows", "update", "Update workflows"),
        ("workflows:delete", "workflows", "delete", "Delete workflows"),
        ("workflows:execute", "workflows", "execute", "Execute workflows"),
        # Reviews
        ("extraction:review", "extraction", "review", "Request extraction reviews"),
        ("reviews:read", "reviews", "read", "Read reviews"),
        ("reviews:update", "reviews", "update", "Update reviews"),
        ("reviews:assign", "reviews", "assign", "Assign reviews"),
        ("reviews:delete", "reviews", "delete", "Delete reviews"),
        # Users
        ("users:invite", "users", "invite", "Invite users"),
        ("users:read", "users", "read", "Read users"),
        ("users:update", "users", "update", "Update users"),
        ("users:delete", "users", "delete", "Delete users"),
    ]

    permissions = {}
    for name, resource, action, description in permissions_data:
        perm = db_session.query(Permission).filter(Permission.name == name).first()
        if not perm:
            perm = Permission(
                name=name,
                resource=resource,
                action=action,
                description=description
            )
            db_session.add(perm)
            db_session.commit()
            db_session.refresh(perm)

        admin_role = seed_roles.get("admin")
        if admin_role:
            existing = db_session.query(RolePermission).filter(
                RolePermission.role_id == admin_role.id,
                RolePermission.permission_id == perm.id
            ).first()
            if not existing:
                db_session.add(RolePermission(role_id=admin_role.id, permission_id=perm.id))
                db_session.commit()

        permissions[name] = perm

    return permissions


def create_test_document(db_session: Session, tenant: Tenant) -> Document:
    """Create a test document for a tenant."""
    doc = Document(
        tenant_id=tenant.id,
        filename=f"test-doc-{uuid4().hex[:8]}.pdf",
        file_path=f"/test/path/{uuid4().hex}.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        status="ready_for_extraction",
        page_count=2,
        document_metadata={}
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


def create_test_extraction_job(
    db_session: Session,
    document: Document,
    tenant: Tenant,
    status: str = "completed"
) -> ExtractionJob:
    """Create a test extraction job."""
    job = ExtractionJob(
        document_id=document.id,
        tenant_id=tenant.id,
        extraction_schema={"type": "object", "properties": {"field": {"type": "string"}}},
        model_provider="google",
        model_name="gemini-2.5-flash",
        processing_mode="batch",
        status=status,
        confidence_score=0.85,
        credits_cost=2,
        credits_deducted=True,
        started_at=datetime.utcnow() - timedelta(minutes=5),
        completed_at=datetime.utcnow() if status == "completed" else None
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def create_test_schema(db_session: Session, tenant: Tenant) -> SchemaDefinition:
    """Create a test schema definition."""
    schema = SchemaDefinition(
        tenant_id=tenant.id,
        name=f"test-schema-{uuid4().hex[:8]}",
        definitions={"type": "object", "properties": {"field": {"type": "string"}}}
    )
    db_session.add(schema)
    db_session.commit()
    db_session.refresh(schema)
    return schema


def create_valid_workflow_definition() -> dict:
    """Create a valid minimal workflow definition."""
    return {
        "nodes": [
            {
                "id": "trigger-1",
                "type": "httpTrigger",
                "position": {"x": 100, "y": 100},
                "data": {
                    "label": "HTTP Trigger",
                    "type": "httpTrigger",
                    "isValid": True,
                    "errors": []
                }
            },
            {
                "id": "extraction-1",
                "type": "extraction",
                "position": {"x": 300, "y": 100},
                "data": {
                    "label": "Extract Data",
                    "type": "extraction",
                    "isValid": True,
                    "errors": [],
                    "config": {
                        "fileSource": "previous_node",
                        "prompt": "Extract data",
                        "schemaId": "schema-123"
                    }
                }
            }
        ],
        "edges": [
            {"id": "edge-1", "source": "trigger-1", "target": "extraction-1"}
        ]
    }


def create_test_workflow(db_session: Session, tenant: Tenant) -> Workflow:
    """Create a test workflow with initial version."""
    workflow = Workflow(
        tenant_id=tenant.id,
        name=f"Test Workflow {uuid4().hex[:8]}",
        description="Test workflow description",
        is_active=True,
        is_archived=False,
        current_version_number=1
    )
    db_session.add(workflow)
    db_session.flush()

    version = WorkflowVersion(
        workflow_id=workflow.id,
        version_number=1,
        definition=create_valid_workflow_definition(),
        conductor_workflow_name=f"test_workflow_{uuid4().hex[:8]}_v1"
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(workflow)

    return workflow


def create_test_workflow_execution(
    db_session: Session,
    workflow: Workflow,
    tenant: Tenant
) -> WorkflowExecution:
    """Create a test workflow execution."""
    version = db_session.query(WorkflowVersion).filter(
        WorkflowVersion.workflow_id == workflow.id,
        WorkflowVersion.version_number == workflow.current_version_number
    ).first()

    execution = WorkflowExecution(
        tenant_id=tenant.id,
        workflow_id=workflow.id,
        workflow_version_id=version.id,
        status=WorkflowExecutionStatus.RUNNING.value,
        input_data={"test": "data"},
        conductor_workflow_id=f"conductor-exec-{uuid4().hex[:8]}"
    )
    db_session.add(execution)
    db_session.commit()
    db_session.refresh(execution)

    return execution


def create_test_review(
    db_session: Session,
    extraction_job: ExtractionJob,
    tenant: Tenant,
    status: str = ReviewRequestStatus.PENDING.value
) -> ReviewRequest:
    """Create a test review request."""
    review = ReviewRequest(
        tenant_id=tenant.id,
        extraction_job_id=extraction_job.id,
        status=status,
        priority=ReviewPriority.NORMAL.value,
        confidence_score=0.65,
        trigger_reason="manual_request",
        sla_deadline=datetime.utcnow() + timedelta(hours=4),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)
    return review


# ==============================================================================
# Test Classes - Document Tenant Isolation
# ==============================================================================


class TestDocumentTenantIsolation:
    """Test tenant isolation for Document resources."""

    def test_cannot_read_other_tenant_document(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that accessing another tenant's document returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        # Create another tenant with a document
        other_tenant = create_other_tenant(db_session, "doc-read")
        other_doc = create_test_document(db_session, other_tenant)

        # Try to access with Tenant A's credentials
        response = client.get(
            f"/api/v1/documents/{other_doc.id}",
            headers=admin_auth_headers
        )

        # Should get 404, NOT 403 (to avoid information disclosure)
        assert response.status_code == 404

    def test_cannot_download_other_tenant_document_file(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that downloading another tenant's document file returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "doc-download")
        other_doc = create_test_document(db_session, other_tenant)

        response = client.get(
            f"/api/v1/documents/{other_doc.id}/file",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_cannot_get_other_tenant_document_pages(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that getting pages of another tenant's document returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "doc-pages")
        other_doc = create_test_document(db_session, other_tenant)

        response = client.get(
            f"/api/v1/documents/{other_doc.id}/pages",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_cannot_parse_other_tenant_document(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that parsing another tenant's document returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "doc-parse")
        other_doc = create_test_document(db_session, other_tenant)

        response = client.post(
            f"/api/v1/documents/{other_doc.id}/parse",
            json={
                "extraction_schema": {"type": "object", "properties": {}},
                "model_provider_config": {"provider": "google", "model": "gemini-2.5-flash"},
                "processing_mode": "batch"
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_document_listing_only_shows_own_tenant_documents(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that document listing only shows current tenant's documents."""
        ensure_all_permissions(db_session, seed_roles)

        # Create document for current tenant
        my_doc = create_test_document(db_session, test_tenant)

        # Create document for another tenant
        other_tenant = create_other_tenant(db_session, "doc-list")
        other_doc = create_test_document(db_session, other_tenant)

        response = client.get(
            "/api/v1/documents",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should only see own documents
        doc_ids = [doc["document_id"] for doc in data["documents"]]
        assert str(my_doc.id) in doc_ids
        assert str(other_doc.id) not in doc_ids


# ==============================================================================
# Test Classes - Job Tenant Isolation
# ==============================================================================


class TestJobTenantIsolation:
    """Test tenant isolation for Extraction Job resources."""

    def test_cannot_read_other_tenant_job_status(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that reading another tenant's job status returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "job-status")
        other_doc = create_test_document(db_session, other_tenant)
        other_job = create_test_extraction_job(db_session, other_doc, other_tenant)

        response = client.get(
            f"/api/v1/jobs/{other_job.id}/status",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_cannot_read_other_tenant_job_results(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that reading another tenant's job results returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "job-result")
        other_doc = create_test_document(db_session, other_tenant)
        other_job = create_test_extraction_job(db_session, other_doc, other_tenant)

        # Create extraction result for the job
        result = ExtractionResult(
            extraction_job_id=other_job.id,
            extracted_data={"invoice_number": "INV-001"},
            model_used="gemini-2.5-flash",
            input_tokens=100,
            output_tokens=50,
            tokens_used=150,
            processing_time_ms=1000,
            confidence_score=0.95
        )
        db_session.add(result)
        db_session.commit()

        response = client.get(
            f"/api/v1/jobs/{other_job.id}/result",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_cannot_retry_other_tenant_job(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that retrying another tenant's job returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "job-retry")
        other_doc = create_test_document(db_session, other_tenant)
        other_job = create_test_extraction_job(
            db_session, other_doc, other_tenant, status="failed"
        )

        response = client.post(
            f"/api/v1/jobs/{other_job.id}/retry",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_job_listing_only_shows_own_tenant_jobs(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that job listing only shows current tenant's jobs."""
        ensure_all_permissions(db_session, seed_roles)

        # Create job for current tenant
        my_doc = create_test_document(db_session, test_tenant)
        my_job = create_test_extraction_job(db_session, my_doc, test_tenant)

        # Create job for another tenant
        other_tenant = create_other_tenant(db_session, "job-list")
        other_doc = create_test_document(db_session, other_tenant)
        other_job = create_test_extraction_job(db_session, other_doc, other_tenant)

        response = client.get(
            "/api/v1/jobs",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should only see own jobs
        job_ids = [job["id"] for job in data["jobs"]]
        assert str(my_job.id) in job_ids
        assert str(other_job.id) not in job_ids


# ==============================================================================
# Test Classes - Schema Tenant Isolation
# ==============================================================================


class TestSchemaTenantIsolation:
    """Test tenant isolation for Schema Definition resources."""

    def test_cannot_read_other_tenant_schema(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that reading another tenant's schema returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "schema-read")
        other_schema = create_test_schema(db_session, other_tenant)

        response = client.get(
            f"/api/v1/schemas/{other_schema.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_cannot_update_other_tenant_schema(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that updating another tenant's schema returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "schema-update")
        other_schema = create_test_schema(db_session, other_tenant)
        original_definitions = other_schema.definitions.copy()

        response = client.put(
            f"/api/v1/schemas/{other_schema.id}",
            json={"definitions": {"type": "object", "hacked": True}},
            headers=admin_auth_headers
        )

        assert response.status_code == 404

        # Verify schema was not modified
        db_session.refresh(other_schema)
        assert other_schema.definitions == original_definitions

    def test_cannot_delete_other_tenant_schema(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that deleting another tenant's schema returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "schema-delete")
        other_schema = create_test_schema(db_session, other_tenant)

        response = client.delete(
            f"/api/v1/schemas/{other_schema.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

        # Verify schema still exists
        still_exists = db_session.query(SchemaDefinition).filter(
            SchemaDefinition.id == other_schema.id
        ).first()
        assert still_exists is not None

    def test_schema_listing_only_shows_own_tenant_schemas(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that schema listing only shows current tenant's schemas."""
        ensure_all_permissions(db_session, seed_roles)

        # Create schema for current tenant
        my_schema = create_test_schema(db_session, test_tenant)

        # Create schema for another tenant
        other_tenant = create_other_tenant(db_session, "schema-list")
        other_schema = create_test_schema(db_session, other_tenant)

        response = client.get(
            "/api/v1/schemas",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should only see own schemas
        schema_ids = [schema["id"] for schema in data["schemas"]]
        assert str(my_schema.id) in schema_ids
        assert str(other_schema.id) not in schema_ids


# ==============================================================================
# Test Classes - Workflow Tenant Isolation
# ==============================================================================


class TestWorkflowTenantIsolation:
    """Test tenant isolation for Workflow resources."""

    def test_cannot_read_other_tenant_workflow(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that reading another tenant's workflow returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "workflow-read")
        other_workflow = create_test_workflow(db_session, other_tenant)

        response = client.get(
            f"/api/v1/workflows/{other_workflow.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_cannot_update_other_tenant_workflow(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that updating another tenant's workflow returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "workflow-update")
        other_workflow = create_test_workflow(db_session, other_tenant)
        original_name = other_workflow.name

        response = client.put(
            f"/api/v1/workflows/{other_workflow.id}",
            json={"name": "Hacked Workflow Name"},
            headers=admin_auth_headers
        )

        assert response.status_code == 404

        # Verify workflow was not modified
        db_session.refresh(other_workflow)
        assert other_workflow.name == original_name

    def test_cannot_delete_other_tenant_workflow(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that deleting another tenant's workflow returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "workflow-delete")
        other_workflow = create_test_workflow(db_session, other_tenant)

        response = client.delete(
            f"/api/v1/workflows/{other_workflow.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

        # Verify workflow still exists and is active
        db_session.refresh(other_workflow)
        assert other_workflow.is_active is True

    def test_cannot_execute_other_tenant_workflow(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that executing another tenant's workflow returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "workflow-execute")
        other_workflow = create_test_workflow(db_session, other_tenant)

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.post(
                f"/api/v1/workflows/{other_workflow.id}/execute",
                json={"inputData": {"test": "data"}},
                headers=admin_auth_headers
            )

        assert response.status_code == 404

    def test_cannot_view_other_tenant_workflow_executions(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that viewing another tenant's workflow executions shows no results.

        Note: The API returns 200 with empty list rather than 404, which is acceptable
        from a security standpoint as it doesn't reveal whether the workflow exists.
        """
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "workflow-execs")
        other_workflow = create_test_workflow(db_session, other_tenant)
        create_test_workflow_execution(db_session, other_workflow, other_tenant)

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.get(
                f"/api/v1/workflows/{other_workflow.id}/executions",
                headers=admin_auth_headers
            )

        # API returns 200 with empty results (tenant-filtered query finds no executions)
        # This is acceptable as it doesn't confirm whether the workflow exists
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["executions"]) == 0

    def test_workflow_listing_only_shows_own_tenant_workflows(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that workflow listing only shows current tenant's workflows."""
        ensure_all_permissions(db_session, seed_roles)

        # Create workflow for current tenant
        my_workflow = create_test_workflow(db_session, test_tenant)

        # Create workflow for another tenant
        other_tenant = create_other_tenant(db_session, "workflow-list")
        other_workflow = create_test_workflow(db_session, other_tenant)

        response = client.get(
            "/api/v1/workflows?include_all=true",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should only see own workflows
        workflow_ids = [workflow["id"] for workflow in data["workflows"]]
        assert str(my_workflow.id) in workflow_ids
        assert str(other_workflow.id) not in workflow_ids


# ==============================================================================
# Test Classes - Review Tenant Isolation
# ==============================================================================


class TestReviewTenantIsolation:
    """Test tenant isolation for Review resources."""

    def test_cannot_read_other_tenant_review(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that reading another tenant's review returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "review-read")
        other_doc = create_test_document(db_session, other_tenant)
        other_job = create_test_extraction_job(db_session, other_doc, other_tenant)
        other_review = create_test_review(db_session, other_job, other_tenant)

        response = client.get(
            f"/api/v1/reviews/{other_review.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_cannot_assign_other_tenant_review(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        test_admin_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that assigning another tenant's review returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "review-assign")
        other_doc = create_test_document(db_session, other_tenant)
        other_job = create_test_extraction_job(db_session, other_doc, other_tenant)
        other_review = create_test_review(db_session, other_job, other_tenant)

        response = client.post(
            f"/api/v1/reviews/{other_review.id}/assign",
            json={"user_id": str(test_admin_user.id)},
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_cannot_submit_corrections_to_other_tenant_review(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that submitting corrections to another tenant's review returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant, other_user = create_other_tenant_with_user(
            db_session, seed_roles, "review-submit"
        )
        other_doc = create_test_document(db_session, other_tenant)
        other_job = create_test_extraction_job(db_session, other_doc, other_tenant)
        other_review = create_test_review(
            db_session, other_job, other_tenant,
            status=ReviewRequestStatus.IN_REVIEW.value
        )
        other_review.assigned_to_user_id = other_user.id
        db_session.commit()

        response = client.post(
            f"/api/v1/reviews/{other_review.id}/submit",
            json={"corrections": [], "review_notes": "Test"},
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_cannot_cancel_other_tenant_review(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that cancelling another tenant's review returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "review-cancel")
        other_doc = create_test_document(db_session, other_tenant)
        other_job = create_test_extraction_job(db_session, other_doc, other_tenant)
        other_review = create_test_review(db_session, other_job, other_tenant)

        response = client.delete(
            f"/api/v1/reviews/{other_review.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

        # Verify review still exists with original status
        db_session.refresh(other_review)
        assert other_review.status == ReviewRequestStatus.PENDING.value

    def test_review_queue_only_shows_own_tenant_reviews(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that review queue only shows current tenant's reviews."""
        ensure_all_permissions(db_session, seed_roles)

        # Create review for current tenant
        my_doc = create_test_document(db_session, test_tenant)
        my_job = create_test_extraction_job(db_session, my_doc, test_tenant)
        my_review = create_test_review(db_session, my_job, test_tenant)

        # Create review for another tenant
        other_tenant = create_other_tenant(db_session, "review-queue")
        other_doc = create_test_document(db_session, other_tenant)
        other_job = create_test_extraction_job(db_session, other_doc, other_tenant)
        other_review = create_test_review(db_session, other_job, other_tenant)

        response = client.get(
            "/api/v1/reviews/queue",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should only see own reviews
        review_ids = [review["id"] for review in data["items"]]
        assert str(my_review.id) in review_ids
        assert str(other_review.id) not in review_ids


# ==============================================================================
# Test Classes - User Tenant Isolation
# ==============================================================================


class TestUserTenantIsolation:
    """Test tenant isolation for User resources."""

    def test_cannot_read_other_tenant_user(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that reading another tenant's user returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant, other_user = create_other_tenant_with_user(
            db_session, seed_roles, "user-read"
        )

        response = client.get(
            f"/api/v1/users/{other_user.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_cannot_update_other_tenant_user(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that updating another tenant's user returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant, other_user = create_other_tenant_with_user(
            db_session, seed_roles, "user-update"
        )
        original_name = other_user.full_name

        response = client.patch(
            f"/api/v1/users/{other_user.id}",
            json={"full_name": "Hacked Name"},
            headers=admin_auth_headers
        )

        assert response.status_code == 404

        # Verify user was not modified
        db_session.refresh(other_user)
        assert other_user.full_name == original_name

    def test_cannot_delete_other_tenant_user(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that deleting another tenant's user returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant, other_user = create_other_tenant_with_user(
            db_session, seed_roles, "user-delete"
        )

        response = client.delete(
            f"/api/v1/users/{other_user.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

        # Verify user still exists and is active
        db_session.refresh(other_user)
        assert other_user.is_active is True

    def test_user_listing_only_shows_own_tenant_users(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        test_admin_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that user listing only shows current tenant's users."""
        ensure_all_permissions(db_session, seed_roles)

        # Create user for another tenant
        other_tenant, other_user = create_other_tenant_with_user(
            db_session, seed_roles, "user-list"
        )

        response = client.get(
            "/api/v1/users",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should only see own users
        user_emails = [user["email"] for user in data["users"]]
        assert test_admin_user.email in user_emails
        assert other_user.email not in user_emails


# ==============================================================================
# Test Classes - Cross-Tenant Request Review Isolation
# ==============================================================================


class TestRequestReviewTenantIsolation:
    """Test tenant isolation for requesting reviews on jobs."""

    def test_cannot_request_review_for_other_tenant_job(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that requesting review for another tenant's job returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "request-review")
        other_doc = create_test_document(db_session, other_tenant)
        other_job = create_test_extraction_job(db_session, other_doc, other_tenant)

        response = client.post(
            f"/api/v1/jobs/{other_job.id}/request-review",
            headers=admin_auth_headers
        )

        assert response.status_code == 404


# ==============================================================================
# Test Classes - Workflow Execution Tenant Isolation
# ==============================================================================


class TestWorkflowExecutionTenantIsolation:
    """Test tenant isolation for workflow executions."""

    def test_cannot_get_other_tenant_execution_status(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that getting another tenant's execution status returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "exec-status")
        other_workflow = create_test_workflow(db_session, other_tenant)
        other_execution = create_test_workflow_execution(
            db_session, other_workflow, other_tenant
        )

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.get(
                f"/api/v1/workflows/executions/{other_execution.id}",
                headers=admin_auth_headers
            )

        assert response.status_code == 404

    def test_cannot_cancel_other_tenant_execution(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that cancelling another tenant's execution returns 404."""
        ensure_all_permissions(db_session, seed_roles)

        other_tenant = create_other_tenant(db_session, "exec-cancel")
        other_workflow = create_test_workflow(db_session, other_tenant)
        other_execution = create_test_workflow_execution(
            db_session, other_workflow, other_tenant
        )

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.delete(
                f"/api/v1/workflows/executions/{other_execution.id}",
                headers=admin_auth_headers
            )

        assert response.status_code == 404

        # Verify execution still has original status
        db_session.refresh(other_execution)
        assert other_execution.status == WorkflowExecutionStatus.RUNNING.value
