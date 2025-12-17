"""Email service for sending transactional emails using SendGrid and Jinja2 templates."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, MimeType
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

logger = logging.getLogger(__name__)


class EmailServiceError(Exception):
    """Base exception for email service errors."""

    pass


class EmailConfigurationError(EmailServiceError):
    """Exception raised when SendGrid is not configured properly."""

    pass


class EmailDeliveryError(EmailServiceError):
    """Exception raised when email sending fails."""

    pass


class EmailService:
    """
    Service for sending transactional emails using SendGrid.

    Uses Jinja2 templates for email rendering and SendGrid API for delivery.

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
        Settings are loaded from app.config.settings by default.
        Override by passing parameters to __init__().
    """

    def __init__(
        self,
        sendgrid_api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
    ):
        """
        Initialize email service with SendGrid settings.

        Args:
            sendgrid_api_key: SendGrid API key (default from settings)
            from_email: Sender email address (default from settings)
            from_name: Sender display name (default from settings)
        """
        from app.config import settings

        self._api_key = sendgrid_api_key if sendgrid_api_key is not None else settings.sendgrid_api_key
        self._from_email = from_email if from_email is not None else settings.email_from_address
        self._from_name = from_name if from_name is not None else settings.email_from_name

        # Initialize SendGrid client if API key is provided
        self._client: Optional[SendGridAPIClient] = None
        if self._api_key:
            self._client = SendGridAPIClient(self._api_key)

        # Initialize Jinja2 environment
        templates_dir = Path(__file__).parent.parent / "templates"
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=True,
        )

    def is_configured(self) -> bool:
        """
        Check if SendGrid is properly configured.

        Returns:
            True if sendgrid_api_key and from_email are set
        """
        return bool(self._api_key and self._from_email)

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
        Send an email via SendGrid.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML body content
            text_content: Optional plain text body (for multipart emails)

        Raises:
            EmailConfigurationError: If SendGrid is not configured
            EmailDeliveryError: If sending fails
        """
        if not self.is_configured():
            raise EmailConfigurationError(
                "SendGrid is not configured. Set SENDGRID_API_KEY and "
                "EMAIL_FROM_ADDRESS environment variables."
            )

        # Build email message
        from_email = Email(self._from_email, self._from_name) if self._from_name else Email(self._from_email)
        to_email_obj = To(to_email)

        message = Mail(
            from_email=from_email,
            to_emails=to_email_obj,
            subject=subject,
        )

        # Add HTML content
        message.add_content(Content(MimeType.html, html_content))

        # Add plain text content if provided (should be added first for proper MIME ordering)
        if text_content:
            message.add_content(Content(MimeType.text, text_content))

        try:
            logger.info(
                "Sending email to %s with subject: %s",
                to_email,
                subject,
            )

            response = self._client.send(message)

            if response.status_code >= 400:
                logger.error(
                    "SendGrid returned error status %d: %s",
                    response.status_code,
                    response.body,
                )
                raise EmailDeliveryError(
                    f"SendGrid API error: status {response.status_code}"
                )

            logger.info("Email sent successfully to %s (status: %d)", to_email, response.status_code)

        except EmailDeliveryError:
            raise
        except Exception as e:
            logger.error("Failed to send email via SendGrid: %s", e)
            raise EmailDeliveryError(
                f"Failed to send email: {type(e).__name__}: {str(e)}"
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
            EmailConfigurationError: If SendGrid is not configured
            EmailDeliveryError: If sending fails
            EmailServiceError: If template rendering fails
        """
        # Prepare template context
        context = {
            "app_name": self._from_name or "AI Document Processing",
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

    async def send_password_reset_email(
        self,
        to_email: str,
        reset_url: str,
        user_name: Optional[str] = None,
        expires_in_hours: int = 24,
    ) -> None:
        """
        Send a password reset email to a user.

        Args:
            to_email: Recipient email address
            reset_url: Full URL for resetting the password
            user_name: Optional user's name for personalization
            expires_in_hours: How many hours until the link expires (default 24)

        Raises:
            EmailConfigurationError: If SendGrid is not configured
            EmailDeliveryError: If sending fails
            EmailServiceError: If template rendering fails
        """
        # Prepare template context
        context = {
            "app_name": self._from_name or "AI Document Processing",
            "reset_url": reset_url,
            "user_name": user_name,
            "expires_in_hours": expires_in_hours,
            "current_year": datetime.now().year,
        }

        # Render HTML template
        html_content = self._render_template("email/password_reset.html", context)

        # Create plain text version
        text_content = f"""
Reset Your Password

Hi{' ' + user_name if user_name else ''},

We received a request to reset the password for your {context['app_name']} account.
Click the link below to create a new password:

{reset_url}

Important: This password reset link will expire in {expires_in_hours} hours.
After that, you'll need to request a new link.

Didn't request this?
If you didn't request a password reset, please ignore this email or
contact support if you're concerned about your account security.
Your password will not change unless you click the link above.

For your security, never share this link with anyone.
{context['app_name']} will never ask for your password via email.

---
This email was sent by {context['app_name']}.
        """.strip()

        # Build subject
        subject = f"Reset Your Password - {context['app_name']}"

        # Send email
        await self._send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    async def send_verification_email(
        self,
        to_email: str,
        verification_url: str,
        user_name: Optional[str] = None,
        expires_in_hours: int = 48,
    ) -> None:
        """
        Send an email verification email to a user.

        Args:
            to_email: Recipient email address
            verification_url: Full URL for verifying the email
            user_name: Optional user's name for personalization
            expires_in_hours: How many hours until the link expires (default 48)

        Raises:
            EmailConfigurationError: If SendGrid is not configured
            EmailDeliveryError: If sending fails
            EmailServiceError: If template rendering fails
        """
        # Prepare template context
        context = {
            "app_name": self._from_name or "AI Document Processing",
            "verification_url": verification_url,
            "user_name": user_name,
            "expires_in_hours": expires_in_hours,
            "current_year": datetime.now().year,
        }

        # Render HTML template
        html_content = self._render_template("email/email_verification.html", context)

        # Create plain text version
        text_content = f"""
Verify Your Email Address

Hi{' ' + user_name if user_name else ''},

Thanks for signing up for {context['app_name']}! Please verify your email address
by clicking the link below to complete your account setup:

{verification_url}

Note: This verification link will expire in {expires_in_hours} hours.
If it expires, you can request a new verification email from your account settings.

Why verify your email?
- Secure Your Account: Protect your account from unauthorized access
- Recover Your Password: Reset your password if you ever forget it
- Receive Important Updates: Get notifications about your account and documents

If you didn't create an account with {context['app_name']}, you can safely ignore this email.
No account will be activated unless you verify your email.

---
This email was sent by {context['app_name']}.
        """.strip()

        # Build subject
        subject = f"Verify Your Email - {context['app_name']}"

        # Send email
        await self._send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    async def send_welcome_email(
        self,
        to_email: str,
        login_url: str,
        user_name: Optional[str] = None,
        tenant_name: Optional[str] = None,
    ) -> None:
        """
        Send a welcome email to a newly registered user.

        Args:
            to_email: Recipient email address
            login_url: Full URL for logging in
            user_name: Optional user's name for personalization
            tenant_name: Optional tenant/organization name

        Raises:
            EmailConfigurationError: If SendGrid is not configured
            EmailDeliveryError: If sending fails
            EmailServiceError: If template rendering fails
        """
        # Prepare template context
        context = {
            "app_name": self._from_name or "AI Document Processing",
            "login_url": login_url,
            "user_name": user_name,
            "tenant_name": tenant_name,
            "current_year": datetime.now().year,
        }

        # Render HTML template
        html_content = self._render_template("email/welcome.html", context)

        # Create plain text version
        tenant_text = f" and you're now part of {tenant_name}" if tenant_name else ""
        text_content = f"""
Welcome to {context['app_name']}!

Hi{' ' + user_name if user_name else ''},

Thank you for joining {context['app_name']}! Your account has been successfully created{tenant_text}.
We're excited to help you automate your document processing workflows.

Get started: {login_url}

Getting Started with {context['app_name']}:

1. Upload Your First Document
   Start by uploading a PDF, image, or scanned document to process

2. Create or Choose a Schema
   Define what data you want to extract, or use a pre-built template

3. Extract Data with AI
   Let our AI analyze your documents and extract structured data

4. Build Automated Workflows
   Create workflows to automate your document processing pipeline

What you can do with {context['app_name']}:
- Process Multiple Document Types: PDFs, images, scanned documents, and more
- Custom Extraction Schemas: Define exactly what data you need to extract
- Visual Workflow Builder: Drag-and-drop interface for building automation
- API Integration: Connect to your existing systems via REST API

Need help?
Check out our documentation or contact support if you have any questions.
We're here to help you get the most out of {context['app_name']}.

We're thrilled to have you on board!

---
This email was sent by {context['app_name']}.
        """.strip()

        # Build subject
        subject = f"Welcome to {context['app_name']}!"

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
