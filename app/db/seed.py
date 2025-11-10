"""Database seeding script for initial data setup."""

import sys
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Tenant, Role, Permission, RolePermission, User
from app.services.auth_service import auth_service


# Platform tenant UUID (constant for consistency)
PLATFORM_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def create_platform_tenant(db: Session) -> Tenant:
    """Create or get the platform tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == PLATFORM_TENANT_ID).first()

    if not tenant:
        tenant = Tenant(
            id=PLATFORM_TENANT_ID,
            name="Platform",
            slug="platform",
            status="active",
            subscription_plan="enterprise",
            cached_balance=1000000,  # Large balance for platform
            tenant_metadata={"is_platform": True, "created_by": "seed_script"}
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        print(f"✓ Created platform tenant: {tenant.name} ({tenant.id})")
    else:
        print(f"✓ Platform tenant already exists: {tenant.name} ({tenant.id})")

    return tenant


def create_permissions(db: Session) -> dict[str, Permission]:
    """Create all default permissions."""
    permissions_data = [
        # Document permissions
        ("documents:create", "documents", "create", "Create documents"),
        ("documents:read", "documents", "read", "Read documents"),
        ("documents:update", "documents", "update", "Update documents"),
        ("documents:delete", "documents", "delete", "Delete documents"),
        ("documents:share", "documents", "share", "Share documents"),
        ("documents:export", "documents", "export", "Export documents"),

        # Extraction permissions (CRITICAL for API tokens)
        ("extraction:create", "extraction", "create", "Extract data from documents"),

        # Job permissions
        ("jobs:read", "jobs", "read", "Read extraction job status and results"),

        # Schema permissions
        ("schemas:create", "schemas", "create", "Create schemas"),
        ("schemas:read", "schemas", "read", "Read schemas"),
        ("schemas:update", "schemas", "update", "Update schemas"),
        ("schemas:delete", "schemas", "delete", "Delete schemas"),
        ("schemas:share", "schemas", "share", "Share schemas"),

        # User permissions
        ("users:invite", "users", "invite", "Invite users"),
        ("users:read", "users", "read", "Read user information"),
        ("users:update", "users", "update", "Update users"),
        ("users:delete", "users", "delete", "Delete users"),

        # Tenant permissions
        ("tenant:manage", "tenant", "manage", "Manage tenant settings"),
        ("tenant:billing", "tenant", "billing", "Manage billing and subscriptions"),

        # Platform permissions
        ("platform:super_admin", "platform", "super_admin", "Super admin platform access"),
    ]

    permissions_map = {}

    for name, resource, action, description in permissions_data:
        permission = db.query(Permission).filter(Permission.name == name).first()

        if not permission:
            permission = Permission(
                name=name,
                resource=resource,
                action=action,
                description=description
            )
            db.add(permission)
            db.commit()
            db.refresh(permission)
            print(f"  ✓ Created permission: {name}")
        else:
            print(f"  ✓ Permission already exists: {name}")

        permissions_map[name] = permission

    return permissions_map


def create_roles(db: Session, permissions_map: dict[str, Permission]) -> dict[str, Role]:
    """Create default roles with their permissions."""
    roles_config = {
        "platform_admin": {
            "display_name": "Platform Administrator",
            "description": "Full platform access - internal use only",
            "is_system": True,
            "tenant_id": None,  # Platform-wide role
            "permissions": [
                # All permissions
                "documents:create", "documents:read", "documents:update", "documents:delete", "documents:share", "documents:export",
                "extraction:create", "jobs:read",
                "schemas:create", "schemas:read", "schemas:update", "schemas:delete", "schemas:share",
                "users:invite", "users:read", "users:update", "users:delete",
                "tenant:manage", "tenant:billing",
                "platform:super_admin"
            ]
        },
        "tenant_admin": {
            "display_name": "Tenant Administrator",
            "description": "Full tenant access with user and billing management",
            "is_system": True,
            "tenant_id": None,  # Can be assigned to any tenant
            "permissions": [
                "documents:create", "documents:read", "documents:update", "documents:delete", "documents:share", "documents:export",
                "extraction:create", "jobs:read",
                "schemas:create", "schemas:read", "schemas:update", "schemas:delete", "schemas:share",
                "users:invite", "users:read", "users:update", "users:delete",
                "tenant:manage", "tenant:billing"
            ]
        },
        "member": {
            "display_name": "Member",
            "description": "Standard user with create/read/update access",
            "is_system": True,
            "tenant_id": None,
            "permissions": [
                "documents:create", "documents:read", "documents:update", "documents:share", "documents:export",
                "extraction:create", "jobs:read",
                "schemas:create", "schemas:read", "schemas:update",
            ]
        },
        "viewer": {
            "display_name": "Viewer",
            "description": "Read-only access to documents and schemas",
            "is_system": True,
            "tenant_id": None,
            "permissions": [
                "documents:read", "documents:export",
                "jobs:read",
                "schemas:read",
            ]
        }
    }

    roles_map = {}

    for role_name, config in roles_config.items():
        role = db.query(Role).filter(Role.name == role_name).first()

        if not role:
            role = Role(
                name=role_name,
                display_name=config["display_name"],
                description=config["description"],
                is_system=config["is_system"],
                tenant_id=config["tenant_id"]
            )
            db.add(role)
            db.commit()
            db.refresh(role)
            print(f"  ✓ Created role: {role_name}")

            # Assign permissions to role
            for perm_name in config["permissions"]:
                permission = permissions_map.get(perm_name)
                if permission:
                    role_perm = RolePermission(
                        role_id=role.id,
                        permission_id=permission.id
                    )
                    db.add(role_perm)

            db.commit()
            print(f"    → Assigned {len(config['permissions'])} permissions")
        else:
            print(f"  ✓ Role already exists: {role_name}")

        roles_map[role_name] = role

    return roles_map


def create_platform_admin_user(
    db: Session,
    tenant: Tenant,
    roles_map: dict[str, Role],
    email: str = "admin@platform.local",
    password: str = "AdminPass123!"
) -> User:
    """Create a platform admin user."""
    user = db.query(User).filter(User.email == email).first()

    if not user:
        platform_admin_role = roles_map["platform_admin"]

        user = User(
            tenant_id=tenant.id,
            email=email,
            hashed_password=auth_service.hash_password(password),
            is_active=True,
            is_verified=True,
            full_name="Platform Administrator",
            locale="en",
            role_id=platform_admin_role.id
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"\n✓ Created platform admin user: {email}")
        print(f"  Password: {password}")
        print(f"  ⚠️  IMPORTANT: Change this password immediately in production!")
    else:
        print(f"\n✓ Platform admin user already exists: {email}")

    return user


def seed_database(create_admin: bool = True):
    """Main seeding function."""
    print("\n" + "="*60)
    print("Database Seeding Script")
    print("="*60 + "\n")

    db = SessionLocal()

    try:
        print("Step 1: Creating platform tenant...")
        tenant = create_platform_tenant(db)

        print("\nStep 2: Creating permissions...")
        permissions_map = create_permissions(db)

        print("\nStep 3: Creating roles...")
        roles_map = create_roles(db, permissions_map)

        if create_admin:
            print("\nStep 4: Creating platform admin user...")
            user = create_platform_admin_user(db, tenant, roles_map)

        print("\n" + "="*60)
        print("✓ Database seeding completed successfully!")
        print("="*60 + "\n")

        # Print summary
        print("Summary:")
        print(f"  - Platform Tenant: {tenant.name} ({tenant.id})")
        print(f"  - Permissions: {len(permissions_map)}")
        print(f"  - Roles: {len(roles_map)}")
        if create_admin:
            print(f"  - Admin User: {user.email}")

        print("\nNext steps:")
        print("  1. Run migrations: alembic upgrade head")
        print("  2. Start the server: uvicorn app.main:app --reload")
        print("  3. Login with platform admin credentials")
        print("  4. Change admin password immediately!\n")

    except Exception as e:
        db.rollback()
        print(f"\n✗ Error during seeding: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Check for command-line arguments
    create_admin = True

    if len(sys.argv) > 1 and sys.argv[1] == "--no-admin":
        create_admin = False
        print("Skipping admin user creation (--no-admin flag)")

    seed_database(create_admin=create_admin)
