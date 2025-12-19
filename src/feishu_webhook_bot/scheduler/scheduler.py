"""Task scheduler for periodic jobs and workflows.

This module wraps APScheduler to provide:
- Easy job registration
- Cron and interval scheduling
- Job persistence (SQLite)
- Error handling and retry logic
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobExecutionEvent
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.base import BaseJobStore
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# Try to import SQLAlchemy job store (optional dependency)
try:
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

    HAS_SQLALCHEMY = True
except ImportError:
    SQLAlchemyJobStore = None
    HAS_SQLALCHEMY = False

from ..core.config import SchedulerConfig
from ..core.logger import get_logger
from .hooks import (
    AlertHook,
    HookRegistry,
    JobExecutionContext,
    JobExecutionResult,
    LoggingHook,
    MetricsHook,
)
from .monitors import JobHealthMonitor, SchedulerHealthConfig
from .stores import ExecutionHistoryStore

logger = get_logger("scheduler")


def job(
    trigger: str = "interval",
    **trigger_args: Any,
) -> Callable[[Callable], Callable]:
    """Decorator to mark a function as a scheduled job.

    This decorator stores scheduling information on the function for later
    registration with the TaskScheduler.

    Args:
        trigger: Trigger type ('interval', 'cron', 'date')
        **trigger_args: Trigger-specific arguments

    Returns:
        Decorated function

    Example:
        ```python
        @job(trigger='interval', minutes=5)
        def my_task():
            print("Running every 5 minutes")

        @job(trigger='cron', hour='9', minute='0')
        def morning_task():
            print("Running at 9:00 AM every day")
        ```
    """

    def decorator(func: Callable) -> Callable:
        # Store scheduling info on the function
        func._scheduler_job = True  # type: ignore
        func._trigger_type = trigger  # type: ignore
        func._trigger_args = trigger_args  # type: ignore

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        # Preserve the metadata
        wrapper._scheduler_job = True  # type: ignore
        wrapper._trigger_type = trigger  # type: ignore
        wrapper._trigger_args = trigger_args  # type: ignore

        return wrapper

    return decorator


class TaskScheduler:
    """Task scheduler for managing periodic jobs and workflows.

    This class wraps APScheduler and provides a simple interface for
    registering and managing scheduled tasks.

    Example:
        ```python
        from feishu_webhook_bot.scheduler import TaskScheduler, job

        scheduler = TaskScheduler(config)
        scheduler.start()

        # Register a function
        @job(trigger='interval', minutes=10)
        def periodic_task():
            print("Running every 10 minutes")

        scheduler.register_job(periodic_task)

        # Or add job programmatically
        scheduler.add_job(
            func=my_function,
            trigger='cron',
            hour='8',
            minute='0'
        )
        ```
    """

    def __init__(self, config: SchedulerConfig):
        """Initialize the task scheduler.

        Args:
            config: Scheduler configuration
        """
        self.config = config
        self._scheduler: BackgroundScheduler | None = None
        self._job_metadata: dict[str, dict[str, Any]] = {}
        self._job_run_counts: dict[str, int] = {}
        self._job_start_times: dict[str, datetime] = {}

        # Initialize hook registry
        self._hook_registry = HookRegistry()
        self._setup_hooks()

        # Initialize health monitor
        self._health_monitor: JobHealthMonitor | None = None
        self._setup_health_monitor()

        # Initialize execution history store
        self._history_store: ExecutionHistoryStore | None = None
        self._setup_history_store()

        self._setup_scheduler()

    def _setup_hooks(self) -> None:
        """Setup execution hooks based on configuration."""
        if getattr(self.config, "logging_hook_enabled", True):
            self._hook_registry.register(LoggingHook())
        if getattr(self.config, "metrics_hook_enabled", True):
            self._hook_registry.register(MetricsHook())
        if getattr(self.config, "alert_hook_enabled", False):
            self._hook_registry.register(AlertHook())
        logger.debug(f"Registered {len(self._hook_registry.get_hooks())} execution hooks")

    def _setup_health_monitor(self) -> None:
        """Setup health monitoring based on configuration."""
        if not getattr(self.config, "health_check_enabled", True):
            return
        health_config = SchedulerHealthConfig(
            enabled=True,
            check_interval_seconds=getattr(self.config, "health_check_interval", 60),
            failure_threshold=getattr(self.config, "failure_threshold", 3),
            stale_job_threshold_seconds=getattr(self.config, "stale_job_threshold", 3600),
        )
        self._health_monitor = JobHealthMonitor(config=health_config)
        logger.debug("Health monitor initialized")

    def _setup_history_store(self) -> None:
        """Setup execution history store based on configuration."""
        if not getattr(self.config, "history_enabled", True):
            return
        history_path = getattr(self.config, "history_path", None)
        if history_path:
            self._history_store = ExecutionHistoryStore(history_path)
            logger.debug(f"Execution history store initialized: {history_path}")

    def _setup_scheduler(self) -> None:
        """Setup APScheduler with configured job store."""
        # Configure job stores
        jobstores: dict[str, Any] = {}
        if self.config.job_store_type == "sqlite" and self.config.job_store_path:
            if not HAS_SQLALCHEMY:
                logger.warning(
                    "SQLite job store requested but SQLAlchemy is not installed. "
                    "Install with: uv add sqlalchemy. Falling back to memory store."
                )
                jobstores["default"] = MemoryJobStore()
                logger.info("Using in-memory job store (fallback)")
            else:
                jobstore_obj = SQLAlchemyJobStore(url=f"sqlite:///{self.config.job_store_path}")
                if isinstance(jobstore_obj, BaseJobStore):
                    jobstores["default"] = jobstore_obj
                    logger.info(f"Using SQLite job store: {self.config.job_store_path}")
                else:
                    logger.debug(
                        "SQLAlchemyJobStore mock detected; falling back to in-memory job store"
                    )
                    jobstores["default"] = MemoryJobStore()
        else:
            jobstores["default"] = MemoryJobStore()
            logger.info("Using in-memory job store")

        # Configure executors with config values
        max_workers = getattr(self.config, "max_workers", 10)
        executors = {"default": ThreadPoolExecutor(max_workers=max_workers)}

        # Job defaults from config
        job_defaults = {
            "coalesce": getattr(self.config, "job_coalesce", True),
            "max_instances": getattr(self.config, "max_instances", 1),
            "misfire_grace_time": getattr(self.config, "misfire_grace_time", 60),
        }

        # Create scheduler
        self._scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=self.config.timezone,
        )

        # Add event listeners
        self._scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self._scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)

        logger.info(f"Scheduler initialized with timezone: {self.config.timezone}")

    def _job_executed(self, event: JobExecutionEvent) -> None:
        """Handler for successful job execution.

        Args:
            event: Job execution event
        """
        job_id = event.job_id
        duration = getattr(event, "run_time", 0.0) or 0.0

        # Update run counts
        self._job_run_counts[job_id] = self._job_run_counts.get(job_id, 0) + 1

        # Record in health monitor
        if self._health_monitor:
            self._health_monitor.record_execution_end(job_id, success=True, duration=duration)

        # Record in history store
        if self._history_store:
            self._history_store.record_execution(job_id, success=True, duration=duration)

        # Execute after hooks
        context = JobExecutionContext(
            job_id=job_id,
            job_name=job_id,
            scheduled_time=datetime.now(),
            start_time=datetime.now(),
        )
        result = JobExecutionResult(
            success=True,
            duration=duration,
            result=event.retval if hasattr(event, "retval") else None,
        )
        self._hook_registry.execute_after_hooks(context, result)

        logger.info(f"Job {job_id} executed successfully (duration: {duration:.3f}s)")

    def _job_error(self, event: JobExecutionEvent) -> None:
        """Handler for job execution errors.

        Args:
            event: Job execution event
        """
        job_id = event.job_id
        error_msg = str(event.exception) if event.exception else "Unknown error"
        duration = getattr(event, "run_time", 0.0) or 0.0

        # Record in health monitor
        if self._health_monitor:
            self._health_monitor.record_execution_end(job_id, success=False, duration=duration)

        # Record in history store
        if self._history_store:
            self._history_store.record_execution(
                job_id, success=False, duration=duration, error=error_msg
            )

        # Execute after hooks with error
        context = JobExecutionContext(
            job_id=job_id,
            job_name=job_id,
            scheduled_time=datetime.now(),
            start_time=datetime.now(),
        )
        result = JobExecutionResult(
            success=False,
            duration=duration,
            error=event.exception,
        )
        self._hook_registry.execute_after_hooks(context, result)

        logger.error(
            f"Job {job_id} failed with exception: {event.exception}",
            exc_info=event.exception,
        )

    def start(self) -> None:
        """Start the scheduler.

        Raises:
            RuntimeError: If scheduler is not enabled in config
        """
        if not self.config.enabled:
            raise RuntimeError("Scheduler is disabled in configuration")

        if self._scheduler and not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler.

        Args:
            wait: Whether to wait for running jobs to complete
        """
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("Scheduler stopped")

    def add_job(
        self,
        func: Callable,
        trigger: str = "interval",
        job_id: str | None = None,
        replace_existing: bool = True,
        **trigger_args: Any,
    ) -> str:
        """Add a job to the scheduler.

        Args:
            func: Function to execute
            trigger: Trigger type ('interval', 'cron', 'date')
            job_id: Unique job ID (auto-generated if None)
            replace_existing: Whether to replace existing job with same ID
            **trigger_args: Trigger-specific arguments

        Returns:
            Job ID

        Example:
            ```python
            # Interval trigger
            scheduler.add_job(
                my_func,
                trigger='interval',
                minutes=5
            )

            # Cron trigger
            scheduler.add_job(
                my_func,
                trigger='cron',
                hour='9',
                minute='0',
                day_of_week='mon-fri'
            )
            ```
        """
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")

        # Generate job_id if not provided
        if job_id is None:
            import uuid

            job_id = f"{func.__module__}.{func.__name__}-{uuid.uuid4().hex}"

        # Create trigger
        trigger_obj: Any = None
        if trigger == "interval":
            trigger_obj = IntervalTrigger(**trigger_args)
        elif trigger == "cron":
            trigger_obj = CronTrigger(**trigger_args, timezone=self.config.timezone)
        else:
            raise ValueError(f"Unsupported trigger type: {trigger}")

        # Add job
        self._scheduler.add_job(
            func,
            trigger_obj,
            id=job_id,
            replace_existing=replace_existing,
        )

        logger.info(f"Job added: {job_id} with trigger {trigger}")
        return job_id

    def register_job(self, func: Callable) -> str | None:
        """Register a function decorated with @job.

        Args:
            func: Function decorated with @job

        Returns:
            Job ID if registered, None if function is not a job

        Example:
            ```python
            @job(trigger='interval', minutes=5)
            def my_task():
                pass

            scheduler.register_job(my_task)
            ```
        """
        # Check if function has scheduling metadata
        if not hasattr(func, "_scheduler_job") or not func._scheduler_job:
            return None

        trigger_type = getattr(func, "_trigger_type", "interval")
        trigger_args = getattr(func, "_trigger_args", {})

        return self.add_job(func, trigger=trigger_type, **trigger_args)

    def register_jobs(self, *funcs: Callable) -> list[str]:
        """Register multiple functions decorated with @job.

        Args:
            *funcs: Functions to register

        Returns:
            List of registered job IDs

        Example:
            ```python
            scheduler.register_jobs(task1, task2, task3)
            ```
        """
        job_ids = []
        for func in funcs:
            job_id = self.register_job(func)
            if job_id:
                job_ids.append(job_id)
        return job_ids

    def remove_job(self, job_id: str) -> None:
        """Remove a job from the scheduler.

        Args:
            job_id: Job ID to remove
        """
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")

        self._scheduler.remove_job(job_id)
        logger.info(f"Job removed: {job_id}")

    def modify_job(
        self,
        job_id: str,
        func: Callable | str | None = None,
        trigger: str | None = None,
        **trigger_args: Any,
    ) -> None:
        """Modify an existing job.

        Args:
            job_id: ID of the job to modify
            func: New function to execute (optional)
            trigger: New trigger type ('interval', 'cron', 'date') (optional)
            **trigger_args: New trigger-specific arguments (optional)
        """
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")

        update_fields: dict[str, Any] = {}
        if func:
            update_fields["func"] = func
        if trigger:
            if trigger == "interval":
                update_fields["trigger"] = IntervalTrigger(**trigger_args)
            elif trigger == "cron":
                update_fields["trigger"] = CronTrigger(
                    **trigger_args, timezone=self.config.timezone
                )
            else:
                raise ValueError(f"Unsupported trigger type: {trigger}")
        elif trigger_args:
            # When no new trigger is supplied we delegate the kwargs to
            # APScheduler so it can update the existing trigger in place.
            update_fields.update(trigger_args)

        self._scheduler.modify_job(job_id, **update_fields)
        logger.info(f"Job modified: {job_id}")

    def pause_job(self, job_id: str) -> None:
        """Pause a job.

        Args:
            job_id: Job ID to pause
        """
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")

        self._scheduler.pause_job(job_id)
        logger.info(f"Job paused: {job_id}")

    def resume_job(self, job_id: str) -> None:
        """Resume a paused job.

        Args:
            job_id: Job ID to resume
        """
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")

        self._scheduler.resume_job(job_id)
        logger.info(f"Job resumed: {job_id}")

    def get_jobs(self) -> list[Any]:
        """Get all scheduled jobs.

        Returns:
            List of job objects
        """
        if not self._scheduler:
            return []

        return self._scheduler.get_jobs()

    def get_job(self, job_id: str) -> Any | None:
        """Get a specific job by ID.

        Args:
            job_id: Job ID

        Returns:
            Job object or None if not found
        """
        if not self._scheduler:
            return None

        return self._scheduler.get_job(job_id)

    def print_jobs(self) -> None:
        """Print all scheduled jobs (for debugging)."""
        if not self._scheduler:
            logger.warning("Scheduler not initialized")
            return

        jobs = self.get_jobs()
        if not jobs:
            logger.info("No scheduled jobs")
            return

        logger.info("Scheduled jobs:")
        for job in jobs:
            logger.info(f"  - {job.id}: next run at {job.next_run_time}")

    # =========================================================================
    # Enhanced Status and Lifecycle Management
    # =========================================================================

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return bool(self._scheduler and self._scheduler.running)

    def get_scheduler_status(self) -> dict[str, Any]:
        """Get comprehensive scheduler status.

        Returns:
            Dictionary with scheduler status information
        """
        if not self._scheduler:
            return {"status": "not_initialized", "running": False}

        jobs = self.get_jobs()
        running_jobs = [j for j in jobs if j.next_run_time is not None]
        paused_jobs = [j for j in jobs if j.next_run_time is None]

        return {
            "status": "running" if self._scheduler.running else "stopped",
            "running": self._scheduler.running,
            "timezone": str(self.config.timezone),
            "job_store_type": self.config.job_store_type,
            "total_jobs": len(jobs),
            "active_jobs": len(running_jobs),
            "paused_jobs": len(paused_jobs),
        }

    def get_job_info(self, job_id: str) -> dict[str, Any] | None:
        """Get detailed information about a specific job.

        Args:
            job_id: Job ID

        Returns:
            Job information dictionary or None if not found
        """
        job = self.get_job(job_id)
        if not job:
            return None

        trigger_info = {}
        if hasattr(job.trigger, "interval"):
            trigger_info["type"] = "interval"
            trigger_info["interval"] = str(job.trigger.interval)
        elif hasattr(job.trigger, "cron"):
            trigger_info["type"] = "cron"

        return {
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "is_paused": job.next_run_time is None,
            "trigger": trigger_info,
            "func": f"{job.func.__module__}.{job.func.__name__}"
            if hasattr(job.func, "__module__")
            else str(job.func),
            "max_instances": job.max_instances,
            "coalesce": job.coalesce,
        }

    def get_next_run_times(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get upcoming job run times.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of upcoming runs sorted by time
        """
        jobs = self.get_jobs()
        upcoming = []

        for job in jobs:
            if job.next_run_time:
                upcoming.append(
                    {
                        "job_id": job.id,
                        "next_run": job.next_run_time.isoformat(),
                        "next_run_timestamp": job.next_run_time.timestamp(),
                    }
                )

        upcoming.sort(key=lambda x: x["next_run_timestamp"])
        return upcoming[:limit]

    def pause_all_jobs(self) -> int:
        """Pause all scheduled jobs.

        Returns:
            Number of jobs paused
        """
        if not self._scheduler:
            return 0

        jobs = self.get_jobs()
        count = 0
        for job in jobs:
            if job.next_run_time is not None:
                try:
                    self._scheduler.pause_job(job.id)
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to pause job {job.id}: {e}")

        logger.info(f"Paused {count} jobs")
        return count

    def resume_all_jobs(self) -> int:
        """Resume all paused jobs.

        Returns:
            Number of jobs resumed
        """
        if not self._scheduler:
            return 0

        jobs = self.get_jobs()
        count = 0
        for job in jobs:
            if job.next_run_time is None:
                try:
                    self._scheduler.resume_job(job.id)
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to resume job {job.id}: {e}")

        logger.info(f"Resumed {count} jobs")
        return count

    def remove_all_jobs(self) -> int:
        """Remove all scheduled jobs.

        Returns:
            Number of jobs removed
        """
        if not self._scheduler:
            return 0

        jobs = self.get_jobs()
        count = 0
        for job in jobs:
            try:
                self._scheduler.remove_job(job.id)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to remove job {job.id}: {e}")

        logger.info(f"Removed {count} jobs")
        return count

    def graceful_shutdown(self, timeout: float = 30.0) -> bool:
        """Gracefully shutdown the scheduler.

        Args:
            timeout: Maximum time to wait for jobs to complete

        Returns:
            True if shutdown completed within timeout
        """
        if not self._scheduler or not self._scheduler.running:
            return True

        logger.info(f"Starting graceful shutdown (timeout: {timeout}s)")
        start = time.time()

        self.pause_all_jobs()

        while time.time() - start < timeout:
            running = self._get_running_job_count()
            if running == 0:
                break
            time.sleep(0.5)

        elapsed = time.time() - start
        self._scheduler.shutdown(wait=False)

        if elapsed < timeout:
            logger.info(f"Graceful shutdown completed in {elapsed:.1f}s")
            return True
        else:
            logger.warning(f"Graceful shutdown timed out after {timeout}s")
            return False

    def _get_running_job_count(self) -> int:
        """Get count of currently running jobs."""
        if not self._scheduler:
            return 0
        try:
            executor = self._scheduler._executors.get("default")
            if executor and hasattr(executor, "_instances"):
                return sum(len(v) for v in executor._instances.values())
        except Exception:
            pass
        return 0

    def run_job_now(self, job_id: str) -> bool:
        """Immediately run a scheduled job.

        Args:
            job_id: Job ID to run

        Returns:
            True if job was triggered successfully
        """
        job = self.get_job(job_id)
        if not job:
            logger.warning(f"Job not found: {job_id}")
            return False

        try:
            job.func()
            logger.info(f"Job {job_id} executed manually")
            return True
        except Exception as e:
            logger.error(f"Failed to run job {job_id}: {e}")
            return False

    def reschedule_job(
        self,
        job_id: str,
        trigger: str,
        **trigger_args: Any,
    ) -> bool:
        """Reschedule a job with a new trigger.

        Args:
            job_id: Job ID to reschedule
            trigger: New trigger type
            **trigger_args: New trigger arguments

        Returns:
            True if rescheduled successfully
        """
        if not self._scheduler:
            return False

        try:
            if trigger == "interval":
                trigger_obj = IntervalTrigger(**trigger_args)
            elif trigger == "cron":
                trigger_obj = CronTrigger(**trigger_args, timezone=self.config.timezone)
            else:
                raise ValueError(f"Unsupported trigger type: {trigger}")

            self._scheduler.reschedule_job(job_id, trigger=trigger_obj)
            logger.info(f"Job {job_id} rescheduled with {trigger} trigger")
            return True
        except Exception as e:
            logger.error(f"Failed to reschedule job {job_id}: {e}")
            return False

    def export_jobs(self) -> list[dict[str, Any]]:
        """Export all job configurations.

        Returns:
            List of job configuration dictionaries
        """
        jobs = self.get_jobs()
        exported = []

        for job in jobs:
            info = self.get_job_info(job.id)
            if info:
                exported.append(info)

        return exported

    def get_job_statistics(self) -> dict[str, Any]:
        """Get statistics about all jobs.

        Returns:
            Dictionary with job statistics
        """
        jobs = self.get_jobs()
        active = sum(1 for j in jobs if j.next_run_time is not None)
        paused = len(jobs) - active

        trigger_types: dict[str, int] = {}
        for job in jobs:
            if hasattr(job.trigger, "interval"):
                t_type = "interval"
            elif hasattr(job.trigger, "fields"):
                t_type = "cron"
            else:
                t_type = "other"
            trigger_types[t_type] = trigger_types.get(t_type, 0) + 1

        return {
            "total_jobs": len(jobs),
            "active_jobs": active,
            "paused_jobs": paused,
            "trigger_types": trigger_types,
        }

    # =========================================================================
    # Health Monitoring and History Access
    # =========================================================================

    @property
    def hook_registry(self) -> HookRegistry:
        """Get the hook registry for adding custom hooks."""
        return self._hook_registry

    @property
    def health_monitor(self) -> JobHealthMonitor | None:
        """Get the health monitor instance."""
        return self._health_monitor

    @property
    def history_store(self) -> ExecutionHistoryStore | None:
        """Get the execution history store."""
        return self._history_store

    def get_health_status(self) -> dict[str, Any]:
        """Get health status of all jobs.

        Returns:
            Dictionary with health status information
        """
        if not self._health_monitor:
            return {"enabled": False}

        metrics = self._health_monitor.get_scheduler_metrics()
        return {
            "enabled": True,
            "overall_status": self._health_monitor.get_overall_status().value,
            "metrics": {
                "total_executions": metrics.total_executions,
                "successful": metrics.total_executions - metrics.total_failures,
                "failed": metrics.total_failures,
            },
            "unhealthy_jobs": [j.to_dict() for j in self._health_monitor.get_unhealthy_jobs()],
        }

    def get_job_health(self, job_id: str) -> dict[str, Any] | None:
        """Get health information for a specific job.

        Args:
            job_id: Job ID

        Returns:
            Health info dictionary or None
        """
        if not self._health_monitor:
            return None

        info = self._health_monitor.get_job_health(job_id)
        if not info:
            return None

        return {
            "job_id": info.job_id,
            "status": info.status.value,
            "total_runs": info.total_runs,
            "successful_runs": info.total_runs - info.total_failures,
            "failed_runs": info.total_failures,
            "consecutive_failures": info.consecutive_failures,
            "last_run": info.last_run.isoformat() if info.last_run else None,
            "last_success": info.last_success.isoformat() if info.last_success else None,
            "last_failure": info.last_failure.isoformat() if info.last_failure else None,
            "avg_duration": info.average_duration,
        }

    def get_execution_history(self, job_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Get execution history for a job.

        Args:
            job_id: Job ID
            limit: Maximum records to return

        Returns:
            List of execution records
        """
        if not self._history_store:
            return []

        records = self._history_store.get_executions(job_id, limit=limit)
        return [
            {
                "job_id": r.job_id,
                "timestamp": r.executed_at.isoformat(),
                "success": r.success,
                "duration": r.duration,
                "error": r.error,
            }
            for r in records
        ]

    def get_execution_statistics(self, job_id: str) -> dict[str, Any]:
        """Get execution statistics for a job.

        Args:
            job_id: Job ID

        Returns:
            Statistics dictionary
        """
        if not self._history_store:
            return {}

        return self._history_store.get_statistics(job_id)

    def cleanup_history(self, days: int | None = None) -> int:
        """Clean up old execution history records.

        Args:
            days: Records older than this will be deleted.
                  If None, uses config value.

        Returns:
            Number of records deleted
        """
        if not self._history_store:
            return 0

        retention_days = days or getattr(self.config, "history_retention_days", 30)
        return self._history_store.cleanup_old_records(days=retention_days)

    def get_job_run_count(self, job_id: str) -> int:
        """Get the number of times a job has run in this session.

        Args:
            job_id: Job ID

        Returns:
            Run count
        """
        return self._job_run_counts.get(job_id, 0)
