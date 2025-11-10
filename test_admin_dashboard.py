#!/usr/bin/env python3
"""Test script to verify admin dashboard query fix."""

from app.database import SessionLocal
from app.services.admin_metrics_service import AdminMetricsService

def test_platform_statistics():
    """Test that platform statistics query works after field name fix."""
    db = SessionLocal()
    try:
        service = AdminMetricsService(db)

        # This should not raise AttributeError anymore
        stats = service.get_platform_statistics()

        print("✅ Platform statistics query successful!")
        print(f"  Total tenants: {stats.total_tenants}")
        print(f"  Total users: {stats.total_users}")
        print(f"  Total jobs: {stats.total_jobs}")
        print(f"  Total credits consumed: {stats.total_credits_consumed}")
        print(f"  Total credits purchased: {stats.total_credits_purchased}")

        return True
    except AttributeError as e:
        print(f"❌ AttributeError: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_platform_statistics()
    exit(0 if success else 1)
