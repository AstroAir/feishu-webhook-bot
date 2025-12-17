"""Comprehensive tests for automation engine functionality.

Tests cover:
- AutomationEngine lifecycle (start/shutdown)
- Schedule-based triggers
- Event-based triggers
- Action execution (send_text, send_template, http_request)
- Context handling and merging
- Template rendering
- HTTP request execution with retry
- Provider/client lookup
- Target validation
- Condition matching
"""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock, patch

import pytest

from feishu_webhook_bot.automation.engine import AutomationEngine
from feishu_webhook_bot.core.config import (
    AutomationActionConfig,
    AutomationEventTriggerConfig,
    AutomationRule,
    AutomationScheduleConfig,
    AutomationTriggerConfig,
    HTTPClientConfig,
    HTTPRequestConfig,
    RetryPolicyConfig,
)
from feishu_webhook_bot.core.provider import BaseProvider, ProviderConfig
from feishu_webhook_bot.core.templates import RenderedTemplate

# ==============================================================================
# Test Fixtures
# ==============================================================================


class MockProvider(BaseProvider):
    """Mock provider for testing."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.sent_messages: list[tuple[str, str]] = []

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def send_message(self, message: Any, target: str) -> Any:
        return Mock(success=True)

    def send_text(self, text: str, target: str) -> Any:
        self.sent_messages.append((text, target))
        return Mock(success=True)

    def send_card(self, card: dict, target: str) -> Any:
        return Mock(success=True)

    def send_rich_text(
        self, title: str, content: list, target: str, language: str = "zh_cn"
    ) -> Any:
        return Mock(success=True)

    def send_image(self, image_key: str, target: str) -> Any:
        return Mock(success=True)


@pytest.fixture
def mock_scheduler():
    """Create mock scheduler."""
    scheduler = Mock()
    scheduler.add_job = Mock(return_value="job_123")
    scheduler.remove_job = Mock()
    return scheduler


@pytest.fixture
def mock_clients():
    """Create mock clients dictionary."""
    client = Mock()
    client.send_text = Mock()
    return {"default": client, "webhook1": Mock()}


@pytest.fixture
def mock_providers():
    """Create mock providers dictionary."""
    config = ProviderConfig(provider_type="test", name="provider1")
    provider = MockProvider(config)
    return {"provider1": provider}


@pytest.fixture
def mock_template_registry():
    """Create mock template registry."""
    registry = Mock()
    registry.render = Mock(
        return_value=RenderedTemplate(
            type="text",
            content="Rendered content",
        )
    )
    return registry


@pytest.fixture
def http_defaults():
    """Create default HTTP client config."""
    return HTTPClientConfig(
        timeout=30.0,
        retry=RetryPolicyConfig(
            max_attempts=3,
            backoff_seconds=1.0,
            backoff_multiplier=2.0,
            max_backoff_seconds=30.0,
        ),
    )


@pytest.fixture
def send_text_func():
    """Create mock send_text function."""
    return Mock()


@pytest.fixture
def send_rendered_func():
    """Create mock send_rendered function."""
    return Mock()


def create_schedule_trigger(mode: str = "interval", **kwargs) -> AutomationTriggerConfig:
    """Helper to create schedule trigger config."""
    arguments = kwargs or {"seconds": 60}
    return AutomationTriggerConfig(
        type="schedule",
        schedule=AutomationScheduleConfig(mode=mode, arguments=arguments),
    )


def create_event_trigger(
    event_type: str = "test.event", conditions: list | None = None
) -> AutomationTriggerConfig:
    """Helper to create event trigger config."""
    return AutomationTriggerConfig(
        type="event",
        event=AutomationEventTriggerConfig(event_type=event_type, conditions=conditions or []),
    )


@pytest.fixture
def simple_rule():
    """Create a simple automation rule."""
    return AutomationRule(
        name="test-rule",
        enabled=True,
        trigger=create_schedule_trigger(),
        actions=[
            AutomationActionConfig(
                type="send_text",
                text="Hello from automation!",
            ),
        ],
        default_webhooks=["default"],
        default_context={"key": "value"},
    )


@pytest.fixture
def event_rule():
    """Create an event-triggered automation rule."""
    return AutomationRule(
        name="event-rule",
        enabled=True,
        trigger=create_event_trigger("im.message.receive_v1"),
        actions=[
            AutomationActionConfig(
                type="send_text",
                text="Event received!",
            ),
        ],
        default_webhooks=["default"],
        default_context={},
    )


@pytest.fixture
def engine(
    simple_rule,
    mock_scheduler,
    mock_clients,
    mock_template_registry,
    http_defaults,
    send_text_func,
    send_rendered_func,
    mock_providers,
):
    """Create automation engine instance."""
    return AutomationEngine(
        rules=[simple_rule],
        scheduler=mock_scheduler,
        clients=mock_clients,
        template_registry=mock_template_registry,
        http_defaults=http_defaults,
        send_text=send_text_func,
        send_rendered=send_rendered_func,
        providers=mock_providers,
    )


# ==============================================================================
# Lifecycle Tests
# ==============================================================================


class TestAutomationEngineLifecycle:
    """Tests for automation engine lifecycle."""

    def test_engine_initialization(
        self,
        simple_rule,
        mock_scheduler,
        mock_clients,
        mock_template_registry,
        http_defaults,
        send_text_func,
        send_rendered_func,
        mock_providers,
    ):
        """Test engine initialization."""
        engine = AutomationEngine(
            rules=[simple_rule],
            scheduler=mock_scheduler,
            clients=mock_clients,
            template_registry=mock_template_registry,
            http_defaults=http_defaults,
            send_text=send_text_func,
            send_rendered=send_rendered_func,
            providers=mock_providers,
        )

        assert engine._rules == [simple_rule]
        assert engine._scheduler is mock_scheduler
        assert engine._clients == mock_clients
        assert engine._providers == mock_providers
        assert engine._registered_jobs == set()

    def test_engine_initialization_without_providers(
        self,
        simple_rule,
        mock_scheduler,
        mock_clients,
        mock_template_registry,
        http_defaults,
        send_text_func,
        send_rendered_func,
    ):
        """Test engine initialization without providers."""
        engine = AutomationEngine(
            rules=[simple_rule],
            scheduler=mock_scheduler,
            clients=mock_clients,
            template_registry=mock_template_registry,
            http_defaults=http_defaults,
            send_text=send_text_func,
            send_rendered=send_rendered_func,
        )

        assert engine._providers == {}

    def test_start_registers_scheduled_jobs(self, engine, mock_scheduler):
        """Test start() registers jobs for schedule-triggered rules."""
        engine.start()

        mock_scheduler.add_job.assert_called_once()
        assert "automation.test-rule" in str(mock_scheduler.add_job.call_args)

    def test_start_without_scheduler(
        self,
        simple_rule,
        mock_clients,
        mock_template_registry,
        http_defaults,
        send_text_func,
        send_rendered_func,
    ):
        """Test start() without scheduler logs warning for schedule rules."""
        engine = AutomationEngine(
            rules=[simple_rule],
            scheduler=None,
            clients=mock_clients,
            template_registry=mock_template_registry,
            http_defaults=http_defaults,
            send_text=send_text_func,
            send_rendered=send_rendered_func,
        )

        # Should not raise
        engine.start()

    def test_start_skips_disabled_rules(
        self,
        mock_scheduler,
        mock_clients,
        mock_template_registry,
        http_defaults,
        send_text_func,
        send_rendered_func,
    ):
        """Test start() skips disabled rules."""
        disabled_rule = AutomationRule(
            name="disabled-rule",
            enabled=False,
            trigger=AutomationTriggerConfig(
                type="schedule",
                schedule=AutomationScheduleConfig(mode="interval", arguments={"seconds": 30}),
            ),
            actions=[AutomationActionConfig(type="send_text", text="Test")],
        )

        engine = AutomationEngine(
            rules=[disabled_rule],
            scheduler=mock_scheduler,
            clients=mock_clients,
            template_registry=mock_template_registry,
            http_defaults=http_defaults,
            send_text=send_text_func,
            send_rendered=send_rendered_func,
        )

        engine.start()

        mock_scheduler.add_job.assert_not_called()

    def test_start_skips_event_rules(
        self,
        event_rule,
        mock_scheduler,
        mock_clients,
        mock_template_registry,
        http_defaults,
        send_text_func,
        send_rendered_func,
    ):
        """Test start() skips event-triggered rules."""
        engine = AutomationEngine(
            rules=[event_rule],
            scheduler=mock_scheduler,
            clients=mock_clients,
            template_registry=mock_template_registry,
            http_defaults=http_defaults,
            send_text=send_text_func,
            send_rendered=send_rendered_func,
        )

        engine.start()

        mock_scheduler.add_job.assert_not_called()

    def test_shutdown_removes_registered_jobs(self, engine, mock_scheduler):
        """Test shutdown() removes registered jobs."""
        engine.start()
        engine.shutdown()

        mock_scheduler.remove_job.assert_called_once()

    def test_shutdown_without_scheduler(
        self,
        simple_rule,
        mock_clients,
        mock_template_registry,
        http_defaults,
        send_text_func,
        send_rendered_func,
    ):
        """Test shutdown() without scheduler does nothing."""
        engine = AutomationEngine(
            rules=[simple_rule],
            scheduler=None,
            clients=mock_clients,
            template_registry=mock_template_registry,
            http_defaults=http_defaults,
            send_text=send_text_func,
            send_rendered=send_rendered_func,
        )

        # Should not raise
        engine.shutdown()


# ==============================================================================
# Event Handling Tests
# ==============================================================================


class TestEventHandling:
    """Tests for event handling."""

    def test_handle_event_triggers_matching_rule(
        self,
        event_rule,
        mock_scheduler,
        mock_clients,
        mock_template_registry,
        http_defaults,
        send_text_func,
        send_rendered_func,
    ):
        """Test handle_event triggers matching rules."""
        engine = AutomationEngine(
            rules=[event_rule],
            scheduler=mock_scheduler,
            clients=mock_clients,
            template_registry=mock_template_registry,
            http_defaults=http_defaults,
            send_text=send_text_func,
            send_rendered=send_rendered_func,
        )

        event_payload = {
            "header": {"event_type": "im.message.receive_v1"},
            "event": {"message": {"content": "Hello"}},
        }

        engine.handle_event(event_payload)

        send_text_func.assert_called_once()

    def test_handle_event_skips_non_matching_event_type(
        self,
        event_rule,
        mock_scheduler,
        mock_clients,
        mock_template_registry,
        http_defaults,
        send_text_func,
        send_rendered_func,
    ):
        """Test handle_event skips rules with non-matching event type."""
        engine = AutomationEngine(
            rules=[event_rule],
            scheduler=mock_scheduler,
            clients=mock_clients,
            template_registry=mock_template_registry,
            http_defaults=http_defaults,
            send_text=send_text_func,
            send_rendered=send_rendered_func,
        )

        event_payload = {
            "header": {"event_type": "different.event.type"},
        }

        engine.handle_event(event_payload)

        send_text_func.assert_not_called()

    def test_handle_event_skips_disabled_rules(
        self,
        mock_scheduler,
        mock_clients,
        mock_template_registry,
        http_defaults,
        send_text_func,
        send_rendered_func,
    ):
        """Test handle_event skips disabled rules."""
        disabled_rule = AutomationRule(
            name="disabled-event-rule",
            enabled=False,
            trigger=AutomationTriggerConfig(
                type="event",
                event=AutomationEventTriggerConfig(event_type="test.event"),
            ),
            actions=[AutomationActionConfig(type="send_text", text="Test")],
        )

        engine = AutomationEngine(
            rules=[disabled_rule],
            scheduler=mock_scheduler,
            clients=mock_clients,
            template_registry=mock_template_registry,
            http_defaults=http_defaults,
            send_text=send_text_func,
            send_rendered=send_rendered_func,
        )

        engine.handle_event({"header": {"event_type": "test.event"}})

        send_text_func.assert_not_called()

    def test_handle_event_skips_schedule_rules(self, engine, send_text_func):
        """Test handle_event skips schedule-triggered rules."""
        engine.handle_event({"header": {"event_type": "any"}})

        send_text_func.assert_not_called()


# ==============================================================================
# Action Execution Tests
# ==============================================================================


class TestActionExecution:
    """Tests for action execution."""

    def test_execute_rule_send_text(self, engine, send_text_func):
        """Test execute_rule with send_text action."""
        engine.execute_rule(engine._rules[0], event_payload=None)

        send_text_func.assert_called_once_with("Hello from automation!", "default")

    def test_execute_rule_with_event_payload(
        self,
        mock_scheduler,
        mock_clients,
        mock_template_registry,
        http_defaults,
        send_text_func,
        send_rendered_func,
    ):
        """Test execute_rule passes event payload to context."""
        rule = AutomationRule(
            name="context-rule",
            enabled=True,
            trigger=create_event_trigger(),
            actions=[
                AutomationActionConfig(
                    type="send_text",
                    text="Received: ${message}",
                ),
            ],
            default_webhooks=["default"],
            default_context={},
        )

        engine = AutomationEngine(
            rules=[rule],
            scheduler=mock_scheduler,
            clients=mock_clients,
            template_registry=mock_template_registry,
            http_defaults=http_defaults,
            send_text=send_text_func,
            send_rendered=send_rendered_func,
        )

        engine.execute_rule(rule, event_payload={"message": "Hello"})

        send_text_func.assert_called_once()

    def test_execute_rule_send_template(
        self,
        mock_scheduler,
        mock_clients,
        mock_template_registry,
        http_defaults,
        send_text_func,
        send_rendered_func,
    ):
        """Test execute_rule with send_template action."""
        rule = AutomationRule(
            name="template-rule",
            enabled=True,
            trigger=create_schedule_trigger(),
            actions=[
                AutomationActionConfig(
                    type="send_template",
                    template="test-template",
                ),
            ],
            default_webhooks=["default"],
        )

        engine = AutomationEngine(
            rules=[rule],
            scheduler=mock_scheduler,
            clients=mock_clients,
            template_registry=mock_template_registry,
            http_defaults=http_defaults,
            send_text=send_text_func,
            send_rendered=send_rendered_func,
        )

        engine.execute_rule(rule, event_payload=None)

        send_rendered_func.assert_called_once()
        mock_template_registry.render.assert_called_once()

    def test_execute_rule_template_not_found(
        self,
        mock_scheduler,
        mock_clients,
        http_defaults,
        send_text_func,
        send_rendered_func,
    ):
        """Test execute_rule handles missing template."""
        mock_registry = Mock()
        mock_registry.render = Mock(return_value=None)

        rule = AutomationRule(
            name="missing-template-rule",
            enabled=True,
            trigger=create_schedule_trigger(),
            actions=[
                AutomationActionConfig(
                    type="send_template",
                    template="nonexistent",
                ),
            ],
            default_webhooks=["default"],
        )

        engine = AutomationEngine(
            rules=[rule],
            scheduler=mock_scheduler,
            clients=mock_clients,
            template_registry=mock_registry,
            http_defaults=http_defaults,
            send_text=send_text_func,
            send_rendered=send_rendered_func,
        )

        # Should not raise, but log error
        engine.execute_rule(rule, event_payload=None)

    def test_execute_rule_action_config_validation(self):
        """Test AutomationActionConfig validates action type."""
        # AutomationActionConfig uses Literal type, so invalid types raise validation error
        with pytest.raises(Exception):  # Pydantic validation error
            AutomationActionConfig(type="unsupported_type")

    def test_execute_rule_send_text_empty_text_with_template_fallback(
        self,
        mock_scheduler,
        mock_clients,
        mock_template_registry,
        http_defaults,
        send_text_func,
        send_rendered_func,
    ):
        """Test send_text action falls back to template when text is None."""
        rule = AutomationRule(
            name="fallback-rule",
            enabled=True,
            trigger=create_schedule_trigger(),
            actions=[
                AutomationActionConfig(
                    type="send_text",
                    text=None,
                    template="test-template",
                ),
            ],
            default_webhooks=["default"],
        )

        engine = AutomationEngine(
            rules=[rule],
            scheduler=mock_scheduler,
            clients=mock_clients,
            template_registry=mock_template_registry,
            http_defaults=http_defaults,
            send_text=send_text_func,
            send_rendered=send_rendered_func,
        )

        engine.execute_rule(rule, event_payload=None)
        # Should use rendered template content
        send_text_func.assert_called()


# ==============================================================================
# HTTP Request Tests
# ==============================================================================


class TestHTTPRequestAction:
    """Tests for HTTP request actions."""

    @patch("httpx.Client")
    def test_http_request_action(
        self,
        mock_httpx_client,
        mock_scheduler,
        mock_clients,
        mock_template_registry,
        http_defaults,
        send_text_func,
        send_rendered_func,
    ):
        """Test HTTP request action execution."""
        mock_response = Mock()
        mock_response.json.return_value = {"result": "success"}
        mock_response.headers = {"content-type": "application/json"}
        mock_response.raise_for_status = Mock()

        mock_client_instance = Mock()
        mock_client_instance.request.return_value = mock_response
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=None)
        mock_httpx_client.return_value = mock_client_instance

        rule = AutomationRule(
            name="http-rule",
            enabled=True,
            trigger=create_schedule_trigger(),
            actions=[
                AutomationActionConfig(
                    type="http_request",
                    request=HTTPRequestConfig(
                        url="https://api.example.com/data",
                        method="GET",
                    ),
                ),
            ],
            default_webhooks=["default"],
        )

        engine = AutomationEngine(
            rules=[rule],
            scheduler=mock_scheduler,
            clients=mock_clients,
            template_registry=mock_template_registry,
            http_defaults=http_defaults,
            send_text=send_text_func,
            send_rendered=send_rendered_func,
        )

        engine.execute_rule(rule, event_payload=None)

        mock_client_instance.request.assert_called_once()

    @patch("httpx.Client")
    def test_http_request_saves_response(
        self,
        mock_httpx_client,
        mock_scheduler,
        mock_clients,
        mock_template_registry,
        http_defaults,
        send_text_func,
        send_rendered_func,
    ):
        """Test HTTP request saves response to context."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": "value"}
        mock_response.headers = {"content-type": "application/json"}
        mock_response.raise_for_status = Mock()

        mock_client_instance = Mock()
        mock_client_instance.request.return_value = mock_response
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=None)
        mock_httpx_client.return_value = mock_client_instance

        rule = AutomationRule(
            name="http-save-rule",
            enabled=True,
            trigger=create_schedule_trigger(),
            actions=[
                AutomationActionConfig(
                    type="http_request",
                    request=HTTPRequestConfig(
                        url="https://api.example.com/data",
                        method="GET",
                        save_as="api_response",
                    ),
                ),
                AutomationActionConfig(
                    type="send_text",
                    text="Got: ${api_response}",
                ),
            ],
            default_webhooks=["default"],
        )

        engine = AutomationEngine(
            rules=[rule],
            scheduler=mock_scheduler,
            clients=mock_clients,
            template_registry=mock_template_registry,
            http_defaults=http_defaults,
            send_text=send_text_func,
            send_rendered=send_rendered_func,
        )

        engine.execute_rule(rule, event_payload=None)

        # send_text should be called with the saved response
        send_text_func.assert_called()


