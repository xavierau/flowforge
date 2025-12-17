"""Integration tests for Document API endpoints.

Test Coverage:
- POST /api/v1/documents/upload
- POST /api/v1/documents/{document_id}/parse
- GET /api/v1/documents
- GET /api/v1/documents/{document_id}
- GET /api/v1/documents/{document_id}/file
- GET /api/v1/documents/{document_id}/pages
"""

import pytest
import io
from uuid import uuid4
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, AsyncMock, MagicMock

from app.models import User, Tenant, Role, Document, DocumentPage, Permission, RolePermission
from app.services.credit_service import CreditService
from app.config import settings
from app.services.auth_service import auth_service


# Helper function to ensure extraction permission exists
def ensure_extraction_permission(db_session: Session, seed_roles: dict):
    """Ensure extraction:create permission exists and is assigned to admin."""
    perm = db_session.query(Permission).filter(Permission.name == "extraction:create").first()
    if not perm:
        perm = Permission(
            name="extraction:create",
            resource="extraction",
            action="create",
            description="Create extractions"
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

    return perm


class TestUploadDocumentEndpoint:
    """Test POST /api/v1/documents/upload endpoint."""

    def test_upload_pdf_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_role_permissions
    ):
        """Test successful PDF upload creates document with 'uploaded' status."""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"

        # Patch at the module level where the function is called
        with patch("app.api.documents.get_storage_service") as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.upload_file = AsyncMock(return_value=("/path/to/file.pdf", len(pdf_content)))
            mock_get_storage.return_value = mock_storage

            with patch("app.tasks.pdf_processor.pdf_to_images.delay") as mock_task:
                mock_task.return_value = MagicMock(id="celery-task-id")

                response = client.post(
                    "/api/v1/documents/upload",
                    files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
                    headers=admin_auth_headers
                )

        assert response.status_code == 201
        data = response.json()

        assert "document_id" in data
        assert data["filename"] == "test.pdf"
        assert data["mime_type"] == "application/pdf"
        assert data["status"] == "uploaded"

        # Verify in database
        doc = db_session.query(Document).filter(Document.id == data["document_id"]).first()
        assert doc is not None
        assert doc.tenant_id == test_tenant.id

    def test_upload_image_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_role_permissions
    ):
        """Test successful image upload creates document with 'ready_for_extraction' status."""
        # Create a minimal valid PNG
        png_content = (
            b'\x89PNG\r\n\x1a\n'
            b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
            b'\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N'
            b'\x00\x00\x00\x00IEND\xaeB`\x82'
        )

        with patch("app.api.documents.get_storage_service") as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.upload_file = AsyncMock(return_value=("/path/to/file.png", len(png_content)))
            mock_get_storage.return_value = mock_storage

            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.png", io.BytesIO(png_content), "image/png")},
                headers=admin_auth_headers
            )

        assert response.status_code == 201
        data = response.json()

        assert data["status"] == "ready_for_extraction"
        assert data["mime_type"] == "image/png"

    def test_upload_invalid_mime_type(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        seed_role_permissions
    ):
        """Test upload with invalid MIME type returns 400."""
        txt_content = b"This is a text file"

        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", io.BytesIO(txt_content), "text/plain")},
            headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "invalid file type" in response.json()["detail"].lower()

    def test_upload_empty_file(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        seed_role_permissions
    ):
        """Test upload with empty file returns 400."""
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
            headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "empty file" in response.json()["detail"].lower()

    def test_upload_unauthorized(self, client: TestClient):
        """Test upload without authentication returns 401."""
        pdf_content = b"%PDF-1.4\ntest content"

        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        )

        assert response.status_code == 401

    def test_upload_forbidden_without_permission(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test upload without documents:create permission returns 403."""
        # Create user with viewer role (no documents:create permission)
        viewer_user = User(
            email="viewer_upload@example.com",
            hashed_password=auth_service.hash_password("TestPass123"),
            full_name="Viewer User",
            tenant_id=test_tenant.id,
            role_id=seed_roles["viewer"].id,
            is_active=True,
            is_verified=True
        )
        db_session.add(viewer_user)
        db_session.commit()
        db_session.refresh(viewer_user)

        # Create auth headers
        access_token = auth_service.create_access_token(
            user_id=str(viewer_user.id),
            tenant_id=str(test_tenant.id)
        )
        allowed_origins = settings.jwt_allowed_origins_list
        origin = next(iter(allowed_origins)) if allowed_origins else "http://localhost:3000"
        viewer_headers = {
            "Authorization": f"Bearer {access_token}",
            "origin": origin
        }

        pdf_content = b"%PDF-1.4\ntest content"
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
            headers=viewer_headers
        )

        assert response.status_code == 403

    def test_upload_tenant_isolation(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_role_permissions
    ):
        """Test uploaded document belongs to user's tenant."""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"

        with patch("app.api.documents.get_storage_service") as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.upload_file = AsyncMock(return_value=("/path/to/file.pdf", len(pdf_content)))
            mock_get_storage.return_value = mock_storage

            with patch("app.tasks.pdf_processor.pdf_to_images.delay"):
                response = client.post(
                    "/api/v1/documents/upload",
                    files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
                    headers=admin_auth_headers
                )

        assert response.status_code == 201
        doc_id = response.json()["document_id"]

        doc = db_session.query(Document).filter(Document.id == doc_id).first()
        assert doc is not None
        assert doc.tenant_id == test_tenant.id


class TestParseDocumentEndpoint:
    """Test POST /api/v1/documents/{document_id}/parse endpoint."""

    def test_parse_with_inline_schema_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successful document parsing with inline schema."""
        # Ensure extraction permission
        ensure_extraction_permission(db_session, seed_roles)

        # Add credits to tenant
        credit_service = CreditService(db_session)
        credit_service.add_credits(
            tenant_id=test_tenant.id,
            amount=100,
            transaction_type="topup",
            description="Test credits"
        )
        db_session.commit()

        # Create ready document
        doc = Document(
            tenant_id=test_tenant.id,
            filename="test.pdf",
            file_path="/test/path.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="ready_for_extraction",
            page_count=2,
            document_metadata={}
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        # Mock the celery task
        with patch("app.tasks.extractor.process_extraction_job.delay") as mock_task:
            mock_task.return_value = MagicMock(id="celery-task-id")

            response = client.post(
                f"/api/v1/documents/{doc.id}/parse",
                json={
                    "extraction_schema": {
                        "type": "object",
                        "properties": {
                            "invoice_number": {"type": "string"}
                        }
                    },
                    "model_provider_config": {
                        "provider": "google",
                        "model": "gemini-2.5-flash"
                    },
                    "processing_mode": "batch"
                },
                headers=admin_auth_headers
            )

        assert response.status_code == 202
        data = response.json()

        assert "extraction_job_id" in data
        assert data["document_id"] == str(doc.id)
        assert data["status"] == "queued"

    def test_parse_document_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test parsing non-existent document returns 404."""
        # Ensure extraction permission
        ensure_extraction_permission(db_session, seed_roles)

        fake_id = uuid4()

        response = client.post(
            f"/api/v1/documents/{fake_id}/parse",
            json={
                "extraction_schema": {"type": "object", "properties": {}},
                "model_provider_config": {"provider": "google", "model": "gemini-2.5-flash"},
                "processing_mode": "batch"
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_parse_invalid_schema(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test parsing with invalid JSON schema returns 400."""
        # Ensure extraction permission
        ensure_extraction_permission(db_session, seed_roles)

        # Add credits to tenant (schema validation happens after credit check)
        credit_service = CreditService(db_session)
        credit_service.add_credits(
            tenant_id=test_tenant.id,
            amount=100,
            transaction_type="topup",
            description="Test credits"
        )
        db_session.commit()

        # Create document
        doc = Document(
            tenant_id=test_tenant.id,
            filename="test.pdf",
            file_path="/test/path.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="ready_for_extraction",
            page_count=1,
            document_metadata={}
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        # Use a truly invalid JSON schema (invalid type value)
        response = client.post(
            f"/api/v1/documents/{doc.id}/parse",
            json={
                "extraction_schema": {"type": "invalid_type_xyz"},
                "model_provider_config": {"provider": "google", "model": "gemini-2.5-flash"},
                "processing_mode": "batch"
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_parse_invalid_provider(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test parsing with invalid provider returns 400."""
        # Ensure extraction permission
        ensure_extraction_permission(db_session, seed_roles)

        doc = Document(
            tenant_id=test_tenant.id,
            filename="test.pdf",
            file_path="/test/path.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="ready_for_extraction",
            page_count=1,
            document_metadata={}
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        response = client.post(
            f"/api/v1/documents/{doc.id}/parse",
            json={
                "extraction_schema": {"type": "object", "properties": {}},
                "model_provider_config": {"provider": "invalid_provider", "model": "some-model"},
                "processing_mode": "batch"
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "invalid provider" in response.json()["detail"].lower()

    def test_parse_cross_tenant_document_404(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test parsing document from another tenant returns 404."""
        # Ensure extraction permission
        ensure_extraction_permission(db_session, seed_roles)

        # Create another tenant with document
        other_tenant = Tenant(
            name="Other Organization",
            slug="other-org-parse",
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
            file_path="/other/path.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="ready_for_extraction",
            page_count=1,
            document_metadata={}
        )
        db_session.add(other_doc)
        db_session.commit()
        db_session.refresh(other_doc)

        # Try to access from current tenant - should get 404
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

    def test_parse_document_wrong_status(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test parsing document in 'failed' status returns 400."""
        # Ensure extraction permission
        ensure_extraction_permission(db_session, seed_roles)

        doc = Document(
            tenant_id=test_tenant.id,
            filename="failed.pdf",
            file_path="/test/path.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="failed",
            page_count=None,
            document_metadata={}
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        response = client.post(
            f"/api/v1/documents/{doc.id}/parse",
            json={
                "extraction_schema": {"type": "object", "properties": {}},
                "model_provider_config": {"provider": "google", "model": "gemini-2.5-flash"},
                "processing_mode": "batch"
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "cannot be processed" in response.json()["detail"].lower()

    def test_parse_unauthorized(self, client: TestClient):
        """Test parsing without authentication returns 401."""
        fake_id = uuid4()

        response = client.post(
            f"/api/v1/documents/{fake_id}/parse",
            json={
                "extraction_schema": {"type": "object"},
                "model_provider_config": {"provider": "google", "model": "gemini-2.5-flash"},
                "processing_mode": "batch"
            }
        )

        assert response.status_code == 401

    def test_parse_insufficient_credits(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test parsing with insufficient credits returns 402."""
        # Ensure extraction permission
        ensure_extraction_permission(db_session, seed_roles)

        # Add jobs:read permission too (often required together)
        jobs_read = db_session.query(Permission).filter(Permission.name == "jobs:read").first()
        if not jobs_read:
            jobs_read = Permission(
                name="jobs:read",
                resource="jobs",
                action="read",
                description="Read jobs"
            )
            db_session.add(jobs_read)
            db_session.commit()
            db_session.refresh(jobs_read)

        admin_role = seed_roles.get("admin")
        if admin_role:
            existing = db_session.query(RolePermission).filter(
                RolePermission.role_id == admin_role.id,
                RolePermission.permission_id == jobs_read.id
            ).first()
            if not existing:
                db_session.add(RolePermission(role_id=admin_role.id, permission_id=jobs_read.id))
                db_session.commit()

        # Do NOT add credits to tenant - ensure balance is 0

        doc = Document(
            tenant_id=test_tenant.id,
            filename="test_insufficient.pdf",
            file_path="/test/path_insufficient.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="ready_for_extraction",
            page_count=5,
            document_metadata={}
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        response = client.post(
            f"/api/v1/documents/{doc.id}/parse",
            json={
                "extraction_schema": {"type": "object", "properties": {}},
                "model_provider_config": {"provider": "google", "model": "gemini-2.5-flash"},
                "processing_mode": "batch"
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 402
        detail = response.json()["detail"]
        # Handle both string and dict responses
        if isinstance(detail, dict):
            detail_str = str(detail).lower()
        else:
            detail_str = detail.lower()
        assert "insufficient" in detail_str


class TestListDocumentsEndpoint:
    """Test GET /api/v1/documents endpoint."""

    def test_list_documents_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_role_permissions
    ):
        """Test listing documents returns tenant-scoped results."""
        for i in range(3):
            doc = Document(
                tenant_id=test_tenant.id,
                filename=f"test_{i}.pdf",
                file_path=f"/test/path_{i}.pdf",
                mime_type="application/pdf",
                size_bytes=1024 * (i + 1),
                status="ready_for_extraction",
                page_count=i + 1,
                document_metadata={}
            )
            db_session.add(doc)
        db_session.commit()

        response = client.get(
            "/api/v1/documents",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "documents" in data
        assert "total" in data
        assert data["total"] == 3
        assert len(data["documents"]) == 3

    def test_list_documents_pagination(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_role_permissions
    ):
        """Test pagination works correctly."""
        for i in range(5):
            doc = Document(
                tenant_id=test_tenant.id,
                filename=f"test_{i}.pdf",
                file_path=f"/test/path_{i}.pdf",
                mime_type="application/pdf",
                size_bytes=1024,
                status="ready_for_extraction",
                page_count=1,
                document_metadata={}
            )
            db_session.add(doc)
        db_session.commit()

        # Get first page (2 items)
        response = client.get(
            "/api/v1/documents?limit=2&offset=0",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 5
        assert len(data["documents"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0

        # Get second page
        response = client.get(
            "/api/v1/documents?limit=2&offset=2",
            headers=admin_auth_headers
        )

        data = response.json()
        assert len(data["documents"]) == 2
        assert data["offset"] == 2

    def test_list_documents_status_filter(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_role_permissions
    ):
        """Test filtering by status works."""
        statuses = ["uploaded", "ready_for_extraction", "completed", "failed"]
        for i, status in enumerate(statuses):
            doc = Document(
                tenant_id=test_tenant.id,
                filename=f"test_{i}.pdf",
                file_path=f"/test/path_{i}.pdf",
                mime_type="application/pdf",
                size_bytes=1024,
                status=status,
                page_count=1,
                document_metadata={}
            )
            db_session.add(doc)
        db_session.commit()

        # Filter by completed
        response = client.get(
            "/api/v1/documents?status=completed",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert all(doc["status"] == "completed" for doc in data["documents"])

    def test_list_documents_tenant_isolation(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_role_permissions
    ):
        """Test documents from other tenants are not visible."""
        doc1 = Document(
            tenant_id=test_tenant.id,
            filename="my_doc.pdf",
            file_path="/test/my.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="ready_for_extraction",
            page_count=1,
            document_metadata={}
        )
        db_session.add(doc1)

        other_tenant = Tenant(
            name="Other Org",
            slug="other-org-list",
            status="active",
            subscription_plan="free",
            tenant_metadata={}
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        doc2 = Document(
            tenant_id=other_tenant.id,
            filename="other_doc.pdf",
            file_path="/other/doc.pdf",
            mime_type="application/pdf",
            size_bytes=2048,
            status="completed",
            page_count=2,
            document_metadata={}
        )
        db_session.add(doc2)
        db_session.commit()

        response = client.get(
            "/api/v1/documents",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["documents"][0]["filename"] == "my_doc.pdf"

    def test_list_documents_unauthorized(self, client: TestClient):
        """Test listing without authentication returns 401."""
        response = client.get("/api/v1/documents")
        assert response.status_code == 401


class TestGetDocumentEndpoint:
    """Test GET /api/v1/documents/{document_id} endpoint."""

    def test_get_document_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_role_permissions
    ):
        """Test getting a specific document."""
        doc = Document(
            tenant_id=test_tenant.id,
            filename="test.pdf",
            file_path="/test/path.pdf",
            mime_type="application/pdf",
            size_bytes=2048,
            status="completed",
            page_count=5,
            document_metadata={"key": "value"}
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        response = client.get(
            f"/api/v1/documents/{doc.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["document_id"] == str(doc.id)
        assert data["filename"] == "test.pdf"
        assert data["status"] == "completed"
        assert data["page_count"] == 5
        assert data["size_bytes"] == 2048

    def test_get_document_not_found(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        seed_role_permissions
    ):
        """Test getting non-existent document returns 404."""
        fake_id = uuid4()

        response = client.get(
            f"/api/v1/documents/{fake_id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_get_document_cross_tenant_404(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_role_permissions
    ):
        """Test accessing document from another tenant returns 404."""
        other_tenant = Tenant(
            name="Other Org",
            slug="other-org-get",
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
            file_path="/other/secret.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="completed",
            page_count=1,
            document_metadata={}
        )
        db_session.add(other_doc)
        db_session.commit()
        db_session.refresh(other_doc)

        response = client.get(
            f"/api/v1/documents/{other_doc.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_get_document_unauthorized(self, client: TestClient):
        """Test getting document without authentication returns 401."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/documents/{fake_id}")
        assert response.status_code == 401


class TestDownloadDocumentFileEndpoint:
    """Test GET /api/v1/documents/{document_id}/file endpoint."""

    def test_download_file_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_role_permissions
    ):
        """Test downloading document file returns streaming response."""
        from app.main import app
        from app.services.storage import get_storage_service

        doc = Document(
            tenant_id=test_tenant.id,
            filename="download_test.pdf",
            file_path="/test/download.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="completed",
            page_count=1,
            document_metadata={}
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        file_content = b"%PDF-1.4\nTest PDF content"

        # Create mock storage service
        mock_storage = AsyncMock()
        mock_storage.download_file = AsyncMock(return_value=file_content)

        # Override the dependency
        app.dependency_overrides[get_storage_service] = lambda: mock_storage

        try:
            response = client.get(
                f"/api/v1/documents/{doc.id}/file",
                headers=admin_auth_headers
            )

            assert response.status_code == 200
            assert response.content == file_content
            assert "content-disposition" in response.headers
            assert "download_test.pdf" in response.headers["content-disposition"]
        finally:
            # Clean up the override
            app.dependency_overrides.pop(get_storage_service, None)

    def test_download_file_not_found(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        seed_role_permissions
    ):
        """Test downloading non-existent document returns 404."""
        fake_id = uuid4()

        response = client.get(
            f"/api/v1/documents/{fake_id}/file",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_download_file_cross_tenant_404(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_role_permissions
    ):
        """Test downloading file from another tenant returns 404."""
        other_tenant = Tenant(
            name="Other Org",
            slug="other-download",
            status="active",
            subscription_plan="free",
            tenant_metadata={}
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        other_doc = Document(
            tenant_id=other_tenant.id,
            filename="private.pdf",
            file_path="/other/private.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="completed",
            page_count=1,
            document_metadata={}
        )
        db_session.add(other_doc)
        db_session.commit()
        db_session.refresh(other_doc)

        response = client.get(
            f"/api/v1/documents/{other_doc.id}/file",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_download_file_unauthorized(self, client: TestClient):
        """Test downloading file without authentication returns 401."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/documents/{fake_id}/file")
        assert response.status_code == 401


class TestGetDocumentPagesEndpoint:
    """Test GET /api/v1/documents/{document_id}/pages endpoint."""

    def test_get_pages_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_role_permissions
    ):
        """Test getting document pages returns ordered list."""
        doc = Document(
            tenant_id=test_tenant.id,
            filename="multipage.pdf",
            file_path="/test/multipage.pdf",
            mime_type="application/pdf",
            size_bytes=2048,
            status="completed",
            page_count=3,
            document_metadata={}
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        # Create pages in reverse order to test ordering
        for i in [3, 1, 2]:
            page = DocumentPage(
                document_id=doc.id,
                page_number=i,
                image_path=f"/images/page_{i}.png",
                status="ready",
                markdown_content=f"# Page {i} content"
            )
            db_session.add(page)
        db_session.commit()

        response = client.get(
            f"/api/v1/documents/{doc.id}/pages",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 3
        # Verify ordering
        assert data[0]["page_number"] == 1
        assert data[1]["page_number"] == 2
        assert data[2]["page_number"] == 3
        # Verify markdown content
        assert data[0]["markdown_content"] == "# Page 1 content"

    def test_get_pages_empty(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_role_permissions
    ):
        """Test getting pages for document with no pages."""
        doc = Document(
            tenant_id=test_tenant.id,
            filename="nopage.pdf",
            file_path="/test/nopage.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="uploaded",
            page_count=None,
            document_metadata={}
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        response = client.get(
            f"/api/v1/documents/{doc.id}/pages",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_get_pages_not_found(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        seed_role_permissions
    ):
        """Test getting pages for non-existent document returns 404."""
        fake_id = uuid4()

        response = client.get(
            f"/api/v1/documents/{fake_id}/pages",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_get_pages_cross_tenant_404(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_role_permissions
    ):
        """Test getting pages from another tenant's document returns 404."""
        other_tenant = Tenant(
            name="Other Org",
            slug="other-pages",
            status="active",
            subscription_plan="free",
            tenant_metadata={}
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        other_doc = Document(
            tenant_id=other_tenant.id,
            filename="private_pages.pdf",
            file_path="/other/pages.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            status="completed",
            page_count=1,
            document_metadata={}
        )
        db_session.add(other_doc)
        db_session.commit()
        db_session.refresh(other_doc)

        response = client.get(
            f"/api/v1/documents/{other_doc.id}/pages",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_get_pages_unauthorized(self, client: TestClient):
        """Test getting pages without authentication returns 401."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/documents/{fake_id}/pages")
        assert response.status_code == 401
