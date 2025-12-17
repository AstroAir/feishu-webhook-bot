#!/usr/bin/env python3
"""Basic Bot Example.

This example demonstrates the basic usage of FeishuBot:
- Creating a bot from configuration
- Sending different message types
- Using the scheduler
- Plugin integration basics
- Event handling

This is the recommended starting point for new users.
"""

import os
import tempfile
from pathlib import Path

import yaml

from feishu_webhook_bot import FeishuBot
from feishu_webhook_bot.core import (
    BotConfig,
    LoggingConfig,
    WebhookConfig,
    get_logger,
    setup_logging,
)

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)


# =============================================================================
# Demo 1: Create Bot from Code
# =============================================================================
def demo_create_bot_from_code() -> None:
    """Demonstrate creating a bot programmatically."""
    print("\n" + "=" * 60)
    print("Demo 1: Create Bot from Code")
    print("=" * 60)

    # Get webhook URL from environment
    webhook_url = os.environ.get(
        "FEISHU_WEBHOOK_URL",
        "https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-id",
    )
    webhook_secret = os.environ.get("FEISHU_WEBHOOK_SECRET")

    # Create configuration
    config = BotConfig(
        webhooks=[
            WebhookConfig(
                url=webhook_url,
                name="default",
                secret=webhook_secret,
            )
        ],
        scheduler={"enabled": True, "timezone": "Asia/Shanghai"},
    )

    print("BotConfig created:")
    print(f"  Webhooks: {len(config.webhooks)}")
    print(f"  Scheduler enabled: {config.scheduler.enabled}")
    print(f"  Timezone: {config.scheduler.timezone}")

    # Create bot
    bot = FeishuBot(config)
    print("\nFeishuBot created")
    print(f"  Client available: {bot.client is not None}")


