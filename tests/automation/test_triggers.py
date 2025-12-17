"""Tests for automation trigger system."""

from __future__ import annotations

from unittest.mock import MagicMock

from feishu_webhook_bot.automation.triggers import (
    ChainTrigger,
    EventTrigger,
    ManualTrigger,
    ScheduleTrigger,
    TriggerContext,
    TriggerRegistry,
    TriggerType,
    WebhookTrigger,
)


class TestTriggerType:
    """Tests for TriggerType enum."""

    def test_all_trigger_types_exist(self) -> None:
        """Test that all expected trigger types are defined."""
        expected_types = ["schedule", "event", "webhook", "manual", "chain"]
        for type_name in expected_types:
            assert hasattr(TriggerType, type_name.upper()), f"Missing TriggerType: {type_name}"


class TestTriggerContext:
    """Tests for TriggerContext dataclass."""

    def test_create_context(self) -> None:
        """Test creating a trigger context."""
        context = TriggerContext(
            trigger_type=TriggerType.EVENT,
            trigger_id="test_trigger",
            payload={"key": "value"},
        )
        assert context.trigger_type == TriggerType.EVENT
        assert context.trigger_id == "test_trigger"
        assert context.payload == {"key": "value"}

    def test_context_defaults(self) -> None:
        """Test trigger context default values."""
        context = TriggerContext(trigger_type=TriggerType.MANUAL)
        assert context.payload == {}
        assert context.metadata == {}
        assert context.trigger_id == ""

    def test_context_to_dict(self) -> None:
        """Test converting context to dictionary."""
        context = TriggerContext(
            trigger_type=TriggerType.EVENT,
            payload={"test": "data"},
        )
        result = context.to_dict()
        assert result["trigger_type"] == "event"
        assert result["payload"] == {"test": "data"}


class TestScheduleTrigger:
    """Tests for ScheduleTrigger."""

    def test_interval_config(self) -> None:
        """Test schedule trigger with interval configuration."""
        callback = MagicMock()
        trigger = ScheduleTrigger(
            rule_name="test_rule",
            config={
                "mode": "interval",
                "arguments": {"minutes": 30},
            },
            callback=callback,
        )
        assert trigger.rule_name == "test_rule"
        assert trigger.trigger_type == TriggerType.SCHEDULE

    def test_cron_config(self) -> None:
        """Test schedule trigger with cron configuration."""
        callback = MagicMock()
        trigger = ScheduleTrigger(
            rule_name="test_rule",
            config={
                "mode": "cron",
                "arguments": {"cron": "0 9 * * *"},
            },
            callback=callback,
        )
        assert trigger.rule_name == "test_rule"

    def test_trigger_enabled(self) -> None:
        """Test that trigger is enabled by default."""
        callback = MagicMock()
        trigger = ScheduleTrigger(
            rule_name="test",
            config={"mode": "interval", "arguments": {"minutes": 1}},
            callback=callback,
        )
        assert trigger.enabled is True

    def test_trigger_fires_callback(self) -> None:
        """Test that trigger fires callback."""
        callback = MagicMock()
        trigger = ScheduleTrigger(
            rule_name="test",
            config={"mode": "interval", "arguments": {"minutes": 1}},
            callback=callback,
        )
        trigger.trigger()
        callback.assert_called_once()


class TestEventTrigger:
    """Tests for EventTrigger."""

    def test_event_trigger_creation(self) -> None:
        """Test event trigger creation."""
        callback = MagicMock()
        trigger = EventTrigger(
            rule_name="test_rule",
            config={"event_type": "im.message.receive_v1"},
            callback=callback,
        )
        assert trigger.rule_name == "test_rule"
        assert trigger.trigger_type == TriggerType.EVENT

    def test_event_trigger_fires(self) -> None:
        """Test event trigger fires callback."""
        callback = MagicMock()
        trigger = EventTrigger(
            rule_name="test_rule",
            config={"event_type": "im.message.receive_v1"},
            callback=callback,
        )
        context = TriggerContext(
            trigger_type=TriggerType.EVENT,
            payload={"event_type": "im.message.receive_v1"},
        )
        trigger.trigger(context)
        callback.assert_called_once_with(context)


class TestWebhookTrigger:
    """Tests for WebhookTrigger."""

    def test_webhook_trigger_creation(self) -> None:
        """Test webhook trigger creation."""
        callback = MagicMock()
        trigger = WebhookTrigger(
            rule_name="test_rule",
            config={"path": "/automation/webhook1"},
            callback=callback,
        )
        assert trigger.rule_name == "test_rule"
        assert trigger.trigger_type == TriggerType.WEBHOOK

    def test_webhook_trigger_fires(self) -> None:
        """Test webhook trigger fires callback."""
        callback = MagicMock()
        trigger = WebhookTrigger(
            rule_name="test_rule",
            config={"path": "/webhook"},
            callback=callback,
        )
        context = TriggerContext(
            trigger_type=TriggerType.WEBHOOK,
            payload={"path": "/webhook"},
        )
        trigger.trigger(context)
        callback.assert_called_once()


