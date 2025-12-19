"""NapCat extended API module.

This module provides NapCat-specific extended APIs:
- Poke functionality
- AI voice features
- Message extensions (history, essence, reactions)
- Group extensions (announcements, honors, files)
- File operations
"""

from .ai_voice import NapcatAIVoiceMixin
from .file import NapcatFileMixin
from .group_ext import NapcatGroupExtMixin
from .message_ext import NapcatMessageExtMixin
from .poke import NapcatPokeMixin

__all__ = [
    "NapcatPokeMixin",
    "NapcatAIVoiceMixin",
    "NapcatMessageExtMixin",
    "NapcatGroupExtMixin",
    "NapcatFileMixin",
]
