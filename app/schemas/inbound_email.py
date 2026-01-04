"""Inbound email-related Pydantic schemas for request/response validation."""

import re
import urllib.parse
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

# Pattern for validating email addresses and domain patterns
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
DOMAIN_PATTERN = re.compile(r'^\*@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def validate_sender_pattern(pattern: str) -> bool:
    """
    Validate a sender pattern is either a full email or domain pattern.

    Args:
        pattern: Email address (user@domain.com) or domain pattern (*@domain.com)

    Returns:
        True if valid, False otherwise
    """
    return bool(EMAIL_PATTERN.match(pattern) or DOMAIN_PATTERN.match(pattern))


def _validate_sender_patterns(v: Optional[List[str]]) -> Optional[List[str]]:
    """
    Shared validator for allowed_senders field.

    Validates each pattern is either a full email or domain pattern (*@domain.com),
    normalizes to lowercase, and removes empty entries.

    Args:
        v: List of sender patterns to validate

    Returns:
        Normalized list of sender patterns, or None if empty

    Raises:
        ValueError: If any pattern is invalid
    """
    if v is None:
        return None

    normalized = [pattern.strip().lower() for pattern in v if pattern and pattern.strip()]
    if not normalized:
        return None

    invalid_patterns = [p for p in normalized if not validate_sender_pattern(p)]
    if invalid_patterns:
        raise ValueError(
            f"Invalid sender patterns: {invalid_patterns}. "
            "Use email@domain.com or *@domain.com format."
        )

    return normalized


def _validate_callback_url_ssrf(v: Optional[str]) -> Optional[str]:
    """
    Validate callback_url to prevent SSRF attacks.

    Blocks internal/private network addresses and requires http(s) scheme.

    Args:
        v: URL to validate

    Returns:
        Validated URL, or None if empty

    Raises:
        ValueError: If URL is invalid or points to internal network
    """
    if v is None:
        return None

    v = v.strip()
    if not v:
        return None

    # Require https:// or http:// scheme
    if not v.startswith(('https://', 'http://')):
        raise ValueError("callback_url must start with https:// or http://")

    # Block internal/private network addresses
    parsed = urllib.parse.urlparse(v)
    hostname = parsed.hostname or ""

    blocked_patterns = [
        'localhost', '127.0.0.1', '10.', '172.16.', '172.17.', '172.18.',
        '172.19.', '172.20.', '172.21.', '172.22.', '172.23.', '172.24.',
        '172.25.', '172.26.', '172.27.', '172.28.', '172.29.', '172.30.',
        '172.31.', '192.168.', '0.0.0.0', '169.254.', '::1', 'fe80::'
    ]
    hostname_lower = hostname.lower()
    if any(hostname_lower.startswith(p) or hostname_lower == p.rstrip('.') for p in blocked_patterns):
        raise ValueError("callback_url cannot point to internal network addresses")

    return v


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================


class InboundEmailAddressCreate(BaseModel):
    """Request schema for creating a new inbound email address."""

    name: str = Field(
        ...,
        description="User-friendly name for this email address",
        min_length=1,
        max_length=255,
        json_schema_extra={"example": "Invoice Processing"}
    )
    description: Optional[str] = Field(
        None,
        description="Optional description of this email address purpose",
        max_length=1000,
        json_schema_extra={"example": "Receives invoices from vendors for automatic extraction"}
    )
    allowed_senders: Optional[List[str]] = Field(
        default=None,
        description="Optional list of allowed sender patterns (email or *@domain.com)",
        json_schema_extra={"example": ["accounting@vendor.com", "*@trusted-partner.com"]}
    )

    # Job configuration
    schema_definition_id: Optional[UUID] = Field(
        None,
        description="ID of saved schema definition to use for extraction",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"}
    )
    extraction_schema: Optional[dict[str, Any]] = Field(
        None,
        description="Custom JSON schema for extraction (used if schema_definition_id not provided)",
        json_schema_extra={
            "example": {
                "type": "object",
                "properties": {
                    "vendor_name": {"type": "string"},
                    "invoice_number": {"type": "string"},
                    "total_amount": {"type": "number"}
                },
                "required": ["vendor_name", "total_amount"]
            }
        }
    )
    custom_prompt: Optional[str] = Field(
        None,
        description="Custom extraction instructions",
        max_length=5000,
        json_schema_extra={"example": "Extract invoice details. Pay attention to line items."}
    )
    model_provider: str = Field(
        default="google",
        description="VLLM provider for extraction",
        json_schema_extra={"example": "google"}
    )
    model_name: str = Field(
        default="gemini-2.5-flash",
        description="Model name for extraction",
        json_schema_extra={"example": "gemini-2.5-flash"}
    )
    split_mode: str = Field(
        default="batch",
        description="Split mode: 'per_page', 'batch', or 'auto'",
        json_schema_extra={"example": "batch"}
    )
    extraction_mode: str = Field(
        default="vllm",
        description="Extraction mode: 'vllm' or 'markdown'",
        json_schema_extra={"example": "vllm"}
    )
    markdown_converter: Optional[str] = Field(
        None,
        description="Markdown converter (only for extraction_mode='markdown')",
        json_schema_extra={"example": "gemini_vision"}
    )
    markdown_format: Optional[str] = Field(
        None,
        description="Markdown format style (only for extraction_mode='markdown')",
        json_schema_extra={"example": "table_heavy"}
    )
    callback_url: Optional[str] = Field(
        default=None,
        description="Optional webhook URL to POST results to when job completes",
        max_length=1024,
        json_schema_extra={"example": "https://example.com/webhooks/email-extraction"}
    )
    llamaextract_mode: Optional[str] = Field(
        default=None,
        description="LlamaExtract extraction mode: 'standard' or 'premium'",
        json_schema_extra={"example": "standard"}
    )
    llamaextract_target: Optional[str] = Field(
        default=None,
        description="LlamaExtract extraction target: 'per_doc' or 'per_page'",
        json_schema_extra={"example": "per_doc"}
    )

    @field_validator("allowed_senders")
    @classmethod
    def validate_allowed_senders(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate and normalize allowed sender patterns."""
        return _validate_sender_patterns(v)

    @field_validator("callback_url")
    @classmethod
    def validate_callback_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate callback_url to prevent SSRF attacks."""
        return _validate_callback_url_ssrf(v)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Invoice Processing",
                "description": "Receives invoices from vendors",
                "allowed_senders": ["*@vendor.com", "accounting@partner.com"],
                "model_provider": "google",
                "model_name": "gemini-2.5-flash",
                "split_mode": "batch",
                "extraction_mode": "vllm"
            }
        }
    )


