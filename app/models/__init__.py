"""Database models."""

from app.models.document import Document, DocumentPage
from app.models.extraction_job import ExtractionJob
from app.models.extraction_result import ExtractionResult
from app.models.model_provider_key import ModelProviderKey
from app.models.schema_definition import SchemaDefinition

# Auth and Multi-tenancy models
from app.models.tenant import Tenant
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user_permission import UserPermission

# Billing models
from app.models.credit_package import CreditPackage
from app.models.credit_transaction import CreditTransaction
from app.models.subscription import Subscription

# API Token model
from app.models.api_token import ApiToken

# Admin audit log model
from app.models.admin_audit_log import AdminAuditLog

# Platform settings model
from app.models.platform_setting import PlatformSetting

__all__ = [
    "Document",
    "DocumentPage",
    "ExtractionJob",
    "ExtractionResult",
    "ModelProviderKey",
    "SchemaDefinition",
    # Auth and Multi-tenancy
    "Tenant",
    "User",
    "Role",
    "Permission",
    "RolePermission",
    "UserPermission",
    # Billing
    "CreditPackage",
    "CreditTransaction",
    "Subscription",
    # API Tokens
    "ApiToken",
    # Admin Audit
    "AdminAuditLog",
    # Platform Settings
    "PlatformSetting",
]
