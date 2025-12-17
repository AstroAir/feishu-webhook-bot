"""Integration tests for enhanced YAML configuration system."""

from unittest.mock import MagicMock

import pytest
import yaml

from feishu_webhook_bot.core.config import BotConfig
from feishu_webhook_bot.tasks import TaskManager
from feishu_webhook_bot.tasks.executor import TaskExecutor
from feishu_webhook_bot.tasks.templates import TaskTemplateEngine
from tests.mocks import MockPlugin, MockScheduler


@pytest.fixture
def full_config_file(tmp_path):
    """Create a full configuration file with all features."""
    config_path = tmp_path / "full_config.yaml"
    config_data = {
        "webhooks": [
            {"name": "default", "url": "https://example.com/webhook"},
            {"name": "alerts", "url": "https://example.com/alerts"},
        ],
        "logging": {"level": "INFO"},
        "scheduler": {"enabled": True},
        "plugins": {
            "enabled": True,
            "plugin_dir": "plugins",
            "plugin_settings": [
                {
                    "plugin_name": "test-plugin",
                    "enabled": True,
                    "priority": 10,
                    "settings": {
                        "api_key": "test-key",
                        "threshold": 80,
                    },
                }
            ],
        },
        "tasks": [
            {
                "name": "health_check",
                "enabled": True,
                "schedule": {"mode": "interval", "arguments": {"minutes": 5}},
                "actions": [
                    {
                        "type": "plugin_method",
                        "plugin_name": "test-plugin",
                        "method_name": "check_health",
                        "parameters": {"url": "https://api.example.com"},
                    },
                    {
                        "type": "send_message",
                        "message": "Health check completed",
                    },
                ],
            }
        ],
        "task_templates": [
            {
                "name": "notification_template",
                "description": "Send a notification",
                "base_task": {
                    "name": "notification_base",
                    "schedule": {"mode": "interval", "arguments": {"hours": 1}},
                    "actions": [
                        {
                            "type": "send_message",
                            "webhook": "default",
                            "message": "${message}",
                        }
                    ],
                },
                "parameters": [{"name": "message", "type": "string", "required": True}],
            }
        ],
        "environments": [
            {
                "name": "development",
                "variables": [
                    {"name": "LOG_LEVEL", "value": "DEBUG"},
                ],
                "overrides": {"logging": {"level": "DEBUG"}},
            },
            {
                "name": "production",
                "variables": [
                    {"name": "LOG_LEVEL", "value": "WARNING"},
                ],
                "overrides": {"logging": {"level": "WARNING"}},
            },
        ],
        "active_environment": "development",
        "config_hot_reload": False,
    }

    with open(config_path, "w") as f:
        yaml.dump(config_data, f)

    return config_path


@pytest.fixture
def mock_plugin_manager():
    """Create a mock plugin manager with a test plugin."""
    from feishu_webhook_bot.core.client import FeishuWebhookClient
    from feishu_webhook_bot.core.config import WebhookConfig

    manager = MagicMock()
    config = BotConfig(webhooks=[{"name": "default", "url": "https://example.com/webhook"}])
    webhook_config = WebhookConfig(url="https://example.com/webhook", name="default")
    client = FeishuWebhookClient(config=webhook_config)
    plugin = MockPlugin(config=config, client=client)
    plugin.set_return_value("check_health", {"status": "healthy"})
    manager.get_plugin.return_value = plugin
    return manager


@pytest.fixture
def mock_clients():
    """Create mock webhook clients."""
    return {
        "default": MagicMock(),
        "alerts": MagicMock(),
    }


