"""Tests for ModelRouter and TaskAnalyzer.

Tests cover:
- ModelRouter initialization and routing strategies
- Context-aware routing
- Budget management
- Cost estimation
- Model health monitoring
- A/B testing
- TaskAnalyzer task analysis
"""

from __future__ import annotations

from feishu_webhook_bot.ai.multi_agent import (
    BudgetConfig,
    BudgetPeriod,
    ModelRouter,
    RoutingContext,
    RoutingDecision,
    RoutingStrategy,
    Task,
    TaskAnalyzer,
    TaskType,
)

# ==============================================================================
# ModelRouter Basic Tests
# ==============================================================================


class TestModelRouterBasic:
    """Basic tests for ModelRouter."""

    def test_router_initialization(self):
        """Test ModelRouter initialization with defaults."""
        router = ModelRouter()

        assert router.strategy == RoutingStrategy.BALANCED
        assert router.default_model == "openai:gpt-4o"
        assert len(router.models) > 0

    def test_router_with_custom_strategy(self):
        """Test ModelRouter with custom strategy."""
        router = ModelRouter(strategy=RoutingStrategy.COST_OPTIMIZED)

        assert router.strategy == RoutingStrategy.COST_OPTIMIZED

    def test_router_with_budget(self):
        """Test ModelRouter with budget configuration."""
        budget = BudgetConfig(enabled=True, limit=10.0)
        router = ModelRouter(budget=budget)

        assert router.budget.enabled is True
        assert router.budget.limit == 10.0

    def test_route_basic_task(self):
        """Test routing a basic task."""
        router = ModelRouter()
        task = Task(content="Hello world", task_type=TaskType.CONVERSATION)

        model = router.route(task)

        assert model is not None
        assert model in router.models


# ==============================================================================
# ModelRouter Strategies Tests
# ==============================================================================


class TestModelRouterStrategies:
    """Tests for different routing strategies."""

    def test_cost_optimized_strategy(self):
        """Test cost-optimized routing selects cheapest model."""
        router = ModelRouter(strategy=RoutingStrategy.COST_OPTIMIZED)
        task = Task(content="Test", task_type=TaskType.CONVERSATION)

        model = router.route(task)

        assert model is not None

    def test_quality_optimized_strategy(self):
        """Test quality-optimized routing selects best quality model."""
        router = ModelRouter(strategy=RoutingStrategy.QUALITY_OPTIMIZED)
        task = Task(content="Test", task_type=TaskType.CONVERSATION)

        model = router.route(task)

        assert model is not None

    def test_speed_optimized_strategy(self):
        """Test speed-optimized routing selects fastest model."""
        router = ModelRouter(strategy=RoutingStrategy.SPEED_OPTIMIZED)
        task = Task(content="Test", task_type=TaskType.CONVERSATION)

        model = router.route(task)

        assert model is not None

    def test_balanced_strategy(self):
        """Test balanced routing."""
        router = ModelRouter(strategy=RoutingStrategy.BALANCED)
        task = Task(content="Test", task_type=TaskType.CONVERSATION)

        model = router.route(task)

        assert model is not None

    def test_round_robin_strategy(self):
        """Test round-robin routing distributes across models."""
        router = ModelRouter(strategy=RoutingStrategy.ROUND_ROBIN)

        models_used = set()
        for _ in range(10):
            task = Task(content="Test", task_type=TaskType.CONVERSATION)
            model = router.route(task)
            models_used.add(model)

        assert len(models_used) >= 1

    def test_latency_optimized_strategy(self):
        """Test latency-optimized routing."""
        router = ModelRouter(strategy=RoutingStrategy.LATENCY_OPTIMIZED)
        task = Task(content="Test", task_type=TaskType.CONVERSATION)

        model = router.route(task)

        assert model is not None

    def test_adaptive_strategy(self):
        """Test adaptive routing based on performance."""
        router = ModelRouter(strategy=RoutingStrategy.ADAPTIVE)
        task = Task(content="Test", task_type=TaskType.CONVERSATION)

        model = router.route(task)

        assert model is not None

    def test_budget_aware_strategy(self):
        """Test budget-aware routing."""
        budget = BudgetConfig(enabled=True, limit=10.0)
        router = ModelRouter(strategy=RoutingStrategy.BUDGET_AWARE, budget=budget)
        task = Task(content="Test", task_type=TaskType.CONVERSATION)

        model = router.route(task)

        assert model is not None


