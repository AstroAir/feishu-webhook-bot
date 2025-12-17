"""Tests for task manager."""

import time
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from feishu_webhook_bot.core.config import (
    BotConfig,
    TaskActionConfig,
    TaskDefinitionConfig,
)
from feishu_webhook_bot.tasks.manager import TaskManager
from tests.mocks import MockScheduler


@pytest.fixture
def mock_config():
    """Create a mock bot configuration with tasks."""
    return BotConfig(
        webhooks=[
            {"name": "default", "url": "https://example.com/webhook"},
        ],
        tasks=[
            {
                "name": "task1",
                "enabled": True,
                "schedule": {"mode": "interval", "arguments": {"minutes": 5}},
                "actions": [{"type": "send_message", "webhook": "default", "message": "Task 1"}],
            },
            {
                "name": "task2",
                "enabled": True,
                "cron": "0 9 * * *",
                "actions": [{"type": "send_message", "webhook": "default", "message": "Task 2"}],
            },
            {
                "name": "task3",
                "enabled": False,
                "schedule": {"mode": "interval", "arguments": {"hours": 1}},
                "actions": [{"type": "send_message", "webhook": "default", "message": "Task 3"}],
            },
        ],
    )


@pytest.fixture
def mock_scheduler():
    """Create a mock scheduler."""
    return MockScheduler()


@pytest.fixture
def mock_plugin_manager():
    """Create a mock plugin manager."""
    return MagicMock()


@pytest.fixture
def mock_clients():
    """Create mock webhook clients."""
    return {"default": MagicMock()}


@pytest.fixture
def task_manager(mock_config, mock_scheduler, mock_plugin_manager, mock_clients):
    """Create a task manager instance."""
    return TaskManager(
        config=mock_config,
        scheduler=mock_scheduler,
        plugin_manager=mock_plugin_manager,
        clients=mock_clients,
    )


class TestTaskRegistration:
    """Test task registration with scheduler."""

    def test_start_registers_enabled_tasks(self, task_manager, mock_scheduler):
        """Test that start() registers all enabled tasks."""
        task_manager.start()

        # Should register task1 and task2 (enabled), but not task3 (disabled)
        assert len(mock_scheduler.jobs) == 2
        assert "task.task1" in mock_scheduler.jobs
        assert "task.task2" in mock_scheduler.jobs
        assert "task.task3" not in mock_scheduler.jobs

    def test_stop_unregisters_all_tasks(self, task_manager, mock_scheduler):
        """Test that stop() unregisters all tasks."""
        task_manager.start()
        assert len(mock_scheduler.jobs) == 2

        task_manager.stop()
        assert len(mock_scheduler.jobs) == 0

    def test_register_task_with_interval_schedule(self, task_manager, mock_scheduler):
        """Test registering a task with interval schedule."""
        task_manager.start()

        job = mock_scheduler.get_job("task.task1")
        assert job is not None
        assert job.trigger == "interval"
        assert job.kwargs.get("minutes") == 5

    def test_register_task_with_cron_schedule(self, task_manager, mock_scheduler):
        """Test registering a task with cron schedule."""
        task_manager.start()

        job = mock_scheduler.get_job("task.task2")
        assert job is not None
        assert job.trigger == "cron"


