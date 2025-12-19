"""Tests for multi-agent base types and models.

Tests cover:
- TaskType, TaskStatus, TaskPriority enums
- AgentMessage model
- AgentResult model
- Task model
- ExecutionPlan model
- ModelInfo model
- BudgetConfig model
- RoutingContext and RoutingDecision models
"""

from __future__ import annotations

from feishu_webhook_bot.ai.multi_agent import (
    AgentMessage,
    AgentResult,
)
from feishu_webhook_bot.ai.multi_agent.base import (
    AgentCapability,
    BudgetConfig,
    BudgetPeriod,
    ExecutionPlan,
    ModelHealth,
    ModelInfo,
    RoutingContext,
    RoutingDecision,
    RoutingStrategy,
    Task,
    TaskPriority,
    TaskStatus,
    TaskType,
)

# ==============================================================================
# TaskType Tests
# ==============================================================================


class TestTaskType:
    """Tests for TaskType enum."""

    def test_all_task_types(self):
        """Test all task type values."""
        assert TaskType.GENERAL.value == "general"
        assert TaskType.SEARCH.value == "search"
        assert TaskType.ANALYSIS.value == "analysis"
        assert TaskType.CODE.value == "code"
        assert TaskType.SUMMARY.value == "summary"
        assert TaskType.TRANSLATION.value == "translation"
        assert TaskType.REASONING.value == "reasoning"
        assert TaskType.PLANNING.value == "planning"
        assert TaskType.CREATIVE.value == "creative"
        assert TaskType.MATH.value == "math"
        assert TaskType.CONVERSATION.value == "conversation"


