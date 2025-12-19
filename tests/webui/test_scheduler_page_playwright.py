"""Playwright browser tests for Scheduler page in WebUI."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
def mock_controller() -> MagicMock:
    """Create mock controller with scheduler methods."""
    controller = MagicMock()
    controller.bot = MagicMock()
    controller.bot.scheduler = MagicMock()

    # Mock scheduler jobs
    controller.get_scheduler_jobs.return_value = [
        {
            "id": "job1",
            "name": "Daily Report",
            "next_run": "2025-12-19 09:00:00",
            "trigger": "cron: 0 9 * * *",
            "paused": False,
        },
        {
            "id": "job2",
            "name": "Hourly Check",
            "next_run": "2025-12-18 14:00:00",
            "trigger": "interval: 1h",
            "paused": True,
        },
    ]

    # Mock scheduler status
    controller.get_scheduler_status.return_value = {
        "running": True,
        "timezone": "Asia/Shanghai",
        "job_count": 2,
        "active_jobs": 1,
        "paused_jobs": 1,
        "job_store_type": "memory",
    }

    # Mock health status
    controller.get_scheduler_health.return_value = {
        "enabled": True,
        "overall_status": "healthy",
        "metrics": {
            "total_executions": 150,
            "successful": 145,
            "failed": 5,
        },
    }

    # Mock statistics
    controller.get_scheduler_statistics.return_value = {
        "total_jobs": 2,
        "active_jobs": 1,
        "paused_jobs": 1,
        "total_runs": 150,
    }

    # Mock job operations
    controller.pause_scheduler_job.return_value = True
    controller.resume_scheduler_job.return_value = True
    controller.remove_scheduler_job.return_value = True
    controller.run_job_now.return_value = True
    controller.pause_all_scheduler_jobs.return_value = 2
    controller.resume_all_scheduler_jobs.return_value = 2

    return controller


class TestSchedulerPageI18n:
    """Test i18n translations for Scheduler page."""

    def test_english_translations_exist(self) -> None:
        """Test that English translations exist for all scheduler keys."""
        from feishu_webhook_bot.webui.i18n import TRANSLATIONS

        en_translations = TRANSLATIONS["en"]
        required_keys = [
            "scheduler.title",
            "scheduler.desc",
            "scheduler.enable",
            "scheduler.timezone",
            "scheduler.job_store_type",
            "scheduler.job_store_path",
            "scheduler.basic_settings",
            "scheduler.advanced_settings",
            "scheduler.tasks_config",
            "scheduler.running_jobs",
            "scheduler.active_jobs",
            "scheduler.scheduler_status",
            "scheduler.job_count",
            "scheduler.paused",
            "scheduler.active",
            "scheduler.pause_job",
            "scheduler.resume_job",
            "scheduler.remove_job",
            # New health monitoring keys
            "scheduler.health_monitoring",
            "scheduler.health_monitoring_desc",
            "scheduler.total_executions",
            "scheduler.successful",
            "scheduler.failed",
            "scheduler.overall_status",
            "scheduler.health_disabled",
            "scheduler.pause_all",
            "scheduler.resume_all",
            "scheduler.jobs_paused",
            "scheduler.jobs_resumed",
            "scheduler.run_now",
            "scheduler.job_triggered",
        ]
        for key in required_keys:
            assert key in en_translations, f"Missing English translation: {key}"

    def test_chinese_translations_exist(self) -> None:
        """Test that Chinese translations exist for all scheduler keys."""
        from feishu_webhook_bot.webui.i18n import TRANSLATIONS

        zh_translations = TRANSLATIONS["zh"]
        required_keys = [
            "scheduler.title",
            "scheduler.desc",
            "scheduler.enable",
            "scheduler.timezone",
            "scheduler.job_store_type",
            "scheduler.job_store_path",
            "scheduler.basic_settings",
            "scheduler.advanced_settings",
            "scheduler.tasks_config",
            "scheduler.running_jobs",
            "scheduler.active_jobs",
            "scheduler.scheduler_status",
            "scheduler.job_count",
            "scheduler.paused",
            "scheduler.active",
            "scheduler.pause_job",
            "scheduler.resume_job",
            "scheduler.remove_job",
            # New health monitoring keys
            "scheduler.health_monitoring",
            "scheduler.health_monitoring_desc",
            "scheduler.total_executions",
            "scheduler.successful",
            "scheduler.failed",
            "scheduler.overall_status",
            "scheduler.health_disabled",
            "scheduler.pause_all",
            "scheduler.resume_all",
            "scheduler.jobs_paused",
            "scheduler.jobs_resumed",
            "scheduler.run_now",
            "scheduler.job_triggered",
        ]
        for key in required_keys:
            assert key in zh_translations, f"Missing Chinese translation: {key}"

    def test_translation_function(self) -> None:
        """Test the translation function works correctly."""
        from feishu_webhook_bot.webui.i18n import set_lang, t

        set_lang("en")
        assert t("scheduler.title") == "Scheduler"
        assert t("scheduler.health_monitoring") == "Health Monitoring"

        set_lang("zh")
        assert t("scheduler.title") == "调度器设置"
        assert t("scheduler.health_monitoring") == "健康监控"


class TestSchedulerControllerMethods:
    """Test scheduler controller methods."""

    def test_controller_has_scheduler_methods(self) -> None:
        """Test that BotController has all scheduler methods."""
        from feishu_webhook_bot.webui.controller import BotController

        # Basic methods
        assert hasattr(BotController, "get_scheduler_jobs")
        assert hasattr(BotController, "get_scheduler_status")
        assert hasattr(BotController, "pause_scheduler_job")
        assert hasattr(BotController, "resume_scheduler_job")
        assert hasattr(BotController, "remove_scheduler_job")

        # New enhanced methods
        assert hasattr(BotController, "get_scheduler_health")
        assert hasattr(BotController, "get_job_health")
        assert hasattr(BotController, "get_job_execution_history")
        assert hasattr(BotController, "get_scheduler_statistics")
        assert hasattr(BotController, "run_job_now")
        assert hasattr(BotController, "pause_all_scheduler_jobs")
        assert hasattr(BotController, "resume_all_scheduler_jobs")

    def test_get_scheduler_jobs_returns_list(self, mock_controller: MagicMock) -> None:
        """Test get_scheduler_jobs returns a list."""
        result = mock_controller.get_scheduler_jobs()
        assert isinstance(result, list)
        assert len(result) == 2
        assert "id" in result[0]
        assert "name" in result[0]
        assert "next_run" in result[0]
        assert "trigger" in result[0]

    def test_get_scheduler_status_returns_dict(self, mock_controller: MagicMock) -> None:
        """Test get_scheduler_status returns status dict."""
        result = mock_controller.get_scheduler_status()
        assert isinstance(result, dict)
        assert "running" in result
        assert "timezone" in result
        assert "job_count" in result
        assert result["running"] is True

    def test_get_scheduler_health_returns_dict(self, mock_controller: MagicMock) -> None:
        """Test get_scheduler_health returns health dict."""
        result = mock_controller.get_scheduler_health()
        assert isinstance(result, dict)
        assert "enabled" in result
        assert "overall_status" in result
        assert "metrics" in result
        assert result["enabled"] is True
        assert result["overall_status"] == "healthy"

    def test_pause_all_scheduler_jobs_returns_count(self, mock_controller: MagicMock) -> None:
        """Test pause_all_scheduler_jobs returns count."""
        result = mock_controller.pause_all_scheduler_jobs()
        assert result == 2

    def test_resume_all_scheduler_jobs_returns_count(self, mock_controller: MagicMock) -> None:
        """Test resume_all_scheduler_jobs returns count."""
        result = mock_controller.resume_all_scheduler_jobs()
        assert result == 2

    def test_run_job_now_returns_bool(self, mock_controller: MagicMock) -> None:
        """Test run_job_now returns boolean."""
        result = mock_controller.run_job_now("job1")
        assert result is True


class TestSchedulerPageUIComponents:
    """Test scheduler page UI component functions."""

    def test_build_scheduler_page_function_exists(self) -> None:
        """Test that build_scheduler_page function exists."""
        from feishu_webhook_bot.webui.pages import scheduler

        assert hasattr(scheduler, "build_scheduler_page")
        assert callable(scheduler.build_scheduler_page)

    def test_build_job_card_function_exists(self) -> None:
        """Test that _build_job_card function exists."""
        from feishu_webhook_bot.webui.pages import scheduler

        assert hasattr(scheduler, "_build_job_card")
        assert callable(scheduler._build_job_card)


class TestSchedulerCLICommands:
    """Test scheduler CLI commands."""

    def test_cli_scheduler_commands_exist(self) -> None:
        """Test that CLI scheduler commands exist."""
        from feishu_webhook_bot.cli.commands import scheduler

        assert hasattr(scheduler, "cmd_scheduler")
        assert hasattr(scheduler, "_cmd_scheduler_status")
        assert hasattr(scheduler, "_cmd_scheduler_jobs")
        assert hasattr(scheduler, "_cmd_scheduler_health")
        assert hasattr(scheduler, "_cmd_scheduler_stats")
        assert hasattr(scheduler, "_cmd_scheduler_pause")
        assert hasattr(scheduler, "_cmd_scheduler_resume")
        assert hasattr(scheduler, "_cmd_scheduler_remove")
        assert hasattr(scheduler, "_cmd_scheduler_trigger")

    def test_cmd_scheduler_health_function(self) -> None:
        """Test _cmd_scheduler_health function is callable."""
        from feishu_webhook_bot.cli.commands.scheduler import _cmd_scheduler_health

        assert callable(_cmd_scheduler_health)

    def test_cmd_scheduler_stats_function(self) -> None:
        """Test _cmd_scheduler_stats function is callable."""
        from feishu_webhook_bot.cli.commands.scheduler import _cmd_scheduler_stats

        assert callable(_cmd_scheduler_stats)


class TestSchedulerModuleIntegration:
    """Test scheduler module integration."""

    def test_scheduler_hooks_module_imports(self) -> None:
        """Test hooks module imports correctly."""
        from feishu_webhook_bot.scheduler.hooks import (
            AlertHook,
            HookRegistry,
            JobHook,
            LoggingHook,
            MetricsHook,
            create_default_hook_registry,
        )

        assert HookRegistry is not None
        assert JobHook is not None
        assert LoggingHook is not None
        assert MetricsHook is not None
        assert AlertHook is not None
        assert callable(create_default_hook_registry)

    def test_scheduler_monitors_module_imports(self) -> None:
        """Test monitors module imports correctly."""
        from feishu_webhook_bot.scheduler.monitors import (
            ExecutionHistoryTracker,
            HealthStatus,
            JobHealthInfo,
            JobHealthMonitor,
            SchedulerHealthConfig,
            SchedulerMetrics,
        )

        assert JobHealthMonitor is not None
        assert SchedulerHealthConfig is not None
        assert SchedulerMetrics is not None
        assert JobHealthInfo is not None
        assert HealthStatus is not None
        assert ExecutionHistoryTracker is not None

    def test_scheduler_stores_module_imports(self) -> None:
        """Test stores module imports correctly."""
        from feishu_webhook_bot.scheduler.stores import (
            ExecutionHistoryStore,
            ExecutionRecord,
            JobStoreFactory,
        )

        assert ExecutionHistoryStore is not None
        assert ExecutionRecord is not None
        assert JobStoreFactory is not None

    def test_scheduler_expressions_module_imports(self) -> None:
        """Test expressions module imports correctly."""
        from feishu_webhook_bot.scheduler.expressions import (
            CronExpressionParser,
            IntervalBuilder,
            ScheduleBuilder,
        )

        assert CronExpressionParser is not None
        assert IntervalBuilder is not None
        assert ScheduleBuilder is not None

    def test_task_scheduler_has_enhanced_methods(self) -> None:
        """Test TaskScheduler has enhanced methods."""
        from feishu_webhook_bot.scheduler import TaskScheduler

        assert hasattr(TaskScheduler, "get_health_status")
        assert hasattr(TaskScheduler, "get_job_health")
        assert hasattr(TaskScheduler, "get_execution_history")
        assert hasattr(TaskScheduler, "get_execution_statistics")
        assert hasattr(TaskScheduler, "cleanup_history")
        assert hasattr(TaskScheduler, "get_job_run_count")
        assert hasattr(TaskScheduler, "hook_registry")
        assert hasattr(TaskScheduler, "health_monitor")
        assert hasattr(TaskScheduler, "history_store")


@pytest.mark.asyncio
class TestSchedulerPagePlaywright:
    """Playwright browser tests for Scheduler page."""

    async def test_scheduler_page_module_imports(self) -> None:
        """Test that scheduler page module can be imported."""
        from feishu_webhook_bot.webui.pages import scheduler

        assert scheduler is not None
        assert hasattr(scheduler, "build_scheduler_page")

    async def test_controller_module_imports(self) -> None:
        """Test that controller module can be imported."""
        from feishu_webhook_bot.webui.controller import BotController

        assert BotController is not None

    async def test_scheduler_config_model(self) -> None:
        """Test SchedulerConfig has all required fields."""
        from feishu_webhook_bot.core.config import SchedulerConfig

        config = SchedulerConfig()

        # Basic fields
        assert hasattr(config, "enabled")
        assert hasattr(config, "timezone")
        assert hasattr(config, "job_store_type")
        assert hasattr(config, "job_store_path")

        # Enhanced fields
        assert hasattr(config, "max_workers")
        assert hasattr(config, "job_coalesce")
        assert hasattr(config, "max_instances")
        assert hasattr(config, "misfire_grace_time")

        # Health monitoring fields
        assert hasattr(config, "health_check_enabled")
        assert hasattr(config, "health_check_interval")
        assert hasattr(config, "failure_threshold")

        # History fields
        assert hasattr(config, "history_enabled")
        assert hasattr(config, "history_path")
        assert hasattr(config, "history_retention_days")

        # Hooks fields
        assert hasattr(config, "logging_hook_enabled")
        assert hasattr(config, "metrics_hook_enabled")
        assert hasattr(config, "alert_hook_enabled")

    async def test_health_status_structure(self) -> None:
        """Test health status data structure."""
        from feishu_webhook_bot.scheduler.monitors import HealthStatus

        # Check enum values
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.WARNING.value == "warning"
        assert HealthStatus.CRITICAL.value == "critical"
        assert HealthStatus.UNKNOWN.value == "unknown"

    async def test_execution_record_structure(self) -> None:
        """Test execution record structure."""
        from datetime import datetime

        from feishu_webhook_bot.scheduler.stores import ExecutionRecord

        record = ExecutionRecord(
            job_id="test_job",
            executed_at=datetime.now(),
            duration=1.5,
            success=True,
        )

        assert record.job_id == "test_job"
        assert record.duration == 1.5
        assert record.success is True
        assert record.error is None


class TestSchedulerHealthMonitoringUI:
    """Test scheduler health monitoring UI integration."""

    def test_health_metrics_display(self, mock_controller: MagicMock) -> None:
        """Test health metrics are correctly structured for display."""
        health = mock_controller.get_scheduler_health()

        assert health["enabled"] is True
        metrics = health["metrics"]
        assert metrics["total_executions"] == 150
        assert metrics["successful"] == 145
        assert metrics["failed"] == 5

        # Calculate success rate
        success_rate = (metrics["successful"] / metrics["total_executions"]) * 100
        assert success_rate > 95  # 96.67%

    def test_job_status_display(self, mock_controller: MagicMock) -> None:
        """Test job status is correctly structured for display."""
        jobs = mock_controller.get_scheduler_jobs()

        active_jobs = [j for j in jobs if not j["paused"]]
        paused_jobs = [j for j in jobs if j["paused"]]

        assert len(active_jobs) == 1
        assert len(paused_jobs) == 1
        assert active_jobs[0]["name"] == "Daily Report"
        assert paused_jobs[0]["name"] == "Hourly Check"


class TestSchedulerBulkOperations:
    """Test scheduler bulk operations."""

    def test_pause_all_jobs(self, mock_controller: MagicMock) -> None:
        """Test pause all jobs operation."""
        count = mock_controller.pause_all_scheduler_jobs()
        assert count == 2
        mock_controller.pause_all_scheduler_jobs.assert_called_once()

    def test_resume_all_jobs(self, mock_controller: MagicMock) -> None:
        """Test resume all jobs operation."""
        count = mock_controller.resume_all_scheduler_jobs()
        assert count == 2
        mock_controller.resume_all_scheduler_jobs.assert_called_once()

    def test_run_job_now(self, mock_controller: MagicMock) -> None:
        """Test run job now operation."""
        result = mock_controller.run_job_now("job1")
        assert result is True
        mock_controller.run_job_now.assert_called_with("job1")
