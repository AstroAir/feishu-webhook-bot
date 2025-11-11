"""Multi-agent orchestration for A2A (Agent-to-Agent) communication."""

from __future__ import annotations

import asyncio
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from ..core.logger import get_logger
from .config import MultiAgentConfig

logger = get_logger("ai.multi_agent")


class AgentMessage(BaseModel):
    """Message passed between agents.

    Attributes:
        from_agent: Name of the sending agent
        to_agent: Name of the receiving agent
        content: Message content
        metadata: Additional metadata
    """

    from_agent: str = Field(description="Sending agent name")
    to_agent: str = Field(description="Receiving agent name")
    content: str = Field(description="Message content")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class AgentResult(BaseModel):
    """Result from an agent execution.

    Attributes:
        agent_name: Name of the agent
        output: Agent output
        success: Whether execution was successful
        error: Error message if failed
        metadata: Additional metadata
    """

    agent_name: str = Field(description="Agent name")
    output: str = Field(description="Agent output")
    success: bool = Field(default=True, description="Success status")
    error: str | None = Field(default=None, description="Error message")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class SpecializedAgent:
    """Base class for specialized agents.

    Each specialized agent has a specific role and expertise.
    """

    def __init__(
        self,
        name: str,
        role: str,
        system_prompt: str,
        model: str = "openai:gpt-4o",
    ) -> None:
        """Initialize a specialized agent.

        Args:
            name: Agent name
            role: Agent role/expertise
            system_prompt: System prompt for the agent
            model: AI model to use
        """
        self.name = name
        self.role = role
        self.model = model

        # Create pydantic-ai agent
        self._agent = Agent(
            model=model,
            output_type=str,
            system_prompt=system_prompt,
        )

        logger.info("Initialized specialized agent: %s (role: %s)", name, role)

    async def process(self, message: str, context: dict[str, Any] | None = None) -> AgentResult:
        """Process a message and generate a response.

        Args:
            message: Input message
            context: Optional context information

        Returns:
            Agent result
        """
        logger.info("Agent %s processing message: %s", self.name, message[:100])

        try:
            # Run the agent
            result = await self._agent.run(message)

            return AgentResult(
                agent_name=self.name,
                output=result.output,
                success=True,
                metadata={"role": self.role, "context": context or {}},
            )

        except Exception as exc:
            logger.error("Agent %s failed: %s", self.name, exc, exc_info=True)
            return AgentResult(
                agent_name=self.name,
                output="",
                success=False,
                error=str(exc),
                metadata={"role": self.role},
            )


class SearchAgent(SpecializedAgent):
    """Agent specialized in information search and retrieval."""

    def __init__(self, model: str = "openai:gpt-4o") -> None:
        """Initialize the search agent."""
        super().__init__(
            name="SearchAgent",
            role="search",
            system_prompt=(
                "You are a search specialist. Your role is to identify what information "
                "needs to be searched for and formulate effective search queries. "
                "Extract key search terms and provide structured search strategies."
            ),
            model=model,
        )


class AnalysisAgent(SpecializedAgent):
    """Agent specialized in analyzing and processing information."""

    def __init__(self, model: str = "openai:gpt-4o") -> None:
        """Initialize the analysis agent."""
        super().__init__(
            name="AnalysisAgent",
            role="analysis",
            system_prompt=(
                "You are an analysis specialist. Your role is to analyze information, "
                "identify patterns, draw insights, and synthesize findings. "
                "Provide clear, structured analysis with key takeaways."
            ),
            model=model,
        )


class ResponseAgent(SpecializedAgent):
    """Agent specialized in generating user-facing responses."""

    def __init__(self, model: str = "openai:gpt-4o") -> None:
        """Initialize the response agent."""
        super().__init__(
            name="ResponseAgent",
            role="response",
            system_prompt=(
                "You are a response specialist. Your role is to take analyzed information "
                "and craft clear, helpful, user-friendly responses. "
                "Be concise, accurate, and engaging in your communication."
            ),
            model=model,
        )


