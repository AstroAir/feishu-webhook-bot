#!/usr/bin/env python3
"""Configuration Hot-Reload Example.

This example demonstrates the configuration hot-reload functionality:
- Watching configuration files for changes
- Automatic reload on file modification
- Validation before reload
- Debouncing to prevent rapid reloads
- Callback-based notification system
- Error handling for invalid configurations

The config watcher enables live configuration updates without restarting the bot.
"""

import tempfile
import threading
import time
from pathlib import Path

import yaml

from feishu_webhook_bot.core import BotConfig, LoggingConfig, get_logger, setup_logging
from feishu_webhook_bot.core.config_watcher import ConfigFileHandler, ConfigWatcher

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)


# =============================================================================
# Demo 1: Basic Config Watcher Setup
# =============================================================================
def demo_basic_config_watcher() -> None:
    """Demonstrate basic config watcher setup."""
    print("\n" + "=" * 60)
    print("Demo 1: Basic Config Watcher Setup")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        # Create initial configuration
        initial_config = {
            "webhooks": [
                {
                    "url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
                    "name": "default",
                }
            ],
            "scheduler": {"enabled": True, "timezone": "Asia/Shanghai"},
        }

        with open(config_path, "w") as f:
            yaml.dump(initial_config, f)

        print(f"Created config file: {config_path}")

        # Track reload events
        reload_events = []

        def on_config_reload(new_config: BotConfig) -> None:
            """Callback when config is reloaded."""
            reload_events.append(
                {"time": time.time(), "webhooks": len(new_config.webhooks)}
            )
            print(f"  Config reloaded! Webhooks: {len(new_config.webhooks)}")

        # Create config watcher
        watcher = ConfigWatcher(
            config_path=config_path,
            reload_callback=on_config_reload,
            reload_delay=0.5,  # Short delay for demo
        )

        print("\nStarting config watcher...")
        watcher.start()
        print(f"Watcher running: {watcher.is_running}")

        # Wait a moment
        time.sleep(1)

        # Modify configuration
        print("\n--- Modifying configuration ---")
        modified_config = {
            "webhooks": [
                {
                    "url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
                    "name": "default",
                },
                {
                    "url": "https://open.feishu.cn/open-apis/bot/v2/hook/yyy",
                    "name": "secondary",
                },
            ],
            "scheduler": {"enabled": True, "timezone": "UTC"},
        }

        with open(config_path, "w") as f:
            yaml.dump(modified_config, f)

        print("Configuration file modified")

        # Wait for reload
        time.sleep(2)

        # Stop watcher
        print("\n--- Stopping watcher ---")
        watcher.stop()
        print(f"Watcher running: {watcher.is_running}")

        print(f"\nTotal reload events: {len(reload_events)}")


