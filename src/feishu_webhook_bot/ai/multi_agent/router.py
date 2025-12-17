"""Model router for intelligent task-to-model routing.

This module provides automatic routing of tasks to the most appropriate
AI model based on task type, cost, speed, and quality requirements.

Features:
- Multiple routing strategies (cost, speed, quality, balanced, etc.)
- Context-aware routing based on conversation history
- Adaptive routing based on model performance
- Budget management and cost tracking
- Model health monitoring and failover
- A/B testing support
- Batch routing for multiple tasks
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from ...core.logger import get_logger
from .base import (
    DEFAULT_MODELS,
    AgentCapability,
    BudgetConfig,
    BudgetPeriod,
    ModelHealth,
    ModelInfo,
    RoutingContext,
    RoutingDecision,
    RoutingHistory,
    RoutingStrategy,
    Task,
    TaskType,
)

logger = get_logger("ai.multi_agent.router")


# Mapping from task types to required capabilities
TASK_CAPABILITY_MAP: dict[TaskType, list[AgentCapability]] = {
    TaskType.GENERAL: [AgentCapability.CONVERSATION],
    TaskType.SEARCH: [AgentCapability.SEARCH],
    TaskType.ANALYSIS: [AgentCapability.ANALYSIS],
    TaskType.CODE: [AgentCapability.CODE_GENERATION],
    TaskType.SUMMARY: [AgentCapability.SUMMARIZATION],
    TaskType.TRANSLATION: [AgentCapability.TRANSLATION],
    TaskType.REASONING: [AgentCapability.REASONING],
    TaskType.PLANNING: [AgentCapability.PLANNING],
    TaskType.CREATIVE: [AgentCapability.CREATIVE_WRITING],
    TaskType.MATH: [AgentCapability.MATH],
    TaskType.CONVERSATION: [AgentCapability.CONVERSATION],
}


class ModelRouter:
    """Routes tasks to appropriate AI models.

    The router supports multiple strategies:
    - cost_optimized: Choose cheapest capable model
    - speed_optimized: Choose fastest capable model
    - quality_optimized: Choose highest quality capable model
    - balanced: Balance between cost, speed, and quality
    - round_robin: Distribute load across models
    - capability_based: Choose based on task requirements
    - context_aware: Route based on conversation context
    - adaptive: Learn from historical performance
    - budget_aware: Consider budget constraints
    - latency_optimized: Minimize response latency

    Example:
        ```python
        router = ModelRouter(strategy=RoutingStrategy.BALANCED)
        model = router.route(task)

        # With context-aware routing
        context = RoutingContext(user_id="user123", language="zh")
        decision = router.route_with_context(task, context)
        ```
    """

    def __init__(
        self,
        strategy: RoutingStrategy = RoutingStrategy.BALANCED,
        models: dict[str, ModelInfo] | None = None,
        default_model: str = "openai:gpt-4o",
        budget: BudgetConfig | None = None,
        enable_health_check: bool = True,
        enable_ab_testing: bool = False,
        ab_test_ratio: float = 0.1,
    ) -> None:
        """Initialize the model router.

        Args:
            strategy: Routing strategy to use
            models: Dictionary of available models
            default_model: Default model when routing fails
            budget: Budget configuration for cost management
            enable_health_check: Whether to enable health monitoring
            enable_ab_testing: Whether to enable A/B testing
            ab_test_ratio: Ratio of requests to use for A/B testing
        """
        self.strategy = strategy
        self.models = models or DEFAULT_MODELS.copy()
        self.default_model = default_model
        self.budget = budget or BudgetConfig()
        self.enable_health_check = enable_health_check
        self.enable_ab_testing = enable_ab_testing
        self.ab_test_ratio = ab_test_ratio

        # Round-robin state
        self._round_robin_index = 0
        self._enabled_models: list[str] = [
            name for name, info in self.models.items() if info.enabled
        ]

        # Usage tracking for load balancing
        self._model_usage: dict[str, int] = {name: 0 for name in self.models}

        # Routing history for adaptive routing
        self._routing_history: list[RoutingHistory] = []
        self._max_history_size = 1000

        # Performance tracking per model per task type
        self._performance_stats: dict[str, dict[str, dict[str, float]]] = defaultdict(
            lambda: defaultdict(lambda: {"success_rate": 1.0, "avg_latency": 1000.0})
        )

        # A/B testing state
        self._ab_test_models: list[str] = []
        self._ab_test_results: dict[str, dict[str, float]] = defaultdict(
            lambda: {"requests": 0, "successes": 0, "total_latency": 0.0}
        )

        # Language to model preferences
        self._language_preferences: dict[str, list[str]] = {
            "zh": ["deepseek:deepseek-chat", "qwen:qwen-max", "qwen:qwen-turbo"],
            "ja": ["openai:gpt-4o", "anthropic:claude-3-5-sonnet-20241022"],
            "ko": ["openai:gpt-4o", "anthropic:claude-3-5-sonnet-20241022"],
            "en": ["openai:gpt-4o", "anthropic:claude-3-5-sonnet-20241022"],
            "de": ["mistral:mistral-large", "openai:gpt-4o"],
            "fr": ["mistral:mistral-large", "openai:gpt-4o"],
        }

        logger.info(
            "ModelRouter initialized (strategy: %s, models: %d, budget: %s, health: %s)",
            strategy.value,
            len(self._enabled_models),
            budget.enabled if budget else False,
            enable_health_check,
        )

    def route(self, task: Task) -> str:
        """Route a task to the most appropriate model.

        Args:
            task: Task to route

        Returns:
            Model name (e.g., "openai:gpt-4o")
        """
        logger.debug(
            "Routing task %s (type: %s) with strategy: %s",
            task.id,
            task.task_type.value,
            self.strategy.value,
        )

        # Get capable models for this task
        capable_models = self._get_capable_models(task.task_type)

        if not capable_models:
            logger.warning(
                "No capable models found for task type %s, using default: %s",
                task.task_type.value,
                self.default_model,
            )
            return self.default_model

        # Apply routing strategy
        selected_model = self._apply_strategy(capable_models, task)

        # Track usage
        self._model_usage[selected_model] = self._model_usage.get(selected_model, 0) + 1

        logger.info(
            "Routed task %s to model: %s",
            task.id,
            selected_model,
        )

        return selected_model

    def route_by_capability(
        self,
        capability: AgentCapability,
        strategy: RoutingStrategy | None = None,
    ) -> str:
        """Route based on a specific capability requirement.

        Args:
            capability: Required capability
            strategy: Optional override strategy

        Returns:
            Model name
        """
        capable_models = [
            name
            for name, info in self.models.items()
            if info.enabled and capability in info.capabilities
        ]

        if not capable_models:
            logger.warning(
                "No models found with capability %s, using default",
                capability.value,
            )
            return self.default_model

        # Create a dummy task for strategy application
        dummy_task = Task(content="", task_type=TaskType.GENERAL)
        return self._apply_strategy(
            capable_models,
            dummy_task,
            strategy or self.strategy,
        )

    def route_for_cost(self, task: Task, max_cost_per_1k: float) -> str:
        """Route to a model within cost constraints.

        Args:
            task: Task to route
            max_cost_per_1k: Maximum cost per 1000 tokens

        Returns:
            Model name within budget
        """
        capable_models = self._get_capable_models(task.task_type)

        # Filter by cost
        affordable_models = [
            name
            for name in capable_models
            if self.models[name].cost_per_1k_input <= max_cost_per_1k
        ]

        if not affordable_models:
            logger.warning(
                "No affordable models found (max: %.4f), using cheapest available",
                max_cost_per_1k,
            )
            # Return cheapest capable model
            return min(
                capable_models,
                key=lambda m: self.models[m].cost_per_1k_input,
            )

        # Among affordable models, choose best quality
        return max(
            affordable_models,
            key=lambda m: self.models[m].quality_rating,
        )

    def route_for_speed(self, task: Task, min_speed_rating: int = 7) -> str:
        """Route to a fast model.

        Args:
            task: Task to route
            min_speed_rating: Minimum speed rating (1-10)

        Returns:
            Fast model name
        """
        capable_models = self._get_capable_models(task.task_type)

        # Filter by speed
        fast_models = [
            name for name in capable_models if self.models[name].speed_rating >= min_speed_rating
        ]

        if not fast_models:
            logger.warning(
                "No fast models found (min speed: %d), using fastest available",
                min_speed_rating,
            )
            return max(
                capable_models,
                key=lambda m: self.models[m].speed_rating,
            )

        # Among fast models, choose best quality
        return max(
            fast_models,
            key=lambda m: self.models[m].quality_rating,
        )

    def route_for_quality(self, task: Task, min_quality_rating: int = 8) -> str:
        """Route to a high-quality model.

        Args:
            task: Task to route
            min_quality_rating: Minimum quality rating (1-10)

        Returns:
            High-quality model name
        """
        capable_models = self._get_capable_models(task.task_type)

        # Filter by quality
        quality_models = [
            name
            for name in capable_models
            if self.models[name].quality_rating >= min_quality_rating
        ]

        if not quality_models:
            logger.warning(
                "No high-quality models found (min quality: %d), using best available",
                min_quality_rating,
            )
            return max(
                capable_models,
                key=lambda m: self.models[m].quality_rating,
            )

        # Among quality models, choose cheapest
        return min(
            quality_models,
            key=lambda m: self.models[m].cost_per_1k_input,
        )

    def _get_capable_models(self, task_type: TaskType) -> list[str]:
        """Get models capable of handling a task type.

        Args:
            task_type: Type of task

        Returns:
            List of capable model names
        """
        required_capabilities = TASK_CAPABILITY_MAP.get(
            task_type,
            [AgentCapability.CONVERSATION],
        )

        capable_models = []
        for name, info in self.models.items():
            if not info.enabled:
                continue

            # Check if model has at least one required capability
            if any(cap in info.capabilities for cap in required_capabilities):
                capable_models.append(name)

        return capable_models

    def _apply_strategy(
        self,
        models: list[str],
        task: Task,
        strategy: RoutingStrategy | None = None,
    ) -> str:
        """Apply routing strategy to select a model.

        Args:
            models: List of candidate models
            task: Task being routed
            strategy: Strategy to apply

        Returns:
            Selected model name
        """
        strategy = strategy or self.strategy

        if strategy == RoutingStrategy.COST_OPTIMIZED:
            return min(models, key=lambda m: self.models[m].cost_per_1k_input)

        elif strategy == RoutingStrategy.SPEED_OPTIMIZED:
            return max(models, key=lambda m: self.models[m].speed_rating)

        elif strategy == RoutingStrategy.QUALITY_OPTIMIZED:
            return max(models, key=lambda m: self.models[m].quality_rating)

        elif strategy == RoutingStrategy.BALANCED:
            # Score = quality * 0.4 + speed * 0.3 - cost * 0.3
            def score(model: str) -> float:
                info = self.models[model]
                # Normalize cost (lower is better, so invert)
                cost_score = 1 / (1 + info.cost_per_1k_input * 100)
                return info.quality_rating * 0.4 + info.speed_rating * 0.3 + cost_score * 10 * 0.3

            return max(models, key=score)

        elif strategy == RoutingStrategy.ROUND_ROBIN:
            # Filter to only enabled models in the candidate list
            available = [m for m in self._enabled_models if m in models]
            if not available:
                return models[0]

            selected = available[self._round_robin_index % len(available)]
            self._round_robin_index += 1
            return selected

        elif strategy == RoutingStrategy.CAPABILITY_BASED:
            # Choose model with most matching capabilities
            required_caps = TASK_CAPABILITY_MAP.get(
                task.task_type,
                [AgentCapability.CONVERSATION],
            )

            def capability_score(model: str) -> int:
                info = self.models[model]
                return sum(1 for cap in required_caps if cap in info.capabilities)

            return max(models, key=capability_score)

        elif strategy == RoutingStrategy.LATENCY_OPTIMIZED:
            # Choose model with lowest latency
            return min(models, key=lambda m: self.models[m].latency_ms)

        elif strategy == RoutingStrategy.ADAPTIVE:
            # Use historical performance data
            return self._apply_adaptive_strategy(models, task)

        elif strategy == RoutingStrategy.BUDGET_AWARE:
            # Consider budget constraints
            return self._apply_budget_aware_strategy(models, task)

        elif strategy == RoutingStrategy.CONTEXT_AWARE:
            # Use context for routing (falls back to balanced without context)
            return self._apply_strategy(models, task, RoutingStrategy.BALANCED)

        else:
            # Default to first model
            return models[0]

    def _apply_adaptive_strategy(self, models: list[str], task: Task) -> str:
        """Apply adaptive routing based on historical performance.

        Args:
            models: List of candidate models
            task: Task being routed

        Returns:
            Selected model name
        """
        task_type_str = task.task_type.value

        def adaptive_score(model: str) -> float:
            stats = self._performance_stats[model][task_type_str]
            info = self.models[model]

            # Combine historical performance with model ratings
            success_weight = stats["success_rate"] * 0.4
            latency_weight = (1 / (1 + stats["avg_latency"] / 1000)) * 0.3
            quality_weight = info.quality_rating / 10 * 0.3

            return success_weight + latency_weight + quality_weight

        return max(models, key=adaptive_score)

    def _apply_budget_aware_strategy(self, models: list[str], task: Task) -> str:
        """Apply budget-aware routing.

        Args:
            models: List of candidate models
            task: Task being routed

        Returns:
            Selected model name
        """
        # Check budget status
        self.budget.reset_if_needed()

        if self.budget.enabled and self.budget.is_exceeded() and self.budget.hard_limit:
            # Budget exceeded with hard limit - use cheapest model
            return min(models, key=lambda m: self.models[m].cost_per_1k_input)

        if self.budget.enabled and self.budget.is_warning():
            # Near budget limit - prefer cheaper models
            def budget_score(model: str) -> float:
                info = self.models[model]
                cost_factor = 1 / (1 + info.cost_per_1k_input * 100)
                quality_factor = info.quality_rating / 10
                return cost_factor * 0.7 + quality_factor * 0.3

            return max(models, key=budget_score)

        # Normal operation - use balanced strategy
        return self._apply_strategy(models, task, RoutingStrategy.BALANCED)

    def add_model(self, model_info: ModelInfo) -> None:
        """Add a new model to the router.

        Args:
            model_info: Model information
        """
        self.models[model_info.name] = model_info
        if model_info.enabled:
            self._enabled_models.append(model_info.name)
        self._model_usage[model_info.name] = 0

        logger.info("Added model to router: %s", model_info.name)

    def remove_model(self, model_name: str) -> bool:
        """Remove a model from the router.

        Args:
            model_name: Name of model to remove

        Returns:
            True if model was removed
        """
        if model_name in self.models:
            del self.models[model_name]
            if model_name in self._enabled_models:
                self._enabled_models.remove(model_name)
            if model_name in self._model_usage:
                del self._model_usage[model_name]

            logger.info("Removed model from router: %s", model_name)
            return True

        return False

    def enable_model(self, model_name: str) -> bool:
        """Enable a model.

        Args:
            model_name: Name of model to enable

        Returns:
            True if model was enabled
        """
        if model_name in self.models:
            self.models[model_name].enabled = True
            if model_name not in self._enabled_models:
                self._enabled_models.append(model_name)
            logger.info("Enabled model: %s", model_name)
            return True
        return False

    def disable_model(self, model_name: str) -> bool:
        """Disable a model.

        Args:
            model_name: Name of model to disable

        Returns:
            True if model was disabled
        """
        if model_name in self.models:
            self.models[model_name].enabled = False
            if model_name in self._enabled_models:
                self._enabled_models.remove(model_name)
            logger.info("Disabled model: %s", model_name)
            return True
        return False

    def set_strategy(self, strategy: RoutingStrategy) -> None:
        """Set the routing strategy.

        Args:
            strategy: New routing strategy
        """
        self.strategy = strategy
        logger.info("Set routing strategy to: %s", strategy.value)

    def get_model_info(self, model_name: str) -> ModelInfo | None:
        """Get information about a model.

        Args:
            model_name: Name of model

        Returns:
            ModelInfo or None if not found
        """
        return self.models.get(model_name)

    def get_available_models(self) -> list[str]:
        """Get list of available (enabled) models.

        Returns:
            List of model names
        """
        return self._enabled_models.copy()

    def get_models_by_capability(
        self,
        capability: AgentCapability,
    ) -> list[str]:
        """Get models that have a specific capability.

        Args:
            capability: Required capability

        Returns:
            List of model names
        """
        return [
            name
            for name, info in self.models.items()
            if info.enabled and capability in info.capabilities
        ]

    def get_stats(self) -> dict[str, Any]:
        """Get router statistics.

        Returns:
            Dictionary with router stats
        """
        return {
            "strategy": self.strategy.value,
            "total_models": len(self.models),
            "enabled_models": len(self._enabled_models),
            "default_model": self.default_model,
            "model_usage": self._model_usage.copy(),
            "budget": {
                "enabled": self.budget.enabled,
                "limit": self.budget.limit,
                "current_usage": self.budget.current_usage,
                "remaining": self.budget.remaining(),
                "usage_percentage": self.budget.usage_percentage(),
            },
            "models": {
                name: {
                    "provider": info.provider,
                    "enabled": info.enabled,
                    "quality_rating": info.quality_rating,
                    "speed_rating": info.speed_rating,
                    "cost_per_1k_input": info.cost_per_1k_input,
                    "health": info.health.value,
                    "success_rate": info.success_rate,
                    "total_requests": info.total_requests,
                }
                for name, info in self.models.items()
            },
        }

    # =========================================================================
    # New Enhanced API Methods
    # =========================================================================

    def route_with_context(
        self,
        task: Task,
        context: RoutingContext,
    ) -> RoutingDecision:
        """Route a task with full context information.

        This method provides intelligent routing based on:
        - User preferences
        - Conversation history
        - Language detection
        - Task urgency

        Args:
            task: Task to route
            context: Routing context with user/conversation info

        Returns:
            RoutingDecision with full details
        """
        capable_models = self._get_capable_models(task.task_type)

        if not capable_models:
            return RoutingDecision(
                model=self.default_model,
                strategy_used=self.strategy,
                reason="No capable models found, using default",
                confidence=0.5,
            )

        # Apply context-aware adjustments
        scored_models: list[tuple[str, float, str]] = []

        for model in capable_models:
            score = 0.0
            reasons: list[str] = []
            info = self.models[model]

            # Base score from model quality
            score += info.quality_rating * 0.2
            reasons.append(f"quality={info.quality_rating}")

            # Language preference bonus
            if context.language in self._language_preferences:
                preferred = self._language_preferences[context.language]
                if model in preferred:
                    bonus = 3.0 - preferred.index(model) * 0.5
                    score += bonus
                    reasons.append(f"language_bonus={bonus:.1f}")

            # User preference bonus
            if model in context.preferred_models:
                idx = context.preferred_models.index(model)
                bonus = 2.0 - idx * 0.3
                score += bonus
                reasons.append(f"user_pref_bonus={bonus:.1f}")

            # Urgency adjustment
            if context.urgency >= 8:
                # High urgency - prefer fast models
                score += info.speed_rating * 0.3
                reasons.append("urgency_speed_boost")
            elif context.urgency <= 3:
                # Low urgency - prefer quality
                score += info.quality_rating * 0.2
                reasons.append("quality_boost")

            # Health penalty
            if info.health == ModelHealth.DEGRADED:
                score -= 1.0
                reasons.append("health_penalty")
            elif info.health == ModelHealth.UNHEALTHY:
                score -= 3.0
                reasons.append("unhealthy_penalty")

            # Historical performance for this task type
            perf = self._performance_stats[model][task.task_type.value]
            score += perf["success_rate"] * 2.0
            reasons.append(f"perf_success={perf['success_rate']:.2f}")

            scored_models.append((model, score, ", ".join(reasons)))

        # Sort by score
        scored_models.sort(key=lambda x: x[1], reverse=True)

        best_model, best_score, best_reason = scored_models[0]
        alternatives = [m[0] for m in scored_models[1:4]]  # Top 3 alternatives

        # Estimate cost and latency
        model_info = self.models[best_model]
        estimated_tokens = len(task.content.split()) * 2  # Rough estimate
        estimated_cost = model_info.estimate_cost(estimated_tokens, estimated_tokens)

        # Track usage
        self._model_usage[best_model] = self._model_usage.get(best_model, 0) + 1

        decision = RoutingDecision(
            model=best_model,
            strategy_used=RoutingStrategy.CONTEXT_AWARE,
            score=best_score,
            alternatives=alternatives,
            reason=best_reason,
            estimated_cost=estimated_cost,
            estimated_latency_ms=model_info.latency_ms,
            confidence=min(1.0, best_score / 10),
            timestamp=datetime.now(),
        )

        logger.info(
            "Context-aware routing: %s (score: %.2f, confidence: %.2f)",
            best_model,
            best_score,
            decision.confidence,
        )

        return decision

    def estimate_cost(
        self,
        task: Task,
        model: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> dict[str, float]:
        """Estimate cost for a task.

        Args:
            task: Task to estimate
            model: Specific model (auto-route if None)
            input_tokens: Input token count (estimate if None)
            output_tokens: Output token count (estimate if None)

        Returns:
            Dictionary with cost estimates
        """
        if model is None:
            model = self.route(task)

        model_info = self.models.get(model)
        if not model_info:
            return {"error": "Model not found", "model": model}

        # Estimate tokens if not provided
        if input_tokens is None:
            input_tokens = len(task.content.split()) * 2  # Rough estimate

        if output_tokens is None:
            output_tokens = input_tokens  # Assume similar output length

        cost = model_info.estimate_cost(input_tokens, output_tokens)

        return {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_per_1k_input": model_info.cost_per_1k_input,
            "cost_per_1k_output": model_info.cost_per_1k_output,
            "estimated_cost": cost,
            "budget_remaining": self.budget.remaining() if self.budget.enabled else None,
        }

    def get_model_health(self, model_name: str | None = None) -> dict[str, Any]:
        """Get health status of models.

        Args:
            model_name: Specific model (all models if None)

        Returns:
            Health status information
        """
        if model_name:
            info = self.models.get(model_name)
            if not info:
                return {"error": "Model not found"}

            return {
                "model": model_name,
                "health": info.health.value,
                "success_rate": info.success_rate,
                "avg_response_time_ms": info.avg_response_time_ms,
                "total_requests": info.total_requests,
                "failed_requests": info.failed_requests,
                "last_used": info.last_used.isoformat() if info.last_used else None,
                "last_health_check": (
                    info.last_health_check.isoformat() if info.last_health_check else None
                ),
            }

        # Return all models health
        return {
            name: {
                "health": info.health.value,
                "success_rate": info.success_rate,
                "total_requests": info.total_requests,
                "enabled": info.enabled,
            }
            for name, info in self.models.items()
        }

    def set_budget(
        self,
        limit: float,
        period: BudgetPeriod = BudgetPeriod.DAILY,
        hard_limit: bool = False,
        warning_threshold: float = 0.8,
    ) -> None:
        """Set budget configuration.

        Args:
            limit: Budget limit in dollars
            period: Budget period
            hard_limit: Whether to block when exceeded
            warning_threshold: Warning threshold (0.0-1.0)
        """
        self.budget = BudgetConfig(
            enabled=True,
            period=period,
            limit=limit,
            hard_limit=hard_limit,
            warning_threshold=warning_threshold,
        )
        logger.info(
            "Budget set: $%.2f per %s (hard_limit: %s)",
            limit,
            period.value,
            hard_limit,
        )

    def get_budget_status(self) -> dict[str, Any]:
        """Get current budget status.

        Returns:
            Budget status information
        """
        self.budget.reset_if_needed()

        return {
            "enabled": self.budget.enabled,
            "period": self.budget.period.value,
            "limit": self.budget.limit,
            "current_usage": self.budget.current_usage,
            "remaining": self.budget.remaining(),
            "usage_percentage": self.budget.usage_percentage(),
            "is_warning": self.budget.is_warning(),
            "is_exceeded": self.budget.is_exceeded(),
            "hard_limit": self.budget.hard_limit,
            "period_start": self.budget.period_start.isoformat(),
        }

    def record_usage(
        self,
        model: str,
        task_type: TaskType,
        success: bool,
        latency_ms: float,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Record usage for a completed request.

        This updates model statistics and budget tracking.

        Args:
            model: Model that was used
            task_type: Type of task
            success: Whether request succeeded
            latency_ms: Response latency in milliseconds
            input_tokens: Input tokens used
            output_tokens: Output tokens used
        """
        # Update model stats
        if model in self.models:
            self.models[model].update_stats(success, latency_ms)

        # Update performance stats
        task_type_str = task_type.value
        stats = self._performance_stats[model][task_type_str]

        # Update success rate (exponential moving average)
        alpha = 0.1
        success_val = 1.0 if success else 0.0
        stats["success_rate"] = alpha * success_val + (1 - alpha) * stats["success_rate"]
        stats["avg_latency"] = alpha * latency_ms + (1 - alpha) * stats["avg_latency"]

        # Update budget
        if self.budget.enabled and model in self.models:
            cost = self.models[model].estimate_cost(input_tokens, output_tokens)
            self.budget.add_usage(cost)

            if self.budget.is_warning():
                logger.warning(
                    "Budget warning: %.1f%% used ($%.4f / $%.2f)",
                    self.budget.usage_percentage(),
                    self.budget.current_usage,
                    self.budget.limit,
                )

        logger.debug(
            "Recorded usage for %s: success=%s, latency=%.0fms, tokens=%d/%d",
            model,
            success,
            latency_ms,
            input_tokens,
            output_tokens,
        )

    def get_routing_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent routing history.

        Args:
            limit: Maximum entries to return

        Returns:
            List of routing history entries
        """
        history = self._routing_history[-limit:]
        return [
            {
                "model": h.decision.model,
                "strategy": h.decision.strategy_used.value,
                "task_type": h.task_type.value,
                "success": h.success,
                "actual_cost": h.actual_cost,
                "actual_latency_ms": h.actual_latency_ms,
                "timestamp": h.decision.timestamp.isoformat(),
            }
            for h in history
        ]

    def add_routing_history(
        self,
        decision: RoutingDecision,
        task_type: TaskType,
        success: bool,
        actual_cost: float,
        actual_latency_ms: float,
    ) -> None:
        """Add entry to routing history.

        Args:
            decision: The routing decision
            task_type: Type of task
            success: Whether request succeeded
            actual_cost: Actual cost incurred
            actual_latency_ms: Actual latency
        """
        entry = RoutingHistory(
            decision=decision,
            task_type=task_type,
            success=success,
            actual_cost=actual_cost,
            actual_latency_ms=actual_latency_ms,
        )
        self._routing_history.append(entry)

        # Trim history if too large
        if len(self._routing_history) > self._max_history_size:
            self._routing_history = self._routing_history[-self._max_history_size :]

    def recommend_model(
        self,
        task_content: str,
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get model recommendation with explanation.

        Args:
            task_content: Task content
            constraints: Optional constraints (max_cost, min_quality, etc.)

        Returns:
            Recommendation with explanation
        """
        constraints = constraints or {}

        # Analyze task
        analyzer = TaskAnalyzer()
        task_type = analyzer.analyze(task_content)
        complexity = analyzer.analyze_complexity(task_content)

        # Create task for routing
        _ = Task(content=task_content, task_type=task_type)

        # Get capable models
        capable_models = self._get_capable_models(task_type)

        # Apply constraints
        if "max_cost" in constraints:
            capable_models = [
                m
                for m in capable_models
                if self.models[m].cost_per_1k_input <= constraints["max_cost"]
            ]

        if "min_quality" in constraints:
            capable_models = [
                m
                for m in capable_models
                if self.models[m].quality_rating >= constraints["min_quality"]
            ]

        if "min_speed" in constraints:
            capable_models = [
                m for m in capable_models if self.models[m].speed_rating >= constraints["min_speed"]
            ]

        if "provider" in constraints:
            capable_models = [
                m for m in capable_models if self.models[m].provider == constraints["provider"]
            ]

        if not capable_models:
            return {
                "error": "No models match constraints",
                "task_type": task_type.value,
                "complexity": complexity,
            }

        # Score models
        recommendations: list[dict[str, Any]] = []
        for model in capable_models:
            info = self.models[model]
            score = (
                info.quality_rating * 0.4
                + info.speed_rating * 0.3
                + (1 / (1 + info.cost_per_1k_input * 100)) * 10 * 0.3
            )

            recommendations.append(
                {
                    "model": model,
                    "score": round(score, 2),
                    "provider": info.provider,
                    "quality_rating": info.quality_rating,
                    "speed_rating": info.speed_rating,
                    "cost_per_1k_input": info.cost_per_1k_input,
                    "estimated_cost": info.estimate_cost(
                        len(task_content.split()) * 2,
                        len(task_content.split()) * 2,
                    ),
                }
            )

        recommendations.sort(key=lambda x: x["score"], reverse=True)

        return {
            "task_type": task_type.value,
            "complexity": complexity,
            "suggested_strategy": analyzer.suggest_strategy(task_type, complexity).value,
            "top_recommendation": recommendations[0] if recommendations else None,
            "alternatives": recommendations[1:4],
            "all_candidates": len(recommendations),
        }

    def batch_route(
        self,
        tasks: list[Task],
        strategy: RoutingStrategy | None = None,
    ) -> list[tuple[Task, str]]:
        """Route multiple tasks efficiently.

        Args:
            tasks: List of tasks to route
            strategy: Optional strategy override

        Returns:
            List of (task, model) tuples
        """
        results: list[tuple[Task, str]] = []

        for task in tasks:
            if strategy:
                old_strategy = self.strategy
                self.strategy = strategy

            model = self.route(task)
            results.append((task, model))

            if strategy:
                self.strategy = old_strategy

        logger.info("Batch routed %d tasks", len(tasks))
        return results

    def setup_ab_test(
        self,
        test_models: list[str],
        ratio: float = 0.1,
    ) -> None:
        """Setup A/B testing for models.

        Args:
            test_models: Models to include in A/B test
            ratio: Ratio of requests to use for testing
        """
        self._ab_test_models = [m for m in test_models if m in self.models]
        self.ab_test_ratio = ratio
        self.enable_ab_testing = True

        # Reset test results
        self._ab_test_results = defaultdict(
            lambda: {"requests": 0, "successes": 0, "total_latency": 0.0}
        )

        logger.info(
            "A/B test setup: models=%s, ratio=%.1f%%",
            self._ab_test_models,
            ratio * 100,
        )

    def get_ab_test_results(self) -> dict[str, Any]:
        """Get A/B test results.

        Returns:
            Test results for each model
        """
        results = {}
        for model, stats in self._ab_test_results.items():
            requests = stats["requests"]
            if requests > 0:
                results[model] = {
                    "requests": requests,
                    "success_rate": stats["successes"] / requests,
                    "avg_latency_ms": stats["total_latency"] / requests,
                }

        return {
            "enabled": self.enable_ab_testing,
            "test_models": self._ab_test_models,
            "ratio": self.ab_test_ratio,
            "results": results,
        }

    def record_ab_test_result(
        self,
        model: str,
        success: bool,
        latency_ms: float,
    ) -> None:
        """Record A/B test result.

        Args:
            model: Model tested
            success: Whether request succeeded
            latency_ms: Response latency
        """
        if model in self._ab_test_models:
            self._ab_test_results[model]["requests"] += 1
            if success:
                self._ab_test_results[model]["successes"] += 1
            self._ab_test_results[model]["total_latency"] += latency_ms

    def get_models_by_tag(self, tag: str) -> list[str]:
        """Get models with a specific tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of model names with the tag
        """
        return [name for name, info in self.models.items() if info.enabled and tag in info.tags]

    def get_models_by_provider(self, provider: str) -> list[str]:
        """Get models from a specific provider.

        Args:
            provider: Provider name

        Returns:
            List of model names from the provider
        """
        return [
            name for name, info in self.models.items() if info.enabled and info.provider == provider
        ]

    def get_cheapest_model(self, task_type: TaskType | None = None) -> str:
        """Get the cheapest capable model.

        Args:
            task_type: Optional task type filter

        Returns:
            Cheapest model name
        """
        models = self._get_capable_models(task_type) if task_type else self._enabled_models
        if not models:
            return self.default_model
        return min(models, key=lambda m: self.models[m].cost_per_1k_input)

    def get_fastest_model(self, task_type: TaskType | None = None) -> str:
        """Get the fastest capable model.

        Args:
            task_type: Optional task type filter

        Returns:
            Fastest model name
        """
        models = self._get_capable_models(task_type) if task_type else self._enabled_models
        if not models:
            return self.default_model
        return max(models, key=lambda m: self.models[m].speed_rating)

    def get_best_quality_model(self, task_type: TaskType | None = None) -> str:
        """Get the highest quality capable model.

        Args:
            task_type: Optional task type filter

        Returns:
            Best quality model name
        """
        models = self._get_capable_models(task_type) if task_type else self._enabled_models
        if not models:
            return self.default_model
        return max(models, key=lambda m: self.models[m].quality_rating)


