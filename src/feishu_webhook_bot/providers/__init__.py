"""Message providers for multi-platform support.

This module provides message provider implementations for various platforms:
- FeishuProvider: Feishu/Lark webhook and Open Platform integration
- NapcatProvider: QQ messaging via Napcat OneBot11 protocol
- FeishuOpenAPI: Full Feishu Open Platform API client
- QQEventHandler: OneBot11 event parsing

QQ Bot Features (via NapcatProvider):
- Full OneBot11 API support
- NapCat extended APIs (AI voice, poke, emoji reactions)
- Group management (kick, ban, admin, etc.)
- Message history and forwarding
- Compatible with NapCatQQ, LLOneBot, Lagrange
"""

from .feishu import FeishuProvider, FeishuProviderConfig
from .feishu_api import (
    FeishuAPIError,
    FeishuOpenAPI,
    MessageSendResult,
    TokenInfo,
    UserToken,
    create_feishu_api,
)
from .qq_event_handler import (
    QQEventHandler,
    QQEventMeta,
    QQEventType,
    QQNoticeEvent,
    QQRequestEvent,
    create_qq_event_handler,
)
from .qq_napcat import (
    NapcatProvider,
    NapcatProviderConfig,
    OneBotResponse,
    OnlineStatus,
    QQGroupInfo,
    QQGroupMember,
    QQMessage,
    QQUserInfo,
)

__all__ = [
    # Feishu Provider
    "FeishuProvider",
    "FeishuProviderConfig",
    # Feishu Open Platform API
    "FeishuOpenAPI",
    "FeishuAPIError",
    "TokenInfo",
    "UserToken",
    "MessageSendResult",
    "create_feishu_api",
    # QQ/Napcat Provider
    "NapcatProvider",
    "NapcatProviderConfig",
    # QQ Data Models
    "QQUserInfo",
    "QQGroupInfo",
    "QQGroupMember",
    "QQMessage",
    "OnlineStatus",
    "OneBotResponse",
    # QQ Event Handler
    "QQEventHandler",
    "QQEventMeta",
    "QQEventType",
    "QQNoticeEvent",
    "QQRequestEvent",
    "create_qq_event_handler",
]
