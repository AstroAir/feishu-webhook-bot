"""Mock plugin for testing."""

from typing import Any

from pydantic import Field

from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata
from feishu_webhook_bot.plugins.config_schema import PluginConfigSchema
from feishu_webhook_bot.plugins.permissions import PluginPermission


class MockPluginConfigSchema(PluginConfigSchema):
    """Mock configuration schema for testing."""

    api_key: str = Field(..., description="API key for testing")
    timeout: int = Field(default=30, description="Timeout in seconds")
    debug: bool = Field(default=False, description="Enable debug mode")


class MockPlugin(BasePlugin):
    """Mock plugin for testing task execution."""

    config_schema = MockPluginConfigSchema

    PERMISSIONS = [
        PluginPermission.NETWORK_SEND,
        PluginPermission.CONFIG_READ,
    ]

    PYTHON_DEPENDENCIES = []
    PLUGIN_DEPENDENCIES = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.call_history = []
        self.return_values = {}
        self.events_received = []

    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            description="Test plugin for unit tests",
            author="Test Author",
        )

    def on_load(self) -> None:
        """Called when plugin is loaded."""
        self.call_history.append(("on_load", [], {}))

    def on_enable(self) -> None:
        """Called when plugin is enabled."""
        self.call_history.append(("on_enable", [], {}))

    def on_disable(self) -> None:
        """Called when plugin is disabled."""
        self.call_history.append(("on_disable", [], {}))

    def on_unload(self) -> None:
        """Called when plugin is unloaded."""
        self.call_history.append(("on_unload", [], {}))

    def process_data(self, data: Any) -> dict:
        """Process data and return result."""
        self.call_history.append(("process_data", [data], {}))
        if "process_data" in self.return_values:
            return self.return_values["process_data"]
        return {"processed": True, "data": data}

    def get_stats(self) -> dict:
        """Get system stats."""
        self.call_history.append(("get_stats", [], {}))
        if "get_stats" in self.return_values:
            return self.return_values["get_stats"]
        return {"cpu": 50, "memory": 60, "disk": 70}

    def send_notification(self, message: str, level: str = "info") -> bool:
        """Send a notification."""
        self.call_history.append(("send_notification", [message, level], {}))
        if "send_notification" in self.return_values:
            return self.return_values["send_notification"]
        return True

    def check_health(self, url: str, timeout: int = 10) -> dict:
        """Check health of a URL."""
        self.call_history.append(("check_health", [url, timeout], {}))
        if "check_health" in self.return_values:
            return self.return_values["check_health"]
        return {"status": "healthy", "url": url, "response_time": 0.5}

    def set_return_value(self, method_name: str, value: Any) -> None:
        """Set return value for a method."""
        self.return_values[method_name] = value

    def get_call_count(self, method_name: str) -> int:
        """Get number of times a method was called."""
        return sum(1 for call in self.call_history if call[0] == method_name)

    def get_last_call(self, method_name: str) -> tuple | None:
        """Get the last call to a method."""
        for call in reversed(self.call_history):
            if call[0] == method_name:
                return call
        return None

    def clear_history(self) -> None:
        """Clear call history."""
        self.call_history.clear()
        self.events_received.clear()

    def handle_event(self, event: dict, context: dict | None = None) -> None:
        """Handle incoming events."""
        self.call_history.append(("handle_event", [event, context], {}))
        self.events_received.append({"event": event, "context": context})

    def get_events_received(self) -> list[dict]:
        """Get all received events."""
        return self.events_received.copy()


class MockPluginWithPermissions(BasePlugin):
    """Mock plugin with dangerous permissions for testing."""

    PERMISSIONS = [
        PluginPermission.NETWORK_SEND,
        PluginPermission.SYSTEM_EXEC,
        PluginPermission.FILE_WRITE,
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.call_history = []

    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="permission-test-plugin",
            version="1.0.0",
            description="Plugin with dangerous permissions for testing",
            author="Test Author",
        )

    def on_load(self) -> None:
        self.call_history.append(("on_load", [], {}))

    def on_enable(self) -> None:
        self.call_history.append(("on_enable", [], {}))

    def on_disable(self) -> None:
        self.call_history.append(("on_disable", [], {}))


class MockPluginWithSchema(BasePlugin):
    """Mock plugin with config schema for testing."""

    class ConfigSchema(PluginConfigSchema):
        """Inner config schema class."""

        api_key: str = Field(..., description="API key")
        endpoint: str = Field(
            default="https://api.example.com",
            description="API endpoint",
        )
        max_retries: int = Field(default=3, description="Max retries")

    config_schema = ConfigSchema

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.call_history = []

    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="schema-test-plugin",
            version="1.0.0",
            description="Plugin with config schema for testing",
            author="Test Author",
        )

    def on_load(self) -> None:
        self.call_history.append(("on_load", [], {}))

    def on_enable(self) -> None:
        self.call_history.append(("on_enable", [], {}))
        # Access config values
        api_key = self.get_config_value("api_key", "")
        endpoint = self.get_config_value("endpoint", "")
        self.call_history.append(("config_accessed", [api_key, endpoint], {}))


class MockPluginWithJobs(BasePlugin):
    """Mock plugin with scheduled jobs for testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.call_history = []
        self.job_executions = []

    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="job-test-plugin",
            version="1.0.0",
            description="Plugin with scheduled jobs for testing",
            author="Test Author",
        )

    def on_enable(self) -> None:
        self.call_history.append(("on_enable", [], {}))
        # Register a test job
        self.register_job(
            self.scheduled_task,
            trigger="interval",
            seconds=60,
            job_id="job-test-plugin.task",
        )

    def on_disable(self) -> None:
        self.call_history.append(("on_disable", [], {}))
        self.cleanup_jobs()

    def scheduled_task(self) -> None:
        """A scheduled task."""
        self.job_executions.append("executed")
        self.call_history.append(("scheduled_task", [], {}))
