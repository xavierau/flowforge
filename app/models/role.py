"""Role model for role-based access control."""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Role(Base):
    """Role model - defines roles with associated permissions."""

    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False, index=True)  # admin, member, viewer
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)  # System roles can't be deleted
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True
    )  # Null = platform-wide role

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_roles_name", "name"),
        Index("idx_roles_is_system", "is_system"),
    )

    def __repr__(self):
        return f"<Role(id={self.id}, name={self.name})>"