class TestTaskExecution:
    """Test task execution."""

    def test_execute_task_now(self, task_manager, mock_clients):
        """Test manual task execution."""
        result = task_manager.execute_task_now("task1")

        assert result is not None
        assert result["task_name"] == "task1"
        # Should have attempted to send message
        mock_clients["default"].send_text.assert_called()

    def test_execute_nonexistent_task(self, task_manager):
        """Test executing a task that doesn't exist."""
        import pytest

        with pytest.raises(ValueError, match="Task not found: nonexistent"):
            task_manager.execute_task_now("nonexistent")

    def test_execute_disabled_task(self, task_manager):
        """Test executing a disabled task."""
        result = task_manager.execute_task_now("task3")

        # Should still execute when called manually
        assert result is not None
        assert result["task_name"] == "task3"

    def test_concurrent_execution_limit(self, task_manager):
        """Test concurrent execution limits."""
        # Create a task that takes time to execute
        config = BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
            tasks=[
                {
                    "name": "slow_task",
                    "enabled": True,
                    "max_concurrent": 1,
                    "schedule": {"mode": "interval", "arguments": {"seconds": 1}},
                    "actions": [{"type": "python_code", "code": "time.sleep(0.5)"}],
                }
            ],
        )

        manager = TaskManager(
            config=config,
            scheduler=MockScheduler(),
            plugin_manager=MagicMock(),
            clients={"default": MagicMock()},
        )

        # Execute task twice concurrently
        import threading

        results = []

        def execute():
            result = manager.execute_task_now("slow_task")
            results.append(result)

        thread1 = threading.Thread(target=execute)
        thread2 = threading.Thread(target=execute)

        thread1.start()
        time.sleep(0.1)  # Small delay to ensure first task starts
        thread2.start()

        thread1.join()
        thread2.join()

        # One should succeed, one should be skipped due to concurrent limit
        assert len(results) == 2
        success_count = sum(1 for r in results if r and r.get("success"))
        # At least one should succeed
        assert success_count >= 1

    def test_execute_task_not_found_logs_error(self, task_manager, caplog):
        """Task execution logs an error when task is missing."""
        with caplog.at_level("ERROR", logger="task.manager"):
            task_manager._execute_task("missing")

        assert any("Task not found: missing" in record.message for record in caplog.records)

    def test_execute_task_respects_concurrency_limit(self, task_manager, monkeypatch):
        """Concurrent executions beyond task limit are skipped."""
        task_manager.start()
        task = task_manager.config.get_task("task1")
        assert task is not None

        task_manager._execution_counts[task.name] = task.max_concurrent

        constructed = 0

        def fake_executor(*args, **kwargs):
            nonlocal constructed
            constructed += 1
            raise AssertionError("Executor should not be constructed when limit reached")

        monkeypatch.setattr("feishu_webhook_bot.tasks.manager.TaskExecutor", fake_executor)
        task_manager._execute_task("task1")

        assert constructed == 0

    def test_execute_task_failure_triggers_retry(self, monkeypatch):
        """Failures should schedule a retry when enabled."""
        config = BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
            tasks=[
                {
                    "name": "retry_task",
                    "enabled": True,
                    "interval": {"minutes": 5},
                    "actions": [{"type": "python_code", "code": "context['value'] = 1"}],
                }
            ],
        )
        scheduler = MockScheduler()
        manager = TaskManager(
            config=config,
            scheduler=scheduler,
            plugin_manager=MagicMock(),
            clients={"default": MagicMock()},
        )
        manager.start()

        failure_result = {
            "task_name": "retry_task",
            "success": False,
            "actions_executed": 0,
            "actions_failed": 1,
            "duration": 0.0,
            "start_time": 0.0,
            "end_time": 0.0,
            "error": "boom",
        }

        class DummyExecutor:
            def __init__(self, **_):
                pass

            def execute(self):
                return failure_result

        monkeypatch.setattr("feishu_webhook_bot.tasks.manager.TaskExecutor", DummyExecutor)

        scheduled: list[tuple[str, dict[str, object]]] = []

        def fake_schedule_retry(task_cfg, result):
            scheduled.append((task_cfg.name, result))

        monkeypatch.setattr(manager, "_schedule_retry", fake_schedule_retry)

        manager._execute_task("retry_task")

        assert scheduled and scheduled[0][0] == "retry_task"


class TestTaskDependencies:
    """Test task dependencies."""

    def test_task_with_depends_on(self):
        """Test task with depends_on dependency."""
        config = BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
            tasks=[
                {
                    "name": "task_a",
                    "enabled": True,
                    "schedule": {"mode": "interval", "arguments": {"minutes": 5}},
                    "actions": [{"type": "send_message", "webhook": "default", "message": "A"}],
                },
                {
                    "name": "task_b",
                    "enabled": True,
                    "depends_on": ["task_a"],
                    "schedule": {"mode": "interval", "arguments": {"minutes": 5}},
                    "actions": [{"type": "send_message", "webhook": "default", "message": "B"}],
                },
            ],
        )

        manager = TaskManager(
            config=config,
            scheduler=MockScheduler(),
            plugin_manager=MagicMock(),
            clients={"default": MagicMock()},
        )

        # Task B should not execute if Task A hasn't run
        # This is a simplified test - full dependency resolution would need more complex setup
        assert manager.config.get_task("task_b").depends_on == ["task_a"]

    def test_task_with_run_after(self):
        """Test task with run_after dependency."""
        config = BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
            tasks=[
                {
                    "name": "task_x",
                    "enabled": True,
                    "schedule": {"mode": "interval", "arguments": {"minutes": 5}},
                    "actions": [{"type": "send_message", "webhook": "default", "message": "X"}],
                },
                {
                    "name": "task_y",
                    "enabled": True,
                    "run_after": ["task_x"],
                    "schedule": {"mode": "interval", "arguments": {"minutes": 5}},
                    "actions": [{"type": "send_message", "webhook": "default", "message": "Y"}],
                },
            ],
        )

        manager = TaskManager(
            config=config,
            scheduler=MockScheduler(),
            plugin_manager=MagicMock(),
            clients={"default": MagicMock()},
        )

        assert manager.config.get_task("task_y").run_after == ["task_x"]


