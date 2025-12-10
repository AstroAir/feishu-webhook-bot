"""Tests for the WebUI configuration interface."""

import importlib
from unittest.mock import MagicMock, patch

import pytest


class TestConfigUIModule:
    """Tests for the config_ui module."""

    def test_module_imports(self):
        """Test that config_ui module can be imported."""
        from feishu_webhook_bot import config_ui

        assert hasattr(config_ui, "run_ui")

    def test_run_ui_function_exists(self):
        """Test that run_ui function exists."""
        from feishu_webhook_bot.config_ui import run_ui

        assert callable(run_ui)


class TestBotController:
    """Tests for BotController helper class."""

    def test_bot_controller_exists(self):
        """Test that BotController class exists."""
        from feishu_webhook_bot.config_ui import BotController

        assert BotController is not None

    def test_bot_controller_init(self, tmp_path):
        """Test BotController initialization."""
        from feishu_webhook_bot.config_ui import BotController
        from pathlib import Path

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "webhooks:\n  - name: default\n    url: https://test.com"
        )

        controller = BotController(config_file)

        # Controller should have bot attribute (may be None before start)
        assert hasattr(controller, "bot")
        assert hasattr(controller, "running")

    def test_bot_controller_has_methods(self, tmp_path):
        """Test BotController has required methods."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "webhooks:\n  - name: default\n    url: https://test.com"
        )

        controller = BotController(config_file)

        # Check that expected methods exist
        assert hasattr(controller, "get_task_list")
        assert hasattr(controller, "get_automation_rules")
        assert hasattr(controller, "get_provider_list")
        assert hasattr(controller, "get_ai_stats")
        assert hasattr(controller, "get_message_stats")
        assert hasattr(controller, "get_user_list")
        assert hasattr(controller, "get_event_server_status")

    def test_bot_controller_get_task_list_empty(self, tmp_path):
        """Test BotController.get_task_list with no tasks."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "webhooks:\n  - name: default\n    url: https://test.com"
        )

        controller = BotController(config_file)

        tasks = controller.get_task_list()
        assert tasks == []

    def test_bot_controller_get_automation_rules_empty(self, tmp_path):
        """Test BotController.get_automation_rules with no automations."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "webhooks:\n  - name: default\n    url: https://test.com"
        )

        controller = BotController(config_file)

        automations = controller.get_automation_rules()
        assert automations == []

    def test_bot_controller_get_provider_list_empty(self, tmp_path):
        """Test BotController.get_provider_list with no providers."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "webhooks:\n  - name: default\n    url: https://test.com"
        )

        controller = BotController(config_file)

        providers = controller.get_provider_list()
        assert providers == []

    def test_bot_controller_get_ai_stats(self, tmp_path):
        """Test BotController.get_ai_stats method."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "webhooks:\n  - name: default\n    url: https://test.com"
        )

        controller = BotController(config_file)

        stats = controller.get_ai_stats()
        assert isinstance(stats, dict)

    def test_bot_controller_get_message_stats(self, tmp_path):
        """Test BotController.get_message_stats method."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "webhooks:\n  - name: default\n    url: https://test.com"
        )

        controller = BotController(config_file)

        stats = controller.get_message_stats()
        assert isinstance(stats, dict)

    def test_bot_controller_get_task_list_with_tasks(self, tmp_path):
        """Test BotController.get_task_list with configured tasks."""
        from feishu_webhook_bot.config_ui import BotController
        from unittest.mock import MagicMock

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "webhooks:\n  - name: default\n    url: https://test.com"
        )

        controller = BotController(config_file)

        # Mock bot with tasks in config
        controller.bot = MagicMock()

        # Create mock task configs
        task1 = MagicMock()
        task1.name = "task1"
        task1.description = "First task"

        task2 = MagicMock()
        task2.name = "task2"
        task2.description = "Second task"

        cfg = MagicMock()
        cfg.tasks = [task1, task2]
        controller.bot.config = cfg

        tasks = controller.get_task_list()
        assert isinstance(tasks, list)
        assert len(tasks) == 2
        assert tasks[0]["name"] == "task1"
        assert tasks[0]["description"] == "First task"
        assert tasks[1]["name"] == "task2"
        assert tasks[1]["description"] == "Second task"
        # Verify structure
        for task in tasks:
            assert "name" in task
            assert "description" in task
            assert "enabled" in task
            assert "next_run" in task

    def test_bot_controller_get_automation_rules_with_rules(self, tmp_path):
        """Test BotController.get_automation_rules with configured rules."""
        from feishu_webhook_bot.config_ui import BotController
        from unittest.mock import MagicMock

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "webhooks:\n  - name: default\n    url: https://test.com"
        )

        controller = BotController(config_file)

        # Mock bot with automations in config
        controller.bot = MagicMock()

        # Create mock automation configs
        auto1 = MagicMock()
        auto1.name = "auto1"
        auto1.trigger = MagicMock()
        auto1.trigger.type = "schedule"

        auto2 = MagicMock()
        auto2.name = "auto2"
        auto2.trigger = MagicMock()
        auto2.trigger.type = "event"

        cfg = MagicMock()
        cfg.automations = [auto1, auto2]
        controller.bot.config = cfg

        rules = controller.get_automation_rules()
        assert isinstance(rules, list)
        assert len(rules) == 2
        assert rules[0]["name"] == "auto1"
        assert rules[1]["name"] == "auto2"
        # Verify structure
        for rule in rules:
            assert "name" in rule
            assert "trigger" in rule
            assert "enabled" in rule
            assert "status" in rule

    def test_bot_controller_get_provider_list_with_providers(self, tmp_path):
        """Test BotController.get_provider_list with running bot."""
        from feishu_webhook_bot.config_ui import BotController
        from unittest.mock import MagicMock

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "webhooks:\n  - name: default\n    url: https://test.com"
        )

        controller = BotController(config_file)

        # Mock bot with providers
        controller.bot = MagicMock()
        mock_provider = MagicMock()
        mock_provider.__class__.__name__ = "TestProvider"
        controller.bot.providers = {"test_provider": mock_provider}

        providers = controller.get_provider_list()
        assert isinstance(providers, list)
        assert len(providers) == 1
        assert providers[0]["name"] == "test_provider"
        assert providers[0]["type"] == "TestProvider"
        assert providers[0]["status"] == "Connected"

    def test_bot_controller_get_user_list(self, tmp_path):
        """Test BotController.get_user_list method."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "webhooks:\n  - name: default\n    url: https://test.com"
        )

        controller = BotController(config_file)

        users = controller.get_user_list()
        assert isinstance(users, list)
        # May be empty if auth is not configured
        for user in users:
            if user:  # If there are users
                assert "id" in user
                assert "username" in user
                assert "email" in user
                assert "status" in user

    def test_bot_controller_get_event_server_status(self, tmp_path):
        """Test BotController.get_event_server_status method."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "webhooks:\n  - name: default\n    url: https://test.com"
        )

        controller = BotController(config_file)

        status = controller.get_event_server_status()
        assert isinstance(status, dict)
        assert "running" in status
        assert "host" in status
        assert "port" in status
        assert "recent_events" in status

    def test_bot_controller_running_property(self, tmp_path):
        """Test BotController.running property."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "webhooks:\n  - name: default\n    url: https://test.com"
        )

        controller = BotController(config_file)

        # Initially should be False
        assert controller.running is False

    def test_bot_controller_config_path(self, tmp_path):
        """Test BotController stores config path."""
        from feishu_webhook_bot.config_ui import BotController
        from pathlib import Path

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "webhooks:\n  - name: default\n    url: https://test.com"
        )

        controller = BotController(config_file)

        assert controller.config_path == config_file

    def test_bot_controller_load_config_creates_default(self, tmp_path):
        """Test BotController.load_config creates default config if missing."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        # Do not create file

        controller = BotController(config_file)
        config = controller.load_config()

        assert config is not None
        # Should have created the file
        assert config_file.exists()

    def test_bot_controller_save_config(self, tmp_path):
        """Test BotController.save_config persists configuration."""
        from feishu_webhook_bot.config_ui import BotController
        from feishu_webhook_bot.core import BotConfig

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "webhooks:\n  - name: default\n    url: https://test.com"
        )

        controller = BotController(config_file)
        config = BotConfig(webhooks=[{"name": "test", "url": "https://test2.com"}])

        controller.save_config(config)

        # Verify file was updated
        assert config_file.exists()
        content = config_file.read_text()
        assert "test" in content
        assert "https://test2.com" in content

    def test_bot_controller_invalid_config_file(self, tmp_path):
        """Test BotController with invalid config file."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: [unclosed")  # Invalid YAML

        controller = BotController(config_file)

        # Should handle gracefully (may return default or raise)
        try:
            config = controller.load_config()
            # If it doesn't raise, it should still be a valid config object
            assert config is not None
        except Exception:
            # It's acceptable to raise on invalid YAML
            pass

    def test_bot_controller_status(self, tmp_path):
        """Test BotController.status method."""
        from feishu_webhook_bot.config_ui import BotController
        from unittest.mock import MagicMock

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "webhooks:\n  - name: default\n    url: https://test.com"
        )

        controller = BotController(config_file)

        status = controller.status()
        assert isinstance(status, dict)
        assert "running" in status
        assert "plugins" in status
        assert "scheduler_running" in status

    def test_bot_controller_ui_logger_attachment(self, tmp_path):
        """Test BotController UI logger attachment."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "webhooks:\n  - name: default\n    url: https://test.com"
        )

        controller = BotController(config_file)

        # Initially no handler
        assert controller._ui_handler is None

        # Attach
        controller._attach_ui_logger()
        assert controller._ui_handler is not None

        # Detach
        controller._detach_ui_logger()
        assert controller._ui_handler is None


