"""AI capabilities for Feishu Webhook Bot.

This package provides AI-powered features including:
- Conversation management with multi-turn dialogue support
- Tool/function calling capabilities
- Web search integration
- Integration with pydantic-ai for structured AI interactions
- Streaming responses for real-time AI interactions
- Output validation with retry logic
- MCP (Model Context Protocol) support
- Multi-agent orchestration (A2A)
- AI-powered automated tasks
"""

from .agent import AIAgent, AIResponse
from .config import AIConfig, ConversationPersistenceConfig, MCPConfig, ModelProviderConfig, MultiAgentConfig, StreamingConfig
from .conversation import ConversationManager, ConversationState
from .commands import CommandHandler, CommandResult
from .conversation_store import ConversationRecord, MessageRecord, PersistentConversationManager
from .exceptions import (
    AIError,
    AIServiceUnavailableError,
    ConfigurationError,
    ConversationNotFoundError,
    ModelResponseError,
    RateLimitError,
    TokenLimitExceededError,
    ToolExecutionError,
)
from .mcp_client import MCPClient
from .multi_agent import (
    AgentMessage,
    AgentOrchestrator,
    AgentResult,
    AnalysisAgent,
    ResponseAgent,
    SearchAgent,
    SpecializedAgent,
)
from .retry import CircuitBreaker, retry_with_exponential_backoff
from .task_integration import AITaskExecutor, AITaskResult, execute_ai_task_action
from .tools import ToolRegistry

__all__ = [
    "AIAgent",
    "AIResponse",
    "AIConfig",
    "ConversationPersistenceConfig",
    "MCPConfig",
    "MultiAgentConfig",
    "StreamingConfig",
    "ModelProviderConfig",
    "ConversationManager",
    "ConversationState",
    "CommandHandler",
    "CommandResult",
    "PersistentConversationManager",
    "ConversationRecord",
    "MessageRecord",
    "ToolRegistry",
    "MCPClient",
    "AgentOrchestrator",
    "SpecializedAgent",
    "SearchAgent",
    "AnalysisAgent",
    "ResponseAgent",
    "AgentMessage",
    "AgentResult",
    "AITaskExecutor",
    "AITaskResult",
    "execute_ai_task_action",
    "AIError",
    "AIServiceUnavailableError",
    "ToolExecutionError",
    "ConversationNotFoundError",
    "ModelResponseError",
    "TokenLimitExceededError",
    "RateLimitError",
    "ConfigurationError",
    "CircuitBreaker",
    "retry_with_exponential_backoff",
]
