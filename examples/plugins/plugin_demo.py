"""Comprehensive demonstration of the Plugin System.

This example demonstrates:
1. Creating custom plugins
2. Plugin lifecycle (load, enable, disable, unload)
3. Registering scheduled jobs from plugins
4. Accessing bot resources (client, config, scheduler)
5. Plugin configuration and settings
6. Event handling in plugins
7. Hot-reload functionality

Run this example:
    python examples/plugin_demo.py
"""

import tempfile
import time
from pathlib import Path

from feishu_webhook_bot import FeishuBot
from feishu_webhook_bot.core.config import (
    BotConfig,
    PluginConfig,
    PluginSettingsConfig,
    WebhookConfig,
)
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

# ============================================================================
# Example Plugin Implementations
# ============================================================================


class HelloWorldPlugin(BasePlugin):
    """Simple plugin that sends a greeting message."""

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="hello-world",
            version="1.0.0",
            description="Sends greeting messages",
            author="Demo",
        )

    def on_load(self) -> None:
        """Called when plugin is loaded."""
        self.logger.info("HelloWorldPlugin loaded!")

    def on_enable(self) -> None:
        """Called when plugin is enabled."""
        self.logger.info("HelloWorldPlugin enabled!")
        # Send a greeting message
        self.client.send_text("👋 Hello from HelloWorldPlugin!")

    def on_disable(self) -> None:
        """Called when plugin is disabled."""
        self.logger.info("HelloWorldPlugin disabled!")

    def on_unload(self) -> None:
        """Called before plugin is unloaded (hot-reload)."""
        self.logger.info("HelloWorldPlugin unloaded!")


class ScheduledTaskPlugin(BasePlugin):
    """Plugin that demonstrates scheduled job registration."""

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="scheduled-task",
            version="1.0.0",
            description="Demonstrates scheduled tasks",
            author="Demo",
        )

    def on_enable(self) -> None:
        """Register scheduled jobs when plugin is enabled."""
        self.logger.info("Registering scheduled jobs...")

        # Register interval-based job (every 30 seconds)
        self.register_job(
            self.interval_task,
            trigger="interval",
            seconds=30,
            job_id="scheduled-task.interval",
        )

        # Register cron-based job (every minute at :00 seconds)
        self.register_job(
            self.cron_task,
            trigger="cron",
            minute="*",
            second="0",
            job_id="scheduled-task.cron",
        )

        self.logger.info("Scheduled jobs registered!")

    def interval_task(self) -> None:
        """Task that runs every 30 seconds."""
        self.logger.info("⏰ Interval task executed!")
        self.client.send_text("⏰ Interval task: Running every 30 seconds")

    def cron_task(self) -> None:
        """Task that runs every minute."""
        self.logger.info("📅 Cron task executed!")
        self.client.send_text("📅 Cron task: Running every minute")

    def on_disable(self) -> None:
        """Clean up jobs when plugin is disabled."""
        self.logger.info("Cleaning up scheduled jobs...")
        self.cleanup_jobs()


class ConfigurablePlugin(BasePlugin):
    """Plugin that demonstrates configuration access."""

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="configurable",
            version="1.0.0",
            description="Demonstrates plugin configuration",
            author="Demo",
        )

    def on_enable(self) -> None:
        """Access plugin-specific configuration."""
        # Get individual config values with defaults
        api_key = self.get_config_value("api_key", "default-key")
        threshold = self.get_config_value("threshold", 50)
        enabled_features = self.get_config_value("features", [])

        self.logger.info(f"API Key: {api_key}")
        self.logger.info(f"Threshold: {threshold}")
        self.logger.info(f"Features: {enabled_features}")

        # Get all config values
        all_config = self.get_all_config()
        self.logger.info(f"All config: {all_config}")

        # Send configuration summary
        message = f"""⚙️ Plugin Configuration:
• API Key: {api_key}
• Threshold: {threshold}
• Features: {", ".join(enabled_features) if enabled_features else "None"}
"""
        self.client.send_text(message)


