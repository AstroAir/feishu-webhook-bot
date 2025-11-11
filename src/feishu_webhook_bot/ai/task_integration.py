"""Integration between AI agent and automated task system.

This module provides functionality to use AI capabilities within automated tasks,
enabling intelligent task execution with natural language processing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from ..core.logger import get_logger

if TYPE_CHECKING:
    from ..core.config import TaskActionConfig
    from .agent import AIAgent

logger = get_logger("ai.task_integration")


class AITaskResult(BaseModel):
    """Result from an AI task action.

    Attributes:
        success: Whether the AI action succeeded
        response: The AI response text
        confidence: Confidence level of the response (if structured output enabled)
        sources_used: List of sources used (e.g., web search results)
        tools_called: List of tools that were called
        error: Error message if the action failed
        metadata: Additional metadata about the execution
    """

    success: bool = Field(description="Whether the AI action succeeded")
    response: str = Field(description="The AI response text")
    confidence: float | None = Field(
        default=None,
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
    error: str | None = Field(
        default=None,
        description="Error message if the action failed",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class AITaskExecutor:
    """Executor for AI-powered task actions.

    This class handles the execution of AI chat and query actions within
    the automated task system, providing proper context management and
    error handling.
    """

    def __init__(self, ai_agent: AIAgent | None = None) -> None:
        """Initialize the AI task executor.

        Args:
            ai_agent: AI agent instance to use for task execution
        """
        self.ai_agent = ai_agent
        logger.info(
            "AITaskExecutor initialized (AI agent: %s)", "enabled" if ai_agent else "disabled"
        )

    async def execute_ai_action(
        self,
        action: TaskActionConfig,
        context: dict[str, Any],
    ) -> AITaskResult:
        """Execute an AI chat or query action.

        Args:
            action: Task action configuration
            context: Execution context with parameters and variables

        Returns:
            AITaskResult with the AI response and metadata

        Raises:
            RuntimeError: If AI agent is not available
            ValueError: If action configuration is invalid
        """
        if not self.ai_agent:
            error_msg = "AI agent not available - ensure AI is enabled in configuration"
            logger.error(error_msg)
            return AITaskResult(
                success=False,
                response="",
                error=error_msg,
            )

        if not action.ai_prompt:
            error_msg = "ai_prompt is required for AI actions"
            logger.error(error_msg)
            return AITaskResult(
                success=False,
                response="",
                error=error_msg,
            )

        try:
            # Build the prompt with context substitution
            prompt = self._build_prompt(action.ai_prompt, context)

            # Determine user ID (use from action or default)
            user_id = action.ai_user_id or context.get("user_id", "task_system")

            logger.info(
                "Executing AI action for user '%s' with prompt: %s",
                user_id,
                prompt[:100] + "..." if len(prompt) > 100 else prompt,
            )

            # Temporarily override AI config if specified
            original_config = None
            if (
                action.ai_system_prompt
                or action.ai_temperature is not None
                or action.ai_max_tokens is not None
            ):
                original_config = self._save_and_override_config(action)

            try:
                # Execute AI chat
                if action.ai_structured_output:
                    # Use structured output
                    response = await self.ai_agent.chat(user_id, prompt)

                    # Extract structured response
                    if hasattr(response, "message"):
                        result = AITaskResult(
                            success=True,
                            response=response.message,
                            confidence=getattr(response, "confidence", None),
                            sources_used=getattr(response, "sources_used", []),
                            tools_called=getattr(response, "tools_called", []),
                        )
                    else:
                        result = AITaskResult(
                            success=True,
                            response=str(response),
                        )
                else:
                    # Use regular string output
                    response = await self.ai_agent.chat(user_id, prompt)
                    result = AITaskResult(
                        success=True,
                        response=str(response),
                    )

                # Save response to context if requested
                if action.ai_save_response_as:
                    context[action.ai_save_response_as] = result.response
                    logger.debug("Saved AI response to context as '%s'", action.ai_save_response_as)

                logger.info("AI action completed successfully")
                return result

            finally:
                # Restore original config if it was overridden
                if original_config:
                    self._restore_config(original_config)

        except Exception as e:
            error_msg = f"AI action failed: {e}"
            logger.error(error_msg, exc_info=True)
            return AITaskResult(
                success=False,
                response="",
                error=error_msg,
            )

    def _build_prompt(self, prompt_template: str, context: dict[str, Any]) -> str:
        """Build the AI prompt with context variable substitution.

        Args:
            prompt_template: Prompt template with ${variable} placeholders
            context: Context dictionary with variable values

        Returns:
            Prompt with variables substituted
        """
        prompt = prompt_template

        # Simple variable substitution
        for key, value in context.items():
            placeholder = f"${{{key}}}"
            if placeholder in prompt:
                prompt = prompt.replace(placeholder, str(value))

        return prompt

    def _save_and_override_config(self, action: TaskActionConfig) -> dict[str, Any]:
        """Save current AI config and apply overrides.

        Args:
            action: Task action with config overrides

        Returns:
            Dictionary with original config values
        """
        if not self.ai_agent:
            return {}

        original: dict[str, Any] = {}

        if action.ai_system_prompt:
            original["system_prompt"] = self.ai_agent.config.system_prompt
            # Note: pydantic-ai Agent doesn't support runtime system_prompt changes
            # This would require recreating the agent, which we'll skip for now
            logger.warning(
                "System prompt override not supported at runtime - using original prompt"
            )

        if action.ai_temperature is not None:
            original["temperature"] = self.ai_agent.config.temperature
            self.ai_agent.config.temperature = action.ai_temperature

        if action.ai_max_tokens is not None:
            original["max_tokens"] = self.ai_agent.config.max_tokens
            self.ai_agent.config.max_tokens = action.ai_max_tokens

        return original

    def _restore_config(self, original_config: dict[str, Any]) -> None:
        """Restore original AI config.

        Args:
            original_config: Dictionary with original config values
        """
        if not self.ai_agent:
            return

        if "temperature" in original_config:
            self.ai_agent.config.temperature = original_config["temperature"]

        if "max_tokens" in original_config:
            self.ai_agent.config.max_tokens = original_config["max_tokens"]


async def execute_ai_task_action(
    action: TaskActionConfig,
    context: dict[str, Any],
    ai_agent: AIAgent | None = None,
) -> AITaskResult:
    """Convenience function to execute an AI task action.

    Args:
        action: Task action configuration
        context: Execution context
        ai_agent: AI agent instance (optional)

    Returns:
        AITaskResult with the AI response and metadata
    """
    executor = AITaskExecutor(ai_agent)
    return await executor.execute_ai_action(action, context)
