"""Message providers for multi-platform support.

This module provides message provider implementations for various platforms:
- FeishuProvider: Feishu/Lark webhook and Open Platform integration
- NapcatProvider: QQ messaging via Napcat OneBot11 protocol
- FeishuOpenAPI: Full Feishu Open Platform API client
- QQEventHandler: OneBot11 event parsing
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
from .qq_event_handler import QQEventHandler, QQEventMeta, create_qq_event_handler
from .qq_napcat import NapcatProvider, NapcatProviderConfig

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
    # QQ Event Handler
    "QQEventHandler",
    "QQEventMeta",
    "create_qq_event_handler",
]

