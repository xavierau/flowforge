"""Credit management endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.credit_transaction import CreditTransaction
from app.schemas.credits import (
    CreditBalanceResponse,
    CreditTopUpRequest,
    CreditTopUpResponse,
    CreditAdjustmentRequest,
    CreditTransactionListResponse,
    CreditTransactionResponse,
)
from app.services.credit_service import CreditService
from app.dependencies.auth import require_permission, get_current_active_user
from app.exceptions.credits import CreditOperationError, InsufficientCreditsError

router = APIRouter(prefix="/api/v1/credits")


@router.get("/balance", response_model=CreditBalanceResponse)
async def get_credit_balance(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CreditBalanceResponse:
    """
    Get current credit balance for authenticated user's tenant.

    Self-service endpoint (no permission required).
    Supports JWT authentication only (not API tokens).

    Returns:
        Current credit balance
    """
    credit_service = CreditService(db)
    balance = credit_service.calculate_balance(current_user.tenant_id)

    return CreditBalanceResponse(
        tenant_id=current_user.tenant_id,
        balance=balance,
        updated_at=datetime.utcnow(),
    )


@router.get("/transactions", response_model=CreditTransactionListResponse)
async def get_transaction_history(
    transaction_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(50, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CreditTransactionListResponse:
    """
    Get transaction history for authenticated user's tenant.

    Self-service endpoint (no permission required).
    Supports JWT authentication only.

    Args:
        transaction_type: Optional filter by transaction type
        limit: Number of results per page
        offset: Pagination offset

    Returns:
        Paginated list of transactions
    """
    credit_service = CreditService(db)
    transactions, total = credit_service.get_transaction_history(
        tenant_id=current_user.tenant_id,
        limit=limit,
        offset=offset,
        transaction_type=transaction_type,
    )

    return CreditTransactionListResponse(
        transactions=[
            CreditTransactionResponse(
                id=tx.id,
                transaction_type=tx.transaction_type,
                amount=tx.amount,
                reference_type=tx.reference_type,
                reference_id=tx.reference_id,
                description=tx.description,
                created_at=tx.created_at,
                metadata=tx.transaction_metadata,
            )
            for tx in transactions
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/topup", response_model=CreditTopUpResponse, status_code=201)
async def topup_credits(
    request: CreditTopUpRequest,
    current_user: User = Depends(require_permission("tenant:billing")),
    db: Session = Depends(get_db),
) -> CreditTopUpResponse:
    """
    Top up credits for tenant (payment processing).

    JWT authentication only (too sensitive for API tokens).

    Required Permission: tenant:billing

    This endpoint integrates with Stripe payment processing.
    In production, this would:
    1. Create Stripe PaymentIntent
    2. Process payment
    3. Add credits on successful payment

    Args:
        request: Credit top-up request with amount and payment info

    Returns:
        Top-up transaction details

    Raises:
        402: Payment required (payment failed)
        500: Payment processing error
    """
    credit_service = CreditService(db)

    try:
        # FIX: Idempotency check - prevent double-crediting for duplicate payment_intent_id
        if request.payment_intent_id:
            existing_transaction = (
                db.query(CreditTransaction)
                .filter(
                    CreditTransaction.stripe_payment_intent_id == request.payment_intent_id,
                    CreditTransaction.tenant_id == current_user.tenant_id
                )
                .first()
            )

            if existing_transaction:
                # Payment already processed - return existing transaction
                # This handles webhook retries and duplicate submissions
                new_balance = credit_service.calculate_balance(current_user.tenant_id)

                return CreditTopUpResponse(
                    transaction_id=existing_transaction.id,
                    credits_added=existing_transaction.amount,
                    new_balance=new_balance,
                    created_at=existing_transaction.created_at,
                )

        # TODO: Integrate with Stripe payment processing
        # For now, create transaction directly (DEMO ONLY)
        transaction = credit_service.add_credits(
            tenant_id=current_user.tenant_id,
            amount=request.credits,
            transaction_type="topup",
            description=f"Credit purchase - {request.credits} credits",
            created_by_user_id=current_user.id,
            stripe_payment_intent_id=request.payment_intent_id,
            metadata={"amount_usd": str(request.amount_usd)},
        )

        db.commit()

        new_balance = credit_service.calculate_balance(current_user.tenant_id)

        return CreditTopUpResponse(
            transaction_id=transaction.id,
            credits_added=request.credits,
            new_balance=new_balance,
            created_at=transaction.created_at,
        )

    except CreditOperationError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/adjust", response_model=CreditTransactionResponse, status_code=201)
async def adjust_credits(
    request: CreditAdjustmentRequest,
    current_user: User = Depends(require_permission("tenant:manage")),
    db: Session = Depends(get_db),
) -> CreditTransactionResponse:
    """
    Manually adjust credits (admin operation).

    JWT authentication only (too sensitive for API tokens).

    Required Permission: tenant:manage

    Allows admins to add or remove credits for troubleshooting,
    refunds, or promotional purposes.

    Args:
        request: Credit adjustment request with amount and reason

    Returns:
        Created transaction record
    """
    credit_service = CreditService(db)

    try:
        if request.amount > 0:
            # Add credits
            transaction = credit_service.add_credits(
                tenant_id=current_user.tenant_id,
                amount=request.amount,
                transaction_type="admin_adjustment",
                description=request.reason,
                created_by_user_id=current_user.id,
                metadata={"admin_user": str(current_user.id)},
            )
        else:
            # Deduct credits (use absolute value)
            # Admin adjustments can go negative (for chargebacks, fraud, etc.)
            transaction = credit_service.deduct_credits(
                tenant_id=current_user.tenant_id,
                amount=abs(request.amount),
                reference_type="manual",
                reference_id=current_user.id,
                description=request.reason,
                created_by_user_id=current_user.id,
                metadata={"admin_user": str(current_user.id)},
                allow_negative=True,  # Admin can force negative balance
            )

        db.commit()

        return CreditTransactionResponse(
            id=transaction.id,
            transaction_type=transaction.transaction_type,
            amount=transaction.amount,
            reference_type=transaction.reference_type,
            reference_id=transaction.reference_id,
            description=transaction.description,
            created_at=transaction.created_at,
            metadata=transaction.transaction_metadata,
        )

    except (ValueError, CreditOperationError) as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except InsufficientCreditsError as e:
        db.rollback()
        raise HTTPException(
            status_code=402,
            detail={
                "error": "insufficient_credits",
                "message": str(e),
                "required_credits": e.required,
                "available_credits": e.available,
            }
        )
