"""Base types and models for multi-agent system.

This module provides foundational types, models, and enums used throughout
the multi-agent orchestration system.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from ...core.logger import get_logger

logger = get_logger("ai.multi_agent.base")


class TaskType(str, Enum):
    """Types of tasks that can be processed by agents."""

    GENERAL = "general"
    SEARCH = "search"
    ANALYSIS = "analysis"
    CODE = "code"
    SUMMARY = "summary"
    TRANSLATION = "translation"
    REASONING = "reasoning"
    PLANNING = "planning"
    CREATIVE = "creative"
    MATH = "math"
    CONVERSATION = "conversation"


class TaskPriority(str, Enum):
    """Priority levels for tasks."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Status of a task in the execution pipeline."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentCapability(str, Enum):
    """Capabilities that agents can have."""

    SEARCH = "search"
    ANALYSIS = "analysis"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    REASONING = "reasoning"
    PLANNING = "planning"
    CREATIVE_WRITING = "creative_writing"
    MATH = "math"
    CONVERSATION = "conversation"
    DATA_EXTRACTION = "data_extraction"


class RoutingStrategy(str, Enum):
    """Strategies for routing tasks to models."""

    COST_OPTIMIZED = "cost_optimized"
    SPEED_OPTIMIZED = "speed_optimized"
    QUALITY_OPTIMIZED = "quality_optimized"
    BALANCED = "balanced"
    ROUND_ROBIN = "round_robin"
    CAPABILITY_BASED = "capability_based"
    CONTEXT_AWARE = "context_aware"
    ADAPTIVE = "adaptive"
    BUDGET_AWARE = "budget_aware"
    LATENCY_OPTIMIZED = "latency_optimized"


class AgentMessage(BaseModel):
    """Message passed between agents.

    Attributes:
        id: Unique message identifier
        from_agent: Name of the sending agent
        to_agent: Name of the receiving agent
        content: Message content
        message_type: Type of message (request, response, notification)
        metadata: Additional metadata
        timestamp: When the message was created
    """

    id: str = Field(default_factory=lambda: f"msg_{datetime.now().timestamp()}")
    from_agent: str = Field(description="Sending agent name")
    to_agent: str = Field(description="Receiving agent name")
    content: str = Field(description="Message content")
    message_type: Literal["request", "response", "notification"] = Field(
        default="request",
        description="Type of message",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Message timestamp",
    )


class AgentResult(BaseModel):
    """Result from an agent execution.

    Attributes:
        agent_name: Name of the agent
        output: Agent output
        success: Whether execution was successful
        error: Error message if failed
        execution_time_ms: Execution time in milliseconds
        tokens_used: Number of tokens used
        metadata: Additional metadata
    """

    agent_name: str = Field(description="Agent name")
    output: str = Field(description="Agent output")
    success: bool = Field(default=True, description="Success status")
    error: str | None = Field(default=None, description="Error message")
    execution_time_ms: float = Field(default=0.0, description="Execution time in ms")
    tokens_used: int = Field(default=0, description="Tokens used")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class Task(BaseModel):
    """A task to be processed by the multi-agent system.

    Attributes:
        id: Unique task identifier
        content: Task content/description
        task_type: Type of task
        priority: Task priority
        status: Current status
        assigned_agent: Agent assigned to this task
        assigned_model: Model assigned to this task
        parent_task_id: Parent task ID for subtasks
        subtask_ids: IDs of subtasks
        context: Additional context for the task
        result: Task result when completed
        created_at: When the task was created
        started_at: When execution started
        completed_at: When execution completed
    """

    id: str = Field(default_factory=lambda: f"task_{datetime.now().timestamp()}")
    content: str = Field(description="Task content")
    task_type: TaskType = Field(default=TaskType.GENERAL, description="Task type")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Priority")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Status")
    assigned_agent: str | None = Field(default=None, description="Assigned agent")
    assigned_model: str | None = Field(default=None, description="Assigned model")
    parent_task_id: str | None = Field(default=None, description="Parent task ID")
    subtask_ids: list[str] = Field(default_factory=list, description="Subtask IDs")
    context: dict[str, Any] = Field(default_factory=dict, description="Task context")
    result: AgentResult | None = Field(default=None, description="Task result")
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    def mark_started(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()

    def mark_completed(self, result: AgentResult) -> None:
        """Mark task as completed with result."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result = result

    def mark_failed(self, error: str) -> None:
        """Mark task as failed with error."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.result = AgentResult(
            agent_name=self.assigned_agent or "unknown",
            output="",
            success=False,
            error=error,
        )


