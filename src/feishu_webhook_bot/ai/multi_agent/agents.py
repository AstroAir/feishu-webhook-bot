"""Specialized agents for multi-agent system.

This module provides various specialized agents, each with specific
expertise and capabilities for different types of tasks.
"""

from __future__ import annotations

import time
from typing import Any

from pydantic_ai import Agent

from ...core.logger import get_logger
from .base import AgentCapability, AgentInfo, AgentResult

logger = get_logger("ai.multi_agent.agents")


class SpecializedAgent:
    """Base class for specialized agents.

    Each specialized agent has a specific role and expertise.
    Agents can process messages and generate responses using their
    assigned AI model.
    """

    def __init__(
        self,
        name: str,
        role: str,
        system_prompt: str,
        model: str = "openai:gpt-4o",
        capabilities: list[AgentCapability] | None = None,
        description: str = "",
    ) -> None:
        """Initialize a specialized agent.

        Args:
            name: Agent name
            role: Agent role/expertise
            system_prompt: System prompt for the agent
            model: AI model to use
            capabilities: List of agent capabilities
            description: Agent description
        """
        self.name = name
        self.role = role
        self.model = model
        self.capabilities = capabilities or []
        self.description = description or f"Agent specialized in {role}"
        self._system_prompt = system_prompt

        # Create pydantic-ai agent
        self._agent = Agent(
            model=model,
            output_type=str,
            system_prompt=system_prompt,
        )

        # Metrics
        self._metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_time_ms": 0.0,
        }

        logger.info(
            "Initialized specialized agent: %s (role: %s, model: %s)",
            name,
            role,
            model,
        )

    async def process(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Process a message and generate a response.

        Args:
            message: Input message
            context: Optional context information

        Returns:
            Agent result with output and metadata
        """
        logger.info("Agent %s processing message: %s...", self.name, message[:100])
        self._metrics["total_requests"] += 1

        start_time = time.time()

        try:
            # Run the agent
            result = await self._agent.run(message)

            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000

            # Track metrics
            self._metrics["successful_requests"] += 1
            self._metrics["total_time_ms"] += execution_time_ms

            tokens_used = 0
            if result.usage():
                tokens_used = (result.usage().input_tokens or 0) + (
                    result.usage().output_tokens or 0
                )
                self._metrics["total_tokens"] += tokens_used

            return AgentResult(
                agent_name=self.name,
                output=result.output,
                success=True,
                execution_time_ms=execution_time_ms,
                tokens_used=tokens_used,
                metadata={
                    "role": self.role,
                    "model": self.model,
                    "context": context or {},
                },
            )

        except Exception as exc:
            execution_time_ms = (time.time() - start_time) * 1000
            self._metrics["failed_requests"] += 1
            self._metrics["total_time_ms"] += execution_time_ms

            logger.error("Agent %s failed: %s", self.name, exc, exc_info=True)
            return AgentResult(
                agent_name=self.name,
                output="",
                success=False,
                error=str(exc),
                execution_time_ms=execution_time_ms,
                metadata={"role": self.role, "model": self.model},
            )

    def has_capability(self, capability: AgentCapability) -> bool:
        """Check if agent has a specific capability.

        Args:
            capability: Capability to check

        Returns:
            True if agent has the capability
        """
        return capability in self.capabilities

    def get_info(self) -> AgentInfo:
        """Get agent information.

        Returns:
            AgentInfo with agent details
        """
        return AgentInfo(
            name=self.name,
            role=self.role,
            capabilities=self.capabilities,
            preferred_model=self.model,
            description=self.description,
            enabled=True,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get agent statistics.

        Returns:
            Dictionary with agent metrics
        """
        total = self._metrics["total_requests"]
        successful = self._metrics["successful_requests"]

        return {
            "name": self.name,
            "role": self.role,
            "model": self.model,
            "total_requests": total,
            "successful_requests": successful,
            "failed_requests": self._metrics["failed_requests"],
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "total_tokens": self._metrics["total_tokens"],
            "avg_time_ms": (self._metrics["total_time_ms"] / total if total > 0 else 0),
        }

    def update_model(self, model: str) -> None:
        """Update the agent's model.

        Args:
            model: New model to use
        """
        self.model = model
        self._agent = Agent(
            model=model,
            output_type=str,
            system_prompt=self._system_prompt,
        )
        logger.info("Agent %s updated to model: %s", self.name, model)


class SearchAgent(SpecializedAgent):
    """Agent specialized in information search and retrieval.

    This agent excels at:
    - Identifying what information needs to be searched
    - Formulating effective search queries
    - Extracting key search terms
    - Providing structured search strategies
    """

    def __init__(self, model: str = "openai:gpt-4o") -> None:
        """Initialize the search agent."""
        super().__init__(
            name="SearchAgent",
            role="search",
            system_prompt=(
                "You are a search specialist. Your role is to identify what information "
                "needs to be searched for and formulate effective search queries. "
                "Extract key search terms and provide structured search strategies. "
                "When given a question or topic:\n"
                "1. Identify the core information need\n"
                "2. Break down complex queries into simpler sub-queries\n"
                "3. Suggest relevant keywords and phrases\n"
                "4. Recommend search strategies (web, academic, news, etc.)"
            ),
            model=model,
            capabilities=[
                AgentCapability.SEARCH,
                AgentCapability.DATA_EXTRACTION,
            ],
            description="Specialist in information search and query formulation",
        )


class AnalysisAgent(SpecializedAgent):
    """Agent specialized in analyzing and processing information.

    This agent excels at:
    - Analyzing complex information
    - Identifying patterns and trends
    - Drawing insights from data
    - Synthesizing findings
    """

    def __init__(self, model: str = "openai:gpt-4o") -> None:
        """Initialize the analysis agent."""
        super().__init__(
            name="AnalysisAgent",
            role="analysis",
            system_prompt=(
                "You are an analysis specialist. Your role is to analyze information, "
                "identify patterns, draw insights, and synthesize findings. "
                "Provide clear, structured analysis with key takeaways. "
                "When analyzing information:\n"
                "1. Identify key facts and data points\n"
                "2. Look for patterns, trends, and relationships\n"
                "3. Draw logical conclusions\n"
                "4. Highlight important insights\n"
                "5. Present findings in a structured format"
            ),
            model=model,
            capabilities=[
                AgentCapability.ANALYSIS,
                AgentCapability.REASONING,
                AgentCapability.DATA_EXTRACTION,
            ],
            description="Specialist in data analysis and insight extraction",
        )


class ResponseAgent(SpecializedAgent):
    """Agent specialized in generating user-facing responses.

    This agent excels at:
    - Crafting clear, helpful responses
    - Adapting tone and style
    - Ensuring accuracy and completeness
    - Making complex information accessible
    """

    def __init__(self, model: str = "openai:gpt-4o") -> None:
        """Initialize the response agent."""
        super().__init__(
            name="ResponseAgent",
            role="response",
            system_prompt=(
                "You are a response specialist. Your role is to take analyzed information "
                "and craft clear, helpful, user-friendly responses. "
                "Be concise, accurate, and engaging in your communication. "
                "When generating responses:\n"
                "1. Understand the user's original question\n"
                "2. Synthesize the provided information\n"
                "3. Structure the response logically\n"
                "4. Use clear, accessible language\n"
                "5. Include relevant details without overwhelming"
            ),
            model=model,
            capabilities=[
                AgentCapability.CONVERSATION,
                AgentCapability.SUMMARIZATION,
            ],
            description="Specialist in generating user-friendly responses",
        )


class CodeAgent(SpecializedAgent):
    """Agent specialized in code generation and analysis.

    This agent excels at:
    - Writing clean, efficient code
    - Reviewing and debugging code
    - Explaining code concepts
    - Suggesting improvements
    """

    def __init__(self, model: str = "openai:gpt-4o") -> None:
        """Initialize the code agent."""
        super().__init__(
            name="CodeAgent",
            role="code",
            system_prompt=(
                "You are a code specialist. Your role is to write, review, and explain code. "
                "Follow best practices and write clean, efficient, well-documented code. "
                "When working with code:\n"
                "1. Understand the requirements clearly\n"
                "2. Choose appropriate algorithms and data structures\n"
                "3. Write readable, maintainable code\n"
                "4. Include helpful comments and documentation\n"
                "5. Consider edge cases and error handling\n"
                "6. Follow language-specific conventions and best practices"
            ),
            model=model,
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.CODE_REVIEW,
                AgentCapability.REASONING,
            ],
            description="Specialist in code generation, review, and debugging",
        )


