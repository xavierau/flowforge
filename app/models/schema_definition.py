"""SchemaDefinition model."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class SchemaDefinition(Base):
    """SchemaDefinition model - represents reusable JSON schemas for extraction."""

    __tablename__ = "schema_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,  # Nullable for platform-wide schemas
        index=True
    )
    name = Column(String(255), nullable=False)
    definitions = Column(JSONB, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="schema_definitions")

    # Indexes
    __table_args__ = (
        Index("idx_schema_definitions_tenant_id", "tenant_id"),
        Index("idx_schema_definitions_name", "tenant_id", "name", unique=True),  # Unique per tenant
        Index("idx_schema_definitions_created_at", "created_at"),
    )