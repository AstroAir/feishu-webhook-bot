"""Tests for the WebUI configuration interface."""

from unittest.mock import MagicMock

import pytest  # noqa: F401


class TestConfigUIModule:
    """Tests for the config_ui module."""

    def test_module_imports(self):
        """Test that config_ui module can be imported."""
        from feishu_webhook_bot import config_ui

        assert hasattr(config_ui, "run_ui")
        assert hasattr(config_ui, "build_ui")
        assert hasattr(config_ui, "BotController")
        assert hasattr(config_ui, "UIMemoryLogHandler")

    def test_run_ui_function_exists(self):
        """Test that run_ui function exists."""
        from feishu_webhook_bot.config_ui import run_ui

        assert callable(run_ui)

    def test_build_ui_function_exists(self):
        """Test that build_ui function exists."""
        from feishu_webhook_bot.config_ui import build_ui

        assert callable(build_ui)


class TestBotController:
    """Tests for BotController helper class."""

    def test_bot_controller_exists(self):
        """Test that BotController class exists."""
        from feishu_webhook_bot.config_ui import BotController

        assert BotController is not None

    def test_bot_controller_init(self, tmp_path):
        """Test BotController initialization."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

        controller = BotController(config_file)

        # Controller should have bot attribute (may be None before start)
        assert hasattr(controller, "bot")
        assert hasattr(controller, "running")

    def test_bot_controller_has_methods(self, tmp_path):
        """Test BotController has required methods."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

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
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

        controller = BotController(config_file)

        tasks = controller.get_task_list()
        assert tasks == []

    def test_bot_controller_get_automation_rules_empty(self, tmp_path):
        """Test BotController.get_automation_rules with no automations."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

        controller = BotController(config_file)

        automations = controller.get_automation_rules()
        assert automations == []

    def test_bot_controller_get_provider_list_empty(self, tmp_path):
        """Test BotController.get_provider_list with no providers."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

        controller = BotController(config_file)

        providers = controller.get_provider_list()
        assert providers == []

    def test_bot_controller_get_ai_stats(self, tmp_path):
        """Test BotController.get_ai_stats method."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

        controller = BotController(config_file)

        stats = controller.get_ai_stats()
        assert isinstance(stats, dict)

    def test_bot_controller_get_message_stats(self, tmp_path):
        """Test BotController.get_message_stats method."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

        controller = BotController(config_file)

        stats = controller.get_message_stats()
        assert isinstance(stats, dict)

    def test_bot_controller_get_task_list_with_tasks(self, tmp_path):
        """Test BotController.get_task_list with configured tasks."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

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

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

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

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

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
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

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
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

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
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

        controller = BotController(config_file)

        # Initially should be False
        assert controller.running is False

    def test_bot_controller_config_path(self, tmp_path):
        """Test BotController stores config path."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

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
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

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

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

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
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

        controller = BotController(config_file)

        # Initially no handler
        assert controller._ui_handler is None

        # Attach
        controller._attach_ui_logger()
        assert controller._ui_handler is not None

        # Detach
        controller._detach_ui_logger()
        assert controller._ui_handler is None


class TestWebUIModule:
    """Tests for WebUI module structure."""

    def test_webui_module_imports(self):
        """Test that webui module can be imported."""
        from feishu_webhook_bot import webui

        assert hasattr(webui, "BotController")
        assert hasattr(webui, "UIMemoryLogHandler")
        assert hasattr(webui, "build_ui")
        assert hasattr(webui, "run_ui")
        assert hasattr(webui, "t")
        assert hasattr(webui, "get_lang")
        assert hasattr(webui, "set_lang")

    def test_webui_pages_module_imports(self):
        """Test that webui.pages module can be imported."""
        from feishu_webhook_bot.webui import pages

        # Check all page builders exist
        assert hasattr(pages, "build_general_page")
        assert hasattr(pages, "build_scheduler_page")
        assert hasattr(pages, "build_plugins_page")
        assert hasattr(pages, "build_logging_page")
        assert hasattr(pages, "build_templates_page")
        assert hasattr(pages, "build_notifications_page")
        assert hasattr(pages, "build_status_page")
        assert hasattr(pages, "build_ai_dashboard_page")
        assert hasattr(pages, "build_tasks_page")
        assert hasattr(pages, "build_automation_page")
        assert hasattr(pages, "build_providers_page")
        assert hasattr(pages, "build_messages_page")
        assert hasattr(pages, "build_auth_page")
        assert hasattr(pages, "build_events_page")
        assert hasattr(pages, "build_logs_page")


class TestI18nModule:
    """Tests for i18n internationalization module."""

    def test_i18n_module_imports(self):
        """Test that i18n module can be imported."""
        from feishu_webhook_bot.webui.i18n import get_lang, set_lang, t

        assert callable(t)
        assert callable(get_lang)
        assert callable(set_lang)

    def test_i18n_default_language(self):
        """Test default language is Chinese."""
        from feishu_webhook_bot.webui.i18n import get_lang

        # Default language should be 'zh'
        assert get_lang() == "zh"

    def test_i18n_set_language(self):
        """Test setting language."""
        from feishu_webhook_bot.webui.i18n import get_lang, set_lang

        original = get_lang()
        try:
            set_lang("en")
            assert get_lang() == "en"
            set_lang("zh")
            assert get_lang() == "zh"
        finally:
            set_lang(original)

    def test_i18n_translation_function(self):
        """Test translation function returns strings."""
        from feishu_webhook_bot.webui.i18n import get_lang, set_lang, t

        original = get_lang()
        try:
            # Test English
            set_lang("en")
            assert isinstance(t("app.title"), str)
            assert t("app.title") == "Feishu Webhook Bot"

            # Test Chinese
            set_lang("zh")
            assert isinstance(t("app.title"), str)
            assert t("app.title") == "飞书 Webhook 机器人"
        finally:
            set_lang(original)

    def test_i18n_missing_key_returns_key(self):
        """Test that missing translation key returns the key itself."""
        from feishu_webhook_bot.webui.i18n import t

        missing_key = "nonexistent.key.that.does.not.exist"
        result = t(missing_key)
        assert result == missing_key

    def test_i18n_has_common_keys(self):
        """Test that common translation keys exist."""
        from feishu_webhook_bot.webui.i18n import get_lang, set_lang, t

        original = get_lang()
        try:
            set_lang("en")
            # Test common keys exist and are not the key itself
            common_keys = [
                "app.title",
                "dashboard.title",
                "general.basic_settings",
                "scheduler.title",
                "plugins.settings",
                "ai.title",
                "tasks.title",
                "common.save",
                "common.cancel",
            ]
            for key in common_keys:
                result = t(key)
                assert result != key, f"Key '{key}' not found in translations"
        finally:
            set_lang(original)


