"""Unit tests for CreditService."""

import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.credit_service import CreditService
from app.models.credit_transaction import CreditTransaction
from app.models.tenant import Tenant
from app.models.extraction_job import ExtractionJob
from app.models.document import Document
from app.models.user import User
from app.exceptions.credits import InsufficientCreditsError, CreditOperationError


class TestCreditServiceCalculateBalance:
    """Tests for calculate_balance method."""

    def test_balance_zero_for_new_tenant(self, db_session: Session):
        """Balance is 0 for tenant with no transactions."""
        service = CreditService(db_session)
        tenant_id = uuid4()
        balance = service.calculate_balance(tenant_id)
        assert balance == 0

    def test_balance_with_single_topup(self, db_session: Session, tenant: Tenant):
        """Balance reflects single top-up transaction."""
        service = CreditService(db_session)
        service.add_credits(
            tenant_id=tenant.id,
            amount=100,
            transaction_type="topup",
            description="Test top-up"
        )
        db_session.commit()
        balance = service.calculate_balance(tenant.id)
        assert balance == 100

    def test_balance_with_multiple_topups(self, db_session: Session, tenant: Tenant):
        """Balance accumulates multiple top-ups."""
        service = CreditService(db_session)
        service.add_credits(tenant.id, 50, "topup", "Top-up 1")
        service.add_credits(tenant.id, 75, "topup", "Top-up 2")
        service.add_credits(tenant.id, 25, "topup", "Top-up 3")
        db_session.commit()
        balance = service.calculate_balance(tenant.id)
        assert balance == 150

    def test_balance_with_deduction(self, db_session: Session, tenant: Tenant):
        """Balance reflects deduction."""
        service = CreditService(db_session)
        service.add_credits(tenant.id, 100, "topup", "Top-up")
        service.deduct_credits(
            tenant_id=tenant.id,
            amount=30,
            reference_type="test",
            reference_id=uuid4(),
            description="Test deduction"
        )
        db_session.commit()
        balance = service.calculate_balance(tenant.id)
        assert balance == 70

    def test_balance_with_multiple_transactions(self, db_session: Session, tenant: Tenant):
        """Balance correctly calculates with mixed transactions."""
        service = CreditService(db_session)
        service.add_credits(tenant.id, 100, "topup", "Top-up 1")
        service.deduct_credits(tenant.id, 20, "test", uuid4(), "Deduct 1")
        service.add_credits(tenant.id, 50, "topup", "Top-up 2")
        service.deduct_credits(tenant.id, 15, "test", uuid4(), "Deduct 2")
        db_session.commit()
        balance = service.calculate_balance(tenant.id)
        assert balance == 115  # 100 - 20 + 50 - 15


class TestCreditServiceCheckSufficient:
    """Tests for check_sufficient_credits method."""

    def test_sufficient_credits_returns_true(self, db_session: Session, tenant: Tenant):
        """Returns True when credits are sufficient."""
        service = CreditService(db_session)
        service.add_credits(tenant.id, 50, "topup", "Top-up")
        db_session.commit()
        has_sufficient, balance = service.check_sufficient_credits(tenant.id, 30)
        assert has_sufficient is True
        assert balance == 50

    def test_insufficient_credits_returns_false(self, db_session: Session, tenant: Tenant):
        """Returns False when credits are insufficient."""
        service = CreditService(db_session)
        service.add_credits(tenant.id, 20, "topup", "Top-up")
        db_session.commit()
        has_sufficient, balance = service.check_sufficient_credits(tenant.id, 30)
        assert has_sufficient is False
        assert balance == 20

    def test_exact_credits_returns_true(self, db_session: Session, tenant: Tenant):
        """Returns True when balance exactly equals required."""
        service = CreditService(db_session)
        service.add_credits(tenant.id, 25, "topup", "Top-up")
        db_session.commit()
        has_sufficient, balance = service.check_sufficient_credits(tenant.id, 25)
        assert has_sufficient is True
        assert balance == 25

    def test_zero_balance_insufficient_for_any_amount(self, db_session: Session, tenant: Tenant):
        """Returns False for any positive amount when balance is 0."""
        service = CreditService(db_session)
        has_sufficient, balance = service.check_sufficient_credits(tenant.id, 1)
        assert has_sufficient is False
        assert balance == 0

    def test_negative_required_raises_error(self, db_session: Session, tenant: Tenant):
        """Raises ValueError if required_credits is negative."""
        service = CreditService(db_session)
        with pytest.raises(ValueError, match="Required credits must be non-negative"):
            service.check_sufficient_credits(tenant.id, -10)


