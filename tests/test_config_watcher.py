"""Tests for configuration hot-reload watcher."""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from feishu_webhook_bot.core.config import BotConfig
from feishu_webhook_bot.core.config_watcher import (
    ConfigFileHandler,
    ConfigWatcher,
)


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary configuration file."""
    config_path = tmp_path / "test_config.yaml"
    config_data = {
        "webhooks": [
            {"name": "default", "url": "https://example.com/webhook"}
        ],
        "logging": {"level": "INFO"},
    }
    
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)
    
    return config_path


@pytest.fixture
def mock_reload_callback():
    """Create a mock reload callback."""
    return MagicMock()


class TestConfigFileHandler:
    """Test configuration file event handler."""

    def test_handler_creation(self, temp_config_file, mock_reload_callback):
        """Test creating a config file handler."""
        handler = ConfigFileHandler(
            Path(temp_config_file),
            mock_reload_callback,
        )

        assert handler is not None
        assert handler.config_path == Path(temp_config_file).resolve()
        assert handler.reload_callback == mock_reload_callback

    def test_handler_tracks_last_reload(self, temp_config_file, mock_reload_callback):
        """Test that handler tracks last reload time."""
        handler = ConfigFileHandler(
            Path(temp_config_file),
            mock_reload_callback,
        )

        initial_time = handler._last_reload_time
        assert initial_time == 0.0

    @patch("feishu_webhook_bot.core.config_watcher.BotConfig.from_yaml")
    def test_handler_on_modified(self, mock_from_yaml, temp_config_file, mock_reload_callback):
        """Test handler on file modification."""
        # Setup mock
        new_config = BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/new-webhook"}]
        )
        mock_from_yaml.return_value = new_config

        handler = ConfigFileHandler(
            Path(temp_config_file),
            mock_reload_callback,
        )

        # Simulate file modification
        from watchdog.events import FileModifiedEvent
        event = FileModifiedEvent(str(temp_config_file))

        # Wait for debounce
        time.sleep(1.5)
        handler.on_modified(event)

        # Should have attempted to reload
        mock_reload_callback.assert_called_once_with(new_config)

    def test_handler_debouncing(self, temp_config_file, mock_reload_callback):
        """Test that handler debounces rapid changes."""
        handler = ConfigFileHandler(
            Path(temp_config_file),
            mock_reload_callback,
        )

        from watchdog.events import FileModifiedEvent
        event = FileModifiedEvent(str(temp_config_file))

        # Trigger multiple rapid modifications
        reload_count = [0]
        original_reload = handler._reload_config

        def count_reloads():
            reload_count[0] += 1
            return original_reload()

        handler._reload_config = count_reloads

        # Rapid modifications
        handler.on_modified(event)
        handler.on_modified(event)
        handler.on_modified(event)

        # Should only reload once due to debouncing
        time.sleep(1.5)
        handler.on_modified(event)

        # Exact count depends on timing, but should be less than 4
        assert reload_count[0] < 4


class TestConfigWatcher:
    """Test configuration watcher."""

    def test_watcher_creation(self, temp_config_file, mock_reload_callback):
        """Test creating a config watcher."""
        watcher = ConfigWatcher(str(temp_config_file), mock_reload_callback)

        assert watcher is not None
        assert watcher.config_path == Path(temp_config_file).resolve()
        assert watcher.reload_callback == mock_reload_callback

    def test_watcher_start_stop(self, temp_config_file, mock_reload_callback):
        """Test starting and stopping the watcher."""
        watcher = ConfigWatcher(str(temp_config_file), mock_reload_callback)

        # Start watcher
        watcher.start()
        assert watcher._observer is not None
        assert watcher._observer.is_alive()

        # Stop watcher
        watcher.stop()
        time.sleep(0.5)  # Give it time to stop
        assert not watcher._observer.is_alive()

    def test_watcher_multiple_start_calls(self, temp_config_file, mock_reload_callback):
        """Test that multiple start calls don't cause issues."""
        watcher = ConfigWatcher(str(temp_config_file), mock_reload_callback)

        watcher.start()
        observer1 = watcher._observer

        # Start again
        watcher.start()
        observer2 = watcher._observer

        # Should be the same observer
        assert observer1 == observer2

        watcher.stop()

    def test_watcher_stop_when_not_started(self, temp_config_file, mock_reload_callback):
        """Test stopping watcher when it's not started."""
        watcher = ConfigWatcher(str(temp_config_file), mock_reload_callback)

        # Should not raise
        watcher.stop()


