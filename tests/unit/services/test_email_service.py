"""Unit tests for EmailService with SendGrid."""

import pytest
from unittest.mock import patch, MagicMock

from app.services.email_service import (
    EmailService,
    EmailConfigurationError,
    EmailDeliveryError,
    EmailServiceError,
    get_email_service,
)


class TestEmailServiceInit:
    """Tests for EmailService initialization."""

    def test_init_with_explicit_config(self):
        """Verify explicit config overrides settings."""
        service = EmailService(
            sendgrid_api_key="SG.test_api_key",
            from_email="custom@example.com",
            from_name="Custom App",
        )

        assert service._api_key == "SG.test_api_key"
        assert service._from_email == "custom@example.com"
        assert service._from_name == "Custom App"

    def test_is_configured_returns_true_when_configured(self):
        """With api_key and from_email set, is_configured returns True."""
        service = EmailService(
            sendgrid_api_key="SG.test_api_key",
            from_email="noreply@example.com",
        )

        assert service.is_configured() is True

    def test_is_configured_returns_false_when_missing_api_key(self):
        """Empty api_key returns False."""
        service = EmailService(
            sendgrid_api_key="",
            from_email="noreply@example.com",
        )

        assert service.is_configured() is False

    def test_is_configured_returns_false_when_missing_from_email(self):
        """Empty from_email returns False."""
        service = EmailService(
            sendgrid_api_key="SG.test_api_key",
            from_email="",
        )

        assert service.is_configured() is False


