"""Base types and constants for MCP client.

This module provides the foundational imports, constants, and type definitions
used throughout the MCP client implementation.
"""

from __future__ import annotations

from typing import Any

try:
    from pydantic_ai.mcp import MCPServerSSE, MCPServerStdio, MCPServerStreamableHTTP

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    MCPServerStdio = None  # type: ignore
    MCPServerSSE = None  # type: ignore
    MCPServerStreamableHTTP = None  # type: ignore

from ...core.logger import get_logger

logger = get_logger("ai.mcp.base")

# Type alias for MCP server instances
MCPServerType = Any  # Can be MCPServerStdio, MCPServerSSE, or MCPServerStreamableHTTP

# Server info type
ServerInfo = dict[str, Any]

__all__ = [
    "MCP_AVAILABLE",
    "MCPServerStdio",
    "MCPServerSSE",
    "MCPServerStreamableHTTP",
    "MCPServerType",
    "ServerInfo",
    "logger",
]