# =============================================================================
# Demo 2: Config File Handler
# =============================================================================
def demo_config_file_handler() -> None:
    """Demonstrate ConfigFileHandler directly."""
    print("\n" + "=" * 60)
    print("Demo 2: Config File Handler")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "handler_config.yaml"

        # Create configuration
        config_data = {
            "webhooks": [
                {"url": "https://example.com/webhook", "name": "test"}
            ],
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        # Track callbacks
        callback_count = [0]

        def reload_callback(config: BotConfig) -> None:
            callback_count[0] += 1
            print(f"  Callback #{callback_count[0]}: Config loaded")

        # Create handler
        handler = ConfigFileHandler(
            config_path=config_path,
            reload_callback=reload_callback,
            reload_delay=0.5,
        )

        print(f"Handler created for: {handler.config_path}")
        print(f"Reload delay: {handler.reload_delay}s")

        # Simulate file modification event
        print("\n--- Simulating file modification ---")

        class MockEvent:
            def __init__(self, path: str):
                self.src_path = path
                self.is_directory = False

        # Trigger handler
        event = MockEvent(str(config_path))
        handler.on_modified(event)

        print(f"\nCallbacks triggered: {callback_count[0]}")


# =============================================================================
# Demo 3: Validation Before Reload
# =============================================================================
def demo_validation_before_reload() -> None:
    """Demonstrate validation before config reload."""
    print("\n" + "=" * 60)
    print("Demo 3: Validation Before Reload")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "validate_config.yaml"

        # Create valid configuration
        valid_config = {
            "webhooks": [
                {"url": "https://example.com/webhook", "name": "test"}
            ],
        }

        with open(config_path, "w") as f:
            yaml.dump(valid_config, f)

        reload_success = [0]
        reload_failed = [0]

        def on_reload(config: BotConfig) -> None:
            reload_success[0] += 1
            print(f"  Reload successful!")

        # Create watcher
        watcher = ConfigWatcher(
            config_path=config_path,
            reload_callback=on_reload,
            reload_delay=0.3,
        )
        watcher.start()
        time.sleep(0.5)

        # Test 1: Valid modification
        print("\n--- Test 1: Valid configuration change ---")
        valid_config["webhooks"].append(
            {"url": "https://example.com/webhook2", "name": "test2"}
        )
        with open(config_path, "w") as f:
            yaml.dump(valid_config, f)
        time.sleep(1)

        # Test 2: Invalid modification (missing required field)
        print("\n--- Test 2: Invalid configuration (will be rejected) ---")
        invalid_config = {"webhooks": [{"name": "missing_url"}]}  # Missing 'url'
        with open(config_path, "w") as f:
            yaml.dump(invalid_config, f)
        time.sleep(1)

        # Test 3: Invalid YAML syntax
        print("\n--- Test 3: Invalid YAML syntax (will be rejected) ---")
        with open(config_path, "w") as f:
            f.write("invalid: yaml: syntax: [")
        time.sleep(1)

        # Restore valid config
        print("\n--- Restoring valid configuration ---")
        with open(config_path, "w") as f:
            yaml.dump(valid_config, f)
        time.sleep(1)

        watcher.stop()

        print(f"\nSuccessful reloads: {reload_success[0]}")


# =============================================================================
# Demo 4: Debouncing Rapid Changes
# =============================================================================
def demo_debouncing() -> None:
    """Demonstrate debouncing of rapid configuration changes."""
    print("\n" + "=" * 60)
    print("Demo 4: Debouncing Rapid Changes")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "debounce_config.yaml"

        # Create configuration
        config_data = {
            "webhooks": [{"url": "https://example.com/webhook", "name": "test"}],
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        reload_count = [0]
        reload_times = []

        def on_reload(config: BotConfig) -> None:
            reload_count[0] += 1
            reload_times.append(time.time())
            print(f"  Reload #{reload_count[0]} at {time.strftime('%H:%M:%S')}")

        # Create watcher with 1 second debounce
        watcher = ConfigWatcher(
            config_path=config_path,
            reload_callback=on_reload,
            reload_delay=1.0,  # 1 second debounce
        )
        watcher.start()
        time.sleep(0.5)

        # Make rapid changes
        print("\n--- Making 5 rapid changes (0.2s apart) ---")
        for i in range(5):
            config_data["webhooks"][0]["name"] = f"test_{i}"
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)
            print(f"  Change {i + 1} written")
            time.sleep(0.2)

        # Wait for debounce to complete
        print("\n--- Waiting for debounce ---")
        time.sleep(2)

        watcher.stop()

        print(f"\nTotal changes made: 5")
        print(f"Total reloads triggered: {reload_count[0]}")
        print("(Debouncing should reduce the number of reloads)")


# =============================================================================
# Demo 5: Multiple Config Watchers
# =============================================================================
def demo_multiple_watchers() -> None:
    """Demonstrate watching multiple configuration files."""
    print("\n" + "=" * 60)
    print("Demo 5: Multiple Config Watchers")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create multiple config files
        configs = {}
        watchers = []

        for name in ["main", "plugins", "ai"]:
            config_path = Path(tmpdir) / f"{name}_config.yaml"
            config_data = {
                "webhooks": [
                    {"url": f"https://example.com/{name}", "name": name}
                ],
            }
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)
            configs[name] = config_path

            # Create watcher for each
            def make_callback(config_name: str):
                def callback(config: BotConfig) -> None:
                    print(f"  [{config_name}] Config reloaded")

                return callback

            watcher = ConfigWatcher(
                config_path=config_path,
                reload_callback=make_callback(name),
                reload_delay=0.3,
            )
            watchers.append((name, watcher))

        # Start all watchers
        print("Starting watchers for: main, plugins, ai")
        for name, watcher in watchers:
            watcher.start()

        time.sleep(0.5)

        # Modify each config
        print("\n--- Modifying configurations ---")
        for name, config_path in configs.items():
            config_data = {
                "webhooks": [
                    {"url": f"https://example.com/{name}_updated", "name": f"{name}_v2"}
                ],
            }
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)
            print(f"  Modified: {name}")
            time.sleep(0.5)

        # Wait for reloads
        time.sleep(1)

        # Stop all watchers
        print("\n--- Stopping all watchers ---")
        for name, watcher in watchers:
            watcher.stop()
            print(f"  Stopped: {name}")


