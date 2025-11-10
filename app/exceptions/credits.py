"""Custom exceptions for credit operations."""


class CreditError(Exception):
    """Base exception for credit-related errors."""
    pass


class InsufficientCreditsError(CreditError):
    """Raised when tenant has insufficient credits for an operation."""

    def __init__(self, required: int, available: int):
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient credits. Required: {required}, Available: {available}"
        )


class CreditOperationError(CreditError):
    """Raised when a credit operation fails (database, validation, etc)."""
    pass


class DuplicateCreditDeductionError(CreditError):
    """Raised when attempting to deduct credits for a job that was already charged."""
    pass