class InboundEmailAddressUpdate(BaseModel):
    """Request schema for updating an inbound email address."""

    name: Optional[str] = Field(
        None,
        description="Updated name for this email address",
        min_length=1,
        max_length=255,
        json_schema_extra={"example": "Updated Invoice Processing"}
    )
    description: Optional[str] = Field(
        None,
        description="Updated description",
        max_length=1000,
        json_schema_extra={"example": "Updated description for email processing"}
    )
    is_active: Optional[bool] = Field(
        None,
        description="Whether this email address is active",
        json_schema_extra={"example": True}
    )
    allowed_senders: Optional[List[str]] = Field(
        default=None,
        description="Updated list of allowed sender patterns",
        json_schema_extra={"example": ["*@new-vendor.com"]}
    )

    # Job configuration
    schema_definition_id: Optional[UUID] = Field(
        None,
        description="Updated schema definition ID",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"}
    )
    extraction_schema: Optional[dict[str, Any]] = Field(
        None,
        description="Updated custom JSON schema for extraction"
    )
    custom_prompt: Optional[str] = Field(
        None,
        description="Updated custom extraction instructions",
        max_length=5000
    )
    model_provider: Optional[str] = Field(
        None,
        description="Updated VLLM provider",
        json_schema_extra={"example": "openai"}
    )
    model_name: Optional[str] = Field(
        None,
        description="Updated model name",
        json_schema_extra={"example": "gpt-4o"}
    )
    split_mode: Optional[str] = Field(
        None,
        description="Updated split mode",
        json_schema_extra={"example": "per_page"}
    )
    extraction_mode: Optional[str] = Field(
        None,
        description="Updated extraction mode",
        json_schema_extra={"example": "markdown"}
    )
    markdown_converter: Optional[str] = Field(
        None,
        description="Updated markdown converter"
    )
    markdown_format: Optional[str] = Field(
        None,
        description="Updated markdown format style"
    )
    callback_url: Optional[str] = Field(
        None,
        description="Updated webhook URL",
        max_length=1024
    )
    llamaextract_mode: Optional[str] = Field(
        None,
        description="Updated LlamaExtract extraction mode"
    )
    llamaextract_target: Optional[str] = Field(
        None,
        description="Updated LlamaExtract extraction target"
    )

    @field_validator("allowed_senders")
    @classmethod
    def validate_allowed_senders(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate and normalize allowed sender patterns."""
        return _validate_sender_patterns(v)

    @field_validator("callback_url")
    @classmethod
    def validate_callback_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate callback_url to prevent SSRF attacks."""
        return _validate_callback_url_ssrf(v)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Invoice Processing",
                "is_active": True,
                "model_provider": "openai",
                "model_name": "gpt-4o"
            }
        }
    )


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================


