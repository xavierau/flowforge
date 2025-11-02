"""ModelProviderKey model."""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import Base


class ModelProviderKey(Base):
    """ModelProviderKey model - stores encrypted VLLM provider API keys."""

    __tablename__ = "model_provider_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(50), nullable=False, unique=True)  # google, openai
    api_key_encrypted = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Indexes
    __table_args__ = (Index("idx_model_provider_keys_provider", "provider", unique=True),)
