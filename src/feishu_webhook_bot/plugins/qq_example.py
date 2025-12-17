"""Example QQ Plugin demonstrating QQ/OneBot11 integration.

This plugin showcases various QQ-specific features:
- Auto poke-back when bot is poked
- Welcome messages for new group members
- Keyword-based auto-replies
- Command handling
- Scheduled group messages

To use this plugin:
1. Copy this file to your plugins directory
2. Configure in config.yaml under plugins.plugin_settings
3. Restart the bot

Configuration example:
    ```yaml
    plugins:
      plugin_settings:
        - plugin_name: "qq-example"
          enabled: true
          settings:
            poke_back: true
            welcome_enabled: true
            welcome_message: "欢迎 {nickname} 加入群聊！"
            keywords:
              "你好": "你好！有什么可以帮你的？"
              "帮助": "可用命令：/ping, /status, /groups"
            auto_approve_friend: false
            auto_approve_group: false
            scheduled_groups: []
    ```
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from ..core.logger import get_logger
from .base import BasePlugin, PluginMetadata
from .config_schema import PluginConfigSchema
from .qq_mixin import (
    QQMessageEvent,
    QQNoticeEvent,
    QQPluginMixin,
    QQRequestEvent,
    on_qq_message,
    on_qq_notice,
    on_qq_poke,
    on_qq_request,
)

logger = get_logger(__name__)


class QQExampleConfigSchema(PluginConfigSchema):
    """Configuration schema for QQ example plugin."""

    # Poke settings
    poke_back: bool = Field(
        default=True,
        description="Automatically poke back when bot is poked",
    )

    poke_message: str = Field(
        default="",
        description="Optional message to send when poked (empty = no message)",
    )

    # Welcome settings
    welcome_enabled: bool = Field(
        default=True,
        description="Send welcome message when new member joins",
    )

    welcome_message: str = Field(
        default="欢迎 {nickname} 加入群聊！🎉",
        description="Welcome message template. Use {nickname}, {user_id}, {group_id}",
    )

    # Keyword auto-reply
    keywords: dict[str, str] = Field(
        default_factory=dict,
        description="Keyword to response mapping for auto-replies",
    )

    # Request handling
    auto_approve_friend: bool = Field(
        default=False,
        description="Auto-approve all friend requests",
    )

    auto_approve_group: bool = Field(
        default=False,
        description="Auto-approve all group join requests",
    )

    friend_approve_keywords: list[str] = Field(
        default_factory=list,
        description="Approve friend request if comment contains any of these keywords",
    )

    # Scheduled messages
    scheduled_groups: list[int] = Field(
        default_factory=list,
        description="Group IDs to send scheduled messages to",
    )

    scheduled_message: str = Field(
        default="",
        description="Message to send on schedule (empty = disabled)",
    )

    schedule_cron: str = Field(
        default="0 9 * * *",
        description="Cron expression for scheduled messages (default: 9am daily)",
    )

    _field_groups = {
        "Poke Settings": ["poke_back", "poke_message"],
        "Welcome Message": ["welcome_enabled", "welcome_message"],
        "Auto Reply": ["keywords"],
        "Request Handling": [
            "auto_approve_friend",
            "auto_approve_group",
            "friend_approve_keywords",
        ],
        "Scheduled Messages": ["scheduled_groups", "scheduled_message", "schedule_cron"],
    }


class QQExamplePlugin(QQPluginMixin, BasePlugin):
    """Example QQ plugin demonstrating QQ/OneBot11 integration.

    Features:
    - Auto poke-back
    - Welcome messages
    - Keyword auto-replies
    - Command handling (/ping, /status, /groups, /help)
    - Auto-approve requests with keyword verification
    - Scheduled group messages
    """

    config_schema = QQExampleConfigSchema

    TAGS = ["qq", "example", "automation"]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the plugin."""
        super().__init__(*args, **kwargs)
        self._start_time = datetime.now()

    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="qq-example",
            version="1.0.0",
            description="QQ 示例插件 - 展示 QQ/OneBot11 集成功能",
            author="Feishu Bot",
            enabled=True,
        )

    def on_load(self) -> None:
        """Called when plugin is loaded."""
        self.logger.info("QQ Example Plugin loaded")

    def on_enable(self) -> None:
        """Called when plugin is enabled."""
        self.logger.info("QQ Example Plugin enabled")

        # Register scheduled message job if configured
        scheduled_message = self.get_config_value("scheduled_message", "")
        scheduled_groups = self.get_config_value("scheduled_groups", [])

        if scheduled_message and scheduled_groups:
            schedule_cron = self.get_config_value("schedule_cron", "0 9 * * *")
            try:
                # Parse cron expression (minute hour day month weekday)
                parts = schedule_cron.split()
                if len(parts) >= 5:
                    self.register_job(
                        self._send_scheduled_message,
                        trigger="cron",
                        job_id="qq_example_scheduled",
                        minute=parts[0],
                        hour=parts[1],
                        day=parts[2] if parts[2] != "*" else None,
                        month=parts[3] if parts[3] != "*" else None,
                        day_of_week=parts[4] if parts[4] != "*" else None,
                    )
                    self.logger.info(
                        "Scheduled message registered: %s to %d groups",
                        schedule_cron,
                        len(scheduled_groups),
                    )
            except Exception as e:
                self.logger.error("Failed to register scheduled job: %s", e)

    def on_disable(self) -> None:
        """Called when plugin is disabled."""
        self.logger.info("QQ Example Plugin disabled")
        self.cleanup_jobs()

    # =========================================================================
    # QQ Event Handlers
    # =========================================================================

    @on_qq_poke
    def handle_poke(self, event: QQNoticeEvent) -> None:
        """Handle poke events - poke back if enabled."""
        if not self.get_config_value("poke_back", True):
            return

        user_id = event.user_id
        group_id = event.group_id
        target_id = event.target_id

        # Only respond if we were the target
        qq_provider = self.get_qq_provider()
        if qq_provider and target_id:
            # Check if we're the target (would need bot_qq to verify)
            self.logger.debug("Poke event: %s poked %s in group %s", user_id, target_id, group_id)

            # Poke back
            if user_id:
                self.send_qq_poke(user_id, group_id)
                self.logger.info("Poked back user %s in group %s", user_id, group_id)

                # Optional message
                poke_message = self.get_config_value("poke_message", "")
                if poke_message and group_id:
                    self.send_qq_message(poke_message, f"group:{group_id}")

    @on_qq_notice("group_increase")
    def handle_member_join(self, event: QQNoticeEvent) -> None:
        """Handle new member joining group - send welcome message."""
        if not self.get_config_value("welcome_enabled", True):
            return

        group_id = event.group_id
        user_id = event.user_id

        if not group_id or not user_id:
            return

        # Get welcome message template
        template = self.get_config_value("welcome_message", "欢迎 {nickname} 加入群聊！🎉")

        # Format message
        message = template.format(
            nickname=f"[CQ:at,qq={user_id}]",
            user_id=user_id,
            group_id=group_id,
        )

        self.send_qq_message(message, f"group:{group_id}")
        self.logger.info("Sent welcome message for user %s in group %s", user_id, group_id)

    @on_qq_notice("group_decrease")
    def handle_member_leave(self, event: QQNoticeEvent) -> None:
        """Handle member leaving group - log the event."""
        group_id = event.group_id
        user_id = event.user_id
        operator_id = event.operator_id
        sub_type = event.sub_type

        action = "被踢出" if sub_type == "kick" else "退出"
        self.logger.info(
            "User %s %s group %s (operator: %s)",
            user_id,
            action,
            group_id,
            operator_id,
        )

    @on_qq_request("friend")
    def handle_friend_request(self, event: QQRequestEvent) -> bool | None:
        """Handle friend requests."""
        user_id = event.user_id
        comment = event.comment
        flag = event.flag

        self.logger.info("Friend request from %s: %s", user_id, comment)

        # Auto-approve if enabled
        if self.get_config_value("auto_approve_friend", False):
            self.qq_approve_friend_request(flag, approve=True)
            self.logger.info("Auto-approved friend request from %s", user_id)
            return True

        # Check for keywords
        keywords = self.get_config_value("friend_approve_keywords", [])
        if keywords:
            for keyword in keywords:
                if keyword in comment:
                    self.qq_approve_friend_request(flag, approve=True)
                    self.logger.info(
                        "Approved friend request from %s (keyword: %s)",
                        user_id,
                        keyword,
                    )
                    return True

        return None  # Let other handlers decide

    @on_qq_request("group")
    def handle_group_request(self, event: QQRequestEvent) -> bool | None:
        """Handle group join/invite requests."""
        user_id = event.user_id
        group_id = event.group_id
        sub_type = event.sub_type
        flag = event.flag

        self.logger.info(
            "Group %s request: user %s for group %s",
            sub_type,
            user_id,
            group_id,
        )

        # Auto-approve if enabled
        if self.get_config_value("auto_approve_group", False):
            self.qq_approve_group_request(flag, sub_type or "add", approve=True)
            self.logger.info("Auto-approved group request")
            return True

        return None

    # =========================================================================
    # Message Handlers
    # =========================================================================

    @on_qq_message(command="/ping")
    def handle_ping(self, event: QQMessageEvent) -> str | None:
        """Handle /ping command."""
        return "pong! 🏓"

    @on_qq_message(command="/status")
    def handle_status(self, event: QQMessageEvent) -> str | None:
        """Handle /status command."""
        uptime = datetime.now() - self._start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        qq_provider = self.get_qq_provider()
        status = "在线" if qq_provider else "离线"

        return (
            f"📊 Bot 状态\n"
            f"• 状态: {status}\n"
            f"• 运行时间: {hours}小时{minutes}分钟{seconds}秒\n"
            f"• 插件: qq-example v1.0.0"
        )

    @on_qq_message(command="/groups")
    def handle_groups(self, event: QQMessageEvent) -> str | None:
        """Handle /groups command - list bot's groups."""
        groups = self.qq_get_group_list()

        if not groups:
            return "暂无群组信息"

        lines = ["📋 群组列表:"]
        for i, group in enumerate(groups[:10], 1):
            name = group.get("group_name", "未知")
            gid = group.get("group_id", "")
            count = group.get("member_count", 0)
            lines.append(f"{i}. {name} ({gid}) - {count}人")

        if len(groups) > 10:
            lines.append(f"... 共 {len(groups)} 个群组")

        return "\n".join(lines)

    @on_qq_message(command="/help")
    def handle_help(self, event: QQMessageEvent) -> str | None:
        """Handle /help command."""
        return (
            "🤖 QQ示例插件帮助\n"
            "可用命令:\n"
            "• /ping - 测试机器人响应\n"
            "• /status - 查看机器人状态\n"
            "• /groups - 查看群组列表\n"
            "• /help - 显示此帮助信息\n"
            "\n"
            "功能:\n"
            "• 自动回戳\n"
            "• 入群欢迎\n"
            "• 关键词回复"
        )

    def handle_qq_message(self, event: dict[str, Any]) -> str | None:
        """Override to add keyword matching.

        This is called by the parent class and also handles keyword auto-replies.
        """
        # First, let the mixin handle decorated handlers
        response = super().handle_qq_message(event)
        if response:
            return response

        # Then check keyword auto-replies
        keywords = self.get_config_value("keywords", {})
        if not keywords:
            return None

        raw_message = event.get("raw_message", "")

        for keyword, reply in keywords.items():
            if keyword in raw_message:
                self.logger.debug("Keyword match: %s -> %s", keyword, reply)
                return reply

        return None

    # =========================================================================
    # Scheduled Tasks
    # =========================================================================

    def _send_scheduled_message(self) -> None:
        """Send scheduled message to configured groups."""
        message = self.get_config_value("scheduled_message", "")
        groups = self.get_config_value("scheduled_groups", [])

        if not message or not groups:
            return

        for group_id in groups:
            try:
                self.send_qq_message(message, f"group:{group_id}")
                self.logger.info("Sent scheduled message to group %s", group_id)
            except Exception as e:
                self.logger.error(
                    "Failed to send scheduled message to group %s: %s",
                    group_id,
                    e,
                )
