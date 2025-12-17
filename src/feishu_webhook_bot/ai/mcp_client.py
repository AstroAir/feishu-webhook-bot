"""MCP (Model Context Protocol) client implementation.

This module provides backward-compatible imports for the MCP client.
The implementation has been refactored into the mcp/ submodule.

For new code, prefer importing from feishu_webhook_bot.ai.mcp directly.
"""

from .mcp import (
    MCP_AVAILABLE,
    MCPClient,
    MCPServerSSE,
    MCPServerStdio,
    MCPServerStreamableHTTP,
)

__all__ = [
    "MCPClient",
    "MCP_AVAILABLE",
    "MCPServerStdio",
    "MCPServerSSE",
    "MCPServerStreamableHTTP",
]
