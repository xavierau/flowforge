"""Integration tests for Credits API endpoints.

Test Coverage:
- GET /api/v1/credits/balance
- GET /api/v1/credits/transactions
- POST /api/v1/credits/topup
- POST /api/v1/credits/adjust
"""

import pytest
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, Tenant, Role, Permission, RolePermission
from app.models.credit_transaction import CreditTransaction
from app.models.enums import CreditTransactionType, ReferenceType


def ensure_billing_permission(db_session: Session, seed_roles: dict):
    """Ensure tenant:billing permission exists and is assigned to admin."""
    perm = db_session.query(Permission).filter(Permission.name == "tenant:billing").first()
    if not perm:
        perm = Permission(
            name="tenant:billing",
            resource="tenant",
            action="billing",
            description="Manage tenant billing"
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


def ensure_manage_permission(db_session: Session, seed_roles: dict):
    """Ensure tenant:manage permission exists and is assigned to admin."""
    perm = db_session.query(Permission).filter(Permission.name == "tenant:manage").first()
    if not perm:
        perm = Permission(
            name="tenant:manage",
            resource="tenant",
            action="manage",
            description="Manage tenant"
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


def seed_credits(db_session: Session, tenant, amount: int = 1000):
    """Seed credits for a tenant by creating a topup transaction and updating cached_balance."""
    from app.models import Tenant

    # If tenant_id is passed, fetch the tenant object
    if not isinstance(tenant, Tenant):
        tenant_obj = db_session.query(Tenant).filter(Tenant.id == tenant).first()
    else:
        tenant_obj = tenant

    transaction = CreditTransaction(
        tenant_id=tenant_obj.id,
        transaction_type=CreditTransactionType.TOPUP.value,
        amount=amount,
        description="Test credit seed",
        transaction_metadata={}
    )
    db_session.add(transaction)

    # Update cached_balance on tenant
    tenant_obj.cached_balance = (tenant_obj.cached_balance or 0) + amount
    db_session.commit()
    return transaction


class TestGetCreditBalanceEndpoint:
    """Tests for GET /api/v1/credits/balance endpoint."""

    def test_get_balance_success(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_role_permissions
    ):
        """Test successful credit balance retrieval."""
        # Seed some credits
        seed_credits(db_session, test_tenant.id, amount=500)

        response = client.get(
            "/api/v1/credits/balance",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["tenant_id"] == str(test_tenant.id)
        assert data["balance"] >= 500
        assert "updated_at" in data

    def test_get_balance_zero(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_role_permissions
    ):
        """Test credit balance with no transactions returns 0."""
        # Delete any existing transactions for this tenant
        db_session.query(CreditTransaction).filter(
            CreditTransaction.tenant_id == test_tenant.id
        ).delete()
        db_session.commit()

        response = client.get(
            "/api/v1/credits/balance",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["balance"] == 0

    def test_get_balance_unauthorized(self, client: TestClient):
        """Test balance retrieval without authentication returns 401."""
        response = client.get("/api/v1/credits/balance")
        assert response.status_code == 401

    def test_get_balance_tenant_isolation(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that balance is isolated per tenant."""
        # Seed credits for current tenant
        seed_credits(db_session, test_tenant.id, amount=500)

        # Create another tenant with different credits
        other_tenant = Tenant(
            name="Other Tenant",
            slug="other-tenant-credits",
            cached_balance=0
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        seed_credits(db_session, other_tenant.id, amount=9999)

        # Current user should only see their tenant's balance
        response = client.get(
            "/api/v1/credits/balance",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["tenant_id"] == str(test_tenant.id)
        # Should not see other tenant's 9999 credits
        assert data["balance"] < 9999


class TestGetTransactionHistoryEndpoint:
    """Tests for GET /api/v1/credits/transactions endpoint."""

    def test_list_transactions_success(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_role_permissions
    ):
        """Test successful transaction list retrieval."""
        # Seed a transaction
        seed_credits(db_session, test_tenant.id, amount=100)

        response = client.get(
            "/api/v1/credits/transactions",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "transactions" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert len(data["transactions"]) > 0

    def test_list_transactions_pagination(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_role_permissions
    ):
        """Test transaction list pagination."""
        # Create multiple transactions
        for i in range(5):
            seed_credits(db_session, test_tenant.id, amount=100)

        # Get first page
        response1 = client.get(
            "/api/v1/credits/transactions",
            params={"limit": 2, "offset": 0},
            headers=admin_auth_headers
        )

        assert response1.status_code == 200
        data1 = response1.json()

        assert len(data1["transactions"]) == 2
        assert data1["limit"] == 2
        assert data1["offset"] == 0

        # Get second page
        response2 = client.get(
            "/api/v1/credits/transactions",
            params={"limit": 2, "offset": 2},
            headers=admin_auth_headers
        )

        assert response2.status_code == 200
        data2 = response2.json()

        assert data2["offset"] == 2
        # Transaction IDs should be different
        if len(data2["transactions"]) > 0:
            assert data1["transactions"][0]["id"] != data2["transactions"][0]["id"]

    def test_list_transactions_type_filter(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_role_permissions
    ):
        """Test filtering transactions by type."""
        # Seed a topup transaction
        seed_credits(db_session, test_tenant.id, amount=100)

        # Filter by topup type
        response = client.get(
            "/api/v1/credits/transactions",
            params={"transaction_type": "topup"},
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        for tx in data["transactions"]:
            assert tx["transaction_type"] == "topup"

    def test_list_transactions_tenant_isolation(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test that transactions are isolated per tenant."""
        # Seed transaction for current tenant
        seed_credits(db_session, test_tenant.id, amount=100)

        # Create another tenant with transactions
        other_tenant = Tenant(
            name="Other Tenant TX",
            slug="other-tenant-tx",
            cached_balance=0
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        other_tx = CreditTransaction(
            tenant_id=other_tenant.id,
            transaction_type=CreditTransactionType.TOPUP.value,
            amount=99999,
            description="Other tenant transaction",
            transaction_metadata={}
        )
        db_session.add(other_tx)
        db_session.commit()

        # Current user should only see their tenant's transactions
        response = client.get(
            "/api/v1/credits/transactions",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should not contain other tenant's transactions
        for tx in data["transactions"]:
            assert tx["amount"] != 99999

    def test_list_transactions_unauthorized(self, client: TestClient):
        """Test transaction list without authentication returns 401."""
        response = client.get("/api/v1/credits/transactions")
        assert response.status_code == 401


class TestTopupCreditsEndpoint:
    """Tests for POST /api/v1/credits/topup endpoint."""

    def test_topup_success(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successful credit top-up."""
        ensure_billing_permission(db_session, seed_roles)

        response = client.post(
            "/api/v1/credits/topup",
            json={
                "credits": 100,
                "amount_usd": 10.00,
                "payment_intent_id": f"pi_test_{uuid4().hex[:8]}"
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 201
        data = response.json()

        assert "transaction_id" in data
        assert data["credits_added"] == 100
        assert data["new_balance"] >= 100
        assert "created_at" in data

    def test_topup_idempotency(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test idempotent top-up with same payment_intent_id."""
        ensure_billing_permission(db_session, seed_roles)

        payment_intent_id = f"pi_idempotent_{uuid4().hex[:8]}"

        # First top-up
        response1 = client.post(
            "/api/v1/credits/topup",
            json={
                "credits": 100,
                "amount_usd": 10.00,
                "payment_intent_id": payment_intent_id
            },
            headers=admin_auth_headers
        )

        assert response1.status_code == 201
        data1 = response1.json()

        # Second top-up with same payment_intent_id should return same transaction
        response2 = client.post(
            "/api/v1/credits/topup",
            json={
                "credits": 100,
                "amount_usd": 10.00,
                "payment_intent_id": payment_intent_id
            },
            headers=admin_auth_headers
        )

        assert response2.status_code == 201
        data2 = response2.json()

        # Should be the same transaction (idempotent)
        assert data1["transaction_id"] == data2["transaction_id"]

    def test_topup_missing_permission(
        self,
        client: TestClient,
        db_session: Session,
        auth_headers: dict,
        seed_role_permissions
    ):
        """Test top-up without billing permission returns 403."""
        response = client.post(
            "/api/v1/credits/topup",
            json={
                "credits": 100,
                "amount_usd": 10.00
            },
            headers=auth_headers
        )

        assert response.status_code == 403

    def test_topup_invalid_credits_zero(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test top-up with zero credits returns 422."""
        ensure_billing_permission(db_session, seed_roles)

        response = client.post(
            "/api/v1/credits/topup",
            json={
                "credits": 0,
                "amount_usd": 10.00
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 422

    def test_topup_invalid_credits_negative(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test top-up with negative credits returns 422."""
        ensure_billing_permission(db_session, seed_roles)

        response = client.post(
            "/api/v1/credits/topup",
            json={
                "credits": -100,
                "amount_usd": 10.00
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 422

    def test_topup_unauthorized(self, client: TestClient):
        """Test top-up without authentication returns 401."""
        response = client.post(
            "/api/v1/credits/topup",
            json={
                "credits": 100,
                "amount_usd": 10.00
            }
        )
        assert response.status_code == 401


class TestAdjustCreditsEndpoint:
    """Tests for POST /api/v1/credits/adjust endpoint."""

    def test_adjust_positive_success(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successful positive credit adjustment."""
        ensure_manage_permission(db_session, seed_roles)

        response = client.post(
            "/api/v1/credits/adjust",
            json={
                "amount": 50,
                "reason": "Promotional credit bonus for testing purposes"
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert data["transaction_type"] == "admin_adjustment"
        assert data["amount"] == 50
        assert "Promotional" in data["description"]

    def test_adjust_negative_success(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test successful negative credit adjustment."""
        ensure_manage_permission(db_session, seed_roles)

        # First add some credits to allow deduction
        seed_credits(db_session, test_tenant.id, amount=100)

        response = client.post(
            "/api/v1/credits/adjust",
            json={
                "amount": -30,
                "reason": "Chargeback adjustment for fraudulent transaction"
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 201
        data = response.json()

        assert data["amount"] == -30

    def test_adjust_missing_permission(
        self,
        client: TestClient,
        db_session: Session,
        auth_headers: dict,
        seed_role_permissions
    ):
        """Test adjustment without manage permission returns 403."""
        response = client.post(
            "/api/v1/credits/adjust",
            json={
                "amount": 50,
                "reason": "This should fail without permission"
            },
            headers=auth_headers
        )

        assert response.status_code == 403

    def test_adjust_zero_amount_validation(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test adjustment with zero amount returns 422."""
        ensure_manage_permission(db_session, seed_roles)

        response = client.post(
            "/api/v1/credits/adjust",
            json={
                "amount": 0,
                "reason": "Zero adjustment should fail validation"
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 422

    def test_adjust_reason_too_short(
        self,
        client: TestClient,
        db_session: Session,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test adjustment with short reason returns 422."""
        ensure_manage_permission(db_session, seed_roles)

        response = client.post(
            "/api/v1/credits/adjust",
            json={
                "amount": 50,
                "reason": "short"  # Less than 10 chars
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 422

    def test_adjust_negative_balance_allowed(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test admin can force negative balance (for chargebacks, fraud)."""
        ensure_manage_permission(db_session, seed_roles)

        # Clear any existing credits
        db_session.query(CreditTransaction).filter(
            CreditTransaction.tenant_id == test_tenant.id
        ).delete()
        db_session.commit()

        # Deduct more than available (should work for admin with allow_negative)
        response = client.post(
            "/api/v1/credits/adjust",
            json={
                "amount": -100,
                "reason": "Fraud chargeback - forcing negative balance"
            },
            headers=admin_auth_headers
        )

        # Admin adjustments should allow negative balance
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == -100

    def test_adjust_unauthorized(self, client: TestClient):
        """Test adjustment without authentication returns 401."""
        response = client.post(
            "/api/v1/credits/adjust",
            json={
                "amount": 50,
                "reason": "This should fail without authentication"
            }
        )
        assert response.status_code == 401

    def test_adjust_metadata_tracking(
        self,
        client: TestClient,
        db_session: Session,
        test_tenant: Tenant,
        admin_auth_headers: dict,
        seed_roles: dict[str, Role],
        seed_role_permissions
    ):
        """Test adjustment includes admin user in metadata."""
        ensure_manage_permission(db_session, seed_roles)

        response = client.post(
            "/api/v1/credits/adjust",
            json={
                "amount": 25,
                "reason": "Test adjustment with metadata tracking"
            },
            headers=admin_auth_headers
        )

        assert response.status_code == 201
        data = response.json()

        # Check metadata is returned
        assert "metadata" in data
        assert "admin_user" in data["metadata"]