class AgentOrchestrator:
    """Orchestrates multiple agents for complex tasks.

    Supports different orchestration modes:
    - Sequential: Agents run one after another
    - Concurrent: Agents run in parallel
    - Hierarchical: Coordinator agent manages sub-agents
    """

    def __init__(self, config: MultiAgentConfig, model: str = "openai:gpt-4o") -> None:
        """Initialize the agent orchestrator.

        Args:
            config: Multi-agent configuration
            model: Default model for agents
        """
        self.config = config
        self.model = model
        self._agents: dict[str, SpecializedAgent] = {}

        # Initialize default specialized agents
        if config.enabled:
            self._initialize_default_agents()

        logger.info(
            "AgentOrchestrator initialized (mode: %s, agents: %d)",
            config.orchestration_mode,
            len(self._agents),
        )

    def _initialize_default_agents(self) -> None:
        """Initialize default specialized agents."""
        self._agents["search"] = SearchAgent(model=self.model)
        self._agents["analysis"] = AnalysisAgent(model=self.model)
        self._agents["response"] = ResponseAgent(model=self.model)

        logger.info("Initialized %d default agents", len(self._agents))

    def register_agent(self, agent: SpecializedAgent) -> None:
        """Register a custom agent.

        Args:
            agent: Specialized agent to register
        """
        self._agents[agent.role] = agent
        logger.info("Registered custom agent: %s (role: %s)", agent.name, agent.role)

    async def orchestrate(
        self,
        message: str,
        mode: Literal["sequential", "concurrent", "hierarchical"] | None = None,
    ) -> str:
        """Orchestrate multiple agents to process a message.

        Args:
            message: Input message
            mode: Orchestration mode (uses config default if not specified)

        Returns:
            Final response
        """
        if not self.config.enabled:
            logger.warning("Multi-agent is disabled, returning empty response")
            return ""

        orchestration_mode = mode or self.config.orchestration_mode
        logger.info(
            "Orchestrating agents in %s mode for message: %s", orchestration_mode, message[:100]
        )

        if orchestration_mode == "sequential":
            return await self._orchestrate_sequential(message)
        elif orchestration_mode == "concurrent":
            return await self._orchestrate_concurrent(message)
        elif orchestration_mode == "hierarchical":
            return await self._orchestrate_hierarchical(message)
        else:
            raise ValueError(f"Unknown orchestration mode: {orchestration_mode}")

    async def _orchestrate_sequential(self, message: str) -> str:
        """Orchestrate agents sequentially: search → analysis → response.

        Args:
            message: Input message

        Returns:
            Final response
        """
        logger.info("Running sequential orchestration")

        # Step 1: Search agent identifies what to search for
        search_result = await self._agents["search"].process(
            f"Identify what information is needed to answer: {message}"
        )

        if not search_result.success:
            return f"Search failed: {search_result.error}"

        # Step 2: Analysis agent processes the search strategy
        analysis_result = await self._agents["analysis"].process(
            f"Based on this search strategy: {search_result.output}\n\n"
            f"Analyze how to answer: {message}"
        )

        if not analysis_result.success:
            return f"Analysis failed: {analysis_result.error}"

        # Step 3: Response agent generates final response
        response_result = await self._agents["response"].process(
            f"Based on this analysis: {analysis_result.output}\n\n"
            f"Generate a response to: {message}"
        )

        if not response_result.success:
            return f"Response generation failed: {response_result.error}"

        logger.info("Sequential orchestration completed successfully")
        return response_result.output

    async def _orchestrate_concurrent(self, message: str) -> str:
        """Orchestrate agents concurrently and combine results.

        Args:
            message: Input message

        Returns:
            Combined response
        """
        logger.info("Running concurrent orchestration")

        # Run all agents concurrently
        tasks = [
            self._agents["search"].process(f"Search perspective on: {message}"),
            self._agents["analysis"].process(f"Analysis perspective on: {message}"),
            self._agents["response"].process(f"Direct response to: {message}"),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine successful results
        outputs = []
        for result in results:
            if isinstance(result, AgentResult) and result.success:
                outputs.append(f"[{result.agent_name}]: {result.output}")

        combined = "\n\n".join(outputs)
        logger.info("Concurrent orchestration completed with %d results", len(outputs))
        return combined

    async def _orchestrate_hierarchical(self, message: str) -> str:
        """Orchestrate agents hierarchically with a coordinator.

        Args:
            message: Input message

        Returns:
            Final response
        """
        logger.info("Running hierarchical orchestration")

        # Create a coordinator agent
        coordinator = Agent(
            model=self.model,
            output_type=str,
            system_prompt=(
                "You are a coordinator agent. Analyze the user's request and decide "
                "which specialized agents (search, analysis, response) should be involved "
                "and in what order. Provide a brief execution plan."
            ),
        )

        # Get execution plan from coordinator
        plan_result = await coordinator.run(f"Create an execution plan for: {message}")

        logger.info("Coordinator plan: %s", plan_result.output[:200])

        # For now, default to sequential execution
        # In a full implementation, parse the plan and execute accordingly
        return await self._orchestrate_sequential(message)

    def get_stats(self) -> dict[str, Any]:
        """Get orchestrator statistics.

        Returns:
            Dictionary with orchestrator statistics
        """
        return {
            "enabled": self.config.enabled,
            "mode": self.config.orchestration_mode,
            "agent_count": len(self._agents),
            "agents": [{"name": agent.name, "role": agent.role} for agent in self._agents.values()],
        }