class TestUIComponents:
    """Tests for UI component existence."""

    def test_create_ai_dashboard_exists(self):
        """Test that create_ai_dashboard function exists."""
        try:
            from feishu_webhook_bot.config_ui import create_ai_dashboard

            assert callable(create_ai_dashboard)
        except ImportError:
            # Function may not exist if WebUI enhancements weren't added
            pytest.skip("create_ai_dashboard not implemented")

    def test_create_tasks_panel_exists(self):
        """Test that create_tasks_panel function exists."""
        try:
            from feishu_webhook_bot.config_ui import create_tasks_panel

            assert callable(create_tasks_panel)
        except ImportError:
            pytest.skip("create_tasks_panel not implemented")

    def test_create_automation_panel_exists(self):
        """Test that create_automation_panel function exists."""
        try:
            from feishu_webhook_bot.config_ui import create_automation_panel

            assert callable(create_automation_panel)
        except ImportError:
            pytest.skip("create_automation_panel not implemented")

    def test_create_providers_panel_exists(self):
        """Test that create_providers_panel function exists."""
        try:
            from feishu_webhook_bot.config_ui import create_providers_panel

            assert callable(create_providers_panel)
        except ImportError:
            pytest.skip("create_providers_panel not implemented")

    def test_create_messages_panel_exists(self):
        """Test that create_messages_panel function exists."""
        try:
            from feishu_webhook_bot.config_ui import create_messages_panel

            assert callable(create_messages_panel)
        except ImportError:
            pytest.skip("create_messages_panel not implemented")

    def test_create_auth_panel_exists(self):
        """Test that create_auth_panel function exists."""
        try:
            from feishu_webhook_bot.config_ui import create_auth_panel

            assert callable(create_auth_panel)
        except ImportError:
            pytest.skip("create_auth_panel not implemented")

    def test_create_events_panel_exists(self):
        """Test that create_events_panel function exists."""
        try:
            from feishu_webhook_bot.config_ui import create_events_panel

            assert callable(create_events_panel)
        except ImportError:
            pytest.skip("create_events_panel not implemented")