# =============================================================================
# Demo 2: Create Bot from YAML Config
# =============================================================================
def demo_create_bot_from_yaml() -> None:
    """Demonstrate creating a bot from YAML configuration."""
    print("\n" + "=" * 60)
    print("Demo 2: Create Bot from YAML Config")
    print("=" * 60)

    # Create temporary config file
    config_data = {
        "webhooks": [
            {
                "url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
                "name": "default",
            }
        ],
        "scheduler": {
            "enabled": True,
            "timezone": "Asia/Shanghai",
        },
        "plugins": {
            "enabled": True,
            "plugin_dir": "./plugins",
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name

    print(f"Config file created: {config_path}")

    # Create bot from config file
    try:
        bot = FeishuBot.from_config(config_path)
        print("\nBot created from config file")
        print(f"  Webhooks: {len(bot.config.webhooks)}")
    finally:
        # Cleanup
        Path(config_path).unlink()


# =============================================================================
# Demo 3: Sending Messages
# =============================================================================
def demo_sending_messages() -> None:
    """Demonstrate sending different message types."""
    print("\n" + "=" * 60)
    print("Demo 3: Sending Messages")
    print("=" * 60)

    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL")

    if not webhook_url:
        print("FEISHU_WEBHOOK_URL not set. Showing message examples only.")

        print("\n1. Text Message:")
        print('   bot.client.send_text("Hello, World!")')

        print("\n2. Rich Text Message:")
        print("""   bot.client.send_rich_text(
       title="Report",
       content=[
           [{"tag": "text", "text": "Hello "}],
           [{"tag": "at", "user_id": "all"}],
       ]
   )""")

        print("\n3. Interactive Card:")
        print("""   card = {
       "header": {"title": {"content": "Alert", "tag": "plain_text"}},
       "elements": [
           {"tag": "div", "text": {"content": "Message", "tag": "plain_text"}}
       ]
   }
   bot.client.send_card(card)""")

        print("\n4. Image Message:")
        print('   bot.client.send_image("img_v2_xxx")')
        return

    # Create bot
    config = BotConfig(webhooks=[WebhookConfig(url=webhook_url, name="default")])
    bot = FeishuBot(config)

    # Send text message
    print("\nSending text message...")
    result = bot.client.send_text("Hello from Basic Bot Example!")
    print(f"Result: {result}")


# =============================================================================
# Demo 4: Bot Configuration Options
# =============================================================================
def demo_configuration_options() -> None:
    """Demonstrate various bot configuration options."""
    print("\n" + "=" * 60)
    print("Demo 4: Bot Configuration Options")
    print("=" * 60)

    print("Available configuration options:")

    print("\n1. Webhooks:")
    print("""   webhooks:
     - url: "https://..."
       name: "default"
       secret: "optional_secret"
     - url: "https://..."
       name: "alerts"
""")

    print("2. Scheduler:")
    print("""   scheduler:
     enabled: true
     timezone: "Asia/Shanghai"
     job_store_type: "memory"  # or "sqlite"
     job_store_url: "jobs.db"
""")

    print("3. Plugins:")
    print("""   plugins:
     enabled: true
     plugin_dir: "./plugins"
     hot_reload: true
     auto_load: true
""")

    print("4. Logging:")
    print("""   logging:
     level: "INFO"
     format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
     file: "bot.log"
""")

    print("5. Authentication (optional):")
    print("""   auth:
     enabled: true
     secret_key: "your-secret-key"
     token_expire_minutes: 30
""")


# =============================================================================
# Demo 5: Using the Scheduler
# =============================================================================
def demo_using_scheduler() -> None:
    """Demonstrate using the task scheduler."""
    print("\n" + "=" * 60)
    print("Demo 5: Using the Scheduler")
    print("=" * 60)

    print("The scheduler allows you to run tasks on a schedule:")

    print("\n1. Interval-based scheduling:")
    print("""   from feishu_webhook_bot import job

   @job(trigger='interval', minutes=30)
   def send_status_update():
       bot.client.send_text("Status: All systems operational")
""")

    print("\n2. Cron-based scheduling:")
    print("""   @job(trigger='cron', hour=9, minute=0)
   def send_morning_report():
       bot.client.send_text("Good morning! Here's your daily report...")
""")

    print("\n3. One-time scheduling:")
    print("""   from datetime import datetime, timedelta

   run_time = datetime.now() + timedelta(hours=1)
   scheduler.add_job(
       send_reminder,
       trigger='date',
       run_date=run_time
   )
""")

    print("\n4. Managing jobs:")
    print("""   # List all jobs
   jobs = scheduler.get_jobs()

   # Pause a job
   scheduler.pause_job(job_id)

   # Resume a job
   scheduler.resume_job(job_id)

   # Remove a job
   scheduler.remove_job(job_id)
""")


# =============================================================================
# Demo 6: Plugin Integration
# =============================================================================
def demo_plugin_integration() -> None:
    """Demonstrate plugin integration basics."""
    print("\n" + "=" * 60)
    print("Demo 6: Plugin Integration")
    print("=" * 60)

    print("Creating a simple plugin:")
    print("""
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class MyPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-plugin",
            version="1.0.0",
            description="My custom plugin"
        )

    def on_load(self) -> None:
        self.logger.info("Plugin loaded!")

    def on_enable(self) -> None:
        # Register scheduled jobs
        self.register_job(
            self.daily_task,
            trigger='cron',
            hour=9
        )

    def daily_task(self) -> None:
        self.client.send_text("Daily task executed!")

    def on_event(self, event: dict) -> None:
        # Handle incoming events
        if event.get("type") == "message":
            self.handle_message(event)
""")

    print("\nLoading plugins:")
    print("""   # In config.yaml
   plugins:
     enabled: true
     plugin_dir: "./plugins"

   # Or programmatically
   bot.plugin_manager.load_plugin("path/to/plugin.py")
""")


# =============================================================================
# Demo 7: Event Handling
# =============================================================================
def demo_event_handling() -> None:
    """Demonstrate event handling."""
    print("\n" + "=" * 60)
    print("Demo 7: Event Handling")
    print("=" * 60)

    print("Setting up event handling:")
    print("""
# In your plugin or bot setup:

def handle_message(event: dict) -> None:
    '''Handle incoming message events.'''
    message = event.get("message", {})
    content = message.get("content", "")
    sender = event.get("sender", {}).get("sender_id", {})

    # Process the message
    if "help" in content.lower():
        bot.client.send_text("Available commands: /status, /help")
    elif content.startswith("/status"):
        bot.client.send_text("All systems operational!")

# Register the handler
bot.on_event("message", handle_message)
""")

    print("\nEvent types:")
    print("  - message: Text messages from users")
    print("  - message_reaction: Reactions to messages")
    print("  - url_verification: Webhook URL verification")
    print("  - card_action: Interactive card button clicks")


# =============================================================================
# Demo 8: Complete Bot Example
# =============================================================================
def demo_complete_example() -> None:
    """Show a complete bot example."""
    print("\n" + "=" * 60)
    print("Demo 8: Complete Bot Example")
    print("=" * 60)

    print("""
# main.py - Complete Feishu Bot Example

import os
from feishu_webhook_bot import FeishuBot, job
from feishu_webhook_bot.core import BotConfig, WebhookConfig

# Configuration
config = BotConfig(
    webhooks=[
        WebhookConfig(
            url=os.environ["FEISHU_WEBHOOK_URL"],
            name="default",
            secret=os.environ.get("FEISHU_WEBHOOK_SECRET"),
        )
    ],
    scheduler={
        "enabled": True,
        "timezone": "Asia/Shanghai",
    },
    plugins={
        "enabled": True,
        "plugin_dir": "./plugins",
    },
)

# Create bot
bot = FeishuBot(config)

# Define scheduled tasks
@job(trigger='cron', hour=9, minute=0)
def morning_greeting():
    bot.client.send_text("Good morning! Have a productive day!")

@job(trigger='interval', hours=1)
def hourly_status():
    bot.client.send_text("Hourly status: All systems operational")

# Event handler
def handle_message(event: dict):
    content = event.get("message", {}).get("content", "")
    if "ping" in content.lower():
        bot.client.send_text("pong!")

bot.on_event("message", handle_message)

# Start the bot
if __name__ == "__main__":
    print("Starting Feishu Bot...")
    bot.start()
""")


# =============================================================================
# Main Entry Point
# =============================================================================
def main() -> None:
    """Run all basic bot demonstrations."""
    print("=" * 60)
    print("Basic Bot Examples")
    print("=" * 60)

    demos = [
        ("Create Bot from Code", demo_create_bot_from_code),
        ("Create Bot from YAML Config", demo_create_bot_from_yaml),
        ("Sending Messages", demo_sending_messages),
        ("Configuration Options", demo_configuration_options),
        ("Using the Scheduler", demo_using_scheduler),
        ("Plugin Integration", demo_plugin_integration),
        ("Event Handling", demo_event_handling),
        ("Complete Bot Example", demo_complete_example),
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
