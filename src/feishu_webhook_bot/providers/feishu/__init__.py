"""Feishu/Lark platform provider module.

This module provides comprehensive Feishu integration:
- FeishuProvider: Webhook-based message sending
- FeishuOpenAPI: Full Open Platform API client

Components:
- webhook.py: FeishuProvider for webhook messaging
- config.py: Configuration classes
- signature.py: HMAC signature generation
- api/: Full Open Platform API implementation
"""

from .api import (
    FeishuAPIError,
    FeishuOpenAPI,
    MessageSendResult,
    TokenInfo,
    UserToken,
    create_feishu_api,
)
from .config import FeishuProviderConfig
from .webhook import FeishuProvider

__all__ = [
    # Webhook Provider
    "FeishuProvider",
    "FeishuProviderConfig",
    # Open Platform API
    "FeishuOpenAPI",
    "FeishuAPIError",
    "TokenInfo",
    "UserToken",
    "MessageSendResult",
    "create_feishu_api",
]
