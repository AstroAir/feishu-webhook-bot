#!/usr/bin/env python3
"""Multi-Agent Orchestration Example.

This example demonstrates multi-agent orchestration (A2A):
- Creating specialized agents
- Agent orchestration patterns (sequential, concurrent, hierarchical)
- Agent-to-agent communication
- Task delegation and coordination
- Result aggregation
- Error handling in multi-agent systems

The multi-agent system enables complex task decomposition and parallel processing.
"""

import asyncio
import os
from typing import Any

from feishu_webhook_bot.core import LoggingConfig, get_logger, setup_logging

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)

# Check for AI dependencies
try:
    from feishu_webhook_bot.ai import (
        AgentMessage,
        AgentOrchestrator,
        AgentResult,
        AnalysisAgent,
        ResponseAgent,
        SearchAgent,
        SpecializedAgent,
    )
    from feishu_webhook_bot.ai.config import MultiAgentConfig

    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("AI dependencies not available. Install with: pip install pydantic-ai")


# =============================================================================
# Demo 1: Specialized Agent Creation
# =============================================================================
def demo_specialized_agent() -> None:
    """Demonstrate creating specialized agents."""
    print("\n" + "=" * 60)
    print("Demo 1: Specialized Agent Creation")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    # Create a custom specialized agent
    agent = SpecializedAgent(
        name="code_reviewer",
        role="Code Review Expert",
        system_prompt="""You are an expert code reviewer. 
        Analyze code for:
        - Best practices
        - Potential bugs
        - Performance issues
        - Security vulnerabilities
        Provide constructive feedback.""",
        model="openai:gpt-4o",
    )

    print(f"Created specialized agent:")
    print(f"  Name: {agent.name}")
    print(f"  Role: {agent.role}")
    print(f"  Model: {agent.model}")


# =============================================================================
# Demo 2: Pre-built Specialized Agents
# =============================================================================
def demo_prebuilt_agents() -> None:
    """Demonstrate pre-built specialized agents."""
    print("\n" + "=" * 60)
    print("Demo 2: Pre-built Specialized Agents")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    # SearchAgent - for information retrieval
    search_agent = SearchAgent(model="openai:gpt-4o")
    print(f"SearchAgent:")
    print(f"  Name: {search_agent.name}")
    print(f"  Role: {search_agent.role}")

    # AnalysisAgent - for data analysis
    analysis_agent = AnalysisAgent(model="openai:gpt-4o")
    print(f"\nAnalysisAgent:")
    print(f"  Name: {analysis_agent.name}")
    print(f"  Role: {analysis_agent.role}")

    # ResponseAgent - for generating responses
    response_agent = ResponseAgent(model="openai:gpt-4o")
    print(f"\nResponseAgent:")
    print(f"  Name: {response_agent.name}")
    print(f"  Role: {response_agent.role}")


# =============================================================================
# Demo 3: Agent Message Passing
# =============================================================================
def demo_agent_messages() -> None:
    """Demonstrate agent-to-agent message passing."""
    print("\n" + "=" * 60)
    print("Demo 3: Agent Message Passing")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    # Create messages between agents
    messages = [
        AgentMessage(
            from_agent="orchestrator",
            to_agent="search_agent",
            content="Find information about Python async programming",
            metadata={"priority": "high", "task_id": "task_001"},
        ),
        AgentMessage(
            from_agent="search_agent",
            to_agent="analysis_agent",
            content="Here are the search results: ...",
            metadata={"source": "web_search", "results_count": 10},
        ),
        AgentMessage(
            from_agent="analysis_agent",
            to_agent="response_agent",
            content="Key findings: async/await syntax, event loops, ...",
            metadata={"analysis_type": "summary"},
        ),
    ]

    print("Agent message flow:")
    for i, msg in enumerate(messages, 1):
        print(f"\n  Message {i}:")
        print(f"    From: {msg.from_agent}")
        print(f"    To: {msg.to_agent}")
        print(f"    Content: {msg.content[:50]}...")
        print(f"    Metadata: {msg.metadata}")


