"""Tests for task executor."""

import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from feishu_webhook_bot.core.config import (
    BotConfig,
    TaskActionConfig,
    TaskConditionConfig,
    TaskDefinitionConfig,
    TaskErrorHandlingConfig,
)
from feishu_webhook_bot.tasks.executor import TaskExecutor
from tests.mocks import MockPlugin


@pytest.fixture
def mock_config():
    """Create a mock bot configuration."""
    return BotConfig(
        webhooks=[
            {"name": "default", "url": "https://example.com/webhook"},
            {"name": "alerts", "url": "https://example.com/alerts"},
        ]
    )


@pytest.fixture
def mock_plugin_manager():
    """Create a mock plugin manager."""
    manager = MagicMock()
    plugin = MockPlugin(config=mock_config(), scheduler=None, clients={})
    manager.get_plugin.return_value = plugin
    return manager


@pytest.fixture
def mock_clients():
    """Create mock webhook clients."""
    default_client = MagicMock()
    alerts_client = MagicMock()
    return {"default": default_client, "alerts": alerts_client}


@pytest.fixture
def task_executor(mock_config, mock_plugin_manager, mock_clients):
    """Create a task executor instance."""
    return TaskExecutor(
        config=mock_config,
        plugin_manager=mock_plugin_manager,
        clients=mock_clients,
    )


class TestTaskConditions:
    """Test task condition checking."""

    def test_no_conditions_always_true(self, task_executor):
        """Test that tasks with no conditions can always execute."""
        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="test",
                )
            ],
        )
        assert task_executor.can_execute(task, {}) is True

    def test_time_range_condition_within_range(self, task_executor):
        """Test time_range condition when current time is within range."""
        current_hour = datetime.now().hour
        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            conditions=[
                TaskConditionConfig(
                    type="time_range",
                    start_time=f"{current_hour:02d}:00",
                    end_time=f"{(current_hour + 1) % 24:02d}:00",
                )
            ],
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="test",
                )
            ],
        )
        assert task_executor.can_execute(task, {}) is True

    def test_time_range_condition_outside_range(self, task_executor):
        """Test time_range condition when current time is outside range."""
        current_hour = datetime.now().hour
        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            conditions=[
                TaskConditionConfig(
                    type="time_range",
                    start_time=f"{(current_hour + 2) % 24:02d}:00",
                    end_time=f"{(current_hour + 3) % 24:02d}:00",
                )
            ],
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="test",
                )
            ],
        )
        assert task_executor.can_execute(task, {}) is False

    def test_day_of_week_condition_matching(self, task_executor):
        """Test day_of_week condition when current day matches."""
        current_day = datetime.now().strftime("%A").lower()
        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            conditions=[
                TaskConditionConfig(
                    type="day_of_week",
                    days=[current_day],
                )
            ],
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="test",
                )
            ],
        )
        assert task_executor.can_execute(task, {}) is True

    def test_day_of_week_condition_not_matching(self, task_executor):
        """Test day_of_week condition when current day doesn't match."""
        current_day = datetime.now().strftime("%A").lower()
        other_days = [d for d in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"] if d != current_day]
        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            conditions=[
                TaskConditionConfig(
                    type="day_of_week",
                    days=other_days[:1],  # Pick one day that's not today
                )
            ],
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="test",
                )
            ],
        )
        assert task_executor.can_execute(task, {}) is False

    def test_environment_condition_matching(self, task_executor):
        """Test environment condition when environment matches."""
        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            conditions=[
                TaskConditionConfig(
                    type="environment",
                    environment="test",
                )
            ],
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="test",
                )
            ],
        )
        context = {"environment": "test"}
        assert task_executor.can_execute(task, context) is True

    def test_environment_condition_not_matching(self, task_executor):
        """Test environment condition when environment doesn't match."""
        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            conditions=[
                TaskConditionConfig(
                    type="environment",
                    environment="production",
                )
            ],
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="test",
                )
            ],
        )
        context = {"environment": "development"}
        assert task_executor.can_execute(task, context) is False

    def test_custom_condition_true(self, task_executor):
        """Test custom condition that evaluates to True."""
        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            conditions=[
                TaskConditionConfig(
                    type="custom",
                    expression="context.get('value', 0) > 10",
                )
            ],
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="test",
                )
            ],
        )
        context = {"value": 15}
        assert task_executor.can_execute(task, context) is True

    def test_custom_condition_false(self, task_executor):
        """Test custom condition that evaluates to False."""
        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            conditions=[
                TaskConditionConfig(
                    type="custom",
                    expression="context.get('value', 0) > 10",
                )
            ],
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="test",
                )
            ],
        )
        context = {"value": 5}
        assert task_executor.can_execute(task, context) is False

    def test_multiple_conditions_all_true(self, task_executor):
        """Test multiple conditions when all are true."""
        current_day = datetime.now().strftime("%A").lower()
        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            conditions=[
                TaskConditionConfig(type="day_of_week", days=[current_day]),
                TaskConditionConfig(type="environment", environment="test"),
            ],
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="test",
                )
            ],
        )
        context = {"environment": "test"}
        assert task_executor.can_execute(task, context) is True

    def test_multiple_conditions_one_false(self, task_executor):
        """Test multiple conditions when one is false."""
        current_day = datetime.now().strftime("%A").lower()
        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            conditions=[
                TaskConditionConfig(type="day_of_week", days=[current_day]),
                TaskConditionConfig(type="environment", environment="production"),
            ],
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="test",
                )
            ],
        )
        context = {"environment": "development"}
        assert task_executor.can_execute(task, context) is False