class TestEmailServiceRenderTemplate:
    """Tests for _render_template method."""

    @pytest.fixture
    def configured_service(self):
        """Create a configured EmailService instance."""
        return EmailService(
            sendgrid_api_key="SG.test_api_key",
            from_email="noreply@example.com",
            from_name="Test App",
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
            sendgrid_api_key="SG.test_api_key",
            from_email="noreply@example.com",
            from_name="Test App",
        )

    @pytest.fixture
    def unconfigured_service(self):
        """Create an unconfigured EmailService instance."""
        return EmailService(
            sendgrid_api_key="",
            from_email="",
        )

    @pytest.mark.asyncio
    async def test_send_email_raises_when_not_configured(self, unconfigured_service):
        """Expect EmailConfigurationError when SendGrid not configured."""
        with pytest.raises(EmailConfigurationError, match="SendGrid is not configured"):
            await unconfigured_service._send_email(
                to_email="test@example.com",
                subject="Test Subject",
                html_content="<p>Test content</p>",
            )

    @pytest.mark.asyncio
    async def test_send_email_success(self, configured_service):
        """Mock SendGrid client, verify it's called correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.body = b""

        with patch.object(configured_service._client, 'send', return_value=mock_response) as mock_send:
            await configured_service._send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_content="<p>Test content</p>",
                text_content="Test content",
            )

            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            message = call_args[0]

            # Verify message structure
            assert message.from_email.email == "noreply@example.com"
            assert message.subject.subject == "Test Subject"

    @pytest.mark.asyncio
    async def test_send_invitation_email_success(self, configured_service):
        """Mock SendGrid client, verify full invitation email flow."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.body = b""

        with patch.object(configured_service._client, 'send', return_value=mock_response) as mock_send:
            await configured_service.send_invitation_email(
                to_email="newuser@example.com",
                invitation_url="https://app.example.com/invite?token=xyz789",
                invited_by="Jane Smith",
                tenant_name="Test Organization",
            )

            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            message = call_args[0]

            # Verify message was constructed correctly
            assert message.from_email.email == "noreply@example.com"
            assert "Test Organization" in message.subject.subject

    @pytest.mark.asyncio
    async def test_send_email_handles_api_error(self, configured_service):
        """Verify EmailDeliveryError raised on SendGrid API error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.body = b"Unauthorized"

        with patch.object(configured_service._client, 'send', return_value=mock_response):
            with pytest.raises(EmailDeliveryError, match="SendGrid API error"):
                await configured_service._send_email(
                    to_email="test@example.com",
                    subject="Test",
                    html_content="<p>Test</p>",
                )

    @pytest.mark.asyncio
    async def test_send_email_handles_exception(self, configured_service):
        """Verify EmailDeliveryError raised on exception."""
        with patch.object(configured_service._client, 'send', side_effect=Exception("Connection failed")):
            with pytest.raises(EmailDeliveryError, match="Failed to send email"):
                await configured_service._send_email(
                    to_email="test@example.com",
                    subject="Test",
                    html_content="<p>Test</p>",
                )


class TestEmailServicePasswordReset:
    """Tests for send_password_reset_email method."""

    @pytest.fixture
    def configured_service(self):
        """Create a fully configured EmailService instance."""
        return EmailService(
            sendgrid_api_key="SG.test_api_key",
            from_email="noreply@example.com",
            from_name="Test App",
        )

    def test_render_password_reset_template(self, configured_service):
        """Verify password reset template renders with correct variables."""
        context = {
            "app_name": "Test Application",
            "reset_url": "https://example.com/reset?token=abc123",
            "user_name": "John Doe",
            "expires_in_hours": 24,
            "current_year": 2025,
        }

        html_content = configured_service._render_template(
            "email/password_reset.html", context
        )

        # Verify key variables are present in rendered output
        assert "Test Application" in html_content
        assert "https://example.com/reset?token=abc123" in html_content
        assert "John Doe" in html_content
        assert "24 hours" in html_content

    @pytest.mark.asyncio
    async def test_send_password_reset_email_success(self, configured_service):
        """Mock SendGrid client, verify full password reset email flow."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.body = b""

        with patch.object(configured_service._client, 'send', return_value=mock_response) as mock_send:
            await configured_service.send_password_reset_email(
                to_email="user@example.com",
                reset_url="https://app.example.com/reset?token=xyz789",
                user_name="John Smith",
                expires_in_hours=24,
            )

            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            message = call_args[0]

            assert message.from_email.email == "noreply@example.com"
            assert "Reset Your Password" in message.subject.subject

    @pytest.mark.asyncio
    async def test_send_password_reset_email_without_user_name(self, configured_service):
        """Verify email sends successfully without user_name."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.body = b""

        with patch.object(configured_service._client, 'send', return_value=mock_response) as mock_send:
            await configured_service.send_password_reset_email(
                to_email="user@example.com",
                reset_url="https://app.example.com/reset?token=xyz789",
            )

            mock_send.assert_called_once()


class TestEmailServiceVerification:
    """Tests for send_verification_email method."""

    @pytest.fixture
    def configured_service(self):
        """Create a fully configured EmailService instance."""
        return EmailService(
            sendgrid_api_key="SG.test_api_key",
            from_email="noreply@example.com",
            from_name="Test App",
        )

    def test_render_verification_template(self, configured_service):
        """Verify verification template renders with correct variables."""
        context = {
            "app_name": "Test Application",
            "verification_url": "https://example.com/verify?token=abc123",
            "user_name": "Jane Doe",
            "expires_in_hours": 48,
            "current_year": 2025,
        }

        html_content = configured_service._render_template(
            "email/email_verification.html", context
        )

        # Verify key variables are present in rendered output
        assert "Test Application" in html_content
        assert "https://example.com/verify?token=abc123" in html_content
        assert "Jane Doe" in html_content
        assert "48 hours" in html_content

    @pytest.mark.asyncio
    async def test_send_verification_email_success(self, configured_service):
        """Mock SendGrid client, verify full verification email flow."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.body = b""

        with patch.object(configured_service._client, 'send', return_value=mock_response) as mock_send:
            await configured_service.send_verification_email(
                to_email="newuser@example.com",
                verification_url="https://app.example.com/verify?token=xyz789",
                user_name="Jane Smith",
                expires_in_hours=48,
            )

            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            message = call_args[0]

            assert message.from_email.email == "noreply@example.com"
            assert "Verify Your Email" in message.subject.subject

    @pytest.mark.asyncio
    async def test_send_verification_email_without_user_name(self, configured_service):
        """Verify email sends successfully without user_name."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.body = b""

        with patch.object(configured_service._client, 'send', return_value=mock_response) as mock_send:
            await configured_service.send_verification_email(
                to_email="user@example.com",
                verification_url="https://app.example.com/verify?token=xyz789",
            )

            mock_send.assert_called_once()


class TestEmailServiceWelcome:
    """Tests for send_welcome_email method."""

    @pytest.fixture
    def configured_service(self):
        """Create a fully configured EmailService instance."""
        return EmailService(
            sendgrid_api_key="SG.test_api_key",
            from_email="noreply@example.com",
            from_name="Test App",
        )

    def test_render_welcome_template(self, configured_service):
        """Verify welcome template renders with correct variables."""
        context = {
            "app_name": "Test Application",
            "login_url": "https://example.com/login",
            "user_name": "New User",
            "tenant_name": "Acme Corp",
            "current_year": 2025,
        }

        html_content = configured_service._render_template(
            "email/welcome.html", context
        )

        # Verify key variables are present in rendered output
        assert "Test Application" in html_content
        assert "https://example.com/login" in html_content
        assert "New User" in html_content
        assert "Acme Corp" in html_content

    @pytest.mark.asyncio
    async def test_send_welcome_email_success(self, configured_service):
        """Mock SendGrid client, verify full welcome email flow."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.body = b""

        with patch.object(configured_service._client, 'send', return_value=mock_response) as mock_send:
            await configured_service.send_welcome_email(
                to_email="newuser@example.com",
                login_url="https://app.example.com/login",
                user_name="New User",
                tenant_name="Test Organization",
            )

            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            message = call_args[0]

            assert message.from_email.email == "noreply@example.com"
            assert "Welcome" in message.subject.subject

    @pytest.mark.asyncio
    async def test_send_welcome_email_without_optional_fields(self, configured_service):
        """Verify email sends successfully without user_name and tenant_name."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.body = b""

        with patch.object(configured_service._client, 'send', return_value=mock_response) as mock_send:
            await configured_service.send_welcome_email(
                to_email="user@example.com",
                login_url="https://app.example.com/login",
            )

            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_welcome_email_with_tenant_only(self, configured_service):
        """Verify email sends successfully with tenant_name but no user_name."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.body = b""

        with patch.object(configured_service._client, 'send', return_value=mock_response) as mock_send:
            await configured_service.send_welcome_email(
                to_email="user@example.com",
                login_url="https://app.example.com/login",
                tenant_name="Test Corp",
            )

            mock_send.assert_called_once()


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