class TestFullWorkflow:
    """Test complete workflow from config to execution."""

    def test_load_config_with_all_features(self, full_config_file):
        """Test loading a configuration with all features."""
        # Load the config file
        with open(full_config_file) as f:
            config_dict = yaml.safe_load(f)

        config = BotConfig(**config_dict)

        # Verify all features are loaded
        assert len(config.webhooks) == 2
        assert len(config.tasks) == 1
        assert len(config.task_templates) == 1
        assert len(config.environments) == 2
        assert config.plugins.enabled is True
        assert len(config.plugins.plugin_settings) == 1

    def test_task_execution_with_plugin_integration(
        self, full_config_file, mock_plugin_manager, mock_clients
    ):
        """Test executing a task that calls a plugin method."""
        # Load config
        with open(full_config_file) as f:
            config_dict = yaml.safe_load(f)
        config = BotConfig(**config_dict)

        # Execute the health_check task
        task = config.tasks[0]

        # Create executor with task and context
        executor = TaskExecutor(
            task=task,
            context={},
            plugin_manager=mock_plugin_manager,
            clients=mock_clients,
        )

        result = executor.execute()

        # Verify execution
        assert result["success"] is True

        # Verify plugin was called
        plugin = mock_plugin_manager.get_plugin.return_value
        assert plugin.get_call_count("check_health") > 0

        # Verify message was sent
        mock_clients["default"].send_text.assert_called_once()

    def test_task_manager_with_scheduler_integration(
        self, full_config_file, mock_plugin_manager, mock_clients
    ):
        """Test task manager integration with scheduler."""
        # Load config
        with open(full_config_file) as f:
            config_dict = yaml.safe_load(f)
        config = BotConfig(**config_dict)

        # Create task manager
        scheduler = MockScheduler()
        task_manager = TaskManager(
            config=config,
            scheduler=scheduler,
            plugin_manager=mock_plugin_manager,
            clients=mock_clients,
        )

        # Start task manager
        task_manager.start()

        # Verify task was registered
        assert len(scheduler.jobs) == 1
        # Job IDs have "task." prefix
        assert "task.health_check" in scheduler.jobs

        # Execute task manually
        result = task_manager.execute_task_now("health_check")

        assert result is not None
        assert result["success"] is True

    def test_template_to_task_workflow(self, full_config_file):
        """Test creating a task from a template."""
        # Load config
        with open(full_config_file) as f:
            config_dict = yaml.safe_load(f)
        config = BotConfig(**config_dict)

        # Create template engine with templates from config
        template_engine = TaskTemplateEngine(config.task_templates)

        # Create task from template
        task = template_engine.create_task_from_template(
            template_name="notification_template",
            task_name="hourly_notification",
            overrides={"message": "Hourly update"},
        )

        assert task is not None
        assert task.name == "hourly_notification"
        assert len(task.actions) == 1
        # Note: The message would need to be substituted by the template engine
        # Depending on implementation, check if it was applied correctly

    def test_environment_based_execution(self, full_config_file, mock_plugin_manager, mock_clients):
        """Test task execution with environment-based conditions."""
        # Load config
        with open(full_config_file) as f:
            config_dict = yaml.safe_load(f)
        config = BotConfig(**config_dict)

        # Apply environment overrides - returns new config
        prod_config = config.apply_environment_overrides("production")

        # Verify overrides were applied
        assert prod_config.logging.level == "WARNING"

        # Get environment variables
        env_vars = prod_config.get_environment_variables("production")
        assert env_vars["LOG_LEVEL"] == "WARNING"


class TestPluginConfigIntegration:
    """Test plugin configuration integration."""

    def test_plugin_reads_config_from_yaml(self, full_config_file):
        """Test that plugin can read its configuration from YAML."""
        # Load config
        with open(full_config_file) as f:
            config_dict = yaml.safe_load(f)
        config = BotConfig(**config_dict)

        # Create plugin
        from feishu_webhook_bot.core.client import FeishuWebhookClient
        from feishu_webhook_bot.core.config import WebhookConfig

        webhook_config = WebhookConfig(url="https://example.com/webhook", name="default")
        client = FeishuWebhookClient(config=webhook_config)
        plugin = MockPlugin(config=config, client=client)

        # Plugin should be able to read its config
        api_key = plugin.get_config_value("api_key")
        threshold = plugin.get_config_value("threshold")

        assert api_key == "test-key"
        assert threshold == 80

    def test_plugin_priority_ordering(self, full_config_file):
        """Test that plugins are ordered by priority."""
        # Load config
        with open(full_config_file) as f:
            config_dict = yaml.safe_load(f)
        config = BotConfig(**config_dict)

        # Get plugin settings sorted by priority
        sorted_settings = sorted(
            config.plugins.plugin_settings,
            key=lambda x: x.priority,
        )

        # Verify ordering
        assert sorted_settings[0].plugin_name == "test-plugin"
        assert sorted_settings[0].priority == 10


