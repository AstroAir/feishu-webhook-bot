"""Example plugin template.

Copy this file to create your own custom plugin.
"""

from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata


class ExamplePlugin(BasePlugin):
    """Example plugin demonstrating the plugin interface."""

    def metadata(self) -> PluginMetadata:
        """Return plugin metadata.

        Returns:
            PluginMetadata with name, version, description, etc.
        """
        return PluginMetadata(
            name="example-plugin",
            version="1.0.0",
            description="An example plugin showing how to create custom plugins",
            author="Your Name",
            enabled=True,  # Set to False to disable by default
        )

    def on_load(self) -> None:
        """Called when plugin is first loaded.

        Use this for:
        - Reading configuration
        - Initializing variables
        - Setting up data structures
        """
        self.logger.info("Example plugin loaded")

        # You can access configuration
        # config_value = self.get_config_value("my_setting", default="default_value")

    def on_enable(self) -> None:
        """Called when plugin is enabled and bot is running.

        Use this for:
        - Registering scheduled jobs
        - Setting up resources
        - Starting background tasks
        """
        self.logger.info("Example plugin enabled")

        # Example: Schedule a task to run every 10 minutes
        self.register_job(
            self.my_periodic_task,
            trigger="interval",
            minutes=10,
            job_id="example_periodic_task",
        )

        # Example: Schedule a task with cron (daily at 9 AM)
        # self.register_job(
        #     self.my_daily_task,
        #     trigger="cron",
        #     hour="9",
        #     minute="0",
        #     job_id="example_daily_task",
        # )

    def my_periodic_task(self) -> None:
        """Example periodic task that runs every 10 minutes."""
        try:
            # Do your work here
            message = "Hello from periodic task!"

            # Send a simple text message
            self.client.send_text(message)

            # Or send an interactive card
            # from feishu_webhook_bot.core.client import CardBuilder
            #
            # card = (
            #     CardBuilder()
            #     .set_header("My Task", template="blue")
            #     .add_markdown("**Status:** Task completed successfully")
            #     .build()
            # )
            # self.client.send_card(card)

            self.logger.info("Periodic task executed successfully")

        except Exception as e:
            self.logger.error(f"Error in periodic task: {e}", exc_info=True)

    def my_daily_task(self) -> None:
        """Example daily task."""
        try:
            self.client.send_text("Daily task executed!")
            self.logger.info("Daily task executed successfully")

        except Exception as e:
            self.logger.error(f"Error in daily task: {e}", exc_info=True)

    def on_disable(self) -> None:
        """Called when plugin is disabled or bot is shutting down.

        Use this for:
        - Cleaning up resources
        - Saving state
        - Closing connections
        """
        self.logger.info("Example plugin disabled")

    def on_unload(self) -> None:
        """Called when plugin is unloaded (before hot-reload).

        Use this for:
        - Final cleanup before reload
        - Closing file handles
        - Releasing locks
        """
        self.logger.info("Example plugin unloaded")
