"""Email service for sending transactional emails using async SMTP and Jinja2 templates."""

import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

logger = logging.getLogger(__name__)


class EmailServiceError(Exception):
    """Base exception for email service errors."""

    pass


class EmailConfigurationError(EmailServiceError):
    """Exception raised when SMTP is not configured properly."""

    pass


class EmailDeliveryError(EmailServiceError):
    """Exception raised when email sending fails."""

    pass


class EmailService:
    """
    Service for sending transactional emails using async SMTP.

    Uses Jinja2 templates for email rendering and aiosmtplib for async delivery.

    Usage:
        service = EmailService()
        if service.is_configured():
            await service.send_invitation_email(
                to_email="user@example.com",
                invitation_url="https://app.example.com/accept?token=...",
                invited_by="John Doe",
                tenant_name="Acme Corp"
            )

    Configuration:
        SMTP settings are loaded from app.config.settings by default.
        Override by passing parameters to __init__().
    """

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_from_email: Optional[str] = None,
        smtp_from_name: Optional[str] = None,
        smtp_use_tls: Optional[bool] = None,
    ):
        """
        Initialize email service with SMTP settings.

        Args:
            smtp_host: SMTP server hostname (default from settings)
            smtp_port: SMTP server port (default from settings)
            smtp_user: SMTP username for authentication (default from settings)
            smtp_password: SMTP password for authentication (default from settings)
            smtp_from_email: Sender email address (default from settings)
            smtp_from_name: Sender display name (default from settings)
            smtp_use_tls: Whether to use STARTTLS (default from settings)
        """
        from app.config import settings

        self._smtp_host = smtp_host if smtp_host is not None else settings.smtp_host
        self._smtp_port = smtp_port if smtp_port is not None else settings.smtp_port
        self._smtp_user = smtp_user if smtp_user is not None else settings.smtp_user
        self._smtp_password = (
            smtp_password if smtp_password is not None else settings.smtp_password
        )
        self._smtp_from_email = (
            smtp_from_email if smtp_from_email is not None else settings.smtp_from_email
        )
        self._smtp_from_name = (
            smtp_from_name if smtp_from_name is not None else settings.smtp_from_name
        )
        self._smtp_use_tls = (
            smtp_use_tls if smtp_use_tls is not None else settings.smtp_use_tls
        )

        # Initialize Jinja2 environment
        templates_dir = Path(__file__).parent.parent / "templates"
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=True,
        )

    def is_configured(self) -> bool:
        """
        Check if SMTP is properly configured.

        Returns:
            True if smtp_host, smtp_port, and smtp_from_email are all set
        """
        return bool(
            self._smtp_host and self._smtp_port and self._smtp_from_email
        )

    def _render_template(self, template_name: str, context: dict) -> str:
        """
        Render a Jinja2 email template.

        Args:
            template_name: Path to template relative to templates directory
            context: Dictionary of variables to pass to template

        Returns:
            Rendered HTML string

        Raises:
            EmailServiceError: If template cannot be found or rendered
        """
        try:
            template = self._jinja_env.get_template(template_name)
            return template.render(**context)
        except TemplateNotFound as e:
            logger.error("Email template not found: %s", template_name)
            raise EmailServiceError(f"Email template not found: {template_name}") from e
        except Exception as e:
            logger.error("Failed to render email template %s: %s", template_name, e)
            raise EmailServiceError(
                f"Failed to render email template: {type(e).__name__}"
            ) from e

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> None:
        """
        Send an email via SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML body content
            text_content: Optional plain text body (for multipart emails)

        Raises:
            EmailConfigurationError: If SMTP is not configured
            EmailDeliveryError: If sending fails
        """
        if not self.is_configured():
            raise EmailConfigurationError(
                "SMTP is not configured. Set SMTP_HOST, SMTP_PORT, and "
                "SMTP_FROM_EMAIL environment variables."
            )

        # Build email message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = (
            f"{self._smtp_from_name} <{self._smtp_from_email}>"
            if self._smtp_from_name
            else self._smtp_from_email
        )
        msg["To"] = to_email

        # Add plain text part (optional)
        if text_content:
            text_part = MIMEText(text_content, "plain", "utf-8")
            msg.attach(text_part)

        # Add HTML part
        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(html_part)

        try:
            logger.info(
                "Sending email to %s with subject: %s",
                to_email,
                subject,
            )

            # Connect and send
            if self._smtp_use_tls:
                # Use STARTTLS
                await aiosmtplib.send(
                    msg,
                    hostname=self._smtp_host,
                    port=self._smtp_port,
                    username=self._smtp_user if self._smtp_user else None,
                    password=self._smtp_password if self._smtp_password else None,
                    start_tls=True,
                )
            else:
                # No TLS (not recommended for production)
                await aiosmtplib.send(
                    msg,
                    hostname=self._smtp_host,
                    port=self._smtp_port,
                    username=self._smtp_user if self._smtp_user else None,
                    password=self._smtp_password if self._smtp_password else None,
                )

            logger.info("Email sent successfully to %s", to_email)

        except aiosmtplib.SMTPAuthenticationError as e:
            logger.error("SMTP authentication failed: %s", e)
            raise EmailDeliveryError(
                "SMTP authentication failed. Check SMTP_USER and SMTP_PASSWORD."
            ) from e
        except aiosmtplib.SMTPConnectError as e:
            logger.error("Failed to connect to SMTP server: %s", e)
            raise EmailDeliveryError(
                f"Failed to connect to SMTP server at {self._smtp_host}:{self._smtp_port}"
            ) from e
        except aiosmtplib.SMTPException as e:
            logger.error("SMTP error while sending email: %s", e)
            raise EmailDeliveryError(f"SMTP error: {type(e).__name__}") from e
        except Exception as e:
            logger.error("Unexpected error sending email: %s", e)
            raise EmailDeliveryError(
                f"Failed to send email: {type(e).__name__}"
            ) from e

    async def send_invitation_email(
        self,
        to_email: str,
        invitation_url: str,
        invited_by: str,
        tenant_name: str,
    ) -> None:
        """
        Send an invitation email to a new user.

        Args:
            to_email: Recipient email address
            invitation_url: Full URL for accepting the invitation
            invited_by: Name of the person who sent the invitation
            tenant_name: Name of the tenant/organization

        Raises:
            EmailConfigurationError: If SMTP is not configured
            EmailDeliveryError: If sending fails
            EmailServiceError: If template rendering fails
        """
        from app.config import settings

        # Prepare template context
        context = {
            "app_name": self._smtp_from_name or "AI Document Processing",
            "invitation_url": invitation_url,
            "invited_by": invited_by,
            "tenant_name": tenant_name,
            "current_year": datetime.now().year,
        }

        # Render HTML template
        html_content = self._render_template("email/invitation.html", context)

        # Create plain text version
        text_content = f"""
You're Invited to Join {tenant_name}

{invited_by} has invited you to join {tenant_name} on {context['app_name']}.

{context['app_name']} is an AI-powered document processing platform that helps teams
extract structured data from documents with ease.

Accept your invitation by visiting:
{invitation_url}

Note: This invitation will expire in 7 days.

What you can do with {context['app_name']}:
- Upload Documents: Process PDFs, images, and scanned documents
- Define Custom Schemas: Create extraction templates for your specific needs
- AI-Powered Extraction: Extract structured data using advanced vision AI
- Build Workflows: Automate document processing with visual workflow builder

If you didn't expect this invitation, you can safely ignore this email.

---
This email was sent by {context['app_name']}.
        """.strip()

        # Build subject
        subject = f"You're Invited to Join {tenant_name}"

        # Send email
        await self._send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )


# Singleton instance - lazy loaded
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """
    Get the singleton email service instance.

    Lazy loads the service using settings from app.config.

    Returns:
        EmailService singleton instance
    """
    global _email_service

    if _email_service is None:
        _email_service = EmailService()

    return _email_service