# =============================================================================
# Demo 4: Agent Results
# =============================================================================
def demo_agent_results() -> None:
    """Demonstrate agent result handling."""
    print("\n" + "=" * 60)
    print("Demo 4: Agent Results")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    # Successful result
    success_result = AgentResult(
        agent_name="search_agent",
        output="Found 5 relevant articles about Python async programming",
        success=True,
        metadata={
            "execution_time": 1.5,
            "sources": ["docs.python.org", "realpython.com"],
        },
    )

    print("Successful result:")
    print(f"  Agent: {success_result.agent_name}")
    print(f"  Success: {success_result.success}")
    print(f"  Output: {success_result.output}")
    print(f"  Metadata: {success_result.metadata}")

    # Failed result
    failed_result = AgentResult(
        agent_name="analysis_agent",
        output="",
        success=False,
        error="Timeout while processing large dataset",
        metadata={"attempted_records": 10000},
    )

    print("\nFailed result:")
    print(f"  Agent: {failed_result.agent_name}")
    print(f"  Success: {failed_result.success}")
    print(f"  Error: {failed_result.error}")


# =============================================================================
# Demo 5: Agent Orchestrator Setup
# =============================================================================
async def demo_orchestrator_setup() -> None:
    """Demonstrate agent orchestrator setup."""
    print("\n" + "=" * 60)
    print("Demo 5: Agent Orchestrator Setup")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    # Create configuration
    config = MultiAgentConfig(
        enabled=True,
        max_agents=10,
        default_timeout=30.0,
        orchestration_mode="sequential",
    )

    print("MultiAgentConfig:")
    print(f"  Enabled: {config.enabled}")
    print(f"  Max agents: {config.max_agents}")
    print(f"  Default timeout: {config.default_timeout}s")
    print(f"  Orchestration mode: {config.orchestration_mode}")

    # Create orchestrator
    orchestrator = AgentOrchestrator(config)

    print("\nAgentOrchestrator created")
    print("Orchestration modes available:")
    print("  - sequential: Agents run one after another")
    print("  - concurrent: Agents run in parallel")
    print("  - hierarchical: Agents organized in hierarchy")


# =============================================================================
# Demo 6: Sequential Orchestration
# =============================================================================
async def demo_sequential_orchestration() -> None:
    """Demonstrate sequential agent orchestration."""
    print("\n" + "=" * 60)
    print("Demo 6: Sequential Orchestration")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    print("Sequential orchestration pattern:")
    print("""
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │   Search    │ ──> │  Analysis   │ ──> │  Response   │
    │   Agent     │     │   Agent     │     │   Agent     │
    └─────────────┘     └─────────────┘     └─────────────┘
    
    1. Search Agent finds relevant information
    2. Analysis Agent processes and summarizes
    3. Response Agent generates final output
    """)

    # Simulated sequential execution
    print("Simulated execution:")
    steps = [
        ("SearchAgent", "Searching for information...", 0.5),
        ("AnalysisAgent", "Analyzing search results...", 0.3),
        ("ResponseAgent", "Generating response...", 0.2),
    ]

    for agent, action, delay in steps:
        print(f"  [{agent}] {action}")
        await asyncio.sleep(delay)

    print("\nSequential execution complete!")


