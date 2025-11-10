"""Admin audit log model for tracking super admin actions."""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, UUID, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class AdminAuditLog(Base):
    """
    Admin audit log model for tracking super admin actions.

    This model stores a comprehensive audit trail of all super admin operations
    performed through the admin API endpoints. It provides accountability,
    security monitoring, and compliance capabilities.

    Attributes:
        id: Unique identifier for the audit log entry
        user_id: ID of the user who performed the action
        action: Action performed (e.g., 'tenant_suspended', 'user_deactivated')
        resource_type: Type of resource affected (e.g., 'tenant', 'user', 'token')
        resource_id: ID of the affected resource
        endpoint: API endpoint accessed
        method: HTTP method used (GET, POST, PATCH, DELETE)
        ip_address: IP address of the request origin
        user_agent: User agent string from the request
        status_code: HTTP status code of the response
        error_message: Error message if the operation failed
        metadata: Additional context data (JSONB)
        created_at: Timestamp when the log was created

    Example:
        # Log a tenant suspension
        audit_log = AdminAuditLog(
            user_id=admin_user.id,
            action="tenant_suspended",
            resource_type="tenant",
            resource_id=tenant.id,
            endpoint="/admin/tenants/{tenant_id}/status",
            method="PATCH",
            ip_address="192.168.1.1",
            status_code=200,
            metadata={"previous_status": "active", "new_status": "suspended"}
        )
    """

    __tablename__ = "admin_audit_logs"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Actor
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True
    )

    # Action details
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True)

    # Request details
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)

    # Response details
    status_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Additional metadata (renamed to avoid SQLAlchemy reserved word)
    audit_metadata = Column("metadata", JSONB, nullable=True, server_default='{}')

    # Timestamp
    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="admin_audit_logs")

    def __repr__(self) -> str:
        """String representation of the audit log."""
        return (
            f"<AdminAuditLog(id={self.id}, "
            f"action={self.action}, "
            f"user_id={self.user_id}, "
            f"created_at={self.created_at})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit log to dictionary representation."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "endpoint": self.endpoint,
            "method": self.method,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "status_code": self.status_code,
            "error_message": self.error_message,
            "metadata": self.audit_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
