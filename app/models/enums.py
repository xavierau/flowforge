"""
Domain enums for type-safe constant values.

These enums use str inheritance to maintain backward compatibility with existing
database string values while providing type safety and IDE support.
"""
from enum import Enum


class CreditTransactionType(str, Enum):
    """
    Credit transaction types (matches current database schema).

    Controls how credits flow in the system:
    - DEDUCTION: Credits consumed (negative amount) - used for extraction jobs
    - TOPUP: Manual credit purchase (positive amount)
    - REFUND: Credits returned (positive)
    - ADMIN_ADJUSTMENT: Manual correction (positive or negative)
    - TRIAL_SIGNUP: Initial free credits (positive)
    - MIGRATION_BALANCE_IMPORT: Data migration (positive)
    """
    DEDUCTION = "deduction"
    TOPUP = "topup"
    REFUND = "refund"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    TRIAL_SIGNUP = "trial_signup"
    MIGRATION_BALANCE_IMPORT = "migration_balance_import"


class ReferenceType(str, Enum):
    """
    Reference types for linking transactions to source entities (matches current database schema).

    Used with reference_id to create foreign key relationships.
    """
    EXTRACTION_JOB = "extraction_job"
    PAYMENT = "payment"
    TENANT_REGISTRATION = "tenant_registration"
    ADMIN_MANUAL_ADJUSTMENT = "admin_manual_adjustment"
    MANUAL = "manual"


class JobStatus(str, Enum):
    """
    Extraction job status lifecycle.

    State machine:
    queued → processing → completed
                ↓
              failed
    """
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentStatus(str, Enum):
    """
    Document processing status lifecycle.

    State machine:
    uploaded → processing → ready_for_extraction → completed
                  ↓
                failed
    """
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY_FOR_EXTRACTION = "ready_for_extraction"
    COMPLETED = "completed"
    FAILED = "failed"


class UserRole(str, Enum):
    """User roles for RBAC"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class SubscriptionStatus(str, Enum):
    """Subscription lifecycle states"""
    ACTIVE = "active"
    TRIAL = "trial"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"