class SummaryAgent(SpecializedAgent):
    """Agent specialized in text summarization.

    This agent excels at:
    - Condensing long texts
    - Extracting key points
    - Creating executive summaries
    - Maintaining essential information
    """

    def __init__(self, model: str = "openai:gpt-4o") -> None:
        """Initialize the summary agent."""
        super().__init__(
            name="SummaryAgent",
            role="summary",
            system_prompt=(
                "You are a summarization specialist. Your role is to condense information "
                "while preserving key points and essential details. "
                "Create clear, concise summaries that capture the essence of the content. "
                "When summarizing:\n"
                "1. Identify the main topic and purpose\n"
                "2. Extract key points and supporting details\n"
                "3. Maintain logical flow and coherence\n"
                "4. Preserve critical information\n"
                "5. Adjust length based on requirements"
            ),
            model=model,
            capabilities=[
                AgentCapability.SUMMARIZATION,
                AgentCapability.DATA_EXTRACTION,
            ],
            description="Specialist in text summarization and key point extraction",
        )


class TranslationAgent(SpecializedAgent):
    """Agent specialized in language translation.

    This agent excels at:
    - Accurate translation between languages
    - Preserving meaning and nuance
    - Adapting cultural context
    - Handling technical terminology
    """

    def __init__(self, model: str = "openai:gpt-4o") -> None:
        """Initialize the translation agent."""
        super().__init__(
            name="TranslationAgent",
            role="translation",
            system_prompt=(
                "You are a translation specialist. Your role is to accurately translate "
                "text between languages while preserving meaning, tone, and nuance. "
                "Consider cultural context and adapt appropriately. "
                "When translating:\n"
                "1. Understand the source text fully\n"
                "2. Preserve the original meaning and intent\n"
                "3. Adapt idioms and cultural references\n"
                "4. Maintain appropriate tone and style\n"
                "5. Handle technical terms accurately"
            ),
            model=model,
            capabilities=[
                AgentCapability.TRANSLATION,
            ],
            description="Specialist in language translation",
        )


