"""Tests for TaskPlanner and DependencyResolver.

Tests cover:
- TaskPlanner initialization and configuration
- Task decomposition and plan creation
- Cost and time estimation
- Plan optimization
- DependencyResolver for task dependencies
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from feishu_webhook_bot.ai.multi_agent.base import (
    ExecutionPlan,
    Task,
    TaskType,
)
from feishu_webhook_bot.ai.multi_agent.planner import DependencyResolver, TaskPlanner

PLANNER_AGENT_MOCK_PATH = "feishu_webhook_bot.ai.multi_agent.planner.Agent"


# ==============================================================================
# TaskPlanner Basic Tests
# ==============================================================================


class TestTaskPlannerBasic:
    """Basic tests for TaskPlanner."""

    @patch(PLANNER_AGENT_MOCK_PATH)
    def test_planner_initialization(self, mock_agent):
        """Test TaskPlanner initialization."""
        planner = TaskPlanner()

        assert planner.model == "openai:gpt-4o"
        assert planner.max_subtasks == 5
        assert planner.auto_decompose_threshold == 7

    @patch(PLANNER_AGENT_MOCK_PATH)
    def test_planner_custom_settings(self, mock_agent):
        """Test TaskPlanner with custom settings."""
        planner = TaskPlanner(
            model="anthropic:claude-3-5-sonnet-20241022",
            max_subtasks=3,
            auto_decompose_threshold=5,
        )

        assert planner.model == "anthropic:claude-3-5-sonnet-20241022"
        assert planner.max_subtasks == 3
        assert planner.auto_decompose_threshold == 5

    @patch(PLANNER_AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_create_plan_simple_task(self, mock_agent):
        """Test creating plan for simple task."""
        mock_result = MagicMock()
        mock_result.output = "1. Simple step"
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent.return_value = mock_agent_instance

        planner = TaskPlanner()
        task = Task(content="Simple task")

        plan = await planner.create_plan(task)

        assert plan is not None
        assert len(plan.steps) >= 1

    @patch(PLANNER_AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_create_plan_complex_task(self, mock_agent):
        """Test creating plan for complex task."""
        mock_result = MagicMock()
        mock_result.output = """1. Research the topic
