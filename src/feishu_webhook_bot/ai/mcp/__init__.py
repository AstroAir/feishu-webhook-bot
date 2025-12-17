"""MCP (Model Context Protocol) client module.

This module provides integration with MCP servers using pydantic-ai's MCP support.
It supports multiple transport types:
- stdio: Run MCP server as subprocess
- sse: HTTP Server-Sent Events (deprecated)
- streamable-http: Modern HTTP streaming transport
"""

from .base import (
    MCP_AVAILABLE,
    MCPServerSSE,
    MCPServerStdio,
    MCPServerStreamableHTTP,
    MCPServerType,
    ServerInfo,
)
from .client import MCPClient
from .resources import MCPResourceManager
from .tools import MCPToolManager
from .transports import MCPTransportManager

__all__ = [
    # Main client
    "MCPClient",
    # Managers
    "MCPTransportManager",
    "MCPToolManager",
    "MCPResourceManager",
    # Base types and constants
    "MCP_AVAILABLE",
    "MCPServerStdio",
    "MCPServerSSE",
    "MCPServerStreamableHTTP",
    "MCPServerType",
    "ServerInfo",
]