class EventHandlerPlugin(BasePlugin):
    """Plugin that demonstrates event handling."""

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="event-handler",
            version="1.0.0",
            description="Handles incoming Feishu events",
            author="Demo",
        )

    def handle_event(self, event: dict, context: dict | None = None) -> None:
        """Handle incoming Feishu events.

        Args:
            event: Event payload from Feishu
            context: Optional context information
        """
        event_type = event.get("type", "unknown")
        self.logger.info(f"📨 Received event: {event_type}")

        # Handle different event types
        if event_type == "message":
            self._handle_message(event)
        elif event_type == "app_mention":
            self._handle_mention(event)
        else:
            self.logger.info(f"Unhandled event type: {event_type}")

    def _handle_message(self, event: dict) -> None:
        """Handle message events."""
        message = event.get("message", {})
        content = message.get("content", "")
        self.logger.info(f"Message received: {content}")
        self.client.send_text(f"📨 Received message: {content}")

    def _handle_mention(self, event: dict) -> None:
        """Handle app mention events."""
        self.logger.info("Bot was mentioned!")
        self.client.send_text("👋 Thanks for mentioning me!")


# ============================================================================
# Helper Functions
# ============================================================================


def get_dummy_webhook() -> list[WebhookConfig]:
    """Get a dummy webhook configuration for demos.

    Note: In demo mode, we use a mock webhook URL. Plugins should handle
    send_text failures gracefully or skip sending messages in demos.
    """
    return [
        WebhookConfig(
            name="default",
            url="https://open.feishu.cn/open-apis/bot/v2/hook/demo-webhook",
        )
    ]


# ============================================================================
# Demo Functions
# ============================================================================


def demo_basic_plugin() -> None:
    """Demonstrate basic plugin creation and lifecycle."""
    print("\n" + "=" * 70)
    print("Demo 1: Basic Plugin Creation and Lifecycle")
    print("=" * 70)

    # Create a temporary plugin directory
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir)

        # Write HelloWorldPlugin to file
        plugin_file = plugin_dir / "hello_plugin.py"
        plugin_code = """
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class HelloPlugin(BasePlugin):
    def metadata(self):
        return PluginMetadata(
            name="hello",
            version="1.0.0",
            description="Simple hello plugin"
        )

    def on_load(self):
        self.logger.info("Plugin loaded!")

    def on_enable(self):
        self.logger.info("Plugin enabled!")
        # Note: Skipping send_text in demo to avoid webhook errors

    def on_disable(self):
        self.logger.info("Plugin disabled!")
"""
        plugin_file.write_text(plugin_code)

        # Create bot configuration
        config = BotConfig(
            webhooks=get_dummy_webhook(),
            plugins=PluginConfig(
                enabled=True,
                plugin_dir=str(plugin_dir),
                auto_reload=False,
            ),
        )

        # Create and start bot
        bot = FeishuBot(config)
        print("\n✅ Bot created with plugin system enabled")
        print(f"✅ Plugin directory: {plugin_dir}")
        print(f"✅ Loaded plugins: {list(bot.plugin_manager.plugins.keys())}")

        # Stop bot
        bot.stop()
        print("\n✅ Bot stopped, plugins disabled")


def demo_scheduled_tasks() -> None:
    """Demonstrate plugin with scheduled tasks."""
    print("\n" + "=" * 70)
    print("Demo 2: Plugin with Scheduled Tasks")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir)

        # Write ScheduledTaskPlugin to file
        plugin_file = plugin_dir / "scheduled_plugin.py"
        plugin_code = """
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class ScheduledPlugin(BasePlugin):
    def metadata(self):
        return PluginMetadata(name="scheduled", version="1.0.0")

    def on_enable(self):
        # Register a job that runs every 5 seconds
        self.register_job(
            self.my_task,
            trigger="interval",
            seconds=5,
            job_id="scheduled.task"
        )
        self.logger.info("Scheduled job registered!")

    def my_task(self):
        self.logger.info("Task executed!")
        # Note: Skipping send_text in demo to avoid webhook errors
"""
        plugin_file.write_text(plugin_code)

        config = BotConfig(
            webhooks=get_dummy_webhook(),
            plugins=PluginConfig(enabled=True, plugin_dir=str(plugin_dir)),
        )

        bot = FeishuBot(config)
        print("\n✅ Bot started with scheduled task plugin")
        print("✅ Waiting 12 seconds to see task executions...")

        # Wait to see some task executions
        time.sleep(12)

        bot.stop()
        print("\n✅ Bot stopped")