# =============================================================================
# Demo 6: Error Recovery
# =============================================================================
def demo_error_recovery() -> None:
    """Demonstrate error recovery in config watching."""
    print("\n" + "=" * 60)
    print("Demo 6: Error Recovery")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "recovery_config.yaml"

        # Create valid configuration
        valid_config = {
            "webhooks": [{"url": "https://example.com/webhook", "name": "test"}],
        }

        with open(config_path, "w") as f:
            yaml.dump(valid_config, f)

        reload_history = []

        def on_reload(config: BotConfig) -> None:
            reload_history.append(("success", len(config.webhooks)))
            print(f"  Reload SUCCESS: {len(config.webhooks)} webhooks")

        watcher = ConfigWatcher(
            config_path=config_path,
            reload_callback=on_reload,
            reload_delay=0.3,
        )
        watcher.start()
        time.sleep(0.5)

        # Sequence of changes
        print("\n--- Change sequence ---")

        # 1. Valid change
        print("\n1. Valid change")
        valid_config["webhooks"].append(
            {"url": "https://example.com/webhook2", "name": "test2"}
        )
        with open(config_path, "w") as f:
            yaml.dump(valid_config, f)
        time.sleep(1)

        # 2. Break the config
        print("\n2. Breaking configuration (invalid)")
        with open(config_path, "w") as f:
            f.write("broken: [yaml")
        time.sleep(1)

        # 3. Fix the config
        print("\n3. Fixing configuration")
        with open(config_path, "w") as f:
            yaml.dump(valid_config, f)
        time.sleep(1)

        # 4. Another valid change
        print("\n4. Another valid change")
        valid_config["webhooks"].append(
            {"url": "https://example.com/webhook3", "name": "test3"}
        )
        with open(config_path, "w") as f:
            yaml.dump(valid_config, f)
        time.sleep(1)

        watcher.stop()

        print(f"\n--- Reload History ---")
        for status, webhooks in reload_history:
            print(f"  {status}: {webhooks} webhooks")


# =============================================================================
# Demo 7: Real-World Usage Pattern
# =============================================================================
def demo_real_world_pattern() -> None:
    """Demonstrate a real-world usage pattern."""
    print("\n" + "=" * 60)
    print("Demo 7: Real-World Usage Pattern")
    print("=" * 60)

    class BotWithHotReload:
        """Example bot with hot-reload support."""

        def __init__(self, config_path: Path):
            self.config_path = config_path
            self.config: BotConfig | None = None
            self.watcher: ConfigWatcher | None = None
            self._running = False
            self._lock = threading.Lock()

        def start(self) -> None:
            """Start the bot with config watching."""
            # Load initial config
            self._load_config()

            # Start config watcher
            self.watcher = ConfigWatcher(
                config_path=self.config_path,
                reload_callback=self._on_config_change,
                reload_delay=1.0,
            )
            self.watcher.start()
            self._running = True
            print(f"Bot started with config: {self.config_path}")

        def stop(self) -> None:
            """Stop the bot."""
            if self.watcher:
                self.watcher.stop()
            self._running = False
            print("Bot stopped")

        def _load_config(self) -> None:
            """Load configuration from file."""
            with open(self.config_path) as f:
                data = yaml.safe_load(f)
            self.config = BotConfig(**data)

        def _on_config_change(self, new_config: BotConfig) -> None:
            """Handle configuration change."""
            with self._lock:
                old_webhooks = len(self.config.webhooks) if self.config else 0
                new_webhooks = len(new_config.webhooks)

                self.config = new_config

                print(f"  Configuration updated:")
                print(f"    Webhooks: {old_webhooks} -> {new_webhooks}")

                # Apply changes (in real bot, would update components)
                self._apply_config_changes()

        def _apply_config_changes(self) -> None:
            """Apply configuration changes to running components."""
            # In a real bot, this would:
            # - Update webhook clients
            # - Reconfigure scheduler
            # - Reload plugins
            # - etc.
            print("    Changes applied to running components")

        def get_status(self) -> dict:
            """Get bot status."""
            return {
                "running": self._running,
                "config_loaded": self.config is not None,
                "webhooks": len(self.config.webhooks) if self.config else 0,
                "watcher_active": (
                    self.watcher.is_running if self.watcher else False
                ),
            }

    # Use the bot
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "bot_config.yaml"

        # Create initial config
        config_data = {
            "webhooks": [{"url": "https://example.com/webhook", "name": "main"}],
            "scheduler": {"enabled": True},
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        # Create and start bot
        bot = BotWithHotReload(config_path)
        bot.start()

        print(f"\nInitial status: {bot.get_status()}")

        # Simulate runtime config changes
        print("\n--- Simulating runtime config changes ---")

        time.sleep(1)

        # Add a webhook
        print("\nAdding a webhook...")
        config_data["webhooks"].append(
            {"url": "https://example.com/webhook2", "name": "secondary"}
        )
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        time.sleep(2)

        # Change scheduler setting
        print("\nChanging scheduler setting...")
        config_data["scheduler"]["timezone"] = "UTC"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        time.sleep(2)

        print(f"\nFinal status: {bot.get_status()}")

        # Stop bot
        bot.stop()


# =============================================================================
# Main Entry Point
# =============================================================================
def main() -> None:
    """Run all config watcher demonstrations."""
    print("=" * 60)
    print("Configuration Hot-Reload Examples")
    print("=" * 60)

    demos = [
        ("Basic Config Watcher Setup", demo_basic_config_watcher),
        ("Config File Handler", demo_config_file_handler),
        ("Validation Before Reload", demo_validation_before_reload),
        ("Debouncing Rapid Changes", demo_debouncing),
        ("Multiple Config Watchers", demo_multiple_watchers),
        ("Error Recovery", demo_error_recovery),
        ("Real-World Usage Pattern", demo_real_world_pattern),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            demo_func()
        except Exception as e:
            print(f"\nDemo {i} ({name}) failed with error: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print("All demonstrations completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
