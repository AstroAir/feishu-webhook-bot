"""AI Agent implementation using pydantic-ai."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext

from ..core.logger import get_logger
from .config import AIConfig
from .conversation import ConversationManager
from .exceptions import (
    AIServiceUnavailableError,
    ModelResponseError,
    ToolExecutionError,
)
from .mcp_client import MCPClient
from .multi_agent import AgentOrchestrator
from .retry import CircuitBreaker
from .tools import ToolRegistry, calculate, get_current_time, register_default_tools, web_search

logger = get_logger("ai.agent")


class AIResponse(BaseModel):
    """Structured response from the AI agent.

    Attributes:
        message: The main response message
        confidence: Confidence level of the response (0.0-1.0)
        sources_used: List of sources used (e.g., web search results)
        tools_called: List of tools that were called
    """

    message: str = Field(description="The main response message")
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence level of the response",
    )
    sources_used: list[str] = Field(
        default_factory=list,
        description="List of sources used",
    )
    tools_called: list[str] = Field(
        default_factory=list,
        description="List of tools that were called",
    )


class AIAgentDependencies:
    """Dependencies for the AI agent.

    Attributes:
        user_id: Unique identifier for the user
        config: AI configuration
        conversation_manager: Conversation state manager
        tool_registry: Tool registry
    """

    def __init__(
        self,
        user_id: str,
        config: AIConfig,
        conversation_manager: ConversationManager,
        tool_registry: ToolRegistry,
    ) -> None:
        """Initialize dependencies.

        Args:
            user_id: Unique identifier for the user
            config: AI configuration
            conversation_manager: Conversation state manager
            tool_registry: Tool registry
        """
        self.user_id = user_id
        self.config = config
        self.conversation_manager = conversation_manager
        self.tool_registry = tool_registry


class AIAgent:
    """AI Agent for handling intelligent conversations.

    This class integrates pydantic-ai to provide:
    - Multi-turn conversation support
    - Tool/function calling
    - Web search capabilities
    - Structured responses
    - Streaming responses
    - Output validation with retry logic
    - MCP (Model Context Protocol) support
    - Multi-agent orchestration (A2A)
    """

    def __init__(self, config: AIConfig) -> None:
        """Initialize the AI agent.

        Args:
            config: AI configuration
        """
        self.config = config
        self.conversation_manager = ConversationManager(
            timeout_minutes=config.conversation_timeout_minutes
        )
        self.tool_registry = ToolRegistry()

        # Register default tools
        register_default_tools(self.tool_registry)

        # Initialize MCP client
        self.mcp_client = MCPClient(config.mcp)

        # Initialize multi-agent orchestrator
        self.orchestrator = AgentOrchestrator(config.multi_agent, model=config.model)

        # Initialize circuit breaker for resilience
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            expected_exception=Exception,
        )

        # Initialize performance metrics
        self._metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        # Set up API key from config or environment
        api_key = config.api_key or self._get_api_key_from_env(config.model)
        if api_key:
            os.environ.setdefault(self._get_env_var_name(config.model), api_key)

        # Determine output type based on configuration
        output_type = AIResponse if config.structured_output_enabled else str

        # Prepare toolsets (MCP servers will be added if enabled)
        toolsets: list[Any] = []

        # Create the pydantic-ai agent
        # Note: MCP servers will be added to toolsets after they're initialized
        self._agent = Agent(
            model=config.model,
            deps_type=AIAgentDependencies,
            output_type=output_type,
            system_prompt=config.system_prompt,
            toolsets=toolsets,
        )

        # Register tools with the agent
        if config.tools_enabled:
            self._register_agent_tools()

        # Register output validators if enabled
        if config.output_validators_enabled:
            self._register_output_validators()

        logger.info(
            "AIAgent initialized with model: %s "
            "(streaming: %s, structured: %s, mcp: %s, multi-agent: %s)",
            config.model,
            config.streaming.enabled,
            config.structured_output_enabled,
            config.mcp.enabled,
            config.multi_agent.enabled,
        )

    def _get_api_key_from_env(self, model: str) -> str | None:
        """Get API key from environment based on model provider.

        Args:
            model: Model string (e.g., 'openai:gpt-4')

        Returns:
            API key or None
        """
        model.split(":")[0].lower()
        env_var_name = self._get_env_var_name(model)
        return os.getenv(env_var_name)

    def _get_env_var_name(self, model: str) -> str:
        """Get environment variable name for API key.

        Args:
            model: Model string (e.g., 'openai:gpt-4')

        Returns:
            Environment variable name
        """
        provider = model.split(":")[0].lower()
        env_var_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "google-gla": "GOOGLE_API_KEY",
            "groq": "GROQ_API_KEY",
            "mistral": "MISTRAL_API_KEY",
            "cohere": "COHERE_API_KEY",
        }
        return env_var_map.get(provider, f"{provider.upper()}_API_KEY")

    def _register_agent_tools(self) -> None:
        """Register tools with the pydantic-ai agent."""

        # Web search tool
        if self.config.web_search_enabled:

            @self._agent.tool
            async def search_web(ctx: RunContext[AIAgentDependencies], query: str) -> str:
                """Search the web for current information.

                Use this tool when you need to find up-to-date information,
                facts, news, or answers that require internet access.

                Args:
                    ctx: Run context with dependencies
                    query: Search query

                Returns:
                    Search results as JSON string
                """
                max_results = ctx.deps.config.web_search_max_results
                return await web_search(query, max_results)

        # Time tool
        @self._agent.tool
        async def current_time(ctx: RunContext[AIAgentDependencies]) -> str:
            """Get the current date and time.

            Use this tool when you need to know the current time or date.

            Args:
                ctx: Run context with dependencies

            Returns:
                Current time in ISO format
            """
            return await get_current_time()

        # Calculator tool
        @self._agent.tool
        async def calculator(ctx: RunContext[AIAgentDependencies], expression: str) -> str:
            """Perform mathematical calculations.

            Use this tool to evaluate mathematical expressions.
            Supports basic operations: +, -, *, /, parentheses.

            Args:
                ctx: Run context with dependencies
                expression: Mathematical expression to evaluate

            Returns:
                Calculation result
            """
            return await calculate(expression)

        logger.info("Registered %d tools with AI agent", 3 if self.config.web_search_enabled else 2)

    def _register_output_validators(self) -> None:
        """Register output validators with the pydantic-ai agent."""

        @self._agent.output_validator
        async def validate_response(ctx: RunContext[AIAgentDependencies], output: Any) -> Any:
            """Validate the AI response.

            This validator checks the response quality and can request retries.

            Args:
                ctx: Run context with dependencies
                output: The output to validate

            Returns:
                Validated output

            Raises:
                ModelRetry: If validation fails and retry is needed
            """
            # For structured output, validate the AIResponse
            if self.config.structured_output_enabled and isinstance(output, AIResponse):
                # Check confidence level
                if output.confidence < 0.3 and ctx.retry < self.config.max_retries:
                    raise ModelRetry(
                        "Response confidence is too low. Please provide a more confident answer."
                    )

                # Check message length
                if len(output.message.strip()) < 10 and ctx.retry < self.config.max_retries:
                    raise ModelRetry(
                        "Response is too short. Please provide a more detailed answer."
                    )

            # For plain text output, basic validation
            elif isinstance(output, str):
                if len(output.strip()) < 5 and ctx.retry < self.config.max_retries:
                    raise ModelRetry(
                        "Response is too short. Please provide a more complete answer."
                    )

            return output

        logger.info("Registered output validators with AI agent")

    async def chat(self, user_id: str, message: str) -> str:
        """Process a chat message and generate a response.

        Args:
            user_id: Unique identifier for the user
            message: User's message

        Returns:
            AI-generated response
        """
        import time

        start_time = time.time()

        logger.info("Processing chat message from user %s: %s", user_id, message[:100])

        # Track request
        self._metrics["total_requests"] += 1

        try:
            # Ensure MCP is initialized if enabled (lazy initialization)
            await self._ensure_mcp_initialized()

            # Check if multi-agent orchestration should be used
            if self.config.multi_agent.enabled:
                logger.info("Using multi-agent orchestration for user %s", user_id)
                response = await self.orchestrator.orchestrate(message)

                # Track success
                self._metrics["successful_requests"] += 1
                response_time = time.time() - start_time
                self._metrics["total_response_time"] += response_time
                logger.info("Response generated in %.2fs", response_time)

                return response

            # Get conversation state
            conversation = await self.conversation_manager.get_conversation(user_id)

            # Create dependencies
            deps = AIAgentDependencies(
                user_id=user_id,
                config=self.config,
                conversation_manager=self.conversation_manager,
                tool_registry=self.tool_registry,
            )

            # Get message history
            message_history = conversation.get_messages(self.config.max_conversation_turns)

            # Run the agent
            result = await self._agent.run(
                message,
                deps=deps,
                message_history=message_history,
            )

            # Store the new messages in conversation history with token tracking
            usage = result.usage()
            input_tokens = usage.input_tokens if usage else 0
            output_tokens = usage.output_tokens if usage else 0

            conversation.add_messages(
                result.new_messages(),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

            # Track metrics
            self._metrics["successful_requests"] += 1
            self._metrics["total_input_tokens"] += input_tokens
            self._metrics["total_output_tokens"] += output_tokens
            response_time = time.time() - start_time
            self._metrics["total_response_time"] += response_time

            logger.info(
                "Generated response for user %s (tokens: in=%d, out=%d, time: %.2fs)",
                user_id,
                input_tokens,
                output_tokens,
                response_time,
            )

            # Extract output based on type
            if isinstance(result.output, AIResponse):
                return result.output.message

            return str(result.output)

        except AIServiceUnavailableError as exc:
            self._metrics["failed_requests"] += 1
            logger.error("AI service unavailable: %s", exc, exc_info=True)
            return (
                "I apologize, but the AI service is currently unavailable. Please try again later."
            )

        except ModelResponseError as exc:
            self._metrics["failed_requests"] += 1
            logger.error("Invalid model response: %s", exc, exc_info=True)
            return (
                "I apologize, but I received an invalid response. "
                "Please try rephrasing your question."
            )

        except ToolExecutionError as exc:
            self._metrics["failed_requests"] += 1
            logger.error("Tool execution failed: %s", exc, exc_info=True)
            return (
                f"I apologize, but I encountered an error while using "
                f"the {exc.tool_name} tool. Please try again."
            )

        except Exception as exc:
            self._metrics["failed_requests"] += 1
            logger.error("Unexpected error processing chat message: %s", exc, exc_info=True)
            return (
                "I apologize, but I encountered an unexpected error. "
                "Please try again or contact support if the issue persists."
            )

    async def chat_stream(self, user_id: str, message: str) -> AsyncIterator[str]:
        """Process a chat message and stream the response.

        Args:
            user_id: Unique identifier for the user
            message: User's message

        Yields:
            Chunks of the AI-generated response
        """
        logger.info("Processing streaming chat message from user %s: %s", user_id, message[:100])

        try:
            # Ensure MCP is initialized if enabled (lazy initialization)
            await self._ensure_mcp_initialized()

            # Get conversation state
            conversation = await self.conversation_manager.get_conversation(user_id)

            # Create dependencies
            deps = AIAgentDependencies(
                user_id=user_id,
                config=self.config,
                conversation_manager=self.conversation_manager,
                tool_registry=self.tool_registry,
            )

            # Get message history
            message_history = conversation.get_messages(self.config.max_conversation_turns)

            # Stream the agent response
            debounce_seconds = self.config.streaming.debounce_ms / 1000.0

            async with self._agent.run_stream(
                message,
                deps=deps,
                message_history=message_history,
            ) as result:
                # Stream text chunks
                async for chunk in result.stream_text(delta=True, debounce_by=debounce_seconds):
                    yield chunk

                # After streaming completes, store messages
                conversation.add_messages(result.new_messages())

                logger.info(
                    "Completed streaming response for user %s (tokens: in=%d, out=%d)",
                    user_id,
                    result.usage().input_tokens if result.usage() else 0,
                    result.usage().output_tokens if result.usage() else 0,
                )

        except Exception as exc:
            logger.error("Error processing streaming chat message: %s", exc, exc_info=True)
            yield f"I apologize, but I encountered an error: {str(exc)}"

    async def _ensure_mcp_initialized(self) -> None:
        """Ensure MCP client is initialized and servers are registered as toolsets.

        This is called lazily on first chat to avoid blocking the synchronous start() method.
        """
        if self.config.mcp.enabled and not self.mcp_client.is_started():
            try:
                logger.info("Initializing MCP client...")
                await self.mcp_client.start()

                # Get MCP servers and add them as toolsets to the agent
                mcp_servers = self.mcp_client.get_mcp_servers()
                if mcp_servers:
                    # Add MCP servers to agent's toolsets
                    # Note: We need to recreate the agent with the new toolsets
                    # because pydantic-ai doesn't support dynamic toolset addition
                    output_type = AIResponse if self.config.structured_output_enabled else str

                    self._agent = Agent(
                        model=self.config.model,
                        deps_type=AIAgentDependencies,
                        output_type=output_type,
                        system_prompt=self.config.system_prompt,
                        toolsets=mcp_servers,
                    )

                    # Re-register tools and validators
                    if self.config.tools_enabled:
                        self._register_agent_tools()
                    if self.config.output_validators_enabled:
                        self._register_output_validators()

                    logger.info("MCP client initialized with %d servers", len(mcp_servers))
                else:
                    logger.warning("MCP enabled but no servers configured")

            except Exception as exc:
                logger.error("Failed to initialize MCP client: %s", exc, exc_info=True)
                # Continue without MCP rather than failing completely

    async def clear_conversation(self, user_id: str) -> None:
        """Clear conversation history for a user.

        Args:
            user_id: Unique identifier for the user
        """
        await self.conversation_manager.clear_conversation(user_id)
        logger.info("Cleared conversation for user: %s", user_id)

    def start(self) -> None:
        """Start the AI agent and background tasks.

        This method:
        1. Starts the conversation cleanup task
        2. Initializes MCP servers if enabled (async operation deferred)
        3. Registers MCP servers as toolsets with the agent

        Note: MCP client initialization is async, so it's deferred to first chat call.
        """
        self.conversation_manager.start_cleanup()
        logger.info("AI agent started")

    async def stop(self) -> None:
        """Stop the AI agent and cleanup."""
        await self.conversation_manager.stop_cleanup()

        # Stop MCP client if started
        if self.mcp_client.is_started():
            await self.mcp_client.stop()

        logger.info("AI agent stopped")

    async def get_stats(self) -> dict[str, Any]:
        """Get comprehensive statistics about the AI agent.

        Returns:
            Dictionary with agent statistics including performance metrics
        """
        conv_stats = await self.conversation_manager.get_stats()
        mcp_stats = self.mcp_client.get_stats()
        orchestrator_stats = self.orchestrator.get_stats()
        tool_stats = self.tool_registry.get_stats()

        # Calculate performance metrics
        total_requests = self._metrics["total_requests"]
        successful_requests = self._metrics["successful_requests"]
        failed_requests = self._metrics["failed_requests"]
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        avg_response_time = (
            self._metrics["total_response_time"] / successful_requests
            if successful_requests > 0
            else 0
        )
        total_tokens = self._metrics["total_input_tokens"] + self._metrics["total_output_tokens"]

        return {
            "model": self.config.model,
            "tools_enabled": self.config.tools_enabled,
            "web_search_enabled": self.config.web_search_enabled,
            "streaming_enabled": self.config.streaming.enabled,
            "structured_output_enabled": self.config.structured_output_enabled,
            "performance": {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate_percent": round(success_rate, 2),
                "average_response_time_seconds": round(avg_response_time, 3),
                "total_input_tokens": self._metrics["total_input_tokens"],
                "total_output_tokens": self._metrics["total_output_tokens"],
                "total_tokens": total_tokens,
            },
            "tools": tool_stats,
            "output_validators_enabled": self.config.output_validators_enabled,
            "conversation_stats": conv_stats,
            "mcp_stats": mcp_stats,
            "orchestrator_stats": orchestrator_stats,
        }