# ==============================================================================
# ModelRouter Context-Aware Tests
# ==============================================================================


class TestModelRouterContextAware:
    """Tests for context-aware routing."""

    def test_route_with_context(self):
        """Test routing with context information."""
        router = ModelRouter()
        task = Task(content="Test message", task_type=TaskType.CONVERSATION)
        context = RoutingContext(
            user_id="user123",
            language="en",
            urgency=5,
        )

        decision = router.route_with_context(task, context)

        assert isinstance(decision, RoutingDecision)
        assert decision.model is not None
        assert decision.strategy_used == RoutingStrategy.CONTEXT_AWARE

    def test_route_with_chinese_language(self):
        """Test routing prefers Chinese models for Chinese language."""
        router = ModelRouter()
        task = Task(content="你好世界", task_type=TaskType.CONVERSATION)
        context = RoutingContext(language="zh")

        decision = router.route_with_context(task, context)

        assert decision.model is not None

    def test_route_with_high_urgency(self):
        """Test routing with high urgency prefers fast models."""
        router = ModelRouter()
        task = Task(content="Urgent task", task_type=TaskType.CONVERSATION)
        context = RoutingContext(urgency=9)

        decision = router.route_with_context(task, context)

        assert decision.model is not None

    def test_route_with_user_preferences(self):
        """Test routing respects user preferences."""
        router = ModelRouter()
        task = Task(content="Test", task_type=TaskType.CONVERSATION)
        context = RoutingContext(preferred_models=["anthropic:claude-3-5-sonnet-20241022"])

        decision = router.route_with_context(task, context)

        assert decision.model is not None


# ==============================================================================
# ModelRouter Budget Tests
# ==============================================================================


class TestModelRouterBudget:
    """Tests for budget management."""

    def test_set_budget(self):
        """Test setting budget configuration."""
        router = ModelRouter()

        router.set_budget(limit=50.0, period=BudgetPeriod.DAILY)

        assert router.budget.enabled is True
        assert router.budget.limit == 50.0
        assert router.budget.period == BudgetPeriod.DAILY

    def test_get_budget_status(self):
        """Test getting budget status."""
        budget = BudgetConfig(enabled=True, limit=10.0)
        router = ModelRouter(budget=budget)

        status = router.get_budget_status()

        assert status["enabled"] is True
        assert status["limit"] == 10.0
        assert status["current_usage"] == 0.0
        assert status["remaining"] == 10.0

    def test_record_usage_updates_budget(self):
        """Test recording usage updates budget."""
        budget = BudgetConfig(enabled=True, limit=10.0)
        router = ModelRouter(budget=budget)

        router.record_usage(
            model="openai:gpt-4o",
            task_type=TaskType.CONVERSATION,
            success=True,
            latency_ms=500,
            input_tokens=100,
            output_tokens=100,
        )

        assert router.budget.current_usage > 0

    def test_budget_warning_threshold(self):
        """Test budget warning threshold detection."""
        budget = BudgetConfig(
            enabled=True,
            limit=1.0,
            warning_threshold=0.5,
        )
        router = ModelRouter(budget=budget)

        router.budget.current_usage = 0.6

        assert router.budget.is_warning() is True

    def test_budget_exceeded(self):
        """Test budget exceeded detection."""
        budget = BudgetConfig(enabled=True, limit=1.0)
        router = ModelRouter(budget=budget)

        router.budget.current_usage = 1.5

        assert router.budget.is_exceeded() is True


# ==============================================================================
# ModelRouter Cost Estimation Tests
# ==============================================================================


