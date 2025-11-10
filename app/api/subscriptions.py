"""Subscription management API endpoints (Stub Implementation)."""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import User, Tenant
from app.dependencies.auth import get_current_active_user

router = APIRouter()


@router.get(
    "/subscriptions/current",
    summary="Get current subscription",
    description="Get current tenant's subscription details (stub implementation)"
)
async def get_current_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current subscription (stub implementation).

    Returns mock subscription data based on tenant.
    """
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()

    now = datetime.utcnow()
    billing_period_start = now.replace(day=1)

    # Calculate credits used this month from credit_transactions
    from app.models.credit_transaction import CreditTransaction
    from app.models.enums import CreditTransactionType, ReferenceType
    from sqlalchemy import and_

    # FIX: Changed from "usage" to CreditTransactionType.DEDUCTION.value
    # Also filter by reference_type to only count extraction job credits
    credits_used_result = (
        db.query(func.sum(CreditTransaction.amount))
        .filter(
            and_(
                CreditTransaction.tenant_id == current_user.tenant_id,
                CreditTransaction.transaction_type == CreditTransactionType.DEDUCTION.value,
                CreditTransaction.reference_type == ReferenceType.EXTRACTION_JOB.value,
                CreditTransaction.created_at >= billing_period_start
            )
        )
        .scalar()
    )

    # Credits used are negative amounts, so we negate them for display
    credits_used = abs(credits_used_result) if credits_used_result else 0

    return {
        "plan": tenant.subscription_plan if tenant else "free",
        "status": "active",
        "credits_balance": tenant.cached_balance if tenant else 0,
        "credits_used": credits_used,
        "balance_last_updated": tenant.balance_last_updated.isoformat() if tenant and tenant.balance_last_updated else now.isoformat(),
        "billing_period_start": billing_period_start.isoformat(),
        "billing_period_end": (billing_period_start + timedelta(days=30)).isoformat(),
        "cancel_at_period_end": False,
        "features": {
            "max_users": 10 if tenant and tenant.subscription_plan == "pro" else 2,
            "api_access": True,
            "priority_support": tenant.subscription_plan == "pro" if tenant else False
        }
    }


@router.get(
    "/subscriptions/plans",
    summary="List available plans",
    description="Get all available subscription plans"
)
async def list_subscription_plans():
    """
    List subscription plans.

    Returns hardcoded plan list.
    """
    return [
        {
            "plan": "free",
            "name": "Free",
            "description": "For individuals getting started",
            "price_monthly": None,
            "features": {
                "max_users": 2,
                "monthly_credits": 100,
                "api_access": False,
                "priority_support": False,
                "custom_integrations": False
            }
        },
        {
            "plan": "starter",
            "name": "Starter",
            "description": "For small teams",
            "price_monthly": 29.00,
            "features": {
                "max_users": 5,
                "monthly_credits": 1000,
                "api_access": True,
                "priority_support": False,
                "custom_integrations": False
            }
        },
        {
            "plan": "pro",
            "name": "Professional",
            "description": "For growing teams",
            "price_monthly": 99.00,
            "features": {
                "max_users": 10,
                "monthly_credits": 5000,
                "api_access": True,
                "priority_support": True,
                "custom_integrations": False
            }
        },
        {
            "plan": "enterprise",
            "name": "Enterprise",
            "description": "For large organizations",
            "price_monthly": 499.00,
            "features": {
                "max_users": None,
                "monthly_credits": None,
                "api_access": True,
                "priority_support": True,
                "custom_integrations": True
            }
        }
    ]


@router.get(
    "/subscriptions/usage",
    summary="Get billing period usage",
    description="Get current billing period usage statistics (stub implementation)"
)
async def get_subscription_usage(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get usage statistics (stub implementation).

    Returns mock usage data.
    """
    now = datetime.utcnow()
    return {
        "documents_processed": 0,
        "api_calls_made": 0,
        "credits_used": 0,
        "period_start": now.replace(day=1).isoformat(),
        "period_end": (now.replace(day=1) + timedelta(days=30)).isoformat()
    }


@router.post(
    "/subscriptions/change-plan",
    summary="Change subscription plan",
    description="Upgrade or downgrade subscription (stub implementation)"
)
async def change_subscription_plan(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change plan (stub implementation).

    Returns success message. Full implementation pending.
    """
    return {"message": "Plan change feature coming soon"}