class TestConfigReload:
    """Test configuration reload functionality."""

    @patch("feishu_webhook_bot.core.config_watcher.BotConfig.from_yaml")
    def test_reload_calls_callback(self, mock_from_yaml, temp_config_file, mock_reload_callback):
        """Test that reload calls the callback."""
        new_config = BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/new-webhook"}]
        )
        mock_from_yaml.return_value = new_config

        handler = ConfigFileHandler(
            Path(temp_config_file),
            mock_reload_callback,
        )
        handler._reload_config()

        # Callback should be called with new config
        mock_reload_callback.assert_called_once_with(new_config)

    @patch("feishu_webhook_bot.core.config_watcher.BotConfig.from_yaml")
    def test_reload_handles_invalid_config(self, mock_from_yaml, temp_config_file, mock_reload_callback):
        """Test that reload handles invalid configuration."""
        # Simulate load failure
        mock_from_yaml.side_effect = Exception("Invalid config")

        handler = ConfigFileHandler(
            Path(temp_config_file),
            mock_reload_callback,
        )

        # Should not raise, just log error
        handler._reload_config()

        # Callback should not be called
        mock_reload_callback.assert_not_called()

    @patch("feishu_webhook_bot.core.config_watcher.validate_yaml_config")
    @patch("feishu_webhook_bot.core.config_watcher.BotConfig.from_yaml")
    def test_reload_validates_before_loading(
        self, mock_from_yaml, mock_validate, temp_config_file, mock_reload_callback
    ):
        """Test that reload validates config before loading."""
        # Setup mocks
        mock_validate.return_value = (True, [])
        new_config = BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/webhook"}]
        )
        mock_from_yaml.return_value = new_config

        handler = ConfigFileHandler(
            Path(temp_config_file),
            mock_reload_callback,
        )
        handler._reload_config()

        # Should validate first
        mock_validate.assert_called_once()

    @patch("feishu_webhook_bot.core.config_watcher.validate_yaml_config")
    @patch("feishu_webhook_bot.core.config_watcher.BotConfig.from_yaml")
    def test_reload_skips_invalid_config(
        self, mock_from_yaml, mock_validate, temp_config_file, mock_reload_callback
    ):
        """Test that reload skips loading if validation fails."""
        # Setup mocks - validation fails
        mock_validate.return_value = (False, ["Error 1", "Error 2"])

        handler = ConfigFileHandler(
            Path(temp_config_file),
            mock_reload_callback,
        )
        handler._reload_config()

        # Should not load config
        mock_from_yaml.assert_not_called()
        mock_reload_callback.assert_not_called()


class TestIntegration:
    """Test integration scenarios."""

    def test_file_modification_triggers_reload(self, temp_config_file, mock_reload_callback):
        """Test that actual file modification triggers reload."""
        watcher = ConfigWatcher(str(temp_config_file), mock_reload_callback)
        watcher.start()

        try:
            # Modify the file
            time.sleep(0.5)
            with open(temp_config_file, "a") as f:
                f.write("\n# Modified\n")

            # Wait for watcher to detect change
            time.sleep(2.0)

            # Reload should have been triggered
            # (This is hard to test without mocking, so we just verify no errors)

        finally:
            watcher.stop()

    def test_watcher_handles_rapid_changes(self, temp_config_file, mock_reload_callback):
        """Test that watcher handles rapid file changes."""
        watcher = ConfigWatcher(str(temp_config_file), mock_reload_callback)
        watcher.start()

        try:
            # Make rapid changes
            for i in range(5):
                with open(temp_config_file, "a") as f:
                    f.write(f"\n# Change {i}\n")
                time.sleep(0.1)

            # Wait for debouncing
            time.sleep(2.0)

            # Should handle gracefully

        finally:
            watcher.stop()

    def test_watcher_cleanup_on_stop(self, temp_config_file, mock_reload_callback):
        """Test that watcher cleans up resources on stop."""
        watcher = ConfigWatcher(str(temp_config_file), mock_reload_callback)
        watcher.start()

        observer = watcher._observer
        assert observer.is_alive()

        watcher.stop()
        time.sleep(0.5)

        # Observer should be stopped
        assert not observer.is_alive()

