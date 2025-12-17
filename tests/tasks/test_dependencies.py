"""Tests for task dependency execution functionality."""

from unittest.mock import MagicMock, patch

import pytest

from feishu_webhook_bot.core.config import BotConfig
from feishu_webhook_bot.tasks.manager import TaskExecutionStatus, TaskManager
from tests.mocks import MockScheduler


@pytest.fixture
def mock_config_with_dependencies():
    """Create a config with tasks that have dependencies."""
    return BotConfig(
        webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
        tasks=[
            {
                "name": "task_a",
                "enabled": True,
                "interval": {"minutes": 5},
                "actions": [{"type": "python_code", "code": "context['a_result'] = 'done'"}],
            },
            {
                "name": "task_b",
                "enabled": True,
                "depends_on": ["task_a"],
                "interval": {"minutes": 5},
                "actions": [{"type": "python_code", "code": "context['b_result'] = 'done'"}],
            },
            {
                "name": "task_c",
                "enabled": True,
                "run_after": ["task_a"],
                "interval": {"minutes": 5},
                "actions": [{"type": "python_code", "code": "context['c_result'] = 'done'"}],
            },
            {
                "name": "task_d",
                "enabled": True,
                "depends_on": ["task_b", "task_c"],
                "interval": {"minutes": 5},
                "actions": [{"type": "python_code", "code": "context['d_result'] = 'done'"}],
            },
        ],
    )


@pytest.fixture
def task_manager_with_deps(mock_config_with_dependencies):
    """Create a task manager with dependency-enabled tasks."""
    manager = TaskManager(
        config=mock_config_with_dependencies,
        scheduler=MockScheduler(),
        plugin_manager=MagicMock(),
        clients={"default": MagicMock()},
    )
    manager.start()
    return manager


class TestDependencyChecking:
    """Test dependency checking logic."""

    def test_check_dependencies_no_deps(self, task_manager_with_deps):
        """Task without dependencies should always pass check."""
        task = task_manager_with_deps._task_instances["task_a"]
        can_execute, reason = task_manager_with_deps._check_dependencies(task)
        assert can_execute is True
        assert "satisfied" in reason.lower()

    def test_check_dependencies_pending_dep(self, task_manager_with_deps):
        """Task with pending dependency should not execute."""
        task = task_manager_with_deps._task_instances["task_b"]
        # task_a is in PENDING state by default
        can_execute, reason = task_manager_with_deps._check_dependencies(task)
        assert can_execute is False
        assert "task_a" in reason

    def test_check_dependencies_success_dep(self, task_manager_with_deps):
        """Task with successful dependency should execute."""
        # Mark task_a as successful
        task_manager_with_deps._task_status["task_a"] = TaskExecutionStatus.SUCCESS

        task = task_manager_with_deps._task_instances["task_b"]
        can_execute, reason = task_manager_with_deps._check_dependencies(task)
        assert can_execute is True

    def test_check_dependencies_failed_dep_skip(self, task_manager_with_deps):
        """Task with failed dependency should be skipped by default."""
        # Mark task_a as failed
        task_manager_with_deps._task_status["task_a"] = TaskExecutionStatus.FAILED

        task = task_manager_with_deps._task_instances["task_b"]
        can_execute, reason = task_manager_with_deps._check_dependencies(task)
        assert can_execute is False
        assert "failed" in reason.lower()

    def test_check_dependencies_run_after_completed(self, task_manager_with_deps):
        """run_after dependency only requires completion, not success."""
        # Mark task_a as failed (but completed)
        task_manager_with_deps._task_status["task_a"] = TaskExecutionStatus.FAILED

        task = task_manager_with_deps._task_instances["task_c"]
        can_execute, reason = task_manager_with_deps._check_dependencies(task)
        # run_after doesn't require success
        assert can_execute is True

    def test_check_dependencies_multiple_deps(self, task_manager_with_deps):
        """Task with multiple dependencies requires all to be satisfied."""
        # Only task_b is successful
        task_manager_with_deps._task_status["task_a"] = TaskExecutionStatus.SUCCESS
        task_manager_with_deps._task_status["task_b"] = TaskExecutionStatus.SUCCESS
        task_manager_with_deps._task_status["task_c"] = TaskExecutionStatus.PENDING

        task = task_manager_with_deps._task_instances["task_d"]
        can_execute, reason = task_manager_with_deps._check_dependencies(task)
        assert can_execute is False
        assert "task_c" in reason

    def test_check_dependencies_all_satisfied(self, task_manager_with_deps):
        """Task executes when all dependencies are satisfied."""
        task_manager_with_deps._task_status["task_a"] = TaskExecutionStatus.SUCCESS
        task_manager_with_deps._task_status["task_b"] = TaskExecutionStatus.SUCCESS
        task_manager_with_deps._task_status["task_c"] = TaskExecutionStatus.SUCCESS

        task = task_manager_with_deps._task_instances["task_d"]
        can_execute, reason = task_manager_with_deps._check_dependencies(task)
        assert can_execute is True


