"""Platform Application service for managing external applications."""

import ipaddress
import re
from datetime import datetime
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.platform_application import PlatformApplication
from app.models.platform_api_key import PlatformApiKey
from app.services.platform_api_key_service import PlatformApiKeyService


class PlatformApplicationService:
    """Service for Platform Application management."""

    def __init__(self, db: Session):
        self.db = db

    def create_application(
        self,
        name: str,
        slug: str,
        description: Optional[str] = None,
        webhook_url: Optional[str] = None,
        allowed_ips: Optional[List[str]] = None,
        rate_limit_per_minute: int = 60,
        rate_limit_per_hour: int = 1000,
    ) -> Tuple[PlatformApplication, str]:
        """
        Create a new platform application with an initial API key.

        Args:
            name: Application display name
            slug: Unique URL-safe identifier
            description: Optional description
            webhook_url: Optional webhook URL for notifications
            allowed_ips: Optional list of allowed IPs/CIDR ranges
            rate_limit_per_minute: Requests per minute limit
            rate_limit_per_hour: Requests per hour limit

        Returns:
            Tuple of (PlatformApplication, initial_api_key)

        Raises:
            ValueError: If slug is invalid or already exists
        """
        # Validate slug format
        if not self._is_valid_slug(slug):
            raise ValueError(
                "Slug must be lowercase alphanumeric with hyphens, "
                "3-100 characters, and start/end with alphanumeric"
            )

        # Check slug uniqueness
        existing = self.get_application_by_slug(slug)
        if existing:
            raise ValueError(f"Application with slug '{slug}' already exists")

        # Validate allowed IPs if provided
        if allowed_ips:
            for ip in allowed_ips:
                if not self._is_valid_ip_or_cidr(ip):
                    raise ValueError(f"Invalid IP or CIDR range: {ip}")

        # Generate webhook secret if webhook_url is provided
        webhook_secret = None
        if webhook_url:
            webhook_secret = PlatformApiKeyService.generate_webhook_secret()

        # Create application
        application = PlatformApplication(
            name=name,
            slug=slug,
            description=description,
            webhook_url=webhook_url,
            webhook_secret=webhook_secret,
            allowed_ips=allowed_ips or [],
            rate_limit_per_minute=rate_limit_per_minute,
            rate_limit_per_hour=rate_limit_per_hour,
            is_active=True,
        )
        self.db.add(application)
        self.db.flush()  # Get the ID

        # Create initial API key with all scopes
        from app.models.enums import PlatformScope
        all_scopes = PlatformScope.all_scopes()

        full_key, key_hash, key_prefix = PlatformApiKeyService.generate_key()

        api_key = PlatformApiKey(
            application_id=application.id,
            name="Initial Key",
            token_hash=key_hash,
            token_prefix=key_prefix,
            scopes=all_scopes,
            is_active=True,
        )
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(application)

        return application, full_key

    def get_application_by_id(self, application_id: UUID) -> Optional[PlatformApplication]:
        """Get application by ID."""
        return self.db.query(PlatformApplication).filter(
            PlatformApplication.id == application_id
        ).first()

    def get_application_by_slug(self, slug: str) -> Optional[PlatformApplication]:
        """Get application by slug."""
        return self.db.query(PlatformApplication).filter(
            PlatformApplication.slug == slug
        ).first()

    def list_applications(
        self,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[PlatformApplication], int]:
        """
        List platform applications with optional filtering.

        Args:
            is_active: Filter by active status
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (applications, total_count)
        """
        query = self.db.query(PlatformApplication)

        if is_active is not None:
            query = query.filter(PlatformApplication.is_active == is_active)

        total = query.count()
        applications = query.order_by(
            PlatformApplication.created_at.desc()
        ).offset(offset).limit(limit).all()

        return applications, total

    def update_application(
        self,
        application_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        webhook_url: Optional[str] = None,
        allowed_ips: Optional[List[str]] = None,
        rate_limit_per_minute: Optional[int] = None,
        rate_limit_per_hour: Optional[int] = None,
    ) -> Optional[PlatformApplication]:
        """
        Update an existing application.

        Args:
            application_id: Application to update
            name: New name (optional)
            description: New description (optional)
            webhook_url: New webhook URL (optional)
            allowed_ips: New IP whitelist (optional)
            rate_limit_per_minute: New rate limit per minute (optional)
            rate_limit_per_hour: New rate limit per hour (optional)

        Returns:
            Updated application or None if not found

        Raises:
            ValueError: If provided values are invalid
        """
        application = self.get_application_by_id(application_id)
        if not application:
            return None

        if name is not None:
            application.name = name

        if description is not None:
            application.description = description

        if webhook_url is not None:
            application.webhook_url = webhook_url
            # Regenerate webhook secret when URL changes
            if webhook_url:
                application.webhook_secret = PlatformApiKeyService.generate_webhook_secret()
            else:
                application.webhook_secret = None

        if allowed_ips is not None:
            for ip in allowed_ips:
                if not self._is_valid_ip_or_cidr(ip):
                    raise ValueError(f"Invalid IP or CIDR range: {ip}")
            application.allowed_ips = allowed_ips

        if rate_limit_per_minute is not None:
            if rate_limit_per_minute < 1:
                raise ValueError("Rate limit per minute must be at least 1")
            application.rate_limit_per_minute = rate_limit_per_minute

        if rate_limit_per_hour is not None:
            if rate_limit_per_hour < 1:
                raise ValueError("Rate limit per hour must be at least 1")
            application.rate_limit_per_hour = rate_limit_per_hour

        application.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(application)

        return application

    def deactivate_application(self, application_id: UUID) -> Optional[PlatformApplication]:
        """
        Deactivate an application (soft delete).

        This also deactivates all associated API keys.

        Args:
            application_id: Application to deactivate

        Returns:
            Deactivated application or None if not found
        """
        application = self.get_application_by_id(application_id)
        if not application:
            return None

        application.is_active = False
        application.updated_at = datetime.utcnow()

        # Deactivate all API keys
        self.db.query(PlatformApiKey).filter(
            PlatformApiKey.application_id == application_id,
            PlatformApiKey.is_active == True
        ).update({
            "is_active": False,
            "revoked_at": datetime.utcnow()
        })

        self.db.commit()
        self.db.refresh(application)

        return application

    def activate_application(self, application_id: UUID) -> Optional[PlatformApplication]:
        """
        Reactivate a deactivated application.

        Note: API keys remain deactivated and must be recreated.

        Args:
            application_id: Application to activate

        Returns:
            Activated application or None if not found
        """
        application = self.get_application_by_id(application_id)
        if not application:
            return None

        application.is_active = True
        application.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(application)

        return application

    def validate_ip_whitelist(self, ip_address: str, allowed_ips: List[str]) -> bool:
        """
        Validate if an IP address is in the whitelist.

        Args:
            ip_address: IP address to check
            allowed_ips: List of allowed IPs or CIDR ranges

        Returns:
            True if IP is allowed (or whitelist is empty), False otherwise
        """
        # Empty whitelist means allow all
        if not allowed_ips:
            return True

        try:
            client_ip = ipaddress.ip_address(ip_address)
        except ValueError:
            return False

        for allowed in allowed_ips:
            try:
                # Try as network (CIDR)
                if '/' in allowed:
                    network = ipaddress.ip_network(allowed, strict=False)
                    if client_ip in network:
                        return True
                else:
                    # Try as single IP
                    if client_ip == ipaddress.ip_address(allowed):
                        return True
            except ValueError:
                continue

        return False

    def _is_valid_slug(self, slug: str) -> bool:
        """Validate slug format."""
        if not slug or len(slug) < 3 or len(slug) > 100:
            return False
        # Must be lowercase alphanumeric with hyphens, start/end with alphanumeric
        pattern = r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$'
        return bool(re.match(pattern, slug))

    def _is_valid_ip_or_cidr(self, value: str) -> bool:
        """Validate IP address or CIDR range."""
        try:
            if '/' in value:
                ipaddress.ip_network(value, strict=False)
            else:
                ipaddress.ip_address(value)
            return True
        except ValueError:
            return False

    # API Key management methods

    def create_api_key(
        self,
        application_id: UUID,
        name: str,
        scopes: List[str],
        expires_in_days: Optional[int] = None,
        created_by_user_id: Optional[UUID] = None,
    ) -> Tuple[PlatformApiKey, str]:
        """
        Create a new API key for an application.

        Args:
            application_id: Application to create key for
            name: User-friendly key name
            scopes: List of granted scopes
            expires_in_days: Optional expiration in days
            created_by_user_id: Optional user who created the key

        Returns:
            Tuple of (PlatformApiKey, full_key)

        Raises:
            ValueError: If application not found or scopes invalid
        """
        from app.models.enums import PlatformScope

        application = self.get_application_by_id(application_id)
        if not application:
            raise ValueError("Application not found")

        if not application.is_active:
            raise ValueError("Application is not active")

        # Validate scopes
        if not PlatformScope.validate_scopes(scopes):
            raise ValueError("Invalid scopes provided")

        # Generate key
        full_key, key_hash, key_prefix = PlatformApiKeyService.generate_key()

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            from datetime import timedelta
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        api_key = PlatformApiKey(
            application_id=application_id,
            name=name,
            token_hash=key_hash,
            token_prefix=key_prefix,
            scopes=scopes,
            expires_at=expires_at,
            created_by_user_id=created_by_user_id,
            is_active=True,
        )
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)

        return api_key, full_key

    def list_api_keys(
        self,
        application_id: UUID,
        is_active: Optional[bool] = None,
    ) -> List[PlatformApiKey]:
        """
        List API keys for an application.

        Args:
            application_id: Application to list keys for
            is_active: Optional filter by active status

        Returns:
            List of API keys (without full token values)
        """
        query = self.db.query(PlatformApiKey).filter(
            PlatformApiKey.application_id == application_id
        )

        if is_active is not None:
            query = query.filter(PlatformApiKey.is_active == is_active)

        return query.order_by(PlatformApiKey.created_at.desc()).all()

    def revoke_api_key(
        self,
        key_id: UUID,
        revoked_by_user_id: Optional[UUID] = None,
    ) -> Optional[PlatformApiKey]:
        """
        Revoke an API key.

        Args:
            key_id: Key to revoke
            revoked_by_user_id: Optional user who revoked the key

        Returns:
            Revoked key or None if not found
        """
        api_key = self.db.query(PlatformApiKey).filter(
            PlatformApiKey.id == key_id
        ).first()

        if not api_key:
            return None

        api_key.is_active = False
        api_key.revoked_at = datetime.utcnow()
        api_key.revoked_by_user_id = revoked_by_user_id

        self.db.commit()
        self.db.refresh(api_key)

        return api_key

    def get_api_key_by_id(self, key_id: UUID) -> Optional[PlatformApiKey]:
        """Get API key by ID."""
        return self.db.query(PlatformApiKey).filter(
            PlatformApiKey.id == key_id
        ).first()
