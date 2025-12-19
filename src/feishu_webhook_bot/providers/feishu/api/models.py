"""Data models for Feishu Open Platform API.

This module contains all data models used by the Feishu API client.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

# Token types
TokenType = Literal["tenant", "app", "user"]

# Receive ID types for message sending
ReceiveIdType = Literal["open_id", "user_id", "union_id", "email", "chat_id"]


@dataclass
class TokenInfo:
    """Access token information with expiration tracking.

    Attributes:
        token: The access token string.
        expires_at: Unix timestamp when token expires.
        token_type: Type of token (tenant, app, user).
    """

    token: str
    expires_at: float
    token_type: TokenType

    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """Check if token is expired or about to expire.

        Args:
            buffer_seconds: Consider expired if within this many seconds of expiry.

        Returns:
            True if token is expired or will expire soon.
        """
        return time.time() >= (self.expires_at - buffer_seconds)


@dataclass
class UserToken:
    """User access token from OAuth flow.

    Attributes:
        access_token: User access token for API calls.
        refresh_token: Token for refreshing access token.
        token_type: Usually "Bearer".
        expires_in: Token lifetime in seconds.
        scope: Authorized scopes.
        open_id: User's open_id.
        union_id: User's union_id.
        user_id: User's user_id (if available).
    """

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 7200
    scope: str = ""
    open_id: str = ""
    union_id: str = ""
    user_id: str = ""

    # Internal tracking
    obtained_at: float = field(default_factory=time.time)

    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """Check if user token is expired."""
        return time.time() >= (self.obtained_at + self.expires_in - buffer_seconds)


@dataclass
class MessageSendResult:
    """Result of message send operation.

    Attributes:
        success: Whether send succeeded.
        message_id: ID of sent message (if successful).
        error_code: Error code (if failed).
        error_msg: Error message (if failed).
    """

    success: bool
    message_id: str = ""
    error_code: int = 0
    error_msg: str = ""

    @classmethod
    def ok(cls, message_id: str) -> MessageSendResult:
        """Create successful result."""
        return cls(success=True, message_id=message_id)

    @classmethod
    def fail(cls, code: int, msg: str) -> MessageSendResult:
        """Create failed result."""
        return cls(success=False, error_code=code, error_msg=msg)


class FeishuAPIError(Exception):
    """Exception for Feishu API errors.

    Attributes:
        code: Feishu error code.
        msg: Error message.
        log_id: Request log ID for debugging.
    """

    def __init__(self, code: int, msg: str, log_id: str = ""):
        self.code = code
        self.msg = msg
        self.log_id = log_id
        super().__init__(f"Feishu API Error {code}: {msg} (log_id: {log_id})")
