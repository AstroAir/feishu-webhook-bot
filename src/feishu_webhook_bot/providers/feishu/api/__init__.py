"""Feishu Open Platform API module.

This module provides comprehensive access to Feishu Open Platform APIs:
- Token management (tenant_access_token, app_access_token)
- Message API (send, reply, recall messages)
- User/Chat info queries
- OAuth authorization flow
- File/Media operations
- Chat management

Components:
- client.py: FeishuOpenAPI core client
- auth.py: Token management and OAuth
- message.py: Message operations
- user.py: User and chat info
- chat.py: Chat management
- media.py: File and image operations
- models.py: Data models
"""

from .auth import FeishuAuthMixin
from .chat import FeishuChatMixin
from .client import FeishuOpenAPI, create_feishu_api
from .media import FeishuMediaMixin
from .message import FeishuMessageMixin
from .models import FeishuAPIError, MessageSendResult, TokenInfo, UserToken
from .user import FeishuUserMixin

__all__ = [
    # Main client
    "FeishuOpenAPI",
    "create_feishu_api",
    # Models
    "FeishuAPIError",
    "TokenInfo",
    "UserToken",
    "MessageSendResult",
    # Mixins (for advanced usage)
    "FeishuAuthMixin",
    "FeishuMessageMixin",
    "FeishuUserMixin",
    "FeishuChatMixin",
    "FeishuMediaMixin",
]
