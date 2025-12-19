"""Tests for enhanced scheduler module functionality."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from feishu_webhook_bot.core.config import SchedulerConfig
from feishu_webhook_bot.scheduler import (
    AlertHook,
    CronExpressionParser,
    DayOfWeek,
    ExecutionHistoryStore,
    ExecutionHistoryTracker,
    HealthStatus,
    HookRegistry,
    IntervalBuilder,
    JobExecutionContext,
    JobExecutionResult,
    JobHealthMonitor,
    JobStoreFactory,
    LoggingHook,
    MetricsHook,
    ScheduleBuilder,
    SchedulerHealthConfig,
    TaskScheduler,
    create_default_hook_registry,
    every,
    job,
)


class TestCronExpressionParser:
    """Tests for CronExpressionParser."""

    def test_parse_valid_expression(self):
        result = CronExpressionParser.parse("0 9 * * *")
        assert result.valid is True
        assert result.minute == "0"
        assert result.hour == "9"
        assert result.day == "*"
        assert result.month == "*"
        assert result.day_of_week == "*"

    def test_parse_invalid_field_count(self):
        result = CronExpressionParser.parse("0 9 *")
        assert result.valid is False
        assert "Expected 5 fields" in result.error

    def test_parse_invalid_minute(self):
        result = CronExpressionParser.parse("60 9 * * *")
        assert result.valid is False
        assert "minute" in result.error.lower()

    def test_parse_range(self):
        result = CronExpressionParser.parse("0 9-17 * * *")
        assert result.valid is True
        assert result.hour == "9-17"

    def test_parse_step(self):
        result = CronExpressionParser.parse("*/5 * * * *")
        assert result.valid is True
        assert result.minute == "*/5"

    def test_parse_list(self):
        result = CronExpressionParser.parse("0 9,12,18 * * *")
        assert result.valid is True
        assert result.hour == "9,12,18"

    def test_parse_day_of_week_alias(self):
        result = CronExpressionParser.parse("0 9 * * mon")
        assert result.valid is True
        assert result.day_of_week == "mon"

    def test_validate(self):
        valid, error = CronExpressionParser.validate("0 9 * * *")
        assert valid is True
        assert error is None

        valid, error = CronExpressionParser.validate("invalid")
        assert valid is False
        assert error is not None

    def test_describe(self):
        desc = CronExpressionParser.describe("0 9 * * *")
        assert "09:00" in desc

        desc = CronExpressionParser.describe("* * * * *")
        assert "Every minute" in desc

    def test_get_next_n_runs(self):
        runs = CronExpressionParser.get_next_n_runs("0 * * * *", n=3)
        assert len(runs) == 3
        for run in runs:
            assert run.minute == 0


class TestIntervalBuilder:
    """Tests for IntervalBuilder."""

    def test_build_minutes(self):
        builder = IntervalBuilder().minutes(5)
        trigger = builder.build()
        assert trigger.interval == timedelta(minutes=5)

    def test_build_hours(self):
        builder = IntervalBuilder().hours(2)
        trigger = builder.build()
        assert trigger.interval == timedelta(hours=2)

    def test_every_minutes(self):
        builder = every(10).minutes
        trigger = builder.build()
        assert trigger.interval == timedelta(minutes=10)

    def test_every_hours(self):
        builder = every(1).hours
        trigger = builder.build()
        assert trigger.interval == timedelta(hours=1)

    def test_chain_methods(self):
        builder = IntervalBuilder().hours(1).minutes(30)
        trigger = builder.build()
        assert trigger.interval == timedelta(hours=1, minutes=30)


class TestScheduleBuilder:
    """Tests for ScheduleBuilder."""

    def test_daily_at(self):
        builder = ScheduleBuilder()
        trigger = builder.daily_at(9, 30)
        assert trigger is not None

    def test_weekly_on(self):
        builder = ScheduleBuilder()
        trigger = builder.weekly_on([DayOfWeek.MONDAY, DayOfWeek.FRIDAY], 9, 0)
        assert trigger is not None

    def test_monthly_on(self):
        builder = ScheduleBuilder()
        trigger = builder.monthly_on(15, 10, 0)
        assert trigger is not None

    def test_every_n_minutes(self):
        builder = ScheduleBuilder()
        trigger = builder.every_n_minutes(15)
        assert trigger is not None

    def test_weekdays_at(self):
        builder = ScheduleBuilder()
        trigger = builder.weekdays_at(9, 0)
        assert trigger is not None

    def test_cron(self):
        builder = ScheduleBuilder()
        trigger = builder.cron("0 9 * * *")
        assert trigger is not None

        trigger = builder.cron("invalid")
        assert trigger is None


class TestHookRegistry:
    """Tests for HookRegistry."""

    def test_register_hook(self):
        registry = HookRegistry()
        hook = LoggingHook()
        registry.register(hook)
        assert len(registry.get_hooks()) == 1

    def test_unregister_hook(self):
        registry = HookRegistry()
        hook = LoggingHook()
        registry.register(hook)
        assert registry.unregister(hook) is True
        assert len(registry.get_hooks()) == 0

    def test_hook_priority_ordering(self):
        registry = HookRegistry()
        metrics = MetricsHook()
        logging = LoggingHook()
        registry.register(metrics)
        registry.register(logging)
        hooks = registry.get_hooks()
        assert hooks[0].priority < hooks[1].priority

    def test_before_execution(self):
        registry = HookRegistry()
        registry.register(LoggingHook())
        context = JobExecutionContext(
            job_id="test",
            job_name="test",
            scheduled_time=datetime.now(),
            actual_start_time=datetime.now(),
        )
        assert registry.before_execution(context) is True

    def test_after_execution(self):
        registry = HookRegistry()
        metrics = MetricsHook()
        registry.register(metrics)

        context = JobExecutionContext(
            job_id="test",
            job_name="test",
            scheduled_time=datetime.now(),
            actual_start_time=datetime.now(),
        )
        result = JobExecutionResult(
            job_id="test",
            success=True,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=0.1,
        )
        registry.before_execution(context)
        registry.after_execution(context, result)
        assert metrics.get_metrics("test")["success_count"] == 1


class TestMetricsHook:
    """Tests for MetricsHook."""

    def test_collect_metrics(self):
        hook = MetricsHook()
        context = JobExecutionContext(
            job_id="test",
            job_name="test",
            scheduled_time=datetime.now(),
            actual_start_time=datetime.now(),
        )
        hook.before_job_execution(context)

        result = JobExecutionResult(
            job_id="test",
            success=True,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=0.5,
        )
        hook.after_job_execution(context, result)

        metrics = hook.get_metrics("test")
        assert metrics["execution_count"] == 1
        assert metrics["success_count"] == 1

    def test_failure_tracking(self):
        hook = MetricsHook()
        context = JobExecutionContext(
            job_id="test",
            job_name="test",
            scheduled_time=datetime.now(),
            actual_start_time=datetime.now(),
        )
        hook.before_job_execution(context)

        result = JobExecutionResult(
            job_id="test",
            success=False,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=0.1,
            error_message="Test error",
        )
        hook.after_job_execution(context, result)

        metrics = hook.get_metrics("test")
        assert metrics["failure_count"] == 1

    def test_history_tracking(self):
        hook = MetricsHook(max_history=10)
        context = JobExecutionContext(
            job_id="test",
            job_name="test",
            scheduled_time=datetime.now(),
            actual_start_time=datetime.now(),
        )

        for _ in range(15):
            hook.before_job_execution(context)
            result = JobExecutionResult(
                job_id="test",
                success=True,
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration=0.1,
            )
            hook.after_job_execution(context, result)

        history = hook.get_history("test")
        assert len(history) == 10


class TestJobHealthMonitor:
    """Tests for JobHealthMonitor."""

    def test_record_execution(self):
        monitor = JobHealthMonitor()
        monitor.record_execution_start("test")
        monitor.record_execution_end("test", success=True, duration=0.5)

        health = monitor.get_job_health("test")
        assert health is not None
        assert health.total_runs == 1
        assert health.consecutive_failures == 0

    def test_failure_tracking(self):
        monitor = JobHealthMonitor()
        for _ in range(3):
            monitor.record_execution_start("test")
            monitor.record_execution_end("test", success=False, duration=0.1)

        health = monitor.get_job_health("test")
        assert health.consecutive_failures == 3
        assert health.total_failures == 3

    def test_success_resets_failures(self):
        monitor = JobHealthMonitor()
        monitor.record_execution_end("test", success=False, duration=0.1)
        monitor.record_execution_end("test", success=False, duration=0.1)
        monitor.record_execution_end("test", success=True, duration=0.1)

        health = monitor.get_job_health("test")
        assert health.consecutive_failures == 0

    def test_get_scheduler_metrics(self):
        monitor = JobHealthMonitor()
        monitor.record_execution_end("job1", success=True, duration=0.1)
        monitor.record_execution_end("job2", success=False, duration=0.1)

        metrics = monitor.get_scheduler_metrics()
        assert metrics.total_executions == 2
        assert metrics.total_failures == 1

    def test_overall_status(self):
        config = SchedulerHealthConfig(failure_threshold=2)
        monitor = JobHealthMonitor(config=config)

        status = monitor.get_overall_status()
        assert status == HealthStatus.UNKNOWN

        monitor.record_execution_end("test", success=True, duration=0.1)
        monitor._check_all_jobs = lambda: None
        # Would need scheduler to test properly


class TestExecutionHistoryTracker:
    """Tests for ExecutionHistoryTracker."""

    def test_record_and_get_history(self):
        tracker = ExecutionHistoryTracker()
        tracker.record("job1", success=True, duration=0.5)
        tracker.record("job1", success=False, duration=0.1, error="Test error")

        history = tracker.get_history("job1")
        assert len(history) == 2

    def test_max_history_limit(self):
        tracker = ExecutionHistoryTracker(max_history_per_job=5)
        for _ in range(10):
            tracker.record("job1", success=True, duration=0.1)

        history = tracker.get_history("job1")
        assert len(history) == 5

    def test_get_recent_failures(self):
        tracker = ExecutionHistoryTracker()
        tracker.record("job1", success=True, duration=0.1)
        tracker.record("job2", success=False, duration=0.1, error="Error 1")
        tracker.record("job3", success=False, duration=0.1, error="Error 2")

        failures = tracker.get_recent_failures(hours=24)
        assert len(failures) == 2

    def test_clear(self):
        tracker = ExecutionHistoryTracker()
        tracker.record("job1", success=True, duration=0.1)
        tracker.clear("job1")
        assert len(tracker.get_history("job1")) == 0


class TestExecutionHistoryStore:
    """Tests for ExecutionHistoryStore (SQLite)."""

    @pytest.fixture
    def store_with_path(self, tmp_path):
        """Create a store with a temporary database."""
        db_path = tmp_path / "test.db"
        store = ExecutionHistoryStore(db_path)
        yield store
        # Close connection to avoid Windows file locking issues
        if hasattr(store._local, "connection"):
            store._local.connection.close()

    def test_record_and_get_executions(self, store_with_path):
        store = store_with_path
        store.record_execution("job1", success=True, duration=0.5)
        store.record_execution("job1", success=False, duration=0.1, error="Test")

        executions = store.get_executions("job1")
        assert len(executions) == 2

    def test_get_statistics(self, store_with_path):
        store = store_with_path
        store.record_execution("job1", success=True, duration=1.0)
        store.record_execution("job1", success=True, duration=2.0)
        store.record_execution("job1", success=False, duration=0.5)

        stats = store.get_statistics("job1")
        assert stats["total_runs"] == 3
        assert stats["success_rate"] == pytest.approx(66.67, rel=0.1)

    def test_cleanup_old_records(self, store_with_path):
        store = store_with_path
        store.record_execution("job1", success=True, duration=0.5)
        deleted = store.cleanup_old_records(days=0)
        assert deleted >= 0


class TestTaskSchedulerEnhanced:
    """Tests for enhanced TaskScheduler functionality."""

    @pytest.fixture
    def scheduler(self):
        config = SchedulerConfig(enabled=True, job_store_type="memory")
        scheduler = TaskScheduler(config)
        yield scheduler
        if scheduler.is_running:
            scheduler.shutdown(wait=False)

    def test_is_running_property(self, scheduler):
        assert scheduler.is_running is False
        scheduler.start()
        assert scheduler.is_running is True
        scheduler.shutdown()
        assert scheduler.is_running is False

    def test_get_scheduler_status(self, scheduler):
        status = scheduler.get_scheduler_status()
        assert "status" in status
        assert status["running"] is False

        scheduler.start()
        status = scheduler.get_scheduler_status()
        assert status["running"] is True

    def test_add_and_get_job_info(self, scheduler):
        scheduler.start()

        def test_func():
            pass

        job_id = scheduler.add_job(test_func, trigger="interval", minutes=5, job_id="test_job")
        info = scheduler.get_job_info(job_id)

        assert info is not None
        assert info["id"] == job_id

    def test_get_next_run_times(self, scheduler):
        scheduler.start()

        def test_func():
            pass

        scheduler.add_job(test_func, trigger="interval", seconds=60, job_id="job1")
        scheduler.add_job(test_func, trigger="interval", seconds=30, job_id="job2")

        upcoming = scheduler.get_next_run_times(limit=5)
        assert len(upcoming) >= 2

    def test_pause_and_resume_all_jobs(self, scheduler):
        scheduler.start()

        def test_func():
            pass

        scheduler.add_job(test_func, trigger="interval", minutes=5, job_id="job1")
        scheduler.add_job(test_func, trigger="interval", minutes=10, job_id="job2")

        paused = scheduler.pause_all_jobs()
        assert paused == 2

        resumed = scheduler.resume_all_jobs()
        assert resumed == 2

    def test_remove_all_jobs(self, scheduler):
        scheduler.start()

        def test_func():
            pass

        scheduler.add_job(test_func, trigger="interval", minutes=5, job_id="job1")
        scheduler.add_job(test_func, trigger="interval", minutes=10, job_id="job2")

        removed = scheduler.remove_all_jobs()
        assert removed == 2
        assert len(scheduler.get_jobs()) == 0

    def test_export_jobs(self, scheduler):
        scheduler.start()

        def test_func():
            pass

        scheduler.add_job(test_func, trigger="interval", minutes=5, job_id="test_job")

        exported = scheduler.export_jobs()
        assert len(exported) == 1
        assert exported[0]["id"] == "test_job"

    def test_get_job_statistics(self, scheduler):
        scheduler.start()

        def test_func():
            pass

        scheduler.add_job(test_func, trigger="interval", minutes=5, job_id="job1")
        scheduler.add_job(test_func, trigger="cron", hour="9", job_id="job2")

        stats = scheduler.get_job_statistics()
        assert stats["total_jobs"] == 2
        assert "trigger_types" in stats

    def test_reschedule_job(self, scheduler):
        scheduler.start()

        def test_func():
            pass

        scheduler.add_job(test_func, trigger="interval", minutes=5, job_id="test_job")
        success = scheduler.reschedule_job("test_job", trigger="interval", minutes=10)
        assert success is True

    def test_run_job_now(self, scheduler):
        scheduler.start()
        called = []

        def test_func():
            called.append(True)

        scheduler.add_job(test_func, trigger="interval", hours=24, job_id="test_job")
        success = scheduler.run_job_now("test_job")

        assert success is True
        assert len(called) == 1


class TestSchedulerIntegration:
    """Tests for integrated hooks, monitors, and stores in TaskScheduler."""

    @pytest.fixture
    def scheduler_with_history(self, tmp_path):
        """Scheduler with history store enabled."""
        config = SchedulerConfig(
            enabled=True,
            job_store_type="memory",
            health_check_enabled=True,
            history_enabled=True,
            history_path=str(tmp_path / "history.db"),
        )
        scheduler = TaskScheduler(config)
        yield scheduler
        if scheduler.is_running:
            scheduler.shutdown(wait=False)

    def test_hook_registry_property(self):
        config = SchedulerConfig(enabled=True)
        scheduler = TaskScheduler(config)
        assert scheduler.hook_registry is not None
        assert len(scheduler.hook_registry.get_hooks()) >= 2  # logging + metrics

    def test_health_monitor_property(self):
        config = SchedulerConfig(enabled=True, health_check_enabled=True)
        scheduler = TaskScheduler(config)
        assert scheduler.health_monitor is not None

    def test_health_monitor_disabled(self):
        config = SchedulerConfig(enabled=True, health_check_enabled=False)
        scheduler = TaskScheduler(config)
        assert scheduler.health_monitor is None

    def test_history_store_property(self, tmp_path):
        config = SchedulerConfig(
            enabled=True,
            history_enabled=True,
            history_path=str(tmp_path / "test.db"),
        )
        scheduler = TaskScheduler(config)
        assert scheduler.history_store is not None

    def test_get_health_status(self):
        config = SchedulerConfig(enabled=True, health_check_enabled=True)
        scheduler = TaskScheduler(config)
        status = scheduler.get_health_status()
        assert status["enabled"] is True
        assert "overall_status" in status
        assert "metrics" in status

    def test_get_health_status_disabled(self):
        config = SchedulerConfig(enabled=True, health_check_enabled=False)
        scheduler = TaskScheduler(config)
        status = scheduler.get_health_status()
        assert status["enabled"] is False

    def test_get_job_health(self):
        config = SchedulerConfig(enabled=True, health_check_enabled=True)
        scheduler = TaskScheduler(config)
        # Record some executions using the correct method name
        scheduler._health_monitor.record_execution_end("test_job", success=True, duration=0.5)
        health = scheduler.get_job_health("test_job")
        assert health is not None
        assert health["job_id"] == "test_job"
        assert health["total_runs"] == 1

    def test_get_execution_history(self, scheduler_with_history):
        scheduler = scheduler_with_history
        # Record some executions
        scheduler._history_store.record_execution("job1", success=True, duration=0.5)
        scheduler._history_store.record_execution("job1", success=False, duration=0.1, error="Test")

        history = scheduler.get_execution_history("job1")
        assert len(history) == 2
        assert history[0]["job_id"] == "job1"

    def test_get_execution_statistics(self, scheduler_with_history):
        scheduler = scheduler_with_history
        scheduler._history_store.record_execution("job1", success=True, duration=1.0)
        scheduler._history_store.record_execution("job1", success=True, duration=2.0)

        stats = scheduler.get_execution_statistics("job1")
        assert stats["total_runs"] == 2

    def test_cleanup_history(self, scheduler_with_history):
        scheduler = scheduler_with_history
        scheduler._history_store.record_execution("job1", success=True, duration=0.5)
        deleted = scheduler.cleanup_history(days=0)
        assert deleted >= 0

    def test_get_job_run_count(self):
        config = SchedulerConfig(enabled=True)
        scheduler = TaskScheduler(config)
        assert scheduler.get_job_run_count("nonexistent") == 0
        scheduler._job_run_counts["test_job"] = 5
        assert scheduler.get_job_run_count("test_job") == 5


class TestLoggingHook:
    """Tests for LoggingHook."""

    def test_before_execution_returns_true(self):
        hook = LoggingHook()
        context = JobExecutionContext(
            job_id="test",
            job_name="test",
            scheduled_time=datetime.now(),
            actual_start_time=datetime.now(),
        )
        assert hook.before_job_execution(context) is True

    def test_after_execution_success(self):
        hook = LoggingHook()
        context = JobExecutionContext(
            job_id="test",
            job_name="test",
            scheduled_time=datetime.now(),
            actual_start_time=datetime.now(),
        )
        result = JobExecutionResult(
            job_id="test",
            success=True,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=0.5,
        )
        # Should not raise
        hook.after_job_execution(context, result)

    def test_on_job_error_returns_false(self):
        hook = LoggingHook()
        context = JobExecutionContext(
            job_id="test",
            job_name="test",
            scheduled_time=datetime.now(),
            actual_start_time=datetime.now(),
        )
        assert hook.on_job_error(context, Exception("test")) is False


class TestAlertHook:
    """Tests for AlertHook."""

    def test_alert_on_consecutive_failures(self):
        alerts = []

        def alert_callback(level, message, data):
            alerts.append((level, message, data))

        hook = AlertHook(alert_callback=alert_callback, failure_threshold=2)
        context = JobExecutionContext(
            job_id="test",
            job_name="test",
            scheduled_time=datetime.now(),
            actual_start_time=datetime.now(),
        )

        # First failure - no alert
        result = JobExecutionResult(
            job_id="test",
            success=False,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=0.1,
        )
        hook.after_job_execution(context, result)
        assert len(alerts) == 0

        # Second failure - should trigger alert
        hook.after_job_execution(context, result)
        assert len(alerts) == 1
        assert "Job Failure" in alerts[0][0]  # First arg is message title

    def test_success_resets_failure_count(self):
        alerts = []

        def alert_callback(level, message, data):
            alerts.append((level, message, data))

        hook = AlertHook(alert_callback=alert_callback, failure_threshold=2)
        context = JobExecutionContext(
            job_id="test",
            job_name="test",
            scheduled_time=datetime.now(),
            actual_start_time=datetime.now(),
        )

        # One failure
        fail_result = JobExecutionResult(
            job_id="test",
            success=False,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=0.1,
        )
        hook.after_job_execution(context, fail_result)

        # Success resets counter
        success_result = JobExecutionResult(
            job_id="test",
            success=True,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=0.1,
        )
        hook.after_job_execution(context, success_result)

        # Another failure - counter should be reset, no alert
        hook.after_job_execution(context, fail_result)
        assert len(alerts) == 0


class TestHookRegistryExtended:
    """Extended tests for HookRegistry."""

    def test_clear(self):
        registry = HookRegistry()
        registry.register(LoggingHook())
        registry.register(MetricsHook())
        assert len(registry.get_hooks()) == 2

        registry.clear()
        assert len(registry.get_hooks()) == 0

    def test_create_default_registry(self):
        registry = create_default_hook_registry()
        hooks = registry.get_hooks()
        assert len(hooks) >= 2
        hook_types = [type(h).__name__ for h in hooks]
        assert "LoggingHook" in hook_types
        assert "MetricsHook" in hook_types


class TestJobStoreFactory:
    """Tests for JobStoreFactory."""

    def test_create_memory_store(self):
        store = JobStoreFactory.create("memory")
        assert store is not None

    def test_create_sqlite_without_path_raises(self):
        with pytest.raises(ValueError, match="store_path required"):
            JobStoreFactory.create("sqlite")

    def test_create_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown store type"):
            JobStoreFactory.create("unknown")


class TestExecutionHistoryStoreExtended:
    """Extended tests for ExecutionHistoryStore."""

    @pytest.fixture
    def store(self, tmp_path):
        db_path = tmp_path / "test.db"
        store = ExecutionHistoryStore(db_path)
        yield store
        if hasattr(store._local, "connection"):
            store._local.connection.close()

    def test_get_all_statistics(self, store):
        store.record_execution("job1", success=True, duration=1.0)
        store.record_execution("job2", success=True, duration=2.0)
        store.record_execution("job2", success=False, duration=0.5)

        all_stats = store.get_all_statistics()
        assert len(all_stats) == 2
        # job2 has more runs, should be first
        assert all_stats[0]["job_id"] == "job2"
        assert all_stats[0]["total_runs"] == 2


class TestJobHealthMonitorExtended:
    """Extended tests for JobHealthMonitor."""

    def test_get_all_health(self):
        monitor = JobHealthMonitor()
        monitor.record_execution_end("job1", success=True, duration=0.1)
        monitor.record_execution_end("job2", success=False, duration=0.1)

        all_health = monitor.get_all_health()
        assert len(all_health) == 2
        assert "job1" in all_health
        assert "job2" in all_health

    def test_get_unhealthy_jobs(self):
        config = SchedulerHealthConfig(failure_threshold=1)
        monitor = JobHealthMonitor(config=config)

        monitor.record_execution_end("healthy_job", success=True, duration=0.1)
        monitor.record_execution_end("unhealthy_job", success=False, duration=0.1)

        # Manually set statuses - healthy job is HEALTHY, unhealthy is WARNING
        healthy = monitor.get_job_health("healthy_job")
        healthy.status = HealthStatus.HEALTHY
        unhealthy_info = monitor.get_job_health("unhealthy_job")
        unhealthy_info.status = HealthStatus.WARNING

        unhealthy = monitor.get_unhealthy_jobs()
        assert len(unhealthy) == 1
        assert unhealthy[0].job_id == "unhealthy_job"


class TestSchedulerConfigIntegration:
    """Tests for SchedulerConfig integration with TaskScheduler."""

    def test_config_with_custom_workers(self):
        config = SchedulerConfig(
            enabled=True, max_workers=5, job_coalesce=False, max_instances=3, misfire_grace_time=120
        )
        scheduler = TaskScheduler(config)
        assert scheduler.config.max_workers == 5
        assert scheduler.config.job_coalesce is False
        assert scheduler.config.max_instances == 3

    def test_config_hooks_disabled(self):
        config = SchedulerConfig(
            enabled=True, logging_hook_enabled=False, metrics_hook_enabled=False
        )
        scheduler = TaskScheduler(config)
        # Should have no hooks registered
        assert len(scheduler.hook_registry.get_hooks()) == 0

    def test_history_store_not_created_without_path(self):
        config = SchedulerConfig(
            enabled=True,
            history_enabled=True,
            history_path=None,  # No path
        )
        scheduler = TaskScheduler(config)
        assert scheduler.history_store is None


class TestTaskSchedulerGracefulShutdown:
    """Tests for graceful shutdown functionality."""

    def test_graceful_shutdown_not_running(self):
        config = SchedulerConfig(enabled=True)
        scheduler = TaskScheduler(config)
        # Should return True immediately if not running
        result = scheduler.graceful_shutdown(timeout=1.0)
        assert result is True

    def test_graceful_shutdown_with_jobs(self):
        config = SchedulerConfig(enabled=True, job_store_type="memory")
        scheduler = TaskScheduler(config)
        scheduler.start()

        def test_func():
            pass

        scheduler.add_job(test_func, trigger="interval", hours=24, job_id="test")

        result = scheduler.graceful_shutdown(timeout=2.0)
        assert result is True
        assert scheduler.is_running is False


class TestJobDecorator:
    """Tests for @job decorator."""

    def test_job_decorator_marks_function(self):
        @job(trigger="interval", minutes=5)
        def my_task():
            pass

        assert hasattr(my_task, "_scheduler_job")
        assert my_task._scheduler_job is True
        assert my_task._trigger_type == "interval"
        assert my_task._trigger_args == {"minutes": 5}

    def test_job_decorator_preserves_function(self):
        @job(trigger="cron", hour="9")
        def my_task():
            return "result"

        assert my_task() == "result"

    def test_job_decorator_cron_trigger(self):
        @job(trigger="cron", hour="9", minute="30")
        def cron_task():
            pass

        assert cron_task._trigger_type == "cron"
        assert cron_task._trigger_args == {"hour": "9", "minute": "30"}
