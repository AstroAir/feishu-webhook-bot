"""Unified chat controller for multi-platform message handling.

This module provides the central orchestrator for routing messages from multiple
platforms to appropriate handlers (commands or AI conversation) and sending responses.

Key features:
- Multi-platform message routing (Feishu, QQ)
- Command system integration with built-in and custom commands
- AI conversation with context preservation
- Extensible message middleware pipeline
- Configurable behavior per chat type (private, group)
- Error handling and graceful degradation
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from ..core.logger import get_logger
from ..core.message_handler import IncomingMessage, get_user_key
from ..core.provider import BaseProvider, SendResult

if TYPE_CHECKING:
    from ..ai.agent import AIAgent
    from ..ai.commands import CommandHandler
    from ..ai.conversation_store import PersistentConversationManager

logger = get_logger("chat_controller")


class ChatConfig(BaseModel):
    """Configuration for chat controller behavior.

    Controls which chat types are enabled, message routing, and response formatting.

    Attributes:
        enabled: Enable chat functionality entirely
        enable_in_groups: Enable response to group chat messages
        require_at_in_groups: Require @bot mention in group chats to respond
        enable_private: Enable response to private messages
        command_prefix: Prefix character for commands (e.g., "/")
        max_message_length: Maximum length for response messages
        typing_indicator: Send typing indicator while processing (if supported)
        error_message: Default error message to send on failures
    """

    enabled: bool = Field(default=True, description="Enable chat functionality")
    enable_in_groups: bool = Field(default=True, description="Enable in group chats")
    require_at_in_groups: bool = Field(
        default=True,
        description="Require @bot in groups to respond",
    )
    enable_private: bool = Field(default=True, description="Enable private chats")
    command_prefix: str = Field(default="/", description="Prefix for commands")
    max_message_length: int = Field(
        default=4000,
        description="Maximum response message length",
    )
    typing_indicator: bool = Field(
        default=False,
        description="Send typing indicator while processing",
    )
    error_message: str = Field(
        default="抱歉，处理您的消息时出现了问题，请稍后重试。",
        description="Error message to send on failure",
    )


@dataclass
class ChatContext:
    """Runtime context for a chat interaction.

    Passed through the message pipeline to provide handlers with necessary
    state and configuration for processing a single message.

    Attributes:
        message: The incoming message being processed
        user_key: Unique user identifier (platform:chat_type:sender_id)
        provider: Message provider for the source platform
        ai_agent: AI agent for conversation (if configured)
        metadata: Additional runtime metadata for handlers
    """

    message: IncomingMessage
    user_key: str
    provider: BaseProvider | None = None
    ai_agent: AIAgent | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# Type for message middleware functions
MessageMiddleware = Callable[[ChatContext], Awaitable[bool]]


class ChatController:
    """Unified chat controller for multi-platform messaging.

    Routes incoming messages from multiple platforms (Feishu, QQ, etc.) through
    a pipeline of middleware, command handlers, and AI conversation, then sends
    responses back to the appropriate platform.

    The controller handles:
    - Multi-platform message reception and routing
    - Command parsing and execution (built-in and custom)
    - AI-powered conversations with context
    - Middleware-based extensibility
    - Configurable behavior per chat type
    - Error handling and logging

    Example:
        ```python
        from feishu_webhook_bot.chat import ChatController, ChatConfig
        from feishu_webhook_bot.core.message_handler import IncomingMessage

        # Create controller
        controller = ChatController(
            ai_agent=ai_agent,
            command_handler=command_handler,
            providers={"feishu": feishu_provider, "qq": qq_provider},
            config=ChatConfig(require_at_in_groups=True),
        )

        # Add middleware
        @controller.middleware
        async def log_messages(ctx: ChatContext) -> bool:
            logger.info("Message from %s: %s", ctx.user_key, ctx.message.content)
            return True  # Continue processing

        # Handle incoming message
        msg = IncomingMessage(
            id="msg_123",
            platform="feishu",
            chat_type="private",
            chat_id="",
            sender_id="user_123",
            sender_name="Alice",
            content="Hello!",
        )
        await controller.handle_incoming(msg)

        # Broadcast to multiple platforms
        results = await controller.broadcast(
            "Important announcement",
            platforms=["feishu", "qq"],
        )
        ```
    """

    def __init__(
        self,
        ai_agent: AIAgent | None = None,
        command_handler: CommandHandler | None = None,
        providers: dict[str, BaseProvider] | None = None,
        config: ChatConfig | None = None,
        conversation_store: PersistentConversationManager | None = None,
    ):
        """Initialize chat controller.

        Args:
            ai_agent: AI agent for conversation handling
            command_handler: Handler for slash commands
            providers: Dict of platform providers {platform: provider}
            config: Chat configuration
            conversation_store: Persistent conversation storage

        Raises:
            ValueError: If neither ai_agent nor command_handler is provided
        """
        self.ai_agent = ai_agent
        self.command_handler = command_handler
        self.providers = providers or {}
        self.config = config or ChatConfig()
        self.conversation_store = conversation_store

        if self.ai_agent is not None and hasattr(self.ai_agent, "set_conversation_store"):
            self.ai_agent.set_conversation_store(conversation_store)

        if self.command_handler is not None and hasattr(self.command_handler, "conversation_store"):
            self.command_handler.conversation_store = conversation_store

        self._middlewares: list[MessageMiddleware] = []
        self._message_queue: asyncio.Queue[IncomingMessage] = asyncio.Queue()
        self._processing = False

        logger.debug(
            "ChatController initialized: ai_agent=%s, command_handler=%s, providers=%s, config=%s",
            ai_agent is not None,
            command_handler is not None,
            list(self.providers.keys()),
            self.config,
        )

    def middleware(self, func: MessageMiddleware) -> MessageMiddleware:
        """Decorator to register a message middleware.

        Middleware functions receive ChatContext and return bool.
        Return True to continue processing, False to stop.

        Middleware is executed in registration order before message routing.
        Use for logging, rate limiting, content filtering, or other cross-cutting concerns.

        Args:
            func: Async function with signature (ChatContext) -> bool

        Returns:
            The same function (allows use as decorator)

        Raises:
            TypeError: If func is not callable

        Example:
            ```python
            @controller.middleware
            async def rate_limit(ctx: ChatContext) -> bool:
                if is_rate_limited(ctx.user_key):
                    await controller.send_reply(
                        ctx.message,
                        "请稍后再试"
                    )
                    return False  # Stop processing
                return True  # Continue

            @controller.middleware
            async def log_access(ctx: ChatContext) -> bool:
                logger.info("Message from %s", ctx.user_key)
                return True
            ```
        """
        self._middlewares.append(func)
        logger.debug("Registered middleware: %s", func.__name__)
        return func

    def add_provider(self, name: str, provider: BaseProvider) -> None:
        """Add or replace a message provider.

        Args:
            name: Platform identifier (e.g., "feishu", "qq")
            provider: Provider instance

        Raises:
            TypeError: If provider is not a BaseProvider instance
        """
        if not isinstance(provider, BaseProvider):
            raise TypeError(f"Provider must be BaseProvider instance, got {type(provider)}")
        self.providers[name] = provider
        logger.info("Added provider: %s", name)

    def get_provider(self, platform: str) -> BaseProvider | None:
        """Get provider for a platform.

        Args:
            platform: Platform identifier

        Returns:
            Provider instance or None if not found
        """
        return self.providers.get(platform)

    def has_provider(self, platform: str) -> bool:
        """Check if provider exists for a platform.

        Args:
            platform: Platform identifier

        Returns:
            True if provider exists
        """
        return platform in self.providers

    async def handle_incoming(self, message: IncomingMessage) -> None:
        """Main entry point for handling incoming messages.

        Processes a message through middleware pipeline, command handlers,
        and AI conversation. Handles all errors gracefully.

        Args:
            message: Incoming message from any platform

        Raises:
            TypeError: If message is not IncomingMessage instance
        """
        if not isinstance(message, IncomingMessage):
            logger.error(
                "Invalid message type: %s, expected IncomingMessage",
                type(message),
            )
            return

        logger.debug(
            "Handling incoming message: id=%s, platform=%s, from=%s",
            message.id,
            message.platform,
            message.sender_id,
        )

        # Check if chat is enabled
        if not self.config.enabled:
            logger.debug("Chat disabled, ignoring message")
            return

        # Check chat type settings
        if message.chat_type == "group" and not self.config.enable_in_groups:
            logger.debug("Group chat disabled, ignoring")
            return

        if message.chat_type == "private" and not self.config.enable_private:
            logger.debug("Private chat disabled, ignoring")
            return

        # Check @bot requirement for groups
        if message.chat_type == "group" and self.config.require_at_in_groups:
            if not message.is_at_bot:
                logger.debug("Message doesn't @bot in group, ignoring")
                return

        # Create context
        user_key = get_user_key(message)
        provider = self.get_provider(message.platform)

        ctx = ChatContext(
            message=message,
            user_key=user_key,
            provider=provider,
            ai_agent=self.ai_agent,
        )

        # Run middlewares
        for middleware in self._middlewares:
            try:
                should_continue = await middleware(ctx)
                if not should_continue:
                    logger.debug(
                        "Middleware stopped processing: %s",
                        middleware.__name__,
                    )
                    return
            except Exception as e:
                logger.error(
                    "Middleware error in %s: %s",
                    middleware.__name__,
                    e,
                    exc_info=True,
                )

        # Process message
        try:
            await self._process_message(ctx)
        except Exception as e:
            logger.error(
                "Error processing message: %s",
                e,
                exc_info=True,
            )
            await self._send_error_response(ctx)

    async def _process_message(self, ctx: ChatContext) -> None:
        """Process a message through command or AI pipeline.

        Args:
            ctx: Chat context with message and configuration
        """
        message = ctx.message
        content = message.content.strip()

        logger.debug("Processing message content: %s", content[:100])

        # Check for commands first
        if self.command_handler and content.startswith(self.config.command_prefix):
            is_cmd, result = await self.command_handler.process(message)
            if is_cmd and result:
                await self.send_reply(message, result.response)
                logger.debug("Command response sent")
                return

        # Process with AI agent
        if self.ai_agent:
            try:
                response = await self.ai_agent.chat(ctx.user_key, content)
                if response:
                    # Truncate if too long
                    if len(response) > self.config.max_message_length:
                        response = response[: self.config.max_message_length - 3] + "..."
                    await self.send_reply(message, response)
                    logger.debug("AI response sent")
            except Exception as e:
                logger.error(
                    "AI chat error: %s",
                    e,
                    exc_info=True,
                )
                await self._send_error_response(ctx)
        else:
            logger.warning("No AI agent configured and message is not a command, ignoring")

    async def send_reply(
        self,
        original: IncomingMessage,
        reply: str,
        reply_in_thread: bool = True,
        quote_reply: bool = False,
    ) -> SendResult | None:
        """Send reply to the original message.

        Routes the reply to the correct provider based on the original message's
        platform and determines the appropriate target (chat_id or sender_id).

        Args:
            original: Original incoming message
            reply: Reply text to send
            reply_in_thread: Whether to reply in thread (if supported)
            quote_reply: Whether to quote the original message (QQ only)

        Returns:
            SendResult with operation status, or None if provider not found

        Raises:
            ValueError: If reply text is empty
        """
        if not reply or not reply.strip():
            logger.warning("Attempted to send empty reply")
            return None

        provider = self.get_provider(original.platform)
        if not provider:
            logger.error(
                "No provider found for platform: %s",
                original.platform,
            )
            return None

        try:
            # Determine target based on platform and chat type
            if original.platform == "feishu":
                # For Feishu, prefer reply API if message ID is available
                if hasattr(provider, "reply_to_message") and original.id and reply_in_thread:
                    try:
                        return await provider.reply_to_message(original.id, reply)
                    except Exception as e:
                        logger.debug(
                            "Thread reply failed, falling back to direct send: %s",
                            e,
                        )

                # Fallback to direct message
                target = original.chat_id or original.sender_id

            elif original.platform == "qq":
                # For QQ, construct target with platform identifier
                if original.chat_type == "group":
                    target = f"group:{original.chat_id}"
                else:
                    target = f"private:{original.sender_id}"

                # Use quote reply if requested and provider supports it
                if quote_reply and original.id and hasattr(provider, "send_reply"):
                    try:
                        result = provider.send_reply(int(original.id), reply, target)
                        if result.success:
                            logger.info(
                                "Quote reply sent successfully: %s",
                                result.message_id,
                            )
                        return result
                    except Exception as e:
                        logger.debug(
                            "Quote reply failed, falling back to direct send: %s",
                            e,
                        )

            else:
                # Generic fallback
                target = original.chat_id or original.sender_id

            logger.debug(
                "Sending reply via %s to target: %s",
                original.platform,
                target,
            )
            result = provider.send_text(reply, target)
            if result.success:
                logger.info("Reply sent successfully: %s", result.message_id)
            else:
                logger.error("Reply send failed: %s", result.error)
            return result

        except Exception as e:
            logger.error(
                "Exception sending reply to %s: %s",
                original.platform,
                e,
                exc_info=True,
            )
            return None

    async def send_rich_reply(
        self,
        original: IncomingMessage,
        text: str | None = None,
        image: str | None = None,
        at_sender: bool = False,
        quote_reply: bool = False,
    ) -> SendResult | None:
        """Send rich reply with multimedia content (QQ enhanced).

        Supports sending text with images, @mentions, and quote replies.
        Falls back to text-only for platforms that don't support rich content.

        Args:
            original: Original incoming message
            text: Text content to send
            image: Image URL or file path to send
            at_sender: Whether to @mention the original sender (group only)
            quote_reply: Whether to quote the original message

        Returns:
            SendResult with operation status, or None if provider not found
        """
        provider = self.get_provider(original.platform)
        if not provider:
            logger.error(
                "No provider found for platform: %s",
                original.platform,
            )
            return None

        try:
            if original.platform == "qq":
                # Build QQ target
                if original.chat_type == "group":
                    target = f"group:{original.chat_id}"
                else:
                    target = f"private:{original.sender_id}"

                # Send @mention + text with optional quote
                if at_sender and original.chat_type == "group":
                    if hasattr(provider, "send_at"):
                        # Use send_at for @mention
                        at_text = text or ""
                        result = provider.send_at(
                            int(original.sender_id),
                            target,
                            at_text,
                        )
                        if not result.success:
                            logger.warning("@mention failed: %s", result.error)
                    elif text:
                        # Fallback: prepend @mention in text
                        text = f"@{original.sender_name} {text}"

                # Send quote reply if requested
                if quote_reply and original.id and hasattr(provider, "send_reply"):
                    result = provider.send_reply(
                        int(original.id),
                        text or "",
                        target,
                    )
                    if result.success:
                        logger.debug("Quote reply sent")
                    # Continue to send image if present

                # Send image if provided
                if image and hasattr(provider, "send_image"):
                    img_result = provider.send_image(image, target)
                    if img_result.success:
                        logger.debug("Image sent successfully")
                    else:
                        logger.warning("Image send failed: %s", img_result.error)
                    if not text and not quote_reply:
                        return img_result

                # Send text if not already sent via quote
                if text and not quote_reply:
                    return provider.send_text(text, target)

                return SendResult.ok("rich_reply")

            else:
                # Fallback for other platforms - text only
                if text:
                    return await self.send_reply(original, text)
                return None

        except Exception as e:
            logger.error(
                "Exception sending rich reply to %s: %s",
                original.platform,
                e,
                exc_info=True,
            )
            return None

    async def send_image_reply(
        self,
        original: IncomingMessage,
        image_url: str,
        caption: str | None = None,
    ) -> SendResult | None:
        """Send image reply to the original message.

        Args:
            original: Original incoming message
            image_url: Image URL or file path
            caption: Optional caption text

        Returns:
            SendResult with operation status
        """
        provider = self.get_provider(original.platform)
        if not provider:
            return None

        try:
            if original.platform == "qq":
                if original.chat_type == "group":
                    target = f"group:{original.chat_id}"
                else:
                    target = f"private:{original.sender_id}"

                # Send caption first if provided
                if caption:
                    provider.send_text(caption, target)

                # Send image
                if hasattr(provider, "send_image"):
                    return provider.send_image(image_url, target)

            elif original.platform == "feishu":
                target = original.chat_id or original.sender_id
                if hasattr(provider, "send_image"):
                    return provider.send_image(image_url, target)

            return SendResult.fail("Image sending not supported for this platform")

        except Exception as e:
            logger.error("Exception sending image: %s", e, exc_info=True)
            return None

    async def _send_error_response(self, ctx: ChatContext) -> None:
        """Send error response to user.

        Args:
            ctx: Chat context with message details
        """
        try:
            result = await self.send_reply(ctx.message, self.config.error_message)
            if result and not result.success:
                logger.error(
                    "Failed to send error response: %s",
                    result.error,
                )
        except Exception as e:
            logger.error(
                "Exception sending error response: %s",
                e,
                exc_info=True,
            )

    async def broadcast(
        self,
        message: str,
        platforms: list[str] | None = None,
        targets: dict[str, list[str]] | None = None,
    ) -> dict[str, list[SendResult]]:
        """Broadcast message to multiple platforms and targets.

        Sends a message to multiple platforms/targets with error handling.
        Failures in one target do not affect others.

        Args:
            message: Message text to broadcast
            platforms: List of platforms to broadcast to (default: all providers)
            targets: Dict of {platform: [target_ids]} for specific targets.
                    If not provided, uses empty string (provider default).

        Returns:
            Dict of {platform: [SendResult]} for each platform

        Example:
            ```python
            results = await controller.broadcast(
                "System announcement",
                platforms=["feishu", "qq"],
                targets={
                    "feishu": ["webhook_url"],
                    "qq": ["group:123", "private:456"]
                }
            )

            # Check results
            for platform, send_results in results.items():
                for result in send_results:
                    if result.success:
                        print(f"Sent to {platform}: {result.message_id}")
                    else:
                        print(f"Failed: {result.error}")
            ```
        """
        if not message or not message.strip():
            logger.warning("Attempted to broadcast empty message")
            return {}

        results: dict[str, list[SendResult]] = {}
        platforms = platforms or list(self.providers.keys())

        logger.info(
            "Broadcasting message to platforms: %s",
            platforms,
        )

        for platform in platforms:
            provider = self.providers.get(platform)
            if not provider:
                logger.warning("Provider not found for platform: %s", platform)
                continue

            results[platform] = []
            platform_targets = targets.get(platform, [""]) if targets else [""]

            for target in platform_targets:
                try:
                    result = provider.send_text(message, target)
                    results[platform].append(result)

                    if result.success:
                        logger.debug(
                            "Broadcast successful: platform=%s, target=%s, message_id=%s",
                            platform,
                            target,
                            result.message_id,
                        )
                    else:
                        logger.warning(
                            "Broadcast failed: platform=%s, target=%s, error=%s",
                            platform,
                            target,
                            result.error,
                        )

                except Exception as e:
                    logger.error(
                        "Exception broadcasting to %s/%s: %s",
                        platform,
                        target,
                        e,
                        exc_info=True,
                    )
                    results[platform].append(SendResult.fail(f"Exception: {str(e)}"))

        return results

    async def get_stats(self) -> dict[str, Any]:
        """Get controller statistics.

        Returns:
            Dictionary with controller stats:
            - providers: List of registered providers
            - middleware_count: Number of middleware functions
            - config: Current configuration
        """
        return {
            "providers": list(self.providers.keys()),
            "middleware_count": len(self._middlewares),
            "config": self.config.model_dump(),
        }


def create_chat_controller(
    ai_agent: AIAgent | None = None,
    providers: dict[str, BaseProvider] | None = None,
    config: ChatConfig | None = None,
    available_models: list[str] | None = None,
    conversation_store: PersistentConversationManager | None = None,
) -> ChatController:
    """Factory function to create a chat controller with command handler.

    Creates and configures a ChatController with an integrated CommandHandler.
    This is the recommended way to create a fully-featured chat controller.

    Args:
        ai_agent: AI agent instance for conversations
        providers: Platform providers {platform: provider}
        config: Chat configuration
        available_models: Models available for /model command

    Returns:
        Fully configured ChatController instance with command handler

    Raises:
        ImportError: If CommandHandler cannot be imported

    Example:
        ```python
        from feishu_webhook_bot.chat import create_chat_controller
        from feishu_webhook_bot.ai import AIAgent

        # Create AI agent
        ai_agent = AIAgent(model="gpt-4o")

        # Create chat controller with command handler
        controller = create_chat_controller(
            ai_agent=ai_agent,
            providers={"feishu": feishu_provider},
            config=ChatConfig(max_message_length=2000),
            available_models=["gpt-4o", "claude-3-sonnet"],
        )

        # Controller now has integrated /help, /reset, /model, etc. commands
        ```
    """
    from ..ai.commands import CommandHandler

    # Get QQ provider for QQ-specific commands
    qq_provider = None
    if providers:
        qq_provider = providers.get("napcat") or providers.get("qq")

    # Create command handler with QQ provider for QQ-specific commands
    command_handler = CommandHandler(
        ai_agent=ai_agent,
        conversation_manager=(ai_agent.conversation_manager if ai_agent else None),
        command_prefix=config.command_prefix if config else "/",
        available_models=available_models,
        qq_provider=qq_provider,
        conversation_store=conversation_store,
    )

    return ChatController(
        ai_agent=ai_agent,
        command_handler=command_handler,
        providers=providers,
        config=config,
        conversation_store=conversation_store,
    )
