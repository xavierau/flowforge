"""Pydantic schemas for credit operations."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class CreditBalanceResponse(BaseModel):
    """Response model for credit balance."""

    tenant_id: UUID
    balance: int = Field(..., ge=0, description="Current credit balance")
    updated_at: datetime

    class Config:
        from_attributes = True


class CreditTransactionResponse(BaseModel):
    """Response model for a single transaction."""

    id: UUID
    transaction_type: str
    amount: int  # Signed: positive=credit, negative=debit
    reference_type: Optional[str] = None
    reference_id: Optional[UUID] = None
    description: str
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class CreditTransactionListResponse(BaseModel):
    """Response model for transaction list."""

    transactions: List[CreditTransactionResponse]
    total: int
    limit: int
    offset: int


class CreditTopUpRequest(BaseModel):
    """Request model for credit top-up."""

    credits: int = Field(..., gt=0, description="Number of credits to purchase")
    amount_usd: Decimal = Field(..., gt=0, description="Payment amount in USD")
    payment_intent_id: Optional[str] = Field(None, description="Stripe payment intent ID")

    @field_validator("credits")
    @classmethod
    def validate_credits(cls, v):
        if v <= 0 or v > 100000:
            raise ValueError("Credits must be between 1 and 100,000")
        return v


class CreditTopUpResponse(BaseModel):
    """Response model for credit top-up."""

    transaction_id: UUID
    credits_added: int
    new_balance: int
    created_at: datetime

    class Config:
        from_attributes = True


class CreditAdjustmentRequest(BaseModel):
    """Request model for manual credit adjustment."""

    amount: int = Field(..., description="Amount to adjust (positive=add, negative=deduct)")
    reason: str = Field(..., min_length=10, max_length=500, description="Reason for adjustment")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v == 0:
            raise ValueError("Adjustment amount cannot be zero")
        if abs(v) > 100000:
            raise ValueError("Adjustment amount cannot exceed 100,000 credits")
        return v
