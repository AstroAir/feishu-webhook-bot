"""Scheduler and task initialization mixin for FeishuBot."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...core import get_logger
from ...scheduler import TaskScheduler
from ...tasks import TaskManager

if TYPE_CHECKING:
    from ..base import BotBase

logger = get_logger("bot.init.scheduler")


class SchedulerInitializerMixin:
    """Mixin for scheduler and task manager initialization."""

    def _init_scheduler(self: BotBase) -> None:
        """Initialize task scheduler if enabled."""
        scheduler_config = getattr(self.config, "scheduler", None)
        if scheduler_config is None:
            logger.warning("Scheduler configuration missing; scheduler disabled")
            return

        enabled_flag = getattr(scheduler_config, "enabled", None)
        if not isinstance(enabled_flag, bool):
            logger.debug(
                "Skipping scheduler initialization; "
                "scheduler config does not provide a boolean 'enabled' flag"
            )
            return

        if not scheduler_config.enabled:
            logger.info("Scheduler is disabled")
            return

        try:
            self.scheduler = TaskScheduler(scheduler_config)
        except Exception as exc:
            logger.error("Failed to initialize scheduler: %s", exc, exc_info=True)
            raise

        logger.info("Scheduler initialized")

    def _init_tasks(self: BotBase) -> None:
        """Initialize task manager for automated tasks."""
        tasks = getattr(self.config, "tasks", []) or []
        if not tasks:
            logger.info("No tasks configured")
            return

        if not self.scheduler:
            logger.warning("Scheduler not available; tasks will not be scheduled")
            return

        try:
            self.task_manager = TaskManager(
                config=self.config,
                scheduler=self.scheduler,
                plugin_manager=self.plugin_manager,
                clients=self.clients,
                ai_agent=self.ai_agent,  # Pass AI agent for ai_chat/ai_query actions
                providers=self.providers,
                template_registry=self.template_registry,
            )
            logger.info("Task manager configured with %s task(s)", len(tasks))
        except Exception as exc:
            logger.error("Failed to initialize task manager: %s", exc, exc_info=True)
            raise
