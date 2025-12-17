"""Integration tests for Schemas API endpoints.

Test Coverage:
- POST /api/v1/schemas (create)
- GET /api/v1/schemas (list)
- GET /api/v1/schemas/{schema_id} (get by ID)
- GET /api/v1/schemas/name/{schema_name} (get by name)
- PUT /api/v1/schemas/{schema_id} (update)
- DELETE /api/v1/schemas/{schema_id} (delete)
"""

import pytest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, Tenant, Role, Permission, RolePermission
from app.models.schema_definition import SchemaDefinition


def ensure_schema_permissions(db_session: Session, seed_roles: dict):
    """Ensure schema permissions exist and are assigned to admin."""
    permissions_to_add = [
        ("schemas:create", "schemas", "create", "Create schemas"),
        ("schemas:read", "schemas", "read", "Read schemas"),
        ("schemas:update", "schemas", "update", "Update schemas"),
        ("schemas:delete", "schemas", "delete", "Delete schemas"),
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


class TestCreateSchemaEndpoint:
    """Tests for POST /api/v1/schemas endpoint."""

    def test_create_schema_success(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successful schema creation."""
        ensure_schema_permissions(db_session, seed_roles)

        response = client.post(
            "/api/v1/schemas",
            json={
                "name": f"invoice-schema-{uuid4().hex[:8]}",
                "definitions": {
                    "type": "object",
                    "properties": {
                        "invoice_number": {"type": "string"},
                        "total": {"type": "number"}
                    },
                    "required": ["invoice_number"]
                }
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert "name" in data
        assert data["definitions"]["type"] == "object"
        assert "created_at" in data

    def test_create_schema_invalid_schema(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test creating schema with invalid JSON schema returns 400."""
        ensure_schema_permissions(db_session, seed_roles)

        response = client.post(
            "/api/v1/schemas",
            json={
                "name": "invalid-schema",
                "definitions": {
                    "type": "invalid_type_xyz"  # Invalid type
                }
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_create_schema_duplicate_name(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test creating schema with duplicate name returns 409."""
        ensure_schema_permissions(db_session, seed_roles)

        schema_name = f"duplicate-schema-{uuid4().hex[:8]}"

        # Create first schema
        schema = SchemaDefinition(
            tenant_id=test_tenant.id,
            name=schema_name,
            definitions={"type": "object"}
        )
        db_session.add(schema)
        db_session.commit()

        # Try to create duplicate
        response = client.post(
            "/api/v1/schemas",
            json={
                "name": schema_name,
                "definitions": {"type": "object"}
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_create_schema_missing_permission(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test creating schema without permission returns 403."""
        from app.services.auth_service import AuthService
        from app.config import settings

        auth_service = AuthService()

        # Create a viewer user (viewer role doesn't have schemas:create permission)
        viewer_user = User(
            email="viewer@example.com",
            hashed_password=auth_service.hash_password("ViewerPass123"),
            full_name="Viewer User",
            tenant_id=test_tenant.id,
            role_id=seed_roles["viewer"].id,
            is_active=True,
            is_verified=True,
            locale="en"
        )
        db_session.add(viewer_user)
        db_session.commit()
        db_session.refresh(viewer_user)

        # Generate auth headers for viewer
        access_token = auth_service.create_access_token(
            user_id=str(viewer_user.id),
            tenant_id=str(test_tenant.id)
        )
        allowed_origins = settings.jwt_allowed_origins.split(",")
        origin = allowed_origins[0].strip() if allowed_origins else "http://localhost:3000"
        viewer_headers = {
            "Authorization": f"Bearer {access_token}",
            "origin": origin
        }

        response = client.post(
            "/api/v1/schemas",
            json={
                "name": "test-schema",
                "definitions": {"type": "object"}
            },
            headers=viewer_headers
        )

        assert response.status_code == 403

    def test_create_schema_unauthorized(self, client: TestClient):
        """Test creating schema without authentication returns 401."""
        response = client.post(
            "/api/v1/schemas",
            json={
                "name": "test-schema",
                "definitions": {"type": "object"}
            }
        )
        assert response.status_code == 401


class TestListSchemasEndpoint:
    """Tests for GET /api/v1/schemas endpoint."""

    def test_list_schemas_success(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successful schema list retrieval."""
        ensure_schema_permissions(db_session, seed_roles)

        # Create a schema
        schema = SchemaDefinition(
            tenant_id=test_tenant.id,
            name=f"list-test-{uuid4().hex[:8]}",
            definitions={"type": "object"}
        )
        db_session.add(schema)
        db_session.commit()

        response = client.get(
            "/api/v1/schemas",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "schemas" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert len(data["schemas"]) > 0

    def test_list_schemas_pagination(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test schema list pagination."""
        ensure_schema_permissions(db_session, seed_roles)

        # Create multiple schemas
        for i in range(5):
            schema = SchemaDefinition(
                tenant_id=test_tenant.id,
                name=f"pagination-test-{uuid4().hex[:8]}",
                definitions={"type": "object"}
            )
            db_session.add(schema)
        db_session.commit()

        # Get first page
        response1 = client.get(
            "/api/v1/schemas",
            params={"limit": 2, "offset": 0},
            headers=admin_auth_headers
        )

        assert response1.status_code == 200
        data1 = response1.json()

        assert len(data1["schemas"]) == 2
        assert data1["limit"] == 2
        assert data1["offset"] == 0

        # Get second page
        response2 = client.get(
            "/api/v1/schemas",
            params={"limit": 2, "offset": 2},
            headers=admin_auth_headers
        )

        assert response2.status_code == 200
        data2 = response2.json()

        assert data2["offset"] == 2

    def test_list_schemas_tenant_isolation(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that schemas are isolated per tenant."""
        ensure_schema_permissions(db_session, seed_roles)

        # Create schema for current tenant
        schema = SchemaDefinition(
            tenant_id=test_tenant.id,
            name=f"my-schema-{uuid4().hex[:8]}",
            definitions={"type": "object"}
        )
        db_session.add(schema)

        # Create another tenant with schema
        other_tenant = Tenant(
            name="Other Tenant Schema",
            slug=f"other-tenant-schema-{uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        other_schema = SchemaDefinition(
            tenant_id=other_tenant.id,
            name="other-tenant-schema-secret",
            definitions={"type": "object", "secret": True}
        )
        db_session.add(other_schema)
        db_session.commit()

        # Current user should only see their tenant's schemas
        response = client.get(
            "/api/v1/schemas",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should not see other tenant's schema
        for s in data["schemas"]:
            assert s["name"] != "other-tenant-schema-secret"

    def test_list_schemas_unauthorized(self, client: TestClient):
        """Test listing schemas without authentication returns 401."""
        response = client.get("/api/v1/schemas")
        assert response.status_code == 401


class TestGetSchemaByIdEndpoint:
    """Tests for GET /api/v1/schemas/{schema_id} endpoint."""

    def test_get_schema_by_id_success(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successful schema retrieval by ID."""
        ensure_schema_permissions(db_session, seed_roles)

        schema = SchemaDefinition(
            tenant_id=test_tenant.id,
            name=f"get-by-id-{uuid4().hex[:8]}",
            definitions={"type": "object", "title": "TestSchema"}
        )
        db_session.add(schema)
        db_session.commit()
        db_session.refresh(schema)

        response = client.get(
            f"/api/v1/schemas/{schema.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(schema.id)
        assert data["definitions"]["title"] == "TestSchema"

    def test_get_schema_by_id_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting non-existent schema returns 404."""
        ensure_schema_permissions(db_session, seed_roles)

        response = client.get(
            f"/api/v1/schemas/{uuid4()}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_get_schema_by_id_cross_tenant_404(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test accessing another tenant's schema returns 404."""
        ensure_schema_permissions(db_session, seed_roles)

        # Create another tenant with schema
        other_tenant = Tenant(
            name="Other Tenant Get",
            slug=f"other-tenant-get-{uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        other_schema = SchemaDefinition(
            tenant_id=other_tenant.id,
            name="other-tenant-schema-get",
            definitions={"type": "object"}
        )
        db_session.add(other_schema)
        db_session.commit()
        db_session.refresh(other_schema)

        # Try to access other tenant's schema
        response = client.get(
            f"/api/v1/schemas/{other_schema.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_get_schema_by_id_unauthorized(self, client: TestClient):
        """Test getting schema without authentication returns 401."""
        response = client.get(f"/api/v1/schemas/{uuid4()}")
        assert response.status_code == 401


class TestGetSchemaByNameEndpoint:
    """Tests for GET /api/v1/schemas/name/{schema_name} endpoint."""

    def test_get_schema_by_name_success(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successful schema retrieval by name."""
        ensure_schema_permissions(db_session, seed_roles)

        schema_name = f"get-by-name-{uuid4().hex[:8]}"
        schema = SchemaDefinition(
            tenant_id=test_tenant.id,
            name=schema_name,
            definitions={"type": "object", "description": "Named schema"}
        )
        db_session.add(schema)
        db_session.commit()

        response = client.get(
            f"/api/v1/schemas/name/{schema_name}",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == schema_name
        assert data["definitions"]["description"] == "Named schema"

    def test_get_schema_by_name_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test getting non-existent schema by name returns 404."""
        ensure_schema_permissions(db_session, seed_roles)

        response = client.get(
            "/api/v1/schemas/name/nonexistent-schema-xyz",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_get_schema_by_name_unauthorized(self, client: TestClient):
        """Test getting schema by name without authentication returns 401."""
        response = client.get("/api/v1/schemas/name/test-schema")
        assert response.status_code == 401


class TestUpdateSchemaEndpoint:
    """Tests for PUT /api/v1/schemas/{schema_id} endpoint."""

    def test_update_schema_success(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successful schema update."""
        ensure_schema_permissions(db_session, seed_roles)

        schema = SchemaDefinition(
            tenant_id=test_tenant.id,
            name=f"update-test-{uuid4().hex[:8]}",
            definitions={"type": "object", "version": 1}
        )
        db_session.add(schema)
        db_session.commit()
        db_session.refresh(schema)

        response = client.put(
            f"/api/v1/schemas/{schema.id}",
            json={
                "definitions": {
                    "type": "object",
                    "version": 2,
                    "properties": {
                        "field1": {"type": "string"}
                    }
                }
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["definitions"]["version"] == 2
        assert "field1" in data["definitions"]["properties"]

    def test_update_schema_invalid_definition(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test updating schema with invalid definition returns 400."""
        ensure_schema_permissions(db_session, seed_roles)

        schema = SchemaDefinition(
            tenant_id=test_tenant.id,
            name=f"update-invalid-{uuid4().hex[:8]}",
            definitions={"type": "object"}
        )
        db_session.add(schema)
        db_session.commit()
        db_session.refresh(schema)

        response = client.put(
            f"/api/v1/schemas/{schema.id}",
            json={
                "definitions": {
                    "type": "invalid_type_xyz"  # Invalid
                }
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 400

    def test_update_schema_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test updating non-existent schema returns 404."""
        ensure_schema_permissions(db_session, seed_roles)

        response = client.put(
            f"/api/v1/schemas/{uuid4()}",
            json={
                "definitions": {"type": "object"}
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_update_schema_cross_tenant_404(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test updating another tenant's schema returns 404."""
        ensure_schema_permissions(db_session, seed_roles)

        # Create another tenant with schema
        other_tenant = Tenant(
            name="Other Tenant Update",
            slug=f"other-tenant-update-{uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        other_schema = SchemaDefinition(
            tenant_id=other_tenant.id,
            name="other-tenant-schema-update",
            definitions={"type": "object"}
        )
        db_session.add(other_schema)
        db_session.commit()
        db_session.refresh(other_schema)

        # Try to update other tenant's schema
        response = client.put(
            f"/api/v1/schemas/{other_schema.id}",
            json={
                "definitions": {"type": "object", "hacked": True}
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_update_schema_unauthorized(self, client: TestClient):
        """Test updating schema without authentication returns 401."""
        response = client.put(
            f"/api/v1/schemas/{uuid4()}",
            json={"definitions": {"type": "object"}}
        )
        assert response.status_code == 401


class TestDeleteSchemaEndpoint:
    """Tests for DELETE /api/v1/schemas/{schema_id} endpoint."""

    def test_delete_schema_success(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successful schema deletion."""
        ensure_schema_permissions(db_session, seed_roles)

        schema = SchemaDefinition(
            tenant_id=test_tenant.id,
            name=f"delete-test-{uuid4().hex[:8]}",
            definitions={"type": "object"}
        )
        db_session.add(schema)
        db_session.commit()
        db_session.refresh(schema)
        schema_id = schema.id

        response = client.delete(
            f"/api/v1/schemas/{schema_id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 204

        # Verify deletion
        deleted_schema = db_session.query(SchemaDefinition).filter(
            SchemaDefinition.id == schema_id
        ).first()
        assert deleted_schema is None

    def test_delete_schema_not_found(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test deleting non-existent schema returns 404."""
        ensure_schema_permissions(db_session, seed_roles)

        response = client.delete(
            f"/api/v1/schemas/{uuid4()}",
            headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_delete_schema_cross_tenant_404(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test deleting another tenant's schema returns 404."""
        ensure_schema_permissions(db_session, seed_roles)

        # Create another tenant with schema
        other_tenant = Tenant(
            name="Other Tenant Delete",
            slug=f"other-tenant-delete-{uuid4().hex[:8]}",
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        other_schema = SchemaDefinition(
            tenant_id=other_tenant.id,
            name="other-tenant-schema-delete",
            definitions={"type": "object"}
        )
        db_session.add(other_schema)
        db_session.commit()
        db_session.refresh(other_schema)

        # Try to delete other tenant's schema
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

    def test_delete_schema_unauthorized(self, client: TestClient):
        """Test deleting schema without authentication returns 401."""
        response = client.delete(f"/api/v1/schemas/{uuid4()}")
        assert response.status_code == 401
