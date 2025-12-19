"""Job monitoring and health checking for the scheduler."""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any

from ..core.logger import get_logger

if TYPE_CHECKING:
    from .scheduler import TaskScheduler

logger = get_logger("scheduler.monitors")


class HealthStatus(str, Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class JobHealthInfo:
    """Health information for a single job."""

    job_id: str
    status: HealthStatus = HealthStatus.UNKNOWN
    last_success: datetime | None = None
    last_failure: datetime | None = None
    last_run: datetime | None = None
    consecutive_failures: int = 0
    total_runs: int = 0
    total_failures: int = 0
    average_duration: float = 0.0
    is_running: bool = False
    issues: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 100.0
        return ((self.total_runs - self.total_failures) / self.total_runs) * 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "consecutive_failures": self.consecutive_failures,
            "total_runs": self.total_runs,
            "success_rate": round(self.success_rate, 2),
            "is_running": self.is_running,
            "issues": self.issues,
        }


@dataclass
class SchedulerHealthConfig:
    """Configuration for scheduler health monitoring."""

    enabled: bool = True
    check_interval_seconds: int = 60
    failure_threshold: int = 3
    stale_job_threshold_seconds: int = 3600
    success_rate_warning_threshold: float = 90.0
    success_rate_critical_threshold: float = 70.0


@dataclass
class SchedulerMetrics:
    """Aggregated metrics for the scheduler."""

    total_jobs: int = 0
    running_jobs: int = 0
    paused_jobs: int = 0
    healthy_jobs: int = 0
    warning_jobs: int = 0
    critical_jobs: int = 0
    total_executions: int = 0
    total_failures: int = 0
    overall_success_rate: float = 100.0
    uptime_seconds: float = 0.0
    last_check: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_jobs": self.total_jobs,
            "running_jobs": self.running_jobs,
            "paused_jobs": self.paused_jobs,
            "healthy_jobs": self.healthy_jobs,
            "warning_jobs": self.warning_jobs,
            "critical_jobs": self.critical_jobs,
            "total_executions": self.total_executions,
            "total_failures": self.total_failures,
            "overall_success_rate": round(self.overall_success_rate, 2),
            "uptime_seconds": round(self.uptime_seconds, 1),
            "last_check": self.last_check.isoformat() if self.last_check else None,
        }


