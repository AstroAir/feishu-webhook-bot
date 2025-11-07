"""Tests for the scheduler module."""

import time

import pytest

from feishu_webhook_bot.core.config import SchedulerConfig
from feishu_webhook_bot.scheduler import TaskScheduler, job


def test_job_decorator():
    """Test job decorator stores metadata."""

    @job(trigger="interval", minutes=5)
    def test_task():
        pass

    assert hasattr(test_task, "_scheduler_job")
    assert test_task._scheduler_job is True  # type: ignore
    assert test_task._trigger_type == "interval"  # type: ignore
    assert test_task._trigger_args == {"minutes": 5}  # type: ignore


def test_job_decorator_cron():
    """Test job decorator with cron trigger."""

    @job(trigger="cron", hour="9", minute="0")
    def morning_task():
        pass

    assert morning_task._scheduler_job is True  # type: ignore
    assert morning_task._trigger_type == "cron"  # type: ignore
    assert morning_task._trigger_args == {"hour": "9", "minute": "0"}  # type: ignore


def test_scheduler_initialization():
    """Test scheduler initialization."""
    config = SchedulerConfig(enabled=True, timezone="UTC", job_store_type="memory")

    scheduler = TaskScheduler(config)
    assert scheduler.config == config
    assert scheduler._scheduler is not None


def test_scheduler_start_shutdown():
    """Test scheduler start and shutdown."""
    config = SchedulerConfig(enabled=True, timezone="UTC")
    scheduler = TaskScheduler(config)

    scheduler.start()
    assert scheduler._scheduler.running

    scheduler.shutdown()
    assert not scheduler._scheduler.running


def test_scheduler_add_interval_job():
    """Test adding an interval-based job."""
    config = SchedulerConfig(enabled=True, timezone="UTC")
    scheduler = TaskScheduler(config)

    call_count = []

    def test_job_func():
        call_count.append(1)

    scheduler.start()

    # Add job that runs every second
    job_id = scheduler.add_job(test_job_func, trigger="interval", seconds=1, job_id="test_interval")

    assert job_id == "test_interval"

    # Wait for job to execute at least once
    time.sleep(2.5)

    scheduler.shutdown()

    # Should have run at least twice
    assert len(call_count) >= 2


def test_scheduler_add_cron_job():
    """Test adding a cron-based job."""
    config = SchedulerConfig(enabled=True, timezone="UTC")
    scheduler = TaskScheduler(config)

    def test_job_func():
        pass

    scheduler.start()

    # Add job that runs at a specific time (won't actually run in test)
    job_id = scheduler.add_job(
        test_job_func, trigger="cron", hour="9", minute="0", job_id="test_cron"
    )

    assert job_id == "test_cron"

    scheduler.shutdown()


def test_scheduler_register_decorated_job():
    """Test registering a decorated job."""
    config = SchedulerConfig(enabled=True, timezone="UTC")
    scheduler = TaskScheduler(config)

    call_count = []

    @job(trigger="interval", seconds=1)
    def decorated_task():
        call_count.append(1)

    scheduler.start()
    job_id = scheduler.register_job(decorated_task)

    assert job_id is not None

    # Wait for execution
    time.sleep(2.5)

    scheduler.shutdown()

    assert len(call_count) >= 2


def test_scheduler_remove_job():
    """Test removing a job."""
    config = SchedulerConfig(enabled=True, timezone="UTC")
    scheduler = TaskScheduler(config)

    def test_job_func():
        pass

    scheduler.start()

    job_id = scheduler.add_job(test_job_func, trigger="interval", seconds=1, job_id="test_remove")

    # Remove the job
    scheduler.remove_job(job_id)

    # Verify job is removed
    job = scheduler.get_job(job_id)
    assert job is None

    scheduler.shutdown()


def test_scheduler_pause_resume_job():
    """Test pausing and resuming a job."""
    config = SchedulerConfig(enabled=True, timezone="UTC")
    scheduler = TaskScheduler(config)

    call_count = []

    def test_job_func():
        call_count.append(1)

    scheduler.start()

    job_id = scheduler.add_job(test_job_func, trigger="interval", seconds=1, job_id="test_pause")

    # Let it run once
    time.sleep(1.5)
    initial_count = len(call_count)
    assert initial_count >= 1

    # Pause the job
    scheduler.pause_job(job_id)
    job = scheduler.get_job(job_id)
    assert job is not None

    # Wait and verify it doesn't run
    time.sleep(2)
    paused_count = len(call_count)
    assert paused_count == initial_count

    # Resume the job
    scheduler.resume_job(job_id)

    # Wait and verify it runs again
    time.sleep(2)
    resumed_count = len(call_count)
    assert resumed_count > paused_count

    scheduler.shutdown()


def test_scheduler_get_jobs():
    """Test getting all jobs."""
    config = SchedulerConfig(enabled=True, timezone="UTC")
    scheduler = TaskScheduler(config)

    def job1():
        pass

    def job2():
        pass

    scheduler.start()

    scheduler.add_job(job1, trigger="interval", seconds=10, job_id="job1")
    scheduler.add_job(job2, trigger="interval", seconds=20, job_id="job2")

    jobs = scheduler.get_jobs()
    assert len(jobs) == 2

    job_ids = [job.id for job in jobs]
    assert "job1" in job_ids
    assert "job2" in job_ids

    scheduler.shutdown()