class ReasoningAgent(SpecializedAgent):
    """Agent specialized in complex reasoning and problem-solving.

    This agent excels at:
    - Logical reasoning
    - Problem decomposition
    - Step-by-step analysis
    - Drawing conclusions
    """

    def __init__(self, model: str = "openai:gpt-4o") -> None:
        """Initialize the reasoning agent."""
        super().__init__(
            name="ReasoningAgent",
            role="reasoning",
            system_prompt=(
                "You are a reasoning specialist. Your role is to apply logical reasoning "
                "to solve complex problems and draw well-founded conclusions. "
                "Think step-by-step and explain your reasoning clearly. "
                "When reasoning:\n"
                "1. Clearly state the problem or question\n"
                "2. Identify relevant information and assumptions\n"
                "3. Break down complex problems into steps\n"
                "4. Apply logical principles consistently\n"
                "5. Consider alternative perspectives\n"
                "6. Draw conclusions with supporting evidence"
            ),
            model=model,
            capabilities=[
                AgentCapability.REASONING,
                AgentCapability.ANALYSIS,
                AgentCapability.MATH,
            ],
            description="Specialist in logical reasoning and problem-solving",
        )


class PlanningAgent(SpecializedAgent):
    """Agent specialized in task planning and decomposition.

    This agent excels at:
    - Breaking down complex tasks
    - Creating execution plans
    - Identifying dependencies
    - Optimizing task order
    """

    def __init__(self, model: str = "openai:gpt-4o") -> None:
        """Initialize the planning agent."""
        super().__init__(
            name="PlanningAgent",
            role="planning",
            system_prompt=(
                "You are a planning specialist. Your role is to break down complex tasks "
                "into manageable steps and create effective execution plans. "
                "Consider dependencies, resources, and optimal ordering. "
                "When planning:\n"
                "1. Understand the overall goal\n"
                "2. Identify required subtasks\n"
                "3. Determine dependencies between tasks\n"
                "4. Estimate effort and resources\n"
                "5. Optimize task ordering\n"
                "6. Identify potential risks and mitigation strategies"
            ),
            model=model,
            capabilities=[
                AgentCapability.PLANNING,
                AgentCapability.REASONING,
            ],
            description="Specialist in task planning and decomposition",
        )