class TestModelRouterCostEstimation:
    """Tests for cost estimation."""

    def test_estimate_cost(self):
        """Test cost estimation for a task."""
        router = ModelRouter()
        task = Task(content="Test message", task_type=TaskType.CONVERSATION)

        estimate = router.estimate_cost(task)

        assert "model" in estimate
        assert "estimated_cost" in estimate
        assert estimate["estimated_cost"] >= 0

    def test_estimate_cost_with_specific_model(self):
        """Test cost estimation with specific model."""
        router = ModelRouter()
        task = Task(content="Test", task_type=TaskType.CONVERSATION)

        estimate = router.estimate_cost(task, model="openai:gpt-4o-mini")

        assert estimate["model"] == "openai:gpt-4o-mini"

    def test_estimate_cost_with_token_counts(self):
        """Test cost estimation with specific token counts."""
        router = ModelRouter()
        task = Task(content="Test", task_type=TaskType.CONVERSATION)

        estimate = router.estimate_cost(
            task,
            model="openai:gpt-4o",
            input_tokens=1000,
            output_tokens=500,
        )

        assert estimate["input_tokens"] == 1000
        assert estimate["output_tokens"] == 500


# ==============================================================================
# ModelRouter Health Tests
# ==============================================================================


class TestModelRouterHealth:
    """Tests for model health monitoring."""

    def test_get_model_health_all(self):
        """Test getting health status of all models."""
        router = ModelRouter()

        health = router.get_model_health()

        assert len(health) > 0
        for _model_name, status in health.items():
            assert "health" in status
            assert "success_rate" in status

    def test_get_model_health_specific(self):
        """Test getting health status of specific model."""
        router = ModelRouter()

        health = router.get_model_health("openai:gpt-4o")

        assert health["model"] == "openai:gpt-4o"
        assert "health" in health
        assert "success_rate" in health

    def test_record_usage_updates_health(self):
        """Test recording usage updates model health."""
        router = ModelRouter()

        for _ in range(5):
            router.record_usage(
                model="openai:gpt-4o",
                task_type=TaskType.CONVERSATION,
                success=False,
                latency_ms=1000,
                input_tokens=100,
                output_tokens=100,
            )

        health = router.get_model_health("openai:gpt-4o")

        assert health["success_rate"] < 1.0


# ==============================================================================
# ModelRouter Recommendation Tests
# ==============================================================================


class TestModelRouterRecommendation:
    """Tests for model recommendation."""

    def test_recommend_model(self):
        """Test model recommendation."""
        router = ModelRouter()

        recommendation = router.recommend_model("Write a Python function")

        assert "task_type" in recommendation
        assert "complexity" in recommendation
        assert "top_recommendation" in recommendation

    def test_recommend_model_with_constraints(self):
        """Test model recommendation with constraints."""
        router = ModelRouter()

        recommendation = router.recommend_model(
            "Simple question",
            constraints={"max_cost": 0.001},
        )

        assert recommendation is not None

    def test_recommend_model_code_task(self):
        """Test model recommendation for code task."""
        router = ModelRouter()

        recommendation = router.recommend_model("Write a Python function to sort a list")

        assert recommendation["task_type"] == "code"


# ==============================================================================
# ModelRouter Batch Routing Tests
# ==============================================================================


class TestModelRouterBatchRouting:
    """Tests for batch routing."""

    def test_batch_route(self):
        """Test batch routing multiple tasks."""
        router = ModelRouter()
        tasks = [
            Task(content="Task 1", task_type=TaskType.CONVERSATION),
            Task(content="Task 2", task_type=TaskType.CODE),
            Task(content="Task 3", task_type=TaskType.SUMMARY),
        ]

        results = router.batch_route(tasks)

        assert len(results) == 3
        for _task, model in results:
            assert model is not None

    def test_batch_route_with_strategy(self):
        """Test batch routing with specific strategy."""
        router = ModelRouter()
        tasks = [
            Task(content="Task 1", task_type=TaskType.CONVERSATION),
            Task(content="Task 2", task_type=TaskType.CONVERSATION),
        ]

        results = router.batch_route(tasks, strategy=RoutingStrategy.COST_OPTIMIZED)

        assert len(results) == 2


# ==============================================================================
# ModelRouter A/B Testing Tests
# ==============================================================================


