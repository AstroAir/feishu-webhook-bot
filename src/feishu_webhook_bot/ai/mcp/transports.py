"""Transport layer for MCP server connections.

This module handles the connection logic for different MCP transport types:
- stdio: Run MCP server as subprocess
- sse: HTTP Server-Sent Events (deprecated)
- streamable-http: Modern HTTP streaming transport
"""

from __future__ import annotations

from ...core.logger import get_logger
from .base import (
    MCP_AVAILABLE,
    MCPServerSSE,
    MCPServerStdio,
    MCPServerStreamableHTTP,
    MCPServerType,
    ServerInfo,
)

logger = get_logger("ai.mcp.transports")


class MCPTransportManager:
    """Manages MCP server transport connections.

    This class handles creating and managing connections to MCP servers
    using different transport types (stdio, SSE, streamable-http).
    """

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        """Initialize the transport manager.

        Args:
            timeout_seconds: Timeout for server connections
        """
        self.timeout_seconds = timeout_seconds

    async def connect_server(
        self,
        server_config: dict[str, str],
    ) -> tuple[str, ServerInfo, MCPServerType]:
        """Connect to an MCP server using appropriate transport.

        Args:
            server_config: Server configuration dict with keys:
                - name: Server name (required)
                - command: Command to run (for stdio transport)
                - args: Command arguments (for stdio transport)
                - url: Server URL (for HTTP transports)

        Returns:
            Tuple of (server_name, server_info, mcp_server)

        Raises:
            ValueError: If server configuration is invalid
            RuntimeError: If MCP support is not available
            Exception: If connection fails
        """
        if not MCP_AVAILABLE:
            raise RuntimeError(
                "pydantic-ai MCP support not available. "
                "Install with: pip install 'pydantic-ai-slim[mcp]'"
            )

        server_name = server_config.get("name", "unknown")
        logger.info("Connecting to MCP server: %s", server_name)

        try:
            mcp_server: MCPServerType = None

            # Determine transport type and create appropriate server instance
            if "command" in server_config:
                mcp_server = self._create_stdio_server(server_name, server_config)

            elif "url" in server_config:
                mcp_server = self._create_http_server(server_name, server_config)

            else:
                raise ValueError(
                    f"Invalid MCP server config for {server_name}: "
                    "must have either 'command' or 'url'"
                )

            # Create server info
            server_info: ServerInfo = {
                "config": server_config,
                "mcp_server": mcp_server,
                "connected": True,
            }

            logger.info("Successfully connected to MCP server: %s", server_name)
            return server_name, server_info, mcp_server

        except Exception as exc:
            logger.error("Failed to connect to MCP server %s: %s", server_name, exc, exc_info=True)
            raise

    def _create_stdio_server(
        self,
        server_name: str,
        server_config: dict[str, str],
    ) -> MCPServerType:
        """Create a stdio transport MCP server.

        Args:
            server_name: Name of the server
            server_config: Server configuration

        Returns:
            MCPServerStdio instance
        """
        command = server_config["command"]
        args = server_config.get("args", "")

        # Parse args if it's a string
        args_list = (args.split() if args else []) if isinstance(args, str) else args

        logger.info(
            "Creating stdio MCP server: %s (command: %s, args: %s)",
            server_name,
            command,
            args_list,
        )

        return MCPServerStdio(
            command,
            args=args_list,
            timeout=self.timeout_seconds,
        )

    def _create_http_server(
        self,
        server_name: str,
        server_config: dict[str, str],
    ) -> MCPServerType:
        """Create an HTTP transport MCP server (SSE or streamable-http).

        Args:
            server_name: Name of the server
            server_config: Server configuration

        Returns:
            MCPServerSSE or MCPServerStreamableHTTP instance
        """
        url = server_config["url"]

        # Determine if SSE or streamable-http based on URL
        if url.endswith("/sse"):
            # SSE transport (deprecated)
            logger.warning(
                "Using deprecated SSE transport for %s. Consider migrating to streamable-http.",
                server_name,
            )
            return MCPServerSSE(url)
        else:
            # Streamable HTTP transport
            logger.info("Creating streamable-http MCP server: %s (url: %s)", server_name, url)
            return MCPServerStreamableHTTP(url)

    async def disconnect_server(self, server_name: str, server_info: ServerInfo) -> None:
        """Disconnect from an MCP server.

        Args:
            server_name: Name of the server to disconnect
            server_info: Server information dict
        """
        logger.info("Disconnecting from MCP server: %s", server_name)

        try:
            # MCP servers are context managers, but we don't need to explicitly close
            # them here as they'll be cleaned up when the agent is done with them
            # or when the process exits
            server_info.get("mcp_server")
            logger.info("Disconnected from MCP server: %s", server_name)

        except Exception as exc:
            logger.error(
                "Error disconnecting from MCP server %s: %s", server_name, exc, exc_info=True
            )