# ==============================================================================
# Client/Provider Lookup Tests
# ==============================================================================


class TestClientProviderLookup:
    """Tests for client/provider lookup."""

    def test_get_client_or_provider_from_providers(self, engine, mock_providers):
        """Test _get_client_or_provider finds provider first."""
        result = engine._get_client_or_provider("provider1")
        assert result is mock_providers["provider1"]

    def test_get_client_or_provider_from_clients(self, engine, mock_clients):
        """Test _get_client_or_provider falls back to clients."""
        result = engine._get_client_or_provider("default")
        assert result is mock_clients["default"]

    def test_get_client_or_provider_not_found(self, engine):
        """Test _get_client_or_provider returns None for unknown name."""
        result = engine._get_client_or_provider("nonexistent")
        assert result is None

    def test_validate_targets_success(self, engine):
        """Test _validate_targets with valid targets."""
        targets = engine._validate_targets(["default", "provider1"], "test-rule")
        assert targets == ["default", "provider1"]

    def test_validate_targets_missing(self, engine):
        """Test _validate_targets raises for missing targets."""
        with pytest.raises(ValueError, match="Unknown webhook/provider"):
            engine._validate_targets(["nonexistent"], "test-rule")


# ==============================================================================
# Condition Matching Tests
# ==============================================================================


