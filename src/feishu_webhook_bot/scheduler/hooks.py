"""Job execution hooks for the scheduler."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ..core.logger import get_logger

logger = get_logger("scheduler.hooks")


class HookPriority(int, Enum):
    """Priority levels for hook execution order."""

    HIGHEST = 0
    HIGH = 25
    NORMAL = 50
    LOW = 75
    LOWEST = 100


@dataclass
class JobExecutionContext:
    """Context information for job execution."""

    job_id: str
    job_name: str
    scheduled_time: datetime | None
    actual_start_time: datetime
    trigger_type: str = "unknown"
    run_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_name": self.job_name,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "actual_start_time": self.actual_start_time.isoformat(),
            "trigger_type": self.trigger_type,
            "run_count": self.run_count,
        }


@dataclass
class JobExecutionResult:
    """Result of a job execution."""

    job_id: str
    success: bool
    start_time: datetime
    end_time: datetime
    duration: float
    return_value: Any = None
    error: Exception | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "success": self.success,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration": self.duration,
            "error_message": self.error_message,
        }


class JobHook(ABC):
    """Base class for job execution hooks."""

    priority: HookPriority = HookPriority.NORMAL

    @abstractmethod
    def before_job_execution(self, context: JobExecutionContext) -> bool:
        """Called before job executes. Return False to skip."""
        pass

    @abstractmethod
    def after_job_execution(self, context: JobExecutionContext, result: JobExecutionResult) -> None:
        """Called after job completes."""
        pass

    @abstractmethod
    def on_job_error(self, context: JobExecutionContext, error: Exception) -> bool:
        """Called on job error. Return True to suppress."""
        pass

    def on_job_timeout(self, context: JobExecutionContext, timeout_seconds: float) -> None:
        """Called on job timeout."""
        pass


class LoggingHook(JobHook):
    """Hook that logs job execution details."""

    priority = HookPriority.HIGHEST

    def __init__(self, log_level: str = "INFO") -> None:
        self._log = getattr(logger, log_level.lower(), logger.info)

    def before_job_execution(self, context: JobExecutionContext) -> bool:
        self._log(f"Job starting: {context.job_id} (run #{context.run_count})")
        return True

    def after_job_execution(self, context: JobExecutionContext, result: JobExecutionResult) -> None:
        if result.success:
            self._log(f"Job completed: {context.job_id} ({result.duration:.3f}s)")
        else:
            logger.error(
                f"Job failed: {context.job_id} ({result.duration:.3f}s, error: {result.error_message})"
            )

    def on_job_error(self, context: JobExecutionContext, error: Exception) -> bool:
        logger.exception(f"Job {context.job_id} raised exception: {error}")
        return False


@dataclass
class JobMetrics:
    """Metrics for a single job."""

    job_id: str
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_duration: float = 0.0
    min_duration: float = 0.0
    max_duration: float = 0.0
    last_duration: float = 0.0
    last_execution: datetime | None = None

    @property
    def success_rate(self) -> float:
        return (self.success_count / self.execution_count * 100) if self.execution_count else 0.0

    @property
    def average_duration(self) -> float:
        return self.total_duration / self.execution_count if self.execution_count else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(self.success_rate, 2),
            "average_duration": round(self.average_duration, 3),
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
        }


class MetricsHook(JobHook):
    """Hook that collects job execution metrics."""

    priority = HookPriority.HIGH

    def __init__(self, max_history: int = 1000) -> None:
        self._metrics: dict[str, JobMetrics] = {}
        self._history: list[JobExecutionResult] = []
        self._max_history = max_history
        self._lock = threading.Lock()

    def before_job_execution(self, context: JobExecutionContext) -> bool:
        with self._lock:
            if context.job_id not in self._metrics:
                self._metrics[context.job_id] = JobMetrics(job_id=context.job_id)
            self._metrics[context.job_id].execution_count += 1
        return True

    def after_job_execution(self, context: JobExecutionContext, result: JobExecutionResult) -> None:
        with self._lock:
            m = self._metrics.get(context.job_id)
            if m:
                if result.success:
                    m.success_count += 1
                else:
                    m.failure_count += 1
                m.total_duration += result.duration
                m.last_execution = result.end_time
                m.last_duration = result.duration
                if m.min_duration == 0 or result.duration < m.min_duration:
                    m.min_duration = result.duration
                if result.duration > m.max_duration:
                    m.max_duration = result.duration
            self._history.append(result)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history :]

    def on_job_error(self, context: JobExecutionContext, error: Exception) -> bool:
        return False

    def get_metrics(self, job_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            if job_id:
                m = self._metrics.get(job_id)
                return m.to_dict() if m else {}
            return {jid: m.to_dict() for jid, m in self._metrics.items()}

    def get_history(self, job_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            history = [h for h in self._history if job_id is None or h.job_id == job_id]
            return [h.to_dict() for h in history[-limit:]]


class AlertHook(JobHook):
    """Hook that sends alerts on job failures."""

    priority = HookPriority.LOW

    def __init__(
        self,
        alert_callback: Callable[[str, str, dict[str, Any]], None] | None = None,
        failure_threshold: int = 3,
    ) -> None:
        self._alert_callback = alert_callback
        self._failure_threshold = failure_threshold
        self._consecutive_failures: dict[str, int] = {}
        self._lock = threading.Lock()

    def before_job_execution(self, context: JobExecutionContext) -> bool:
        return True

    def after_job_execution(self, context: JobExecutionContext, result: JobExecutionResult) -> None:
        with self._lock:
            if result.success:
                self._consecutive_failures[context.job_id] = 0
            else:
                failures = self._consecutive_failures.get(context.job_id, 0) + 1
                self._consecutive_failures[context.job_id] = failures
                if failures >= self._failure_threshold and self._alert_callback:
                    self._alert_callback(
                        f"Job Failure: {context.job_id}",
                        f"Job failed {failures} times. Error: {result.error_message}",
                        {"job_id": context.job_id, "failures": failures},
                    )

    def on_job_error(self, context: JobExecutionContext, error: Exception) -> bool:
        return False


class HookRegistry:
    """Registry for managing job execution hooks."""

    def __init__(self) -> None:
        self._hooks: list[JobHook] = []
        self._lock = threading.Lock()

    def register(self, hook: JobHook) -> None:
        with self._lock:
            self._hooks.append(hook)
            self._hooks.sort(key=lambda h: h.priority)
        logger.debug(f"Registered hook: {hook.__class__.__name__}")

    def unregister(self, hook: JobHook) -> bool:
        with self._lock:
            if hook in self._hooks:
                self._hooks.remove(hook)
                return True
            return False

    def get_hooks(self) -> list[JobHook]:
        with self._lock:
            return list(self._hooks)

    def clear(self) -> None:
        with self._lock:
            self._hooks.clear()

    def before_execution(self, context: JobExecutionContext) -> bool:
        for hook in self.get_hooks():
            try:
                if not hook.before_job_execution(context):
                    return False
            except Exception as e:
                logger.error(f"Hook {hook.__class__.__name__} failed: {e}")
        return True

    def after_execution(self, context: JobExecutionContext, result: JobExecutionResult) -> None:
        for hook in self.get_hooks():
            try:
                hook.after_job_execution(context, result)
            except Exception as e:
                logger.error(f"Hook {hook.__class__.__name__} failed: {e}")

    def on_error(self, context: JobExecutionContext, error: Exception) -> bool:
        suppress = False
        for hook in self.get_hooks():
            try:
                if hook.on_job_error(context, error):
                    suppress = True
            except Exception as e:
                logger.error(f"Hook {hook.__class__.__name__} failed: {e}")
        return suppress


def create_default_hook_registry() -> HookRegistry:
    """Create a hook registry with default hooks."""
    registry = HookRegistry()
    registry.register(LoggingHook())
    registry.register(MetricsHook())
    return registry


__all__ = [
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
]
