"""Unit tests for Extraction Service.

Tests input validation, credit deduction, and pessimistic locking.

This module tests the ExtractionCreditValidator service which handles:
- Input validation (page_count, model_provider, model_name)
- Credit balance checking and deduction
- Pessimistic locking via SELECT FOR UPDATE
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError

from app.services.extraction_service import ExtractionCreditValidator
from app.exceptions.credits import InsufficientCreditsError


class TestInputValidation:
    """Tests for input validation in ExtractionCreditValidator."""

    def test_page_count_minimum_valid(self):
        """Page count >= 1 is valid and should not raise an error."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 100
        mock_tenant.id = uuid4()

        # Setup query chain to return tenant
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        # Mock CreditService.deduct_credits
        mock_transaction = MagicMock()
        mock_transaction.id = uuid4()

        validator = ExtractionCreditValidator(mock_db)

        with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction):
            # Act - should not raise for page_count = 1
            transaction, cost = validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=1,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="google",
                model_name="gemini-2.5-flash"
            )

            # Assert
            assert transaction == mock_transaction
            assert cost == 1

    def test_page_count_zero_invalid(self):
        """Page count of 0 should calculate as 1 credit (minimum)."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 100
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        mock_transaction = MagicMock()
        mock_transaction.id = uuid4()

        validator = ExtractionCreditValidator(mock_db)

        with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction):
            # Act - page_count=0 should default to 1 credit
            transaction, cost = validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=0,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="google",
                model_name="gemini-2.5-flash"
            )

            # Assert - cost should be 1 (minimum)
            assert cost == 1

    def test_page_count_negative_invalid(self):
        """Negative page_count should raise HTTPException 400."""
        # Arrange
        mock_db = MagicMock()
        validator = ExtractionCreditValidator(mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=-5,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="google",
                model_name="gemini-2.5-flash"
            )

        assert exc_info.value.status_code == 400
        assert "page_count" in str(exc_info.value.detail)
        assert "cannot be negative" in str(exc_info.value.detail)

    def test_page_count_exceeds_maximum(self):
        """Page count exceeding 10000 should raise HTTPException 400."""
        # Arrange
        mock_db = MagicMock()
        validator = ExtractionCreditValidator(mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=10001,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="google",
                model_name="gemini-2.5-flash"
            )

        assert exc_info.value.status_code == 400
        assert "page_count" in str(exc_info.value.detail)
        assert "exceeds maximum" in str(exc_info.value.detail)

    def test_model_provider_whitelist_valid(self):
        """Valid providers (google, openai, deepseek, llamaextract) should pass validation."""
        # Arrange
        valid_providers = ["google", "openai", "deepseek", "llamaextract"]

        for provider in valid_providers:
            mock_db = MagicMock()
            mock_tenant = MagicMock()
            mock_tenant.cached_balance = 100
            mock_tenant.id = uuid4()

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.with_for_update.return_value = mock_query
            mock_query.first.return_value = mock_tenant
            mock_db.query.return_value = mock_query
            mock_db.execute = MagicMock()

            mock_transaction = MagicMock()
            mock_transaction.id = uuid4()

            validator = ExtractionCreditValidator(mock_db)

            with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction):
                # Act - should not raise
                transaction, cost = validator.validate_and_deduct_credits(
                    tenant_id=uuid4(),
                    page_count=5,
                    job_id=uuid4(),
                    document_id=uuid4(),
                    user_id=uuid4(),
                    model_provider=provider,
                    model_name="test-model"
                )

                # Assert
                assert transaction == mock_transaction

    def test_model_provider_invalid(self):
        """Invalid provider should raise HTTPException 400."""
        # Arrange
        mock_db = MagicMock()
        validator = ExtractionCreditValidator(mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=5,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="invalid_provider",
                model_name="some-model"
            )

        assert exc_info.value.status_code == 400
        assert "model_provider" in str(exc_info.value.detail)
        assert "Invalid provider" in str(exc_info.value.detail)

    def test_model_name_required_empty_string(self):
        """Empty model name should raise HTTPException 400."""
        # Arrange
        mock_db = MagicMock()
        validator = ExtractionCreditValidator(mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=5,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="google",
                model_name=""
            )

        assert exc_info.value.status_code == 400
        assert "model_name" in str(exc_info.value.detail)
        assert "cannot be empty" in str(exc_info.value.detail)

    def test_model_name_required_whitespace_only(self):
        """Whitespace-only model name should raise HTTPException 400."""
        # Arrange
        mock_db = MagicMock()
        validator = ExtractionCreditValidator(mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=5,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="google",
                model_name="   "
            )

        assert exc_info.value.status_code == 400
        assert "model_name" in str(exc_info.value.detail)
        assert "cannot be empty" in str(exc_info.value.detail)


class TestCreditDeduction:
    """Tests for credit deduction in ExtractionCreditValidator."""

    def test_sufficient_credits_success(self):
        """Extraction proceeds when tenant has sufficient credits."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 100
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        mock_transaction = MagicMock()
        mock_transaction.id = uuid4()

        validator = ExtractionCreditValidator(mock_db)

        with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction):
            # Act
            transaction, cost = validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=10,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="google",
                model_name="gemini-2.5-flash"
            )

            # Assert
            assert transaction == mock_transaction
            assert cost == 10

    def test_insufficient_credits_error(self):
        """InsufficientCreditsError raised when tenant has insufficient credits."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 3  # Only 3 credits, need 10
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        validator = ExtractionCreditValidator(mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=10,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="google",
                model_name="gemini-2.5-flash"
            )

        assert exc_info.value.status_code == 402  # Payment Required
        assert "insufficient_credits" in str(exc_info.value.detail)

    def test_credit_deduction_atomicity(self):
        """Credits deducted atomically with job creation via CreditService."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        tenant_id = uuid4()
        job_id = uuid4()
        document_id = uuid4()
        user_id = uuid4()
        mock_tenant.cached_balance = 100
        mock_tenant.id = tenant_id

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        mock_transaction = MagicMock()
        mock_transaction.id = uuid4()

        validator = ExtractionCreditValidator(mock_db)

        with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction) as mock_deduct:
            # Act
            validator.validate_and_deduct_credits(
                tenant_id=tenant_id,
                page_count=5,
                job_id=job_id,
                document_id=document_id,
                user_id=user_id,
                model_provider="google",
                model_name="gemini-2.5-flash"
            )

            # Assert - verify deduct_credits was called with correct parameters
            mock_deduct.assert_called_once()
            call_kwargs = mock_deduct.call_args[1]
            assert call_kwargs['tenant_id'] == tenant_id
            assert call_kwargs['amount'] == 5
            assert call_kwargs['reference_id'] == job_id
            assert call_kwargs['created_by_user_id'] == user_id
            assert call_kwargs['allow_negative'] is False

    def test_credit_calculation_by_page_count(self):
        """Credits calculated based on page count (1 credit per page)."""
        # Arrange
        test_cases = [
            (1, 1),    # 1 page = 1 credit
            (5, 5),    # 5 pages = 5 credits
            (100, 100), # 100 pages = 100 credits
        ]

        for page_count, expected_credits in test_cases:
            mock_db = MagicMock()
            mock_tenant = MagicMock()
            mock_tenant.cached_balance = 500
            mock_tenant.id = uuid4()

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.with_for_update.return_value = mock_query
            mock_query.first.return_value = mock_tenant
            mock_db.query.return_value = mock_query
            mock_db.execute = MagicMock()

            mock_transaction = MagicMock()
            mock_transaction.id = uuid4()

            validator = ExtractionCreditValidator(mock_db)

            with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction) as mock_deduct:
                # Act
                transaction, cost = validator.validate_and_deduct_credits(
                    tenant_id=uuid4(),
                    page_count=page_count,
                    job_id=uuid4(),
                    document_id=uuid4(),
                    user_id=uuid4(),
                    model_provider="google",
                    model_name="gemini-2.5-flash"
                )

                # Assert
                assert cost == expected_credits
                call_kwargs = mock_deduct.call_args[1]
                assert call_kwargs['amount'] == expected_credits

    def test_tenant_not_found_raises_404(self):
        """HTTPException 404 raised when tenant is not found."""
        # Arrange
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = None  # Tenant not found
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        validator = ExtractionCreditValidator(mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=5,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="google",
                model_name="gemini-2.5-flash"
            )

        assert exc_info.value.status_code == 404
        assert "tenant_not_found" in str(exc_info.value.detail)

    def test_credit_service_insufficient_credits_error_handled(self):
        """InsufficientCreditsError from CreditService is converted to HTTP 402."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 100  # Has balance to pass initial check
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        validator = ExtractionCreditValidator(mock_db)

        # CreditService raises InsufficientCreditsError (race condition scenario)
        with patch.object(
            validator.credit_service,
            'deduct_credits',
            side_effect=InsufficientCreditsError(required=10, available=5)
        ):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                validator.validate_and_deduct_credits(
                    tenant_id=uuid4(),
                    page_count=10,
                    job_id=uuid4(),
                    document_id=uuid4(),
                    user_id=uuid4(),
                    model_provider="google",
                    model_name="gemini-2.5-flash"
                )

            assert exc_info.value.status_code == 402


class TestPessimisticLocking:
    """Tests for pessimistic locking behavior in ExtractionCreditValidator."""

    def test_lock_acquisition_success(self):
        """SELECT FOR UPDATE lock acquired successfully."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 100
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_for_update = MagicMock()

        mock_query.filter.return_value = mock_filter
        mock_filter.with_for_update.return_value = mock_for_update
        mock_for_update.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        mock_transaction = MagicMock()
        mock_transaction.id = uuid4()

        validator = ExtractionCreditValidator(mock_db)

        with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction):
            # Act
            transaction, cost = validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=5,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="google",
                model_name="gemini-2.5-flash"
            )

            # Assert - verify with_for_update was called (pessimistic lock)
            mock_filter.with_for_update.assert_called_once()
            assert transaction == mock_transaction

    def test_lock_timeout_returns_503(self):
        """Lock timeout returns 503 Service Unavailable."""
        # Arrange
        mock_db = MagicMock()
        mock_query = MagicMock()

        # Simulate lock timeout by raising OperationalError
        lock_timeout_error = OperationalError(
            "statement", {}, Exception("lock timeout")
        )
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.side_effect = lock_timeout_error
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        validator = ExtractionCreditValidator(mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=5,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="google",
                model_name="gemini-2.5-flash"
            )

        assert exc_info.value.status_code == 503
        assert "service_busy" in str(exc_info.value.detail)

    def test_concurrent_extraction_isolation(self):
        """Concurrent extractions don't interfere due to FOR UPDATE lock."""
        # This test verifies the lock is set before balance check
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 100
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_for_update = MagicMock()

        mock_query.filter.return_value = mock_filter
        mock_filter.with_for_update.return_value = mock_for_update
        mock_for_update.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        mock_transaction = MagicMock()
        mock_transaction.id = uuid4()

        validator = ExtractionCreditValidator(mock_db)

        # Track call order
        call_order = []

        original_filter = mock_query.filter
        def track_filter(*args, **kwargs):
            call_order.append('filter')
            return original_filter(*args, **kwargs)
        mock_query.filter = track_filter

        original_for_update = mock_filter.with_for_update
        def track_for_update(*args, **kwargs):
            call_order.append('with_for_update')
            return original_for_update(*args, **kwargs)
        mock_filter.with_for_update = track_for_update

        with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction):
            # Act
            validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=5,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="google",
                model_name="gemini-2.5-flash"
            )

            # Assert - with_for_update called after filter (SELECT FOR UPDATE)
            assert 'filter' in call_order
            assert 'with_for_update' in call_order
            filter_index = call_order.index('filter')
            for_update_index = call_order.index('with_for_update')
            assert filter_index < for_update_index

    def test_lock_timeout_set_before_query(self):
        """Lock timeout is set to 5 seconds before query execution."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 100
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query

        # Track execute calls for SET LOCAL lock_timeout
        execute_calls = []
        def track_execute(statement):
            execute_calls.append(str(statement))
        mock_db.execute = track_execute

        mock_transaction = MagicMock()
        mock_transaction.id = uuid4()

        validator = ExtractionCreditValidator(mock_db)

        with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction):
            # Act
            validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=5,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="google",
                model_name="gemini-2.5-flash"
            )

            # Assert - lock_timeout was set
            assert any("lock_timeout" in call for call in execute_calls)


class TestEdgeCases:
    """Tests for edge cases in ExtractionCreditValidator."""

    def test_none_page_count_defaults_to_one(self):
        """When page_count is None, it defaults to 1 credit."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 100
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        mock_transaction = MagicMock()
        mock_transaction.id = uuid4()

        validator = ExtractionCreditValidator(mock_db)

        with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction):
            # Act
            transaction, cost = validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=None,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="google",
                model_name="gemini-2.5-flash"
            )

            # Assert - defaults to 1 credit
            assert cost == 1

    def test_exact_balance_succeeds(self):
        """Extraction succeeds when balance exactly equals required credits."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 5  # Exactly 5 credits, need 5
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        mock_transaction = MagicMock()
        mock_transaction.id = uuid4()

        validator = ExtractionCreditValidator(mock_db)

        with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction):
            # Act
            transaction, cost = validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=5,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="google",
                model_name="gemini-2.5-flash"
            )

            # Assert
            assert transaction == mock_transaction
            assert cost == 5

    def test_zero_balance_fails(self):
        """Extraction fails when balance is 0."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 0  # No credits
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        validator = ExtractionCreditValidator(mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=1,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="google",
                model_name="gemini-2.5-flash"
            )

        assert exc_info.value.status_code == 402

    def test_null_cached_balance_treated_as_zero(self):
        """When cached_balance is None, it's treated as 0."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = None  # Null balance
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        validator = ExtractionCreditValidator(mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=1,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="google",
                model_name="gemini-2.5-flash"
            )

        assert exc_info.value.status_code == 402

    def test_generic_exception_returns_500(self):
        """Generic exceptions during credit deduction return 500."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 100
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        validator = ExtractionCreditValidator(mock_db)

        # CreditService raises unexpected error
        with patch.object(
            validator.credit_service,
            'deduct_credits',
            side_effect=RuntimeError("Database connection lost")
        ):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                validator.validate_and_deduct_credits(
                    tenant_id=uuid4(),
                    page_count=5,
                    job_id=uuid4(),
                    document_id=uuid4(),
                    user_id=uuid4(),
                    model_provider="google",
                    model_name="gemini-2.5-flash"
                )

            assert exc_info.value.status_code == 500
            assert "Credit deduction failed" in str(exc_info.value.detail)

    def test_metadata_passed_to_credit_service(self):
        """Job metadata is correctly passed to CreditService."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        tenant_id = uuid4()
        job_id = uuid4()
        document_id = uuid4()
        mock_tenant.cached_balance = 100
        mock_tenant.id = tenant_id

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        mock_transaction = MagicMock()
        mock_transaction.id = uuid4()

        validator = ExtractionCreditValidator(mock_db)

        with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction) as mock_deduct:
            # Act
            validator.validate_and_deduct_credits(
                tenant_id=tenant_id,
                page_count=5,
                job_id=job_id,
                document_id=document_id,
                user_id=uuid4(),
                model_provider="google",
                model_name="gemini-2.5-flash"
            )

            # Assert - verify metadata was passed
            call_kwargs = mock_deduct.call_args[1]
            metadata = call_kwargs['metadata']
            assert metadata['job_id'] == str(job_id)
            assert metadata['document_id'] == str(document_id)
            assert metadata['page_count'] == 5
            assert metadata['model_provider'] == "google"
            assert metadata['model_name'] == "gemini-2.5-flash"


class TestLlamaExtractPricing:
    """Tests for LlamaExtract mode-based credit calculation."""

    def test_llamaextract_standard_mode_1_credit_per_page(self):
        """LlamaExtract standard mode charges 1 credit per page."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 100
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        mock_transaction = MagicMock()
        mock_transaction.id = uuid4()

        validator = ExtractionCreditValidator(mock_db)

        with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction):
            # Act - 5 pages with standard mode = 5 credits
            transaction, cost = validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=5,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="llamaextract",
                model_name="llamaextract",
                llamaextract_mode="standard"
            )

            # Assert
            assert cost == 5  # 5 pages * 1 credit/page

    def test_llamaextract_premium_mode_2_credits_per_page(self):
        """LlamaExtract premium mode charges 2 credits per page."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 100
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        mock_transaction = MagicMock()
        mock_transaction.id = uuid4()

        validator = ExtractionCreditValidator(mock_db)

        with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction):
            # Act - 5 pages with premium mode = 10 credits
            transaction, cost = validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=5,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="llamaextract",
                model_name="llamaextract",
                llamaextract_mode="premium"
            )

            # Assert
            assert cost == 10  # 5 pages * 2 credits/page

    def test_llamaextract_defaults_to_standard_mode(self):
        """LlamaExtract defaults to standard mode when mode not specified."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 100
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        mock_transaction = MagicMock()
        mock_transaction.id = uuid4()

        validator = ExtractionCreditValidator(mock_db)

        with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction):
            # Act - 5 pages without mode = defaults to standard = 5 credits
            transaction, cost = validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=5,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="llamaextract",
                model_name="llamaextract"
            )

            # Assert - defaults to standard mode (1 credit/page)
            assert cost == 5

    def test_llamaextract_is_valid_provider(self):
        """LlamaExtract is a valid model provider."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 100
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        mock_transaction = MagicMock()
        mock_transaction.id = uuid4()

        validator = ExtractionCreditValidator(mock_db)

        with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction):
            # Act - should not raise for llamaextract provider
            transaction, cost = validator.validate_and_deduct_credits(
                tenant_id=uuid4(),
                page_count=1,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                model_provider="llamaextract",
                model_name="llamaextract"
            )

            # Assert
            assert transaction == mock_transaction

    def test_llamaextract_metadata_includes_mode(self):
        """LlamaExtract metadata includes the mode used."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        tenant_id = uuid4()
        job_id = uuid4()
        document_id = uuid4()
        mock_tenant.cached_balance = 100
        mock_tenant.id = tenant_id

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        mock_transaction = MagicMock()
        mock_transaction.id = uuid4()

        validator = ExtractionCreditValidator(mock_db)

        with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction) as mock_deduct:
            # Act
            validator.validate_and_deduct_credits(
                tenant_id=tenant_id,
                page_count=5,
                job_id=job_id,
                document_id=document_id,
                user_id=uuid4(),
                model_provider="llamaextract",
                model_name="llamaextract",
                llamaextract_mode="premium"
            )

            # Assert - verify metadata includes llamaextract_mode
            call_kwargs = mock_deduct.call_args[1]
            metadata = call_kwargs['metadata']
            assert metadata['llamaextract_mode'] == "premium"
            assert metadata['credits_per_page'] == 2