class TestTaskStatus:
    """Test task status reporting."""

    def test_get_task_status(self, task_manager):
        """Test getting task status."""
        task_manager.start()

        status = task_manager.get_task_status("task1")

        assert status is not None
        assert status["name"] == "task1"
        assert status["enabled"] is True
        assert "registered" in status

    def test_get_status_for_nonexistent_task(self, task_manager):
        """Test getting status for a task that doesn't exist."""
        status = task_manager.get_task_status("nonexistent")

        assert status == {"error": "Task not found"}

    def test_list_tasks(self, task_manager):
        """Test listing all tasks."""
        task_manager.start()

        tasks = task_manager.list_tasks()

        assert len(tasks) >= 2  # At least task1 and task2
        task_names = [t["name"] for t in tasks]
        assert "task1" in task_names
        assert "task2" in task_names

    def test_list_tasks_without_start(self, task_manager):
        """No tasks registered before start is invoked."""
        assert task_manager.list_tasks() == []

    def test_get_task_status_includes_next_run(self, task_manager):
        """Status output contains next run timestamp when available."""
        task_manager.start()
        job = task_manager.scheduler.get_job("task.task1")
        assert job is not None
        job.next_run_time = datetime(2024, 1, 1, 12, 0)

        status = task_manager.get_task_status("task1")
        assert status["next_run"] == "2024-01-01 12:00:00"


class TestTaskReload:
    """Test task reloading."""

    def test_reload_tasks(self, task_manager, mock_scheduler):
        """Test reloading tasks from configuration."""
        task_manager.start()
        initial_job_count = len(mock_scheduler.jobs)

        # Modify config to add a new task
        new_task = TaskDefinitionConfig(
            name="new_task",
            enabled=True,
            schedule={"mode": "interval", "arguments": {"minutes": 10}},
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="New task",
                )
            ],
        )
        task_manager.config.tasks.append(new_task)

        # Reload tasks
        task_manager.reload_tasks()

        # Should have one more job
        assert len(mock_scheduler.jobs) == initial_job_count + 1
        assert "task.new_task" in mock_scheduler.jobs


class TestTaskManagerUtilities:
    """Additional coverage for manager helpers."""

    def test_start_without_scheduler_logs_warning(self, mock_plugin_manager, mock_clients, caplog):
        config = BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
            tasks=[
                {
                    "name": "orphan_task",
                    "enabled": True,
                    "interval": {"minutes": 5},
                    "actions": [{"type": "send_message", "webhooks": ["default"], "message": "hi"}],
                }
            ],
        )

        manager = TaskManager(
            config=config,
            scheduler=None,
            plugin_manager=mock_plugin_manager,
            clients=mock_clients,
        )

        with caplog.at_level("WARNING", logger="task.manager"):
            manager.start()

        assert any("Scheduler not available" in record.message for record in caplog.records)

    def test_build_context_includes_environment(self):
        config = BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
            active_environment="prod",
            environments=[
                {
                    "name": "prod",
                    "enabled": True,
                    "variables": [
                        {"name": "API_KEY", "value": "secret"},
                    ],
                }
            ],
            tasks=[
                {
                    "name": "ctx_task",
                    "enabled": True,
                    "interval": {"minutes": 5},
                    "context": {"base": "value"},
                    "parameters": [
                        {"name": "limit", "default": 10},
                    ],
                    "actions": [
                        {"type": "python_code", "code": "pass"},
                    ],
                }
            ],
        )

        manager = TaskManager(
            config=config,
            scheduler=MockScheduler(),
            plugin_manager=MagicMock(),
            clients={"default": MagicMock()},
        )

        task = manager.config.tasks[0]
        context = manager._build_context(task)

        assert context["API_KEY"] == "secret"
        assert context["environment"] == "prod"
        assert context["limit"] == 10
        assert context["base"] == "value"

    def test_schedule_retry_logs_message(self, task_manager, caplog):
        task = task_manager.config.get_task("task1")
        assert task is not None

        with caplog.at_level("INFO", logger="task.manager"):
            task_manager._schedule_retry(task, {"error": "boom"})

        # Retry logic is now implemented with exponential backoff
        assert any("Scheduling retry" in record.message for record in caplog.records)