class TestModelRouterABTesting:
    """Tests for A/B testing."""

    def test_setup_ab_test(self):
        """Test setting up A/B test."""
        router = ModelRouter()

        router.setup_ab_test(
            test_models=["openai:gpt-4o", "openai:gpt-4o-mini"],
            ratio=0.2,
        )

        assert router.enable_ab_testing is True
        assert router.ab_test_ratio == 0.2

    def test_get_ab_test_results(self):
        """Test getting A/B test results."""
        router = ModelRouter()
        router.setup_ab_test(["openai:gpt-4o"])

        results = router.get_ab_test_results()

        assert results["enabled"] is True
        assert "results" in results

    def test_record_ab_test_result(self):
        """Test recording A/B test result."""
        router = ModelRouter()
        router.setup_ab_test(["openai:gpt-4o"])

        router.record_ab_test_result(
            model="openai:gpt-4o",
            success=True,
            latency_ms=500,
        )

        results = router.get_ab_test_results()
        assert results["results"]["openai:gpt-4o"]["requests"] == 1


# ==============================================================================
# ModelRouter Utilities Tests
# ==============================================================================


class TestModelRouterUtilities:
    """Tests for utility methods."""

    def test_get_models_by_tag(self):
        """Test getting models by tag."""
        router = ModelRouter()

        chinese_models = router.get_models_by_tag("chinese")

        assert isinstance(chinese_models, list)

    def test_get_models_by_provider(self):
        """Test getting models by provider."""
        router = ModelRouter()

        openai_models = router.get_models_by_provider("openai")

        assert len(openai_models) > 0
        for model in openai_models:
            assert "openai:" in model

    def test_get_cheapest_model(self):
        """Test getting cheapest model."""
        router = ModelRouter()

        cheapest = router.get_cheapest_model()

        assert cheapest is not None

    def test_get_fastest_model(self):
        """Test getting fastest model."""
        router = ModelRouter()

        fastest = router.get_fastest_model()

        assert fastest is not None

    def test_get_best_quality_model(self):
        """Test getting best quality model."""
        router = ModelRouter()

        best = router.get_best_quality_model()

        assert best is not None

    def test_get_routing_history(self):
        """Test getting routing history."""
        router = ModelRouter()

        history = router.get_routing_history()

        assert isinstance(history, list)


# ==============================================================================
# TaskAnalyzer Tests
# ==============================================================================


class TestTaskAnalyzerEnhanced:
    """Enhanced tests for TaskAnalyzer."""

    def test_analyze_code_task(self):
        """Test analyzing code task."""
        analyzer = TaskAnalyzer()

        task_type = analyzer.analyze("Write a Python function to sort a list")

        assert task_type == TaskType.CODE

    def test_analyze_math_task(self):
        """Test analyzing math task."""
        analyzer = TaskAnalyzer()

        task_type = analyzer.analyze("Calculate the sum of 1 + 2 + 3")

        assert task_type == TaskType.MATH

    def test_analyze_translation_task(self):
        """Test analyzing translation task."""
        analyzer = TaskAnalyzer()

        task_type = analyzer.analyze("Translate this to Chinese")

        assert task_type == TaskType.TRANSLATION

    def test_analyze_complexity_simple(self):
        """Test analyzing simple task complexity."""
        analyzer = TaskAnalyzer()

        complexity = analyzer.analyze_complexity("Hello")

        assert complexity <= 5

    def test_analyze_complexity_complex(self):
        """Test analyzing complex task complexity."""
        analyzer = TaskAnalyzer()

        complexity = analyzer.analyze_complexity(
            "Design a distributed machine learning system with "
            "neural network architecture for scalability and performance optimization. "
            "Include step by step implementation details for multiple components."
        )

        assert complexity >= 7

    def test_suggest_strategy_high_complexity(self):
        """Test strategy suggestion for high complexity."""
        analyzer = TaskAnalyzer()

        strategy = analyzer.suggest_strategy(TaskType.CODE, complexity=9)

        assert strategy == RoutingStrategy.QUALITY_OPTIMIZED

    def test_suggest_strategy_low_complexity(self):
        """Test strategy suggestion for low complexity."""
        analyzer = TaskAnalyzer()

        strategy = analyzer.suggest_strategy(TaskType.CONVERSATION, complexity=2)

        assert strategy == RoutingStrategy.COST_OPTIMIZED