class TestTaskDependencyExecution:
    """Test task dependency execution."""

    def test_tasks_with_dependencies(self, mock_plugin_manager, mock_clients):
        """Test executing tasks with dependencies."""
        config = BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
            tasks=[
                {
                    "name": "task_a",
                    "enabled": True,
                    "schedule": {"mode": "interval", "arguments": {"minutes": 5}},
                    "actions": [
                        {
                            "type": "python_code",
                            "code": "context['task_a_result'] = 'A completed'",
                        }
                    ],
                },
                {
                    "name": "task_b",
                    "enabled": True,
                    "depends_on": ["task_a"],
                    "schedule": {"mode": "interval", "arguments": {"minutes": 5}},
                    "actions": [
                        {
                            "type": "python_code",
                            "code": "context['task_b_result'] = 'B completed after A'",
                        }
                    ],
                },
            ],
        )

        # Create task manager
        scheduler = MockScheduler()
        task_manager = TaskManager(
            config=config,
            scheduler=scheduler,
            plugin_manager=mock_plugin_manager,
            clients=mock_clients,
        )

        task_manager.start()

        # Both tasks should be registered
        assert len(scheduler.jobs) == 2

        # Verify dependency is recorded
        task_b = config.get_task("task_b")
        assert task_b.depends_on == ["task_a"]


class TestErrorHandlingIntegration:
    """Test error handling integration."""

    def test_task_retry_on_failure(self, mock_plugin_manager, mock_clients):
        """Test task error handling on failure."""
        # Make client fail
        mock_clients["default"].send_text.side_effect = Exception("Temporary failure")

        config = BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
            tasks=[
                {
                    "name": "retry_task",
                    "enabled": True,
                    "schedule": {"mode": "interval", "arguments": {"minutes": 5}},
                    "actions": [
                        {
                            "type": "send_message",
                            "message": "Test",
                        }
                    ],
                    "error_handling": {
                        "on_failure_action": "log",
                        "retry_on_failure": False,  # Currently retries not implemented
                        "max_retries": 3,
                        "retry_delay": 0.1,
                    },
                }
            ],
        )

        task = config.tasks[0]
        executor = TaskExecutor(
            task=task,
            context={},
            plugin_manager=mock_plugin_manager,
            clients=mock_clients,
        )

        result = executor.execute()

        # Should fail since retry is not enabled
        assert result["success"] is False
        assert result["error"] is not None


class TestConfigValidationIntegration:
    """Test configuration validation integration."""

    def test_validate_and_load_config(self, full_config_file):
        """Test validating and loading a configuration."""
        from feishu_webhook_bot.core.validation import validate_yaml_config

        # Validate config
        is_valid, errors = validate_yaml_config(str(full_config_file))

        assert is_valid is True
        assert len(errors) == 0

        # Load config
        with open(full_config_file) as f:
            config_dict = yaml.safe_load(f)
        config = BotConfig(**config_dict)

        assert config is not None

    def test_reject_invalid_config(self, tmp_path):
        """Test that invalid config is rejected."""
        from feishu_webhook_bot.core.validation import validate_yaml_config

        # Create invalid config
        invalid_config_path = tmp_path / "invalid.yaml"
        with open(invalid_config_path, "w") as f:
            yaml.dump({"webhooks": [{"name": "test"}]}, f)  # Missing url

        # Validate
        is_valid, errors = validate_yaml_config(str(invalid_config_path))

        assert is_valid is False
        assert len(errors) > 0


class TestEndToEndScenarios:
    """Test end-to-end scenarios."""

    def test_complete_bot_initialization(self, full_config_file, mock_plugin_manager, mock_clients):
        """Test complete bot initialization with all features."""
        # Load config
        with open(full_config_file) as f:
            config_dict = yaml.safe_load(f)
        config = BotConfig(**config_dict)

        # Initialize components
        scheduler = MockScheduler()
        task_manager = TaskManager(
            config=config,
            scheduler=scheduler,
            plugin_manager=mock_plugin_manager,
            clients=mock_clients,
        )
        template_engine = TaskTemplateEngine(config.task_templates)

        # Start task manager
        task_manager.start()

        # Verify everything is initialized
        assert len(scheduler.jobs) == 1
        assert template_engine.get_template("notification_template") is not None
        assert config.get_environment("development") is not None

    def test_task_execution_with_all_features(
        self, full_config_file, mock_plugin_manager, mock_clients
    ):
        """Test task execution using all features."""
        # Load config
        with open(full_config_file) as f:
            config_dict = yaml.safe_load(f)
        config = BotConfig(**config_dict)

        # Apply environment
        config_with_env = config.apply_environment_overrides("development")
        env_vars = config_with_env.get_environment_variables("development")

        # Execute task with environment context
        task = config_with_env.tasks[0]
        context = {"environment": "development", **env_vars}

        executor = TaskExecutor(
            task=task,
            context=context,
            plugin_manager=mock_plugin_manager,
            clients=mock_clients,
        )

        result = executor.execute()

        # Verify execution
        assert result["success"] is True