class TestConditionMatching:
    """Tests for condition matching."""

    def test_extract_simple_path(self, engine):
        """Test _extract with simple path."""
        payload = {"key": "value"}
        result = engine._extract(payload, "key")
        assert result == "value"

    def test_extract_nested_path(self, engine):
        """Test _extract with nested path."""
        payload = {"header": {"event_type": "test"}}
        result = engine._extract(payload, "header.event_type")
        assert result == "test"

    def test_extract_missing_path(self, engine):
        """Test _extract with missing path."""
        payload = {"key": "value"}
        result = engine._extract(payload, "missing.path")
        assert result is None

    def test_conditions_match_equals(self, engine):
        """Test _conditions_match with equals condition."""

        class MockCondition:
            path = "status"
            equals = "active"
            contains = None

        conditions = [MockCondition()]
        payload = {"status": "active"}

        result = engine._conditions_match(conditions, payload)
        assert result is True

    def test_conditions_match_equals_fail(self, engine):
        """Test _conditions_match fails with non-matching equals."""

        class MockCondition:
            path = "status"
            equals = "active"
            contains = None

        conditions = [MockCondition()]
        payload = {"status": "inactive"}

        result = engine._conditions_match(conditions, payload)
        assert result is False

    def test_conditions_match_contains(self, engine):
        """Test _conditions_match with contains condition."""

        class MockCondition:
            path = "message"
            equals = None
            contains = "hello"

        conditions = [MockCondition()]
        payload = {"message": "say hello world"}

        result = engine._conditions_match(conditions, payload)
        assert result is True

    def test_conditions_match_contains_fail(self, engine):
        """Test _conditions_match fails with non-matching contains."""

        class MockCondition:
            path = "message"
            equals = None
            contains = "hello"

        conditions = [MockCondition()]
        payload = {"message": "goodbye world"}

        result = engine._conditions_match(conditions, payload)
        assert result is False

    def test_conditions_match_empty(self, engine):
        """Test _conditions_match with empty conditions."""
        result = engine._conditions_match([], {"any": "data"})
        assert result is True