def demo_plugin_configuration() -> None:
    """Demonstrate plugin configuration access."""
    print("\n" + "=" * 70)
    print("Demo 3: Plugin Configuration")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir)

        # Write ConfigurablePlugin to file
        plugin_file = plugin_dir / "config_plugin.py"
        plugin_code = """
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class ConfigPlugin(BasePlugin):
    def metadata(self):
        return PluginMetadata(name="config-demo", version="1.0.0")

    def on_enable(self):
        api_key = self.get_config_value("api_key", "default")
        threshold = self.get_config_value("threshold", 100)
        self.logger.info(f"API Key: {api_key}, Threshold: {threshold}")
        # Note: Skipping send_text in demo to avoid webhook errors
"""
        plugin_file.write_text(plugin_code)

        # Create configuration with plugin settings
        config = BotConfig(
            webhooks=get_dummy_webhook(),
            plugins=PluginConfig(
                enabled=True,
                plugin_dir=str(plugin_dir),
                plugin_settings=[
                    PluginSettingsConfig(
                        plugin_name="config-demo",
                        enabled=True,
                        priority=100,
                        settings={
                            "api_key": "secret-key-123",
                            "threshold": 75,
                            "features": ["feature1", "feature2"],
                        },
                    )
                ],
            ),
        )

        bot = FeishuBot(config)
        print("\n✅ Bot started with configured plugin")
        print("✅ Plugin settings:")
        print("   • api_key: secret-key-123")
        print("   • threshold: 75")
        print("   • features: ['feature1', 'feature2']")

        bot.stop()
        print("\n✅ Bot stopped")


def demo_event_handling() -> None:
    """Demonstrate plugin event handling."""
    print("\n" + "=" * 70)
    print("Demo 4: Plugin Event Handling")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir)

        # Write EventHandlerPlugin to file
        plugin_file = plugin_dir / "event_plugin.py"
        plugin_code = """
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class EventPlugin(BasePlugin):
    def metadata(self):
        return PluginMetadata(name="event-handler", version="1.0.0")

    def handle_event(self, event, context=None):
        event_type = event.get("type", "unknown")
        self.logger.info(f"Received event: {event_type}")

        if event_type == "message":
            content = event.get("message", {}).get("content", "")
            self.logger.info(f"Would echo: {content}")
            # Note: Skipping send_text in demo to avoid webhook errors
"""
        plugin_file.write_text(plugin_code)

        config = BotConfig(
            webhooks=get_dummy_webhook(),
            plugins=PluginConfig(enabled=True, plugin_dir=str(plugin_dir)),
        )

        bot = FeishuBot(config)
        print("\n✅ Bot started with event handler plugin")

        # Simulate event dispatch
        test_event = {
            "type": "message",
            "message": {"content": "Hello from test!"},
        }

        print("\n📨 Dispatching test event...")
        for plugin in bot.plugin_manager.plugins.values():
            plugin.handle_event(test_event)

        bot.stop()
        print("\n✅ Bot stopped")


