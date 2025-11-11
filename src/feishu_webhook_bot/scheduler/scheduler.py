"""Task scheduler for periodic jobs and workflows.

This module wraps APScheduler to provide:
- Easy job registration
- Cron and interval scheduling
- Job persistence (SQLite)
- Error handling and retry logic
"""

from __future__ import annotations

import functools
from collections.abc import Callable
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
        self._setup_scheduler()

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

        # Configure executors
        executors = {"default": ThreadPoolExecutor(max_workers=10)}

        # Job defaults
        job_defaults = {
            "coalesce": True,  # Combine missed runs
            "max_instances": 1,  # Only one instance per job
            "misfire_grace_time": 60,  # 60 seconds grace period
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
        logger.info(f"Job {event.job_id} executed successfully")

    def _job_error(self, event: JobExecutionEvent) -> None:
        """Handler for job execution errors.

        Args:
            event: Job execution event
        """
        logger.error(
            f"Job {event.job_id} failed with exception: {event.exception}",
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
