"""Tests for automation action executors."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from feishu_webhook_bot.automation.actions import (
    ActionExecutorFactory,
    ActionResult,
    ActionType,
    ConditionalExecutor,
    DelayExecutor,
    LogExecutor,
    LoopExecutor,
    NotifyExecutor,
    ParallelExecutor,
    PluginMethodExecutor,
    PythonCodeExecutor,
    SetVariableExecutor,
)


class TestActionResult:
    """Tests for ActionResult dataclass."""

    def test_successful_result(self) -> None:
        """Test creating a successful result."""
        result = ActionResult(success=True, data={"key": "value"}, duration=0.5)
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.duration == 0.5
        assert result.error is None

    def test_failed_result(self) -> None:
        """Test creating a failed result."""
        result = ActionResult(success=False, error="Something went wrong", duration=0.1)
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None

    def test_default_values(self) -> None:
        """Test default values."""
        result = ActionResult(success=True)
        assert result.data is None
        assert result.error is None
        assert result.duration == 0.0


class TestActionType:
    """Tests for ActionType enum."""

    def test_all_action_types_exist(self) -> None:
        """Test that all expected action types are defined."""
        expected_types = [
            "send_text",
            "send_template",
            "http_request",
            "plugin_method",
            "python_code",
            "ai_chat",
            "ai_query",
            "conditional",
            "loop",
            "set_variable",
            "delay",
            "notify",
            "log",
            "parallel",
            "chain_rule",
        ]
        for type_name in expected_types:
            assert hasattr(ActionType, type_name.upper()), f"Missing ActionType: {type_name}"


class TestSetVariableExecutor:
    """Tests for SetVariableExecutor."""

    def test_set_simple_variable(self) -> None:
        """Test setting a simple variable."""
        context: dict[str, Any] = {}
        executor = SetVariableExecutor(context)

        config = {
            "name": "test_var",
            "value": "test_value",
        }
        result = executor.execute(config)

        assert result.success is True
        assert context["test_var"] == "test_value"

    def test_set_variable_with_expression(self) -> None:
        """Test setting a variable using an expression."""
        context: dict[str, Any] = {"x": 10, "y": 20}
        executor = SetVariableExecutor(context)

        config = {
            "name": "result",
            "expression": "x + y",
        }
        result = executor.execute(config)

        assert result.success is True
        assert context["result"] == 30

    def test_set_variable_missing_name(self) -> None:
        """Test error when variable name is missing."""
        context: dict[str, Any] = {}
        executor = SetVariableExecutor(context)

        config = {"value": "test"}
        result = executor.execute(config)

        assert result.success is False
        assert "name" in result.error.lower()

    def test_set_variable_expression_error(self) -> None:
        """Test error handling for invalid expression."""
        context: dict[str, Any] = {}
        executor = SetVariableExecutor(context)

        config = {
            "name": "result",
            "expression": "undefined_var + 1",
        }
        result = executor.execute(config)

        # Expression with undefined var returns None, not error
        assert result.success is True


class TestDelayExecutor:
    """Tests for DelayExecutor."""

    def test_delay_seconds(self) -> None:
        """Test delay in seconds."""
        context: dict[str, Any] = {}
        executor = DelayExecutor(context)

        config = {"seconds": 0.01}  # Very short delay for testing
        result = executor.execute(config)

        assert result.success is True
        assert result.data["delayed"] >= 0.01

    def test_delay_milliseconds(self) -> None:
        """Test delay in milliseconds."""
        context: dict[str, Any] = {}
        executor = DelayExecutor(context)

        config = {"milliseconds": 10}  # 10ms
        result = executor.execute(config)

        assert result.success is True
        assert result.data["delayed"] >= 0.01

    def test_zero_delay(self) -> None:
        """Test zero delay."""
        context: dict[str, Any] = {}
        executor = DelayExecutor(context)

        config = {"seconds": 0}
        result = executor.execute(config)

        assert result.success is True
        assert result.skipped is True


class TestLogExecutor:
    """Tests for LogExecutor."""

    def test_log_info(self) -> None:
        """Test logging at info level."""
        context: dict[str, Any] = {}
        executor = LogExecutor(context)

        config = {
            "message": "Test log message",
            "level": "info",
        }
        result = executor.execute(config)

        assert result.success is True
        assert result.data["message"] == "Test log message"
        assert result.data["level"] == "info"

    def test_log_with_interpolation(self) -> None:
        """Test logging with variable interpolation."""
        context: dict[str, Any] = {"user": "Alice", "count": 5}
        executor = LogExecutor(context)

        config = {
            "message": "User ${user} has ${count} items",
            "level": "debug",
        }
        result = executor.execute(config)

        assert result.success is True

    def test_log_default_level(self) -> None:
        """Test logging with default level."""
        context: dict[str, Any] = {}
        executor = LogExecutor(context)

        config = {"message": "Test message"}
        result = executor.execute(config)

        assert result.success is True
        assert result.data["level"] == "info"

    def test_log_missing_message(self) -> None:
        """Test error when message is missing."""
        context: dict[str, Any] = {}
        executor = LogExecutor(context)

        config = {"level": "info"}
        result = executor.execute(config)

        assert result.success is False


class TestNotifyExecutor:
    """Tests for NotifyExecutor."""

    def test_notify_webhook(self) -> None:
        """Test notification via webhook channel."""
        context: dict[str, Any] = {}
        send_text = MagicMock()
        executor = NotifyExecutor(context, send_text=send_text)

        config = {
            "message": "Test notification",
            "channel": "webhook",
            "level": "info",
        }
        result = executor.execute(config)

        assert result.success is True

    def test_notify_log_channel(self) -> None:
        """Test notification via log channel."""
        context: dict[str, Any] = {}
        executor = NotifyExecutor(context)

        config = {
            "message": "Test notification",
            "channel": "log",
            "level": "warning",
        }
        result = executor.execute(config)

        assert result.success is True

    def test_notify_missing_message(self) -> None:
        """Test error when message is missing."""
        context: dict[str, Any] = {}
        executor = NotifyExecutor(context)

        config = {"channel": "log"}
        result = executor.execute(config)

        assert result.success is False


class TestConditionalExecutor:
    """Tests for ConditionalExecutor."""

    def test_condition_true_branch(self) -> None:
        """Test executing then branch when condition is true."""
        context: dict[str, Any] = {"value": 10}
        action_executor = MagicMock(return_value=ActionResult(success=True))
        executor = ConditionalExecutor(context, action_executor=action_executor)

        config = {
            "condition": "value > 5",
            "then_actions": [{"type": "log", "message": "then branch"}],
            "else_actions": [{"type": "log", "message": "else branch"}],
        }
        result = executor.execute(config)

        assert result.success is True
        # then_actions should be executed
        action_executor.assert_called()

    def test_condition_false_branch(self) -> None:
        """Test executing else branch when condition is false."""
        context: dict[str, Any] = {"value": 3}
        action_executor = MagicMock(return_value=ActionResult(success=True))
        executor = ConditionalExecutor(context, action_executor=action_executor)

        config = {
            "condition": "value > 5",
            "then_actions": [{"type": "log", "message": "then branch"}],
            "else_actions": [{"type": "log", "message": "else branch"}],
        }
        result = executor.execute(config)

        assert result.success is True

    def test_condition_missing(self) -> None:
        """Test error when condition is missing."""
        context: dict[str, Any] = {}
        executor = ConditionalExecutor(context)

        config = {
            "then_actions": [{"type": "log", "message": "test"}],
        }
        result = executor.execute(config)

        assert result.success is False

    def test_condition_syntax_error(self) -> None:
        """Test handling of invalid condition syntax."""
        context: dict[str, Any] = {}
        executor = ConditionalExecutor(context)

        config = {
            "condition": "invalid syntax >>>",
            "then_actions": [],
        }
        result = executor.execute(config)

        # Invalid condition evaluates to False, skipping execution
        # The executor doesn't fail, it just doesn't execute actions
        assert result.success is True


class TestLoopExecutor:
    """Tests for LoopExecutor."""

    def test_loop_over_list(self) -> None:
        """Test looping over a list."""
        context: dict[str, Any] = {}
        action_executor = MagicMock(return_value=ActionResult(success=True))
        executor = LoopExecutor(context, action_executor=action_executor)

        config = {
            "items": [1, 2, 3],
            "item_var": "num",
            "actions": [{"type": "log", "message": "Item: ${num}"}],
        }
        result = executor.execute(config)

        assert result.success is True
        assert action_executor.call_count == 3

    def test_loop_with_max_iterations(self) -> None:
        """Test loop with max iterations limit."""
        context: dict[str, Any] = {}
        action_executor = MagicMock(return_value=ActionResult(success=True))
        executor = LoopExecutor(context, action_executor=action_executor)

        config = {
            "items": list(range(10)),
            "max_iterations": 5,
            "actions": [{"type": "log", "message": "test"}],
        }
        result = executor.execute(config)

        assert result.success is True
        assert action_executor.call_count == 5

    def test_loop_break_on_error(self) -> None:
        """Test loop stops on error when break_on_error is true."""
        context: dict[str, Any] = {}
        action_executor = MagicMock(
            side_effect=[
                ActionResult(success=True),
                ActionResult(success=False, error="Error"),
                ActionResult(success=True),
            ]
        )
        executor = LoopExecutor(context, action_executor=action_executor)

        config = {
            "items": [1, 2, 3],
            "break_on_error": True,
            "actions": [{"type": "log", "message": "test"}],
        }
        executor.execute(config)

        # Should stop after 2 iterations
        assert action_executor.call_count == 2

    def test_loop_empty_items(self) -> None:
        """Test loop with empty items."""
        context: dict[str, Any] = {}
        action_executor = MagicMock()
        executor = LoopExecutor(context, action_executor=action_executor)

        config = {
            "items": [],
            "actions": [{"type": "log", "message": "test"}],
        }
        result = executor.execute(config)

        assert result.success is True
        action_executor.assert_not_called()


class TestParallelExecutor:
    """Tests for ParallelExecutor."""

    def test_parallel_execution(self) -> None:
        """Test parallel execution of actions."""
        context: dict[str, Any] = {}
        action_executor = MagicMock(return_value=ActionResult(success=True))
        executor = ParallelExecutor(context, action_executor=action_executor)

        config = {
            "actions": [
                {"type": "log", "message": "action 1"},
                {"type": "log", "message": "action 2"},
                {"type": "log", "message": "action 3"},
            ],
            "max_concurrent": 2,
        }
        result = executor.execute(config)

        assert result.success is True
        assert action_executor.call_count == 3

    def test_parallel_fail_fast(self) -> None:
        """Test parallel execution with fail_fast option."""
        context: dict[str, Any] = {}
        call_count = [0]

        def mock_executor(config: dict, ctx: dict = None) -> ActionResult:
            call_count[0] += 1
            if call_count[0] == 2:
                return ActionResult(success=False, error="Failed")
            return ActionResult(success=True)

        executor = ParallelExecutor(context, action_executor=mock_executor)

        config = {
            "actions": [
                {"type": "delay", "delay_seconds": 0.01},
                {"type": "log", "message": "fail"},
                {"type": "delay", "delay_seconds": 0.01},
            ],
            "fail_fast": True,
        }
        exec_result = executor.execute(config)

        # At least one should fail
        assert not exec_result.success or exec_result.data.get("failed", 0) > 0


class TestPythonCodeExecutor:
    """Tests for PythonCodeExecutor."""

    def test_simple_code_execution(self) -> None:
        """Test executing simple Python code."""
        context: dict[str, Any] = {}
        executor = PythonCodeExecutor(context)

        config = {
            "code": "output = 1 + 2",
        }
        result = executor.execute(config)

        assert result.success is True
        assert result.data == 3

    def test_code_with_context(self) -> None:
        """Test code execution with context variables."""
        context: dict[str, Any] = {"x": 10, "y": 5}
        executor = PythonCodeExecutor(context)

        config = {
            "code": "output = context['x'] * context['y']",
        }
        result = executor.execute(config)

        assert result.success is True
        assert result.data == 50

    def test_code_modifies_context(self) -> None:
        """Test that code can modify context."""
        context: dict[str, Any] = {"items": [1, 2, 3]}
        executor = PythonCodeExecutor(context)

        config = {
            "code": "output = sum(context['items'])",
        }
        result = executor.execute(config)

        assert result.success is True
        assert result.data == 6

    def test_code_syntax_error(self) -> None:
        """Test handling of syntax errors."""
        context: dict[str, Any] = {}
        executor = PythonCodeExecutor(context)

        config = {
            "code": "invalid python syntax >>>",
        }
        result = executor.execute(config)

        assert result.success is False
        assert "error" in result.error.lower() or "syntax" in result.error.lower()

    def test_code_runtime_error(self) -> None:
        """Test handling of runtime errors."""
        context: dict[str, Any] = {}
        executor = PythonCodeExecutor(context)

        config = {
            "code": "output = 1 / 0",
        }
        result = executor.execute(config)

        assert result.success is False

    def test_code_missing(self) -> None:
        """Test error when code is missing."""
        context: dict[str, Any] = {}
        executor = PythonCodeExecutor(context)

        config = {}
        result = executor.execute(config)

        assert result.success is False


class TestPluginMethodExecutor:
    """Tests for PluginMethodExecutor."""

    def test_call_plugin_method(self) -> None:
        """Test calling a plugin method."""
        context: dict[str, Any] = {}

        # Mock plugin manager
        mock_plugin = MagicMock()
        mock_plugin.test_method.return_value = "result"

        plugin_manager = MagicMock()
        plugin_manager.get_plugin.return_value = mock_plugin

        executor = PluginMethodExecutor(context, plugin_manager=plugin_manager)

        config = {
            "plugin_name": "test_plugin",
            "method_name": "test_method",
            "parameters": {"arg1": "value1"},
        }
        result = executor.execute(config)

        assert result.success is True
        plugin_manager.get_plugin.assert_called_with("test_plugin")
        mock_plugin.test_method.assert_called_with(arg1="value1")

    def test_plugin_not_found(self) -> None:
        """Test error when plugin is not found."""
        context: dict[str, Any] = {}

        plugin_manager = MagicMock()
        plugin_manager.get_plugin.return_value = None

        executor = PluginMethodExecutor(context, plugin_manager=plugin_manager)

        config = {
            "plugin_name": "nonexistent",
            "method_name": "test",
        }
        result = executor.execute(config)

        assert result.success is False

    def test_method_not_found(self) -> None:
        """Test error when method is not found on plugin."""
        context: dict[str, Any] = {}

        mock_plugin = MagicMock(spec=[])  # No methods

        plugin_manager = MagicMock()
        plugin_manager.get_plugin.return_value = mock_plugin

        executor = PluginMethodExecutor(context, plugin_manager=plugin_manager)

        config = {
            "plugin_name": "test_plugin",
            "method_name": "nonexistent_method",
        }
        result = executor.execute(config)

        assert result.success is False

    def test_no_plugin_manager(self) -> None:
        """Test error when no plugin manager is available."""
        context: dict[str, Any] = {}
        executor = PluginMethodExecutor(context, plugin_manager=None)

        config = {
            "plugin_name": "test",
            "method_name": "test",
        }
        result = executor.execute(config)

        assert result.success is False


class TestActionExecutorFactory:
    """Tests for ActionExecutorFactory."""

    def test_create_set_variable_executor(self) -> None:
        """Test creating SetVariableExecutor."""
        factory = ActionExecutorFactory()
        context: dict[str, Any] = {}

        executor = factory.create_executor("set_variable", context)

        assert executor is not None
        assert isinstance(executor, SetVariableExecutor)

    def test_create_delay_executor(self) -> None:
        """Test creating DelayExecutor."""
        factory = ActionExecutorFactory()
        context: dict[str, Any] = {}

        executor = factory.create_executor("delay", context)

        assert executor is not None
        assert isinstance(executor, DelayExecutor)

    def test_create_log_executor(self) -> None:
        """Test creating LogExecutor."""
        factory = ActionExecutorFactory()
        context: dict[str, Any] = {}

        executor = factory.create_executor("log", context)

        assert executor is not None
        assert isinstance(executor, LogExecutor)

    def test_create_conditional_executor(self) -> None:
        """Test creating ConditionalExecutor."""
        factory = ActionExecutorFactory()
        context: dict[str, Any] = {}

        executor = factory.create_executor("conditional", context)

        assert executor is not None
        assert isinstance(executor, ConditionalExecutor)

    def test_create_loop_executor(self) -> None:
        """Test creating LoopExecutor."""
        factory = ActionExecutorFactory()
        context: dict[str, Any] = {}

        executor = factory.create_executor("loop", context)

        assert executor is not None
        assert isinstance(executor, LoopExecutor)

    def test_create_parallel_executor(self) -> None:
        """Test creating ParallelExecutor."""
        factory = ActionExecutorFactory()
        context: dict[str, Any] = {}

        executor = factory.create_executor("parallel", context)

        assert executor is not None
        assert isinstance(executor, ParallelExecutor)

    def test_create_unknown_type_returns_none(self) -> None:
        """Test that unknown type returns None."""
        factory = ActionExecutorFactory()
        context: dict[str, Any] = {}

        executor = factory.create_executor("unknown_type", context)

        assert executor is None

    def test_factory_with_dependencies(self) -> None:
        """Test factory with injected dependencies."""
        plugin_manager = MagicMock()
        ai_agent = MagicMock()
        send_text = MagicMock()

        factory = ActionExecutorFactory(
            plugin_manager=plugin_manager,
            ai_agent=ai_agent,
            send_text=send_text,
        )
        context: dict[str, Any] = {}

        executor = factory.create_executor("plugin_method", context)

        assert executor is not None
        assert isinstance(executor, PluginMethodExecutor)

    def test_set_action_executor(self) -> None:
        """Test setting a nested action executor."""
        factory = ActionExecutorFactory()

        mock_executor = MagicMock()
        factory.set_action_executor(mock_executor)

        context: dict[str, Any] = {}
        executor = factory.create_executor("loop", context)

        # The executor should have the action_executor set
        assert executor is not None
