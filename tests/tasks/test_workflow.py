"""Tests for task chain and workflow execution."""

from unittest.mock import MagicMock

import pytest

from feishu_webhook_bot.core.config import BotConfig
from feishu_webhook_bot.tasks.manager import TaskManager
from tests.mocks import MockScheduler


@pytest.fixture
def mock_config_for_workflow():
    """Create a config with tasks for workflow testing."""
    return BotConfig(
        webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
        tasks=[
            {
                "name": "step_1",
                "enabled": True,
                "interval": {"minutes": 5},
                "actions": [{"type": "python_code", "code": "context['step1'] = 'done'"}],
            },
            {
                "name": "step_2",
                "enabled": True,
                "interval": {"minutes": 5},
                "actions": [{"type": "python_code", "code": "context['step2'] = 'done'"}],
            },
            {
                "name": "step_3",
                "enabled": True,
                "interval": {"minutes": 5},
                "actions": [{"type": "python_code", "code": "context['step3'] = 'done'"}],
            },
            {
                "name": "failing_task",
                "enabled": True,
                "interval": {"minutes": 5},
                "actions": [{"type": "python_code", "code": "raise ValueError('fail')"}],
            },
        ],
    )


@pytest.fixture
def workflow_manager(mock_config_for_workflow):
    """Create a task manager for workflow testing."""
    manager = TaskManager(
        config=mock_config_for_workflow,
        scheduler=MockScheduler(),
        plugin_manager=MagicMock(),
        clients={"default": MagicMock()},
    )
    manager.start()
    return manager


class TestTaskChain:
    """Test task chain execution."""

    def test_run_task_chain_success(self, workflow_manager):
        """Test running a successful task chain."""
        result = workflow_manager.run_task_chain(["step_1", "step_2", "step_3"])

        assert result["success"] is True
        assert len(result["completed"]) == 3
        assert len(result["failed"]) == 0
        assert len(result["skipped"]) == 0

    def test_run_task_chain_stop_on_failure(self, workflow_manager):
        """Test chain stops on failure when stop_on_failure=True."""
        result = workflow_manager.run_task_chain(
            ["step_1", "failing_task", "step_3"],
            stop_on_failure=True,
        )

        assert result["success"] is False
        assert "step_1" in result["completed"]
        assert "failing_task" in result["failed"]
        assert "step_3" in result["skipped"]

    def test_run_task_chain_continue_on_failure(self, workflow_manager):
        """Test chain continues on failure when stop_on_failure=False."""
        result = workflow_manager.run_task_chain(
            ["step_1", "failing_task", "step_3"],
            stop_on_failure=False,
        )

        assert result["success"] is False
        assert "step_1" in result["completed"]
        assert "failing_task" in result["failed"]
        assert "step_3" in result["completed"]
        assert len(result["skipped"]) == 0

    def test_run_task_chain_with_context(self, workflow_manager):
        """Test chain execution with shared context."""
        result = workflow_manager.run_task_chain(
            ["step_1", "step_2"],
            context={"shared_value": "test"},
        )

        assert result["success"] is True
        # Context should be passed to tasks

    def test_run_task_chain_nonexistent_task(self, workflow_manager):
        """Test chain with nonexistent task."""
        result = workflow_manager.run_task_chain(
            ["step_1", "nonexistent", "step_2"],
            stop_on_failure=True,
        )

        assert result["success"] is False
        assert "nonexistent" in result["skipped"]

    def test_run_task_chain_empty(self, workflow_manager):
        """Test running empty chain."""
        result = workflow_manager.run_task_chain([])

        assert result["success"] is True
        assert len(result["completed"]) == 0


class TestParallelTasks:
    """Test parallel task execution."""

    def test_run_parallel_tasks_success(self, workflow_manager):
        """Test running tasks in parallel."""
        result = workflow_manager.run_parallel_tasks(
            ["step_1", "step_2", "step_3"],
            max_workers=3,
        )

        assert len(result["completed"]) == 3
        assert len(result["failed"]) == 0

    def test_run_parallel_tasks_with_failure(self, workflow_manager):
        """Test parallel execution with some failures."""
        result = workflow_manager.run_parallel_tasks(
            ["step_1", "failing_task", "step_2"],
            max_workers=3,
        )

        assert "step_1" in result["completed"]
        assert "step_2" in result["completed"]
        assert "failing_task" in result["failed"]

    def test_run_parallel_tasks_limited_workers(self, workflow_manager):
        """Test parallel execution with limited workers."""
        result = workflow_manager.run_parallel_tasks(
            ["step_1", "step_2", "step_3"],
            max_workers=1,  # Sequential execution
        )

        # All should complete even with 1 worker
        assert len(result["completed"]) == 3