2. Analyze findings
3. Create outline
4. Write content
5. Review and refine"""
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent.return_value = mock_agent_instance

        planner = TaskPlanner()
        task = Task(
            content="Write a comprehensive research paper on distributed systems "
            "with detailed analysis and implementation recommendations"
        )

        plan = await planner.create_plan(task, force_decompose=True)

        assert plan is not None
        assert len(plan.steps) >= 1

    @patch(PLANNER_AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_create_plan_force_decompose(self, mock_agent):
        """Test force decompose option."""
        mock_result = MagicMock()
        mock_result.output = "1. Step one\n2. Step two"
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent.return_value = mock_agent_instance

        planner = TaskPlanner()
        task = Task(content="Simple task")

        plan = await planner.create_plan(task, force_decompose=True)

        assert plan is not None


# ==============================================================================
# TaskPlanner Estimation Tests
# ==============================================================================


class TestTaskPlannerEstimation:
    """Tests for TaskPlanner estimation methods."""

    @patch(PLANNER_AGENT_MOCK_PATH)
    def test_estimate_cost(self, mock_agent):
        """Test cost estimation."""
        planner = TaskPlanner()
        plan = ExecutionPlan(
            original_task=Task(content="Main"),
            steps=[Task(content="Step 1"), Task(content="Step 2")],
        )

        estimate = planner.estimate_cost(plan)

        assert "estimated_cost_usd" in estimate
        assert "total_steps" in estimate
        assert estimate["total_steps"] == 2

    @patch(PLANNER_AGENT_MOCK_PATH)
    def test_estimate_time(self, mock_agent):
        """Test time estimation."""
        planner = TaskPlanner()
        plan = ExecutionPlan(
            original_task=Task(content="Main"),
            steps=[Task(content="Step 1"), Task(content="Step 2"), Task(content="Step 3")],
        )

        estimate = planner.estimate_time(plan)

        assert "estimated_time_seconds" in estimate
        assert "total_steps" in estimate
        assert estimate["total_steps"] == 3

    @patch(PLANNER_AGENT_MOCK_PATH)
    def test_get_stats(self, mock_agent):
        """Test getting planner statistics."""
        planner = TaskPlanner()

        stats = planner.get_stats()

        assert stats["model"] == "openai:gpt-4o"
        assert stats["max_subtasks"] == 5
        assert stats["plans_created"] == 0


# ==============================================================================
# TaskPlanner Optimization Tests
# ==============================================================================


class TestTaskPlannerOptimization:
    """Tests for plan optimization."""

    @patch(PLANNER_AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_optimize_plan(self, mock_agent):
        """Test plan optimization."""
        planner = TaskPlanner()

        plan = ExecutionPlan(
            original_task=Task(content="Main"),
            steps=[
                Task(content="Summarize", task_type=TaskType.SUMMARY),
                Task(content="Search", task_type=TaskType.SEARCH),
                Task(content="Analyze", task_type=TaskType.ANALYSIS),
            ],
        )

        optimized = await planner.optimize_plan(plan)

        # Should reorder (search first, then analysis, then summary)
        assert optimized.steps[0].task_type == TaskType.SEARCH
        assert optimized.steps[1].task_type == TaskType.ANALYSIS


# ==============================================================================
# DependencyResolver Tests
# ==============================================================================


class TestDependencyResolver:
    """Tests for DependencyResolver."""

    def test_resolver_initialization(self):
        """Test DependencyResolver initialization."""
        resolver = DependencyResolver()

        assert resolver._dependency_graph == {}

    def test_add_dependency(self):
        """Test adding dependency."""
        resolver = DependencyResolver()

        resolver.add_dependency("task2", "task1")

        deps = resolver.get_dependencies("task2")
        assert "task1" in deps

    def test_get_dependencies_empty(self):
        """Test getting dependencies for task with none."""
        resolver = DependencyResolver()

        deps = resolver.get_dependencies("task1")

        assert deps == []

    def test_get_dependencies_multiple(self):
        """Test getting multiple dependencies."""
        resolver = DependencyResolver()

        resolver.add_dependency("task3", "task1")
        resolver.add_dependency("task3", "task2")

        deps = resolver.get_dependencies("task3")

        assert len(deps) == 2
        assert "task1" in deps
        assert "task2" in deps

    def test_can_parallelize_independent(self):
        """Test independent tasks can parallelize."""
        resolver = DependencyResolver()

        task1 = Task(content="Task 1")
        task2 = Task(content="Task 2")

        assert resolver.can_parallelize(task1, task2) is True

    def test_can_parallelize_dependent(self):
        """Test dependent tasks cannot parallelize."""
        resolver = DependencyResolver()

        task1 = Task(content="Task 1")
        task2 = Task(content="Task 2")

        resolver.add_dependency(task2.id, task1.id)

        assert resolver.can_parallelize(task1, task2) is False

    def test_get_execution_order_simple(self):
        """Test execution order for simple tasks."""
        resolver = DependencyResolver()

        tasks = [
            Task(content="Task 1"),
            Task(content="Task 2"),
        ]

        groups = resolver.get_execution_order(tasks)

        assert len(groups) >= 1

    def test_get_execution_order_with_dependencies(self):
        """Test execution order with dependencies."""
        resolver = DependencyResolver()

        task1 = Task(content="Task 1")
        task2 = Task(content="Task 2")
        task3 = Task(content="Task 3")

        # task2 depends on task1, task3 depends on task2
        resolver.add_dependency(task2.id, task1.id)
        resolver.add_dependency(task3.id, task2.id)

        groups = resolver.get_execution_order([task1, task2, task3])

        assert len(groups) >= 1
        # task1 should be in first group
        assert task1.id in [t.id for t in groups[0]]

    def test_clear_dependencies(self):
        """Test clearing all dependencies."""
        resolver = DependencyResolver()

        resolver.add_dependency("task2", "task1")
        resolver.add_dependency("task3", "task2")

        resolver.clear()

        assert resolver.get_dependencies("task2") == []
        assert resolver.get_dependencies("task3") == []
