"""Enhanced agent orchestrator for multi-agent system.

This module provides advanced orchestration capabilities including:
- Multiple orchestration modes
- Dynamic agent selection
- Task delegation and aggregation
- Execution plan management
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Literal

from pydantic_ai import Agent

from ...core.logger import get_logger
from .agents import (
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
)
from .base import (
    AgentCapability,
    AgentResult,
    ExecutionPlan,
    Task,
    TaskStatus,
    TaskType,
)
from .planner import DependencyResolver, TaskPlanner
from .router import ModelRouter, RoutingStrategy, TaskAnalyzer

logger = get_logger("ai.multi_agent.orchestrator")


class AgentOrchestrator:
    """Orchestrates multiple agents for complex tasks.

    Supports different orchestration modes:
    - Sequential: Agents run one after another
    - Concurrent: Agents run in parallel
    - Hierarchical: Coordinator agent manages sub-agents
    - Dynamic: Automatically selects agents based on task analysis
    - Pipeline: Chain of agents with data flow

    Example:
        ```python
        orchestrator = AgentOrchestrator(config, model="openai:gpt-4o")
        response = await orchestrator.orchestrate("Analyze this data...")
        ```
    """

    def __init__(
        self,
        config: Any,
        model: str = "openai:gpt-4o",
        enable_routing: bool = True,
        routing_strategy: RoutingStrategy = RoutingStrategy.BALANCED,
    ) -> None:
        """Initialize the agent orchestrator.

        Args:
            config: Multi-agent configuration
            model: Default model for agents
            enable_routing: Whether to enable automatic model routing
            routing_strategy: Strategy for model routing
        """
        self.config = config
        self.model = model
        self.enable_routing = enable_routing

        # Initialize components
        self._agents: dict[str, SpecializedAgent] = {}
        self._router = ModelRouter(strategy=routing_strategy, default_model=model)
        self._planner = TaskPlanner(model=model)
        self._analyzer = TaskAnalyzer()
        self._dependency_resolver = DependencyResolver()

        # Metrics
        self._metrics = {
            "total_orchestrations": 0,
            "successful_orchestrations": 0,
            "failed_orchestrations": 0,
            "total_time_ms": 0.0,
            "mode_usage": {},
        }

        # Initialize default agents if enabled
        if config.enabled:
            self._initialize_default_agents()

        logger.info(
            "AgentOrchestrator initialized (mode: %s, agents: %d, routing: %s)",
            config.orchestration_mode,
            len(self._agents),
            enable_routing,
        )

    def _initialize_default_agents(self) -> None:
        """Initialize default specialized agents."""
        # Core agents
        self._agents["search"] = SearchAgent(model=self.model)
        self._agents["analysis"] = AnalysisAgent(model=self.model)
        self._agents["response"] = ResponseAgent(model=self.model)

        # Extended agents
        self._agents["code"] = CodeAgent(model=self.model)
        self._agents["summary"] = SummaryAgent(model=self.model)
        self._agents["translation"] = TranslationAgent(model=self.model)
        self._agents["reasoning"] = ReasoningAgent(model=self.model)
        self._agents["planning"] = PlanningAgent(model=self.model)
        self._agents["creative"] = CreativeAgent(model=self.model)
        self._agents["math"] = MathAgent(model=self.model)

        logger.info("Initialized %d default agents", len(self._agents))

    def register_agent(self, agent: SpecializedAgent) -> None:
        """Register a custom agent.

        Args:
            agent: Specialized agent to register
        """
        self._agents[agent.role] = agent
        logger.info("Registered custom agent: %s (role: %s)", agent.name, agent.role)

    def unregister_agent(self, role: str) -> bool:
        """Unregister an agent by role.

        Args:
            role: Agent role to unregister

        Returns:
            True if agent was unregistered
        """
        if role in self._agents:
            del self._agents[role]
            logger.info("Unregistered agent: %s", role)
            return True
        return False

    def get_agent(self, role: str) -> SpecializedAgent | None:
        """Get an agent by role.

        Args:
            role: Agent role

        Returns:
            Agent or None if not found
        """
        return self._agents.get(role)

    def get_agent_by_capability(
        self,
        capability: AgentCapability,
    ) -> SpecializedAgent | None:
        """Get an agent that has a specific capability.

        Args:
            capability: Required capability

        Returns:
            First agent with the capability, or None
        """
        for agent in self._agents.values():
            if agent.has_capability(capability):
                return agent
        return None

    async def orchestrate(
        self,
        message: str,
        mode: Literal["sequential", "concurrent", "hierarchical", "dynamic", "pipeline"]
        | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Orchestrate multiple agents to process a message.

        Args:
            message: Input message
            mode: Orchestration mode (uses config default if not specified)
            context: Optional context information

        Returns:
            Final response
        """
        if not self.config.enabled:
            logger.warning("Multi-agent is disabled, returning empty response")
            return ""

        start_time = time.time()
        self._metrics["total_orchestrations"] += 1

        orchestration_mode = mode or self.config.orchestration_mode
        self._metrics["mode_usage"][orchestration_mode] = (
            self._metrics["mode_usage"].get(orchestration_mode, 0) + 1
        )

        logger.info(
            "Orchestrating agents in %s mode for message: %s...",
            orchestration_mode,
            message[:100],
        )

        try:
            if orchestration_mode == "sequential":
                result = await self._orchestrate_sequential(message, context)
            elif orchestration_mode == "concurrent":
                result = await self._orchestrate_concurrent(message, context)
            elif orchestration_mode == "hierarchical":
                result = await self._orchestrate_hierarchical(message, context)
            elif orchestration_mode == "dynamic":
                result = await self._orchestrate_dynamic(message, context)
            elif orchestration_mode == "pipeline":
                result = await self._orchestrate_pipeline(message, context)
            else:
                raise ValueError(f"Unknown orchestration mode: {orchestration_mode}")

            self._metrics["successful_orchestrations"] += 1
            execution_time = (time.time() - start_time) * 1000
            self._metrics["total_time_ms"] += execution_time

            logger.info(
                "Orchestration completed in %.2fms",
                execution_time,
            )

            return result

        except Exception as exc:
            self._metrics["failed_orchestrations"] += 1
            logger.error("Orchestration failed: %s", exc, exc_info=True)
            return f"Orchestration failed: {str(exc)}"

    async def _orchestrate_sequential(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Orchestrate agents sequentially: search → analysis → response.

        Args:
            message: Input message
            context: Optional context

        Returns:
            Final response
        """
        logger.info("Running sequential orchestration")

        # Step 1: Search agent identifies what to search for
        search_result = await self._agents["search"].process(
            f"Identify what information is needed to answer: {message}",
            context,
        )

        if not search_result.success:
            return f"Search failed: {search_result.error}"

        # Step 2: Analysis agent processes the search strategy
        analysis_result = await self._agents["analysis"].process(
            f"Based on this search strategy: {search_result.output}\n\n"
            f"Analyze how to answer: {message}",
            context,
        )

        if not analysis_result.success:
            return f"Analysis failed: {analysis_result.error}"

        # Step 3: Response agent generates final response
        response_result = await self._agents["response"].process(
            f"Based on this analysis: {analysis_result.output}\n\n"
            f"Generate a response to: {message}",
            context,
        )

        if not response_result.success:
            return f"Response generation failed: {response_result.error}"

        logger.info("Sequential orchestration completed successfully")
        return response_result.output

    async def _orchestrate_concurrent(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Orchestrate agents concurrently and combine results.

        Args:
            message: Input message
            context: Optional context

        Returns:
            Combined response
        """
        logger.info("Running concurrent orchestration")

        # Run multiple agents concurrently
        tasks = [
            self._agents["search"].process(f"Search perspective on: {message}", context),
            self._agents["analysis"].process(f"Analysis perspective on: {message}", context),
            self._agents["response"].process(f"Direct response to: {message}", context),
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

    async def _orchestrate_hierarchical(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Orchestrate agents hierarchically with a coordinator.

        Args:
            message: Input message
            context: Optional context

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
                "which specialized agents should be involved. "
                "Available agents: search, analysis, response, code, summary, "
                "translation, reasoning, planning, creative, math.\n\n"
                "Respond with a comma-separated list of agent roles to use, "
                "in the order they should be executed."
            ),
        )

        # Get execution plan from coordinator
        plan_result = await coordinator.run(f"Which agents should handle: {message}")
        agent_roles = [role.strip().lower() for role in plan_result.output.split(",")]

        logger.info("Coordinator selected agents: %s", agent_roles)

        # Execute selected agents sequentially
        accumulated_context = message
        final_result = ""

        for role in agent_roles:
            if role in self._agents:
                result = await self._agents[role].process(
                    accumulated_context,
                    context,
                )
                if result.success:
                    accumulated_context = f"{accumulated_context}\n\n{role} output: {result.output}"
                    final_result = result.output

        return final_result or await self._orchestrate_sequential(message, context)

    async def _orchestrate_dynamic(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Dynamically select and orchestrate agents based on task analysis.

        Args:
            message: Input message
            context: Optional context

        Returns:
            Final response
        """
        logger.info("Running dynamic orchestration")

        # Analyze the task
        task_type = self._analyzer.analyze(message)
        complexity = self._analyzer.analyze_complexity(message)

        logger.info(
            "Task analysis: type=%s, complexity=%d",
            task_type.value,
            complexity,
        )

        # Select agents based on task type
        selected_agents = self._select_agents_for_task(task_type, complexity)

        logger.info("Selected agents: %s", [a.role for a in selected_agents])

        # Route to appropriate model if enabled
        if self.enable_routing:
            task = Task(content=message, task_type=task_type)
            optimal_model = self._router.route(task)

            # Update agents to use optimal model
            for agent in selected_agents:
                if agent.model != optimal_model:
                    agent.update_model(optimal_model)

        # Execute selected agents
        if len(selected_agents) == 1:
            result = await selected_agents[0].process(message, context)
            return result.output if result.success else f"Error: {result.error}"

        # Multiple agents - chain them
        accumulated = message
        for agent in selected_agents:
            result = await agent.process(accumulated, context)
            if not result.success:
                return f"Agent {agent.name} failed: {result.error}"
            accumulated = f"Previous output: {result.output}\n\nOriginal request: {message}"

        return result.output

    async def _orchestrate_pipeline(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Orchestrate agents in a pipeline with data flow.

        Args:
            message: Input message
            context: Optional context

        Returns:
            Final response
        """
        logger.info("Running pipeline orchestration")

        # Create execution plan
        task = Task(content=message, task_type=self._analyzer.analyze(message))
        plan = await self._planner.create_plan(task)

        # Execute plan steps
        results: list[AgentResult] = []
        accumulated_context = {"original_message": message, "step_outputs": []}

        for step in plan.steps:
            step.mark_started()

            # Select agent for this step
            agent = self._select_agent_for_step(step)
            if not agent:
                agent = self._agents.get("response", list(self._agents.values())[0])

            # Build prompt with accumulated context
            prompt = self._build_step_prompt(step, accumulated_context)

            # Execute step
            result = await agent.process(prompt, context)
            results.append(result)

            if result.success:
                step.mark_completed(result)
                accumulated_context["step_outputs"].append(
                    {"step": step.id, "output": result.output}
                )
            else:
                step.mark_failed(result.error or "Unknown error")
                logger.warning("Step %s failed: %s", step.id, result.error)

        # Aggregate results
        return self._aggregate_results(results, message)

    def _select_agents_for_task(
        self,
        task_type: TaskType,
        complexity: int,
    ) -> list[SpecializedAgent]:
        """Select appropriate agents for a task.

        Args:
            task_type: Type of task
            complexity: Task complexity (1-10)

        Returns:
            List of selected agents
        """
        # Map task types to primary agents
        type_to_agent: dict[TaskType, str] = {
            TaskType.SEARCH: "search",
            TaskType.ANALYSIS: "analysis",
            TaskType.CODE: "code",
            TaskType.SUMMARY: "summary",
            TaskType.TRANSLATION: "translation",
            TaskType.REASONING: "reasoning",
            TaskType.PLANNING: "planning",
            TaskType.CREATIVE: "creative",
            TaskType.MATH: "math",
            TaskType.GENERAL: "response",
            TaskType.CONVERSATION: "response",
        }

        primary_role = type_to_agent.get(task_type, "response")
        selected = []

        # Add primary agent
        if primary_role in self._agents:
            selected.append(self._agents[primary_role])

        # For complex tasks, add supporting agents
        if complexity >= 7:
            if "analysis" not in [a.role for a in selected] and "analysis" in self._agents:
                selected.insert(0, self._agents["analysis"])

            if "response" not in [a.role for a in selected] and "response" in self._agents:
                selected.append(self._agents["response"])

        if selected:
            return selected
        return [self._agents.get("response", list(self._agents.values())[0])]

    def _select_agent_for_step(self, step: Task) -> SpecializedAgent | None:
        """Select an agent for a specific step.

        Args:
            step: Task step

        Returns:
            Selected agent or None
        """
        # Map task type to agent role
        type_to_role: dict[TaskType, str] = {
            TaskType.SEARCH: "search",
            TaskType.ANALYSIS: "analysis",
            TaskType.CODE: "code",
            TaskType.SUMMARY: "summary",
            TaskType.TRANSLATION: "translation",
            TaskType.REASONING: "reasoning",
            TaskType.PLANNING: "planning",
            TaskType.CREATIVE: "creative",
            TaskType.MATH: "math",
        }

        role = type_to_role.get(step.task_type)
        if role and role in self._agents:
            return self._agents[role]

        return None

    def _build_step_prompt(
        self,
        step: Task,
        accumulated_context: dict[str, Any],
    ) -> str:
        """Build prompt for a step with accumulated context.

        Args:
            step: Current step
            accumulated_context: Context from previous steps

        Returns:
            Prompt string
        """
        prompt_parts = [f"Task: {step.content}"]

        # Add context from previous steps
        if accumulated_context.get("step_outputs"):
            prompt_parts.append("\nPrevious step outputs:")
            for output in accumulated_context["step_outputs"][-3:]:  # Last 3 outputs
                prompt_parts.append(f"- {output['output'][:500]}")

        prompt_parts.append(f"\nOriginal request: {accumulated_context['original_message']}")

        return "\n".join(prompt_parts)

    def _aggregate_results(
        self,
        results: list[AgentResult],
        original_message: str,
    ) -> str:
        """Aggregate results from multiple agents.

        Args:
            results: List of agent results
            original_message: Original user message

        Returns:
            Aggregated response
        """
        successful_results = [r for r in results if r.success]

        if not successful_results:
            return "Unable to process the request. All agents failed."

        # If only one result, return it directly
        if len(successful_results) == 1:
            return successful_results[0].output

        # Return the last successful result (final step)
        return successful_results[-1].output

    async def delegate_task(
        self,
        task: Task,
        agent_role: str | None = None,
    ) -> AgentResult:
        """Delegate a task to a specific agent or auto-select.

        Args:
            task: Task to delegate
            agent_role: Specific agent role (auto-select if None)

        Returns:
            Agent result
        """
        # Select agent
        if agent_role and agent_role in self._agents:
            agent = self._agents[agent_role]
        else:
            agents = self._select_agents_for_task(task.task_type, 5)
            agent = agents[0] if agents else list(self._agents.values())[0]

        # Route to model if enabled
        if self.enable_routing:
            optimal_model = self._router.route(task)
            if agent.model != optimal_model:
                agent.update_model(optimal_model)

        # Execute
        task.assigned_agent = agent.name
        task.mark_started()

        result = await agent.process(task.content, task.context)

        if result.success:
            task.mark_completed(result)
        else:
            task.mark_failed(result.error or "Unknown error")

        return result

    async def execute_plan(self, plan: ExecutionPlan) -> list[AgentResult]:
        """Execute an execution plan.

        Args:
            plan: Plan to execute

        Returns:
            List of results from each step
        """
        logger.info("Executing plan: %s with %d steps", plan.id, len(plan.steps))

        plan.status = TaskStatus.RUNNING
        results: list[AgentResult] = []

        for step in plan.steps:
            result = await self.delegate_task(step)
            results.append(result)

            if not result.success:
                logger.warning("Step %s failed, continuing...", step.id)

        plan.status = TaskStatus.COMPLETED if plan.is_complete() else TaskStatus.FAILED

        logger.info(
            "Plan %s completed: %d/%d steps successful",
            plan.id,
            sum(1 for r in results if r.success),
            len(results),
        )

        return results

    def route_to_model(
        self,
        task_content: str,
        task_type: TaskType | None = None,
    ) -> str:
        """Route a task to the most appropriate model.

        Args:
            task_content: Task content
            task_type: Optional task type (auto-detected if None)

        Returns:
            Model name
        """
        if task_type is None:
            task_type = self._analyzer.analyze(task_content)

        task = Task(content=task_content, task_type=task_type)
        return self._router.route(task)

    def analyze_task(self, content: str) -> dict[str, Any]:
        """Analyze a task and return its characteristics.

        Args:
            content: Task content

        Returns:
            Task analysis results
        """
        task_type = self._analyzer.analyze(content)
        complexity = self._analyzer.analyze_complexity(content)
        suggested_strategy = self._analyzer.suggest_strategy(task_type, complexity)

        return {
            "task_type": task_type.value,
            "complexity": complexity,
            "suggested_strategy": suggested_strategy.value,
            "suggested_agents": [
                a.role for a in self._select_agents_for_task(task_type, complexity)
            ],
            "suggested_model": self.route_to_model(content, task_type),
        }

    def get_stats(self) -> dict[str, Any]:
        """Get orchestrator statistics.

        Returns:
            Dictionary with orchestrator statistics
        """
        agent_stats = {role: agent.get_stats() for role, agent in self._agents.items()}

        total = self._metrics["total_orchestrations"]
        successful = self._metrics["successful_orchestrations"]

        return {
            "enabled": self.config.enabled,
            "mode": self.config.orchestration_mode,
            "routing_enabled": self.enable_routing,
            "agent_count": len(self._agents),
            "agents": [
                {"name": agent.name, "role": agent.role, "model": agent.model}
                for agent in self._agents.values()
            ],
            "total_orchestrations": total,
            "successful_orchestrations": successful,
            "failed_orchestrations": self._metrics["failed_orchestrations"],
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "avg_time_ms": (self._metrics["total_time_ms"] / total if total > 0 else 0),
            "mode_usage": self._metrics["mode_usage"],
            "agent_stats": agent_stats,
            "router_stats": self._router.get_stats(),
            "planner_stats": self._planner.get_stats(),
        }

    def get_available_agents(self) -> list[str]:
        """Get list of available agent roles.

        Returns:
            List of agent roles
        """
        return list(self._agents.keys())

    def get_available_modes(self) -> list[str]:
        """Get list of available orchestration modes.

        Returns:
            List of mode names
        """
        return ["sequential", "concurrent", "hierarchical", "dynamic", "pipeline"]
