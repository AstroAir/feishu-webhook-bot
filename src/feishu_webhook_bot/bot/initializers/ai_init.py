"""AI agent and chat controller initialization mixin for FeishuBot."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...chat.controller import ChatConfig, create_chat_controller
from ...core import get_logger

if TYPE_CHECKING:
    from ..base import BotBase

logger = get_logger("bot.init.ai")


class AIInitializerMixin:
    """Mixin for AI agent and chat controller initialization."""

    def _init_ai_agent(self: BotBase) -> None:
        """Initialize AI agent if configured."""
        ai_config = getattr(self.config, "ai", None)
        if not ai_config:
            logger.info("AI agent disabled")
            return

        enabled_flag = getattr(ai_config, "enabled", None)
        if not isinstance(enabled_flag, bool) or not enabled_flag:
            logger.info("AI agent disabled")
            return

        try:
            from ...ai import AIAgent
            from ...ai.config import AIConfig

            # Convert to AIConfig if it's a dict
            if isinstance(ai_config, dict):
                ai_config = AIConfig(**ai_config)
            elif not hasattr(ai_config, "enabled"):
                logger.warning("Invalid AI configuration, skipping AI agent initialization")
                return

            self.ai_agent = AIAgent(ai_config)
            logger.info("AI agent initialized with model: %s", ai_config.model)
        except ImportError as exc:
            logger.error("Failed to import AI modules: %s", exc, exc_info=True)
        except Exception as exc:
            logger.error("Failed to initialize AI agent: %s", exc, exc_info=True)

    def _init_chat_controller(self: BotBase) -> None:
        """Initialize chat controller for unified message handling."""
        # Check if chat configuration is available
        chat_config = getattr(self.config, "chat", None)
        if chat_config is None:
            # Use default configuration
            chat_config = ChatConfig()

        if not chat_config.enabled:
            logger.info("Chat controller disabled")
            return

        # Get available models from AI configuration
        ai_config = getattr(self.config, "ai", None)
        available_models = None
        if ai_config:
            available_models = getattr(ai_config, "available_models", None)

        conversation_store = None
        if ai_config is not None:
            persistence_config = getattr(ai_config, "conversation_persistence", None)
            if persistence_config and getattr(persistence_config, "enabled", False):
                try:
                    from ...ai.conversation_store import PersistentConversationManager

                    conversation_store = PersistentConversationManager(
                        db_url=persistence_config.database_url,
                        echo=False,
                    )
                except Exception as exc:
                    logger.error(
                        "Failed to initialize conversation store: %s",
                        exc,
                        exc_info=True,
                    )

        try:
            self.chat_controller = create_chat_controller(
                ai_agent=self.ai_agent,
                providers=self.providers,
                config=chat_config,
                available_models=available_models,
                conversation_store=conversation_store,
            )
            logger.info("Chat controller initialized")
        except Exception as e:
            logger.error("Failed to initialize chat controller: %s", e, exc_info=True)
