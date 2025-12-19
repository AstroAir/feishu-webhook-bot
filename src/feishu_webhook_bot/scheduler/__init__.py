"""Scheduler module for running periodic tasks and workflows.

This package provides:
- APScheduler-based task scheduling
- Job persistence
- Cron expression parsing and validation
- Job execution hooks and monitoring
- Execution history tracking
"""

from .expressions import (
    CronExpressionParser,
    CronField,
    CronParseResult,
    DayOfWeek,
    IntervalBuilder,
    ScheduleBuilder,
    every,
)
from .hooks import (
    AlertHook,
    HookPriority,
    HookRegistry,
    JobExecutionContext,
    JobExecutionResult,
    JobHook,
    JobMetrics,
    LoggingHook,
    MetricsHook,
    create_default_hook_registry,
)
from .monitors import (
    ExecutionHistoryTracker,
    HealthStatus,
    JobHealthInfo,
    JobHealthMonitor,
    SchedulerHealthConfig,
    SchedulerMetrics,
)
from .scheduler import TaskScheduler, job
from .stores import ExecutionHistoryStore, ExecutionRecord, JobStoreFactory

__all__ = [
    # Scheduler
    "TaskScheduler",
    "job",
    # Expressions
    "CronExpressionParser",
    "CronField",
    "CronParseResult",
    "DayOfWeek",
    "IntervalBuilder",
    "ScheduleBuilder",
    "every",
    # Hooks
    "AlertHook",
    "HookPriority",
    "HookRegistry",
    "JobExecutionContext",
    "JobExecutionResult",
    "JobHook",
    "JobMetrics",
    "LoggingHook",
    "MetricsHook",
    "create_default_hook_registry",
    # Monitors
    "ExecutionHistoryTracker",
    "HealthStatus",
    "JobHealthInfo",
    "JobHealthMonitor",
    "SchedulerHealthConfig",
    "SchedulerMetrics",
    # Stores
    "ExecutionHistoryStore",
    "ExecutionRecord",
    "JobStoreFactory",
]
