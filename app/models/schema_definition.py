"""SchemaDefinition model."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.database import Base


class SchemaDefinition(Base):
    """SchemaDefinition model - represents reusable JSON schemas for extraction."""

    __tablename__ = "schema_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    definitions = Column(JSONB, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Indexes
    __table_args__ = (
        Index("idx_schema_definitions_name", "name", unique=True),
        Index("idx_schema_definitions_created_at", "created_at"),
    )