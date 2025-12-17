"""Configuration for AI features."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .persona import PersonaConfig


class ModelProviderConfig(BaseModel):
    """Provider-specific configuration for AI models.

    Attributes:
        provider: Model provider name (openai, anthropic, google, groq, cohere, ollama)
        base_url: Custom base URL for the provider API (useful for Ollama or proxies)
        api_version: API version to use (provider-specific)
        organization_id: Organization ID (for OpenAI)
        timeout: Request timeout in seconds
        max_retries: Maximum number of retries for failed requests
        additional_headers: Additional HTTP headers to send with requests
        additional_params: Additional parameters to pass to the model
    """

    provider: Literal["openai", "anthropic", "google", "groq", "cohere", "ollama"] | None = Field(
        default=None,
        description="Model provider (auto-detected from model string if not specified)",
    )
    base_url: str | None = Field(
        default=None,
        description="Custom base URL for provider API (e.g., for Ollama: http://localhost:11434/v1)",
    )
    api_version: str | None = Field(
        default=None,
        description="API version to use (provider-specific)",
    )
    organization_id: str | None = Field(
        default=None,
        description="Organization ID (for OpenAI)",
    )
    timeout: float = Field(
        default=60.0,
        ge=1.0,
        description="Request timeout in seconds",
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Maximum retries for failed requests",
    )
    additional_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Additional HTTP headers",
    )
    additional_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional model parameters",
    )


class SearchProviderConfig(BaseModel):
    """Configuration for a search provider.

    Attributes:
        provider: Provider type (duckduckgo, tavily, exa, brave, bing, google)
        enabled: Whether this provider is enabled
        api_key: API key for the provider (if required)
        priority: Priority order (lower = higher priority)
        options: Provider-specific options
    """

    provider: str = Field(
        ...,
        description="Provider type (duckduckgo, tavily, exa, brave, bing, google)",
    )
    enabled: bool = Field(default=True, description="Enable this provider")
    api_key: str | None = Field(
        default=None,
        description="API key for the provider (if required)",
    )
    priority: int = Field(
        default=100,
        ge=0,
        description="Priority order (lower = higher priority)",
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific options",
    )


class WebSearchConfig(BaseModel):
    """Configuration for web search capabilities.

    Attributes:
        enabled: Whether web search is enabled
        default_provider: Default search provider to use
        max_results: Maximum number of search results
        cache_enabled: Whether to cache search results
        cache_ttl_minutes: Cache TTL in minutes
        enable_failover: Whether to failover to backup providers
        concurrent_search: Whether to search multiple providers concurrently
        providers: List of search provider configurations
    """

    enabled: bool = Field(default=True, description="Enable web search")
    default_provider: str = Field(
        default="duckduckgo",
        description="Default search provider",
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of search results",
    )
    cache_enabled: bool = Field(
        default=True,
        description="Enable search result caching",
    )
    cache_ttl_minutes: int = Field(
        default=60,
        ge=1,
        le=1440,
        description="Cache TTL in minutes",
    )
    enable_failover: bool = Field(
        default=True,
        description="Failover to backup providers on failure",
    )
    concurrent_search: bool = Field(
        default=False,
        description="Search multiple providers concurrently",
    )
    providers: list[SearchProviderConfig] = Field(
        default_factory=lambda: [
            SearchProviderConfig(provider="duckduckgo", priority=0),
        ],
        description="List of search provider configurations",
    )


class MCPConfig(BaseModel):
    """Configuration for Model Context Protocol (MCP) support.

    Attributes:
        enabled: Whether MCP support is enabled
        servers: List of MCP server configurations
        timeout_seconds: Timeout for MCP server connections
    """

    enabled: bool = Field(default=False, description="Enable MCP support")
    servers: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of MCP server configurations (name, command, args)",
    )
    timeout_seconds: int = Field(
        default=30,
        ge=1,
        description="Timeout for MCP server connections",
    )


class BudgetTrackingConfig(BaseModel):
    """Configuration for budget tracking and cost management.

    Attributes:
        enabled: Whether budget tracking is enabled
        period: Budget period (hourly, daily, weekly, monthly)
        limit: Budget limit in dollars
        warning_threshold: Percentage of budget to trigger warning (0.0-1.0)
        hard_limit: Whether to block requests when budget exceeded
        notify_on_warning: Whether to send notifications on warning
        notify_on_exceeded: Whether to send notifications when exceeded
    """

    enabled: bool = Field(default=False, description="Enable budget tracking")
    period: Literal["hourly", "daily", "weekly", "monthly"] = Field(
        default="daily",
        description="Budget period",
    )
    limit: float = Field(
        default=10.0,
        ge=0.0,
        description="Budget limit in dollars",
    )
    warning_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Warning threshold (0.0-1.0)",
    )
    hard_limit: bool = Field(
        default=False,
        description="Block requests when budget exceeded",
    )
    notify_on_warning: bool = Field(
        default=True,
        description="Send notification on warning",
    )
    notify_on_exceeded: bool = Field(
        default=True,
        description="Send notification when exceeded",
    )


class HealthCheckConfig(BaseModel):
    """Configuration for model health monitoring.

    Attributes:
        enabled: Whether health checking is enabled
        check_interval_seconds: Interval between health checks
        unhealthy_threshold: Number of failures before marking unhealthy
        recovery_threshold: Number of successes before marking healthy
        auto_disable_unhealthy: Automatically disable unhealthy models
        failover_enabled: Enable automatic failover to healthy models
    """

    enabled: bool = Field(default=True, description="Enable health checking")
    check_interval_seconds: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Interval between health checks in seconds",
    )
    unhealthy_threshold: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Failures before marking unhealthy",
    )
    recovery_threshold: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Successes before marking healthy",
    )
    auto_disable_unhealthy: bool = Field(
        default=False,
        description="Auto-disable unhealthy models",
    )
    failover_enabled: bool = Field(
        default=True,
        description="Enable automatic failover",
    )


class ABTestConfig(BaseModel):
    """Configuration for A/B testing of models.

    Attributes:
        enabled: Whether A/B testing is enabled
        test_ratio: Ratio of requests to use for testing (0.0-1.0)
        test_models: List of models to include in A/B test
        min_samples: Minimum samples before drawing conclusions
        auto_promote: Automatically promote winning model
    """

    enabled: bool = Field(default=False, description="Enable A/B testing")
    test_ratio: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="Ratio of requests for testing",
    )
    test_models: list[str] = Field(
        default_factory=list,
        description="Models to include in A/B test",
    )
    min_samples: int = Field(
        default=100,
        ge=10,
        description="Minimum samples before conclusions",
    )
    auto_promote: bool = Field(
        default=False,
        description="Auto-promote winning model",
    )


class ModelRouterConfig(BaseModel):
    """Configuration for automatic model routing.

    Attributes:
        enabled: Whether model routing is enabled
        strategy: Routing strategy to use
        default_model: Default model when routing fails
        cost_threshold: Maximum cost per 1K tokens for cost-optimized routing
        min_speed_rating: Minimum speed rating for speed-optimized routing
        min_quality_rating: Minimum quality rating for quality-optimized routing
        budget: Budget tracking configuration
        health_check: Health check configuration
        ab_test: A/B testing configuration
        language_routing: Enable language-based model routing
        adaptive_learning: Enable adaptive routing based on performance
    """

    enabled: bool = Field(default=True, description="Enable model routing")
    strategy: Literal[
        "cost_optimized",
        "speed_optimized",
        "quality_optimized",
        "balanced",
        "round_robin",
        "capability_based",
        "context_aware",
        "adaptive",
        "budget_aware",
        "latency_optimized",
    ] = Field(
        default="balanced",
        description="Routing strategy",
    )
    default_model: str = Field(
        default="openai:gpt-4o",
        description="Default model when routing fails",
    )
    cost_threshold: float = Field(
        default=0.01,
        ge=0.0,
        description="Max cost per 1K tokens for cost-optimized routing",
    )
    min_speed_rating: int = Field(
        default=7,
        ge=1,
        le=10,
        description="Min speed rating for speed-optimized routing",
    )
    min_quality_rating: int = Field(
        default=8,
        ge=1,
        le=10,
        description="Min quality rating for quality-optimized routing",
    )
    budget: BudgetTrackingConfig = Field(
        default_factory=BudgetTrackingConfig,
        description="Budget tracking configuration",
    )
    health_check: HealthCheckConfig = Field(
        default_factory=HealthCheckConfig,
        description="Health check configuration",
    )
    ab_test: ABTestConfig = Field(
        default_factory=ABTestConfig,
        description="A/B testing configuration",
    )
    language_routing: bool = Field(
        default=True,
        description="Enable language-based model routing",
    )
    adaptive_learning: bool = Field(
        default=True,
        description="Enable adaptive routing based on performance",
    )


class MultiAgentConfig(BaseModel):
    """Configuration for multi-agent (A2A) support.

    Attributes:
        enabled: Whether multi-agent support is enabled
        orchestration_mode: How agents are orchestrated
        max_agents: Maximum number of agents that can run concurrently
        auto_decompose: Whether to automatically decompose complex tasks
        decompose_threshold: Complexity threshold for auto-decomposition (1-10)
        router: Model router configuration
        default_agents: List of default agent roles to initialize
    """

    enabled: bool = Field(default=False, description="Enable multi-agent support")
    orchestration_mode: Literal[
        "sequential", "concurrent", "hierarchical", "dynamic", "pipeline"
    ] = Field(
        default="sequential",
        description="Agent orchestration mode",
    )
    max_agents: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Maximum concurrent agents",
    )
    auto_decompose: bool = Field(
        default=True,
        description="Automatically decompose complex tasks",
    )
    decompose_threshold: int = Field(
        default=7,
        ge=1,
        le=10,
        description="Complexity threshold for auto-decomposition",
    )
    router: ModelRouterConfig = Field(
        default_factory=ModelRouterConfig,
        description="Model router configuration",
    )
    default_agents: list[str] = Field(
        default_factory=lambda: [
            "search",
            "analysis",
            "response",
            "code",
            "summary",
            "translation",
            "reasoning",
            "planning",
            "creative",
            "math",
        ],
        description="Default agent roles to initialize",
    )


class StreamingConfig(BaseModel):
    """Configuration for streaming responses.

    Attributes:
        enabled: Whether streaming is enabled
        debounce_ms: Milliseconds to debounce streaming updates
    """

    enabled: bool = Field(default=False, description="Enable streaming responses")
    debounce_ms: int = Field(
        default=100,
        ge=0,
        description="Debounce streaming updates (milliseconds)",
    )


class ConversationPersistenceConfig(BaseModel):
    """Configuration for conversation persistence.

    Attributes:
        enabled: Whether persistence is enabled
        database_url: SQLAlchemy database URL
        max_history_days: Days to keep conversation history
        auto_cleanup: Whether to automatically cleanup old conversations
        cleanup_interval_hours: Hours between cleanup runs
    """

    enabled: bool = Field(default=False, description="Enable conversation persistence")
    database_url: str = Field(
        default="sqlite:///data/conversations.db",
        description="SQLAlchemy database URL",
    )
    max_history_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Days to keep conversation history",
    )
    auto_cleanup: bool = Field(
        default=True,
        description="Automatically cleanup old conversations",
    )
    cleanup_interval_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Hours between cleanup runs",
    )


class AIConfig(BaseModel):
    """Configuration for AI capabilities.

    Attributes:
        enabled: Whether AI features are enabled
        model: The AI model to use (e.g., 'openai:gpt-4', 'anthropic:claude-3-5-sonnet-20241022')
        api_key: API key for the AI provider (can use environment variable)
        provider_config: Provider-specific configuration options
        fallback_models: List of fallback models to try if primary model fails
        system_prompt: Default system prompt for the AI agent
        max_conversation_turns: Maximum number of conversation turns to keep in history
        temperature: Temperature for AI responses (0.0-2.0)
        max_tokens: Maximum tokens in AI responses
        web_search_enabled: Whether to enable web search capabilities
        web_search_max_results: Maximum number of search results to retrieve
        conversation_timeout_minutes: Minutes of inactivity before conversation expires
        tools_enabled: Whether to enable tool/function calling
        structured_output_enabled: Whether to use structured output validation
        output_validators_enabled: Whether to enable output validators
        retry_on_validation_error: Whether to retry on validation errors
        max_retries: Maximum number of retries for validation errors
        mcp: MCP configuration
        multi_agent: Multi-agent configuration
        streaming: Streaming configuration
        personas: Persona presets
        default_persona: Default persona id
    """

    enabled: bool = Field(default=False, description="Enable AI features")
    model: str = Field(
        default="openai:gpt-4o",
        description="AI model to use (format: 'provider:model-name')",
    )
    api_key: str | None = Field(
        default=None,
        description="API key for AI provider (or set via environment variable)",
    )
    provider_config: ModelProviderConfig = Field(
        default_factory=ModelProviderConfig,
        description="Provider-specific configuration options",
    )
    fallback_models: list[str] = Field(
        default_factory=list,
        description=(
            "List of fallback models to try if primary model fails (format: 'provider:model-name')"
        ),
    )
    system_prompt: str = Field(
        default="You are a helpful AI assistant integrated with Feishu. "
        "Provide clear, concise, and accurate responses to user queries.",
        description="Default system prompt for the AI agent",
    )
    personas: dict[str, PersonaConfig] = Field(
        default_factory=dict,
        description="Persona presets",
    )
    default_persona: str | None = Field(
        default=None,
        description="Default persona id",
    )
    max_conversation_turns: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum conversation turns to keep in history",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for AI responses",
    )
    max_tokens: int | None = Field(
        default=None,
        ge=1,
        description="Maximum tokens in AI responses",
    )
    web_search_enabled: bool = Field(
        default=True,
        description="Enable web search capabilities (legacy, use web_search.enabled)",
    )
    web_search_max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of search results (legacy, use web_search.max_results)",
    )
    web_search: WebSearchConfig = Field(
        default_factory=WebSearchConfig,
        description="Web search configuration with multiple providers",
    )
    conversation_timeout_minutes: int = Field(
        default=30,
        ge=1,
        description="Minutes of inactivity before conversation expires",
    )
    tools_enabled: bool = Field(
        default=True,
        description="Enable tool/function calling",
    )
    structured_output_enabled: bool = Field(
        default=False,
        description="Enable structured output validation with Pydantic models",
    )
    output_validators_enabled: bool = Field(
        default=False,
        description="Enable output validators for response validation",
    )
    retry_on_validation_error: bool = Field(
        default=True,
        description="Retry on validation errors",
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retries for validation errors",
    )
    mcp: MCPConfig = Field(
        default_factory=MCPConfig,
        description="MCP configuration",
    )
    multi_agent: MultiAgentConfig = Field(
        default_factory=MultiAgentConfig,
        description="Multi-agent configuration",
    )
    streaming: StreamingConfig = Field(
        default_factory=StreamingConfig,
        description="Streaming configuration",
    )
    conversation_persistence: ConversationPersistenceConfig | None = Field(
        default=None,
        description="Conversation persistence configuration",
    )
    available_models: list[str] = Field(
        default_factory=lambda: [
            "openai:gpt-4o",
            "openai:gpt-4o-mini",
            "anthropic:claude-3-5-sonnet-20241022",
        ],
        description="List of models available for user switching via /model command",
    )
