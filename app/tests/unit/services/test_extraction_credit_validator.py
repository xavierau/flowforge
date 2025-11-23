"""Unit tests for ExtractionCreditValidator service."""

import pytest
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.extraction_service import ExtractionCreditValidator
from app.models.tenant import Tenant
from app.models.user import User
from app.models.credit_transaction import CreditTransaction
from app.models.enums import CreditTransactionType, ReferenceType
from app.exceptions.credits import InsufficientCreditsError


class TestExtractionCreditValidator:
    """Unit tests for credit validation logic."""

    def test_validate_and_deduct_credits_success(self, db_session: Session):
        """
        GIVEN a tenant with sufficient credits (100 credits)
        WHEN validate_and_deduct_credits is called for 5-page document
        THEN credits are deducted and transaction is created
        """
        # Arrange
        tenant = Tenant(id=uuid4(), name="Test Tenant", cached_balance=100)
        db_session.add(tenant)

        user = User(
            id=uuid4(),
            tenant_id=tenant.id,
            email="test@example.com",
            hashed_password="test",
            role="member"
        )
        db_session.add(user)
        db_session.commit()

        job_id = uuid4()
        document_id = uuid4()

        validator = ExtractionCreditValidator(db_session)

        # Act
        transaction, required_credits = validator.validate_and_deduct_credits(
            tenant_id=tenant.id,
            page_count=5,
            job_id=job_id,
            document_id=document_id,
            user_id=user.id,
            model_provider="google",
            model_name="gemini-2.5-flash"
        )

        # Assert
        assert transaction is not None
        assert required_credits == 5
        assert transaction.amount == -5
        assert transaction.reference_id == job_id
        assert transaction.reference_type == ReferenceType.EXTRACTION_JOB.value

        # Verify tenant balance updated
        db_session.refresh(tenant)
        assert tenant.cached_balance == 95

    def test_validate_and_deduct_credits_insufficient_balance(self, db_session: Session):
        """
        GIVEN a tenant with insufficient credits (3 credits)
        WHEN validate_and_deduct_credits is called for 5-page document
        THEN HTTPException(402) is raised with error details
        """
        # Arrange
        tenant = Tenant(id=uuid4(), name="Test Tenant", cached_balance=3)
        db_session.add(tenant)

        user = User(
            id=uuid4(),
            tenant_id=tenant.id,
            email="test@example.com",
            hashed_password="test",
            role="member"
        )
        db_session.add(user)
        db_session.commit()

        validator = ExtractionCreditValidator(db_session)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_and_deduct_credits(
                tenant_id=tenant.id,
                page_count=5,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=user.id,
                model_provider="google",
                model_name="gemini-2.5-flash"
            )

        assert exc_info.value.status_code == 402
        detail = exc_info.value.detail
        assert detail["error"] == "insufficient_credits"
        assert detail["required_credits"] == 5
        assert detail["available_credits"] == 3
        assert detail["credits_needed"] == 2

        # Verify balance unchanged
        db_session.refresh(tenant)
        assert tenant.cached_balance == 3

    def test_validate_and_deduct_credits_tenant_not_found(self, db_session: Session):
        """
        GIVEN a non-existent tenant ID
        WHEN validate_and_deduct_credits is called
        THEN HTTPException(404) is raised
        """
        validator = ExtractionCreditValidator(db_session)

        with pytest.raises(HTTPException) as exc_info:
            validator.validate_and_deduct_credits(
                tenant_id=uuid4(),  # Non-existent
                page_count=1,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="google",
                model_name="gemini-2.5-flash"
            )

        assert exc_info.value.status_code == 404
        assert "Tenant not found" in str(exc_info.value.detail)

    def test_validate_and_deduct_credits_metadata_correct(self, db_session: Session):
        """
        GIVEN valid credit deduction request
        WHEN validate_and_deduct_credits is called
        THEN transaction metadata contains all required fields
        """
        tenant = Tenant(id=uuid4(), name="Test Tenant", cached_balance=100)
        db_session.add(tenant)

        user = User(
            id=uuid4(),
            tenant_id=tenant.id,
            email="test@example.com",
            hashed_password="test",
            role="member"
        )
        db_session.add(user)
        db_session.commit()

        job_id = uuid4()
        document_id = uuid4()

        validator = ExtractionCreditValidator(db_session)
        transaction, _ = validator.validate_and_deduct_credits(
            tenant_id=tenant.id,
            page_count=3,
            job_id=job_id,
            document_id=document_id,
            user_id=user.id,
            model_provider="openai",
            model_name="gpt-4-vision"
        )

        metadata = transaction.transaction_metadata
        assert metadata["job_id"] == str(job_id)
        assert metadata["document_id"] == str(document_id)
        assert metadata["page_count"] == 3
        assert metadata["model_provider"] == "openai"
        assert metadata["model_name"] == "gpt-4-vision"

    def test_validate_and_deduct_credits_zero_page_count(self, db_session: Session):
        """
        GIVEN a document with 0 pages
        WHEN validate_and_deduct_credits is called
        THEN defaults to 1 credit minimum
        """
        tenant = Tenant(id=uuid4(), name="Test Tenant", cached_balance=100)
        db_session.add(tenant)

        user = User(
            id=uuid4(),
            tenant_id=tenant.id,
            email="test@example.com",
            hashed_password="test",
            role="member"
        )
        db_session.add(user)
        db_session.commit()

        validator = ExtractionCreditValidator(db_session)
        transaction, required_credits = validator.validate_and_deduct_credits(
            tenant_id=tenant.id,
            page_count=0,  # Edge case
            job_id=uuid4(),
            document_id=uuid4(),
            user_id=user.id,
            model_provider="google",
            model_name="gemini-2.5-flash"
        )

        assert required_credits == 1
        assert transaction.amount == -1

    def test_validate_and_deduct_credits_transaction_type_correct(self, db_session: Session):
        """
        GIVEN valid credit deduction
        WHEN transaction is created
        THEN transaction_type is DEDUCTION and reference_type is EXTRACTION_JOB
        """
        tenant = Tenant(id=uuid4(), name="Test Tenant", cached_balance=100)
        db_session.add(tenant)

        user = User(
            id=uuid4(),
            tenant_id=tenant.id,
            email="test@example.com",
            hashed_password="test",
            role="member"
        )
        db_session.add(user)
        db_session.commit()

        validator = ExtractionCreditValidator(db_session)
        transaction, _ = validator.validate_and_deduct_credits(
            tenant_id=tenant.id,
            page_count=2,
            job_id=uuid4(),
            document_id=uuid4(),
            user_id=user.id,
            model_provider="google",
            model_name="gemini-2.5-flash"
        )

        # Verify enum values are used correctly
        assert transaction.transaction_type == CreditTransactionType.DEDUCTION.value
        assert transaction.reference_type == ReferenceType.EXTRACTION_JOB.value
