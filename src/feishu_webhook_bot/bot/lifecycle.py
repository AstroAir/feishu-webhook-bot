"""Lifecycle management mixin for FeishuBot."""

from __future__ import annotations

import asyncio
import signal
from types import FrameType
from typing import TYPE_CHECKING

from ..core import get_logger

if TYPE_CHECKING:
    from .base import BotBase

logger = get_logger("bot.lifecycle")


class LifecycleMixin:
    """Mixin for bot lifecycle management (start/stop/signals)."""

    async def _run_message_queue_processor(self: BotBase) -> None:
        """Run message queue processor in background loop.

        This method runs continuously while the bot is running,
        processing queued messages with error handling and backoff.
        """
        while self._running:
            try:
                if self.message_queue:
                    await self.message_queue.process_queue()
                await asyncio.sleep(1.0)  # Process interval
            except asyncio.CancelledError:
                logger.info("Message queue processor cancelled")
                break
            except Exception as exc:
                logger.error("Message queue processing error: %s", exc, exc_info=True)
                await asyncio.sleep(5.0)  # Backoff on error

    def _setup_signal_handlers(self: BotBase) -> None:
        """Setup signal handlers for graceful shutdown."""
        if self._signal_handlers_installed:
            return

        def signal_handler(sig: int, frame: FrameType | None) -> None:
            logger.info("Received signal %s, initiating shutdown", sig)
            self._shutdown_event.set()
            self.stop()

        for sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
            if sig is None:
                continue
            try:
                previous = signal.getsignal(sig)
                self._signal_handlers[sig] = previous
                signal.signal(sig, signal_handler)
            except (AttributeError, OSError, ValueError) as exc:
                logger.warning("Unable to register handler for signal %s: %s", sig, exc)

        self._signal_handlers_installed = True

    def _wait_for_shutdown(self: BotBase) -> None:
        """Block until a shutdown event is triggered."""
        while self._running:
            try:
                if self._shutdown_event.wait(timeout=1.0):
                    break
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received; signalling shutdown")
                self._shutdown_event.set()
                break

    def _restore_signal_handlers(self: BotBase) -> None:
        """Restore original signal handlers if they were overridden."""
        if not self._signal_handlers_installed:
            return

        for sig, handler in self._signal_handlers.items():
            try:
                handler_to_set = handler if handler is not None else signal.SIG_DFL
                signal.signal(sig, handler_to_set)
            except (AttributeError, OSError, ValueError) as exc:
                logger.debug("Unable to restore handler for signal %s: %s", sig, exc)

        self._signal_handlers.clear()
        self._signal_handlers_installed = False

    def start(self: BotBase) -> None:
        """Start the bot.

        This initializes all components and starts the scheduler.
        The bot will run until interrupted.
        """
        if self._running:
            logger.warning("Bot is already running")
            return

        logger.info("Starting Feishu Bot...")
        self._shutdown_event.clear()

        try:
            # Connect all providers
            for name, provider in self.providers.items():
                try:
                    provider.connect()
                    logger.info("Provider connected: %s", name)
                except Exception as exc:
                    logger.error("Failed to connect provider '%s': %s", name, exc, exc_info=True)
                    raise

            # Start scheduler
            if self.scheduler:
                try:
                    self.scheduler.start()
                    logger.info("Scheduler started")
                except Exception as exc:
                    logger.error("Failed to start scheduler: %s", exc, exc_info=True)
                    raise

            if self.automation_engine:
                try:
                    self.automation_engine.start()
                    logger.info("Automation engine started")
                except Exception as exc:
                    logger.error(
                        "Failed to start automation engine: %s",
                        exc,
                        exc_info=True,
                    )
                    raise

            if self.task_manager:
                try:
                    self.task_manager.start()
                    logger.info("Task manager started")
                except Exception as exc:
                    logger.error("Failed to start task manager: %s", exc, exc_info=True)
                    raise

            if self.config_watcher:
                try:
                    self.config_watcher.start()
                    logger.info("Configuration watcher started")
                except Exception as exc:
                    logger.warning(
                        "Failed to start config watcher: %s",
                        exc,
                        exc_info=True,
                    )

            if self.ai_agent:
                try:
                    self.ai_agent.start()
                    logger.info("AI agent started")
                except Exception as exc:
                    logger.error("Failed to start AI agent: %s", exc, exc_info=True)
                    raise

            # Start message queue processor
            if self.message_queue:
                try:
                    self._message_queue_task = asyncio.create_task(
                        self._run_message_queue_processor()
                    )
                    logger.info("Message queue processor started")
                except Exception as exc:
                    logger.warning(
                        "Failed to start message queue processor: %s", exc, exc_info=True
                    )

            self._running = True
            try:
                self._setup_signal_handlers()
            except Exception as exc:
                logger.warning(
                    "Failed to set up signal handlers; continuing without them: %s",
                    exc,
                    exc_info=True,
                )

            logger.info("🚀 Feishu Bot is running!")

            event_config = getattr(self.config, "event_server", None)
            if (
                self.event_server
                and event_config
                and event_config.enabled
                and event_config.auto_start
            ):
                try:
                    self.event_server.start()
                except Exception as exc:
                    logger.error("Failed to start event server: %s", exc, exc_info=True)
                    raise

            # Send startup notification (with pre-validation)
            if self.client:
                # Validate webhook before attempting to send
                is_valid, error_msg = self.client.validate_webhook()
                if not is_valid:
                    logger.warning(
                        "Startup notification skipped: %s",
                        error_msg or "webhook not properly configured",
                    )
                elif not self.client.is_configured():
                    logger.warning(
                        "Startup notification skipped: webhook URL appears to be a placeholder"
                    )
                else:
                    try:
                        self.client.send_text("🤖 Feishu Bot started successfully!")
                    except Exception as exc:
                        logger.warning(
                            "Failed to send startup notification: %s", exc, exc_info=True
                        )
            else:
                logger.warning("No default webhook client configured; startup notification skipped")

            # Keep the main thread alive by waiting for shutdown signal
            pause_fn = getattr(signal, "pause", None)
            if callable(pause_fn):
                try:
                    pause_fn()
                except (KeyboardInterrupt, SystemExit):
                    logger.info("Keyboard interrupt received; signalling shutdown")
                    self._shutdown_event.set()
            else:
                self._wait_for_shutdown()

        except Exception as exc:
            logger.error("Error starting bot: %s", exc, exc_info=True)
            if self._running:
                self.stop()
            raise
        finally:
            if not self._running:
                self._restore_signal_handlers()

    def stop(self: BotBase) -> None:
        """Stop the bot and clean up resources."""
        self._shutdown_event.set()

        if not self._running:
            self._restore_signal_handlers()
            return

        logger.info("Stopping Feishu Bot...")

        try:
            # Send shutdown notification
            if self.client:
                try:
                    self.client.send_text("🛑 Feishu Bot is shutting down...")
                except Exception as exc:
                    logger.warning("Failed to send shutdown notification: %s", exc, exc_info=True)

            # Stop hot reload
            if self.plugin_manager:
                try:
                    self.plugin_manager.stop_hot_reload()
                except Exception as exc:
                    logger.error("Failed to stop plugin hot reload: %s", exc, exc_info=True)

            # Disable all plugins
            if self.plugin_manager:
                try:
                    self.plugin_manager.disable_all()
                except Exception as exc:
                    logger.error("Failed to disable plugins: %s", exc, exc_info=True)

            if self.event_server and self.event_server.is_running:
                try:
                    self.event_server.stop()
                except Exception as exc:
                    logger.error("Failed to stop event server: %s", exc, exc_info=True)

            if self.automation_engine:
                try:
                    self.automation_engine.shutdown()
                except Exception as exc:
                    logger.error("Failed to shutdown automation engine: %s", exc, exc_info=True)

            # Stop task manager
            if self.task_manager:
                try:
                    self.task_manager.stop()
                except Exception as exc:
                    logger.error("Failed to stop task manager: %s", exc, exc_info=True)

            # Stop config watcher
            if self.config_watcher:
                try:
                    self.config_watcher.stop()
                except Exception as exc:
                    logger.error("Failed to stop config watcher: %s", exc, exc_info=True)

            # Stop AI agent
            if self.ai_agent:
                try:
                    import asyncio

                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self.ai_agent.stop())
                    else:
                        loop.run_until_complete(self.ai_agent.stop())
                except Exception as exc:
                    logger.error("Failed to stop AI agent: %s", exc, exc_info=True)

            # Stop scheduler
            if self.scheduler:
                try:
                    self.scheduler.shutdown()
                except Exception as exc:
                    logger.error("Failed to shutdown scheduler: %s", exc, exc_info=True)

            # Stop message queue processor
            if self._message_queue_task:
                try:
                    self._message_queue_task.cancel()
                    logger.info("Message queue processor stopped")
                except Exception as exc:
                    logger.error("Failed to stop message queue: %s", exc, exc_info=True)

            # Stop message tracker cleanup thread
            if self.message_tracker:
                try:
                    self.message_tracker.stop_cleanup()
                    logger.info("Message tracker stopped")
                except Exception as exc:
                    logger.error("Failed to stop message tracker: %s", exc, exc_info=True)

            # Disconnect all providers
            for name, provider in self.providers.items():
                try:
                    provider.disconnect()
                    logger.info("Provider disconnected: %s", name)
                except Exception as exc:
                    logger.error("Error disconnecting provider %s: %s", name, exc, exc_info=True)

            # Close clients
            for name, client in self.clients.items():
                try:
                    client.close()
                except Exception as exc:
                    logger.error("Error closing client %s: %s", name, exc, exc_info=True)

        except Exception as exc:
            logger.error("Error stopping bot: %s", exc, exc_info=True)
        finally:
            self._running = False
            self._restore_signal_handlers()
            logger.info("Feishu Bot stopped")