class TestTaskPriority:
    """Tests for TaskPriority enum."""

    def test_all_priorities(self):
        """Test all priority values."""
        assert TaskPriority.LOW.value == "low"
        assert TaskPriority.MEDIUM.value == "medium"
        assert TaskPriority.HIGH.value == "high"
        assert TaskPriority.CRITICAL.value == "critical"

    def test_priority_comparison(self):
        """Test priority values can be compared."""
        priorities = [
            TaskPriority.LOW,
            TaskPriority.MEDIUM,
            TaskPriority.HIGH,
            TaskPriority.CRITICAL,
        ]
        assert len(priorities) == 4


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_all_statuses(self):
        """Test all status values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"


class TestAgentCapability:
    """Tests for AgentCapability enum."""

    def test_all_capabilities(self):
        """Test all capability values."""
        assert AgentCapability.SEARCH.value == "search"
        assert AgentCapability.ANALYSIS.value == "analysis"
        assert AgentCapability.CODE_GENERATION.value == "code_generation"
        assert AgentCapability.CODE_REVIEW.value == "code_review"
        assert AgentCapability.SUMMARIZATION.value == "summarization"
        assert AgentCapability.TRANSLATION.value == "translation"
        assert AgentCapability.REASONING.value == "reasoning"
        assert AgentCapability.PLANNING.value == "planning"
        assert AgentCapability.CREATIVE_WRITING.value == "creative_writing"
        assert AgentCapability.MATH.value == "math"
        assert AgentCapability.CONVERSATION.value == "conversation"


class TestRoutingStrategy:
    """Tests for RoutingStrategy enum."""

    def test_all_strategies(self):
        """Test all routing strategy values."""
        assert RoutingStrategy.COST_OPTIMIZED.value == "cost_optimized"
        assert RoutingStrategy.SPEED_OPTIMIZED.value == "speed_optimized"
        assert RoutingStrategy.QUALITY_OPTIMIZED.value == "quality_optimized"
        assert RoutingStrategy.BALANCED.value == "balanced"
        assert RoutingStrategy.ROUND_ROBIN.value == "round_robin"
        assert RoutingStrategy.CAPABILITY_BASED.value == "capability_based"


# ==============================================================================
# AgentMessage Tests
# ==============================================================================


class TestAgentMessage:
    """Tests for AgentMessage model."""

    def test_message_creation(self):
        """Test AgentMessage creation with required fields."""
        msg = AgentMessage(
            from_agent="search",
            to_agent="analysis",
            content="Search results here",
        )

        assert msg.from_agent == "search"
        assert msg.to_agent == "analysis"
        assert msg.content == "Search results here"
        assert msg.metadata == {}

    def test_message_with_metadata(self):
        """Test AgentMessage with metadata."""
        msg = AgentMessage(
            from_agent="search",
            to_agent="analysis",
            content="Results",
            metadata={"query": "test", "count": 10},
        )

        assert msg.metadata["query"] == "test"
        assert msg.metadata["count"] == 10

    def test_message_serialization(self):
        """Test AgentMessage serialization."""
        msg = AgentMessage(
            from_agent="a",
            to_agent="b",
            content="test",
        )

        data = msg.model_dump()

        assert data["from_agent"] == "a"
        assert data["to_agent"] == "b"
        assert data["content"] == "test"

    def test_message_with_complex_metadata(self):
        """Test AgentMessage with complex metadata."""
        msg = AgentMessage(
            from_agent="search",
            to_agent="analysis",
            content="Results",
            metadata={
                "nested": {"key": "value"},
                "list": [1, 2, 3],
                "unicode": "你好",
            },
        )

        assert msg.metadata["nested"]["key"] == "value"
        assert msg.metadata["list"] == [1, 2, 3]
        assert msg.metadata["unicode"] == "你好"

    def test_message_with_empty_content(self):
        """Test AgentMessage with empty content."""
        msg = AgentMessage(
            from_agent="a",
            to_agent="b",
            content="",
        )

        assert msg.content == ""

    def test_message_with_unicode_content(self):
        """Test AgentMessage with unicode content."""
        msg = AgentMessage(
            from_agent="search",
            to_agent="analysis",
            content="搜索结果：找到了相关信息 🔍",
        )

        assert "搜索结果" in msg.content
        assert "🔍" in msg.content


# ==============================================================================
# AgentResult Tests
# ==============================================================================


class TestAgentResult:
    """Tests for AgentResult model."""

    def test_result_success(self):
        """Test successful AgentResult."""
        result = AgentResult(
            agent_name="SearchAgent",
            output="Found 5 results",
        )

        assert result.agent_name == "SearchAgent"
        assert result.output == "Found 5 results"
        assert result.success is True
        assert result.error is None
        assert result.metadata == {}

    def test_result_failure(self):
        """Test failed AgentResult."""
        result = AgentResult(
            agent_name="SearchAgent",
            output="",
            success=False,
            error="Connection timeout",
        )

        assert result.success is False
        assert result.error == "Connection timeout"

    def test_result_with_metadata(self):
        """Test AgentResult with metadata."""
        result = AgentResult(
            agent_name="AnalysisAgent",
            output="Analysis complete",
            metadata={"confidence": 0.95, "tokens": 150},
        )

        assert result.metadata["confidence"] == 0.95
        assert result.metadata["tokens"] == 150

    def test_result_serialization(self):
        """Test AgentResult serialization."""
        result = AgentResult(
            agent_name="test",
            output="output",
            success=True,
        )

        data = result.model_dump()

        assert data["agent_name"] == "test"
        assert data["output"] == "output"
        assert data["success"] is True

    def test_result_with_complex_metadata(self):
        """Test AgentResult with complex metadata."""
        result = AgentResult(
            agent_name="AnalysisAgent",
            output="Analysis complete",
            metadata={
                "tokens_used": 150,
                "model": "gpt-4",
                "latency_ms": 1234,
                "sources": ["web", "database"],
            },
        )

        assert result.metadata["tokens_used"] == 150
        assert result.metadata["sources"] == ["web", "database"]

    def test_result_with_long_error(self):
        """Test AgentResult with long error message."""
        long_error = "Error: " + "x" * 1000
        result = AgentResult(
            agent_name="FailedAgent",
            output="",
            success=False,
            error=long_error,
        )

        assert len(result.error) > 1000

    def test_result_with_unicode_output(self):
        """Test AgentResult with unicode output."""
        result = AgentResult(
            agent_name="ResponseAgent",
            output="回答：这是一个测试响应 ✅",
        )

        assert "回答" in result.output
        assert "✅" in result.output


# ==============================================================================
# Task Model Tests
# ==============================================================================


class TestTaskModel:
    """Tests for Task model."""

    def test_task_creation_defaults(self):
        """Test Task creation with defaults."""
        task = Task(content="Test task")

        assert task.content == "Test task"
        assert task.task_type == TaskType.GENERAL
        assert task.priority == TaskPriority.MEDIUM
        assert task.status == TaskStatus.PENDING
        assert task.id is not None

    def test_task_creation_with_values(self):
        """Test Task creation with custom values."""
        task = Task(
            content="Code task",
            task_type=TaskType.CODE,
            priority=TaskPriority.HIGH,
            status=TaskStatus.PENDING,
            context={"language": "python"},
        )

        assert task.content == "Code task"
        assert task.task_type == TaskType.CODE
        assert task.priority == TaskPriority.HIGH
        assert task.context["language"] == "python"

    def test_task_mark_started(self):
        """Test marking task as started."""
        task = Task(content="Test")

        task.mark_started()

        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None

    def test_task_mark_completed(self):
        """Test marking task as completed."""
        task = Task(content="Test")
        task.mark_started()

        result = AgentResult(agent_name="test", output="Result output")
        task.mark_completed(result)

        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert task.result.output == "Result output"

    def test_task_mark_failed(self):
        """Test marking task as failed."""
        task = Task(content="Test")
        task.mark_started()

        task.mark_failed("Error message")

        assert task.status == TaskStatus.FAILED
        assert task.result is not None
        assert task.result.error == "Error message"
        assert task.result.success is False

    def test_task_with_subtasks(self):
        """Test task with subtask IDs."""
        parent_task = Task(content="Parent")
        subtask1 = Task(content="Subtask 1", parent_task_id=parent_task.id)
        subtask2 = Task(content="Subtask 2", parent_task_id=parent_task.id)

        parent_task.subtask_ids.append(subtask1.id)
        parent_task.subtask_ids.append(subtask2.id)

        assert len(parent_task.subtask_ids) == 2
        assert subtask1.parent_task_id == parent_task.id

    def test_task_serialization(self):
        """Test Task serialization."""
        task = Task(
            content="Serializable task",
            task_type=TaskType.ANALYSIS,
            priority=TaskPriority.HIGH,
        )

        data = task.model_dump()

        assert data["content"] == "Serializable task"
        assert data["task_type"] == TaskType.ANALYSIS
        assert data["priority"] == TaskPriority.HIGH


# ==============================================================================
# ExecutionPlan Tests
# ==============================================================================


class TestExecutionPlan:
    """Tests for ExecutionPlan model."""

    def test_plan_creation(self):
        """Test ExecutionPlan creation."""
        original_task = Task(content="Main task")
        steps = [
            Task(content="Step 1"),
            Task(content="Step 2"),
            Task(content="Step 3"),
        ]

        plan = ExecutionPlan(
            original_task=original_task,
            steps=steps,
        )

        assert plan.original_task == original_task
        assert len(plan.steps) == 3
        assert plan.status == TaskStatus.PENDING
        assert plan.current_step == 0

    def test_plan_get_current_step(self):
        """Test getting current step."""
        plan = ExecutionPlan(
            original_task=Task(content="Main"),
            steps=[Task(content="Step 1"), Task(content="Step 2")],
        )

        current = plan.get_current_step()

        assert current is not None
        assert current.content == "Step 1"

    def test_plan_advance_step(self):
        """Test advancing to next step."""
        plan = ExecutionPlan(
            original_task=Task(content="Main"),
            steps=[Task(content="Step 1"), Task(content="Step 2")],
        )

        plan.advance_step()

        assert plan.current_step == 1
        current = plan.get_current_step()
        assert current.content == "Step 2"

    def test_plan_is_complete(self):
        """Test checking if plan is complete."""
        step = Task(content="Step 1")
        plan = ExecutionPlan(
            original_task=Task(content="Main"),
            steps=[step],
        )

        assert plan.is_complete() is False

        # Mark step as completed
        step.mark_completed(AgentResult(agent_name="test", output="Done"))

        assert plan.is_complete() is True

    def test_plan_get_current_step_when_complete(self):
        """Test getting current step when plan is complete."""
        plan = ExecutionPlan(
            original_task=Task(content="Main"),
            steps=[Task(content="Step 1")],
        )
        plan.advance_step()

        current = plan.get_current_step()

        assert current is None

    def test_plan_with_empty_steps(self):
        """Test plan with empty steps."""
        plan = ExecutionPlan(
            original_task=Task(content="Main"),
            steps=[],
        )

        assert plan.is_complete() is True
        assert plan.get_current_step() is None


# ==============================================================================
# BudgetConfig Tests
# ==============================================================================


class TestBudgetConfig:
    """Tests for BudgetConfig."""

    def test_budget_config_defaults(self):
        """Test BudgetConfig default values."""
        budget = BudgetConfig()

        assert budget.enabled is False
        assert budget.period == BudgetPeriod.DAILY
        assert budget.limit == 10.0

    def test_budget_add_usage(self):
        """Test adding usage to budget."""
        budget = BudgetConfig(enabled=True, limit=10.0)

        budget.add_usage(2.5)

        assert budget.current_usage == 2.5

    def test_budget_remaining(self):
        """Test budget remaining calculation."""
        budget = BudgetConfig(enabled=True, limit=10.0)
        budget.current_usage = 3.0

        assert budget.remaining() == 7.0

    def test_budget_usage_percentage(self):
        """Test budget usage percentage calculation."""
        budget = BudgetConfig(enabled=True, limit=10.0)
        budget.current_usage = 5.0

        assert budget.usage_percentage() == 50.0

    def test_budget_is_warning(self):
        """Test budget warning detection."""
        budget = BudgetConfig(
            enabled=True,
            limit=10.0,
            warning_threshold=0.8,
        )
        budget.current_usage = 8.5

        assert budget.is_warning() is True

    def test_budget_is_exceeded(self):
        """Test budget exceeded detection."""
        budget = BudgetConfig(enabled=True, limit=10.0)
        budget.current_usage = 12.0

        assert budget.is_exceeded() is True


# ==============================================================================
# ModelInfo Tests
# ==============================================================================


class TestModelInfo:
    """Tests for ModelInfo."""

    def test_model_info_estimate_cost(self):
        """Test ModelInfo cost estimation."""
        model = ModelInfo(
            name="test:model",
            provider="test",
            cost_per_1k_input=0.01,
            cost_per_1k_output=0.02,
        )

        cost = model.estimate_cost(1000, 500)

        # 1000 input tokens * 0.01 + 500 output tokens * 0.02 = 0.01 + 0.01 = 0.02
        assert cost == 0.02

    def test_model_info_update_stats_success(self):
        """Test ModelInfo stats update on success."""
        model = ModelInfo(
            name="test:model",
            provider="test",
        )

        model.update_stats(success=True, response_time_ms=500)

        assert model.total_requests == 1
        assert model.failed_requests == 0
        assert model.success_rate == 1.0

    def test_model_info_update_stats_failure(self):
        """Test ModelInfo stats update on failure."""
        model = ModelInfo(
            name="test:model",
            provider="test",
        )

        model.update_stats(success=False, response_time_ms=500)

        assert model.total_requests == 1
        assert model.failed_requests == 1
        assert model.success_rate == 0.0

    def test_model_info_health_updates(self):
        """Test ModelInfo health status updates."""
        model = ModelInfo(
            name="test:model",
            provider="test",
        )

        # Multiple successes should result in healthy
        for _ in range(10):
            model.update_stats(success=True, response_time_ms=500)

        assert model.health == ModelHealth.HEALTHY

    def test_model_info_health_degrades(self):
        """Test ModelInfo health degrades on failures."""
        model = ModelInfo(
            name="test:model",
            provider="test",
        )

        # Mix of successes and failures
        for _ in range(8):
            model.update_stats(success=True, response_time_ms=500)
        for _ in range(2):
            model.update_stats(success=False, response_time_ms=500)

        # Success rate is 80%, should be DEGRADED
        assert model.health == ModelHealth.DEGRADED


# ==============================================================================
# RoutingContext and RoutingDecision Tests
# ==============================================================================


class TestRoutingContext:
    """Tests for RoutingContext."""

    def test_routing_context_defaults(self):
        """Test RoutingContext default values."""
        context = RoutingContext()

        assert context.user_id is None
        assert context.language == "en"
        assert context.urgency == 5

    def test_routing_context_with_values(self):
        """Test RoutingContext with custom values."""
        context = RoutingContext(
            user_id="user123",
            language="zh",
            urgency=8,
            preferred_models=["deepseek:deepseek-chat"],
        )

        assert context.user_id == "user123"
        assert context.language == "zh"
        assert context.urgency == 8
        assert "deepseek:deepseek-chat" in context.preferred_models


class TestRoutingDecision:
    """Tests for RoutingDecision."""

    def test_routing_decision_creation(self):
        """Test RoutingDecision creation."""
        decision = RoutingDecision(
            model="openai:gpt-4o",
            strategy_used=RoutingStrategy.BALANCED,
            score=8.5,
            reason="Best balanced score",
        )

        assert decision.model == "openai:gpt-4o"
        assert decision.strategy_used == RoutingStrategy.BALANCED
        assert decision.score == 8.5

    def test_routing_decision_with_alternatives(self):
        """Test RoutingDecision with alternatives."""
        decision = RoutingDecision(
            model="openai:gpt-4o",
            strategy_used=RoutingStrategy.BALANCED,
            alternatives=["openai:gpt-4o-mini", "anthropic:claude-3-5-haiku-20241022"],
        )

        assert len(decision.alternatives) == 2