class ExecutionPlan(BaseModel):
    """An execution plan for processing a complex task.

    Attributes:
        id: Unique plan identifier
        original_task: The original task to be processed
        steps: List of execution steps
        current_step: Index of current step
        status: Plan status
        created_at: When the plan was created
    """

    id: str = Field(default_factory=lambda: f"plan_{datetime.now().timestamp()}")
    original_task: Task = Field(description="Original task")
    steps: list[Task] = Field(default_factory=list, description="Execution steps")
    current_step: int = Field(default=0, description="Current step index")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Plan status")
    created_at: datetime = Field(default_factory=datetime.now)

    def get_current_step(self) -> Task | None:
        """Get the current step task."""
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None

    def advance_step(self) -> bool:
        """Advance to the next step. Returns True if there are more steps."""
        self.current_step += 1
        return self.current_step < len(self.steps)

    def is_complete(self) -> bool:
        """Check if all steps are complete."""
        return all(step.status == TaskStatus.COMPLETED for step in self.steps)


class ModelHealth(str, Enum):
    """Health status of a model."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ModelInfo(BaseModel):
    """Information about an AI model.

    Attributes:
        name: Model name (e.g., "openai:gpt-4o")
        provider: Provider name (e.g., "openai")
        capabilities: List of capabilities
        cost_per_1k_input: Cost per 1000 input tokens
        cost_per_1k_output: Cost per 1000 output tokens
        max_tokens: Maximum context tokens
        speed_rating: Speed rating (1-10, higher is faster)
        quality_rating: Quality rating (1-10, higher is better)
        latency_ms: Average latency in milliseconds
        enabled: Whether the model is enabled
        health: Current health status
        success_rate: Historical success rate (0.0-1.0)
        avg_response_time_ms: Average response time in milliseconds
        total_requests: Total number of requests made
        failed_requests: Number of failed requests
        last_used: Timestamp of last use
        last_health_check: Timestamp of last health check
        tags: Custom tags for filtering
    """

    name: str = Field(description="Model name")
    provider: str = Field(description="Provider name")
    capabilities: list[AgentCapability] = Field(
        default_factory=list,
        description="Model capabilities",
    )
    cost_per_1k_input: float = Field(default=0.0, description="Cost per 1K input tokens")
    cost_per_1k_output: float = Field(default=0.0, description="Cost per 1K output tokens")
    max_tokens: int = Field(default=128000, description="Max context tokens")
    speed_rating: int = Field(default=5, ge=1, le=10, description="Speed rating")
    quality_rating: int = Field(default=5, ge=1, le=10, description="Quality rating")
    latency_ms: float = Field(default=1000.0, description="Average latency in ms")
    enabled: bool = Field(default=True, description="Whether enabled")
    health: ModelHealth = Field(default=ModelHealth.UNKNOWN, description="Health status")
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="Success rate")
    avg_response_time_ms: float = Field(default=0.0, description="Avg response time in ms")
    total_requests: int = Field(default=0, description="Total requests")
    failed_requests: int = Field(default=0, description="Failed requests")
    last_used: datetime | None = Field(default=None, description="Last used timestamp")
    last_health_check: datetime | None = Field(default=None, description="Last health check")
    tags: list[str] = Field(default_factory=list, description="Custom tags")

    def update_stats(self, success: bool, response_time_ms: float) -> None:
        """Update model statistics after a request.

        Args:
            success: Whether the request was successful
            response_time_ms: Response time in milliseconds
        """
        self.total_requests += 1
        if not success:
            self.failed_requests += 1

        # Update success rate
        if self.total_requests > 0:
            self.success_rate = 1.0 - (self.failed_requests / self.total_requests)

        # Update average response time (exponential moving average)
        alpha = 0.2  # Smoothing factor
        if self.avg_response_time_ms == 0:
            self.avg_response_time_ms = response_time_ms
        else:
            self.avg_response_time_ms = (
                alpha * response_time_ms + (1 - alpha) * self.avg_response_time_ms
            )

        self.last_used = datetime.now()

        # Update health based on success rate
        if self.success_rate >= 0.95:
            self.health = ModelHealth.HEALTHY
        elif self.success_rate >= 0.8:
            self.health = ModelHealth.DEGRADED
        else:
            self.health = ModelHealth.UNHEALTHY

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a request.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in dollars
        """
        return (input_tokens / 1000) * self.cost_per_1k_input + (
            output_tokens / 1000
        ) * self.cost_per_1k_output