def test_scheduler_get_specific_job():
    """Test getting a specific job by ID."""
    config = SchedulerConfig(enabled=True, timezone="UTC")
    scheduler = TaskScheduler(config)

    def test_job_func():
        pass

    scheduler.start()

    job_id = scheduler.add_job(test_job_func, trigger="interval", seconds=1, job_id="specific_job")

    # Get the job
    job = scheduler.get_job(job_id)
    assert job is not None
    assert job.id == "specific_job"

    scheduler.shutdown()


def test_scheduler_job_error_handling():
    """Test error handling in jobs."""
    config = SchedulerConfig(enabled=True, timezone="UTC")
    scheduler = TaskScheduler(config)

    def failing_job():
        raise ValueError("Test error")

    scheduler.start()

    # Job should be added even if it will fail
    job_id = scheduler.add_job(failing_job, trigger="interval", seconds=1, job_id="failing_test")

    assert job_id == "failing_test"

    # Wait for it to attempt execution
    time.sleep(1.5)

    # Scheduler should still be running
    assert scheduler._scheduler.running

    scheduler.shutdown()


def test_scheduler_disabled():
    """Test scheduler when disabled in config."""
    config = SchedulerConfig(enabled=False, timezone="UTC")
    scheduler = TaskScheduler(config)

    # Should raise error when trying to start disabled scheduler
    with pytest.raises(RuntimeError, match="Scheduler is disabled"):
        scheduler.start()


def test_scheduler_register_jobs_multiple():
    """Test registering multiple jobs at once."""
    config = SchedulerConfig(enabled=True, timezone="UTC")
    scheduler = TaskScheduler(config)

    @job(trigger="interval", seconds=10)
    def task1():
        pass

    @job(trigger="interval", seconds=20)
    def task2():
        pass

    def task3():  # Not decorated
        pass

    scheduler.start()
    job_ids = scheduler.register_jobs(task1, task2, task3)

    # Only task1 and task2 should be registered
    assert len(job_ids) == 2

    scheduler.shutdown()


def test_scheduler_print_jobs():
    """Test print_jobs method."""
    config = SchedulerConfig(enabled=True, timezone="UTC")
    scheduler = TaskScheduler(config)

    def test_job_func():
        pass

    scheduler.start()
    scheduler.add_job(test_job_func, trigger="interval", seconds=10, job_id="print_test")

    # Should not raise any errors
    scheduler.print_jobs()

    scheduler.shutdown()


def test_scheduler_invalid_trigger():
    """Test adding job with invalid trigger type."""
    config = SchedulerConfig(enabled=True, timezone="UTC")
    scheduler = TaskScheduler(config)

    def test_job_func():
        pass

    scheduler.start()

    with pytest.raises(ValueError, match="Unsupported trigger type"):
        scheduler.add_job(test_job_func, trigger="invalid_trigger")

    scheduler.shutdown()


def test_scheduler_job_replace_existing():
    """Test replacing an existing job."""
    config = SchedulerConfig(enabled=True, timezone="UTC")
    scheduler = TaskScheduler(config)

    def job_v1():
        return "v1"

    def job_v2():
        return "v2"

    scheduler.start()

    # Add initial job
    scheduler.add_job(job_v1, trigger="interval", seconds=10, job_id="replaceable")

    # Replace with new job
    scheduler.add_job(
        job_v2,
        trigger="interval",
        seconds=5,
        job_id="replaceable",
        replace_existing=True,
    )

    jobs = scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "replaceable"

    scheduler.shutdown()


def test_scheduler_modify_job():
    """Test modifying an existing job."""
    config = SchedulerConfig(enabled=True, timezone="UTC")
    scheduler = TaskScheduler(config)

    def job_func():
        pass

    scheduler.start()
    job_id = scheduler.add_job(job_func, trigger="interval", seconds=10, job_id="modifiable_job")

    # Modify the job's trigger
    scheduler.modify_job(job_id, trigger="interval", seconds=5)

    modified_job = scheduler.get_job(job_id)
    assert modified_job is not None
    # Note: Direct comparison of trigger objects is complex. We infer success if no error is raised
    # and the job still exists. A more detailed test would mock the scheduler's modify_job.
    assert modified_job.id == "modifiable_job"

    scheduler.shutdown()


def test_add_job_generates_unique_ids():
    """Test that add_job generates unique IDs when no job_id is provided."""
    config = SchedulerConfig(enabled=True, timezone="UTC")
    scheduler = TaskScheduler(config)

    def job_func():
        pass

    scheduler.start()

    # Add the same function twice without an ID
    job_id1 = scheduler.add_job(job_func, trigger="interval", seconds=10)
    job_id2 = scheduler.add_job(job_func, trigger="interval", seconds=10)

    assert job_id1 != job_id2
    assert len(scheduler.get_jobs()) == 2

    scheduler.shutdown()


def test_scheduler_uses_sqlite_jobstore(mocker, tmp_path):
    """Test that the scheduler attempts to use SQLiteJobStore when configured."""
    # Mock that SQLAlchemy is installed
    mocker.patch("feishu_webhook_bot.scheduler.scheduler.HAS_SQLALCHEMY", True)
    mock_sql_jobstore = mocker.patch("feishu_webhook_bot.scheduler.scheduler.SQLAlchemyJobStore")

    db_path = tmp_path / "jobs.db"
    config = SchedulerConfig(
        enabled=True, timezone="UTC", job_store_type="sqlite", job_store_path=str(db_path)
    )

    scheduler = TaskScheduler(config)

    # Verify that SQLAlchemyJobStore was initialized with the correct URL
    mock_sql_jobstore.assert_called_once_with(url=f"sqlite:///{db_path}")
    assert scheduler._scheduler is not None
