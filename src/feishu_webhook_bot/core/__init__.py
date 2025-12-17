"""Core modules for Feishu Webhook Bot framework.

This package contains the core functionality including:
- Webhook client for sending messages
- Configuration management
- Logging utilities
- Circuit breaker for fault tolerance
- Message tracking and delivery confirmation
- Message queue for reliable delivery with retry support
- Multi-provider abstraction layer
- Unified message handling interface for multi-platform support
"""

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpen,
    CircuitBreakerRegistry,
    CircuitState,
    circuit_breaker,
)
from .client import CardBuilder, FeishuWebhookClient
from .config import (
    AuthConfig,
    BotConfig,
    CircuitBreakerPolicyConfig,
    LoggingConfig,
    ProviderConfigBase,
    WebhookConfig,
)
from .image_uploader import (
    FeishuImageUploader,
    FeishuImageUploaderError,
    FeishuPermissionChecker,
    FeishuPermissionDeniedError,
    create_image_card,
)
from .logger import get_logger, setup_logging
from .message_handler import (
    IncomingMessage,
    MessageHandler,
    MessageParser,
    get_chat_key,
    get_user_key,
)
from .message_parsers import (
    FeishuMessageParser,
    QQMessageParser,
    create_feishu_parser,
    create_qq_parser,
)
from .message_queue import MessageQueue, QueuedMessage
from .message_tracker import MessageStatus, MessageTracker, TrackedMessage
from .provider import (
    BaseProvider,
    Message,
    MessageType,
    ProviderConfig,
    ProviderRegistry,
    SendResult,
)

__all__ = [
    # Client and card builder
    "FeishuWebhookClient",
    "CardBuilder",
    # Image uploader
    "FeishuImageUploader",
    "FeishuImageUploaderError",
    "FeishuPermissionChecker",
    "FeishuPermissionDeniedError",
    "create_image_card",
    # Configuration
    "BotConfig",
    "WebhookConfig",
    "AuthConfig",
    "LoggingConfig",
    "ProviderConfigBase",
    "CircuitBreakerPolicyConfig",
    # Logging
    "get_logger",
    "setup_logging",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerOpen",
    "CircuitBreakerRegistry",
    "CircuitState",
    "circuit_breaker",
    # Message handling
    "IncomingMessage",
    "MessageHandler",
    "MessageParser",
    "get_user_key",
    "get_chat_key",
    # Message parsers
    "FeishuMessageParser",
    "QQMessageParser",
    "create_feishu_parser",
    "create_qq_parser",
    # Message queue
    "MessageQueue",
    "QueuedMessage",
    # Message tracking
    "MessageStatus",
    "MessageTracker",
    "TrackedMessage",
    # Provider abstraction
    "BaseProvider",
    "ProviderConfig",
    "ProviderRegistry",
    "Message",
    "MessageType",
    "SendResult",
]