class AgentInfo(BaseModel):
    """Information about a specialized agent.

    Attributes:
        name: Agent name
        role: Agent role
        capabilities: List of capabilities
        preferred_model: Preferred model for this agent
        description: Agent description
        enabled: Whether the agent is enabled
    """

    name: str = Field(description="Agent name")
    role: str = Field(description="Agent role")
    capabilities: list[AgentCapability] = Field(
        default_factory=list,
        description="Agent capabilities",
    )
    preferred_model: str | None = Field(default=None, description="Preferred model")
    description: str = Field(default="", description="Agent description")
    enabled: bool = Field(default=True, description="Whether enabled")


# Default model configurations
DEFAULT_MODELS: dict[str, ModelInfo] = {
    "openai:gpt-4o": ModelInfo(
        name="openai:gpt-4o",
        provider="openai",
        capabilities=[
            AgentCapability.SEARCH,
            AgentCapability.ANALYSIS,
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.SUMMARIZATION,
            AgentCapability.TRANSLATION,
            AgentCapability.REASONING,
            AgentCapability.PLANNING,
            AgentCapability.CREATIVE_WRITING,
            AgentCapability.MATH,
            AgentCapability.CONVERSATION,
            AgentCapability.DATA_EXTRACTION,
        ],
        cost_per_1k_input=0.0025,
        cost_per_1k_output=0.01,
        max_tokens=128000,
        speed_rating=8,
        quality_rating=9,
    ),
    "openai:gpt-4o-mini": ModelInfo(
        name="openai:gpt-4o-mini",
        provider="openai",
        capabilities=[
            AgentCapability.SEARCH,
            AgentCapability.ANALYSIS,
            AgentCapability.CODE_GENERATION,
            AgentCapability.SUMMARIZATION,
            AgentCapability.TRANSLATION,
            AgentCapability.CONVERSATION,
        ],
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
        max_tokens=128000,
        speed_rating=9,
        quality_rating=7,
    ),
    "anthropic:claude-3-5-sonnet-20241022": ModelInfo(
        name="anthropic:claude-3-5-sonnet-20241022",
        provider="anthropic",
        capabilities=[
            AgentCapability.SEARCH,
            AgentCapability.ANALYSIS,
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.SUMMARIZATION,
            AgentCapability.TRANSLATION,
            AgentCapability.REASONING,
            AgentCapability.PLANNING,
            AgentCapability.CREATIVE_WRITING,
            AgentCapability.MATH,
            AgentCapability.CONVERSATION,
            AgentCapability.DATA_EXTRACTION,
        ],
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        max_tokens=200000,
        speed_rating=7,
        quality_rating=10,
    ),
    "anthropic:claude-3-5-haiku-20241022": ModelInfo(
        name="anthropic:claude-3-5-haiku-20241022",
        provider="anthropic",
        capabilities=[
            AgentCapability.SEARCH,
            AgentCapability.ANALYSIS,
            AgentCapability.CODE_GENERATION,
            AgentCapability.SUMMARIZATION,
            AgentCapability.TRANSLATION,
            AgentCapability.CONVERSATION,
        ],
        cost_per_1k_input=0.001,
        cost_per_1k_output=0.005,
        max_tokens=200000,
        speed_rating=9,
        quality_rating=7,
    ),
    "google:gemini-2.0-flash": ModelInfo(
        name="google:gemini-2.0-flash",
        provider="google",
        capabilities=[
            AgentCapability.SEARCH,
            AgentCapability.ANALYSIS,
            AgentCapability.CODE_GENERATION,
            AgentCapability.SUMMARIZATION,
            AgentCapability.TRANSLATION,
            AgentCapability.REASONING,
            AgentCapability.CONVERSATION,
        ],
        cost_per_1k_input=0.0001,
        cost_per_1k_output=0.0004,
        max_tokens=1000000,
        speed_rating=10,
        quality_rating=8,
    ),
    "groq:llama-3.3-70b-versatile": ModelInfo(
        name="groq:llama-3.3-70b-versatile",
        provider="groq",
        capabilities=[
            AgentCapability.SEARCH,
            AgentCapability.ANALYSIS,
            AgentCapability.CODE_GENERATION,
            AgentCapability.SUMMARIZATION,
            AgentCapability.CONVERSATION,
        ],
        cost_per_1k_input=0.00059,
        cost_per_1k_output=0.00079,
        max_tokens=128000,
        speed_rating=10,
        quality_rating=7,
    ),
    # DeepSeek models
    "deepseek:deepseek-chat": ModelInfo(
        name="deepseek:deepseek-chat",
        provider="deepseek",
        capabilities=[
            AgentCapability.SEARCH,
            AgentCapability.ANALYSIS,
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.SUMMARIZATION,
            AgentCapability.TRANSLATION,
            AgentCapability.REASONING,
            AgentCapability.CONVERSATION,
        ],
        cost_per_1k_input=0.00014,
        cost_per_1k_output=0.00028,
        max_tokens=64000,
        speed_rating=8,
        quality_rating=8,
        latency_ms=800,
        tags=["chinese", "coding"],
    ),
    "deepseek:deepseek-reasoner": ModelInfo(
        name="deepseek:deepseek-reasoner",
        provider="deepseek",
        capabilities=[
            AgentCapability.REASONING,
            AgentCapability.MATH,
            AgentCapability.CODE_GENERATION,
            AgentCapability.ANALYSIS,
            AgentCapability.PLANNING,
        ],
        cost_per_1k_input=0.00055,
        cost_per_1k_output=0.00219,
        max_tokens=64000,
        speed_rating=5,
        quality_rating=10,
        latency_ms=3000,
        tags=["reasoning", "math", "o1-like"],
    ),
    # Qwen models
    "qwen:qwen-max": ModelInfo(
        name="qwen:qwen-max",
        provider="qwen",
        capabilities=[
            AgentCapability.SEARCH,
            AgentCapability.ANALYSIS,
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.SUMMARIZATION,
            AgentCapability.TRANSLATION,
            AgentCapability.REASONING,
            AgentCapability.CREATIVE_WRITING,
            AgentCapability.CONVERSATION,
        ],
        cost_per_1k_input=0.0016,
        cost_per_1k_output=0.0064,
        max_tokens=32000,
        speed_rating=7,
        quality_rating=9,
        latency_ms=1200,
        tags=["chinese", "multilingual"],
    ),
    "qwen:qwen-turbo": ModelInfo(
        name="qwen:qwen-turbo",
        provider="qwen",
        capabilities=[
            AgentCapability.SEARCH,
            AgentCapability.ANALYSIS,
            AgentCapability.CODE_GENERATION,
            AgentCapability.SUMMARIZATION,
            AgentCapability.TRANSLATION,
            AgentCapability.CONVERSATION,
        ],
        cost_per_1k_input=0.0003,
        cost_per_1k_output=0.0006,
        max_tokens=128000,
        speed_rating=9,
        quality_rating=7,
        latency_ms=500,
        tags=["chinese", "fast"],
    ),
    # Mistral models
    "mistral:mistral-large": ModelInfo(
        name="mistral:mistral-large",
        provider="mistral",
        capabilities=[
            AgentCapability.SEARCH,
            AgentCapability.ANALYSIS,
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.SUMMARIZATION,
            AgentCapability.TRANSLATION,
            AgentCapability.REASONING,
            AgentCapability.CONVERSATION,
        ],
        cost_per_1k_input=0.002,
        cost_per_1k_output=0.006,
        max_tokens=128000,
        speed_rating=7,
        quality_rating=9,
        latency_ms=1000,
        tags=["european", "multilingual"],
    ),
    "mistral:mistral-small": ModelInfo(
        name="mistral:mistral-small",
        provider="mistral",
        capabilities=[
            AgentCapability.SEARCH,
            AgentCapability.ANALYSIS,
            AgentCapability.CODE_GENERATION,
            AgentCapability.SUMMARIZATION,
            AgentCapability.CONVERSATION,
        ],
        cost_per_1k_input=0.0002,
        cost_per_1k_output=0.0006,
        max_tokens=128000,
        speed_rating=9,
        quality_rating=7,
        latency_ms=400,
        tags=["fast", "efficient"],
    ),
    # Cohere models
    "cohere:command-r-plus": ModelInfo(
        name="cohere:command-r-plus",
        provider="cohere",
        capabilities=[
            AgentCapability.SEARCH,
            AgentCapability.ANALYSIS,
            AgentCapability.SUMMARIZATION,
            AgentCapability.TRANSLATION,
            AgentCapability.REASONING,
            AgentCapability.CONVERSATION,
            AgentCapability.DATA_EXTRACTION,
        ],
        cost_per_1k_input=0.0025,
        cost_per_1k_output=0.01,
        max_tokens=128000,
        speed_rating=7,
        quality_rating=8,
        latency_ms=1200,
        tags=["rag", "enterprise"],
    ),
    "cohere:command-r": ModelInfo(
        name="cohere:command-r",
        provider="cohere",
        capabilities=[
            AgentCapability.SEARCH,
            AgentCapability.ANALYSIS,
            AgentCapability.SUMMARIZATION,
            AgentCapability.CONVERSATION,
        ],
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
        max_tokens=128000,
        speed_rating=9,
        quality_rating=7,
        latency_ms=600,
        tags=["rag", "fast"],
    ),
    # OpenAI o1 models
    "openai:o1": ModelInfo(
        name="openai:o1",
        provider="openai",
        capabilities=[
            AgentCapability.REASONING,
            AgentCapability.MATH,
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.ANALYSIS,
            AgentCapability.PLANNING,
        ],
        cost_per_1k_input=0.015,
        cost_per_1k_output=0.06,
        max_tokens=200000,
        speed_rating=3,
        quality_rating=10,
        latency_ms=5000,
        tags=["reasoning", "math", "complex"],
    ),
    "openai:o1-mini": ModelInfo(
        name="openai:o1-mini",
        provider="openai",
        capabilities=[
            AgentCapability.REASONING,
            AgentCapability.MATH,
            AgentCapability.CODE_GENERATION,
            AgentCapability.ANALYSIS,
        ],
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.012,
        max_tokens=128000,
        speed_rating=5,
        quality_rating=9,
        latency_ms=3000,
        tags=["reasoning", "math", "efficient"],
    ),
}


