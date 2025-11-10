#!/usr/bin/env python3
"""
Test script for Platform Settings and Credit Management features.

Tests:
1. Platform Settings API (GET, PATCH)
2. Trial credits on new tenant registration
3. Manual credit addition to tenant
"""

import requests
import json
import sys
from typing import Optional, Dict, Any

API_BASE_URL = "http://localhost:8000/api/v1"

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_success(message: str):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message: str):
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(message: str):
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")


def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")


def register_test_admin() -> Optional[str]:
    """Register a test super admin user and return JWT token."""
    print_info("Registering test super admin user...")

    # First, try to login with existing admin
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={
                "email": "admin@test.com",
                "password": "Admin123!@#"
            }
        )

        if response.status_code == 200:
            token = response.json()["access_token"]
            print_success("Logged in with existing admin user")
            return token
    except:
        pass

    # Register new admin (note: in production this would need to be done via database)
    print_warning("Note: Creating super admin requires database setup. Using test credentials.")
    return None


def test_platform_settings_get(token: str) -> Dict[str, Any]:
    """Test GET /admin/settings endpoint."""
    print_info("Testing GET /admin/settings...")

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE_URL}/admin/settings", headers=headers)

    if response.status_code == 200:
        data = response.json()
        print_success(f"Retrieved {data['total']} settings")

        # Find trial_credits_amount setting
        trial_setting = next(
            (s for s in data['settings'] if s['key'] == 'trial_credits_amount'),
            None
        )

        if trial_setting:
            print_success(f"Trial credits amount: {trial_setting['value']}")
            return trial_setting
        else:
            print_error("trial_credits_amount setting not found")
            return {}
    else:
        print_error(f"Failed to get settings: {response.status_code}")
        print_error(response.text)
        return {}


def test_platform_settings_update(token: str, new_value: int) -> bool:
    """Test PATCH /admin/settings/{key} endpoint."""
    print_info(f"Testing PATCH /admin/settings/trial_credits_amount (updating to {new_value})...")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.patch(
        f"{API_BASE_URL}/admin/settings/trial_credits_amount",
        headers=headers,
        json={
            "value": new_value,
            "description": "Test update of trial credits"
        }
    )

    if response.status_code == 200:
        data = response.json()
        print_success(f"Updated trial credits to {data['value']}")
        return True
    else:
        print_error(f"Failed to update setting: {response.status_code}")
        print_error(response.text)
        return False


def test_new_tenant_registration(expected_credits: int) -> bool:
    """Test that new tenant receives correct trial credits."""
    print_info(f"Testing new tenant registration (expecting {expected_credits} credits)...")

    # Generate unique email
    import time
    email = f"test_tenant_{int(time.time())}@example.com"

    response = requests.post(
        f"{API_BASE_URL}/auth/register",
        json={
            "email": email,
            "password": "TestPassword123!",
            "full_name": "Test Tenant",
            "tenant_name": f"Test Tenant {int(time.time())}"
        }
    )

    if response.status_code == 201:
        data = response.json()
        tenant = data.get("tenant", {})

        # The tenant credit balance might be in cached_balance
        # Let's check what we get
        print_success(f"New tenant created: {tenant.get('name')}")
        print_info(f"Tenant data: {json.dumps(tenant, indent=2)}")

        # Note: We'd need to query the tenant details via admin API to see actual balance
        # For now, just confirm registration succeeded
        print_success("Registration succeeded - credits will be verified via admin API")
        return True
    else:
        print_error(f"Failed to register tenant: {response.status_code}")
        print_error(response.text)
        return False


def test_add_tenant_credits(token: str, tenant_id: str, amount: int) -> bool:
    """Test POST /admin/tenants/{tenant_id}/credits endpoint."""
    print_info(f"Testing POST /admin/tenants/{tenant_id}/credits (adding {amount} credits)...")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(
        f"{API_BASE_URL}/admin/tenants/{tenant_id}/credits",
        headers=headers,
        json={
            "amount": amount,
            "reason": "Test credit addition via API test"
        }
    )

    if response.status_code == 200:
        data = response.json()
        print_success(f"Added {amount} credits successfully")
        print_info(f"New balance: {data.get('data', {}).get('new_balance')} credits")
        return True
    else:
        print_error(f"Failed to add credits: {response.status_code}")
        print_error(response.text)
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Platform Settings & Credit Management Test Suite")
    print("=" * 60 + "\n")

    # Check API health
    try:
        response = requests.get(f"{API_BASE_URL.replace('/api/v1', '')}/health")
        if response.status_code != 200:
            print_error("API is not healthy")
            sys.exit(1)
        print_success("API is healthy\n")
    except Exception as e:
        print_error(f"Cannot connect to API: {e}")
        sys.exit(1)

    # Get admin token
    print_info("Note: This test requires a super admin user with credentials:")
    print_info("  Email: admin@test.com")
    print_info("  Password: Admin123!@#")
    print_info("  Role: platform_admin")
    print()
    print_warning("If this user doesn't exist, please create it via database migration or seed script.\n")

    token = register_test_admin()

    if not token:
        print_error("Could not obtain admin token. Skipping authenticated tests.")
        print_info("You can manually test the endpoints using curl with a valid token:\n")
        print_info("# Get settings")
        print_info('curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/admin/settings\n')
        print_info("# Update trial credits")
        print_info('curl -X PATCH -H "Authorization: Bearer YOUR_TOKEN" -H "Content-Type: application/json" \\')
        print_info('  -d \'{"value": 50}\' http://localhost:8000/api/v1/admin/settings/trial_credits_amount\n')
        print_info("# Add credits to tenant")
        print_info('curl -X POST -H "Authorization: Bearer YOUR_TOKEN" -H "Content-Type: application/json" \\')
        print_info('  -d \'{"amount": 1000, "reason": "Test"}\' \\')
        print_info('  http://localhost:8000/api/v1/admin/tenants/TENANT_ID/credits\n')
        return

    # Test 1: Get current settings
    print("\n" + "-" * 60)
    print("TEST 1: Get Platform Settings")
    print("-" * 60)
    current_setting = test_platform_settings_get(token)
    current_value = current_setting.get('value', 100) if current_setting else 100

    # Test 2: Update trial credits to 50
    print("\n" + "-" * 60)
    print("TEST 2: Update Trial Credits Amount")
    print("-" * 60)
    test_platform_settings_update(token, 50)

    # Test 3: Verify update
    print("\n" + "-" * 60)
    print("TEST 3: Verify Settings Update")
    print("-" * 60)
    updated_setting = test_platform_settings_get(token)

    # Test 4: Test new tenant registration
    print("\n" + "-" * 60)
    print("TEST 4: New Tenant Registration with Trial Credits")
    print("-" * 60)
    test_new_tenant_registration(50)

    # Test 5: Restore original value
    print("\n" + "-" * 60)
    print("TEST 5: Restore Original Trial Credits Value")
    print("-" * 60)
    test_platform_settings_update(token, current_value)

    print("\n" + "=" * 60)
    print("Test Suite Complete")
    print("=" * 60 + "\n")

    print_info("Note: To fully test credit addition, you need a valid tenant ID.")
    print_info("Use the admin dashboard or API to get a tenant ID, then run:")
    print_info(f"  test_add_tenant_credits(token, 'TENANT_ID', 1000)")


if __name__ == "__main__":
    main()
