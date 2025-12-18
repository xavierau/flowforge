"""Password Reset Token model for secure password recovery."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class PasswordResetToken(Base):
    """Password Reset Token model - stores tokens for password recovery flow.

    This model provides a secure, auditable way to manage password reset tokens.
    Tokens are single-use and time-limited for security.
    """

    __tablename__ = "password_reset_tokens"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key to user
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Token data - hashed token for security
    token = Column(String(255), unique=True, nullable=False, index=True)

    # Expiration
    expires_at = Column(DateTime, nullable=False)

    # Usage tracking for audit
    used_at = Column(DateTime, nullable=True)  # Set when token is used

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="password_reset_tokens")

    # Indexes
    __table_args__ = (
        Index("idx_password_reset_tokens_user_id", "user_id"),
        Index("idx_password_reset_tokens_token", "token", unique=True),
        Index("idx_password_reset_tokens_expires_at", "expires_at"),
    )

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired.

        Returns:
            True if the token has expired, False otherwise.
        """
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the token is valid (not expired and not used).

        Returns:
            True if the token is valid for use, False otherwise.
        """
        return not self.is_expired and self.used_at is None

    def mark_as_used(self) -> None:
        """Mark the token as used by setting used_at timestamp."""
        self.used_at = datetime.utcnow()

    def __repr__(self):
        return f"<PasswordResetToken(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at}, used={self.used_at is not None})>"
