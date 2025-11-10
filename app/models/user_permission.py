"""UserPermission model - custom permissions granted/revoked for individual users."""

from datetime import datetime
from sqlalchemy import Column, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class UserPermission(Base):
    """UserPermission model - grants or revokes specific permissions for individual users."""

    __tablename__ = "user_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    permission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    granted = Column(Boolean, nullable=False, default=True)  # True=grant, False=revoke

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="custom_permissions")
    permission = relationship("Permission")

    # Indexes
    __table_args__ = (
        Index("idx_user_permissions_user_id", "user_id"),
        Index("idx_user_permissions_permission_id", "permission_id"),
        Index("idx_user_permissions_unique", "user_id", "permission_id", unique=True),
    )

    def __repr__(self):
        return f"<UserPermission(user_id={self.user_id}, permission_id={self.permission_id}, granted={self.granted})>"
