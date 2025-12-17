"""Integration tests for Workflows API endpoints.

Test Coverage:
- POST /api/v1/workflows (create workflow)
- GET /api/v1/workflows (list workflows)
- GET /api/v1/workflows/{workflow_id} (get workflow)
- PUT /api/v1/workflows/{workflow_id} (update workflow)
- DELETE /api/v1/workflows/{workflow_id} (delete/soft-delete workflow)
- POST /api/v1/workflows/{workflow_id}/execute (execute workflow)
- GET /api/v1/workflows/executions/{execution_id} (get execution status)
- DELETE /api/v1/workflows/executions/{execution_id} (cancel execution)
- GET /api/v1/workflows/{workflow_id}/executions (list workflow executions)
- GET /api/v1/workflows/executions/{execution_id}/nodes (get node executions)
- POST /api/v1/workflows/test-node (test single node - not implemented)
"""

import pytest
from uuid import uuid4
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, AsyncMock, MagicMock

from app.models import User, Tenant, Role, Permission, RolePermission
from app.models.workflow import Workflow, WorkflowVersion, WorkflowExecution, WorkflowNodeExecution
from app.models.enums import (
    WorkflowExecutionStatus,
    WorkflowNodeExecutionStatus,
    NodeType,
)
from app.services.auth_service import auth_service
from app.config import settings


# ==============================================================================
# Helper Functions
# ==============================================================================


def ensure_workflow_permissions(db_session: Session, seed_roles: dict) -> dict:
    """Ensure all workflow permissions exist and are assigned to admin."""
    permissions_data = [
        ("workflows:create", "workflows", "create", "Create workflows"),
        ("workflows:read", "workflows", "read", "Read workflows"),
        ("workflows:update", "workflows", "update", "Update workflows"),
        ("workflows:delete", "workflows", "delete", "Delete workflows"),
        ("workflows:execute", "workflows", "execute", "Execute workflows"),
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


def create_valid_workflow_definition() -> dict:
    """Create a valid minimal workflow definition with HTTP Trigger and Extraction nodes."""
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
                    "label": "Extract Invoice",
                    "type": "extraction",
                    "isValid": True,
                    "errors": [],
                    "config": {
                        "fileSource": "previous_node",
                        "prompt": "Extract invoice data",
                        "schemaId": "schema-123"
                    }
                }
            }
        ],
        "edges": [
            {
                "id": "edge-1",
                "source": "trigger-1",
                "target": "extraction-1"
            }
        ]
    }