class TestTaskActions:
    """Test task action execution."""

    def test_send_message_action(self, task_executor, mock_clients):
        """Test send_message action execution."""
        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="Test message",
                )
            ],
        )
        result = task_executor.execute(task, {})

        assert result["success"] is True
        assert result["task_name"] == "test_task"
        mock_clients["default"].send_text.assert_called_once_with("Test message")

    def test_send_message_with_template_vars(self, task_executor, mock_clients):
        """Test send_message action with template variable substitution."""
        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="Value: ${test_value}",
                )
            ],
        )
        context = {"test_value": "42"}
        result = task_executor.execute(task, context)

        assert result["success"] is True
        mock_clients["default"].send_text.assert_called_once_with("Value: 42")

    def test_plugin_method_action(self, task_executor, mock_plugin_manager):
        """Test plugin_method action execution."""
        plugin = mock_plugin_manager.get_plugin.return_value
        plugin.process_data.return_value = {"result": "processed"}

        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            actions=[
                TaskActionConfig(
                    type="plugin_method",
                    plugin="test-plugin",
                    method="process_data",
                    args=["test_data"],
                    save_as="result",
                )
            ],
        )
        result = task_executor.execute(task, {})

        assert result["success"] is True
        assert result["context"]["result"] == {"result": "processed"}
        plugin.process_data.assert_called_once_with("test_data")

    def test_plugin_method_with_kwargs(self, task_executor, mock_plugin_manager):
        """Test plugin_method action with keyword arguments."""
        plugin = mock_plugin_manager.get_plugin.return_value
        plugin.check_health.return_value = {"status": "healthy"}

        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            actions=[
                TaskActionConfig(
                    type="plugin_method",
                    plugin="test-plugin",
                    method="check_health",
                    args=["https://example.com"],
                    kwargs={"timeout": 30},
                    save_as="health",
                )
            ],
        )
        result = task_executor.execute(task, {})

        assert result["success"] is True
        assert result["context"]["health"] == {"status": "healthy"}
        plugin.check_health.assert_called_once_with("https://example.com", timeout=30)

    @patch("httpx.request")
    def test_http_request_action(self, mock_request, task_executor):
        """Test http_request action execution."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_request.return_value = mock_response

        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            actions=[
                TaskActionConfig(
                    type="http_request",
                    request={
                        "method": "GET",
                        "url": "https://api.example.com/data",
                        "timeout": 10,
                        "save_as": "api_response",
                    }
                )
            ],
        )
        result = task_executor.execute(task, {})

        assert result["success"] is True
        assert "api_response" in result["context"]
        mock_request.assert_called_once()

    def test_python_code_action(self, task_executor):
        """Test python_code action execution."""
        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            actions=[
                TaskActionConfig(
                    type="python_code",
                    code="context['result'] = 2 + 2",
                )
            ],
        )
        result = task_executor.execute(task, {})

        assert result["success"] is True
        assert result["context"]["result"] == 4

    def test_multiple_actions_in_sequence(self, task_executor, mock_clients, mock_plugin_manager):
        """Test multiple actions executed in sequence."""
        plugin = mock_plugin_manager.get_plugin.return_value
        plugin.get_stats.return_value = {"cpu": 75}

        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            actions=[
                TaskActionConfig(
                    type="plugin_method",
                    plugin="test-plugin",
                    method="get_stats",
                    save_as="stats",
                ),
                TaskActionConfig(
                    type="python_code",
                    code="context['cpu_high'] = context['stats']['cpu'] > 80",
                ),
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="CPU: ${stats}",
                ),
            ],
        )
        result = task_executor.execute(task, {})

        assert result["success"] is True
        assert result["context"]["stats"] == {"cpu": 75}
        assert result["context"]["cpu_high"] is False
        mock_clients["default"].send_text.assert_called_once()


class TestErrorHandling:
    """Test task error handling."""

    def test_error_handling_log_strategy(self, task_executor, mock_clients):
        """Test error handling with 'log' strategy."""
        mock_clients["default"].send_text.side_effect = Exception("Send failed")

        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="test",
                )
            ],
            error_handling=TaskErrorHandlingConfig(
                on_failure="log",
                retry_on_failure=False,
            ),
        )
        result = task_executor.execute(task, {})

        assert result["success"] is False
        assert "error" in result

    def test_error_handling_with_retry(self, task_executor, mock_clients):
        """Test error handling with retry logic."""
        # Fail twice, then succeed
        call_count = [0]
        def send_with_retry(msg):
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Temporary failure")
            return True

        mock_clients["default"].send_text.side_effect = send_with_retry

        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="test",
                )
            ],
            error_handling=TaskErrorHandlingConfig(
                on_failure="log",
                retry_on_failure=True,
                max_retries=3,
                retry_delay=0.1,
            ),
        )
        result = task_executor.execute(task, {})

        assert result["success"] is True
        assert call_count[0] == 3

    def test_timeout_handling(self, task_executor):
        """Test task timeout handling."""
        task = TaskDefinitionConfig(
            name="test_task",
            enabled=True,
            timeout=1,
            actions=[
                TaskActionConfig(
                    type="python_code",
                    code="import time; time.sleep(5)",
                )
            ],
        )
        result = task_executor.execute(task, {})

        # Should timeout and fail
        assert result["success"] is False
        assert "timeout" in str(result.get("error", "")).lower() or "error" in result

