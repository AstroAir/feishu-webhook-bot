"""Tests for webhook trigger functionality."""

import hashlib
import hmac
from unittest.mock import MagicMock, patch

import pytest

from feishu_webhook_bot.core.config import BotConfig
from feishu_webhook_bot.tasks.manager import TaskManager
from feishu_webhook_bot.tasks.webhook_trigger import WebhookTriggerManager
from tests.mocks import MockScheduler


@pytest.fixture
def mock_config():
    """Create a mock bot configuration."""
    return BotConfig(
        webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
        tasks=[
            {
                "name": "webhook_task",
                "enabled": True,
                "interval": {"minutes": 5},
                "actions": [{"type": "python_code", "code": "context['executed'] = True"}],
            },
            {
                "name": "another_task",
                "enabled": True,
                "interval": {"minutes": 10},
                "actions": [{"type": "send_message", "webhook": "default", "message": "Hello"}],
            },
        ],
    )


@pytest.fixture
def task_manager(mock_config):
    """Create a task manager instance."""
    manager = TaskManager(
        config=mock_config,
        scheduler=MockScheduler(),
        plugin_manager=MagicMock(),
        clients={"default": MagicMock()},
    )
    manager.start()
    return manager


@pytest.fixture
def trigger_manager(task_manager):
    """Create a webhook trigger manager."""
    return WebhookTriggerManager(task_manager)


class TestWebhookTriggerRegistration:
    """Test webhook trigger registration."""

    def test_register_trigger(self, trigger_manager):
        """Test registering a webhook trigger."""
        config = trigger_manager.register_trigger(
            trigger_id="test-trigger",
            task_name="webhook_task",
            description="Test trigger",
        )

        assert config.task_name == "webhook_task"
        assert config.enabled is True
        assert "POST" in config.allowed_methods

    def test_register_trigger_with_secret(self, trigger_manager):
        """Test registering a trigger with secret."""
        config = trigger_manager.register_trigger(
            trigger_id="secure-trigger",
            task_name="webhook_task",
            secret="my-secret-key",
        )

        assert config.secret == "my-secret-key"

    def test_register_trigger_nonexistent_task(self, trigger_manager):
        """Test registering trigger for nonexistent task."""
        with pytest.raises(ValueError, match="Task not found"):
            trigger_manager.register_trigger(
                trigger_id="bad-trigger",
                task_name="nonexistent_task",
            )

    def test_unregister_trigger(self, trigger_manager):
        """Test unregistering a trigger."""
        trigger_manager.register_trigger("test-trigger", "webhook_task")

        result = trigger_manager.unregister_trigger("test-trigger")

        assert result is True
        assert trigger_manager.get_trigger("test-trigger") is None

    def test_unregister_nonexistent_trigger(self, trigger_manager):
        """Test unregistering nonexistent trigger."""
        result = trigger_manager.unregister_trigger("nonexistent")
        assert result is False

    def test_list_triggers(self, trigger_manager):
        """Test listing all triggers."""
        trigger_manager.register_trigger("trigger-1", "webhook_task")
        trigger_manager.register_trigger("trigger-2", "another_task")

        triggers = trigger_manager.list_triggers()

        assert len(triggers) == 2
        assert "trigger-1" in triggers
        assert "trigger-2" in triggers


class TestTriggerEnableDisable:
    """Test trigger enable/disable functionality."""

    def test_enable_trigger(self, trigger_manager):
        """Test enabling a trigger."""
        trigger_manager.register_trigger("test-trigger", "webhook_task")
        trigger_manager.disable_trigger("test-trigger")

        result = trigger_manager.enable_trigger("test-trigger")

        assert result is True
        assert trigger_manager.get_trigger("test-trigger").enabled is True

    def test_disable_trigger(self, trigger_manager):
        """Test disabling a trigger."""
        trigger_manager.register_trigger("test-trigger", "webhook_task")

        result = trigger_manager.disable_trigger("test-trigger")

        assert result is True
        assert trigger_manager.get_trigger("test-trigger").enabled is False

    def test_enable_nonexistent_trigger(self, trigger_manager):
        """Test enabling nonexistent trigger."""
        result = trigger_manager.enable_trigger("nonexistent")
        assert result is False


class TestSignatureVerification:
    """Test HMAC signature verification."""

    def test_verify_signature_valid(self, trigger_manager):
        """Test valid signature verification."""
        secret = "test-secret"
        trigger_manager.register_trigger("secure-trigger", "webhook_task", secret=secret)

        payload = b'{"event": "test"}'
        expected_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        result = trigger_manager.verify_signature("secure-trigger", payload, expected_sig)

        assert result is True

    def test_verify_signature_with_prefix(self, trigger_manager):
        """Test signature verification with sha256= prefix."""
        secret = "test-secret"
        trigger_manager.register_trigger("secure-trigger", "webhook_task", secret=secret)

        payload = b'{"event": "test"}'
        expected_sig = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        result = trigger_manager.verify_signature("secure-trigger", payload, expected_sig)

        assert result is True

    def test_verify_signature_invalid(self, trigger_manager):
        """Test invalid signature verification."""
        trigger_manager.register_trigger("secure-trigger", "webhook_task", secret="test-secret")

        result = trigger_manager.verify_signature(
            "secure-trigger", b'{"event": "test"}', "invalid-signature"
        )

        assert result is False

    def test_verify_signature_no_secret(self, trigger_manager):
        """Test signature verification when no secret configured."""
        trigger_manager.register_trigger("no-secret-trigger", "webhook_task")

        result = trigger_manager.verify_signature(
            "no-secret-trigger", b'{"event": "test"}', "any-signature"
        )

        # Should pass when no secret is configured
        assert result is True


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_within_limit(self, trigger_manager):
        """Test requests within rate limit."""
        trigger_manager.register_trigger("rate-limited", "webhook_task", rate_limit=10)

        for _ in range(5):
            assert trigger_manager.check_rate_limit("rate-limited") is True

    def test_rate_limit_exceeded(self, trigger_manager):
        """Test rate limit exceeded."""
        trigger_manager.register_trigger("rate-limited", "webhook_task", rate_limit=3)

        # Use up the limit
        for _ in range(3):
            trigger_manager.check_rate_limit("rate-limited")

        # Next request should be rejected
        assert trigger_manager.check_rate_limit("rate-limited") is False