class TestTaskGroups:
    """Test task group management."""

    @pytest.fixture
    def grouped_config(self):
        """Create config with grouped tasks."""
        return BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
            tasks=[
                {
                    "name": "group_a_task_1",
                    "enabled": True,
                    "group": "group_a",
                    "tags": ["important", "daily"],
                    "interval": {"minutes": 5},
                    "actions": [{"type": "python_code", "code": "pass"}],
                },
                {
                    "name": "group_a_task_2",
                    "enabled": True,
                    "group": "group_a",
                    "tags": ["important"],
                    "interval": {"minutes": 5},
                    "actions": [{"type": "python_code", "code": "pass"}],
                },
                {
                    "name": "group_b_task_1",
                    "enabled": True,
                    "group": "group_b",
                    "tags": ["daily"],
                    "interval": {"minutes": 5},
                    "actions": [{"type": "python_code", "code": "pass"}],
                },
                {
                    "name": "ungrouped_task",
                    "enabled": True,
                    "interval": {"minutes": 5},
                    "actions": [{"type": "python_code", "code": "pass"}],
                },
            ],
        )

    @pytest.fixture
    def grouped_manager(self, grouped_config):
        """Create manager with grouped tasks."""
        manager = TaskManager(
            config=grouped_config,
            scheduler=MockScheduler(),
            plugin_manager=MagicMock(),
            clients={"default": MagicMock()},
        )
        manager.start()
        return manager

    def test_get_task_groups(self, grouped_manager):
        """Test getting all task groups."""
        groups = grouped_manager.get_task_groups()

        assert "group_a" in groups
        assert "group_b" in groups
        assert len(groups["group_a"]) == 2
        assert len(groups["group_b"]) == 1

    def test_get_tasks_by_group(self, grouped_manager):
        """Test getting tasks by group name."""
        tasks = grouped_manager.get_tasks_by_group("group_a")

        assert len(tasks) == 2
        task_names = [t.name for t in tasks]
        assert "group_a_task_1" in task_names
        assert "group_a_task_2" in task_names

    def test_get_tasks_by_group_nonexistent(self, grouped_manager):
        """Test getting tasks from nonexistent group."""
        tasks = grouped_manager.get_tasks_by_group("nonexistent")
        assert len(tasks) == 0

    def test_get_tasks_by_tag(self, grouped_manager):
        """Test getting tasks by tag."""
        important_tasks = grouped_manager.get_tasks_by_tag("important")
        daily_tasks = grouped_manager.get_tasks_by_tag("daily")

        assert len(important_tasks) == 2
        assert len(daily_tasks) == 2

    def test_run_group(self, grouped_manager):
        """Test running all tasks in a group."""
        result = grouped_manager.run_group("group_a")

        assert "group_a_task_1" in result
        assert "group_a_task_2" in result
        assert len(result) == 2

    def test_run_group_nonexistent(self, grouped_manager):
        """Test running nonexistent group."""
        result = grouped_manager.run_group("nonexistent")
        assert "error" in result

    def test_enable_group(self, grouped_manager):
        """Test enabling all tasks in a group."""
        # First disable them
        grouped_manager.disable_task("group_a_task_1")
        grouped_manager.disable_task("group_a_task_2")

        result = grouped_manager.enable_group("group_a")

        assert result["group_a_task_1"] is True
        assert result["group_a_task_2"] is True

    def test_disable_group(self, grouped_manager):
        """Test disabling all tasks in a group."""
        result = grouped_manager.disable_group("group_a")

        assert result["group_a_task_1"] is True
        assert result["group_a_task_2"] is True

        # Verify tasks are disabled
        task1 = grouped_manager.get_task("group_a_task_1")
        task2 = grouped_manager.get_task("group_a_task_2")
        assert task1.enabled is False
        assert task2.enabled is False
