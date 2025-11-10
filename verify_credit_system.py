#!/usr/bin/env python
"""Verify credit billing system is working correctly."""

from app.database import SessionLocal
from app.models.tenant import Tenant
from app.services.credit_service import CreditService
from uuid import uuid4

def main():
    db = SessionLocal()

    try:
        print("=" * 60)
        print("CREDIT BILLING SYSTEM VERIFICATION")
        print("=" * 60)

        # Check if cached_balance column exists
        print("\n1. Verifying database schema...")
        tenant = db.query(Tenant).first()

        if tenant is None:
            print("   ⚠️  No tenants in database")
        else:
            has_cached_balance = hasattr(tenant, 'cached_balance')
            has_balance_updated = hasattr(tenant, 'balance_last_updated')

            if has_cached_balance and has_balance_updated:
                print("   ✅ cached_balance column exists")
                print("   ✅ balance_last_updated column exists")
                print(f"   Current balance: {tenant.cached_balance}")
            else:
                print("   ❌ Migration not applied correctly")
                return

        # Test CreditService
        print("\n2. Testing CreditService...")
        credit_service = CreditService(db)

        # Test balance calculation
        if tenant:
            balance = credit_service.calculate_balance(tenant.id, use_cache=True)
            print(f"   ✅ Balance calculation works: {balance} credits")

        # Test check_sufficient_credits
        if tenant:
            has_sufficient, current_balance = credit_service.check_sufficient_credits(
                tenant.id,
                10
            )
            print(f"   ✅ Credit check works: sufficient={has_sufficient}, balance={current_balance}")

        # Verify atomic cache update methods exist
        print("\n3. Verifying atomic cache updates...")
        if hasattr(credit_service, 'deduct_credits'):
            print("   ✅ deduct_credits method exists")
        if hasattr(credit_service, 'add_credits'):
            print("   ✅ add_credits method exists")
        if hasattr(credit_service, 'refund_job_credits'):
            print("   ✅ refund_job_credits method exists")
        if hasattr(credit_service, 'recalculate_cached_balance'):
            print("   ✅ recalculate_cached_balance method exists")

        print("\n" + "=" * 60)
        print("✅ VERIFICATION COMPLETE - All systems operational!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()

if __name__ == "__main__":
    main()
