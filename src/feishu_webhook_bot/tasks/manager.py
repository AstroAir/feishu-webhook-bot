"""Task manager for scheduling and managing automated tasks."""

from __future__ import annotations

from typing import Any

from ..core.config import BotConfig, TaskDefinitionConfig
from ..core.logger import get_logger
from .executor import TaskExecutor

logger = get_logger("task.manager")


class TaskManager:
    """Manages task scheduling and execution."""

    def __init__(
        self,
        config: BotConfig,
        scheduler: Any = None,
        plugin_manager: Any = None,
        clients: dict[str, Any] | None = None,
    ):
        """Initialize task manager.

        Args:
            config: Bot configuration
            scheduler: Task scheduler instance
            plugin_manager: Plugin manager instance
            clients: Dictionary of webhook clients
        """
        self.config = config
        self.scheduler = scheduler
        self.plugin_manager = plugin_manager
        self.clients = clients or {}
        self._registered_jobs: set[str] = set()
        self._task_instances: dict[str, TaskDefinitionConfig] = {}
        self._execution_counts: dict[str, int] = {}

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
            )

            # Execute task
            logger.info(f"Executing task: {task_name}")
            result = executor.execute()

            # Log result
            if result["success"]:
                logger.info(
                    f"Task {task_name} completed successfully in {result['duration']:.2f}s"
                )
            else:
                logger.error(
                    f"Task {task_name} failed: {result.get('error', 'Unknown error')}"
                )

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
        """Schedule a retry for a failed task.

        Args:
            task: Task definition
            result: Execution result
        """
        # TODO: Implement retry logic with exponential backoff
        logger.info(f"Retry scheduling not yet implemented for task: {task.name}")

    def execute_task_now(self, task_name: str) -> dict[str, Any]:
        """Execute a task immediately (outside of schedule).

        Args:
            task_name: Name of the task to execute

        Returns:
            Execution result
        """
        task = self._task_instances.get(task_name)
        if not task:
            task = self.config.get_task(task_name)
            if not task:
                raise ValueError(f"Task not found: {task_name}")

        context = self._build_context(task)
        executor = TaskExecutor(
            task=task,
            context=context,
            plugin_manager=self.plugin_manager,
            clients=self.clients,
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
            try:
                job = self.scheduler.get_job(job_id)
            except Exception:
                pass

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
        return [self.get_task_status(name) for name in self._task_instances.keys()]

    def reload_tasks(self) -> None:
        """Reload tasks from configuration."""
        logger.info("Reloading tasks...")
        self.stop()
        self.start()

