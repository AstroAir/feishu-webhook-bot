"""Chat module for unified chat bot functionality.

This module provides a centralized chat controller for handling incoming messages
from multiple platforms, routing them to command handlers or AI agents, and sending
responses back to the appropriate platform.

Key components:
- ChatController: Main orchestrator for message handling
- ChatConfig: Configuration for chat behavior
- ChatContext: Runtime context for a message interaction
- create_chat_controller: Factory function for creating configured controllers
"""

from .controller import ChatConfig, ChatController, create_chat_controller

__all__ = ["ChatController", "ChatConfig", "create_chat_controller"]