class TestCreditServiceDeductCredits:
    """Tests for deduct_credits method."""

    def test_deduction_creates_negative_transaction(self, db_session: Session, tenant: Tenant):
        """Deduction creates transaction with negative amount."""
        service = CreditService(db_session)
        tx = service.deduct_credits(
            tenant_id=tenant.id,
            amount=25,
            reference_type="test",
            reference_id=uuid4(),
            description="Test deduction"
        )
        assert tx.amount == -25
        assert tx.transaction_type == "deduction"
        assert tx.description == "Test deduction"

    def test_deduction_with_metadata(self, db_session: Session, tenant: Tenant):
        """Deduction stores metadata correctly."""
        service = CreditService(db_session)
        metadata = {"job_id": "123", "page_count": 5}
        tx = service.deduct_credits(
            tenant_id=tenant.id,
            amount=10,
            reference_type="test",
            reference_id=uuid4(),
            description="Test",
            metadata=metadata
        )
        assert tx.transaction_metadata == metadata

    def test_deduction_zero_raises_error(self, db_session: Session, tenant: Tenant):
        """Raises ValueError if deduction amount is 0."""
        service = CreditService(db_session)
        with pytest.raises(ValueError, match="Deduction amount must be positive"):
            service.deduct_credits(tenant.id, 0, "test", uuid4(), "Test")

    def test_deduction_negative_raises_error(self, db_session: Session, tenant: Tenant):
        """Raises ValueError if deduction amount is negative."""
        service = CreditService(db_session)
        with pytest.raises(ValueError, match="Deduction amount must be positive"):
            service.deduct_credits(tenant.id, -10, "test", uuid4(), "Test")


class TestCreditServiceAddCredits:
    """Tests for add_credits method."""

    def test_add_credits_creates_positive_transaction(self, db_session: Session, tenant: Tenant):
        """Adding credits creates transaction with positive amount."""
        service = CreditService(db_session)
        tx = service.add_credits(
            tenant_id=tenant.id,
            amount=100,
            transaction_type="topup",
            description="Test top-up"
        )
        assert tx.amount == 100
        assert tx.transaction_type == "topup"

    def test_add_credits_with_stripe_info(self, db_session: Session, tenant: Tenant):
        """Adding credits stores Stripe payment info."""
        service = CreditService(db_session)
        tx = service.add_credits(
            tenant_id=tenant.id,
            amount=50,
            transaction_type="topup",
            description="Stripe purchase",
            stripe_payment_intent_id="pi_123456",
            stripe_charge_id="ch_123456"
        )
        assert tx.stripe_payment_intent_id == "pi_123456"
        assert tx.stripe_charge_id == "ch_123456"

    def test_add_credits_zero_raises_error(self, db_session: Session, tenant: Tenant):
        """Raises ValueError if credit amount is 0."""
        service = CreditService(db_session)
        with pytest.raises(ValueError, match="Credit amount must be positive"):
            service.add_credits(tenant.id, 0, "topup", "Test")

    def test_add_credits_negative_raises_error(self, db_session: Session, tenant: Tenant):
        """Raises ValueError if credit amount is negative."""
        service = CreditService(db_session)
        with pytest.raises(ValueError, match="Credit amount must be positive"):
            service.add_credits(tenant.id, -10, "topup", "Test")

    def test_add_credits_invalid_type_raises_error(self, db_session: Session, tenant: Tenant):
        """Raises ValueError for invalid transaction type."""
        service = CreditService(db_session)
        with pytest.raises(ValueError, match="Invalid transaction type"):
            service.add_credits(tenant.id, 10, "invalid_type", "Test")


class TestCreditServiceFinalizeJobCredits:
    """Tests for finalize_job_credits method (idempotency)."""

    def test_finalize_deducts_credits_once(
        self, db_session: Session, tenant: Tenant, extraction_job: ExtractionJob
    ):
        """Finalize deducts credits on first call."""
        service = CreditService(db_session)

        # Add credits first
        service.add_credits(tenant.id, 100, "topup", "Top-up")
        extraction_job.credits_cost = 10
        db_session.commit()

        # First call - should deduct
        tx = service.finalize_job_credits(
            job_id=extraction_job.id,
            tenant_id=tenant.id,
            actual_credits_used=10
        )
        assert tx is not None
        db_session.commit()

        balance = service.calculate_balance(tenant.id)
        assert balance == 90

    def test_finalize_is_idempotent(
        self, db_session: Session, tenant: Tenant, extraction_job: ExtractionJob
    ):
        """Finalize is idempotent - only deducts once."""
        service = CreditService(db_session)

        # Add credits
        service.add_credits(tenant.id, 100, "topup", "Top-up")
        extraction_job.credits_cost = 10
        db_session.commit()

        # First call - should deduct
        tx1 = service.finalize_job_credits(
            job_id=extraction_job.id,
            tenant_id=tenant.id,
            actual_credits_used=10
        )
        assert tx1 is not None
        db_session.commit()

        # Second call - should skip (already deducted)
        tx2 = service.finalize_job_credits(
            job_id=extraction_job.id,
            tenant_id=tenant.id,
            actual_credits_used=10
        )
        assert tx2 is None

        # Balance should only reflect one deduction
        balance = service.calculate_balance(tenant.id)
        assert balance == 90

    def test_finalize_links_transaction_to_job(
        self, db_session: Session, tenant: Tenant, extraction_job: ExtractionJob
    ):
        """Finalize links credit transaction to job."""
        service = CreditService(db_session)

        service.add_credits(tenant.id, 100, "topup", "Top-up")
        extraction_job.credits_cost = 5
        db_session.commit()

        tx = service.finalize_job_credits(
            job_id=extraction_job.id,
            tenant_id=tenant.id,
            actual_credits_used=5
        )
        db_session.commit()
        db_session.refresh(extraction_job)

        assert extraction_job.credit_transaction_id == tx.id
        assert extraction_job.credits_deducted is True


