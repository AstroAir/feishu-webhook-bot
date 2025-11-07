"""Example plugin: Periodic Reminder.

This plugin sends customizable reminders at specified intervals.
"""

from datetime import datetime

from feishu_webhook_bot.core.client import CardBuilder
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata


class ReminderPlugin(BasePlugin):
    """Plugin that sends periodic reminders."""

    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="reminder",
            version="1.0.0",
            description="Sends customizable reminders at specified times",
            author="Feishu Bot Team",
            enabled=True,
        )

    def on_load(self) -> None:
        """Called when plugin is loaded."""
        self.logger.info("Reminder plugin loaded")

        # Define your reminders here
        self.reminders = [
            {
                "name": "Stand up meeting",
                "time": {"hour": "10", "minute": "0"},
                "message": "🗓️ Time for daily stand-up meeting!",
                "days": "mon-fri",  # Monday to Friday
            },
            {
                "name": "Lunch break",
                "time": {"hour": "12", "minute": "30"},
                "message": "🍱 Time for lunch! Take a break.",
                "days": "mon-fri",
            },
            {
                "name": "End of day",
                "time": {"hour": "18", "minute": "0"},
                "message": "🏠 End of workday! Don't forget to commit your code.",
                "days": "mon-fri",
            },
        ]

    def on_enable(self) -> None:
        """Called when plugin is enabled."""
        # Schedule all reminders
        for reminder in self.reminders:
            job_id = f"reminder_{reminder['name'].replace(' ', '_')}"

            trigger_args = {
                "hour": reminder["time"]["hour"],
                "minute": reminder["time"]["minute"],
            }

            # Add day_of_week if specified
            if "days" in reminder:
                trigger_args["day_of_week"] = reminder["days"]

            self.register_job(
                lambda r=reminder: self.send_reminder(r),
                trigger="cron",
                job_id=job_id,
                **trigger_args,
            )

            self.logger.info(
                f"Scheduled reminder: {reminder['name']} at "
                f"{reminder['time']['hour']}:{reminder['time']['minute']}"
            )

    def send_reminder(self, reminder: dict) -> None:
        """Send a reminder message.

        Args:
            reminder: Reminder configuration dict
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Build reminder card
            card = (
                CardBuilder()
                .set_config(wide_screen_mode=True)
                .set_header(f"⏰ {reminder['name']}", template="orange")
                .add_markdown(reminder["message"])
                .add_divider()
                .add_note(f"Reminder at {timestamp}")
                .build()
            )

            self.client.send_card(card)
            self.logger.info(f"Reminder sent: {reminder['name']}")

        except Exception as e:
            self.logger.error(f"Failed to send reminder '{reminder['name']}': {e}", exc_info=True)

    def on_disable(self) -> None:
        """Called when plugin is disabled."""
        self.logger.info("Reminder plugin disabled")