# ==============================================================================
# Context Handling Tests
# ==============================================================================


class TestContextHandling:
    """Tests for context handling."""

    def test_merge_context(self, engine):
        """Test _merge_context merges base and override."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}

        result = engine._merge_context(base, override)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_interpolate_string(self, engine):
        """Test _interpolate with string template."""
        result = engine._interpolate("Hello $name!", {"name": "World"})
        assert result == "Hello World!"

    def test_interpolate_non_string(self, engine):
        """Test _interpolate with non-string returns unchanged."""
        result = engine._interpolate(123, {"name": "World"})
        assert result == 123

    def test_interpolate_mapping_dict(self, engine):
        """Test _interpolate_mapping with dict."""
        value = {"key": "$value", "other": "static"}
        context = {"value": "dynamic"}

        result = engine._interpolate_mapping(value, context)

        assert result == {"key": "dynamic", "other": "static"}

    def test_interpolate_mapping_list(self, engine):
        """Test _interpolate_mapping with list."""
        value = ["$first", "$second", "static"]
        context = {"first": "a", "second": "b"}

        result = engine._interpolate_mapping(value, context)

        assert result == ["a", "b", "static"]


# ==============================================================================
# Template Rendering Tests
# ==============================================================================


class TestTemplateRendering:
    """Tests for template rendering."""

    def test_render_template_success(self, engine, mock_template_registry):
        """Test _render_template with valid template."""
        result = engine._render_template("test-template", {"key": "value"})

        assert result is not None
        assert result.content == "Rendered content"
        mock_template_registry.render.assert_called_once()

    def test_render_template_no_registry(
        self,
        simple_rule,
        mock_scheduler,
        mock_clients,
        http_defaults,
        send_text_func,
        send_rendered_func,
    ):
        """Test _render_template without registry returns None."""
        engine = AutomationEngine(
            rules=[simple_rule],
            scheduler=mock_scheduler,
            clients=mock_clients,
            template_registry=None,
            http_defaults=http_defaults,
            send_text=send_text_func,
            send_rendered=send_rendered_func,
        )

        result = engine._render_template("any-template", {})

        assert result is None

    def test_send_text_with_template_override(
        self,
        mock_scheduler,
        mock_clients,
        mock_template_registry,
        http_defaults,
        send_text_func,
        send_rendered_func,
    ):
        """Test send_text action uses template when specified."""
        rule = AutomationRule(
            name="text-with-template",
            enabled=True,
            trigger=create_schedule_trigger(),
            actions=[
                AutomationActionConfig(
                    type="send_text",
                    text="Fallback text",
                    template="test-template",
                ),
            ],
            default_webhooks=["default"],
        )

        engine = AutomationEngine(
            rules=[rule],
            scheduler=mock_scheduler,
            clients=mock_clients,
            template_registry=mock_template_registry,
            http_defaults=http_defaults,
            send_text=send_text_func,
            send_rendered=send_rendered_func,
        )

        engine.execute_rule(rule, event_payload=None)

        # Should use rendered template content, not fallback
        send_text_func.assert_called_once_with("Rendered content", "default")


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestAutomationEngineIntegration:
    """Integration tests for automation engine."""

    def test_full_schedule_workflow(
        self,
        mock_scheduler,
        mock_clients,
        mock_template_registry,
        http_defaults,
        send_text_func,
        send_rendered_func,
    ):
        """Test full schedule-triggered workflow."""
        rule = AutomationRule(
            name="integration-rule",
            enabled=True,
            trigger=AutomationTriggerConfig(
                type="schedule",
                schedule=AutomationScheduleConfig(
                    mode="cron",
                    arguments={"hour": "9", "minute": "0"},
                ),
            ),
            actions=[
                AutomationActionConfig(
                    type="send_text",
                    text="Good morning!",
                ),
            ],
            default_webhooks=["default"],
        )

        engine = AutomationEngine(
            rules=[rule],
            scheduler=mock_scheduler,
            clients=mock_clients,
            template_registry=mock_template_registry,
            http_defaults=http_defaults,
            send_text=send_text_func,
            send_rendered=send_rendered_func,
        )

        # Start engine
        engine.start()
        assert len(engine._registered_jobs) == 1

        # Manually execute rule
        engine.execute_rule(rule, event_payload=None)
        send_text_func.assert_called_once()

        # Shutdown
        engine.shutdown()
        assert len(engine._registered_jobs) == 0

    def test_full_event_workflow(
        self,
        mock_scheduler,
        mock_clients,
        mock_template_registry,
        http_defaults,
        send_text_func,
        send_rendered_func,
    ):
        """Test full event-triggered workflow."""
        rule = AutomationRule(
            name="event-integration-rule",
            enabled=True,
            trigger=AutomationTriggerConfig(
                type="event",
                event=AutomationEventTriggerConfig(
                    event_type="im.message.receive_v1",
                    conditions=[],
                ),
            ),
            actions=[
                AutomationActionConfig(
                    type="send_text",
                    text="Message received: ${event}",
                ),
            ],
            default_webhooks=["default"],
        )

        engine = AutomationEngine(
            rules=[rule],
            scheduler=mock_scheduler,
            clients=mock_clients,
            template_registry=mock_template_registry,
            http_defaults=http_defaults,
            send_text=send_text_func,
            send_rendered=send_rendered_func,
        )

        # Simulate event
        event_payload = {
            "header": {"event_type": "im.message.receive_v1"},
            "event": {"message": {"content": "Hello"}},
        }

        engine.handle_event(event_payload)

        send_text_func.assert_called_once()
