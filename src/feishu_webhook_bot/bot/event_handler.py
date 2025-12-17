"""Event handling mixin for FeishuBot."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from ..core import get_logger
from ..core.message_handler import IncomingMessage
from ..core.message_parsers import FeishuMessageParser, QQMessageParser
from ..providers.qq_event_handler import QQEventHandler

if TYPE_CHECKING:
    from .base import BotBase

logger = get_logger("bot.event")


class EventHandlerMixin:
    """Mixin for incoming event handling."""

    # QQ event handler instance (lazily initialized)
    _qq_event_handler: QQEventHandler | None = None

    def _get_qq_event_handler(self: BotBase) -> QQEventHandler:
        """Get or create QQ event handler."""
        if self._qq_event_handler is None:
            # Get bot_qq from provider config
            bot_qq = None
            for p_config in self.config.providers or []:
                if p_config.provider_type == "napcat":
                    bot_qq = getattr(p_config, "bot_qq", None)
                    break
            self._qq_event_handler = QQEventHandler(bot_qq=bot_qq)
        return self._qq_event_handler

    def _handle_incoming_event(self: BotBase, payload: dict[str, Any]) -> None:
        """Handle inbound events from the event server."""
        logger.debug("Handling incoming event: %s", payload.get("type", "unknown"))

        # Check for QQ notice/request events
        provider = payload.get("_provider", "")
        post_type = payload.get("post_type", "")

        if provider in ("napcat", "qq") or post_type in ("notice", "request"):
            asyncio.create_task(self._handle_qq_event(payload))

        # Handle AI chat messages via ChatController if available
        if self.chat_controller and self._is_chat_message(payload):
            try:
                # Parse message from payload and route to chat controller
                message = self._parse_incoming_message(payload)
                if message:
                    asyncio.create_task(self.chat_controller.handle_incoming(message))
                    logger.debug("Message routed to chat controller")
                    # Note: Plugin and automation dispatch still happens below for
                    # backward compatibility and non-message event handling
                else:
                    logger.debug("Could not parse message from payload")
            except Exception as exc:
                logger.error("Chat controller message handling failed: %s", exc, exc_info=True)
        # Fallback to old AI chat handler if no chat controller
        elif self.ai_agent and self._is_chat_message(payload):
            try:
                asyncio.create_task(self._handle_ai_chat(payload))
            except Exception as exc:
                logger.error("AI chat handling failed: %s", exc, exc_info=True)

        if self.plugin_manager:
            try:
                self.plugin_manager.dispatch_event(payload, context={})
            except Exception as exc:
                logger.error("Plugin event dispatch failed: %s", exc, exc_info=True)

        if self.automation_engine:
            try:
                self.automation_engine.handle_event(payload)
            except Exception as exc:
                logger.error("Automation event handling failed: %s", exc, exc_info=True)

        # Handle message bridge forwarding
        if self.message_bridge and self.message_bridge.is_running():
            try:
                message = self._parse_incoming_message(payload)
                if message:
                    asyncio.create_task(self.message_bridge.handle_message(message))
                    logger.debug("Message routed to bridge engine")
            except Exception as exc:
                logger.error("Message bridge handling failed: %s", exc, exc_info=True)

    async def _handle_qq_event(self: BotBase, payload: dict[str, Any]) -> None:
        """Handle QQ-specific events (notice, request, meta_event).

        Args:
            payload: QQ event payload
        """
        post_type = payload.get("post_type", "")

        if post_type == "notice":
            await self._handle_qq_notice(payload)
        elif post_type == "request":
            await self._handle_qq_request(payload)
        elif post_type == "meta_event":
            self._handle_qq_meta_event(payload)

    async def _handle_qq_notice(self: BotBase, payload: dict[str, Any]) -> None:
        """Handle QQ notice events.

        Args:
            payload: Notice event payload
        """
        notice_type = payload.get("notice_type", "")
        sub_type = payload.get("sub_type", "")

        logger.info("QQ notice event: %s/%s", notice_type, sub_type)

        # Get QQ provider for sending responses
        qq_provider = self.providers.get("napcat") or self.providers.get("qq")

        if notice_type == "group_increase":
            # New member joined group
            group_id = payload.get("group_id")
            user_id = payload.get("user_id")
            operator_id = payload.get("operator_id")

            logger.info(
                "New member %s joined group %s (operator: %s)",
                user_id,
                group_id,
                operator_id,
            )

            # Send welcome message if configured
            if qq_provider and hasattr(self.config, "qq_welcome_enabled"):
                if getattr(self.config, "qq_welcome_enabled", False):
                    welcome_msg = getattr(
                        self.config, "qq_welcome_message", f"欢迎 [CQ:at,qq={user_id}] 加入群聊！"
                    )
                    qq_provider.send_text(welcome_msg, f"group:{group_id}")

        elif notice_type == "group_decrease":
            # Member left/kicked from group
            group_id = payload.get("group_id")
            user_id = payload.get("user_id")
            operator_id = payload.get("operator_id")

            action = "被踢出" if sub_type == "kick" else "退出"
            logger.info(
                "Member %s %s group %s (operator: %s)",
                user_id,
                action,
                group_id,
                operator_id,
            )

        elif notice_type == "group_ban":
            # Member banned/unbanned
            group_id = payload.get("group_id")
            user_id = payload.get("user_id")
            duration = payload.get("duration", 0)

            if sub_type == "ban":
                logger.info(
                    "Member %s banned in group %s for %d seconds",
                    user_id,
                    group_id,
                    duration,
                )
            else:
                logger.info("Member %s unbanned in group %s", user_id, group_id)

        elif notice_type == "friend_add":
            # New friend added
            user_id = payload.get("user_id")
            logger.info("New friend added: %s", user_id)

        elif notice_type == "notify" and sub_type == "poke":
            # Poke notification
            group_id = payload.get("group_id")
            user_id = payload.get("user_id")
            target_id = payload.get("target_id")

            logger.debug(
                "Poke: %s poked %s in group %s",
                user_id,
                target_id,
                group_id,
            )

    async def _handle_qq_request(self: BotBase, payload: dict[str, Any]) -> None:
        """Handle QQ request events (friend/group add requests).

        Args:
            payload: Request event payload
        """
        request_type = payload.get("request_type", "")
        flag = payload.get("flag", "")

        logger.info("QQ request event: %s (flag=%s)", request_type, flag)

        qq_provider = self.providers.get("napcat") or self.providers.get("qq")

        if request_type == "friend":
            # Friend add request
            user_id = payload.get("user_id")
            comment = payload.get("comment", "")

            logger.info(
                "Friend request from %s: %s",
                user_id,
                comment,
            )

            # Auto-approve if configured
            if qq_provider and hasattr(self.config, "qq_auto_approve_friend"):
                if getattr(self.config, "qq_auto_approve_friend", False):
                    if hasattr(qq_provider, "set_friend_add_request"):
                        qq_provider.set_friend_add_request(flag, approve=True)
                        logger.info("Auto-approved friend request from %s", user_id)

        elif request_type == "group":
            # Group add/invite request
            sub_type = payload.get("sub_type", "")
            group_id = payload.get("group_id")
            user_id = payload.get("user_id")
            comment = payload.get("comment", "")

            if sub_type == "add":
                logger.info(
                    "Group join request: user %s wants to join group %s (%s)",
                    user_id,
                    group_id,
                    comment,
                )
            else:
                logger.info(
                    "Group invite: user %s invited to group %s",
                    user_id,
                    group_id,
                )

            # Auto-approve if configured
            if qq_provider and hasattr(self.config, "qq_auto_approve_group"):
                if getattr(self.config, "qq_auto_approve_group", False):
                    if hasattr(qq_provider, "set_group_add_request"):
                        qq_provider.set_group_add_request(flag, sub_type=sub_type, approve=True)
                        logger.info("Auto-approved group request")

    def _handle_qq_meta_event(self: BotBase, payload: dict[str, Any]) -> None:
        """Handle QQ meta events (lifecycle, heartbeat).

        Args:
            payload: Meta event payload
        """
        meta_event_type = payload.get("meta_event_type", "")

        if meta_event_type == "lifecycle":
            sub_type = payload.get("sub_type", "")
            logger.info("QQ lifecycle event: %s", sub_type)

        elif meta_event_type == "heartbeat":
            # Heartbeat - just log at debug level
            status = payload.get("status", {})
            online = status.get("online", False)
            logger.debug("QQ heartbeat: online=%s", online)

    def _parse_incoming_message(self: BotBase, payload: dict[str, Any]) -> IncomingMessage | None:
        """Parse event payload into a unified IncomingMessage.

        Uses platform-specific parsers for comprehensive message parsing:
        - FeishuMessageParser for Feishu events
        - QQMessageParser for OneBot11/Napcat events

        Args:
            payload: Event payload from webhook

        Returns:
            IncomingMessage instance or None if parsing fails
        """
        try:
            # Determine platform from payload marker (set by event_server)
            provider = payload.get("_provider", "")

            # Try Feishu parser
            if provider == "feishu" or not provider:
                # Get bot_open_id from provider config if available
                bot_open_id = None
                for p_config in self.config.providers or []:
                    if p_config.provider_type == "feishu":
                        api_config = getattr(p_config, "api", None)
                        if api_config:
                            # In a real implementation, bot_open_id would be obtained from API
                            pass
                        break

                feishu_parser = FeishuMessageParser(bot_open_id=bot_open_id)
                if feishu_parser.can_parse(payload):
                    message = feishu_parser.parse(payload)
                    if message:
                        return message

            # Try QQ parser
            if provider == "napcat" or provider == "qq" or not provider:
                # Get bot_qq from provider config
                bot_qq = None
                for p_config in self.config.providers or []:
                    if p_config.provider_type == "napcat":
                        bot_qq = getattr(p_config, "bot_qq", None)
                        break

                qq_parser = QQMessageParser(bot_qq=bot_qq)
                if qq_parser.can_parse(payload):
                    message = qq_parser.parse(payload)
                    if message:
                        return message

            # Fallback: Try basic Feishu structure for backward compatibility
            event_type = payload.get("type")
            if event_type == "message":
                event = payload.get("event", payload)
                message_data = event.get("message", {})
                sender = event.get("sender", {})

                return IncomingMessage(
                    id=message_data.get("message_id", ""),
                    platform="feishu",
                    chat_type=event.get("chat_type", "private"),
                    chat_id=event.get("chat_id", ""),
                    sender_id=sender.get("sender_id", {}).get("user_id", ""),
                    sender_name=sender.get("sender_name", "Unknown"),
                    content=message_data.get("text", ""),
                    is_at_bot=False,
                    raw_content=message_data,
                    metadata={"event_id": payload.get("event_id", "")},
                )

            return None

        except Exception as e:
            logger.debug("Failed to parse incoming message: %s", e, exc_info=True)
            return None

    def _is_chat_message(self: BotBase, payload: dict[str, Any]) -> bool:
        """Check if the payload is a chat message that should be handled by AI.

        Supports both Feishu and QQ (OneBot11) message structures.

        Args:
            payload: Event payload

        Returns:
            True if this is a chat message
        """
        # Check for Feishu message event structure
        event_type = payload.get("type")
        if event_type == "message":
            return True

        # Check for nested event structure (Feishu v2.0)
        header = payload.get("header", {})
        if header.get("event_type") == "im.message.receive_v1":
            return True

        event = payload.get("event", {})
        if event.get("type") == "message":
            return True

        # Check for QQ/OneBot11 message event structure
        return payload.get("post_type") == "message"

    async def _handle_ai_chat(self: BotBase, payload: dict[str, Any]) -> None:
        """Handle AI chat message.

        Note: This method is now primarily handled by ChatController when available.
        It's kept for backward compatibility and as a fallback when chat_controller
        is not initialized.

        Args:
            payload: Event payload
        """
        # If chat controller is available, it should handle this
        if self.chat_controller:
            logger.debug("AI chat should be handled by ChatController, skipping legacy handler")
            return

        try:
            # Extract message content and user ID from payload
            event = payload.get("event", payload)
            message_content = event.get("text", event.get("content", ""))
            user_id = event.get("sender", {}).get("sender_id", {}).get("user_id", "unknown")

            if not message_content:
                logger.warning("Received empty message, skipping AI processing")
                return

            logger.info("Processing AI chat from user %s: %s", user_id, message_content[:100])

            # Get AI response
            response = await self.ai_agent.chat(user_id, message_content)

            # Send response back via webhook
            if response and self.client:
                self.client.send_text(response)
                logger.info("Sent AI response to user %s", user_id)

        except Exception as exc:
            logger.error("Error handling AI chat: %s", exc, exc_info=True)
