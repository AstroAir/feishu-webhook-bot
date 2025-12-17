"""Multi-agent orchestration module for A2A (Agent-to-Agent) communication.

This module provides a comprehensive multi-agent system with:
- Specialized agents for different task types
- Intelligent model routing
- Task planning and decomposition
- Multiple orchestration modes

Example:
    ```python
    from feishu_webhook_bot.ai.multi_agent import (
        AgentOrchestrator,
        ModelRouter,
        TaskPlanner,
    )

    # Create orchestrator
    orchestrator = AgentOrchestrator(config, model="openai:gpt-4o")

    # Orchestrate a task
    response = await orchestrator.orchestrate("Analyze this data...")

    # Or use model routing directly
    router = ModelRouter(strategy=RoutingStrategy.BALANCED)
    model = router.route(task)
    ```
"""

from .agents import (
    AGENT_REGISTRY,
    AnalysisAgent,
    CodeAgent,
    CreativeAgent,
    MathAgent,
    PlanningAgent,
    ReasoningAgent,
    ResponseAgent,
    SearchAgent,
    SpecializedAgent,
    SummaryAgent,
    TranslationAgent,
    create_agent,
    get_available_roles,
)
from .base import (
    DEFAULT_MODELS,
    AgentCapability,
    AgentInfo,
    AgentMessage,
    AgentResult,
    BudgetConfig,
    BudgetPeriod,
    ExecutionPlan,
    ModelHealth,
    ModelInfo,
    RoutingContext,
    RoutingDecision,
    RoutingHistory,
    RoutingStrategy,
    Task,
    TaskPriority,
    TaskStatus,
    TaskType,
)
from .orchestrator import AgentOrchestrator
from .planner import DependencyResolver, TaskPlanner
from .router import ModelRouter, TaskAnalyzer

__all__ = [
    # Orchestrator
    "AgentOrchestrator",
    # Agents
    "SpecializedAgent",
    "SearchAgent",
    "AnalysisAgent",
    "ResponseAgent",
    "CodeAgent",
    "SummaryAgent",
    "TranslationAgent",
    "ReasoningAgent",
    "PlanningAgent",
    "CreativeAgent",
    "MathAgent",
    "AGENT_REGISTRY",
    "create_agent",
    "get_available_roles",
    # Router
    "ModelRouter",
    "TaskAnalyzer",
    # Planner
    "TaskPlanner",
    "DependencyResolver",
    # Base types
    "AgentMessage",
    "AgentResult",
    "Task",
    "TaskType",
    "TaskPriority",
    "TaskStatus",
    "ExecutionPlan",
    "AgentCapability",
    "RoutingStrategy",
    "ModelInfo",
    "ModelHealth",
    "AgentInfo",
    "DEFAULT_MODELS",
    # Budget and routing
    "BudgetConfig",
    "BudgetPeriod",
    "RoutingContext",
    "RoutingDecision",
    "RoutingHistory",
]