class TestPageBasedPricing:
    """Tests for page-based pricing (e.g., LlamaParse document converters)."""

    def test_page_based_credits_calculated_from_pricing_table(self):
        """Page-based credits use credit_rate_per_page from ModelPricing."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 100
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        mock_transaction = MagicMock()
        mock_transaction.id = uuid4()

        validator = ExtractionCreditValidator(mock_db)

        # Mock pricing lookup to return 2 credits per page
        pricing_snapshot = {
            "converter": "llamaparse",
            "pricing_type": "page",
            "pricing_id": str(uuid4()),
            "page_count": 5,
            "credit_rate_per_page": 2.0,
            "credits_calculated": 10,
        }

        with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction):
            with patch('app.services.extraction_service.PricingService') as MockPricingService:
                mock_pricing = MagicMock()
                mock_pricing.calculate_page_based_credits.return_value = (10, pricing_snapshot)
                MockPricingService.return_value = mock_pricing

                # Act
                transaction, cost, snapshot = validator.validate_and_deduct_page_based_credits(
                    tenant_id=uuid4(),
                    page_count=5,
                    job_id=uuid4(),
                    document_id=uuid4(),
                    user_id=uuid4(),
                    converter_name="llamaparse"
                )

                # Assert - 5 pages * 2 credits/page = 10 credits
                assert cost == 10
                assert snapshot["credit_rate_per_page"] == 2.0
                mock_pricing.calculate_page_based_credits.assert_called_once_with(
                    converter_name="llamaparse",
                    page_count=5,
                )

    def test_page_based_negative_page_count_rejected(self):
        """Negative page count raises HTTPException 400."""
        # Arrange
        mock_db = MagicMock()
        validator = ExtractionCreditValidator(mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_and_deduct_page_based_credits(
                tenant_id=uuid4(),
                page_count=-1,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                converter_name="llamaparse"
            )

        assert exc_info.value.status_code == 400
        assert "page_count" in str(exc_info.value.detail)

    def test_page_based_exceeds_maximum_rejected(self):
        """Page count > 10000 raises HTTPException 400."""
        # Arrange
        mock_db = MagicMock()
        validator = ExtractionCreditValidator(mock_db)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_and_deduct_page_based_credits(
                tenant_id=uuid4(),
                page_count=10001,
                job_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                converter_name="llamaparse"
            )

        assert exc_info.value.status_code == 400
        assert "exceeds maximum" in str(exc_info.value.detail)

    def test_page_based_converter_not_found(self):
        """Unknown converter raises HTTPException 400."""
        # Arrange
        mock_db = MagicMock()
        validator = ExtractionCreditValidator(mock_db)

        with patch('app.services.extraction_service.PricingService') as MockPricingService:
            mock_pricing = MagicMock()
            mock_pricing.calculate_page_based_credits.side_effect = ValueError(
                "No pricing configured for document converter: unknown_converter"
            )
            MockPricingService.return_value = mock_pricing

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                validator.validate_and_deduct_page_based_credits(
                    tenant_id=uuid4(),
                    page_count=5,
                    job_id=uuid4(),
                    document_id=uuid4(),
                    user_id=uuid4(),
                    converter_name="unknown_converter"
                )

            assert exc_info.value.status_code == 400
            assert "converter_name" in str(exc_info.value.detail)

    def test_page_based_insufficient_credits(self):
        """Insufficient credits raises HTTPException 402."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 5  # Only 5 credits, need 10
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        validator = ExtractionCreditValidator(mock_db)

        pricing_snapshot = {
            "converter": "llamaparse",
            "pricing_type": "page",
            "pricing_id": str(uuid4()),
            "page_count": 5,
            "credit_rate_per_page": 2.0,
            "credits_calculated": 10,
        }

        with patch('app.services.extraction_service.PricingService') as MockPricingService:
            mock_pricing = MagicMock()
            mock_pricing.calculate_page_based_credits.return_value = (10, pricing_snapshot)
            MockPricingService.return_value = mock_pricing

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                validator.validate_and_deduct_page_based_credits(
                    tenant_id=uuid4(),
                    page_count=5,
                    job_id=uuid4(),
                    document_id=uuid4(),
                    user_id=uuid4(),
                    converter_name="llamaparse"
                )

            assert exc_info.value.status_code == 402

    def test_page_based_metadata_includes_pricing_info(self):
        """Metadata includes pricing type and rate information."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 100
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        mock_transaction = MagicMock()
        mock_transaction.id = uuid4()

        validator = ExtractionCreditValidator(mock_db)

        pricing_id = str(uuid4())
        pricing_snapshot = {
            "converter": "llamaparse",
            "pricing_type": "page",
            "pricing_id": pricing_id,
            "page_count": 5,
            "credit_rate_per_page": 2.0,
            "credits_calculated": 10,
        }

        with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction) as mock_deduct:
            with patch('app.services.extraction_service.PricingService') as MockPricingService:
                mock_pricing = MagicMock()
                mock_pricing.calculate_page_based_credits.return_value = (10, pricing_snapshot)
                MockPricingService.return_value = mock_pricing

                # Act
                validator.validate_and_deduct_page_based_credits(
                    tenant_id=uuid4(),
                    page_count=5,
                    job_id=uuid4(),
                    document_id=uuid4(),
                    user_id=uuid4(),
                    converter_name="llamaparse"
                )

                # Assert
                call_kwargs = mock_deduct.call_args[1]
                metadata = call_kwargs['metadata']
                assert metadata['pricing_type'] == "page"
                assert metadata['converter'] == "llamaparse"
                assert metadata['credit_rate_per_page'] == 2.0
                assert metadata['pricing_id'] == pricing_id

    def test_page_based_tenant_not_found(self):
        """HTTPException 404 raised when tenant not found."""
        # Arrange
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = None  # Tenant not found
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        validator = ExtractionCreditValidator(mock_db)

        pricing_snapshot = {
            "converter": "llamaparse",
            "pricing_type": "page",
            "pricing_id": str(uuid4()),
            "page_count": 5,
            "credit_rate_per_page": 2.0,
            "credits_calculated": 10,
        }

        with patch('app.services.extraction_service.PricingService') as MockPricingService:
            mock_pricing = MagicMock()
            mock_pricing.calculate_page_based_credits.return_value = (10, pricing_snapshot)
            MockPricingService.return_value = mock_pricing

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                validator.validate_and_deduct_page_based_credits(
                    tenant_id=uuid4(),
                    page_count=5,
                    job_id=uuid4(),
                    document_id=uuid4(),
                    user_id=uuid4(),
                    converter_name="llamaparse"
                )

            assert exc_info.value.status_code == 404

    def test_page_based_returns_pricing_snapshot(self):
        """Method returns pricing snapshot for audit trail."""
        # Arrange
        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.cached_balance = 100
        mock_tenant.id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query
        mock_query.first.return_value = mock_tenant
        mock_db.query.return_value = mock_query
        mock_db.execute = MagicMock()

        mock_transaction = MagicMock()
        mock_transaction.id = uuid4()

        validator = ExtractionCreditValidator(mock_db)

        pricing_snapshot = {
            "converter": "llamaparse",
            "pricing_type": "page",
            "pricing_id": str(uuid4()),
            "page_count": 5,
            "credit_rate_per_page": 2.0,
            "credits_calculated": 10,
            "calculated_at": "2025-12-23T10:00:00+00:00",
        }

        with patch.object(validator.credit_service, 'deduct_credits', return_value=mock_transaction):
            with patch('app.services.extraction_service.PricingService') as MockPricingService:
                mock_pricing = MagicMock()
                mock_pricing.calculate_page_based_credits.return_value = (10, pricing_snapshot)
                MockPricingService.return_value = mock_pricing

                # Act
                transaction, cost, returned_snapshot = validator.validate_and_deduct_page_based_credits(
                    tenant_id=uuid4(),
                    page_count=5,
                    job_id=uuid4(),
                    document_id=uuid4(),
                    user_id=uuid4(),
                    converter_name="llamaparse"
                )

                # Assert
                assert returned_snapshot == pricing_snapshot
                assert returned_snapshot["credits_calculated"] == 10
                assert returned_snapshot["calculated_at"] is not None
