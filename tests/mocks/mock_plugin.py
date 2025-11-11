"""Mock plugin for testing."""

from typing import Any

from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata


class MockPlugin(BasePlugin):
    """Mock plugin for testing task execution."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.call_history = []
        self.return_values = {}

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