class TestDependencyExecution:
    """Test task execution with dependencies."""

    def test_execute_task_skips_unmet_deps(self, task_manager_with_deps):
        """Task execution is skipped when dependencies are not met."""
        # task_b depends on task_a which is PENDING
        task_manager_with_deps._execute_task("task_b")

        # task_b should be marked as SKIPPED
        assert task_manager_with_deps._task_status["task_b"] == TaskExecutionStatus.SKIPPED

    def test_execute_task_runs_with_met_deps(self, task_manager_with_deps):
        """Task executes when dependencies are met."""
        # Mark task_a as successful
        task_manager_with_deps._task_status["task_a"] = TaskExecutionStatus.SUCCESS
        task_manager_with_deps._last_execution_result["task_a"] = {"success": True}

        # Execute task_b
        task_manager_with_deps._execute_task("task_b")

        # task_b should have run
        status = task_manager_with_deps._task_status["task_b"]
        assert status in (TaskExecutionStatus.SUCCESS, TaskExecutionStatus.FAILED)

    def test_dependency_results_in_context(self, task_manager_with_deps):
        """Dependency results are available in task context."""
        # Mark task_a as successful with result
        task_manager_with_deps._task_status["task_a"] = TaskExecutionStatus.SUCCESS
        task_manager_with_deps._last_execution_result["task_a"] = {
            "success": True,
            "output": "task_a_output",
        }

        # Capture the context passed to executor
        captured_context = {}

        def capture_executor(*args, **kwargs):
            captured_context.update(kwargs.get("context", {}))
            mock = MagicMock()
            mock.execute.return_value = {"success": True, "duration": 0.1}
            return mock

        with patch("feishu_webhook_bot.tasks.manager.TaskExecutor", capture_executor):
            task_manager_with_deps._execute_task("task_b")

        assert "dependency_results" in captured_context
        assert "task_a" in captured_context["dependency_results"]


class TestTaskStatusManagement:
    """Test task status management methods."""

    def test_get_task_dependency_status(self, task_manager_with_deps):
        """get_task_dependency_status returns correct information."""
        task_manager_with_deps._task_status["task_a"] = TaskExecutionStatus.SUCCESS

        status = task_manager_with_deps.get_task_dependency_status("task_b")

        assert status["task_name"] == "task_b"
        assert "task_a" in status["dependencies"]
        assert status["dependencies"]["task_a"]["status"] == "success"
        assert status["dependencies"]["task_a"]["required"] is True

    def test_reset_task_status(self, task_manager_with_deps):
        """reset_task_status resets status to PENDING."""
        task_manager_with_deps._task_status["task_a"] = TaskExecutionStatus.SUCCESS
        task_manager_with_deps._last_execution_result["task_a"] = {"success": True}

        result = task_manager_with_deps.reset_task_status("task_a")

        assert result is True
        assert task_manager_with_deps._task_status["task_a"] == TaskExecutionStatus.PENDING
        assert "task_a" not in task_manager_with_deps._last_execution_result

    def test_reset_all_task_statuses(self, task_manager_with_deps):
        """reset_all_task_statuses resets all tasks."""
        task_manager_with_deps._task_status["task_a"] = TaskExecutionStatus.SUCCESS
        task_manager_with_deps._task_status["task_b"] = TaskExecutionStatus.FAILED

        task_manager_with_deps.reset_all_task_statuses()

        for status in task_manager_with_deps._task_status.values():
            assert status == TaskExecutionStatus.PENDING

    def test_get_all_task_statuses(self, task_manager_with_deps):
        """get_all_task_statuses returns all statuses."""
        task_manager_with_deps._task_status["task_a"] = TaskExecutionStatus.SUCCESS
        task_manager_with_deps._task_status["task_b"] = TaskExecutionStatus.RUNNING

        statuses = task_manager_with_deps.get_all_task_statuses()

        assert statuses["task_a"] == "success"
        assert statuses["task_b"] == "running"