# =============================================================================
# Demo 7: Concurrent Orchestration
# =============================================================================
async def demo_concurrent_orchestration() -> None:
    """Demonstrate concurrent agent orchestration."""
    print("\n" + "=" * 60)
    print("Demo 7: Concurrent Orchestration")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    print("Concurrent orchestration pattern:")
    print("""
                    ┌─────────────┐
                ┌──>│  Agent A    │──┐
                │   └─────────────┘  │
    ┌───────┐   │   ┌─────────────┐  │   ┌───────────┐
    │ Input │───┼──>│  Agent B    │──┼──>│ Aggregate │
    └───────┘   │   └─────────────┘  │   └───────────┘
                │   ┌─────────────┐  │
                └──>│  Agent C    │──┘
                    └─────────────┘
    
    All agents run in parallel, results are aggregated.
    """)

    # Simulated concurrent execution
    async def simulate_agent(name: str, delay: float) -> AgentResult:
        print(f"  [{name}] Starting...")
        await asyncio.sleep(delay)
        print(f"  [{name}] Complete!")
        return AgentResult(
            agent_name=name,
            output=f"Result from {name}",
            success=True,
        )

    print("Simulated concurrent execution:")
    tasks = [
        simulate_agent("AgentA", 0.3),
        simulate_agent("AgentB", 0.5),
        simulate_agent("AgentC", 0.2),
    ]

    results = await asyncio.gather(*tasks)

    print("\nResults aggregated:")
    for result in results:
        print(f"  {result.agent_name}: {result.output}")


# =============================================================================
# Demo 8: Hierarchical Orchestration
# =============================================================================
async def demo_hierarchical_orchestration() -> None:
    """Demonstrate hierarchical agent orchestration."""
    print("\n" + "=" * 60)
    print("Demo 8: Hierarchical Orchestration")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    print("Hierarchical orchestration pattern:")
    print("""
                    ┌─────────────────┐
                    │   Coordinator   │
                    │     Agent       │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
    ┌───────▼───────┐ ┌──────▼──────┐ ┌───────▼───────┐
    │   Research    │ │   Writing   │ │   Review      │
    │   Team Lead   │ │  Team Lead  │ │  Team Lead    │
    └───────┬───────┘ └──────┬──────┘ └───────┬───────┘
            │                │                │
       ┌────┴────┐      ┌────┴────┐      ┌────┴────┐
       │ Workers │      │ Workers │      │ Workers │
       └─────────┘      └─────────┘      └─────────┘
    
    Coordinator delegates to team leads, who manage workers.
    """)

    # Simulated hierarchical execution
    print("Simulated hierarchical execution:")

    async def team_work(team_name: str, workers: int) -> str:
        print(f"  [{team_name} Lead] Delegating to {workers} workers...")
        await asyncio.sleep(0.2)
        for i in range(workers):
            print(f"    [{team_name} Worker {i + 1}] Working...")
            await asyncio.sleep(0.1)
        print(f"  [{team_name} Lead] Team complete!")
        return f"{team_name} results"

    print("\n[Coordinator] Starting task delegation...")

    teams = [
        ("Research", 2),
        ("Writing", 3),
        ("Review", 2),
    ]

    results = await asyncio.gather(*[team_work(name, workers) for name, workers in teams])

    print("\n[Coordinator] All teams complete!")
    print(f"  Results: {results}")


# =============================================================================
# Demo 9: Error Handling in Multi-Agent Systems
# =============================================================================
async def demo_error_handling() -> None:
    """Demonstrate error handling in multi-agent systems."""
    print("\n" + "=" * 60)
    print("Demo 9: Error Handling in Multi-Agent Systems")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    print("Error handling strategies:")

    # Strategy 1: Retry with fallback
    print("\n1. Retry with Fallback:")
    print("""
    async def execute_with_retry(agent, task, max_retries=3):
        for attempt in range(max_retries):
            try:
                result = await agent.process(task)
                if result.success:
                    return result
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
        
        # Fallback to simpler agent
        return await fallback_agent.process(task)
    """)

    # Strategy 2: Circuit breaker per agent
    print("2. Circuit Breaker per Agent:")
    print("""
    Each agent has its own circuit breaker:
    - Opens after N failures
    - Prevents cascading failures
    - Auto-recovers after timeout
    """)

    # Strategy 3: Graceful degradation
    print("3. Graceful Degradation:")
    print("""
    If specialized agent fails:
    1. Try alternative agent with similar capability
    2. Fall back to general-purpose agent
    3. Return partial results with warning
    """)

    # Simulated error handling
    print("\n--- Simulated Error Handling ---")

    async def unreliable_agent(name: str, fail_rate: float = 0.5) -> AgentResult:
        import random

        if random.random() < fail_rate:
            return AgentResult(
                agent_name=name,
                output="",
                success=False,
                error="Simulated failure",
            )
        return AgentResult(
            agent_name=name,
            output=f"Success from {name}",
            success=True,
        )

    # Execute with retry
    max_retries = 3
    for attempt in range(max_retries):
        result = await unreliable_agent("TestAgent", fail_rate=0.7)
        if result.success:
            print(f"  Attempt {attempt + 1}: Success!")
            break
        else:
            print(f"  Attempt {attempt + 1}: Failed - {result.error}")
    else:
        print("  All attempts failed, using fallback")


