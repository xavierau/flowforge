"""
Platform Settings Service

Manages system-wide configuration settings that can be modified by super admins.
Uses Redis for distributed caching to ensure thread-safety and consistency across workers.
"""

from typing import Optional, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
import json
import redis

from app.models.platform_setting import PlatformSetting
from app.config import settings as app_settings


# Redis client for distributed caching
_redis_client: Optional[redis.Redis] = None

# Constants
DEFAULT_TRIAL_CREDITS = 100
TRIAL_CREDITS_MIN = 0
TRIAL_CREDITS_MAX = 1_000_000
CACHE_TTL = 3600  # 1 hour


class PlatformSettingsService:
    """
    Service for managing platform-wide configuration settings.

    SOLID Compliance:
    - Single Responsibility: Platform settings management only
    - Open/Closed: Extensible via new setting keys
    - Dependency Inversion: Depends on Session abstraction

    Security:
    - Input validation for all setting values
    - Type-specific validation rules
    - Protection against JSONB injection
    """

    def __init__(self, db: Session):
        """
        Initialize platform settings service.

        Args:
            db: Database session for queries (injected dependency)
        """
        self.db = db
        self._init_redis()

    def _init_redis(self):
        """Initialize Redis client if not already initialized."""
        global _redis_client
        if _redis_client is None:
            try:
                # Parse Redis URL from app settings
                redis_url = app_settings.celery_broker_url  # Reuse Celery Redis
                _redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,  # Auto-decode bytes to str
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                _redis_client.ping()
            except Exception as e:
                # Fallback: Redis not available, disable caching
                print(f"Warning: Redis not available for settings cache: {e}")
                _redis_client = None

    def _get_cache_key(self, key: str) -> str:
        """Generate Redis cache key for a setting."""
        return f"platform_setting:{key}"

    def _validate_setting_value(self, key: str, value: Any) -> Any:
        """
        Validate and sanitize setting values based on key.

        Args:
            key: Setting key
            value: Proposed value

        Returns:
            Validated value

        Raises:
            ValueError: If value is invalid for the given key
        """
        if key == "trial_credits_amount":
            # Validate trial credits amount
            if not isinstance(value, (int, float)):
                raise ValueError(f"trial_credits_amount must be a number, got {type(value).__name__}")

            value = int(value)  # Convert to int

            if value < TRIAL_CREDITS_MIN:
                raise ValueError(f"trial_credits_amount must be at least {TRIAL_CREDITS_MIN}")

            if value > TRIAL_CREDITS_MAX:
                raise ValueError(f"trial_credits_amount cannot exceed {TRIAL_CREDITS_MAX:,}")

            return value

        # Add validation for other settings as needed
        # For now, accept any JSON-serializable value
        try:
            json.dumps(value)  # Ensure it's JSON-serializable
            return value
        except (TypeError, ValueError) as e:
            raise ValueError(f"Setting value must be JSON-serializable: {e}")

    def get_setting(self, key: str, default: Any = None, use_cache: bool = True) -> Any:
        """
        Get a platform setting value by key.

        Args:
            key: Setting key (e.g., "trial_credits_amount")
            default: Default value if setting doesn't exist
            use_cache: If True, use Redis cache; if False, query database

        Returns:
            Setting value (from JSONB field) or default

        Example:
            >>> service.get_setting("trial_credits_amount", 100)
            50
        """
        # Check Redis cache first
        if use_cache and _redis_client:
            try:
                cache_key = self._get_cache_key(key)
                cached_value = _redis_client.get(cache_key)
                if cached_value is not None:
                    return json.loads(cached_value)
            except Exception as e:
                # Cache error - continue to database
                print(f"Warning: Redis cache read failed: {e}")

        # Query database
        setting = self.db.query(PlatformSetting).filter(PlatformSetting.key == key).first()

        if setting:
            value = setting.value
            # Update Redis cache
            if _redis_client:
                try:
                    cache_key = self._get_cache_key(key)
                    _redis_client.setex(
                        cache_key,
                        CACHE_TTL,
                        json.dumps(value)
                    )
                except Exception as e:
                    print(f"Warning: Redis cache write failed: {e}")
            return value

        return default

    def update_setting(self, key: str, value: Any, description: Optional[str] = None, category: str = "general") -> PlatformSetting:
        """
        Update or create a platform setting with validation.

        Args:
            key: Setting key
            value: New value (will be validated and stored as JSONB)
            description: Optional description of the setting
            category: Setting category (default: "general")

        Returns:
            Updated or created PlatformSetting instance

        Raises:
            ValueError: If key or value is invalid
        """
        if not key:
            raise ValueError("Setting key cannot be empty")

        # Validate value based on key
        validated_value = self._validate_setting_value(key, value)

        # Check if setting exists
        setting = self.db.query(PlatformSetting).filter(PlatformSetting.key == key).first()

        if setting:
            # Update existing setting
            setting.value = validated_value
            setting.updated_at = datetime.now(timezone.utc)
            if description is not None:
                setting.description = description
        else:
            # Create new setting
            setting = PlatformSetting(
                key=key,
                value=validated_value,
                description=description,
                category=category
            )
            self.db.add(setting)

        try:
            self.db.commit()
            self.db.refresh(setting)

            # Invalidate Redis cache for this key
            if _redis_client:
                try:
                    cache_key = self._get_cache_key(key)
                    _redis_client.delete(cache_key)
                except Exception as e:
                    print(f"Warning: Redis cache invalidation failed: {e}")

            return setting

        except IntegrityError as e:
            self.db.rollback()
            raise ValueError(f"Failed to update setting: {str(e)}")

    def get_all_settings(self, category: Optional[str] = None) -> List[PlatformSetting]:
        """
        Get all platform settings, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of PlatformSetting instances
        """
        query = self.db.query(PlatformSetting)

        if category:
            query = query.filter(PlatformSetting.category == category)

        return query.order_by(PlatformSetting.key).all()

    def delete_setting(self, key: str) -> bool:
        """
        Delete a platform setting.

        Args:
            key: Setting key to delete

        Returns:
            True if setting was deleted, False if not found
        """
        setting = self.db.query(PlatformSetting).filter(PlatformSetting.key == key).first()

        if not setting:
            return False

        self.db.delete(setting)
        self.db.commit()

        # Invalidate Redis cache
        if _redis_client:
            try:
                cache_key = self._get_cache_key(key)
                _redis_client.delete(cache_key)
            except Exception as e:
                print(f"Warning: Redis cache invalidation failed: {e}")

        return True

    def get_trial_credits_amount(self) -> int:
        """
        Get the trial credits amount for new tenant signups.

        This is a convenience method that wraps get_setting with proper typing
        and default value.

        Returns:
            Number of credits to grant to new tenants (default: DEFAULT_TRIAL_CREDITS)
        """
        value = self.get_setting("trial_credits_amount", DEFAULT_TRIAL_CREDITS)

        # Ensure it's an integer
        try:
            return int(value)
        except (TypeError, ValueError):
            return DEFAULT_TRIAL_CREDITS

    def clear_cache(self, key: Optional[str] = None) -> None:
        """
        Clear the Redis settings cache.

        Args:
            key: Optional specific key to clear. If None, clears all settings cache.

        Useful for testing or when settings are updated externally.
        """
        if not _redis_client:
            return

        try:
            if key:
                # Clear specific key
                cache_key = self._get_cache_key(key)
                _redis_client.delete(cache_key)
            else:
                # Clear all settings cache
                pattern = self._get_cache_key("*")
                for cache_key in _redis_client.scan_iter(match=pattern):
                    _redis_client.delete(cache_key)
        except Exception as e:
            print(f"Warning: Redis cache clear failed: {e}")
