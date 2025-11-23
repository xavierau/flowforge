"""
Standardized error response schemas.

This module provides consistent error response formats across all API endpoints,
ensuring clients can reliably parse and handle errors programmatically.

SOLID Principles:
    - SRP: Single responsibility - error response formatting
    - OCP: Open for extension (add new error codes without changing existing)
    - LSP: All error details are substitutable (same base structure)

Usage:
    from app.schemas.error import ErrorDetail, ErrorCode

    # Return standardized error
    raise HTTPException(
        status_code=404,
        detail=ErrorDetail(
            error_code=ErrorCode.TENANT_NOT_FOUND,
            message="Tenant not found",
            details={"tenant_id": str(tenant_id)}
        ).dict()
    )
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """
    Standardized error codes for API responses.

    These codes provide machine-readable error identification,
    allowing clients to handle specific errors programmatically.
    """
    # Resource not found errors (HTTP 404)
    TENANT_NOT_FOUND = "tenant_not_found"
    DOCUMENT_NOT_FOUND = "document_not_found"
    JOB_NOT_FOUND = "job_not_found"
    SCHEMA_NOT_FOUND = "schema_not_found"
    USER_NOT_FOUND = "user_not_found"

    # Credit-related errors (HTTP 402)
    INSUFFICIENT_CREDITS = "insufficient_credits"

    # Validation errors (HTTP 400)
    INVALID_INPUT = "invalid_input"
    INVALID_SCHEMA = "invalid_schema"
    INVALID_FILE_TYPE = "invalid_file_type"
    INVALID_FILE_SIZE = "invalid_file_size"
    INVALID_PROCESSING_MODE = "invalid_processing_mode"
    INVALID_MODEL_PROVIDER = "invalid_model_provider"
    INVALID_PAGE_COUNT = "invalid_page_count"

    # State errors (HTTP 400)
    DOCUMENT_NOT_READY = "document_not_ready"
    JOB_NOT_COMPLETED = "job_not_completed"

    # Service errors (HTTP 503)
    SERVICE_BUSY = "service_busy"

    # Server errors (HTTP 500)
    CREDIT_DEDUCTION_FAILED = "credit_deduction_failed"
    EXTRACTION_FAILED = "extraction_failed"
    STORAGE_ERROR = "storage_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorDetail(BaseModel):
    """
    Standardized error response format.

    All API endpoints MUST return errors in this format for consistency.

    Attributes:
        error_code: Machine-readable error code (from ErrorCode enum)
        message: Human-readable error message
        details: Optional additional context (structured data)

    Example:
        {
            "error_code": "insufficient_credits",
            "message": "Insufficient credits. Required: 5, Available: 3",
            "details": {
                "required_credits": 5,
                "available_credits": 3,
                "credits_needed": 2
            }
        }
    """
    error_code: ErrorCode = Field(
        ...,
        description="Machine-readable error code for programmatic handling"
    )
    message: str = Field(
        ...,
        description="Human-readable error message for display",
        min_length=1,
        max_length=500
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional structured data providing additional error context"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True  # Serialize enums as strings
        json_schema_extra = {
            "example": {
                "error_code": "insufficient_credits",
                "message": "Insufficient credits to process document. Required: 5, Available: 3",
                "details": {
                    "required_credits": 5,
                    "available_credits": 3,
                    "credits_needed": 2
                }
            }
        }


# Convenience factory functions for common errors

def insufficient_credits_error(
    required: int,
    available: int
) -> Dict[str, Any]:
    """
    Create standardized insufficient credits error.

    Args:
        required: Number of credits required
        available: Number of credits available

    Returns:
        Error detail dict ready for HTTPException
    """
    return ErrorDetail(
        error_code=ErrorCode.INSUFFICIENT_CREDITS,
        message=f"Insufficient credits to process document. Required: {required}, Available: {available}",
        details={
            "required_credits": required,
            "available_credits": available,
            "credits_needed": required - available,
        }
    ).dict()


def tenant_not_found_error(tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create standardized tenant not found error.

    Args:
        tenant_id: Optional tenant ID for details

    Returns:
        Error detail dict ready for HTTPException
    """
    return ErrorDetail(
        error_code=ErrorCode.TENANT_NOT_FOUND,
        message="Tenant not found",
        details={"tenant_id": tenant_id} if tenant_id else None
    ).dict()


def document_not_found_error(document_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create standardized document not found error.

    Args:
        document_id: Optional document ID for details

    Returns:
        Error detail dict ready for HTTPException
    """
    return ErrorDetail(
        error_code=ErrorCode.DOCUMENT_NOT_FOUND,
        message="Document not found",
        details={"document_id": document_id} if document_id else None
    ).dict()


def job_not_found_error(job_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create standardized job not found error.

    Args:
        job_id: Optional job ID for details

    Returns:
        Error detail dict ready for HTTPException
    """
    return ErrorDetail(
        error_code=ErrorCode.JOB_NOT_FOUND,
        message="Job not found",
        details={"job_id": job_id} if job_id else None
    ).dict()


def service_busy_error(retry_after: int = 3) -> Dict[str, Any]:
    """
    Create standardized service busy error.

    Args:
        retry_after: Seconds to wait before retrying

    Returns:
        Error detail dict ready for HTTPException
    """
    return ErrorDetail(
        error_code=ErrorCode.SERVICE_BUSY,
        message="Service is currently busy. Please retry in a few seconds.",
        details={"retry_after": retry_after}
    ).dict()


def invalid_input_error(
    field: str,
    reason: str,
    value: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Create standardized invalid input error.

    Args:
        field: Name of invalid field
        reason: Why the input is invalid
        value: Optional invalid value (be careful not to log sensitive data)

    Returns:
        Error detail dict ready for HTTPException
    """
    details = {"field": field, "reason": reason}
    if value is not None:
        details["value"] = value

    return ErrorDetail(
        error_code=ErrorCode.INVALID_INPUT,
        message=f"Invalid input for field '{field}': {reason}",
        details=details
    ).dict()