# =============================================================================
# Demo 10: Real-World Multi-Agent Pattern
# =============================================================================
async def demo_real_world_pattern() -> None:
    """Demonstrate a real-world multi-agent pattern."""
    print("\n" + "=" * 60)
    print("Demo 10: Real-World Multi-Agent Pattern")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    class ResearchAssistant:
        """Multi-agent research assistant."""

        def __init__(self):
            self.agents: dict[str, Any] = {}
            self._setup_agents()

        def _setup_agents(self) -> None:
            """Setup specialized agents."""
            # In real implementation, these would be actual agents
            self.agents = {
                "planner": "Plans research strategy",
                "searcher": "Searches for information",
                "analyzer": "Analyzes findings",
                "writer": "Writes summaries",
                "reviewer": "Reviews output quality",
            }

        async def research(self, topic: str) -> dict[str, Any]:
            """Conduct research on a topic."""
            print(f"Researching: {topic}")
            results = {}

            # Step 1: Planning
            print("\n  [Planner] Creating research plan...")
            await asyncio.sleep(0.2)
            results["plan"] = f"Research plan for: {topic}"

            # Step 2: Searching (parallel)
            print("  [Searcher] Searching multiple sources...")
            await asyncio.sleep(0.3)
            results["sources"] = ["Source A", "Source B", "Source C"]

            # Step 3: Analysis
            print("  [Analyzer] Analyzing findings...")
            await asyncio.sleep(0.2)
            results["analysis"] = "Key findings summarized"

            # Step 4: Writing
            print("  [Writer] Writing summary...")
            await asyncio.sleep(0.2)
            results["summary"] = f"Summary of research on {topic}"

            # Step 5: Review
            print("  [Reviewer] Reviewing output...")
            await asyncio.sleep(0.1)
            results["quality_score"] = 0.95

            return results

    # Use the research assistant
    assistant = ResearchAssistant()

    print("ResearchAssistant agents:")
    for name, role in assistant.agents.items():
        print(f"  - {name}: {role}")

    # Conduct research
    print("\n--- Conducting Research ---")
    results = await assistant.research("Python async programming best practices")

    print("\n--- Research Results ---")
    for key, value in results.items():
        print(f"  {key}: {value}")


# =============================================================================
# Main Entry Point
# =============================================================================
async def main() -> None:
    """Run all multi-agent demonstrations."""
    print("=" * 60)
    print("Multi-Agent Orchestration Examples")
    print("=" * 60)

    demos = [
        ("Specialized Agent Creation", demo_specialized_agent),
        ("Pre-built Specialized Agents", demo_prebuilt_agents),
        ("Agent Message Passing", demo_agent_messages),
        ("Agent Results", demo_agent_results),
        ("Agent Orchestrator Setup", demo_orchestrator_setup),
        ("Sequential Orchestration", demo_sequential_orchestration),
        ("Concurrent Orchestration", demo_concurrent_orchestration),
        ("Hierarchical Orchestration", demo_hierarchical_orchestration),
        ("Error Handling", demo_error_handling),
        ("Real-World Multi-Agent Pattern", demo_real_world_pattern),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            if asyncio.iscoroutinefunction(demo_func):
                await demo_func()
            else:
                demo_func()
        except Exception as e:
            print(f"\nDemo {i} ({name}) failed with error: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print("All demonstrations completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