class TestWebhookHandling:
    """Test webhook request handling."""

    def test_handle_webhook_success(self, trigger_manager):
        """Test successful webhook handling."""
        trigger_manager.register_trigger("test-trigger", "webhook_task")

        with patch.object(
            trigger_manager.task_manager,
            "run_task_with_params",
            return_value={"success": True, "duration": 0.1},
        ):
            result = trigger_manager.handle_webhook(
                trigger_id="test-trigger",
                method="POST",
                payload={"data": "test"},
            )

        assert result.success is True
        assert result.task_name == "webhook_task"
        assert result.execution_id is not None

    def test_handle_webhook_trigger_not_found(self, trigger_manager):
        """Test handling webhook for unknown trigger."""
        result = trigger_manager.handle_webhook(
            trigger_id="unknown",
            method="POST",
        )

        assert result.success is False
        assert "not found" in result.message.lower()

    def test_handle_webhook_trigger_disabled(self, trigger_manager):
        """Test handling webhook for disabled trigger."""
        trigger_manager.register_trigger("disabled-trigger", "webhook_task")
        trigger_manager.disable_trigger("disabled-trigger")

        result = trigger_manager.handle_webhook(
            trigger_id="disabled-trigger",
            method="POST",
        )

        assert result.success is False
        assert "disabled" in result.message.lower()

    def test_handle_webhook_method_not_allowed(self, trigger_manager):
        """Test handling webhook with wrong HTTP method."""
        trigger_manager.register_trigger("post-only", "webhook_task", allowed_methods=["POST"])

        result = trigger_manager.handle_webhook(
            trigger_id="post-only",
            method="GET",
        )

        assert result.success is False
        assert "not allowed" in result.message.lower()

    def test_handle_webhook_rate_limited(self, trigger_manager):
        """Test handling webhook when rate limited."""
        trigger_manager.register_trigger("rate-limited", "webhook_task", rate_limit=1)

        # First request succeeds
        with patch.object(
            trigger_manager.task_manager,
            "run_task_with_params",
            return_value={"success": True},
        ):
            trigger_manager.handle_webhook("rate-limited", "POST")

        # Second request is rate limited
        result = trigger_manager.handle_webhook("rate-limited", "POST")

        assert result.success is False
        assert "rate limit" in result.message.lower()

    def test_handle_webhook_invalid_signature(self, trigger_manager):
        """Test handling webhook with invalid signature."""
        trigger_manager.register_trigger("secure-trigger", "webhook_task", secret="secret")

        result = trigger_manager.handle_webhook(
            trigger_id="secure-trigger",
            method="POST",
            body=b'{"data": "test"}',
            headers={"X-Signature-256": "invalid"},
        )

        assert result.success is False
        assert "signature" in result.message.lower()

    def test_handle_webhook_payload_in_context(self, trigger_manager):
        """Test that payload is passed to task context."""
        trigger_manager.register_trigger("test-trigger", "webhook_task")

        captured_params = {}

        def capture_params(task_name, params=None, force=False):
            captured_params.update(params or {})
            return {"success": True}

        with patch.object(
            trigger_manager.task_manager,
            "run_task_with_params",
            side_effect=capture_params,
        ):
            trigger_manager.handle_webhook(
                trigger_id="test-trigger",
                method="POST",
                payload={"custom_data": "value"},
            )

        assert "custom_data" in captured_params
        assert captured_params["custom_data"] == "value"
        assert "_webhook_trigger" in captured_params


class TestAsyncExecution:
    """Test async webhook execution."""

    def test_handle_webhook_async(self, trigger_manager):
        """Test async webhook execution."""
        trigger_manager.register_trigger("async-trigger", "webhook_task")

        result = trigger_manager.handle_webhook(
            trigger_id="async-trigger",
            method="POST",
            async_execution=True,
        )

        assert result.success is True
        assert "started" in result.message.lower()
        assert result.execution_id is not None


class TestUtilities:
    """Test utility methods."""

    def test_generate_trigger_url(self, trigger_manager):
        """Test URL generation."""
        trigger_manager.register_trigger("my-trigger", "webhook_task")

        url = trigger_manager.generate_trigger_url("my-trigger", base_url="https://api.example.com")

        assert url == "https://api.example.com/api/tasks/webhook/my-trigger"

    def test_generate_secret(self, trigger_manager):
        """Test secret generation."""
        secret = trigger_manager.generate_secret()

        assert len(secret) == 64  # 32 bytes = 64 hex chars
        assert secret.isalnum()
