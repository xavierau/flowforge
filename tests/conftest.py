"""Pytest configuration and fixtures for testing."""

import pytest
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import User, Tenant, Role, Permission, RolePermission
from app.services.auth_service import auth_service


# Test database URL (use in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
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
