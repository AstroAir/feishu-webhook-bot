"""Task planner for multi-agent orchestration.

This module provides task planning capabilities including:
- Task decomposition into subtasks
- Execution plan generation
- Dependency management
- Plan optimization
"""

from __future__ import annotations

from typing import Any

from pydantic_ai import Agent

from ...core.logger import get_logger
from .base import (
    ExecutionPlan,
    Task,
    TaskStatus,
    TaskType,
)
from .router import TaskAnalyzer

logger = get_logger("ai.multi_agent.planner")


class TaskPlanner:
    """Plans and decomposes complex tasks into executable steps.

    The planner can:
    - Analyze task complexity
    - Decompose tasks into subtasks
    - Create execution plans
    - Optimize task ordering
    - Manage dependencies

    Example:
        ```python
        planner = TaskPlanner(model="openai:gpt-4o")
        plan = await planner.create_plan(task)
        for step in plan.steps:
            result = await execute_step(step)
        ```
    """

    def __init__(
        self,
        model: str = "openai:gpt-4o",
        max_subtasks: int = 5,
        auto_decompose_threshold: int = 7,
    ) -> None:
        """Initialize the task planner.

        Args:
            model: AI model for planning
            max_subtasks: Maximum number of subtasks per decomposition
            auto_decompose_threshold: Complexity threshold for auto-decomposition
        """
        self.model = model
        self.max_subtasks = max_subtasks
        self.auto_decompose_threshold = auto_decompose_threshold

        # Task analyzer for complexity assessment
        self._analyzer = TaskAnalyzer()

        # Planning agent
        self._planning_agent = Agent(
            model=model,
            output_type=str,
            system_prompt=(
                "You are a task planning specialist. Your role is to analyze complex tasks "
                "and break them down into clear, actionable subtasks. "
                "For each task, identify:\n"
                "1. The main objective\n"
                "2. Required subtasks (max 5)\n"
                "3. Dependencies between subtasks\n"
                "4. Optimal execution order\n\n"
                "Format your response as a numbered list of subtasks, "
                "each on its own line with a brief description."
            ),
        )

        # Metrics
        self._metrics = {
            "plans_created": 0,
            "tasks_decomposed": 0,
            "total_subtasks": 0,
        }

        logger.info(
            "TaskPlanner initialized (model: %s, max_subtasks: %d)",
            model,
            max_subtasks,
        )

    async def create_plan(
        self,
        task: Task,
        force_decompose: bool = False,
    ) -> ExecutionPlan:
        """Create an execution plan for a task.

        Args:
            task: Task to plan
            force_decompose: Force decomposition even for simple tasks

        Returns:
            ExecutionPlan with steps
        """
        logger.info("Creating plan for task: %s", task.id)

        # Analyze task complexity
        complexity = self._analyzer.analyze_complexity(task.content)
        task_type = self._analyzer.analyze(task.content)

        logger.debug(
            "Task analysis: type=%s, complexity=%d",
            task_type.value,
            complexity,
        )

        # Decide whether to decompose
        should_decompose = force_decompose or complexity >= self.auto_decompose_threshold

        if should_decompose:
            # Decompose into subtasks
            subtasks = await self._decompose_task(task, task_type)
        else:
            # Single-step plan
            subtasks = [task]

        # Create execution plan
        plan = ExecutionPlan(
            original_task=task,
            steps=subtasks,
            status=TaskStatus.PENDING,
        )

        # Update metrics
        self._metrics["plans_created"] += 1
        self._metrics["total_subtasks"] += len(subtasks)

        logger.info(
            "Created plan %s with %d steps",
            plan.id,
            len(plan.steps),
        )

        return plan

    async def _decompose_task(
        self,
        task: Task,
        task_type: TaskType,
    ) -> list[Task]:
        """Decompose a complex task into subtasks.

        Args:
            task: Task to decompose
            task_type: Detected task type

        Returns:
            List of subtasks
        """
        logger.info("Decomposing task: %s", task.id)

        try:
            # Use AI to decompose the task
            prompt = (
                f"Break down this task into {self.max_subtasks} or fewer clear subtasks:\n\n"
                f"Task: {task.content}\n\n"
                "List each subtask on a new line, numbered 1-5."
            )

            result = await self._planning_agent.run(prompt)
            subtask_descriptions = self._parse_subtasks(result.output)

            # Create subtask objects
            subtasks = []
            for i, description in enumerate(subtask_descriptions):
                subtask = Task(
                    content=description,
                    task_type=self._infer_subtask_type(description, task_type),
                    priority=task.priority,
                    status=TaskStatus.PENDING,
                    parent_task_id=task.id,
                    context={"parent_content": task.content, "step": i + 1},
                )
                subtasks.append(subtask)
                task.subtask_ids.append(subtask.id)

            self._metrics["tasks_decomposed"] += 1

            logger.info(
                "Decomposed task %s into %d subtasks",
                task.id,
                len(subtasks),
            )

            return subtasks if subtasks else [task]

        except Exception as exc:
            logger.error(
                "Failed to decompose task %s: %s",
                task.id,
                exc,
                exc_info=True,
            )
            # Return original task as single step
            return [task]

    def _parse_subtasks(self, output: str) -> list[str]:
        """Parse subtask descriptions from AI output.

        Args:
            output: AI output text

        Returns:
            List of subtask descriptions
        """
        subtasks = []
        lines = output.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Remove numbering (1., 1), 1:, etc.)
            import re

            cleaned = re.sub(r"^[\d]+[.\):\-]\s*", "", line)
            if cleaned and len(cleaned) > 5:
                subtasks.append(cleaned)

            if len(subtasks) >= self.max_subtasks:
                break

        return subtasks

    def _infer_subtask_type(
        self,
        description: str,
        parent_type: TaskType,
    ) -> TaskType:
        """Infer the type of a subtask.

        Args:
            description: Subtask description
            parent_type: Parent task type

        Returns:
            Inferred task type
        """
        # Use analyzer for subtask
        inferred = self._analyzer.analyze(description)

        # If analyzer returns general, use parent type
        if inferred == TaskType.GENERAL or inferred == TaskType.CONVERSATION:
            return parent_type

        return inferred

    async def optimize_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Optimize an execution plan.

        This method can:
        - Reorder steps for efficiency
        - Identify parallelizable steps
        - Remove redundant steps

        Args:
            plan: Plan to optimize

        Returns:
            Optimized plan
        """
        logger.info("Optimizing plan: %s", plan.id)

        # For now, simple optimization based on task type
        # Group similar tasks together
        steps_by_type: dict[TaskType, list[Task]] = {}
        for step in plan.steps:
            if step.task_type not in steps_by_type:
                steps_by_type[step.task_type] = []
            steps_by_type[step.task_type].append(step)

        # Reorder: search first, then analysis, then response
        priority_order = [
            TaskType.SEARCH,
            TaskType.ANALYSIS,
            TaskType.REASONING,
            TaskType.CODE,
            TaskType.SUMMARY,
            TaskType.CONVERSATION,
        ]

        optimized_steps = []
        for task_type in priority_order:
            if task_type in steps_by_type:
                optimized_steps.extend(steps_by_type.pop(task_type))

        # Add remaining steps
        for steps in steps_by_type.values():
            optimized_steps.extend(steps)

        plan.steps = optimized_steps

        logger.info("Plan optimized: %s", plan.id)
        return plan

    def estimate_cost(self, plan: ExecutionPlan) -> dict[str, float]:
        """Estimate the cost of executing a plan.

        Args:
            plan: Plan to estimate

        Returns:
            Cost estimates
        """
        # Rough estimates based on step count and complexity
        base_cost_per_step = 0.01  # $0.01 per step
        complexity_multiplier = 1.5

        total_steps = len(plan.steps)
        avg_complexity = sum(
            self._analyzer.analyze_complexity(step.content) for step in plan.steps
        ) / max(total_steps, 1)

        estimated_cost = (
            total_steps * base_cost_per_step * (1 + (avg_complexity / 10) * complexity_multiplier)
        )

        return {
            "estimated_cost_usd": round(estimated_cost, 4),
            "total_steps": total_steps,
            "avg_complexity": round(avg_complexity, 2),
        }

    def estimate_time(self, plan: ExecutionPlan) -> dict[str, float]:
        """Estimate the time to execute a plan.

        Args:
            plan: Plan to estimate

        Returns:
            Time estimates in seconds
        """
        # Rough estimates
        base_time_per_step = 2.0  # 2 seconds per step
        complexity_multiplier = 0.5

        total_steps = len(plan.steps)
        avg_complexity = sum(
            self._analyzer.analyze_complexity(step.content) for step in plan.steps
        ) / max(total_steps, 1)

        estimated_time = (
            total_steps * base_time_per_step * (1 + (avg_complexity / 10) * complexity_multiplier)
        )

        return {
            "estimated_time_seconds": round(estimated_time, 2),
            "total_steps": total_steps,
            "avg_complexity": round(avg_complexity, 2),
        }

    def get_stats(self) -> dict[str, Any]:
        """Get planner statistics.

        Returns:
            Dictionary with planner stats
        """
        return {
            "model": self.model,
            "max_subtasks": self.max_subtasks,
            "auto_decompose_threshold": self.auto_decompose_threshold,
            "plans_created": self._metrics["plans_created"],
            "tasks_decomposed": self._metrics["tasks_decomposed"],
            "total_subtasks": self._metrics["total_subtasks"],
            "avg_subtasks_per_decomposition": (
                self._metrics["total_subtasks"] / self._metrics["tasks_decomposed"]
                if self._metrics["tasks_decomposed"] > 0
                else 0
            ),
        }


class DependencyResolver:
    """Resolves dependencies between tasks in an execution plan.

    This class helps identify:
    - Which tasks can run in parallel
    - Which tasks must run sequentially
    - Optimal execution order
    """

    def __init__(self) -> None:
        """Initialize the dependency resolver."""
        self._dependency_graph: dict[str, list[str]] = {}
        logger.info("DependencyResolver initialized")

    def add_dependency(self, task_id: str, depends_on: str) -> None:
        """Add a dependency between tasks.

        Args:
            task_id: Task that has the dependency
            depends_on: Task that must complete first
        """
        if task_id not in self._dependency_graph:
            self._dependency_graph[task_id] = []
        self._dependency_graph[task_id].append(depends_on)

    def get_dependencies(self, task_id: str) -> list[str]:
        """Get dependencies for a task.

        Args:
            task_id: Task ID

        Returns:
            List of task IDs that must complete first
        """
        return self._dependency_graph.get(task_id, [])

    def get_execution_order(self, tasks: list[Task]) -> list[list[Task]]:
        """Get optimal execution order with parallelization.

        Args:
            tasks: List of tasks

        Returns:
            List of task groups (tasks in same group can run in parallel)
        """
        # Build task map
        task_map = {task.id: task for task in tasks}

        # Find tasks with no dependencies (can start immediately)
        remaining = set(task.id for task in tasks)
        completed: set[str] = set()
        execution_groups: list[list[Task]] = []

        while remaining:
            # Find tasks that can run now
            ready = []
            for task_id in remaining:
                deps = self.get_dependencies(task_id)
                if all(dep in completed for dep in deps):
                    ready.append(task_id)

            if not ready:
                # No tasks ready - break cycle by taking first remaining
                ready = [next(iter(remaining))]

            # Add ready tasks as a parallel group
            group = [task_map[tid] for tid in ready if tid in task_map]
            if group:
                execution_groups.append(group)

            # Mark as completed
            for task_id in ready:
                remaining.discard(task_id)
                completed.add(task_id)

        return execution_groups

    def can_parallelize(self, task1: Task, task2: Task) -> bool:
        """Check if two tasks can run in parallel.

        Args:
            task1: First task
            task2: Second task

        Returns:
            True if tasks can run in parallel
        """
        # Check if either depends on the other
        deps1 = self.get_dependencies(task1.id)
        deps2 = self.get_dependencies(task2.id)

        return task2.id not in deps1 and task1.id not in deps2

    def clear(self) -> None:
        """Clear all dependencies."""
        self._dependency_graph.clear()