def create_test_workflow(
    db_session: Session,
    tenant: Tenant,
    name: str = "Test Workflow",
    is_active: bool = True,
    is_archived: bool = False,
) -> Workflow:
    """Create a test workflow with initial version."""
    workflow = Workflow(
        tenant_id=tenant.id,
        name=name,
        description="Test workflow description",
        is_active=is_active,
        is_archived=is_archived,
        current_version_number=1
    )
    db_session.add(workflow)
    db_session.flush()

    version = WorkflowVersion(
        workflow_id=workflow.id,
        version_number=1,
        definition=create_valid_workflow_definition(),
        conductor_workflow_name=f"{name}_v1"
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(workflow)
    db_session.refresh(version)

    return workflow


def create_test_execution(
    db_session: Session,
    workflow: Workflow,
    tenant: Tenant,
    status: str = WorkflowExecutionStatus.RUNNING.value,
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
        status=status,
        input_data={"test": "data"},
        conductor_workflow_id="conductor-exec-123"
    )
    db_session.add(execution)
    db_session.commit()
    db_session.refresh(execution)

    return execution


# ==============================================================================
# Test Classes
# ==============================================================================


class TestCreateWorkflow:
    """Test POST /api/v1/workflows endpoint."""

    def test_create_workflow_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successful workflow creation with valid definition."""
        ensure_workflow_permissions(db_session, seed_roles)

        response = client.post(
            "/api/v1/workflows",
            json={
                "name": "Invoice Processing Workflow",
                "description": "Automated invoice extraction",
                "definition": create_valid_workflow_definition()
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert data["name"] == "Invoice Processing Workflow"
        assert data["description"] == "Automated invoice extraction"
        assert data["isActive"] is True
        assert data["isArchived"] is False
        assert data["currentVersionNumber"] == 1
        assert data["currentVersion"] is not None
        assert data["currentVersion"]["versionNumber"] == 1

        # Verify in database
        workflow = db_session.query(Workflow).filter(Workflow.id == data["id"]).first()
        assert workflow is not None
        assert workflow.tenant_id == test_tenant.id

    def test_create_workflow_validation_error_no_trigger(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test creation fails with no HTTP Trigger node."""
        ensure_workflow_permissions(db_session, seed_roles)

        invalid_definition = {
            "nodes": [
                {
                    "id": "extraction-1",
                    "type": "extraction",
                    "position": {"x": 100, "y": 100},
                    "data": {
                        "label": "Extract",
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
            "edges": []
        }

        response = client.post(
            "/api/v1/workflows",
            json={
                "name": "Invalid Workflow",
                "definition": invalid_definition
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "HTTP Trigger" in response.json()["detail"]

    def test_create_workflow_validation_error_multiple_triggers(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test creation fails with multiple HTTP Trigger nodes."""
        ensure_workflow_permissions(db_session, seed_roles)

        invalid_definition = {
            "nodes": [
                {
                    "id": "trigger-1",
                    "type": "httpTrigger",
                    "position": {"x": 100, "y": 100},
                    "data": {"label": "Trigger 1", "type": "httpTrigger", "isValid": True, "errors": []}
                },
                {
                    "id": "trigger-2",
                    "type": "httpTrigger",
                    "position": {"x": 300, "y": 100},
                    "data": {"label": "Trigger 2", "type": "httpTrigger", "isValid": True, "errors": []}
                }
            ],
            "edges": []
        }

        response = client.post(
            "/api/v1/workflows",
            json={
                "name": "Invalid Workflow",
                "definition": invalid_definition
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "only have one" in response.json()["detail"].lower()

    def test_create_workflow_validation_error_empty_nodes(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test creation fails with empty nodes array."""
        ensure_workflow_permissions(db_session, seed_roles)

        response = client.post(
            "/api/v1/workflows",
            json={
                "name": "Empty Workflow",
                "definition": {"nodes": [], "edges": []}
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 422  # Pydantic validation error

    def test_create_workflow_validation_error_cycle(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test creation fails when workflow has cycles."""
        ensure_workflow_permissions(db_session, seed_roles)

        cyclic_definition = {
            "nodes": [
                {
                    "id": "trigger-1",
                    "type": "httpTrigger",
                    "position": {"x": 100, "y": 100},
                    "data": {"label": "Trigger", "type": "httpTrigger", "isValid": True, "errors": []}
                },
                {
                    "id": "node-a",
                    "type": "pythonRunner",
                    "position": {"x": 300, "y": 100},
                    "data": {
                        "label": "Node A",
                        "type": "pythonRunner",
                        "isValid": True,
                        "errors": [],
                        "config": {"code": "print('a')"}
                    }
                },
                {
                    "id": "node-b",
                    "type": "pythonRunner",
                    "position": {"x": 500, "y": 100},
                    "data": {
                        "label": "Node B",
                        "type": "pythonRunner",
                        "isValid": True,
                        "errors": [],
                        "config": {"code": "print('b')"}
                    }
                }
            ],
            "edges": [
                {"id": "e1", "source": "trigger-1", "target": "node-a"},
                {"id": "e2", "source": "node-a", "target": "node-b"},
                {"id": "e3", "source": "node-b", "target": "node-a"}  # Creates cycle
            ]
        }

        response = client.post(
            "/api/v1/workflows",
            json={
                "name": "Cyclic Workflow",
                "definition": cyclic_definition
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "cycle" in response.json()["detail"].lower()

    def test_create_workflow_unauthorized(self, client: TestClient):
        """Test creation without authentication returns 401."""
        response = client.post(
            "/api/v1/workflows",
            json={
                "name": "Test Workflow",
                "definition": create_valid_workflow_definition()
            }
        )

        assert response.status_code == 401

    def test_create_workflow_forbidden_without_permission(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test creation without workflows:create permission returns 403."""
        ensure_workflow_permissions(db_session, seed_roles)

        # Create user with viewer role (no workflows:create permission)
        viewer_user = User(
            email="viewer_workflow@example.com",
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

        response = client.post(
            "/api/v1/workflows",
            json={
                "name": "Test Workflow",
                "definition": create_valid_workflow_definition()
            },
            headers=viewer_headers
        )

        assert response.status_code == 403


class TestListWorkflows:
    """Test GET /api/v1/workflows endpoint."""

    def test_list_workflows_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test listing workflows returns tenant-scoped results."""
        ensure_workflow_permissions(db_session, seed_roles)

        # Create test workflows
        for i in range(3):
            create_test_workflow(db_session, test_tenant, name=f"Workflow {i}")

        response = client.get(
            "/api/v1/workflows",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "workflows" in data
        assert "total" in data
        assert data["total"] == 3
        assert len(data["workflows"]) == 3

    def test_list_workflows_pagination(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test pagination works correctly."""
        ensure_workflow_permissions(db_session, seed_roles)

        for i in range(5):
            create_test_workflow(db_session, test_tenant, name=f"Workflow {i}")

        # Get first page
        response = client.get(
            "/api/v1/workflows?page=1&page_size=2",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["workflows"]) == 2
        assert data["page"] == 1
        assert data["pageSize"] == 2

        # Get second page
        response = client.get(
            "/api/v1/workflows?page=2&page_size=2",
            headers=admin_auth_headers
        )

        data = response.json()
        assert len(data["workflows"]) == 2
        assert data["page"] == 2

    def test_list_workflows_filter_archived_default(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test default filter shows only non-archived workflows."""
        ensure_workflow_permissions(db_session, seed_roles)

        create_test_workflow(db_session, test_tenant, name="Active Workflow", is_archived=False)
        create_test_workflow(db_session, test_tenant, name="Archived Workflow", is_archived=True)

        response = client.get(
            "/api/v1/workflows",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["workflows"][0]["name"] == "Active Workflow"

    def test_list_workflows_filter_archived_true(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test filter shows only archived workflows when is_archived=True."""
        ensure_workflow_permissions(db_session, seed_roles)

        create_test_workflow(db_session, test_tenant, name="Active Workflow", is_archived=False)
        create_test_workflow(db_session, test_tenant, name="Archived Workflow", is_archived=True)

        response = client.get(
            "/api/v1/workflows?is_archived=true",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["workflows"][0]["name"] == "Archived Workflow"

    def test_list_workflows_include_all(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test include_all shows all workflows regardless of archived status."""
        ensure_workflow_permissions(db_session, seed_roles)

        create_test_workflow(db_session, test_tenant, name="Active Workflow", is_archived=False)
        create_test_workflow(db_session, test_tenant, name="Archived Workflow", is_archived=True)

        response = client.get(
            "/api/v1/workflows?include_all=true",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_list_workflows_filter_active(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test filtering by is_active status."""
        ensure_workflow_permissions(db_session, seed_roles)

        create_test_workflow(db_session, test_tenant, name="Active Workflow", is_active=True)
        create_test_workflow(db_session, test_tenant, name="Inactive Workflow", is_active=False)

        response = client.get(
            "/api/v1/workflows?is_active=true",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["workflows"][0]["name"] == "Active Workflow"

    def test_list_workflows_tenant_isolation(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test workflows from other tenants are not visible."""
        ensure_workflow_permissions(db_session, seed_roles)

        # Create workflow for current tenant
        create_test_workflow(db_session, test_tenant, name="My Workflow")

        # Create another tenant with workflow
        other_tenant = Tenant(
            name="Other Org",
            slug="other-org-workflows",
            status="active",
            subscription_plan="free",
            tenant_metadata={}
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        create_test_workflow(db_session, other_tenant, name="Other Workflow")

        response = client.get(
            "/api/v1/workflows?include_all=true",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["workflows"][0]["name"] == "My Workflow"

    def test_list_workflows_unauthorized(self, client: TestClient):
        """Test listing without authentication returns 401."""
        response = client.get("/api/v1/workflows")
        assert response.status_code == 401


class TestGetWorkflow:
    """Test GET /api/v1/workflows/{workflow_id} endpoint."""

    def test_get_workflow_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting a specific workflow with current version."""
        ensure_workflow_permissions(db_session, seed_roles)

        workflow = create_test_workflow(db_session, test_tenant, name="Get Test Workflow")

        response = client.get(
            f"/api/v1/workflows/{workflow.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(workflow.id)
        assert data["name"] == "Get Test Workflow"
        assert data["currentVersion"] is not None
        assert data["currentVersion"]["versionNumber"] == 1
        assert "definition" in data["currentVersion"]

    def test_get_workflow_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting non-existent workflow returns 404."""
        ensure_workflow_permissions(db_session, seed_roles)

        fake_id = uuid4()
        response = client.get(
            f"/api/v1/workflows/{fake_id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_get_workflow_cross_tenant_404(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test accessing workflow from another tenant returns 404."""
        ensure_workflow_permissions(db_session, seed_roles)

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

        other_workflow = create_test_workflow(db_session, other_tenant, name="Other Workflow")

        response = client.get(
            f"/api/v1/workflows/{other_workflow.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_get_workflow_unauthorized(self, client: TestClient):
        """Test getting workflow without authentication returns 401."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/workflows/{fake_id}")
        assert response.status_code == 401


class TestUpdateWorkflow:
    """Test PUT /api/v1/workflows/{workflow_id} endpoint."""

    def test_update_workflow_name_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test updating workflow name without creating new version."""
        ensure_workflow_permissions(db_session, seed_roles)

        workflow = create_test_workflow(db_session, test_tenant, name="Original Name")

        response = client.put(
            f"/api/v1/workflows/{workflow.id}",
            json={"name": "Updated Name"},
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Updated Name"
        assert data["currentVersionNumber"] == 1  # No version bump

        # Verify in database
        db_session.refresh(workflow)
        assert workflow.name == "Updated Name"

    def test_update_workflow_definition_creates_new_version(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test updating definition creates a new version."""
        ensure_workflow_permissions(db_session, seed_roles)

        workflow = create_test_workflow(db_session, test_tenant, name="Version Test")
        original_version = workflow.current_version_number

        new_definition = create_valid_workflow_definition()
        new_definition["nodes"][0]["data"]["label"] = "Updated Trigger"

        response = client.put(
            f"/api/v1/workflows/{workflow.id}",
            json={"definition": new_definition},
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["currentVersionNumber"] == original_version + 1
        assert data["currentVersion"]["versionNumber"] == original_version + 1

        # Verify new version in database
        versions = db_session.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == workflow.id
        ).order_by(WorkflowVersion.version_number).all()
        assert len(versions) == 2

    def test_update_workflow_archive(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test archiving a workflow."""
        ensure_workflow_permissions(db_session, seed_roles)

        workflow = create_test_workflow(db_session, test_tenant, name="Archive Test")

        response = client.put(
            f"/api/v1/workflows/{workflow.id}",
            json={"isArchived": True},
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["isArchived"] is True

        db_session.refresh(workflow)
        assert workflow.is_archived is True

    def test_update_workflow_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test updating non-existent workflow returns 404."""
        ensure_workflow_permissions(db_session, seed_roles)

        fake_id = uuid4()
        response = client.put(
            f"/api/v1/workflows/{fake_id}",
            json={"name": "New Name"},
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_update_workflow_cross_tenant_404(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test updating workflow from another tenant returns 404."""
        ensure_workflow_permissions(db_session, seed_roles)

        other_tenant = Tenant(
            name="Other Org",
            slug="other-org-update",
            status="active",
            subscription_plan="free",
            tenant_metadata={}
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        other_workflow = create_test_workflow(db_session, other_tenant, name="Other Workflow")

        response = client.put(
            f"/api/v1/workflows/{other_workflow.id}",
            json={"name": "Hacked Name"},
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_update_workflow_unauthorized(self, client: TestClient):
        """Test updating workflow without authentication returns 401."""
        fake_id = uuid4()
        response = client.put(
            f"/api/v1/workflows/{fake_id}",
            json={"name": "New Name"}
        )
        assert response.status_code == 401


class TestDeleteWorkflow:
    """Test DELETE /api/v1/workflows/{workflow_id} endpoint."""

    def test_delete_workflow_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test soft delete sets is_active=False."""
        ensure_workflow_permissions(db_session, seed_roles)

        workflow = create_test_workflow(db_session, test_tenant, name="Delete Test")

        response = client.delete(
            f"/api/v1/workflows/{workflow.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 204

        # Verify soft delete
        db_session.refresh(workflow)
        assert workflow.is_active is False

    def test_delete_workflow_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test deleting non-existent workflow returns 404."""
        ensure_workflow_permissions(db_session, seed_roles)

        fake_id = uuid4()
        response = client.delete(
            f"/api/v1/workflows/{fake_id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_delete_workflow_cross_tenant_404(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test deleting workflow from another tenant returns 404."""
        ensure_workflow_permissions(db_session, seed_roles)

        other_tenant = Tenant(
            name="Other Org",
            slug="other-org-delete",
            status="active",
            subscription_plan="free",
            tenant_metadata={}
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        other_workflow = create_test_workflow(db_session, other_tenant, name="Other Workflow")

        response = client.delete(
            f"/api/v1/workflows/{other_workflow.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_delete_workflow_unauthorized(self, client: TestClient):
        """Test deleting workflow without authentication returns 401."""
        fake_id = uuid4()
        response = client.delete(f"/api/v1/workflows/{fake_id}")
        assert response.status_code == 401


class TestExecuteWorkflow:
    """Test POST /api/v1/workflows/{workflow_id}/execute endpoint."""

    def test_execute_workflow_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successful workflow execution creation."""
        ensure_workflow_permissions(db_session, seed_roles)

        workflow = create_test_workflow(db_session, test_tenant, name="Execute Test")

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.register_workflow = AsyncMock(return_value=(True, None))
            mock_conductor.start_workflow = AsyncMock(return_value=("conductor-exec-123", None))
            mock_conductor.translate_workflow_to_conductor = MagicMock(return_value={})
            mock_conductor._determine_execution_order = MagicMock(return_value=["trigger-1", "extraction-1"])

            # Context manager support
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.post(
                f"/api/v1/workflows/{workflow.id}/execute",
                json={"inputData": {"document_id": "doc-123"}},
                headers=admin_auth_headers
            )

        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert data["workflowId"] == str(workflow.id)
        assert data["status"] == "running"
        assert data["conductorWorkflowId"] == "conductor-exec-123"
        assert data["inputData"]["document_id"] == "doc-123"

    def test_execute_workflow_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test executing non-existent workflow returns 404."""
        ensure_workflow_permissions(db_session, seed_roles)

        fake_id = uuid4()

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.post(
                f"/api/v1/workflows/{fake_id}/execute",
                json={"inputData": {}},
                headers=admin_auth_headers
            )

        assert response.status_code == 404

    def test_execute_inactive_workflow(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test executing inactive workflow returns 404."""
        ensure_workflow_permissions(db_session, seed_roles)

        workflow = create_test_workflow(db_session, test_tenant, name="Inactive", is_active=False)

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.post(
                f"/api/v1/workflows/{workflow.id}/execute",
                json={"inputData": {}},
                headers=admin_auth_headers
            )

        assert response.status_code == 404

    def test_execute_workflow_cross_tenant_404(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test executing workflow from another tenant returns 404."""
        ensure_workflow_permissions(db_session, seed_roles)

        other_tenant = Tenant(
            name="Other Org",
            slug="other-org-execute",
            status="active",
            subscription_plan="free",
            tenant_metadata={}
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        other_workflow = create_test_workflow(db_session, other_tenant, name="Other Workflow")

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.post(
                f"/api/v1/workflows/{other_workflow.id}/execute",
                json={"inputData": {}},
                headers=admin_auth_headers
            )

        assert response.status_code == 404

    def test_execute_workflow_unauthorized(self, client: TestClient):
        """Test executing workflow without authentication returns 401."""
        fake_id = uuid4()
        response = client.post(
            f"/api/v1/workflows/{fake_id}/execute",
            json={"inputData": {}}
        )
        assert response.status_code == 401


class TestGetExecutionStatus:
    """Test GET /api/v1/workflows/executions/{execution_id} endpoint."""

    def test_get_execution_status_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting execution status with Conductor sync."""
        ensure_workflow_permissions(db_session, seed_roles)

        workflow = create_test_workflow(db_session, test_tenant, name="Status Test")
        execution = create_test_execution(db_session, workflow, test_tenant)

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.get_execution_status = AsyncMock(return_value=({
                "status": "RUNNING",
                "output": {},
                "tasks": []
            }, None))
            mock_conductor.map_conductor_status_to_ours = MagicMock(return_value=WorkflowExecutionStatus.RUNNING)
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.get(
                f"/api/v1/workflows/executions/{execution.id}",
                headers=admin_auth_headers
            )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(execution.id)
        assert data["workflowId"] == str(workflow.id)
        assert data["status"] == "running"

    def test_get_execution_status_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting non-existent execution returns 404."""
        ensure_workflow_permissions(db_session, seed_roles)

        fake_id = uuid4()

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.get(
                f"/api/v1/workflows/executions/{fake_id}",
                headers=admin_auth_headers
            )

        assert response.status_code == 404

    def test_get_execution_status_cross_tenant_404(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting execution from another tenant returns 404."""
        ensure_workflow_permissions(db_session, seed_roles)

        other_tenant = Tenant(
            name="Other Org",
            slug="other-org-status",
            status="active",
            subscription_plan="free",
            tenant_metadata={}
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        workflow = create_test_workflow(db_session, other_tenant, name="Other Workflow")
        execution = create_test_execution(db_session, workflow, other_tenant)

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.get(
                f"/api/v1/workflows/executions/{execution.id}",
                headers=admin_auth_headers
            )

        assert response.status_code == 404

    def test_get_execution_status_unauthorized(self, client: TestClient):
        """Test getting execution status without authentication returns 401."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/workflows/executions/{fake_id}")
        assert response.status_code == 401


class TestCancelExecution:
    """Test DELETE /api/v1/workflows/executions/{execution_id} endpoint."""

    def test_cancel_execution_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successful execution cancellation."""
        ensure_workflow_permissions(db_session, seed_roles)

        workflow = create_test_workflow(db_session, test_tenant, name="Cancel Test")
        execution = create_test_execution(
            db_session, workflow, test_tenant,
            status=WorkflowExecutionStatus.RUNNING.value
        )

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.cancel_workflow = AsyncMock(return_value=(True, None))
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.delete(
                f"/api/v1/workflows/executions/{execution.id}",
                headers=admin_auth_headers
            )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "cancelled"

        # Verify in database
        db_session.refresh(execution)
        assert execution.status == WorkflowExecutionStatus.CANCELLED.value
        assert execution.completed_at is not None

    def test_cancel_execution_already_completed(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test cancelling already completed execution returns 400."""
        ensure_workflow_permissions(db_session, seed_roles)

        workflow = create_test_workflow(db_session, test_tenant, name="Completed Test")
        execution = create_test_execution(
            db_session, workflow, test_tenant,
            status=WorkflowExecutionStatus.COMPLETED.value
        )

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.delete(
                f"/api/v1/workflows/executions/{execution.id}",
                headers=admin_auth_headers
            )

        assert response.status_code == 400
        assert "cannot cancel" in response.json()["detail"].lower()

    def test_cancel_execution_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test cancelling non-existent execution returns 404."""
        ensure_workflow_permissions(db_session, seed_roles)

        fake_id = uuid4()

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.delete(
                f"/api/v1/workflows/executions/{fake_id}",
                headers=admin_auth_headers
            )

        assert response.status_code == 404

    def test_cancel_execution_cross_tenant_404(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test cancelling execution from another tenant returns 404."""
        ensure_workflow_permissions(db_session, seed_roles)

        other_tenant = Tenant(
            name="Other Org",
            slug="other-org-cancel",
            status="active",
            subscription_plan="free",
            tenant_metadata={}
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        workflow = create_test_workflow(db_session, other_tenant, name="Other Workflow")
        execution = create_test_execution(
            db_session, workflow, other_tenant,
            status=WorkflowExecutionStatus.RUNNING.value
        )

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.delete(
                f"/api/v1/workflows/executions/{execution.id}",
                headers=admin_auth_headers
            )

        assert response.status_code == 404

    def test_cancel_execution_unauthorized(self, client: TestClient):
        """Test cancelling execution without authentication returns 401."""
        fake_id = uuid4()
        response = client.delete(f"/api/v1/workflows/executions/{fake_id}")
        assert response.status_code == 401


class TestListWorkflowExecutions:
    """Test GET /api/v1/workflows/{workflow_id}/executions endpoint."""

    def test_list_executions_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test listing executions for a workflow."""
        ensure_workflow_permissions(db_session, seed_roles)

        workflow = create_test_workflow(db_session, test_tenant, name="List Executions Test")

        # Create multiple executions
        for _ in range(3):
            create_test_execution(db_session, workflow, test_tenant)

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.get(
                f"/api/v1/workflows/{workflow.id}/executions",
                headers=admin_auth_headers
            )

        assert response.status_code == 200
        data = response.json()

        assert "executions" in data
        assert "total" in data
        assert data["total"] == 3
        assert len(data["executions"]) == 3

    def test_list_executions_pagination(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test pagination of executions list."""
        ensure_workflow_permissions(db_session, seed_roles)

        workflow = create_test_workflow(db_session, test_tenant, name="Pagination Test")

        for _ in range(5):
            create_test_execution(db_session, workflow, test_tenant)

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.get(
                f"/api/v1/workflows/{workflow.id}/executions?page=1&page_size=2",
                headers=admin_auth_headers
            )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 5
        assert len(data["executions"]) == 2
        assert data["page"] == 1
        assert data["pageSize"] == 2

    def test_list_executions_workflow_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test listing executions for non-existent workflow returns empty list."""
        ensure_workflow_permissions(db_session, seed_roles)

        fake_id = uuid4()

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.get(
                f"/api/v1/workflows/{fake_id}/executions",
                headers=admin_auth_headers
            )

        # Returns empty list, not 404 (see service implementation)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["executions"]) == 0

    def test_list_executions_unauthorized(self, client: TestClient):
        """Test listing executions without authentication returns 401."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/workflows/{fake_id}/executions")
        assert response.status_code == 401


class TestGetNodeExecutions:
    """Test GET /api/v1/workflows/executions/{execution_id}/nodes endpoint."""

    def test_get_node_executions_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting node execution details."""
        ensure_workflow_permissions(db_session, seed_roles)

        workflow = create_test_workflow(db_session, test_tenant, name="Node Exec Test")
        execution = create_test_execution(db_session, workflow, test_tenant)

        # Create node executions
        node_exec_1 = WorkflowNodeExecution(
            workflow_execution_id=execution.id,
            node_id="trigger-1",
            node_type=NodeType.HTTP_TRIGGER.value,
            node_label="HTTP Trigger",
            status=WorkflowNodeExecutionStatus.COMPLETED.value,
            execution_order=0
        )
        node_exec_2 = WorkflowNodeExecution(
            workflow_execution_id=execution.id,
            node_id="extraction-1",
            node_type=NodeType.EXTRACTION.value,
            node_label="Extract Invoice",
            status=WorkflowNodeExecutionStatus.RUNNING.value,
            execution_order=1
        )
        db_session.add_all([node_exec_1, node_exec_2])
        db_session.commit()

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.get(
                f"/api/v1/workflows/executions/{execution.id}/nodes",
                headers=admin_auth_headers
            )

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        # Verify ordering by execution_order
        assert data[0]["nodeId"] == "trigger-1"
        assert data[0]["status"] == "completed"
        assert data[1]["nodeId"] == "extraction-1"
        assert data[1]["status"] == "running"

    def test_get_node_executions_empty(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting node executions for execution with no nodes."""
        ensure_workflow_permissions(db_session, seed_roles)

        workflow = create_test_workflow(db_session, test_tenant, name="Empty Nodes Test")
        execution = create_test_execution(db_session, workflow, test_tenant)

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.get(
                f"/api/v1/workflows/executions/{execution.id}/nodes",
                headers=admin_auth_headers
            )

        assert response.status_code == 200
        assert response.json() == []

    def test_get_node_executions_cross_tenant_empty(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting node executions from another tenant returns empty list."""
        ensure_workflow_permissions(db_session, seed_roles)

        other_tenant = Tenant(
            name="Other Org",
            slug="other-org-nodes",
            status="active",
            subscription_plan="free",
            tenant_metadata={}
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        workflow = create_test_workflow(db_session, other_tenant, name="Other Workflow")
        execution = create_test_execution(db_session, workflow, other_tenant)

        # Add node execution to other tenant's execution
        node_exec = WorkflowNodeExecution(
            workflow_execution_id=execution.id,
            node_id="trigger-1",
            node_type=NodeType.HTTP_TRIGGER.value,
            node_label="HTTP Trigger",
            status=WorkflowNodeExecutionStatus.COMPLETED.value,
            execution_order=0
        )
        db_session.add(node_exec)
        db_session.commit()

        with patch("app.api.workflows.ConductorClient") as MockConductorClient:
            mock_conductor = AsyncMock()
            mock_conductor.__aenter__ = AsyncMock(return_value=mock_conductor)
            mock_conductor.__aexit__ = AsyncMock(return_value=None)
            MockConductorClient.return_value = mock_conductor

            response = client.get(
                f"/api/v1/workflows/executions/{execution.id}/nodes",
                headers=admin_auth_headers
            )

        # Returns empty list due to tenant isolation, not 404
        assert response.status_code == 200
        assert response.json() == []

    def test_get_node_executions_unauthorized(self, client: TestClient):
        """Test getting node executions without authentication returns 401."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/workflows/executions/{fake_id}/nodes")
        assert response.status_code == 401


class TestTestNode:
    """Test POST /api/v1/workflows/test-node endpoint."""

    def test_test_node_not_implemented(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test single node testing returns 501 Not Implemented."""
        ensure_workflow_permissions(db_session, seed_roles)

        response = client.post(
            "/api/v1/workflows/test-node",
            json={},
            headers=admin_auth_headers
        )

        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"].lower()

    def test_test_node_unauthorized(self, client: TestClient):
        """Test node testing without authentication returns 401."""
        response = client.post(
            "/api/v1/workflows/test-node",
            json={}
        )
        assert response.status_code == 401
