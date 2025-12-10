"""Task manager for scheduling and managing automated tasks."""

from __future__ import annotations

import contextlib
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from ..core.config import BotConfig, TaskDefinitionConfig
from ..core.logger import get_logger
from ..core.provider import BaseProvider
from ..core.templates import TemplateRegistry
from .executor import TaskExecutor

if TYPE_CHECKING:
    from ..ai.agent import AIAgent

logger = get_logger("task.manager")


class TaskManager:
    """Manages task scheduling and execution."""

    def __init__(
        self,
        config: BotConfig,
        scheduler: Any = None,
        plugin_manager: Any = None,
        clients: dict[str, Any] | None = None,
        ai_agent: AIAgent | None = None,
        providers: dict[str, BaseProvider] | None = None,
        template_registry: TemplateRegistry | None = None,
    ):
        """Initialize task manager.

        Args:
            config: Bot configuration
            scheduler: Task scheduler instance
            plugin_manager: Plugin manager instance
            clients: Dictionary of webhook clients
            ai_agent: AI agent for AI-powered task actions
            providers: Dictionary of message providers (new architecture)
            template_registry: Template registry for rendering message templates
        """
        self.config = config
        self.scheduler = scheduler
        self.plugin_manager = plugin_manager
        self.clients = clients or {}
        self.providers = providers or {}
        self.ai_agent = ai_agent
        self.template_registry = template_registry
        self._registered_jobs: set[str] = set()
        self._task_instances: dict[str, TaskDefinitionConfig] = {}
        self._execution_counts: dict[str, int] = {}
        self._retry_counts: dict[str, int] = {}  # Track retry attempts per task

    def start(self) -> None:
        """Start task manager and register all tasks."""
        logger.info("Starting task manager...")

        # Load tasks from configuration
        for task in self.config.tasks:
            if task.enabled:
                self._register_task(task)

        logger.info(f"Registered {len(self._registered_jobs)} tasks")

    def stop(self) -> None:
        """Stop task manager and unregister all tasks."""
        logger.info("Stopping task manager...")

        if self.scheduler:
            for job_id in list(self._registered_jobs):
                try:
                    self.scheduler.remove_job(job_id)
                except Exception as e:
                    logger.debug(f"Failed to remove job {job_id}: {e}")

        self._registered_jobs.clear()
        logger.info("Task manager stopped")

    def _register_task(self, task: TaskDefinitionConfig) -> None:
        """Register a task with the scheduler.

        Args:
            task: Task definition
        """
        if not self.scheduler:
            logger.warning(f"Scheduler not available, cannot register task: {task.name}")
            return

        # Store task instance
        self._task_instances[task.name] = task
        self._execution_counts[task.name] = 0

        # Determine trigger configuration
        trigger_type = None
        trigger_args = {}

        if task.schedule:
            trigger_type = task.schedule.mode
            trigger_args = task.schedule.arguments
        elif task.cron:
            trigger_type = "cron"
            # Parse cron expression
            # Format: "minute hour day month day_of_week"
            parts = task.cron.split()
            if len(parts) >= 5:
                trigger_args = {
                    "minute": parts[0],
                    "hour": parts[1],
                    "day": parts[2],
                    "month": parts[3],
                    "day_of_week": parts[4],
                }
        elif task.interval:
            trigger_type = "interval"
            trigger_args = task.interval

        if not trigger_type:
            logger.warning(f"No valid trigger configuration for task: {task.name}")
            return

        # Create job function
        def task_runner() -> None:
            self._execute_task(task.name)

        # Register with scheduler
        try:
            job_id = f"task.{task.name}"
            self.scheduler.add_job(
                task_runner,
                trigger=trigger_type,
                job_id=job_id,
                replace_existing=True,
                **trigger_args,
            )
            self._registered_jobs.add(job_id)
            logger.info(f"Registered task '{task.name}' with trigger {trigger_type}")
        except Exception as e:
            logger.error(f"Failed to register task '{task.name}': {e}", exc_info=True)

    def _execute_task(self, task_name: str) -> None:
        """Execute a task by name.

        Args:
            task_name: Name of the task to execute
        """
        task = self._task_instances.get(task_name)
        if not task:
            logger.error(f"Task not found: {task_name}")
            return

        # Check concurrent execution limit
        current_count = self._execution_counts.get(task_name, 0)
        if current_count >= task.max_concurrent:
            logger.warning(
                f"Task {task_name} already running {current_count} instances, "
                f"max concurrent is {task.max_concurrent}"
            )
            return

        # Increment execution count
        self._execution_counts[task_name] = current_count + 1

        try:
            # Build execution context
            context = self._build_context(task)

            # Create executor
            executor = TaskExecutor(
                task=task,
                context=context,
                plugin_manager=self.plugin_manager,
                clients=self.clients,
                ai_agent=self.ai_agent,
                providers=self.providers,
                template_registry=self.template_registry,
            )

            # Execute task
            logger.info(f"Executing task: {task_name}")
            result = executor.execute()

            # Log result
            if result["success"]:
                logger.info(f"Task {task_name} completed successfully in {result['duration']:.2f}s")
                # Reset retry count on success
                self._retry_counts[task_name] = 0
            else:
                logger.error(f"Task {task_name} failed: {result.get('error', 'Unknown error')}")

            # Handle retry on failure
            if not result["success"] and task.error_handling.retry_on_failure:
                self._schedule_retry(task, result)

        except Exception as e:
            logger.error(f"Error executing task {task_name}: {e}", exc_info=True)

        finally:
            # Decrement execution count
            self._execution_counts[task_name] = max(0, self._execution_counts[task_name] - 1)

    def _build_context(self, task: TaskDefinitionConfig) -> dict[str, Any]:
        """Build execution context for a task.

        Args:
            task: Task definition

        Returns:
            Context dictionary
        """
        context = dict(task.context)

        # Add environment variables
        if self.config.active_environment:
            env_vars = self.config.get_environment_variables()
            context.update(env_vars)
            context["environment"] = self.config.active_environment

        # Add task parameters with defaults
        for param in task.parameters:
            if param.name not in context and param.default is not None:
                context[param.name] = param.default

        return context

    def _schedule_retry(self, task: TaskDefinitionConfig, result: dict[str, Any]) -> None:
        """Schedule a retry for a failed task with exponential backoff.

        Args:
            task: Task definition
            result: Execution result
        """
        task_name = task.name
        error_config = task.error_handling
        retry_count = self._retry_counts.get(task_name, 0)
        max_retries = error_config.max_retries

        if retry_count >= max_retries:
            logger.warning(
                f"Task {task_name} exceeded max retries ({max_retries}), giving up"
            )
            self._retry_counts[task_name] = 0  # Reset for next scheduled run
            self._handle_final_failure(task, result)
            return

        # Calculate delay with exponential backoff: 1s, 2s, 4s, 8s... max 300s
        base_delay = getattr(error_config, "retry_delay", 1.0)
        multiplier = 2**retry_count
        delay = min(base_delay * multiplier, 300.0)

        # Increment retry count
        self._retry_counts[task_name] = retry_count + 1

        logger.info(
            f"Scheduling retry {retry_count + 1}/{max_retries} "
            f"for task {task_name} in {delay:.1f}s"
        )

        # Schedule one-time retry job
        if self.scheduler:
            job_id = f"retry.{task_name}.{retry_count + 1}"
            run_date = datetime.now() + timedelta(seconds=delay)

            # Use closure to capture task_name
            def retry_runner(tn: str = task_name) -> None:
                self._execute_task(tn)

            self.scheduler.add_job(
                retry_runner,
                trigger="date",
                run_date=run_date,
                id=job_id,
                replace_existing=True,
            )

    def _handle_final_failure(
        self, task: TaskDefinitionConfig, result: dict[str, Any]
    ) -> None:
        """Handle task that failed all retry attempts.

        Args:
            task: Task definition
            result: Final execution result
        """
        error_handling = task.error_handling

        if error_handling.on_failure_action == "disable":
            task.enabled = False
            logger.warning(f"Task {task.name} disabled after max retries")

        elif error_handling.on_failure_action == "notify":
            self._send_failure_notification(task, result)

        elif error_handling.on_failure_action == "log":
            logger.error(
                f"Task {task.name} failed permanently after all retries: "
                f"{result.get('error', 'Unknown error')}"
            )

    def _send_failure_notification(
        self, task: TaskDefinitionConfig, result: dict[str, Any]
    ) -> None:
        """Send notification for task failure.

        Args:
            task: Task definition
            result: Execution result
        """
        error_handling = task.error_handling
        webhook_name = error_handling.notification_webhook

        if not webhook_name:
            logger.warning(
                f"No notification webhook configured for task {task.name}"
            )
            return

        # Try providers first, then legacy clients
        sender = self.providers.get(webhook_name) or self.clients.get(webhook_name)
        if not sender:
            logger.warning(f"Notification webhook not found: {webhook_name}")
            return

        try:
            error_msg = (
                f"Task '{task.name}' failed permanently after all retries.\n"
                f"Error: {result.get('error', 'Unknown error')}"
            )
            if hasattr(sender, "send_text"):
                sender.send_text(error_msg, "")
            logger.info(f"Sent failure notification for task {task.name}")
        except Exception as e:
            logger.error(f"Failed to send failure notification: {e}")

    def execute_task_now(self, task_name: str, force: bool = False) -> dict[str, Any]:
        """Execute a task immediately (outside of schedule).

        Args:
            task_name: Name of the task to execute
            force: If True, bypass concurrent execution limit

        Returns:
            Execution result
        """
        task = self._task_instances.get(task_name)
        if not task:
            task = self.config.get_task(task_name)
            if not task:
                raise ValueError(f"Task not found: {task_name}")

        # Check concurrent execution limit unless forced
        if not force:
            current_count = self._execution_counts.get(task_name, 0)
            max_concurrent = getattr(task, "max_concurrent", 1)
            if current_count >= max_concurrent:
                return {
                    "success": False,
                    "error": f"Task {task_name} already running {current_count} instances, "
                    f"max concurrent is {max_concurrent}. Use force=True to bypass.",
                    "duration": 0,
                }

        context = self._build_context(task)
        executor = TaskExecutor(
            task=task,
            context=context,
            plugin_manager=self.plugin_manager,
            clients=self.clients,
            ai_agent=self.ai_agent,
            providers=self.providers,
            template_registry=self.template_registry,
        )

        return executor.execute()

    def get_task_status(self, task_name: str) -> dict[str, Any]:
        """Get status information for a task.

        Args:
            task_name: Name of the task

        Returns:
            Status dictionary
        """
        task = self._task_instances.get(task_name)
        if not task:
            return {"error": "Task not found"}

        job_id = f"task.{task_name}"
        job = None
        if self.scheduler:
            with contextlib.suppress(Exception):
                job = self.scheduler.get_job(job_id)

        return {
            "name": task_name,
            "enabled": task.enabled,
            "registered": job_id in self._registered_jobs,
            "next_run": str(job.next_run_time) if job else None,
            "current_executions": self._execution_counts.get(task_name, 0),
            "max_concurrent": task.max_concurrent,
        }

    def list_tasks(self) -> list[dict[str, Any]]:
        """List all registered tasks.

        Returns:
            List of task status dictionaries
        """
        return [self.get_task_status(name) for name in self._task_instances]

    def reload_tasks(self) -> None:
        """Reload tasks from configuration."""
        logger.info("Reloading tasks...")
        self.stop()
        self.start()
