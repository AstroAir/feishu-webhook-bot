#!/usr/bin/env python3
"""Example: Using the Feishu Calendar Plugin

This script demonstrates how to:
1. Create a bot with the calendar plugin
2. Configure calendar monitoring
3. Send event reminders
"""

import asyncio
import os
from pathlib import Path

from feishu_webhook_bot import FeishuBot
from feishu_webhook_bot.core.config import BotConfig
from feishu_webhook_bot.core.logger import setup_logging


def setup_calendar_plugin_example():
    """Setup and run bot with calendar plugin."""

    # 1. Setup logging
    setup_logging()

    # 2. Create configuration from file
    config_path = Path(__file__).parent / "feishu_calendar_config.yaml"

    if not config_path.exists():
        print(f"Error: Configuration file not found at {config_path}")
        print("Please copy feishu_calendar_config.yaml to the examples directory")
        return

    # 3. Load bot configuration
    try:
        config = BotConfig.from_file(str(config_path))
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return

    # 4. Verify environment variables are set
    if not os.getenv("FEISHU_APP_ID") or not os.getenv("FEISHU_APP_SECRET"):
        print("Error: FEISHU_APP_ID and FEISHU_APP_SECRET environment variables must be set")
        print("\nSet them with:")
        print('  export FEISHU_APP_ID="your_app_id"')
        print('  export FEISHU_APP_SECRET="your_app_secret"')
        return

    # 5. Create and start bot
    print("Initializing bot with Feishu Calendar plugin...")
    bot = FeishuBot.from_config(config)

    try:
        # Start the bot
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Error running bot: {e}")
        import traceback
        traceback.print_exc()


def minimal_calendar_setup():
    """Minimal example of calendar plugin setup in code.

    This shows how to programmatically configure the calendar plugin
    without using a YAML file.
    """

    from feishu_webhook_bot.core.config import (
        BotConfig,
        WebhookConfig,
        PluginConfig,
        PluginSettings,
    )

    # Create webhook configuration
    webhook_config = WebhookConfig(
        name="default",
        url="https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_ID",
    )

    # Create plugin settings for calendar plugin
    plugin_settings = PluginSettings(
        plugin_name="feishu-calendar",
        enabled=True,
        settings={
            "app_id": os.getenv("FEISHU_APP_ID"),
            "app_secret": os.getenv("FEISHU_APP_SECRET"),
            "calendar_ids": ["primary"],
            "check_interval_minutes": 5,
            "reminder_minutes": [15, 5],
            "webhook_name": "default",
        },
    )

    # Create plugin configuration
    plugin_config = PluginConfig(
        enabled=True,
        plugin_settings=[plugin_settings],
    )

    # Create bot configuration
    config = BotConfig(
        webhooks={"default": webhook_config},
        plugins=plugin_config,
    )

    # Initialize and start bot
    print("Initializing bot with calendar plugin (code-based configuration)...")
    bot = FeishuBot.from_config(config)

    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\nBot stopped by user")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--code-config":
        print("Running with code-based configuration...")
        minimal_calendar_setup()
    else:
        print("Running with YAML configuration...")
        print("(Use --code-config to run with code-based configuration)")
        setup_calendar_plugin_example()
