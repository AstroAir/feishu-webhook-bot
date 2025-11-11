"""Mock scheduler for testing."""

from collections.abc import Callable
from typing import Any


class MockJob:
    """Mock APScheduler job."""

    def __init__(self, job_id: str, func: Callable, trigger: Any, **kwargs):
        self.id = job_id
        self.func = func
        self.trigger = trigger
        self.kwargs = kwargs
        self.next_run_time = None

    def __repr__(self):
        return f"MockJob(id={self.id})"


class MockScheduler:
    """Mock scheduler for testing task scheduling."""

    def __init__(self):
        self.jobs = {}
        self.running = False
        self.started = False

    def add_job(
        self,
        func: Callable,
        trigger: str | None = None,
        job_id: str | None = None,
        **kwargs,
    ) -> MockJob:
        """Add a job to the scheduler."""
        if job_id is None:
            job_id = f"job_{len(self.jobs)}"

        job = MockJob(job_id, func, trigger, **kwargs)
        self.jobs[job_id] = job
        return job

    def remove_job(self, job_id: str) -> None:
        """Remove a job from the scheduler."""
        if job_id in self.jobs:
            del self.jobs[job_id]

    def get_job(self, job_id: str) -> MockJob | None:
        """Get a job by ID."""
        return self.jobs.get(job_id)

    def get_jobs(self) -> list[MockJob]:
        """Get all jobs."""
        return list(self.jobs.values())

    def start(self) -> None:
        """Start the scheduler."""
        self.running = True
        self.started = True

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler."""
        self.running = False

    def pause_job(self, job_id: str) -> None:
        """Pause a job."""
        if job_id in self.jobs:
            self.jobs[job_id].paused = True

    def resume_job(self, job_id: str) -> None:
        """Resume a job."""
        if job_id in self.jobs:
            self.jobs[job_id].paused = False

    def modify_job(self, job_id: str, **changes) -> MockJob | None:
        """Modify a job."""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            for key, value in changes.items():
                setattr(job, key, value)
            return job
        return None

    def reschedule_job(self, job_id: str, trigger: Any = None, **trigger_args) -> MockJob | None:
        """Reschedule a job."""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.trigger = trigger
            return job
        return None

    def execute_job(self, job_id: str) -> Any:
        """Manually execute a job."""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            return job.func()
        return None

    def clear(self) -> None:
        """Clear all jobs."""
        self.jobs.clear()