class TestCreditServiceGetTransactionHistory:
    """Tests for get_transaction_history method."""

    def test_get_empty_history(self, db_session: Session, tenant: Tenant):
        """Returns empty list for tenant with no transactions."""
        service = CreditService(db_session)
        transactions, total = service.get_transaction_history(tenant.id)
        assert transactions == []
        assert total == 0

    def test_get_history_ordered_by_date(self, db_session: Session, tenant: Tenant):
        """Returns transactions ordered by created_at DESC."""
        service = CreditService(db_session)

        # Add multiple transactions
        service.add_credits(tenant.id, 10, "topup", "First")
        service.add_credits(tenant.id, 20, "topup", "Second")
        service.add_credits(tenant.id, 30, "topup", "Third")
        db_session.commit()

        transactions, total = service.get_transaction_history(tenant.id, limit=10)

        assert total == 3
        assert len(transactions) == 3
        # Should be in reverse chronological order
        assert transactions[0].description == "Third"
        assert transactions[1].description == "Second"
        assert transactions[2].description == "First"

    def test_get_history_pagination(self, db_session: Session, tenant: Tenant):
        """Pagination works correctly."""
        service = CreditService(db_session)

        # Add 5 transactions
        for i in range(5):
            service.add_credits(tenant.id, 10, "topup", f"Transaction {i}")
        db_session.commit()

        # Get first 2
        transactions, total = service.get_transaction_history(tenant.id, limit=2, offset=0)
        assert len(transactions) == 2
        assert total == 5

        # Get next 2
        transactions, total = service.get_transaction_history(tenant.id, limit=2, offset=2)
        assert len(transactions) == 2
        assert total == 5

    def test_get_history_filter_by_type(self, db_session: Session, tenant: Tenant):
        """Filter by transaction type works."""
        service = CreditService(db_session)

        service.add_credits(tenant.id, 10, "topup", "Top-up 1")
        service.add_credits(tenant.id, 20, "admin_adjustment", "Adjustment")
        service.add_credits(tenant.id, 30, "topup", "Top-up 2")
        db_session.commit()

        transactions, total = service.get_transaction_history(
            tenant.id, transaction_type="topup"
        )

        assert total == 2
        assert all(tx.transaction_type == "topup" for tx in transactions)


class TestCreditServiceReserveCredits:
    """Tests for reserve_credits_for_job method."""

    def test_reserve_with_sufficient_credits(
        self, db_session: Session, tenant: Tenant, extraction_job: ExtractionJob
    ):
        """Reserve succeeds with sufficient credits."""
        service = CreditService(db_session)

        service.add_credits(tenant.id, 50, "topup", "Top-up")
        db_session.commit()

        success, error_msg = service.reserve_credits_for_job(
            tenant_id=tenant.id,
            job_id=extraction_job.id,
            required_credits=10
        )

        assert success is True
        assert error_msg is None

    def test_reserve_with_insufficient_credits(
        self, db_session: Session, tenant: Tenant, extraction_job: ExtractionJob
    ):
        """Reserve fails with insufficient credits."""
        service = CreditService(db_session)

        service.add_credits(tenant.id, 5, "topup", "Top-up")
        db_session.commit()

        success, error_msg = service.reserve_credits_for_job(
            tenant_id=tenant.id,
            job_id=extraction_job.id,
            required_credits=10
        )

        assert success is False
        assert "Insufficient credits" in error_msg

    def test_reserve_updates_job_cost(
        self, db_session: Session, tenant: Tenant, extraction_job: ExtractionJob
    ):
        """Reserve updates job with cost estimate."""
        service = CreditService(db_session)

        service.add_credits(tenant.id, 50, "topup", "Top-up")
        db_session.commit()

        service.reserve_credits_for_job(
            tenant_id=tenant.id,
            job_id=extraction_job.id,
            required_credits=15
        )
        db_session.commit()
        db_session.refresh(extraction_job)

        assert extraction_job.credits_cost == 15
