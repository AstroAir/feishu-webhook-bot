"""QQ platform provider module.

This module provides comprehensive QQ bot integration via OneBot11 protocol:
- NapcatProvider: Full OneBot11 API support with NapCat extensions
- QQEventHandler: Event parsing and handling

Components:
- provider.py: NapcatProvider core messaging
- config.py: Configuration classes
- models.py: Data models
- event_handler.py: Event parsing
- api/: OneBot11 standard APIs
- napcat/: NapCat extended APIs
- async_provider.py: Async operations
"""

from .async_provider import AsyncNapcatMixin
from .config import NapcatProviderConfig
from .event_handler import (
    QQEventHandler,
    QQEventMeta,
    QQEventType,
    QQNoticeEvent,
    QQRequestEvent,
    create_qq_event_handler,
)
from .models import (
    OneBotResponse,
    OnlineStatus,
    QQGroupInfo,
    QQGroupMember,
    QQMessage,
    QQUserInfo,
)
from .provider import NapcatProvider

__all__ = [
    # Main Provider
    "NapcatProvider",
    "NapcatProviderConfig",
    "AsyncNapcatMixin",
    # Data Models
    "QQUserInfo",
    "QQGroupInfo",
    "QQGroupMember",
    "QQMessage",
    "OnlineStatus",
    "OneBotResponse",
    # Event Handler
    "QQEventHandler",
    "QQEventMeta",
    "QQEventType",
    "QQNoticeEvent",
    "QQRequestEvent",
    "create_qq_event_handler",
]
