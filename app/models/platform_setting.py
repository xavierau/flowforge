"""
Platform Settings Model

Stores system-wide configuration settings that can be modified by super admins.
Settings are stored with JSONB values to support different data types.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class PlatformSetting(Base):
    """
    Platform-wide configuration settings.

    Examples:
    - trial_credits_amount: Number of credits new tenants receive on signup
    - max_file_size_mb: Maximum upload file size
    - feature_flags: JSON object with feature toggles
    """
    __tablename__ = "platform_settings"

    key = Column(String(100), primary_key=True, index=True, nullable=False)
    value = Column(JSONB, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False, index=True, default="general")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<PlatformSetting(key={self.key}, value={self.value})>"
