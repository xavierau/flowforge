"""Permission model for granular access control."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import Base


class Permission(Base):
    """Permission model - defines granular permissions for resources and actions."""

    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)  # documents:create
    resource = Column(String(50), nullable=False, index=True)  # documents, schemas, users
    action = Column(String(50), nullable=False)  # create, read, update, delete, share, export
    description = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_permissions_resource", "resource"),
        Index("idx_permissions_action", "action"),
        Index("idx_permissions_name", "name"),
    )

    def __repr__(self):
        return f"<Permission(id={self.id}, name={self.name})>"
