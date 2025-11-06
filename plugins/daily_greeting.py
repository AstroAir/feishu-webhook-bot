"""Example plugin: Daily Good Morning greeting.

This plugin sends a good morning message every day at a specified time.
"""

from datetime import datetime

from feishu_webhook_bot.core.client import CardBuilder
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata


class DailyGreetingPlugin(BasePlugin):
    """Plugin that sends daily greeting messages."""

    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="daily-greeting",
            version="1.0.0",
            description="Sends a good morning message every day at 9:00 AM",
            author="Feishu Bot Team",
            enabled=True,
        )

    def on_load(self) -> None:
        """Called when plugin is loaded."""
        self.logger.info("Daily Greeting plugin loaded")

    def on_enable(self) -> None:
        """Called when plugin is enabled."""
        # Schedule daily greeting at 9:00 AM
        self.register_job(
            self.send_morning_greeting,
            trigger="cron",
            hour="9",
            minute="0",
            job_id="daily_greeting_morning",
        )

        # Optional: Also send at noon
        # self.register_job(
        #     self.send_noon_greeting,
        #     trigger="cron",
        #     hour="12",
        #     minute="0",
        #     job_id="daily_greeting_noon",
        # )

        self.logger.info("Daily greeting scheduled for 9:00 AM every day")

    def send_morning_greeting(self) -> None:
        """Send morning greeting message."""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d %A")

            # Build an interactive card
            card = (
                CardBuilder()
                .set_config(wide_screen_mode=True)
                .set_header("☀️ Good Morning!", template="blue")
                .add_markdown(f"**Date:** {current_date}")
                .add_divider()
                .add_text("Have a great day ahead! 💪")
                .add_note("This is an automated message from Feishu Bot")
                .build()
            )

            self.client.send_card(card)
            self.logger.info("Morning greeting sent successfully")

        except Exception as e:
            self.logger.error(f"Failed to send morning greeting: {e}", exc_info=True)

    def send_noon_greeting(self) -> None:
        """Send noon greeting message."""
        try:
            self.client.send_text("🍜 Lunch time! Don't forget to take a break!")
            self.logger.info("Noon greeting sent successfully")

        except Exception as e:
            self.logger.error(f"Failed to send noon greeting: {e}", exc_info=True)

    def on_disable(self) -> None:
        """Called when plugin is disabled."""
        self.logger.info("Daily Greeting plugin disabled")