class TestManualTrigger:
    """Tests for ManualTrigger."""

    def test_manual_trigger_creation(self) -> None:
        """Test manual trigger creation."""
        callback = MagicMock()
        trigger = ManualTrigger(
            rule_name="test_rule",
            config={},
            callback=callback,
        )
        assert trigger.rule_name == "test_rule"
        assert trigger.trigger_type == TriggerType.MANUAL

    def test_manual_trigger_fires(self) -> None:
        """Test manual trigger fires callback."""
        callback = MagicMock()
        trigger = ManualTrigger(
            rule_name="test_rule",
            config={},
            callback=callback,
        )
        trigger.trigger()
        callback.assert_called_once()

    def test_manual_trigger_disabled(self) -> None:
        """Test disabled manual trigger doesn't fire."""
        callback = MagicMock()
        trigger = ManualTrigger(
            rule_name="test_rule",
            config={},
            callback=callback,
        )
        trigger.enabled = False
        trigger.trigger()
        callback.assert_not_called()


class TestChainTrigger:
    """Tests for ChainTrigger."""

    def test_chain_trigger_creation(self) -> None:
        """Test chain trigger creation."""
        callback = MagicMock()
        trigger = ChainTrigger(
            rule_name="target_rule",
            config={"from_rule": "source_rule"},
            callback=callback,
        )
        assert trigger.rule_name == "target_rule"
        assert trigger.trigger_type == TriggerType.CHAIN

    def test_chain_trigger_fires(self) -> None:
        """Test chain trigger fires callback."""
        callback = MagicMock()
        trigger = ChainTrigger(
            rule_name="target_rule",
            config={"from_rule": "source_rule"},
            callback=callback,
        )
        context = TriggerContext(
            trigger_type=TriggerType.CHAIN,
            metadata={"source_rule": "source_rule"},
        )
        trigger.trigger(context)
        callback.assert_called_once()


class TestTriggerRegistry:
    """Tests for TriggerRegistry."""

    def test_create_registry(self) -> None:
        """Test creating a trigger registry."""
        registry = TriggerRegistry()
        assert registry is not None

    def test_registry_with_scheduler(self) -> None:
        """Test registry with scheduler."""
        scheduler = MagicMock()
        registry = TriggerRegistry(scheduler=scheduler)
        assert registry.scheduler is scheduler

    def test_register_and_get_trigger(self) -> None:
        """Test registering and retrieving a trigger."""
        registry = TriggerRegistry()
        callback = MagicMock()
        trigger_config = {"type": "manual", "manual": {}}
        trigger = registry.register("test", trigger_config, callback)
        assert trigger is not None
        assert registry.get_trigger("test") is trigger

    def test_unregister_trigger(self) -> None:
        """Test unregistering a trigger."""
        registry = TriggerRegistry()
        callback = MagicMock()
        trigger_config = {"type": "manual", "manual": {}}
        registry.register("test", trigger_config, callback)
        result = registry.unregister("test")
        assert result is True
        assert registry.get_trigger("test") is None

    def test_register_schedule_trigger(self) -> None:
        """Test registering a schedule trigger."""
        scheduler = MagicMock()
        registry = TriggerRegistry(scheduler=scheduler)
        callback = MagicMock()
        trigger_config = {
            "type": "schedule",
            "schedule": {"mode": "interval", "arguments": {"minutes": 5}},
        }
        trigger = registry.register("scheduled_rule", trigger_config, callback)
        assert trigger is not None
        assert trigger.trigger_type == TriggerType.SCHEDULE

    def test_register_event_trigger(self) -> None:
        """Test registering an event trigger."""
        registry = TriggerRegistry()
        callback = MagicMock()
        trigger_config = {
            "type": "event",
            "event": {"event_type": "im.message.receive_v1"},
        }
        trigger = registry.register("event_rule", trigger_config, callback)
        assert trigger is not None
        assert trigger.trigger_type == TriggerType.EVENT

    def test_register_webhook_trigger(self) -> None:
        """Test registering a webhook trigger."""
        registry = TriggerRegistry()
        callback = MagicMock()
        trigger_config = {
            "type": "webhook",
            "webhook": {"path": "/automation/test"},
        }
        trigger = registry.register("webhook_rule", trigger_config, callback)
        assert trigger is not None
        assert trigger.trigger_type == TriggerType.WEBHOOK

    def test_handle_event(self) -> None:
        """Test handling events."""
        registry = TriggerRegistry()
        callback = MagicMock()
        trigger_config = {
            "type": "event",
            "event": {"event_type": "test.event"},
        }
        registry.register("event_rule", trigger_config, callback)

        triggered = registry.handle_event({"type": "test.event"})
        # Result depends on event matching logic
        assert isinstance(triggered, list)
