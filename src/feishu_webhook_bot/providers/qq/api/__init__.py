"""OneBot11 standard API module.

This module provides standard OneBot11 API implementations:
- Message operations (send, delete, forward)
- User information queries
- Group information queries
- Group management (admin operations)
- Request handling (friend/group requests)
- System status
"""

from .group import OneBotGroupInfoMixin
from .group_admin import OneBotGroupAdminMixin
from .message import OneBotMessageMixin
from .request import OneBotRequestMixin
from .system import OneBotSystemMixin
from .user import OneBotUserMixin

__all__ = [
    "OneBotMessageMixin",
    "OneBotUserMixin",
    "OneBotGroupInfoMixin",
    "OneBotGroupAdminMixin",
    "OneBotRequestMixin",
    "OneBotSystemMixin",
]
