"""Task manager for scheduling and managing automated tasks."""

from __future__ import annotations

import contextlib
import threading
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any

from ..core.config import BotConfig, TaskDefinitionConfig
from ..core.logger import get_logger
from ..core.provider import BaseProvider
from ..core.templates import TemplateRegistry
from .executor import TaskExecutor
from .persistence import TaskExecutionStore

if TYPE_CHECKING:
    from ..ai.agent import AIAgent

logger = get_logger("task.manager")


class TaskExecutionStatus(Enum):
    """Task execution status for dependency tracking."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_DEPENDENCY = "waiting_dependency"


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
        execution_store: TaskExecutionStore | None = None,
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
        self._execution_history: list[dict[str, Any]] = []
        self._max_history: int = 100
        # Execution persistence
        self._execution_store = execution_store
        # Dependency tracking
        self._task_status: dict[str, TaskExecutionStatus] = {}
        self._last_execution_result: dict[str, dict[str, Any]] = {}
        self._dependency_lock = threading.Lock()
        # Task groups
        self._task_groups: dict[str, set[str]] = {}  # group_name -> set of task_names

    def start(self) -> None:
        """Start task manager and register all tasks."""
        logger.info("Starting task manager...")

        # Build task groups index
        self._build_task_groups()

        # Load tasks from configuration
        for task in self.config.tasks:
            if task.enabled:
                self._register_task(task)
                self._task_status[task.name] = TaskExecutionStatus.PENDING

        logger.info(f"Registered {len(self._registered_jobs)} tasks")

    def _build_task_groups(self) -> None:
        """Build task groups index from task configurations."""
        self._task_groups.clear()
        for task in self.config.tasks:
            if task.group:
                if task.group not in self._task_groups:
                    self._task_groups[task.group] = set()
                self._task_groups[task.group].add(task.name)

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

    def _check_dependencies(self, task: TaskDefinitionConfig) -> tuple[bool, str]:
        """Check if task dependencies are satisfied.

        Args:
            task: Task definition to check

        Returns:
            Tuple of (can_execute, reason)
        """
        # Check depends_on (must have completed successfully)
        for dep_name in task.depends_on:
            with self._dependency_lock:
                dep_status = self._task_status.get(dep_name)

            if dep_status is None:
                return False, f"Dependency '{dep_name}' not found"

            if dep_status == TaskExecutionStatus.RUNNING:
                return False, f"Dependency '{dep_name}' is still running"

            if dep_status == TaskExecutionStatus.FAILED and task.skip_if_dependency_failed:
                return False, f"Dependency '{dep_name}' failed"

            if dep_status == TaskExecutionStatus.PENDING:
                return False, f"Dependency '{dep_name}' has not run yet"

            if dep_status == TaskExecutionStatus.SKIPPED and task.skip_if_dependency_failed:
                return False, f"Dependency '{dep_name}' was skipped"

        # Check run_after (must have completed, success or failure)
        for dep_name in task.run_after:
            with self._dependency_lock:
                dep_status = self._task_status.get(dep_name)

            if dep_status is None:
                return False, f"Run-after task '{dep_name}' not found"

            if dep_status in (TaskExecutionStatus.PENDING, TaskExecutionStatus.RUNNING):
                return False, f"Run-after task '{dep_name}' has not completed yet"

        return True, "All dependencies satisfied"

    def _wait_for_dependencies(
        self, task: TaskDefinitionConfig, timeout: float | None = None
    ) -> tuple[bool, str]:
        """Wait for task dependencies to be satisfied.

        Args:
            task: Task definition
            timeout: Maximum time to wait (uses task.dependency_timeout if None)

        Returns:
            Tuple of (dependencies_satisfied, reason)
        """
        wait_timeout = timeout if timeout is not None else task.dependency_timeout
        start_time = time.time()
        poll_interval = 1.0  # Check every second

        while True:
            can_execute, reason = self._check_dependencies(task)
            if can_execute:
                return True, reason

            # Check if any dependency failed and we should skip
            is_failure = "failed" in reason.lower() or "skipped" in reason.lower()
            if is_failure and task.skip_if_dependency_failed:
                return False, reason

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed >= wait_timeout:
                return False, f"Dependency wait timeout after {elapsed:.1f}s: {reason}"

            # Wait before next check
            time.sleep(poll_interval)

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

        # Check dependencies
        has_dependencies = task.depends_on or task.run_after
        if has_dependencies:
            with self._dependency_lock:
                self._task_status[task_name] = TaskExecutionStatus.WAITING_DEPENDENCY

            can_execute, reason = self._check_dependencies(task)
            if not can_execute:
                # For scheduled tasks, we don't wait - just skip this run
                logger.info(f"Task {task_name} skipped due to unmet dependencies: {reason}")
                with self._dependency_lock:
                    self._task_status[task_name] = TaskExecutionStatus.SKIPPED
                return

        # Increment execution count
        self._execution_counts[task_name] = current_count + 1

        # Update status to running
        with self._dependency_lock:
            self._task_status[task_name] = TaskExecutionStatus.RUNNING

        try:
            # Build execution context
            context = self._build_context(task)

            # Add dependency results to context if available
            if has_dependencies:
                dep_results = {}
                for dep_name in task.depends_on + task.run_after:
                    if dep_name in self._last_execution_result:
                        dep_results[dep_name] = self._last_execution_result[dep_name]
                if dep_results:
                    context["dependency_results"] = dep_results

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

            # Update status based on result
            with self._dependency_lock:
                if result["success"]:
                    self._task_status[task_name] = TaskExecutionStatus.SUCCESS
                else:
                    self._task_status[task_name] = TaskExecutionStatus.FAILED
                # Store result for dependent tasks
                self._last_execution_result[task_name] = result

            # Log result
            if result["success"]:
                logger.info(f"Task {task_name} completed successfully in {result['duration']:.2f}s")
                # Reset retry count on success
                self._retry_counts[task_name] = 0
            else:
                logger.error(f"Task {task_name} failed: {result.get('error', 'Unknown error')}")

            # Record execution history
            self._record_execution(task_name, result)

            # Handle retry on failure
            if not result["success"] and task.error_handling.retry_on_failure:
                self._schedule_retry(task, result)

            # Trigger dependent tasks if this task succeeded
            if result["success"]:
                self._trigger_dependent_tasks(task_name)

        except Exception as e:
            logger.error(f"Error executing task {task_name}: {e}", exc_info=True)
            with self._dependency_lock:
                self._task_status[task_name] = TaskExecutionStatus.FAILED

        finally:
            # Decrement execution count
            self._execution_counts[task_name] = max(0, self._execution_counts[task_name] - 1)

    def _trigger_dependent_tasks(self, completed_task_name: str) -> None:
        """Trigger tasks that depend on the completed task.

        Args:
            completed_task_name: Name of the task that just completed
        """
        for task_name, task in self._task_instances.items():
            if not task.enabled:
                continue

            # Check if this task depends on the completed task
            is_dependent = (
                completed_task_name in task.depends_on or completed_task_name in task.run_after
            )
            if not is_dependent:
                continue

            # Check if all dependencies are now satisfied
            can_execute, _ = self._check_dependencies(task)
            if can_execute:
                # Check if task is waiting for dependencies
                with self._dependency_lock:
                    status = self._task_status.get(task_name)
                if status == TaskExecutionStatus.WAITING_DEPENDENCY:
                    logger.info(
                        f"Dependencies satisfied for task {task_name}, triggering execution"
                    )
                    # Execute in a separate thread to avoid blocking
                    import threading

                    thread = threading.Thread(
                        target=self._execute_task,
                        args=(task_name,),
                        daemon=True,
                    )
                    thread.start()

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
            logger.warning(f"Task {task_name} exceeded max retries ({max_retries}), giving up")
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
            f"Scheduling retry {retry_count + 1}/{max_retries} for task {task_name} in {delay:.1f}s"
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

    def _handle_final_failure(self, task: TaskDefinitionConfig, result: dict[str, Any]) -> None:
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
            logger.warning(f"No notification webhook configured for task {task.name}")
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

    def _record_execution(self, task_name: str, result: dict[str, Any]) -> None:
        """Record task execution to history.

        Args:
            task_name: Name of the task
            result: Execution result dictionary
        """
        history_entry = {
            "task_name": task_name,
            "executed_at": datetime.now().isoformat(),
            "success": result.get("success", False),
            "duration": result.get("duration", 0),
            "error": result.get("error"),
            "actions_executed": result.get("actions_executed", 0),
            "actions_failed": result.get("actions_failed", 0),
            "timed_out": result.get("timed_out", False),
        }
        self._execution_history.append(history_entry)

        # Trim history if needed
        if len(self._execution_history) > self._max_history:
            self._execution_history = self._execution_history[-self._max_history :]

        # Persist to database if store is available
        if self._execution_store:
            try:
                self._execution_store.record_execution(task_name, result)
            except Exception as e:
                logger.warning(f"Failed to persist execution record: {e}")

    def get_execution_history(
        self,
        task_name: str | None = None,
        limit: int = 20,
        from_database: bool = False,
    ) -> list[dict[str, Any]]:
        """Get task execution history.

        Args:
            task_name: Optional filter by task name
            limit: Maximum number of entries to return
            from_database: If True and store available, query from database

        Returns:
            List of execution history entries (newest first)
        """
        # Use database if requested and available
        if from_database and self._execution_store:
            return self._execution_store.get_execution_history(task_name=task_name, limit=limit)

        # Fall back to in-memory history
        history = self._execution_history
        if task_name:
            history = [h for h in history if h.get("task_name") == task_name]
        return list(reversed(history[-limit:]))

    def get_persistent_task_status(self, task_name: str) -> dict[str, Any] | None:
        """Get persistent task status from database.

        Args:
            task_name: Name of the task

        Returns:
            Task status from database or None if not available
        """
        if not self._execution_store:
            return None
        return self._execution_store.get_task_status(task_name)

    def get_task_statistics(self, task_name: str | None = None, days: int = 7) -> dict[str, Any]:
        """Get task execution statistics.

        Args:
            task_name: Optional filter by task name
            days: Number of days to include

        Returns:
            Statistics dictionary
        """
        if self._execution_store:
            return self._execution_store.get_task_statistics(task_name, days)

        # Fall back to in-memory calculation
        history = self._execution_history
        if task_name:
            history = [h for h in history if h.get("task_name") == task_name]

        total = len(history)
        successful = sum(1 for h in history if h.get("success"))
        failed = total - successful
        success_rate = (successful / total * 100) if total > 0 else 0

        durations = [h.get("duration", 0) for h in history if h.get("duration")]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "period_days": days,
            "total_executions": total,
            "successful_executions": successful,
            "failed_executions": failed,
            "success_rate": round(success_rate, 2),
            "average_duration": round(avg_duration, 3),
            "daily_statistics": [],  # Not available for in-memory
        }

    def enable_task(self, task_name: str) -> bool:
        """Enable a task.

        Args:
            task_name: Name of the task to enable

        Returns:
            True if task was enabled, False if not found
        """
        task = self._task_instances.get(task_name)
        if not task:
            # Try to find in config
            task = self.config.get_task(task_name)
            if not task:
                return False

        task.enabled = True

        # Re-register the task if scheduler is available
        registered_task_names = [j.replace("task.", "") for j in self._registered_jobs]
        if self.scheduler and task_name not in registered_task_names:
            self._register_task(task)

        logger.info(f"Enabled task: {task_name}")
        return True

    def disable_task(self, task_name: str) -> bool:
        """Disable a task.

        Args:
            task_name: Name of the task to disable

        Returns:
            True if task was disabled, False if not found
        """
        task = self._task_instances.get(task_name)
        if not task:
            return False

        task.enabled = False

        # Remove from scheduler if registered
        job_id = f"task.{task_name}"
        if self.scheduler and job_id in self._registered_jobs:
            try:
                self.scheduler.remove_job(job_id)
                self._registered_jobs.discard(job_id)
            except Exception as e:
                logger.debug(f"Failed to remove job {job_id}: {e}")

        logger.info(f"Disabled task: {task_name}")
        return True

    def pause_task(self, task_name: str) -> bool:
        """Pause a task (keep registered but don't execute).

        Args:
            task_name: Name of the task to pause

        Returns:
            True if task was paused, False if not found
        """
        job_id = f"task.{task_name}"
        if not self.scheduler or job_id not in self._registered_jobs:
            return False

        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused task: {task_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to pause task {task_name}: {e}")
            return False

    def resume_task(self, task_name: str) -> bool:
        """Resume a paused task.

        Args:
            task_name: Name of the task to resume

        Returns:
            True if task was resumed, False if not found
        """
        job_id = f"task.{task_name}"
        if not self.scheduler or job_id not in self._registered_jobs:
            return False

        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed task: {task_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to resume task {task_name}: {e}")
            return False

    def run_task(self, task_name: str, force: bool = False) -> dict[str, Any]:
        """Run a task immediately (alias for execute_task_now).

        Args:
            task_name: Name of the task to run
            force: If True, bypass concurrent execution limit

        Returns:
            Execution result dictionary
        """
        result = self.execute_task_now(task_name, force=force)
        # Record to history
        self._record_execution(task_name, result)
        return result

    def get_task(self, task_name: str) -> TaskDefinitionConfig | None:
        """Get a task by name.

        Args:
            task_name: Name of the task

        Returns:
            TaskDefinitionConfig if found, None otherwise
        """
        return self._task_instances.get(task_name) or self.config.get_task(task_name)

    def get_task_details(self, task_name: str) -> dict[str, Any]:
        """Get detailed information about a task.

        Args:
            task_name: Name of the task

        Returns:
            Detailed task information dictionary
        """
        task = self.get_task(task_name)
        if not task:
            return {"error": f"Task not found: {task_name}"}

        status = self.get_task_status(task_name)
        recent_history = self.get_execution_history(task_name, limit=5)

        # Calculate success rate from history
        task_history = self.get_execution_history(task_name, limit=100)
        total_runs = len(task_history)
        successful_runs = sum(1 for h in task_history if h.get("success"))
        success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0

        # Determine schedule info
        schedule_info = "None"
        if task.cron:
            schedule_info = f"cron: {task.cron}"
        elif task.interval:
            schedule_info = f"interval: {task.interval}"
        elif task.schedule:
            schedule_info = f"{task.schedule.mode}: {task.schedule.arguments}"

        return {
            "name": task.name,
            "description": task.description,
            "enabled": task.enabled,
            "schedule": schedule_info,
            "timeout": task.timeout,
            "max_concurrent": task.max_concurrent,
            "priority": task.priority,
            "actions_count": len(task.actions),
            "conditions_count": len(task.conditions),
            "error_handling": {
                "retry_on_failure": task.error_handling.retry_on_failure,
                "max_retries": task.error_handling.max_retries,
                "on_failure_action": task.error_handling.on_failure_action,
            },
            "status": status,
            "recent_history": recent_history,
            "total_runs": total_runs,
            "success_rate": round(success_rate, 1),
        }

    def run_task_with_params(
        self,
        task_name: str,
        params: dict[str, Any] | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Run a task with custom parameters.

        Args:
            task_name: Name of the task to run
            params: Custom parameters to override task defaults
            force: If True, bypass concurrent execution limit

        Returns:
            Execution result dictionary
        """
        task = self._task_instances.get(task_name)
        if not task:
            task = self.config.get_task(task_name)
            if not task:
                return {"success": False, "error": f"Task not found: {task_name}"}

        # Check concurrent execution limit unless forced
        if not force:
            current_count = self._execution_counts.get(task_name, 0)
            max_concurrent = getattr(task, "max_concurrent", 1)
            if current_count >= max_concurrent:
                return {
                    "success": False,
                    "error": f"Task {task_name} already running {current_count} instances",
                    "duration": 0,
                }

        # Build context with custom params
        context = self._build_context(task)
        if params:
            context.update(params)

        executor = TaskExecutor(
            task=task,
            context=context,
            plugin_manager=self.plugin_manager,
            clients=self.clients,
            ai_agent=self.ai_agent,
            providers=self.providers,
            template_registry=self.template_registry,
        )

        result = executor.execute()
        self._record_execution(task_name, result)
        return result

    def update_task_config(self, task_name: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update task configuration at runtime.

        Args:
            task_name: Name of the task to update
            updates: Dictionary of configuration updates

        Returns:
            Result dictionary with success status
        """
        task = self._task_instances.get(task_name)
        if not task:
            return {"success": False, "error": f"Task not found: {task_name}"}

        try:
            # Apply updates
            updated_fields = []

            if "enabled" in updates:
                task.enabled = updates["enabled"]
                updated_fields.append("enabled")
                # Re-register or unregister based on enabled state
                if task.enabled:
                    self._register_task(task)
                else:
                    self.disable_task(task_name)

            if "timeout" in updates:
                task.timeout = updates["timeout"]
                updated_fields.append("timeout")

            if "max_concurrent" in updates:
                task.max_concurrent = updates["max_concurrent"]
                updated_fields.append("max_concurrent")

            if "priority" in updates:
                task.priority = updates["priority"]
                updated_fields.append("priority")

            if "description" in updates:
                task.description = updates["description"]
                updated_fields.append("description")

            # Update error handling
            if "error_handling" in updates:
                eh = updates["error_handling"]
                if "retry_on_failure" in eh:
                    task.error_handling.retry_on_failure = eh["retry_on_failure"]
                if "max_retries" in eh:
                    task.error_handling.max_retries = eh["max_retries"]
                if "on_failure_action" in eh:
                    task.error_handling.on_failure_action = eh["on_failure_action"]
                updated_fields.append("error_handling")

            # Update context
            if "context" in updates:
                task.context.update(updates["context"])
                updated_fields.append("context")

            logger.info(f"Updated task {task_name}: {', '.join(updated_fields)}")
            return {
                "success": True,
                "updated_fields": updated_fields,
                "task_name": task_name,
            }

        except Exception as e:
            logger.error(f"Failed to update task {task_name}: {e}")
            return {"success": False, "error": str(e)}

    def get_all_task_stats(self) -> dict[str, Any]:
        """Get statistics for all tasks.

        Returns:
            Dictionary with task statistics
        """
        total = len(self._task_instances)
        enabled = sum(1 for t in self._task_instances.values() if t.enabled)
        registered = len(self._registered_jobs)

        # Calculate overall success rate
        all_history = self._execution_history
        total_runs = len(all_history)
        successful_runs = sum(1 for h in all_history if h.get("success"))
        success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0

        return {
            "total_tasks": total,
            "enabled_tasks": enabled,
            "disabled_tasks": total - enabled,
            "registered_jobs": registered,
            "total_executions": total_runs,
            "successful_executions": successful_runs,
            "failed_executions": total_runs - successful_runs,
            "overall_success_rate": round(success_rate, 1),
        }

    # =========================================================================
    # Task Group Management
    # =========================================================================

    def get_task_groups(self) -> dict[str, list[str]]:
        """Get all task groups and their members.

        Returns:
            Dictionary mapping group names to list of task names
        """
        return {group: list(tasks) for group, tasks in self._task_groups.items()}

    def get_tasks_by_group(self, group_name: str) -> list[TaskDefinitionConfig]:
        """Get all tasks in a specific group.

        Args:
            group_name: Name of the group

        Returns:
            List of task configurations in the group
        """
        task_names = self._task_groups.get(group_name, set())
        return [self._task_instances[name] for name in task_names if name in self._task_instances]

    def get_tasks_by_tag(self, tag: str) -> list[TaskDefinitionConfig]:
        """Get all tasks with a specific tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of task configurations with the tag
        """
        return [task for task in self._task_instances.values() if tag in task.tags]

    def run_group(self, group_name: str, force: bool = False) -> dict[str, Any]:
        """Run all tasks in a group.

        Args:
            group_name: Name of the group to run
            force: If True, bypass concurrent execution limits

        Returns:
            Dictionary with results for each task
        """
        tasks = self.get_tasks_by_group(group_name)
        if not tasks:
            return {"error": f"Group not found or empty: {group_name}"}

        results = {}
        for task in tasks:
            if task.enabled:
                results[task.name] = self.execute_task_now(task.name, force=force)
        return results

    def enable_group(self, group_name: str) -> dict[str, bool]:
        """Enable all tasks in a group.

        Args:
            group_name: Name of the group

        Returns:
            Dictionary mapping task names to success status
        """
        tasks = self.get_tasks_by_group(group_name)
        return {task.name: self.enable_task(task.name) for task in tasks}

    def disable_group(self, group_name: str) -> dict[str, bool]:
        """Disable all tasks in a group.

        Args:
            group_name: Name of the group

        Returns:
            Dictionary mapping task names to success status
        """
        tasks = self.get_tasks_by_group(group_name)
        return {task.name: self.disable_task(task.name) for task in tasks}

    # =========================================================================
    # Dependency Status Management
    # =========================================================================

    def get_task_dependency_status(self, task_name: str) -> dict[str, Any]:
        """Get dependency status for a task.

        Args:
            task_name: Name of the task

        Returns:
            Dictionary with dependency information
        """
        task = self._task_instances.get(task_name)
        if not task:
            return {"error": f"Task not found: {task_name}"}

        deps_status = {}
        for dep_name in task.depends_on:
            with self._dependency_lock:
                status = self._task_status.get(dep_name, TaskExecutionStatus.PENDING)
            deps_status[dep_name] = {
                "status": status.value,
                "required": True,
                "last_result": self._last_execution_result.get(dep_name),
            }

        for dep_name in task.run_after:
            with self._dependency_lock:
                status = self._task_status.get(dep_name, TaskExecutionStatus.PENDING)
            deps_status[dep_name] = {
                "status": status.value,
                "required": False,  # run_after doesn't require success
                "last_result": self._last_execution_result.get(dep_name),
            }

        can_execute, reason = self._check_dependencies(task)

        return {
            "task_name": task_name,
            "dependencies": deps_status,
            "can_execute": can_execute,
            "reason": reason,
            "dependency_timeout": task.dependency_timeout,
            "skip_if_dependency_failed": task.skip_if_dependency_failed,
        }

    def reset_task_status(self, task_name: str) -> bool:
        """Reset a task's execution status to PENDING.

        Args:
            task_name: Name of the task to reset

        Returns:
            True if reset successful, False if task not found
        """
        if task_name not in self._task_instances:
            return False

        with self._dependency_lock:
            self._task_status[task_name] = TaskExecutionStatus.PENDING
            if task_name in self._last_execution_result:
                del self._last_execution_result[task_name]

        logger.info(f"Reset task status: {task_name}")
        return True

    def reset_all_task_statuses(self) -> None:
        """Reset all task statuses to PENDING."""
        with self._dependency_lock:
            for task_name in self._task_instances:
                self._task_status[task_name] = TaskExecutionStatus.PENDING
            self._last_execution_result.clear()

        logger.info("Reset all task statuses")

    def get_all_task_statuses(self) -> dict[str, str]:
        """Get execution status for all tasks.

        Returns:
            Dictionary mapping task names to status values
        """
        with self._dependency_lock:
            return {name: status.value for name, status in self._task_status.items()}

    # =========================================================================
    # Task Chain / Workflow Execution
    # =========================================================================

    def run_task_chain(
        self,
        task_names: list[str],
        stop_on_failure: bool = True,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a chain of tasks sequentially.

        Args:
            task_names: List of task names to run in order
            stop_on_failure: If True, stop chain on first failure
            context: Optional shared context passed to all tasks

        Returns:
            Dictionary with chain execution results
        """
        chain_results: dict[str, Any] = {
            "chain": task_names,
            "results": {},
            "completed": [],
            "failed": [],
            "skipped": [],
            "success": True,
        }

        shared_context = context or {}

        for task_name in task_names:
            task = self._task_instances.get(task_name)
            if not task:
                chain_results["skipped"].append(task_name)
                chain_results["results"][task_name] = {
                    "success": False,
                    "error": "Task not found",
                }
                if stop_on_failure:
                    chain_results["success"] = False
                    break
                continue

            # Build context with shared data and previous results
            task_context = self._build_context(task)
            task_context.update(shared_context)
            task_context["chain_results"] = chain_results["results"]

            # Execute task
            executor = TaskExecutor(
                task=task,
                context=task_context,
                plugin_manager=self.plugin_manager,
                clients=self.clients,
                ai_agent=self.ai_agent,
                providers=self.providers,
                template_registry=self.template_registry,
            )

            result = executor.execute()
            chain_results["results"][task_name] = result
            self._record_execution(task_name, result)

            if result["success"]:
                chain_results["completed"].append(task_name)
                # Update shared context with task output if available
                if "output" in result:
                    shared_context[f"{task_name}_output"] = result["output"]
            else:
                chain_results["failed"].append(task_name)
                chain_results["success"] = False
                if stop_on_failure:
                    # Mark remaining tasks as skipped
                    remaining_idx = task_names.index(task_name) + 1
                    chain_results["skipped"].extend(task_names[remaining_idx:])
                    break

        return chain_results

    def run_parallel_tasks(
        self,
        task_names: list[str],
        max_workers: int = 4,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Run multiple tasks in parallel.

        Args:
            task_names: List of task names to run
            max_workers: Maximum number of concurrent workers
            timeout: Optional timeout for the entire operation

        Returns:
            Dictionary with parallel execution results
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results: dict[str, Any] = {
            "tasks": task_names,
            "results": {},
            "completed": [],
            "failed": [],
            "timed_out": [],
        }

        def execute_task(name: str) -> tuple[str, dict[str, Any]]:
            return name, self.execute_task_now(name, force=True)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(execute_task, name): name for name in task_names}

            for future in as_completed(futures, timeout=timeout):
                task_name = futures[future]
                try:
                    _, result = future.result()
                    results["results"][task_name] = result
                    if result["success"]:
                        results["completed"].append(task_name)
                    else:
                        results["failed"].append(task_name)
                except TimeoutError:
                    results["timed_out"].append(task_name)
                    results["results"][task_name] = {
                        "success": False,
                        "error": "Execution timed out",
                    }
                except Exception as e:
                    results["failed"].append(task_name)
                    results["results"][task_name] = {
                        "success": False,
                        "error": str(e),
                    }

        return results
