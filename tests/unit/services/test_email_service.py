"""Unit tests for EmailService."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.email_service import (
    EmailService,
    EmailConfigurationError,
    EmailDeliveryError,
    EmailServiceError,
    get_email_service,
    _email_service,
)


class TestEmailServiceInit:
    """Tests for EmailService initialization."""

    def test_init_with_explicit_config(self):
        """Verify explicit config overrides settings."""
        service = EmailService(
            smtp_host="custom.smtp.com",
            smtp_port=2525,
            smtp_user="custom_user",
            smtp_password="custom_pass",
            smtp_from_email="custom@example.com",
            smtp_from_name="Custom App",
            smtp_use_tls=False,
        )

        assert service._smtp_host == "custom.smtp.com"
        assert service._smtp_port == 2525
        assert service._smtp_user == "custom_user"
        assert service._smtp_password == "custom_pass"
        assert service._smtp_from_email == "custom@example.com"
        assert service._smtp_from_name == "Custom App"
        assert service._smtp_use_tls is False

    def test_is_configured_returns_true_when_configured(self):
        """With host, port, from_email set, is_configured returns True."""
        service = EmailService(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_from_email="noreply@example.com",
        )

        assert service.is_configured() is True

    def test_is_configured_returns_false_when_missing_host(self):
        """Empty smtp_host returns False."""
        service = EmailService(
            smtp_host="",
            smtp_port=587,
            smtp_from_email="noreply@example.com",
        )

        assert service.is_configured() is False

    def test_is_configured_returns_false_when_missing_from_email(self):
        """Empty from_email returns False."""
        service = EmailService(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_from_email="",
        )

        assert service.is_configured() is False

    def test_is_configured_returns_false_when_missing_port(self):
        """Port 0 or None returns False."""
        service = EmailService(
            smtp_host="smtp.example.com",
            smtp_port=0,
            smtp_from_email="noreply@example.com",
        )

        assert service.is_configured() is False


class TestEmailServiceRenderTemplate:
    """Tests for _render_template method."""

    @pytest.fixture
    def configured_service(self):
        """Create a configured EmailService instance."""
        return EmailService(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_from_email="noreply@example.com",
            smtp_from_name="Test App",
        )

    def test_render_invitation_template(self, configured_service):
        """Verify template renders with correct variables."""
        context = {
            "app_name": "Test Application",
            "invitation_url": "https://example.com/invite?token=abc123",
            "invited_by": "John Doe",
            "tenant_name": "Acme Corp",
            "current_year": 2025,
        }

        html_content = configured_service._render_template(
            "email/invitation.html", context
        )

        # Verify key variables are present in rendered output
        assert "Test Application" in html_content
        assert "https://example.com/invite?token=abc123" in html_content
        assert "John Doe" in html_content
        assert "Acme Corp" in html_content

    def test_render_template_raises_on_missing_template(self, configured_service):
        """Raises EmailServiceError when template not found."""
        with pytest.raises(EmailServiceError, match="template not found"):
            configured_service._render_template("email/nonexistent.html", {})


class TestEmailServiceSendEmail:
    """Tests for _send_email and send_invitation_email methods."""

    @pytest.fixture
    def configured_service(self):
        """Create a fully configured EmailService instance."""
        return EmailService(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="password123",
            smtp_from_email="noreply@example.com",
            smtp_from_name="Test App",
            smtp_use_tls=True,
        )

    @pytest.fixture
    def unconfigured_service(self):
        """Create an unconfigured EmailService instance."""
        return EmailService(
            smtp_host="",
            smtp_port=0,
            smtp_from_email="",
        )

    @pytest.mark.asyncio
    async def test_send_email_raises_when_not_configured(self, unconfigured_service):
        """Expect EmailConfigurationError when SMTP not configured."""
        with pytest.raises(EmailConfigurationError, match="SMTP is not configured"):
            await unconfigured_service._send_email(
                to_email="test@example.com",
                subject="Test Subject",
                html_content="<p>Test content</p>",
            )

    @pytest.mark.asyncio
    async def test_send_email_success(self, configured_service):
        """Mock aiosmtplib.send, verify it's called with correct params."""
        with patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            await configured_service._send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_content="<p>Test content</p>",
                text_content="Test content",
            )

            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args[1]

            assert call_kwargs["hostname"] == "smtp.example.com"
            assert call_kwargs["port"] == 587
            assert call_kwargs["username"] == "user@example.com"
            assert call_kwargs["password"] == "password123"
            assert call_kwargs["start_tls"] is True

    @pytest.mark.asyncio
    async def test_send_email_without_tls(self):
        """Verify email sending without TLS."""
        service = EmailService(
            smtp_host="smtp.example.com",
            smtp_port=25,
            smtp_from_email="noreply@example.com",
            smtp_use_tls=False,
        )

        with patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            await service._send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_content="<p>Test content</p>",
            )

            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args[1]

            # start_tls should not be in kwargs when not using TLS
            assert "start_tls" not in call_kwargs

    @pytest.mark.asyncio
    async def test_send_invitation_email_success(self, configured_service):
        """Mock aiosmtplib.send, verify full invitation email flow."""
        with patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            await configured_service.send_invitation_email(
                to_email="newuser@example.com",
                invitation_url="https://app.example.com/invite?token=xyz789",
                invited_by="Jane Smith",
                tenant_name="Test Organization",
            )

            mock_send.assert_called_once()

            # Verify the message was constructed correctly
            call_args = mock_send.call_args[0]
            message = call_args[0]

            assert message["To"] == "newuser@example.com"
            assert "Test Organization" in message["Subject"]
            assert "Test App <noreply@example.com>" in message["From"]

    @pytest.mark.asyncio
    async def test_send_email_handles_authentication_error(self, configured_service):
        """Verify EmailDeliveryError raised on SMTP authentication failure."""
        import aiosmtplib

        with patch(
            "app.services.email_service.aiosmtplib.send",
            new_callable=AsyncMock,
            side_effect=aiosmtplib.SMTPAuthenticationError(535, "Authentication failed"),
        ):
            with pytest.raises(EmailDeliveryError, match="authentication failed"):
                await configured_service._send_email(
                    to_email="test@example.com",
                    subject="Test",
                    html_content="<p>Test</p>",
                )

    @pytest.mark.asyncio
    async def test_send_email_handles_connection_error(self, configured_service):
        """Verify EmailDeliveryError raised on SMTP connection failure."""
        import aiosmtplib

        with patch(
            "app.services.email_service.aiosmtplib.send",
            new_callable=AsyncMock,
            side_effect=aiosmtplib.SMTPConnectError("Connection refused"),
        ):
            with pytest.raises(EmailDeliveryError, match="Failed to connect"):
                await configured_service._send_email(
                    to_email="test@example.com",
                    subject="Test",
                    html_content="<p>Test</p>",
                )

    @pytest.mark.asyncio
    async def test_send_email_handles_smtp_exception(self, configured_service):
        """Verify EmailDeliveryError raised on general SMTP error."""
        import aiosmtplib

        with patch(
            "app.services.email_service.aiosmtplib.send",
            new_callable=AsyncMock,
            side_effect=aiosmtplib.SMTPException("Unknown SMTP error"),
        ):
            with pytest.raises(EmailDeliveryError, match="SMTP error"):
                await configured_service._send_email(
                    to_email="test@example.com",
                    subject="Test",
                    html_content="<p>Test</p>",
                )


class TestEmailServiceSingleton:
    """Tests for get_email_service singleton function."""

    def test_get_email_service_returns_singleton(self):
        """Reset _email_service, verify same instance returned."""
        import app.services.email_service as email_module

        # Reset the singleton
        email_module._email_service = None

        # Get first instance
        service1 = get_email_service()

        # Get second instance
        service2 = get_email_service()

        # Should be the same instance
        assert service1 is service2

        # Clean up: reset singleton after test
        email_module._email_service = None

    def test_get_email_service_returns_email_service_instance(self):
        """Verify get_email_service returns EmailService type."""
        import app.services.email_service as email_module

        # Reset the singleton
        email_module._email_service = None

        service = get_email_service()

        assert isinstance(service, EmailService)

        # Clean up
        email_module._email_service = None