class JobHealthMonitor:
    """Monitors the health of scheduled jobs."""

    def __init__(
        self, scheduler: TaskScheduler | None = None, config: SchedulerHealthConfig | None = None
    ) -> None:
        self._scheduler = scheduler
        self._config = config or SchedulerHealthConfig()
        self._job_health: dict[str, JobHealthInfo] = {}
        self._running_jobs: dict[str, datetime] = {}
        self._lock = threading.Lock()
        self._monitor_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._start_time = datetime.now()

    def set_scheduler(self, scheduler: TaskScheduler) -> None:
        self._scheduler = scheduler

    def start(self) -> None:
        if not self._config.enabled:
            return
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Health monitor started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Health monitor stopped")

    def _monitor_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._check_all_jobs()
            except Exception as e:
                logger.error(f"Health check failed: {e}")
            self._stop_event.wait(self._config.check_interval_seconds)

    def _check_all_jobs(self) -> None:
        if not self._scheduler:
            return
        jobs = self._scheduler.get_jobs()
        now = datetime.now()
        with self._lock:
            for job in jobs:
                if job.id not in self._job_health:
                    self._job_health[job.id] = JobHealthInfo(job_id=job.id)
                health = self._job_health[job.id]
                health.issues.clear()
                if health.last_run:
                    since = (now - health.last_run).total_seconds()
                    if since > self._config.stale_job_threshold_seconds:
                        health.issues.append(f"Stale: {since:.0f}s since last run")
                if health.consecutive_failures >= self._config.failure_threshold:
                    health.issues.append(f"Consecutive failures: {health.consecutive_failures}")
                if (
                    health.total_runs > 0
                    and health.success_rate < self._config.success_rate_critical_threshold
                ):
                    health.status = HealthStatus.CRITICAL
                elif health.issues:
                    health.status = HealthStatus.WARNING
                else:
                    health.status = HealthStatus.HEALTHY

    def record_execution_start(self, job_id: str) -> None:
        with self._lock:
            self._running_jobs[job_id] = datetime.now()
            if job_id in self._job_health:
                self._job_health[job_id].is_running = True

    def record_execution_end(self, job_id: str, success: bool, duration: float) -> None:
        now = datetime.now()
        with self._lock:
            self._running_jobs.pop(job_id, None)
            if job_id not in self._job_health:
                self._job_health[job_id] = JobHealthInfo(job_id=job_id)
            health = self._job_health[job_id]
            health.is_running = False
            health.last_run = now
            health.total_runs += 1
            if success:
                health.last_success = now
                health.consecutive_failures = 0
            else:
                health.last_failure = now
                health.total_failures += 1
                health.consecutive_failures += 1

    def get_job_health(self, job_id: str) -> JobHealthInfo | None:
        with self._lock:
            return self._job_health.get(job_id)

    def get_all_health(self) -> dict[str, JobHealthInfo]:
        with self._lock:
            return dict(self._job_health)

    def get_unhealthy_jobs(self) -> list[JobHealthInfo]:
        with self._lock:
            return [h for h in self._job_health.values() if h.status != HealthStatus.HEALTHY]

    def get_scheduler_metrics(self) -> SchedulerMetrics:
        metrics = SchedulerMetrics()
        with self._lock:
            all_health = list(self._job_health.values())
        if self._scheduler:
            jobs = self._scheduler.get_jobs()
            metrics.total_jobs = len(jobs)
            metrics.paused_jobs = sum(1 for j in jobs if j.next_run_time is None)
        metrics.running_jobs = len(self._running_jobs)
        metrics.healthy_jobs = sum(1 for h in all_health if h.status == HealthStatus.HEALTHY)
        metrics.warning_jobs = sum(1 for h in all_health if h.status == HealthStatus.WARNING)
        metrics.critical_jobs = sum(1 for h in all_health if h.status == HealthStatus.CRITICAL)
        total_runs = sum(h.total_runs for h in all_health)
        total_failures = sum(h.total_failures for h in all_health)
        metrics.total_executions = total_runs
        metrics.total_failures = total_failures
        if total_runs > 0:
            metrics.overall_success_rate = ((total_runs - total_failures) / total_runs) * 100
        metrics.uptime_seconds = (datetime.now() - self._start_time).total_seconds()
        metrics.last_check = datetime.now()
        return metrics

    def get_overall_status(self) -> HealthStatus:
        metrics = self.get_scheduler_metrics()
        if metrics.critical_jobs > 0:
            return HealthStatus.CRITICAL
        if metrics.warning_jobs > 0:
            return HealthStatus.WARNING
        if metrics.total_jobs == 0:
            return HealthStatus.UNKNOWN
        return HealthStatus.HEALTHY

    def reset(self) -> None:
        with self._lock:
            self._job_health.clear()
            self._running_jobs.clear()


class ExecutionHistoryTracker:
    """Tracks execution history for jobs."""

    def __init__(self, max_history_per_job: int = 100) -> None:
        self._max_history = max_history_per_job
        self._history: dict[str, deque[dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def record(self, job_id: str, success: bool, duration: float, error: str | None = None) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "duration": duration,
            "error": error,
        }
        with self._lock:
            if job_id not in self._history:
                self._history[job_id] = deque(maxlen=self._max_history)
            self._history[job_id].append(entry)

    def get_history(self, job_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        with self._lock:
            history = self._history.get(job_id)
            if not history:
                return []
            entries = list(history)
            return entries[-limit:] if limit else entries

    def get_recent_failures(self, hours: int = 24, limit: int = 50) -> list[dict[str, Any]]:
        cutoff = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff.isoformat()
        failures = []
        with self._lock:
            for job_id, history in self._history.items():
                for entry in history:
                    if not entry["success"] and entry["timestamp"] > cutoff_str:
                        failures.append({"job_id": job_id, **entry})
        failures.sort(key=lambda x: x["timestamp"], reverse=True)
        return failures[:limit]

    def clear(self, job_id: str | None = None) -> None:
        with self._lock:
            if job_id:
                self._history.pop(job_id, None)
            else:
                self._history.clear()


__all__ = [
    "ExecutionHistoryTracker",
    "HealthStatus",
    "JobHealthInfo",
    "JobHealthMonitor",
    "SchedulerHealthConfig",
    "SchedulerMetrics",
]
