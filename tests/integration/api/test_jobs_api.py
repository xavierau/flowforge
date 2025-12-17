"""Integration tests for Jobs API endpoints.

Test Coverage:
- POST /api/v1/jobs/extract
- GET /api/v1/jobs
- GET /api/v1/jobs/{job_id}/status
- GET /api/v1/jobs/{job_id}/result
- POST /api/v1/jobs/{job_id}/retry
"""

import pytest
import io
import json
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, AsyncMock, MagicMock

from app.models import User, Tenant, Role, Document, Permission, RolePermission
from app.models.extraction_job import ExtractionJob
from app.models.extraction_result import ExtractionResult
from app.services.credit_service import CreditService
from app.config import settings
from app.services.auth_service import auth_service


def ensure_jobs_permissions(db_session: Session, seed_roles: dict):
    """Ensure extraction:create and jobs:read permissions exist and are assigned to admin."""
    permissions_to_add = [
        ("extraction:create", "extraction", "create", "Create extractions"),
        ("jobs:read", "jobs", "read", "Read jobs"),
    ]

    for perm_name, resource, action, description in permissions_to_add:
        perm = db_session.query(Permission).filter(Permission.name == perm_name).first()
        if not perm:
            perm = Permission(
                name=perm_name,
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


class TestExtractFromFileEndpoint:
    """Test POST /api/v1/jobs/extract endpoint."""

    def test_extract_with_inline_schema_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successful extraction with inline schema."""
        from app.main import app
        from app.services.storage import get_storage_service

        ensure_jobs_permissions(db_session, seed_roles)

        # Add credits to tenant
        credit_service = CreditService(db_session)
        credit_service.add_credits(
            tenant_id=test_tenant.id,
            amount=100,
            transaction_type="topup",
            description="Test credits"
        )
        db_session.commit()

        # Create minimal PNG content
        png_content = (
            b'\x89PNG\r\n\x1a\n'
            b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
            b'\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N'
            b'\x00\x00\x00\x00IEND\xaeB`\x82'
        )

        # Mock storage
        mock_storage = AsyncMock()
        mock_storage.upload_file = AsyncMock(return_value=("/path/to/file.png", len(png_content)))
        app.dependency_overrides[get_storage_service] = lambda: mock_storage

        try:
            with patch("app.tasks.combined_extraction.process_document_and_extract.delay") as mock_task:
                mock_task.return_value = MagicMock(id="celery-task-id")

                response = client.post(
                    "/api/v1/jobs/extract",
                    files={"file": ("test.png", io.BytesIO(png_content), "image/png")},
                    data={
                        "extraction_schema": json.dumps({
                            "type": "object",
                            "properties": {"invoice_number": {"type": "string"}}
                        }),
                        "model_provider": "google",
                        "model_name": "gemini-2.5-flash",
                        "processing_mode": "batch"
                    },
                    headers=admin_auth_headers
                )

            assert response.status_code == 202
            data = response.json()

            assert "extraction_job_id" in data
            assert "document_id" in data
            assert data["status"] == "queued"
        finally:
            app.dependency_overrides.pop(get_storage_service, None)

    def test_extract_missing_schema(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test extraction without schema returns 400."""
        ensure_jobs_permissions(db_session, seed_roles)

        png_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'

        response = client.post(
            "/api/v1/jobs/extract",
            files={"file": ("test.png", io.BytesIO(png_content), "image/png")},
            data={
                "model_provider": "google",
                "model_name": "gemini-2.5-flash"
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "schema" in response.json()["detail"].lower()

    def test_extract_invalid_file_type(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test extraction with invalid file type returns 400."""
        ensure_jobs_permissions(db_session, seed_roles)

        txt_content = b"This is a text file"

        response = client.post(
            "/api/v1/jobs/extract",
            files={"file": ("test.txt", io.BytesIO(txt_content), "text/plain")},
            data={
                "extraction_schema": json.dumps({"type": "object"}),
                "model_provider": "google",
                "model_name": "gemini-2.5-flash"
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "invalid file type" in response.json()["detail"].lower()

    def test_extract_empty_file(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test extraction with empty file returns 400."""
        ensure_jobs_permissions(db_session, seed_roles)

        response = client.post(
            "/api/v1/jobs/extract",
            files={"file": ("empty.png", io.BytesIO(b""), "image/png")},
            data={
                "extraction_schema": json.dumps({"type": "object"}),
                "model_provider": "google",
                "model_name": "gemini-2.5-flash"
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "empty file" in response.json()["detail"].lower()

    def test_extract_invalid_provider(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test extraction with invalid provider returns 400."""
        ensure_jobs_permissions(db_session, seed_roles)

        png_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'

        response = client.post(
            "/api/v1/jobs/extract",
            files={"file": ("test.png", io.BytesIO(png_content), "image/png")},
            data={
                "extraction_schema": json.dumps({"type": "object"}),
                "model_provider": "invalid_provider",
                "model_name": "some-model"
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "invalid provider" in response.json()["detail"].lower()

    def test_extract_unauthorized(self, client: TestClient):
        """Test extraction without authentication returns 401."""
        png_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'

        response = client.post(
            "/api/v1/jobs/extract",
            files={"file": ("test.png", io.BytesIO(png_content), "image/png")},
            data={
                "extraction_schema": json.dumps({"type": "object"}),
                "model_provider": "google",
                "model_name": "gemini-2.5-flash"
            }
        )

        assert response.status_code == 401


class TestListJobsEndpoint:
    """Test GET /api/v1/jobs endpoint."""

    def test_list_jobs_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test listing jobs returns tenant-scoped results."""
        ensure_jobs_permissions(db_session, seed_roles)

        # Create a document first
        doc = Document(
            tenant_id=test_tenant.id,
            filename="test_list.pdf",
            file_path="/test/list.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="completed",
            page_count=2,
            document_metadata={}
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        # Create test jobs
        for i in range(3):
            job = ExtractionJob(
                document_id=doc.id,
                tenant_id=test_tenant.id,
                extraction_schema={"type": "object"},
                model_provider="google",
                model_name="gemini-2.5-flash",
                processing_mode="batch",
                status="completed" if i < 2 else "queued",
                credits_cost=2,
                credits_deducted=True
            )
            db_session.add(job)
        db_session.commit()

        response = client.get(
            "/api/v1/jobs",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "jobs" in data
        assert "total" in data
        assert data["total"] == 3
        assert len(data["jobs"]) == 3

    def test_list_jobs_pagination(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test pagination works correctly."""
        ensure_jobs_permissions(db_session, seed_roles)

        doc = Document(
            tenant_id=test_tenant.id,
            filename="test_page.pdf",
            file_path="/test/page.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="completed",
            page_count=1,
            document_metadata={}
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        # Create 5 jobs
        for i in range(5):
            job = ExtractionJob(
                document_id=doc.id,
                tenant_id=test_tenant.id,
                extraction_schema={"type": "object"},
                model_provider="google",
                model_name="gemini-2.5-flash",
                processing_mode="batch",
                status="completed",
                credits_cost=1,
                credits_deducted=True
            )
            db_session.add(job)
        db_session.commit()

        # Get first page
        response = client.get(
            "/api/v1/jobs?limit=2&offset=0",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 5
        assert len(data["jobs"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0

    def test_list_jobs_tenant_isolation(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test jobs from other tenants are not visible."""
        ensure_jobs_permissions(db_session, seed_roles)

        # Create document and job for test tenant
        doc1 = Document(
            tenant_id=test_tenant.id,
            filename="my_doc.pdf",
            file_path="/test/my.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="completed",
            page_count=1,
            document_metadata={}
        )
        db_session.add(doc1)
        db_session.commit()
        db_session.refresh(doc1)

        job1 = ExtractionJob(
            document_id=doc1.id,
            tenant_id=test_tenant.id,
            extraction_schema={"type": "object"},
            model_provider="google",
            model_name="gemini-2.5-flash",
            processing_mode="batch",
            status="completed",
            credits_cost=1,
            credits_deducted=True
        )
        db_session.add(job1)

        # Create another tenant with job
        other_tenant = Tenant(
            name="Other Org",
            slug="other-org-jobs",
            status="active",
            subscription_plan="free",
            tenant_metadata={}
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        doc2 = Document(
            tenant_id=other_tenant.id,
            filename="other.pdf",
            file_path="/other/doc.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="completed",
            page_count=1,
            document_metadata={}
        )
        db_session.add(doc2)
        db_session.commit()
        db_session.refresh(doc2)

        job2 = ExtractionJob(
            document_id=doc2.id,
            tenant_id=other_tenant.id,
            extraction_schema={"type": "object"},
            model_provider="google",
            model_name="gemini-2.5-flash",
            processing_mode="batch",
            status="completed",
            credits_cost=1,
            credits_deducted=True
        )
        db_session.add(job2)
        db_session.commit()

        response = client.get(
            "/api/v1/jobs",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["jobs"][0]["document_name"] == "my_doc.pdf"

    def test_list_jobs_unauthorized(self, client: TestClient):
        """Test listing without authentication returns 401."""
        response = client.get("/api/v1/jobs")
        assert response.status_code == 401


class TestGetJobStatusEndpoint:
    """Test GET /api/v1/jobs/{job_id}/status endpoint."""

    def test_get_job_status_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting job status returns correct data."""
        ensure_jobs_permissions(db_session, seed_roles)

        doc = Document(
            tenant_id=test_tenant.id,
            filename="status_test.pdf",
            file_path="/test/status.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="completed",
            page_count=3,
            document_metadata={}
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        job = ExtractionJob(
            document_id=doc.id,
            tenant_id=test_tenant.id,
            extraction_schema={"type": "object"},
            model_provider="google",
            model_name="gemini-2.5-flash",
            processing_mode="batch",
            status="processing",
            started_at=datetime.utcnow(),
            credits_cost=3,
            credits_deducted=True
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        response = client.get(
            f"/api/v1/jobs/{job.id}/status",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["job_id"] == str(job.id)
        assert data["status"] == "processing"
        assert data["progress"] is not None
        assert data["progress"]["total_pages"] == 3

    def test_get_job_status_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting status for non-existent job returns 404."""
        ensure_jobs_permissions(db_session, seed_roles)

        fake_id = uuid4()

        response = client.get(
            f"/api/v1/jobs/{fake_id}/status",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_get_job_status_cross_tenant_404(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting status for another tenant's job returns 404."""
        ensure_jobs_permissions(db_session, seed_roles)

        other_tenant = Tenant(
            name="Other Org",
            slug="other-status",
            status="active",
            subscription_plan="free",
            tenant_metadata={}
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        other_doc = Document(
            tenant_id=other_tenant.id,
            filename="other.pdf",
            file_path="/other/doc.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="completed",
            page_count=1,
            document_metadata={}
        )
        db_session.add(other_doc)
        db_session.commit()
        db_session.refresh(other_doc)

        other_job = ExtractionJob(
            document_id=other_doc.id,
            tenant_id=other_tenant.id,
            extraction_schema={"type": "object"},
            model_provider="google",
            model_name="gemini-2.5-flash",
            processing_mode="batch",
            status="completed",
            credits_cost=1,
            credits_deducted=True
        )
        db_session.add(other_job)
        db_session.commit()
        db_session.refresh(other_job)

        response = client.get(
            f"/api/v1/jobs/{other_job.id}/status",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_get_job_status_unauthorized(self, client: TestClient):
        """Test getting status without authentication returns 401."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/jobs/{fake_id}/status")
        assert response.status_code == 401


class TestGetJobResultEndpoint:
    """Test GET /api/v1/jobs/{job_id}/result endpoint."""

    def test_get_job_result_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting job result returns extracted data."""
        ensure_jobs_permissions(db_session, seed_roles)

        doc = Document(
            tenant_id=test_tenant.id,
            filename="result_test.pdf",
            file_path="/test/result.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="completed",
            page_count=1,
            document_metadata={}
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        job = ExtractionJob(
            document_id=doc.id,
            tenant_id=test_tenant.id,
            extraction_schema={"type": "object"},
            model_provider="google",
            model_name="gemini-2.5-flash",
            processing_mode="batch",
            status="completed",
            completed_at=datetime.utcnow(),
            credits_cost=1,
            credits_deducted=True
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        # Create extraction result
        result = ExtractionResult(
            extraction_job_id=job.id,
            extracted_data={"invoice_number": "INV-001", "total": 100.0},
            model_used="gemini-2.5-flash",
            input_tokens=500,
            output_tokens=200,
            tokens_used=700,
            processing_time_ms=1500,
            confidence_score=0.95
        )
        db_session.add(result)
        db_session.commit()

        response = client.get(
            f"/api/v1/jobs/{job.id}/result",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["job_id"] == str(job.id)
        assert data["status"] == "completed"
        assert "extracted_data" in data
        assert data["extracted_data"]["invoice_number"] == "INV-001"
        assert "metadata" in data
        assert data["metadata"]["confidence_score"] == 0.95

    def test_get_job_result_not_completed(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting result for non-completed job returns 400."""
        ensure_jobs_permissions(db_session, seed_roles)

        doc = Document(
            tenant_id=test_tenant.id,
            filename="incomplete.pdf",
            file_path="/test/incomplete.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="processing",
            page_count=1,
            document_metadata={}
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        job = ExtractionJob(
            document_id=doc.id,
            tenant_id=test_tenant.id,
            extraction_schema={"type": "object"},
            model_provider="google",
            model_name="gemini-2.5-flash",
            processing_mode="batch",
            status="processing",
            credits_cost=1,
            credits_deducted=True
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        response = client.get(
            f"/api/v1/jobs/{job.id}/result",
            headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()

    def test_get_job_result_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting result for non-existent job returns 404."""
        ensure_jobs_permissions(db_session, seed_roles)

        fake_id = uuid4()

        response = client.get(
            f"/api/v1/jobs/{fake_id}/result",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_get_job_result_cross_tenant_404(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting result for another tenant's job returns 404."""
        ensure_jobs_permissions(db_session, seed_roles)

        other_tenant = Tenant(
            name="Other Org",
            slug="other-result",
            status="active",
            subscription_plan="free",
            tenant_metadata={}
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        other_doc = Document(
            tenant_id=other_tenant.id,
            filename="secret.pdf",
            file_path="/secret/doc.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="completed",
            page_count=1,
            document_metadata={}
        )
        db_session.add(other_doc)
        db_session.commit()
        db_session.refresh(other_doc)

        other_job = ExtractionJob(
            document_id=other_doc.id,
            tenant_id=other_tenant.id,
            extraction_schema={"type": "object"},
            model_provider="google",
            model_name="gemini-2.5-flash",
            processing_mode="batch",
            status="completed",
            credits_cost=1,
            credits_deducted=True
        )
        db_session.add(other_job)
        db_session.commit()
        db_session.refresh(other_job)

        response = client.get(
            f"/api/v1/jobs/{other_job.id}/result",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_get_job_result_unauthorized(self, client: TestClient):
        """Test getting result without authentication returns 401."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/jobs/{fake_id}/result")
        assert response.status_code == 401


class TestRetryJobEndpoint:
    """Test POST /api/v1/jobs/{job_id}/retry endpoint."""

    def test_retry_job_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test retrying a job creates a new job with same configuration."""
        ensure_jobs_permissions(db_session, seed_roles)

        # Add credits
        credit_service = CreditService(db_session)
        credit_service.add_credits(
            tenant_id=test_tenant.id,
            amount=100,
            transaction_type="topup",
            description="Test credits"
        )
        db_session.commit()

        doc = Document(
            tenant_id=test_tenant.id,
            filename="retry_test.pdf",
            file_path="/test/retry.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="completed",
            page_count=2,
            document_metadata={}
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        original_job = ExtractionJob(
            document_id=doc.id,
            tenant_id=test_tenant.id,
            extraction_schema={"type": "object", "properties": {"test": {"type": "string"}}},
            model_provider="google",
            model_name="gemini-2.5-flash",
            processing_mode="batch",
            status="failed",
            error_message="Test failure",
            credits_cost=2,
            credits_deducted=True
        )
        db_session.add(original_job)
        db_session.commit()
        db_session.refresh(original_job)

        with patch("app.tasks.combined_extraction.process_document_and_extract.delay") as mock_task:
            mock_task.return_value = MagicMock(id="celery-task-id")

            response = client.post(
                f"/api/v1/jobs/{original_job.id}/retry",
                headers=admin_auth_headers
            )

        assert response.status_code == 202
        data = response.json()

        assert "extraction_job_id" in data
        assert data["extraction_job_id"] != str(original_job.id)
        assert data["status"] == "queued"
        assert data["message"] == "Extraction job retried successfully"

    def test_retry_job_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test retrying non-existent job returns 404."""
        ensure_jobs_permissions(db_session, seed_roles)

        fake_id = uuid4()

        response = client.post(
            f"/api/v1/jobs/{fake_id}/retry",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_retry_job_cross_tenant_404(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test retrying another tenant's job returns 404."""
        ensure_jobs_permissions(db_session, seed_roles)

        other_tenant = Tenant(
            name="Other Org",
            slug="other-retry",
            status="active",
            subscription_plan="free",
            tenant_metadata={}
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        other_doc = Document(
            tenant_id=other_tenant.id,
            filename="other.pdf",
            file_path="/other/doc.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="completed",
            page_count=1,
            document_metadata={}
        )
        db_session.add(other_doc)
        db_session.commit()
        db_session.refresh(other_doc)

        other_job = ExtractionJob(
            document_id=other_doc.id,
            tenant_id=other_tenant.id,
            extraction_schema={"type": "object"},
            model_provider="google",
            model_name="gemini-2.5-flash",
            processing_mode="batch",
            status="failed",
            credits_cost=1,
            credits_deducted=True
        )
        db_session.add(other_job)
        db_session.commit()
        db_session.refresh(other_job)

        response = client.post(
            f"/api/v1/jobs/{other_job.id}/retry",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_retry_job_insufficient_credits(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test retrying job with insufficient credits returns 402."""
        ensure_jobs_permissions(db_session, seed_roles)

        # Do NOT add credits

        doc = Document(
            tenant_id=test_tenant.id,
            filename="nocredit.pdf",
            file_path="/test/nocredit.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="completed",
            page_count=5,
            document_metadata={}
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        job = ExtractionJob(
            document_id=doc.id,
            tenant_id=test_tenant.id,
            extraction_schema={"type": "object"},
            model_provider="google",
            model_name="gemini-2.5-flash",
            processing_mode="batch",
            status="failed",
            credits_cost=5,
            credits_deducted=True
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        response = client.post(
            f"/api/v1/jobs/{job.id}/retry",
            headers=admin_auth_headers
        )

        assert response.status_code == 402
        detail = response.json()["detail"]
        if isinstance(detail, dict):
            detail_str = str(detail).lower()
        else:
            detail_str = detail.lower()
        assert "insufficient" in detail_str

    def test_retry_job_unauthorized(self, client: TestClient):
        """Test retrying without authentication returns 401."""
        fake_id = uuid4()
        response = client.post(f"/api/v1/jobs/{fake_id}/retry")
        assert response.status_code == 401