class BudgetPeriod(str, Enum):
    """Budget period types."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class BudgetConfig(BaseModel):
    """Budget configuration for cost management.

    Attributes:
        enabled: Whether budget tracking is enabled
        period: Budget period (hourly, daily, weekly, monthly)
        limit: Budget limit in dollars
        warning_threshold: Percentage of budget to trigger warning (0.0-1.0)
        hard_limit: Whether to block requests when budget exceeded
        current_usage: Current usage in the period
        period_start: Start of current budget period
    """

    enabled: bool = Field(default=False, description="Enable budget tracking")
    period: BudgetPeriod = Field(default=BudgetPeriod.DAILY, description="Budget period")
    limit: float = Field(default=10.0, ge=0.0, description="Budget limit in dollars")
    warning_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="Warning threshold")
    hard_limit: bool = Field(default=False, description="Block when exceeded")
    current_usage: float = Field(default=0.0, ge=0.0, description="Current usage")
    period_start: datetime = Field(default_factory=datetime.now, description="Period start")

    def add_usage(self, cost: float) -> None:
        """Add usage to current period.

        Args:
            cost: Cost to add in dollars
        """
        self.current_usage += cost

    def reset_if_needed(self) -> bool:
        """Reset budget if period has elapsed.

        Returns:
            True if budget was reset
        """
        now = datetime.now()
        should_reset = False

        if self.period == BudgetPeriod.HOURLY:
            should_reset = (now - self.period_start).total_seconds() >= 3600
        elif self.period == BudgetPeriod.DAILY:
            should_reset = (now - self.period_start).days >= 1
        elif self.period == BudgetPeriod.WEEKLY:
            should_reset = (now - self.period_start).days >= 7
        elif self.period == BudgetPeriod.MONTHLY:
            should_reset = (now - self.period_start).days >= 30

        if should_reset:
            self.current_usage = 0.0
            self.period_start = now
            return True
        return False

    def is_exceeded(self) -> bool:
        """Check if budget is exceeded.

        Returns:
            True if budget exceeded
        """
        return self.current_usage >= self.limit

    def is_warning(self) -> bool:
        """Check if budget warning threshold reached.

        Returns:
            True if warning threshold reached
        """
        return self.current_usage >= (self.limit * self.warning_threshold)

    def remaining(self) -> float:
        """Get remaining budget.

        Returns:
            Remaining budget in dollars
        """
        return max(0.0, self.limit - self.current_usage)

    def usage_percentage(self) -> float:
        """Get usage percentage.

        Returns:
            Usage as percentage (0.0-100.0)
        """
        if self.limit == 0:
            return 100.0
        return (self.current_usage / self.limit) * 100


class RoutingContext(BaseModel):
    """Context information for intelligent routing decisions.

    Attributes:
        user_id: User identifier
        conversation_id: Conversation identifier
        message_count: Number of messages in conversation
        avg_message_length: Average message length
        task_history: Recent task types
        preferred_models: User's preferred models
        language: Detected language
        urgency: Task urgency level (1-10)
        custom_context: Additional custom context
    """

    user_id: str | None = Field(default=None, description="User ID")
    conversation_id: str | None = Field(default=None, description="Conversation ID")
    message_count: int = Field(default=0, description="Message count")
    avg_message_length: float = Field(default=0.0, description="Avg message length")
    task_history: list[TaskType] = Field(default_factory=list, description="Task history")
    preferred_models: list[str] = Field(default_factory=list, description="Preferred models")
    language: str = Field(default="en", description="Detected language")
    urgency: int = Field(default=5, ge=1, le=10, description="Urgency level")
    custom_context: dict[str, Any] = Field(default_factory=dict, description="Custom context")


class RoutingDecision(BaseModel):
    """Result of a routing decision.

    Attributes:
        model: Selected model name
        strategy_used: Strategy that was used
        score: Routing score
        alternatives: Alternative models considered
        reason: Reason for selection
        estimated_cost: Estimated cost for the task
        estimated_latency_ms: Estimated latency in milliseconds
        confidence: Confidence in the decision (0.0-1.0)
        timestamp: When the decision was made
    """

    model: str = Field(description="Selected model")
    strategy_used: RoutingStrategy = Field(description="Strategy used")
    score: float = Field(default=0.0, description="Routing score")
    alternatives: list[str] = Field(default_factory=list, description="Alternative models")
    reason: str = Field(default="", description="Selection reason")
    estimated_cost: float = Field(default=0.0, description="Estimated cost")
    estimated_latency_ms: float = Field(default=0.0, description="Estimated latency")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp")


class RoutingHistory(BaseModel):
    """History entry for routing decisions.

    Attributes:
        decision: The routing decision made
        task_type: Type of task
        actual_cost: Actual cost incurred
        actual_latency_ms: Actual latency
        success: Whether the request succeeded
        feedback_score: Optional user feedback score
    """

    decision: RoutingDecision = Field(description="Routing decision")
    task_type: TaskType = Field(description="Task type")
    actual_cost: float = Field(default=0.0, description="Actual cost")
    actual_latency_ms: float = Field(default=0.0, description="Actual latency")
    success: bool = Field(default=True, description="Success status")
    feedback_score: float | None = Field(default=None, description="User feedback")