class TaskAnalyzer:
    """Analyzes tasks to determine their type and requirements.

    This class uses heuristics and optional AI analysis to classify
    tasks and determine the best routing strategy.
    """

    # Keywords for task type detection
    TASK_KEYWORDS: dict[TaskType, list[str]] = {
        TaskType.CODE: [
            "code",
            "program",
            "function",
            "class",
            "debug",
            "fix",
            "implement",
            "python",
            "javascript",
            "typescript",
            "java",
            "c++",
            "rust",
            "go",
            "sql",
            "api",
            "bug",
            "error",
            "exception",
        ],
        TaskType.SEARCH: [
            "search",
            "find",
            "look up",
            "what is",
            "who is",
            "where is",
            "when did",
            "latest",
            "news",
            "current",
        ],
        TaskType.ANALYSIS: [
            "analyze",
            "analysis",
            "compare",
            "evaluate",
            "assess",
            "review",
            "examine",
            "investigate",
            "study",
        ],
        TaskType.SUMMARY: [
            "summarize",
            "summary",
            "brief",
            "overview",
            "tldr",
            "key points",
            "main points",
            "condense",
        ],
        TaskType.TRANSLATION: [
            "translate",
            "translation",
            "convert to",
            "in english",
            "in chinese",
            "in spanish",
            "in french",
            "in german",
            "in japanese",
        ],
        TaskType.REASONING: [
            "why",
            "how does",
            "explain",
            "reason",
            "logic",
            "deduce",
            "infer",
            "conclude",
            "prove",
        ],
        TaskType.PLANNING: [
            "plan",
            "schedule",
            "organize",
            "steps",
            "roadmap",
            "strategy",
            "approach",
            "how to",
        ],
        TaskType.CREATIVE: [
            "write",
            "create",
            "compose",
            "story",
            "poem",
            "creative",
            "imagine",
            "design",
            "invent",
        ],
        TaskType.MATH: [
            "calculate",
            "compute",
            "math",
            "equation",
            "formula",
            "solve",
            "number",
            "percentage",
            "statistics",
        ],
    }

    def __init__(self) -> None:
        """Initialize the task analyzer."""
        logger.info("TaskAnalyzer initialized")

    def analyze(self, content: str) -> TaskType:
        """Analyze task content to determine its type.

        Args:
            content: Task content to analyze

        Returns:
            Detected task type
        """
        content_lower = content.lower()

        # Score each task type based on keyword matches
        scores: dict[TaskType, int] = {}

        for task_type, keywords in self.TASK_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in content_lower)
            if score > 0:
                scores[task_type] = score

        if scores:
            # Return task type with highest score
            best_type = max(scores, key=lambda t: scores[t])
            logger.debug(
                "Analyzed task type: %s (score: %d)",
                best_type.value,
                scores[best_type],
            )
            return best_type

        # Default to general conversation
        return TaskType.CONVERSATION

    def analyze_complexity(self, content: str) -> int:
        """Analyze task complexity (1-10).

        Args:
            content: Task content

        Returns:
            Complexity score (1-10)
        """
        # Simple heuristics for complexity
        complexity = 5  # Base complexity

        # Length factor
        word_count = len(content.split())
        if word_count > 200:
            complexity += 2
        elif word_count > 100:
            complexity += 1
        elif word_count < 20:
            complexity -= 1

        # Technical indicators
        technical_terms = [
            "algorithm",
            "architecture",
            "optimization",
            "performance",
            "scalability",
            "concurrent",
            "distributed",
            "machine learning",
            "neural network",
        ]
        if any(term in content.lower() for term in technical_terms):
            complexity += 2

        # Multi-step indicators
        if any(
            phrase in content.lower()
            for phrase in ["step by step", "multiple", "several", "various"]
        ):
            complexity += 1

        return max(1, min(10, complexity))

    def suggest_strategy(self, task_type: TaskType, complexity: int) -> RoutingStrategy:
        """Suggest a routing strategy based on task analysis.

        Args:
            task_type: Type of task
            complexity: Task complexity (1-10)

        Returns:
            Suggested routing strategy
        """
        # High complexity tasks need quality
        if complexity >= 8:
            return RoutingStrategy.QUALITY_OPTIMIZED

        # Code tasks benefit from quality models
        if task_type == TaskType.CODE:
            return RoutingStrategy.QUALITY_OPTIMIZED

        # Simple tasks can use cost optimization
        if complexity <= 3:
            return RoutingStrategy.COST_OPTIMIZED

        # Default to balanced
        return RoutingStrategy.BALANCED
