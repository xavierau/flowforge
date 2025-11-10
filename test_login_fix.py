#!/usr/bin/env python3
"""Test script to verify login schema fix."""

from app.database import SessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import TenantInfo

def test_tenant_info_schema():
    """Test that TenantInfo schema works with cached_balance field."""
    db = SessionLocal()
    try:
        # Get first tenant
        tenant = db.query(Tenant).first()

        if not tenant:
            print("❌ No tenant found in database")
            return False

        print(f"Tenant found: {tenant.name}")
        print(f"  cached_balance: {tenant.cached_balance}")

        # Try to create TenantInfo from Tenant model
        try:
            tenant_info = TenantInfo.model_validate(tenant)
            print(f"✅ TenantInfo schema validated successfully!")
            print(f"  credit_balance in response: {tenant_info.credit_balance}")
            return True
        except Exception as e:
            print(f"❌ TenantInfo validation failed: {e}")
            return False

    finally:
        db.close()

if __name__ == "__main__":
    success = test_tenant_info_schema()
    exit(0 if success else 1)