class CreativeAgent(SpecializedAgent):
    """Agent specialized in creative writing and content generation.

    This agent excels at:
    - Creative writing
    - Content generation
    - Storytelling
    - Marketing copy
    """

    def __init__(self, model: str = "openai:gpt-4o") -> None:
        """Initialize the creative agent."""
        super().__init__(
            name="CreativeAgent",
            role="creative",
            system_prompt=(
                "You are a creative writing specialist. Your role is to generate engaging, "
                "original content that captures attention and conveys messages effectively. "
                "Be imaginative while staying on topic. "
                "When creating content:\n"
                "1. Understand the purpose and audience\n"
                "2. Develop engaging hooks and openings\n"
                "3. Use vivid language and imagery\n"
                "4. Maintain consistent tone and voice\n"
                "5. Create memorable and impactful content"
            ),
            model=model,
            capabilities=[
                AgentCapability.CREATIVE_WRITING,
                AgentCapability.CONVERSATION,
            ],
            description="Specialist in creative writing and content generation",
        )


class MathAgent(SpecializedAgent):
    """Agent specialized in mathematical computations and explanations.

    This agent excels at:
    - Mathematical calculations
    - Problem solving
    - Explaining mathematical concepts
    - Statistical analysis
    """

    def __init__(self, model: str = "openai:gpt-4o") -> None:
        """Initialize the math agent."""
        super().__init__(
            name="MathAgent",
            role="math",
            system_prompt=(
                "You are a mathematics specialist. Your role is to solve mathematical "
                "problems, perform calculations, and explain mathematical concepts clearly. "
                "Show your work and explain your reasoning. "
                "When working with math:\n"
                "1. Understand the problem completely\n"
                "2. Identify the appropriate methods\n"
                "3. Show step-by-step solutions\n"
                "4. Verify your answers\n"
                "5. Explain concepts in accessible terms"
            ),
            model=model,
            capabilities=[
                AgentCapability.MATH,
                AgentCapability.REASONING,
            ],
            description="Specialist in mathematical computations and explanations",
        )


# Agent registry for easy access
AGENT_REGISTRY: dict[str, type[SpecializedAgent]] = {
    "search": SearchAgent,
    "analysis": AnalysisAgent,
    "response": ResponseAgent,
    "code": CodeAgent,
    "summary": SummaryAgent,
    "translation": TranslationAgent,
    "reasoning": ReasoningAgent,
    "planning": PlanningAgent,
    "creative": CreativeAgent,
    "math": MathAgent,
}


def create_agent(role: str, model: str = "openai:gpt-4o") -> SpecializedAgent:
    """Create a specialized agent by role.

    Args:
        role: Agent role (search, analysis, response, code, etc.)
        model: AI model to use

    Returns:
        Specialized agent instance

    Raises:
        ValueError: If role is not recognized
    """
    agent_class = AGENT_REGISTRY.get(role)
    if agent_class is None:
        raise ValueError(
            f"Unknown agent role: {role}. Available roles: {', '.join(AGENT_REGISTRY.keys())}"
        )
    return agent_class(model=model)


def get_available_roles() -> list[str]:
    """Get list of available agent roles.

    Returns:
        List of role names
    """
    return list(AGENT_REGISTRY.keys())