def demo_hot_reload() -> None:
    """Demonstrate plugin hot-reload functionality."""
    print("\n" + "=" * 70)
    print("Demo 5: Plugin Hot-Reload")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir)

        # Write initial plugin version
        plugin_file = plugin_dir / "reload_plugin.py"
        plugin_code_v1 = """
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class ReloadPlugin(BasePlugin):
    def metadata(self):
        return PluginMetadata(name="reload-demo", version="1.0.0")

    def on_enable(self):
        self.logger.info("Plugin v1.0.0 enabled!")
        # Note: Skipping send_text in demo to avoid webhook errors
"""
        plugin_file.write_text(plugin_code_v1)

        config = BotConfig(
            webhooks=get_dummy_webhook(),
            plugins=PluginConfig(
                enabled=True,
                plugin_dir=str(plugin_dir),
                auto_reload=True,  # Enable hot-reload
            ),
        )

        bot = FeishuBot(config)
        print("\n✅ Bot started with hot-reload enabled")
        print("✅ Plugin v1.0.0 loaded")

        # Wait a moment
        time.sleep(2)

        # Update plugin file (simulate code change)
        print("\n🔄 Updating plugin code...")
        plugin_code_v2 = """
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class ReloadPlugin(BasePlugin):
    def metadata(self):
        return PluginMetadata(name="reload-demo", version="2.0.0")

    def on_enable(self):
        self.logger.info("Plugin v2.0.0 enabled!")
        # Note: Skipping send_text in demo to avoid webhook errors
"""
        plugin_file.write_text(plugin_code_v2)

        print("✅ Plugin file updated to v2.0.0")
        print("✅ Waiting for hot-reload to trigger...")
        time.sleep(3)

        bot.stop()
        print("\n✅ Bot stopped")


def demo_plugin_priority() -> None:
    """Demonstrate plugin loading priority."""
    print("\n" + "=" * 70)
    print("Demo 6: Plugin Loading Priority")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir)

        # Create multiple plugins
        for i in range(1, 4):
            plugin_file = plugin_dir / f"plugin_{i}.py"
            plugin_code = f"""
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class Plugin{i}(BasePlugin):
    def metadata(self):
        return PluginMetadata(name="plugin-{i}", version="1.0.0")

    def on_enable(self):
        self.logger.info("Plugin {i} enabled!")
        # Note: Skipping send_text in demo to avoid webhook errors
"""
            plugin_file.write_text(plugin_code)

        # Configure with different priorities
        config = BotConfig(
            webhooks=get_dummy_webhook(),
            plugins=PluginConfig(
                enabled=True,
                plugin_dir=str(plugin_dir),
                plugin_settings=[
                    PluginSettingsConfig(plugin_name="plugin-1", priority=30),
                    PluginSettingsConfig(plugin_name="plugin-2", priority=10),  # Loads first
                    PluginSettingsConfig(plugin_name="plugin-3", priority=20),
                ],
            ),
        )

        bot = FeishuBot(config)
        print("\n✅ Bot started with 3 plugins")
        print("✅ Loading order (by priority):")
        print("   1. plugin-2 (priority: 10)")
        print("   2. plugin-3 (priority: 20)")
        print("   3. plugin-1 (priority: 30)")

        bot.stop()
        print("\n✅ Bot stopped")


# ============================================================================
# Main Demo Runner
# ============================================================================


def main() -> None:
    """Run all plugin system demonstrations."""
    print("\n" + "=" * 70)
    print("FEISHU WEBHOOK BOT - PLUGIN SYSTEM DEMONSTRATION")
    print("=" * 70)

    demos = [
        ("Basic Plugin Creation", demo_basic_plugin),
        ("Scheduled Tasks", demo_scheduled_tasks),
        ("Plugin Configuration", demo_plugin_configuration),
        ("Event Handling", demo_event_handling),
        ("Hot-Reload", demo_hot_reload),
        ("Plugin Priority", demo_plugin_priority),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            demo_func()
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
            import traceback

            traceback.print_exc()

        if i < len(demos):
            print("\n" + "-" * 70)
            input("Press Enter to continue to next demo...")

    print("\n" + "=" * 70)
    print("ALL DEMONSTRATIONS COMPLETED!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("• Plugins extend bot functionality without modifying core code")
    print("• Plugins have a clear lifecycle: load → enable → disable → unload")
    print("• Plugins can register scheduled jobs for periodic tasks")
    print("• Plugins can access configuration, client, and scheduler")
    print("• Hot-reload allows updating plugins without restarting the bot")
    print("• Plugin priority controls loading order")
    print("• Plugins can handle incoming Feishu events")


if __name__ == "__main__":
    main()