class InboundEmailAddressResponse(BaseModel):
    """Response schema for an inbound email address."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440000",
                "email_address": "abc123@parse.phbsolution.com",
                "name": "Invoice Processing",
                "description": "Receives invoices from vendors",
                "is_active": True,
                "allowed_senders": ["*@vendor.com"],
                "schema_definition_id": "550e8400-e29b-41d4-a716-446655440000",
                "extraction_schema": None,
                "model_provider": "google",
                "model_name": "gemini-2.5-flash",
                "split_mode": "batch",
                "extraction_mode": "vllm",
                "callback_url": "https://example.com/webhooks/email-extraction",
                "emails_received_count": 42,
                "documents_processed_count": 38,
                "last_email_at": "2025-11-15T14:30:00Z",
                "created_at": "2025-11-01T10:00:00Z",
                "updated_at": "2025-11-15T14:30:00Z"
            }
        }
    )

    id: UUID = Field(..., description="Unique email address identifier")
    email_address: str = Field(
        ...,
        description="Full email address (uuid@domain)",
        json_schema_extra={"example": "abc123@parse.phbsolution.com"}
    )
    name: str = Field(..., description="User-friendly name")
    description: Optional[str] = Field(None, description="Description of purpose")
    is_active: bool = Field(..., description="Whether this address is active")
    allowed_senders: Optional[List[str]] = Field(
        None,
        description="List of allowed sender patterns"
    )

    # Job configuration
    schema_definition_id: Optional[UUID] = Field(
        None,
        description="Schema definition ID for extraction"
    )
    extraction_schema: Optional[dict[str, Any]] = Field(
        None,
        description="Custom JSON schema for extraction"
    )
    model_provider: str = Field(..., description="VLLM provider")
    model_name: str = Field(..., description="Model name")
    split_mode: str = Field(..., description="Split mode for processing")
    extraction_mode: str = Field(..., description="Extraction mode")
    callback_url: Optional[str] = Field(None, description="Webhook URL for results")

    # Stats
    emails_received_count: int = Field(
        ...,
        description="Total number of emails received",
        json_schema_extra={"example": 42}
    )
    documents_processed_count: int = Field(
        ...,
        description="Total number of documents processed from emails",
        json_schema_extra={"example": 38}
    )
    last_email_at: Optional[datetime] = Field(
        None,
        description="Timestamp of last received email"
    )

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class InboundEmailAddressListResponse(BaseModel):
    """Response schema for listing inbound email addresses."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "addresses": [
                    {
                        "id": "660e8400-e29b-41d4-a716-446655440000",
                        "email_address": "abc123@parse.phbsolution.com",
                        "name": "Invoice Processing",
                        "is_active": True,
                        "emails_received_count": 42,
                        "documents_processed_count": 38
                    }
                ],
                "total": 5,
                "limit": 20,
                "offset": 0
            }
        }
    )

    addresses: List[InboundEmailAddressResponse] = Field(
        ...,
        description="List of inbound email addresses"
    )
    total: int = Field(..., description="Total number of addresses")
    limit: int = Field(..., description="Results per page")
    offset: int = Field(..., description="Offset for pagination")


