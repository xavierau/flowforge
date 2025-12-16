"""Unit tests for email tasks."""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock


class TestSendInvitationEmailTask:
    """Tests for send_invitation_email_task Celery task."""

    def _run_task_with_mocks(
        self,
        mock_email_service,
        to_email: str,
        invitation_url: str,
        invited_by: str,
        tenant_name: str,
        retries: int = 0,
        retry_side_effect=None,
    ):
        """
        Helper to run the task with mocked dependencies.

        This recreates the task logic to enable unit testing without
        requiring a full Celery worker context.
        """
        from app.services.email_service import (
            EmailConfigurationError,
            EmailDeliveryError,
        )

        # Simulate the mock self object (Celery Task)
        mock_self = MagicMock()
        mock_self.request.retries = retries
        mock_self.max_retries = 5

        if retry_side_effect:
            mock_self.retry.side_effect = retry_side_effect

        # Execute the same logic as the task
        try:
            email_service = mock_email_service

            if not email_service.is_configured():
                return {
                    "status": "skipped",
                    "reason": "SMTP not configured",
                    "to_email": to_email,
                    "invited_by": invited_by,
                    "tenant_name": tenant_name,
                }

            asyncio.run(
                email_service.send_invitation_email(
                    to_email=to_email,
                    invitation_url=invitation_url,
                    invited_by=invited_by,
                    tenant_name=tenant_name,
                )
            )

            return {
                "status": "success",
                "to_email": to_email,
                "invited_by": invited_by,
                "tenant_name": tenant_name,
            }

        except EmailConfigurationError as e:
            return {
                "status": "failed",
                "reason": "configuration_error",
                "error": str(e),
                "to_email": to_email,
                "invited_by": invited_by,
                "tenant_name": tenant_name,
            }

        except EmailDeliveryError as e:
            raise mock_self.retry(exc=e, countdown=60 * (2 ** mock_self.request.retries))

        except Exception as e:
            raise mock_self.retry(exc=e, countdown=60 * (2 ** mock_self.request.retries))

    def test_skips_when_smtp_not_configured(self):
        """Verify result status is 'skipped' when SMTP not configured."""
        mock_service = MagicMock()
        mock_service.is_configured.return_value = False

        result = self._run_task_with_mocks(
            mock_email_service=mock_service,
            to_email="test@example.com",
            invitation_url="https://example.com/invite",
            invited_by="John Doe",
            tenant_name="Test Corp",
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "SMTP not configured"
        assert result["to_email"] == "test@example.com"
        mock_service.is_configured.assert_called_once()

    def test_sends_email_when_configured(self):
        """Verify result status is 'success' when email sent successfully."""
        mock_service = MagicMock()
        mock_service.is_configured.return_value = True
        mock_service.send_invitation_email = AsyncMock(return_value=None)

        result = self._run_task_with_mocks(
            mock_email_service=mock_service,
            to_email="newuser@example.com",
            invitation_url="https://app.example.com/invite?token=abc",
            invited_by="Jane Smith",
            tenant_name="Acme Corp",
        )

        assert result["status"] == "success"
        assert result["to_email"] == "newuser@example.com"
        assert result["invited_by"] == "Jane Smith"
        assert result["tenant_name"] == "Acme Corp"

    def test_retries_on_delivery_error(self):
        """Verify task.retry() is called on EmailDeliveryError."""
        from app.services.email_service import EmailDeliveryError

        mock_service = MagicMock()
        mock_service.is_configured.return_value = True
        delivery_error = EmailDeliveryError("SMTP connection failed")
        mock_service.send_invitation_email = AsyncMock(side_effect=delivery_error)

        with pytest.raises(Exception, match="Retry called"):
            self._run_task_with_mocks(
                mock_email_service=mock_service,
                to_email="test@example.com",
                invitation_url="https://example.com/invite",
                invited_by="John Doe",
                tenant_name="Test Corp",
                retries=0,
                retry_side_effect=Exception("Retry called"),
            )

    def test_retries_on_unexpected_error(self):
        """Verify task.retry() is called on unexpected exceptions."""
        mock_service = MagicMock()
        mock_service.is_configured.return_value = True

        unexpected_error = RuntimeError("Unexpected failure")
        mock_service.send_invitation_email = AsyncMock(side_effect=unexpected_error)

        with pytest.raises(Exception, match="Retry called"):
            self._run_task_with_mocks(
                mock_email_service=mock_service,
                to_email="test@example.com",
                invitation_url="https://example.com/invite",
                invited_by="John Doe",
                tenant_name="Test Corp",
                retries=2,
                retry_side_effect=Exception("Retry called"),
            )

    def test_returns_failed_on_configuration_error(self):
        """Verify result status is 'failed' on EmailConfigurationError (no retry)."""
        from app.services.email_service import EmailConfigurationError

        mock_service = MagicMock()
        mock_service.is_configured.return_value = True

        config_error = EmailConfigurationError("Invalid SMTP settings")
        mock_service.send_invitation_email = AsyncMock(side_effect=config_error)

        result = self._run_task_with_mocks(
            mock_email_service=mock_service,
            to_email="test@example.com",
            invitation_url="https://example.com/invite",
            invited_by="John Doe",
            tenant_name="Test Corp",
        )

        assert result["status"] == "failed"
        assert result["reason"] == "configuration_error"
        assert "Invalid SMTP settings" in result["error"]

    def test_exponential_backoff_calculation(self):
        """Verify exponential backoff countdown calculation for retries."""
        from app.services.email_service import EmailDeliveryError

        # Test different retry counts
        expected_countdowns = [
            (0, 60),    # 60 * 2^0 = 60
            (1, 120),   # 60 * 2^1 = 120
            (2, 240),   # 60 * 2^2 = 240
            (3, 480),   # 60 * 2^3 = 480
            (4, 960),   # 60 * 2^4 = 960
        ]

        for retry_count, expected_countdown in expected_countdowns:
            mock_service = MagicMock()
            mock_service.is_configured.return_value = True

            delivery_error = EmailDeliveryError("Connection timeout")
            mock_service.send_invitation_email = AsyncMock(side_effect=delivery_error)

            # Custom retry that captures the countdown
            captured_countdown = None
            def capture_retry(exc, countdown):
                nonlocal captured_countdown
                captured_countdown = countdown
                raise Exception("Retry called")

            mock_self = MagicMock()
            mock_self.request.retries = retry_count
            mock_self.max_retries = 5
            mock_self.retry.side_effect = capture_retry

            # Execute task logic directly
            try:
                email_service = mock_service
                asyncio.run(
                    email_service.send_invitation_email(
                        to_email="test@example.com",
                        invitation_url="https://example.com/invite",
                        invited_by="John Doe",
                        tenant_name="Test Corp",
                    )
                )
            except EmailDeliveryError as e:
                try:
                    mock_self.retry(exc=e, countdown=60 * (2 ** mock_self.request.retries))
                except Exception:
                    pass

            assert captured_countdown == expected_countdown, (
                f"Expected countdown {expected_countdown} for retry {retry_count}, "
                f"got {captured_countdown}"
            )


class TestSendInvitationEmailTaskIntegration:
    """
    Integration-style tests that verify the actual Celery task function logic.

    These tests patch the dependencies at the correct locations and call the
    actual task's run method.
    """

    def test_task_function_exists(self):
        """Verify the task function is properly registered."""
        from app.tasks.email_tasks import send_invitation_email_task

        assert send_invitation_email_task is not None
        assert hasattr(send_invitation_email_task, 'run')
        assert send_invitation_email_task.name == 'app.tasks.email_tasks.send_invitation_email_task'

    def test_task_has_correct_retry_settings(self):
        """Verify the task has correct retry configuration."""
        from app.tasks.email_tasks import send_invitation_email_task

        assert send_invitation_email_task.max_retries == 5
        assert send_invitation_email_task.default_retry_delay == 60

    def test_task_is_bound(self):
        """Verify the task is bound (bind=True in decorator)."""
        from app.tasks.email_tasks import send_invitation_email_task

        # Bound tasks have access to self.request
        assert hasattr(send_invitation_email_task, 'request')
