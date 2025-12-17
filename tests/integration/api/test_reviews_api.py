"""Integration tests for Reviews API endpoints (HITL System).

Test Coverage:
- POST /api/v1/jobs/{job_id}/request-review - Request manual review for a job
- GET /api/v1/reviews/queue - Get review queue (paginated, filtered)
- GET /api/v1/reviews/{review_id} - Get review details
- POST /api/v1/reviews/{review_id}/assign - Assign review to a user
- POST /api/v1/reviews/{review_id}/start - Start review (mark as in_review)
- POST /api/v1/reviews/{review_id}/submit - Submit corrections and complete review
- GET /api/v1/reviews/{review_id}/corrections - Get corrections for a review
- DELETE /api/v1/reviews/{review_id} - Cancel a review request
- POST /api/v1/reviews/{review_id}/escalate - Escalate a review request
- GET /api/v1/reviews/metrics - Get review accuracy metrics
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, Tenant, Role, Permission, RolePermission
from app.models.document import Document
from app.models.extraction_job import ExtractionJob
from app.models.extraction_result import ExtractionResult
from app.models.review_request import ReviewRequest
from app.models.review_correction import ReviewCorrection
from app.models.enums import (
    ReviewRequestStatus,
    ReviewPriority,
    CorrectionType,
    JobStatus,
)
from app.config import settings
from app.services.auth_service import auth_service


# Helper function to ensure review permissions exist
def ensure_review_permissions(db_session: Session, seed_roles: dict):
    """Ensure all review-related permissions exist and are assigned to admin."""
    permissions_data = [
        ("extraction:review", "extraction", "review", "Request extraction reviews"),
        ("reviews:read", "reviews", "read", "Read reviews"),
        ("reviews:update", "reviews", "update", "Update reviews"),
        ("reviews:assign", "reviews", "assign", "Assign reviews"),
        ("reviews:delete", "reviews", "delete", "Delete reviews"),
        ("jobs:read", "jobs", "read", "Read jobs"),
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
        permissions[name] = perm

    admin_role = seed_roles.get("admin")
    if admin_role:
        for perm in permissions.values():
            existing = db_session.query(RolePermission).filter(
                RolePermission.role_id == admin_role.id,
                RolePermission.permission_id == perm.id
            ).first()
            if not existing:
                db_session.add(RolePermission(role_id=admin_role.id, permission_id=perm.id))
        db_session.commit()

    return permissions


def create_test_document(db_session: Session, tenant: Tenant) -> Document:
    """Create a test document for review testing."""
    doc = Document(
        tenant_id=tenant.id,
        filename="review_test.pdf",
        file_path="/test/review_test.pdf",
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
    confidence_score: float = 0.65,
    status: str = "completed"
) -> ExtractionJob:
    """Create a test extraction job for review testing."""
    job = ExtractionJob(
        document_id=document.id,
        tenant_id=tenant.id,
        extraction_schema={"type": "object", "properties": {"invoice_number": {"type": "string"}}},
        model_provider="google",
        model_name="gemini-2.5-flash",
        processing_mode="batch",
        status=status,
        confidence_score=confidence_score,
        credits_cost=2,
        credits_deducted=True,
        started_at=datetime.utcnow() - timedelta(minutes=5),
        completed_at=datetime.utcnow() if status == "completed" else None
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def create_test_extraction_result(
    db_session: Session,
    extraction_job: ExtractionJob,
    extracted_data: dict = None
) -> ExtractionResult:
    """Create a test extraction result."""
    if extracted_data is None:
        extracted_data = {
            "invoice_number": "INV-2024-0001",
            "total": 357.50,
            "vendor": {"name": "Test Vendor Inc."}
        }
    result = ExtractionResult(
        extraction_job_id=extraction_job.id,
        extracted_data=extracted_data,
        confidence_score=extraction_job.confidence_score or 0.65,
        model_used="gemini-2.5-flash",
        tokens_used=500,
        processing_time_ms=1200,
        input_tokens=400,
        output_tokens=100
    )
    db_session.add(result)
    db_session.flush()  # Ensure data is written to DB
    db_session.commit()
    db_session.refresh(result)
    return result


def create_test_review_request(
    db_session: Session,
    extraction_job: ExtractionJob,
    tenant: Tenant,
    status: str = ReviewRequestStatus.PENDING.value,
    priority: str = ReviewPriority.NORMAL.value,
    assigned_to_user_id=None,
    sla_hours: int = 4
) -> ReviewRequest:
    """Create a test review request."""
    review = ReviewRequest(
        tenant_id=tenant.id,
        extraction_job_id=extraction_job.id,
        status=status,
        priority=priority,
        confidence_score=extraction_job.confidence_score or 0.65,
        trigger_reason="manual_request",
        assigned_to_user_id=assigned_to_user_id,
        sla_deadline=datetime.utcnow() + timedelta(hours=sla_hours),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    if assigned_to_user_id:
        review.assigned_at = datetime.utcnow()
    if status == ReviewRequestStatus.IN_REVIEW.value:
        review.started_at = datetime.utcnow()
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)
    return review


class TestRequestReview:
    """Test POST /api/v1/jobs/{job_id}/request-review endpoint."""

    def test_request_review_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successful review request creation."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)

        response = client.post(
            f"/api/v1/jobs/{job.id}/request-review",
            headers=admin_auth_headers
        )

        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert data["extraction_job_id"] == str(job.id)
        assert data["tenant_id"] == str(test_tenant.id)
        assert data["status"] == ReviewRequestStatus.PENDING.value
        assert data["trigger_reason"] == "manual_request"

        # Verify in database
        review = db_session.query(ReviewRequest).filter(
            ReviewRequest.extraction_job_id == job.id
        ).first()
        assert review is not None
        assert review.tenant_id == test_tenant.id

    def test_request_review_job_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test review request for non-existent job returns 404."""
        ensure_review_permissions(db_session, seed_roles)

        fake_id = uuid4()
        response = client.post(
            f"/api/v1/jobs/{fake_id}/request-review",
            headers=admin_auth_headers
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_request_review_cross_tenant_404(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test review request for job from another tenant returns 404."""
        ensure_review_permissions(db_session, seed_roles)

        # Create another tenant with job
        other_tenant = Tenant(
            name="Other Organization",
            slug="other-org-review",
            status="active",
            subscription_plan="free",
            tenant_metadata={}
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        doc = create_test_document(db_session, other_tenant)
        job = create_test_extraction_job(db_session, doc, other_tenant)

        response = client.post(
            f"/api/v1/jobs/{job.id}/request-review",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_request_review_duplicate_returns_400(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test duplicate review request returns 400."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)

        # Create existing review request
        create_test_review_request(db_session, job, test_tenant)

        response = client.post(
            f"/api/v1/jobs/{job.id}/request-review",
            headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_request_review_unauthorized(self, client: TestClient):
        """Test review request without authentication returns 401."""
        fake_id = uuid4()
        response = client.post(f"/api/v1/jobs/{fake_id}/request-review")
        assert response.status_code == 401


class TestGetReviewQueue:
    """Test GET /api/v1/reviews/queue endpoint."""

    def test_get_review_queue_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting review queue returns paginated results."""
        ensure_review_permissions(db_session, seed_roles)

        # Create multiple reviews
        for i in range(3):
            doc = create_test_document(db_session, test_tenant)
            job = create_test_extraction_job(db_session, doc, test_tenant)
            create_test_review_request(db_session, job, test_tenant)

        response = client.get(
            "/api/v1/reviews/queue",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_get_review_queue_status_filter(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        test_admin_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test filtering review queue by status."""
        ensure_review_permissions(db_session, seed_roles)

        # Create reviews with different statuses
        doc1 = create_test_document(db_session, test_tenant)
        job1 = create_test_extraction_job(db_session, doc1, test_tenant)
        create_test_review_request(db_session, job1, test_tenant, status=ReviewRequestStatus.PENDING.value)

        doc2 = create_test_document(db_session, test_tenant)
        job2 = create_test_extraction_job(db_session, doc2, test_tenant)
        create_test_review_request(
            db_session, job2, test_tenant,
            status=ReviewRequestStatus.ASSIGNED.value,
            assigned_to_user_id=test_admin_user.id
        )

        response = client.get(
            "/api/v1/reviews/queue?status=pending",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert all(item["status"] == "pending" for item in data["items"])

    def test_get_review_queue_priority_filter(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test filtering review queue by priority."""
        ensure_review_permissions(db_session, seed_roles)

        # Create reviews with different priorities
        doc1 = create_test_document(db_session, test_tenant)
        job1 = create_test_extraction_job(db_session, doc1, test_tenant)
        create_test_review_request(db_session, job1, test_tenant, priority=ReviewPriority.HIGH.value)

        doc2 = create_test_document(db_session, test_tenant)
        job2 = create_test_extraction_job(db_session, doc2, test_tenant)
        create_test_review_request(db_session, job2, test_tenant, priority=ReviewPriority.NORMAL.value)

        response = client.get(
            "/api/v1/reviews/queue?priority=high",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert all(item["priority"] == "high" for item in data["items"])

    def test_get_review_queue_pagination(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test pagination works correctly."""
        ensure_review_permissions(db_session, seed_roles)

        # Create 5 reviews
        for i in range(5):
            doc = create_test_document(db_session, test_tenant)
            job = create_test_extraction_job(db_session, doc, test_tenant)
            create_test_review_request(db_session, job, test_tenant)

        response = client.get(
            "/api/v1/reviews/queue?page=1&page_size=2",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total_pages"] == 3

    def test_get_review_queue_tenant_isolation(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test review queue only returns tenant's reviews."""
        ensure_review_permissions(db_session, seed_roles)

        # Create review for current tenant
        doc1 = create_test_document(db_session, test_tenant)
        job1 = create_test_extraction_job(db_session, doc1, test_tenant)
        create_test_review_request(db_session, job1, test_tenant)

        # Create review for other tenant
        other_tenant = Tenant(
            name="Other Org",
            slug="other-org-queue",
            status="active",
            subscription_plan="free",
            tenant_metadata={}
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        doc2 = create_test_document(db_session, other_tenant)
        job2 = create_test_extraction_job(db_session, doc2, other_tenant)
        create_test_review_request(db_session, job2, other_tenant)

        response = client.get(
            "/api/v1/reviews/queue",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert all(item["tenant_id"] == str(test_tenant.id) for item in data["items"])

    def test_get_review_queue_unauthorized(self, client: TestClient):
        """Test getting review queue without authentication returns 401."""
        response = client.get("/api/v1/reviews/queue")
        assert response.status_code == 401


class TestGetReviewDetails:
    """Test GET /api/v1/reviews/{review_id} endpoint."""

    def test_get_review_details_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting review details succeeds."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(db_session, job, test_tenant)

        response = client.get(
            f"/api/v1/reviews/{review.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(review.id)
        assert data["extraction_job_id"] == str(job.id)
        assert data["tenant_id"] == str(test_tenant.id)
        assert data["status"] == ReviewRequestStatus.PENDING.value

    def test_get_review_details_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting non-existent review returns 404."""
        ensure_review_permissions(db_session, seed_roles)

        fake_id = uuid4()
        response = client.get(
            f"/api/v1/reviews/{fake_id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_get_review_details_cross_tenant_404(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test accessing review from another tenant returns 404."""
        ensure_review_permissions(db_session, seed_roles)

        other_tenant = Tenant(
            name="Other Org",
            slug="other-org-details",
            status="active",
            subscription_plan="free",
            tenant_metadata={}
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        doc = create_test_document(db_session, other_tenant)
        job = create_test_extraction_job(db_session, doc, other_tenant)
        review = create_test_review_request(db_session, job, other_tenant)

        response = client.get(
            f"/api/v1/reviews/{review.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_get_review_details_unauthorized(self, client: TestClient):
        """Test getting review details without authentication returns 401."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/reviews/{fake_id}")
        assert response.status_code == 401


class TestAssignReview:
    """Test POST /api/v1/reviews/{review_id}/assign endpoint."""

    def test_assign_review_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        test_admin_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successful review assignment."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(db_session, job, test_tenant)

        response = client.post(
            f"/api/v1/reviews/{review.id}/assign",
            json={"user_id": str(test_admin_user.id)},
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["assigned_to_user_id"] == str(test_admin_user.id)
        assert data["status"] == ReviewRequestStatus.ASSIGNED.value

        # Verify in database
        db_session.refresh(review)
        assert review.assigned_to_user_id == test_admin_user.id
        assert review.status == ReviewRequestStatus.ASSIGNED.value
        assert review.assigned_at is not None

    def test_assign_review_reassign_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        test_admin_user: User,
        test_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test re-assigning an already assigned review succeeds."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(
            db_session, job, test_tenant,
            status=ReviewRequestStatus.ASSIGNED.value,
            assigned_to_user_id=test_user.id
        )

        response = client.post(
            f"/api/v1/reviews/{review.id}/assign",
            json={"user_id": str(test_admin_user.id)},
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["assigned_to_user_id"] == str(test_admin_user.id)

    def test_assign_review_invalid_state_returns_400(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        test_admin_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test assigning review in invalid state returns 400."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(
            db_session, job, test_tenant,
            status=ReviewRequestStatus.COMPLETED.value,
            assigned_to_user_id=test_admin_user.id
        )

        response = client.post(
            f"/api/v1/reviews/{review.id}/assign",
            json={"user_id": str(test_admin_user.id)},
            headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "cannot assign" in response.json()["detail"].lower()

    def test_assign_review_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_admin_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test assigning non-existent review returns 404."""
        ensure_review_permissions(db_session, seed_roles)

        fake_id = uuid4()
        response = client.post(
            f"/api/v1/reviews/{fake_id}/assign",
            json={"user_id": str(test_admin_user.id)},
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_assign_review_unauthorized(self, client: TestClient):
        """Test assigning review without authentication returns 401."""
        fake_id = uuid4()
        response = client.post(
            f"/api/v1/reviews/{fake_id}/assign",
            json={"user_id": str(uuid4())}
        )
        assert response.status_code == 401


class TestStartReview:
    """Test POST /api/v1/reviews/{review_id}/start endpoint."""

    def test_start_review_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        test_admin_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successfully starting a review."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(
            db_session, job, test_tenant,
            status=ReviewRequestStatus.ASSIGNED.value,
            assigned_to_user_id=test_admin_user.id
        )

        response = client.post(
            f"/api/v1/reviews/{review.id}/start",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == ReviewRequestStatus.IN_REVIEW.value

        # Verify in database
        db_session.refresh(review)
        assert review.status == ReviewRequestStatus.IN_REVIEW.value
        assert review.started_at is not None

    def test_start_review_wrong_user_returns_403(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        test_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test starting review assigned to another user returns 403."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(
            db_session, job, test_tenant,
            status=ReviewRequestStatus.ASSIGNED.value,
            assigned_to_user_id=test_user.id  # Assigned to different user
        )

        response = client.post(
            f"/api/v1/reviews/{review.id}/start",
            headers=admin_auth_headers  # Using admin, but review is assigned to test_user
        )

        assert response.status_code == 403
        assert "assigned to another user" in response.json()["detail"].lower()

    def test_start_review_wrong_state_returns_400(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        test_admin_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test starting review in PENDING state returns 400."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(
            db_session, job, test_tenant,
            status=ReviewRequestStatus.PENDING.value
        )

        response = client.post(
            f"/api/v1/reviews/{review.id}/start",
            headers=admin_auth_headers
        )

        assert response.status_code == 400

    def test_start_review_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test starting non-existent review returns 404."""
        ensure_review_permissions(db_session, seed_roles)

        fake_id = uuid4()
        response = client.post(
            f"/api/v1/reviews/{fake_id}/start",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_start_review_unauthorized(self, client: TestClient):
        """Test starting review without authentication returns 401."""
        fake_id = uuid4()
        response = client.post(f"/api/v1/reviews/{fake_id}/start")
        assert response.status_code == 401


class TestSubmitCorrections:
    """Test POST /api/v1/reviews/{review_id}/submit endpoint."""

    def test_submit_corrections_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        test_admin_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successfully submitting corrections."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        result = create_test_extraction_result(db_session, job)
        review = create_test_review_request(
            db_session, job, test_tenant,
            status=ReviewRequestStatus.IN_REVIEW.value,
            assigned_to_user_id=test_admin_user.id
        )

        corrections = [
            {
                "extraction_result_id": str(result.id),
                "field_path": "total",
                "original_value": 357.50,
                "corrected_value": 360.00,
                "correction_type": CorrectionType.VALUE_CHANGE.value,
                "correction_notes": "Corrected total amount"
            }
        ]

        response = client.post(
            f"/api/v1/reviews/{review.id}/submit",
            json={
                "corrections": corrections,
                "review_notes": "Reviewed and corrected total"
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == ReviewRequestStatus.COMPLETED.value

        # Verify in database
        db_session.refresh(review)
        assert review.status == ReviewRequestStatus.COMPLETED.value
        assert review.completed_at is not None
        assert review.review_notes == "Reviewed and corrected total"

        # Verify correction was created
        correction = db_session.query(ReviewCorrection).filter(
            ReviewCorrection.review_request_id == review.id
        ).first()
        assert correction is not None
        assert correction.field_path == "total"

    def test_submit_corrections_empty_list_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        test_admin_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test submitting empty corrections list (approve as-is)."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(
            db_session, job, test_tenant,
            status=ReviewRequestStatus.IN_REVIEW.value,
            assigned_to_user_id=test_admin_user.id
        )

        response = client.post(
            f"/api/v1/reviews/{review.id}/submit",
            json={
                "corrections": [],
                "review_notes": "No corrections needed"
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ReviewRequestStatus.COMPLETED.value

    def test_submit_corrections_wrong_user_returns_403(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        test_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test submitting corrections for review assigned to another user returns 403."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(
            db_session, job, test_tenant,
            status=ReviewRequestStatus.IN_REVIEW.value,
            assigned_to_user_id=test_user.id  # Different user
        )

        response = client.post(
            f"/api/v1/reviews/{review.id}/submit",
            json={"corrections": [], "review_notes": "Test"},
            headers=admin_auth_headers
        )

        assert response.status_code == 403
        assert "assigned to another user" in response.json()["detail"].lower()

    def test_submit_corrections_wrong_state_returns_400(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        test_admin_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test submitting corrections for review not in IN_REVIEW state returns 400."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(
            db_session, job, test_tenant,
            status=ReviewRequestStatus.ASSIGNED.value,
            assigned_to_user_id=test_admin_user.id
        )

        response = client.post(
            f"/api/v1/reviews/{review.id}/submit",
            json={"corrections": [], "review_notes": "Test"},
            headers=admin_auth_headers
        )

        assert response.status_code == 400

    def test_submit_corrections_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test submitting corrections for non-existent review returns 404."""
        ensure_review_permissions(db_session, seed_roles)

        fake_id = uuid4()
        response = client.post(
            f"/api/v1/reviews/{fake_id}/submit",
            json={"corrections": [], "review_notes": "Test"},
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_submit_corrections_unauthorized(self, client: TestClient):
        """Test submitting corrections without authentication returns 401."""
        fake_id = uuid4()
        response = client.post(
            f"/api/v1/reviews/{fake_id}/submit",
            json={"corrections": [], "review_notes": "Test"}
        )
        assert response.status_code == 401


class TestGetReviewCorrections:
    """Test GET /api/v1/reviews/{review_id}/corrections endpoint."""

    def test_get_corrections_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        test_admin_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting corrections for a review."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        result = create_test_extraction_result(db_session, job)
        review = create_test_review_request(
            db_session, job, test_tenant,
            status=ReviewRequestStatus.COMPLETED.value,
            assigned_to_user_id=test_admin_user.id
        )

        # Create corrections
        correction = ReviewCorrection(
            review_request_id=review.id,
            extraction_result_id=result.id,
            corrected_by_user_id=test_admin_user.id,
            field_path="total",
            original_value=357.50,
            corrected_value=360.00,
            correction_type=CorrectionType.VALUE_CHANGE.value,
            correction_notes="Corrected total"
        )
        db_session.add(correction)
        db_session.commit()

        response = client.get(
            f"/api/v1/reviews/{review.id}/corrections",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["field_path"] == "total"
        assert data[0]["correction_type"] == CorrectionType.VALUE_CHANGE.value

    def test_get_corrections_empty(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting corrections for review with no corrections."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(db_session, job, test_tenant)

        response = client.get(
            f"/api/v1/reviews/{review.id}/corrections",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_get_corrections_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting corrections for non-existent review returns 404."""
        ensure_review_permissions(db_session, seed_roles)

        fake_id = uuid4()
        response = client.get(
            f"/api/v1/reviews/{fake_id}/corrections",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_get_corrections_unauthorized(self, client: TestClient):
        """Test getting corrections without authentication returns 401."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/reviews/{fake_id}/corrections")
        assert response.status_code == 401


class TestCancelReview:
    """Test DELETE /api/v1/reviews/{review_id} endpoint."""

    def test_cancel_review_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successfully cancelling a review."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(db_session, job, test_tenant)

        response = client.delete(
            f"/api/v1/reviews/{review.id}?reason=No+longer+needed",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == ReviewRequestStatus.CANCELLED.value

        # Verify in database
        db_session.refresh(review)
        assert review.status == ReviewRequestStatus.CANCELLED.value
        assert "Cancelled: No longer needed" in review.review_notes

    def test_cancel_review_no_reason_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test cancelling review without reason succeeds."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(db_session, job, test_tenant)

        response = client.delete(
            f"/api/v1/reviews/{review.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ReviewRequestStatus.CANCELLED.value

    def test_cancel_completed_review_returns_400(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        test_admin_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test cancelling completed review returns 400."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(
            db_session, job, test_tenant,
            status=ReviewRequestStatus.COMPLETED.value,
            assigned_to_user_id=test_admin_user.id
        )

        response = client.delete(
            f"/api/v1/reviews/{review.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "completed" in response.json()["detail"].lower()

    def test_cancel_review_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test cancelling non-existent review returns 404."""
        ensure_review_permissions(db_session, seed_roles)

        fake_id = uuid4()
        response = client.delete(
            f"/api/v1/reviews/{fake_id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_cancel_review_unauthorized(self, client: TestClient):
        """Test cancelling review without authentication returns 401."""
        fake_id = uuid4()
        response = client.delete(f"/api/v1/reviews/{fake_id}")
        assert response.status_code == 401


class TestEscalateReview:
    """Test POST /api/v1/reviews/{review_id}/escalate endpoint."""

    def test_escalate_review_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        test_admin_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successfully escalating a review."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(
            db_session, job, test_tenant,
            status=ReviewRequestStatus.IN_REVIEW.value,
            assigned_to_user_id=test_admin_user.id
        )

        response = client.post(
            f"/api/v1/reviews/{review.id}/escalate",
            json={"reason": "Document requires specialist expertise in technical terminology"},
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == ReviewRequestStatus.ESCALATED.value

        # Verify in database
        db_session.refresh(review)
        assert review.status == ReviewRequestStatus.ESCALATED.value
        assert "ESCALATED" in review.review_notes
        assert "specialist expertise" in review.review_notes

    def test_escalate_review_from_pending_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test escalating review from PENDING state succeeds."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(db_session, job, test_tenant)

        response = client.post(
            f"/api/v1/reviews/{review.id}/escalate",
            json={"reason": "High priority document needs immediate attention from senior reviewer"},
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ReviewRequestStatus.ESCALATED.value

    def test_escalate_completed_review_returns_400(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        test_admin_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test escalating completed review returns 400."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(
            db_session, job, test_tenant,
            status=ReviewRequestStatus.COMPLETED.value,
            assigned_to_user_id=test_admin_user.id
        )

        response = client.post(
            f"/api/v1/reviews/{review.id}/escalate",
            json={"reason": "Cannot escalate completed review - this should fail"},
            headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "completed" in response.json()["detail"].lower()

    def test_escalate_cancelled_review_returns_400(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test escalating cancelled review returns 400."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(
            db_session, job, test_tenant,
            status=ReviewRequestStatus.CANCELLED.value
        )

        response = client.post(
            f"/api/v1/reviews/{review.id}/escalate",
            json={"reason": "Cannot escalate cancelled review - this should fail"},
            headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "cancelled" in response.json()["detail"].lower()

    def test_escalate_review_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test escalating non-existent review returns 404."""
        ensure_review_permissions(db_session, seed_roles)

        fake_id = uuid4()
        response = client.post(
            f"/api/v1/reviews/{fake_id}/escalate",
            json={"reason": "This review does not exist so this should fail"},
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_escalate_review_short_reason_returns_422(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test escalating with too short reason returns 422."""
        ensure_review_permissions(db_session, seed_roles)

        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(db_session, job, test_tenant)

        response = client.post(
            f"/api/v1/reviews/{review.id}/escalate",
            json={"reason": "Short"},  # Less than 10 chars
            headers=admin_auth_headers
        )

        assert response.status_code == 422

    def test_escalate_review_unauthorized(self, client: TestClient):
        """Test escalating review without authentication returns 401."""
        fake_id = uuid4()
        response = client.post(
            f"/api/v1/reviews/{fake_id}/escalate",
            json={"reason": "This should fail because we are not authenticated"}
        )
        assert response.status_code == 401


class TestGetReviewMetrics:
    """Test GET /api/v1/reviews/metrics endpoint."""

    def test_get_metrics_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        test_admin_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting review metrics succeeds."""
        ensure_review_permissions(db_session, seed_roles)

        # Create completed review
        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        review = create_test_review_request(
            db_session, job, test_tenant,
            status=ReviewRequestStatus.COMPLETED.value,
            assigned_to_user_id=test_admin_user.id
        )
        review.started_at = datetime.utcnow() - timedelta(minutes=15)
        review.completed_at = datetime.utcnow()
        db_session.commit()

        response = client.get(
            "/api/v1/reviews/metrics",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "total_reviews" in data
        assert "completed_reviews" in data
        assert "pending_reviews" in data
        assert "average_review_time_minutes" in data
        assert "sla_breach_count" in data
        assert "accuracy_by_schema" in data
        assert "most_corrected_fields" in data

        assert data["total_reviews"] >= 1
        assert data["completed_reviews"] >= 1

    def test_get_metrics_with_escalated_reviews(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test SLA breach count includes escalated reviews."""
        ensure_review_permissions(db_session, seed_roles)

        # Create escalated review
        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        create_test_review_request(
            db_session, job, test_tenant,
            status=ReviewRequestStatus.ESCALATED.value
        )

        response = client.get(
            "/api/v1/reviews/metrics",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sla_breach_count"] >= 1

    def test_get_metrics_with_top_corrected_fields(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        test_admin_user: User,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test metrics include most corrected fields."""
        ensure_review_permissions(db_session, seed_roles)

        # Create review with corrections
        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        result = create_test_extraction_result(db_session, job)
        review = create_test_review_request(
            db_session, job, test_tenant,
            status=ReviewRequestStatus.COMPLETED.value,
            assigned_to_user_id=test_admin_user.id
        )

        # Create multiple corrections for same field
        for _ in range(3):
            correction = ReviewCorrection(
                review_request_id=review.id,
                extraction_result_id=result.id,
                corrected_by_user_id=test_admin_user.id,
                field_path="invoice.total",
                original_value=100.0,
                corrected_value=150.0,
                correction_type=CorrectionType.VALUE_CHANGE.value
            )
            db_session.add(correction)
        db_session.commit()

        response = client.get(
            "/api/v1/reviews/metrics",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["most_corrected_fields"]) > 0
        # Find the invoice.total entry
        total_field = next(
            (f for f in data["most_corrected_fields"] if f["field_path"] == "invoice.total"),
            None
        )
        assert total_field is not None
        assert total_field["correction_count"] >= 3

    def test_get_metrics_date_filter(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test filtering metrics by date range."""
        ensure_review_permissions(db_session, seed_roles)

        # Create review
        doc = create_test_document(db_session, test_tenant)
        job = create_test_extraction_job(db_session, doc, test_tenant)
        create_test_review_request(db_session, job, test_tenant)

        start_date = (datetime.utcnow() - timedelta(days=1)).isoformat()
        end_date = (datetime.utcnow() + timedelta(days=1)).isoformat()

        response = client.get(
            f"/api/v1/reviews/metrics?start_date={start_date}&end_date={end_date}",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_reviews"] >= 1

    def test_get_metrics_empty(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting metrics when no reviews exist."""
        ensure_review_permissions(db_session, seed_roles)

        response = client.get(
            "/api/v1/reviews/metrics",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_reviews"] == 0
        assert data["completed_reviews"] == 0
        assert data["pending_reviews"] == 0
        assert data["sla_breach_count"] == 0

    def test_get_metrics_tenant_isolation(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test metrics only include current tenant's reviews."""
        ensure_review_permissions(db_session, seed_roles)

        # Create review for current tenant
        doc1 = create_test_document(db_session, test_tenant)
        job1 = create_test_extraction_job(db_session, doc1, test_tenant)
        create_test_review_request(db_session, job1, test_tenant)

        # Create review for other tenant
        other_tenant = Tenant(
            name="Other Org",
            slug="other-org-metrics",
            status="active",
            subscription_plan="free",
            tenant_metadata={}
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        doc2 = create_test_document(db_session, other_tenant)
        job2 = create_test_extraction_job(db_session, doc2, other_tenant)
        create_test_review_request(db_session, job2, other_tenant)

        response = client.get(
            "/api/v1/reviews/metrics",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # Should only count current tenant's reviews
        assert data["total_reviews"] == 1

    def test_get_metrics_unauthorized(self, client: TestClient):
        """Test getting metrics without authentication returns 401."""
        response = client.get("/api/v1/reviews/metrics")
        assert response.status_code == 401
