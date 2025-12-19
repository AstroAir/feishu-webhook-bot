"""Message providers for multi-platform support.

This module provides message provider implementations for various platforms:
- FeishuProvider: Feishu/Lark webhook and Open Platform integration
- NapcatProvider: QQ messaging via Napcat OneBot11 protocol
- FeishuOpenAPI: Full Feishu Open Platform API client
- QQEventHandler: OneBot11 event parsing

Directory Structure:
- common/: Shared base classes and utilities
- feishu/: Feishu platform providers and APIs
- qq/: QQ platform providers and APIs

QQ Bot Features (via NapcatProvider):
- Full OneBot11 API support
- NapCat extended APIs (AI voice, poke, emoji reactions)
- Group management (kick, ban, admin, etc.)
- Message history and forwarding
- Compatible with NapCatQQ, LLOneBot, Lagrange

Backward Compatibility:
All imports from the old flat structure are preserved.
Use submodules directly for new code:
    from feishu_webhook_bot.providers.feishu import FeishuProvider
    from feishu_webhook_bot.providers.qq import NapcatProvider
"""

# Common utilities
from .common import (
    AsyncHTTPProviderMixin,
    EnhancedBaseProvider,
    HTTPProviderMixin,
    ProviderResponse,
)

# Feishu platform - import from new submodule
from .feishu import (
    FeishuAPIError,
    FeishuOpenAPI,
    FeishuProvider,
    FeishuProviderConfig,
    MessageSendResult,
    TokenInfo,
    UserToken,
    create_feishu_api,
)

# QQ platform - import from new submodule
from .qq import (
    AsyncNapcatMixin,
    NapcatProvider,
    NapcatProviderConfig,
    OneBotResponse,
    OnlineStatus,
    QQEventHandler,
    QQEventMeta,
    QQEventType,
    QQGroupInfo,
    QQGroupMember,
    QQMessage,
    QQNoticeEvent,
    QQRequestEvent,
    QQUserInfo,
    create_qq_event_handler,
)

__all__ = [
    # Common utilities
    "HTTPProviderMixin",
    "AsyncHTTPProviderMixin",
    "EnhancedBaseProvider",
    "ProviderResponse",
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
    "AsyncNapcatMixin",
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
