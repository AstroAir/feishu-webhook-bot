"""Configuration for AI features."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


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


class MultiAgentConfig(BaseModel):
    """Configuration for multi-agent (A2A) support.

    Attributes:
        enabled: Whether multi-agent support is enabled
        orchestration_mode: How agents are orchestrated (sequential, concurrent, hierarchical)
        max_agents: Maximum number of agents that can run concurrently
    """

    enabled: bool = Field(default=False, description="Enable multi-agent support")
    orchestration_mode: Literal["sequential", "concurrent", "hierarchical"] = Field(
        default="sequential",
        description="Agent orchestration mode",
    )
    max_agents: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum concurrent agents",
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
            "List of fallback models to try if primary model fails "
            "(format: 'provider:model-name')"
        ),
    )
    system_prompt: str = Field(
        default="You are a helpful AI assistant integrated with Feishu. "
        "Provide clear, concise, and accurate responses to user queries.",
        description="Default system prompt for the AI agent",
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
        description="Enable web search capabilities",
    )
    web_search_max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of search results",
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