class InboundEmailLogResponse(BaseModel):
    """Response schema for an inbound email log entry."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "770e8400-e29b-41d4-a716-446655440000",
                "sender_email": "vendor@example.com",
                "sender_name": "Vendor Accounting",
                "subject": "Invoice #12345",
                "status": "processed",
                "error_message": None,
                "attachment_count": 2,
                "attachment_names": ["invoice.pdf", "receipt.pdf"],
                "document_ids": [
                    "880e8400-e29b-41d4-a716-446655440000",
                    "990e8400-e29b-41d4-a716-446655440000"
                ],
                "extraction_job_ids": [
                    "aa0e8400-e29b-41d4-a716-446655440000",
                    "bb0e8400-e29b-41d4-a716-446655440000"
                ],
                "received_at": "2025-11-15T14:30:00Z",
                "processed_at": "2025-11-15T14:30:45Z"
            }
        }
    )

    id: UUID = Field(..., description="Unique log entry identifier")
    sender_email: str = Field(
        ...,
        description="Email address of the sender",
        json_schema_extra={"example": "vendor@example.com"}
    )
    sender_name: Optional[str] = Field(
        None,
        description="Display name of the sender",
        json_schema_extra={"example": "Vendor Accounting"}
    )
    subject: Optional[str] = Field(
        None,
        description="Email subject line",
        json_schema_extra={"example": "Invoice #12345"}
    )
    status: str = Field(
        ...,
        description="Processing status: 'received', 'processing', 'processed', 'failed', 'rejected'",
        json_schema_extra={"example": "processed"}
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if processing failed"
    )
    attachment_count: int = Field(
        ...,
        description="Number of attachments in the email",
        json_schema_extra={"example": 2}
    )
    attachment_names: Optional[List[str]] = Field(
        None,
        description="List of attachment filenames",
        json_schema_extra={"example": ["invoice.pdf", "receipt.pdf"]}
    )
    document_ids: Optional[List[UUID]] = Field(
        None,
        description="List of created document IDs"
    )
    extraction_job_ids: Optional[List[UUID]] = Field(
        None,
        description="List of created extraction job IDs"
    )
    received_at: datetime = Field(
        ...,
        description="When the email was received"
    )
    processed_at: Optional[datetime] = Field(
        None,
        description="When processing completed"
    )


class InboundEmailLogListResponse(BaseModel):
    """Response schema for listing inbound email logs."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "logs": [
                    {
                        "id": "770e8400-e29b-41d4-a716-446655440000",
                        "sender_email": "vendor@example.com",
                        "subject": "Invoice #12345",
                        "status": "processed",
                        "attachment_count": 2,
                        "received_at": "2025-11-15T14:30:00Z"
                    }
                ],
                "total": 100,
                "limit": 20,
                "offset": 0
            }
        }
    )

    logs: List[InboundEmailLogResponse] = Field(
        ...,
        description="List of inbound email log entries"
    )
    total: int = Field(..., description="Total number of log entries")
    limit: int = Field(..., description="Results per page")
    offset: int = Field(..., description="Offset for pagination")