class TestUIMemoryLogHandler:
    """Tests for UIMemoryLogHandler class."""

    def test_ui_memory_log_handler_exists(self):
        """Test that UIMemoryLogHandler class exists."""
        from feishu_webhook_bot.config_ui import UIMemoryLogHandler

        assert UIMemoryLogHandler is not None

    def test_ui_memory_log_handler_init(self):
        """Test UIMemoryLogHandler initialization."""
        from collections import deque

        from feishu_webhook_bot.config_ui import UIMemoryLogHandler

        ring = deque(maxlen=100)
        handler = UIMemoryLogHandler(ring)

        assert handler.ring is ring

    def test_ui_memory_log_handler_emit(self):
        """Test UIMemoryLogHandler emit method."""
        import logging
        from collections import deque

        from feishu_webhook_bot.config_ui import UIMemoryLogHandler

        ring = deque(maxlen=100)
        handler = UIMemoryLogHandler(ring)

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        assert len(ring) == 1
        level, msg = ring[0]
        assert level == logging.INFO
        assert "Test message" in msg


class TestBotControllerAIStats:
    """Tests for BotController AI statistics methods."""

    def test_get_ai_stats_without_bot(self, tmp_path):
        """Test get_ai_stats returns default values when bot is not running."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

        controller = BotController(config_file)
        stats = controller.get_ai_stats()

        assert stats["enabled"] is False
        assert stats["current_model"] == "N/A"
        assert stats["requests"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["tokens_used"] == 0
        assert stats["mcp_servers"] == []

    def test_get_ai_stats_structure(self, tmp_path):
        """Test get_ai_stats returns correct structure."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

        controller = BotController(config_file)
        stats = controller.get_ai_stats()

        required_keys = [
            "enabled",
            "current_model",
            "requests",
            "success_rate",
            "tokens_used",
            "mcp_servers",
        ]
        for key in required_keys:
            assert key in stats, f"Missing key: {key}"


class TestBotControllerMessageStats:
    """Tests for BotController message statistics methods."""

    def test_get_message_stats_without_bot(self, tmp_path):
        """Test get_message_stats returns default values when bot is not running."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

        controller = BotController(config_file)
        stats = controller.get_message_stats()

        assert stats["queue_size"] == 0
        assert stats["queued"] == 0
        assert stats["pending"] == 0
        assert stats["failed"] == 0
        assert stats["success"] == 0

    def test_get_message_stats_structure(self, tmp_path):
        """Test get_message_stats returns correct structure."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

        controller = BotController(config_file)
        stats = controller.get_message_stats()

        required_keys = ["queue_size", "queued", "pending", "failed", "success"]
        for key in required_keys:
            assert key in stats, f"Missing key: {key}"


class TestBotControllerEventServer:
    """Tests for BotController event server methods."""

    def test_get_event_server_status_without_bot(self, tmp_path):
        """Test get_event_server_status returns default values when bot is not running."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

        controller = BotController(config_file)
        status = controller.get_event_server_status()

        assert status["running"] is False
        assert status["host"] == "N/A"
        assert status["port"] == 0
        assert status["recent_events"] == []

    def test_get_event_server_status_structure(self, tmp_path):
        """Test get_event_server_status returns correct structure."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

        controller = BotController(config_file)
        status = controller.get_event_server_status()

        required_keys = ["running", "host", "port", "recent_events"]
        for key in required_keys:
            assert key in status, f"Missing key: {key}"


class TestBotControllerLifecycle:
    """Tests for BotController lifecycle methods."""

    def test_controller_start_stop_methods_exist(self, tmp_path):
        """Test that start/stop/restart methods exist."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

        controller = BotController(config_file)

        assert hasattr(controller, "start")
        assert hasattr(controller, "stop")
        assert hasattr(controller, "restart")
        assert callable(controller.start)
        assert callable(controller.stop)
        assert callable(controller.restart)

    def test_controller_set_runtime_log_level(self, tmp_path):
        """Test set_runtime_log_level method exists and is callable."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

        controller = BotController(config_file)

        assert hasattr(controller, "set_runtime_log_level")
        assert callable(controller.set_runtime_log_level)

    def test_controller_send_test_message_method_exists(self, tmp_path):
        """Test send_test_message method exists."""
        from feishu_webhook_bot.config_ui import BotController

        config_file = tmp_path / "config.yaml"
        config_file.write_text("webhooks:\n  - name: default\n    url: https://test.com")

        controller = BotController(config_file)

        assert hasattr(controller, "send_test_message")
        assert callable(controller.send_test_message)
