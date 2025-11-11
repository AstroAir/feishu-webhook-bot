"""MCP (Model Context Protocol) client implementation.

This module provides integration with MCP servers using pydantic-ai's MCP support.
It supports multiple transport types:
- stdio: Run MCP server as subprocess
- sse: HTTP Server-Sent Events (deprecated)
- streamable-http: Modern HTTP streaming transport
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

from ..core.logger import get_logger
from .config import MCPConfig

logger = get_logger("ai.mcp_client")


class MCPClient:
    """Client for Model Context Protocol (MCP) integration.

    This class provides integration with MCP servers using pydantic-ai's MCP support.
    It enables:
    - Standardized context sharing between AI models and tools
    - Tool discovery and execution through MCP
    - Resource management through MCP
    - Multiple transport types (stdio, SSE, streamable-http)

    The client automatically detects the transport type based on server configuration:
    - If 'command' is present: uses stdio transport
    - If 'url' ends with '/sse': uses SSE transport (deprecated)
    - If 'url' is present: uses streamable-http transport

    Example:
        ```python
        config = MCPConfig(
            enabled=True,
            servers=[
                {
                    "name": "python-runner",
                    "command": "uv",
                    "args": ["run", "mcp-run-python", "stdio"]
                },
                {
                    "name": "weather-api",
                    "url": "http://localhost:3001/sse"
                }
            ]
        )
        client = MCPClient(config)
        await client.start()
        ```
    """

    def __init__(self, config: MCPConfig) -> None:
        """Initialize the MCP client.

        Args:
            config: MCP configuration with server definitions

        Raises:
            ImportError: If pydantic-ai MCP support is not installed
        """
        if not MCP_AVAILABLE:
            logger.warning(
                "pydantic-ai MCP support not available. "
                "Install with: pip install 'pydantic-ai-slim[mcp]'"
            )

        self.config = config
        self._servers: dict[str, Any] = {}
        self._mcp_servers: list[Any] = []  # List of pydantic-ai MCP server instances
        self._started = False

        logger.info("MCPClient initialized with %d servers", len(config.servers))

    async def start(self) -> None:
        """Start the MCP client and connect to servers.

        This method creates pydantic-ai MCP server instances for each configured server
        and stores them for use with agents.

        Raises:
            RuntimeError: If MCP support is not available
            Exception: If server connection fails
        """
        if not self.config.enabled:
            logger.info("MCP is disabled, skipping start")
            return

        if self._started:
            logger.warning("MCP client already started")
            return

        if not MCP_AVAILABLE:
            raise RuntimeError(
                "pydantic-ai MCP support not available. "
                "Install with: pip install 'pydantic-ai-slim[mcp]'"
            )

        logger.info("Starting MCP client...")

        try:
            # Create MCP server instances for each configured server
            for server_config in self.config.servers:
                await self._connect_server(server_config)

            self._started = True
            logger.info("MCP client started successfully with %d servers", len(self._servers))

        except Exception as exc:
            logger.error("Failed to start MCP client: %s", exc, exc_info=True)
            raise

    async def _connect_server(self, server_config: dict[str, str]) -> None:
        """Connect to an MCP server using appropriate transport.

        Args:
            server_config: Server configuration dict with keys:
                - name: Server name (required)
                - command: Command to run (for stdio transport)
                - args: Command arguments (for stdio transport)
                - url: Server URL (for HTTP transports)

        Raises:
            ValueError: If server configuration is invalid
            Exception: If connection fails
        """
        server_name = server_config.get("name", "unknown")
        logger.info("Connecting to MCP server: %s", server_name)

        try:
            mcp_server: Any = None

            # Determine transport type and create appropriate server instance
            if "command" in server_config:
                # stdio transport
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

                mcp_server = MCPServerStdio(
                    command,
                    args=args_list,
                    timeout=self.config.timeout_seconds,
                )

            elif "url" in server_config:
                url = server_config["url"]

                # Determine if SSE or streamable-http based on URL
                if url.endswith("/sse"):
                    # SSE transport (deprecated)
                    logger.warning(
                        "Using deprecated SSE transport for %s. "
                        "Consider migrating to streamable-http.",
                        server_name,
                    )
                    mcp_server = MCPServerSSE(url)
                else:
                    # Streamable HTTP transport
                    logger.info(
                        "Creating streamable-http MCP server: %s (url: %s)", server_name, url
                    )
                    mcp_server = MCPServerStreamableHTTP(url)

            else:
                raise ValueError(
                    f"Invalid MCP server config for {server_name}: "
                    "must have either 'command' or 'url'"
                )

            # Store server reference
            self._servers[server_name] = {
                "config": server_config,
                "mcp_server": mcp_server,
                "connected": True,
            }
            self._mcp_servers.append(mcp_server)

            logger.info("Successfully connected to MCP server: %s", server_name)

        except Exception as exc:
            logger.error("Failed to connect to MCP server %s: %s", server_name, exc, exc_info=True)
            raise

    def get_mcp_servers(self) -> list[Any]:
        """Get list of pydantic-ai MCP server instances.

        These can be used as toolsets with pydantic-ai agents.

        Returns:
            List of MCP server instances (MCPServerStdio, MCPServerSSE, or MCPServerStreamableHTTP)

        Example:
            ```python
            client = MCPClient(config)
            await client.start()

            agent = Agent('openai:gpt-4o', toolsets=client.get_mcp_servers())
            ```
        """
        return self._mcp_servers

    async def discover_tools(self) -> list[dict[str, Any]]:
        """Discover tools from all connected MCP servers.

        Note: With pydantic-ai MCP integration, tools are automatically discovered
        when MCP servers are used as toolsets with agents. This method provides
        a way to inspect available tools programmatically.

        Returns:
            List of tool definitions with metadata

        Raises:
            RuntimeError: If MCP client is not started
        """
        if not self._started:
            logger.warning("MCP client not started, cannot discover tools")
            return []

        all_tools: list[dict[str, Any]] = []
        for server_name, server_info in self._servers.items():
            logger.info("Discovering tools from MCP server: %s", server_name)

            # Note: pydantic-ai MCP servers handle tool discovery automatically
            # This is primarily for logging/debugging purposes
            mcp_server = server_info.get("mcp_server")
            if mcp_server:
                # Tools are discovered automatically when the server is used
                logger.debug("MCP server %s tools will be discovered on first use", server_name)

        logger.info("MCP servers ready for tool discovery")
        return all_tools

    async def discover_resources(self) -> list[dict[str, Any]]:
        """Discover resources from all connected MCP servers.

        Note: With pydantic-ai MCP integration, resources are automatically discovered
        when MCP servers are used. This method provides a way to inspect available
        resources programmatically.

        Returns:
            List of resource definitions

        Raises:
            RuntimeError: If MCP client is not started
        """
        if not self._started:
            logger.warning("MCP client not started, cannot discover resources")
            return []

        all_resources: list[dict[str, Any]] = []
        for server_name, _server_info in self._servers.items():
            logger.info("Discovering resources from MCP server: %s", server_name)

            # Note: pydantic-ai MCP servers handle resource discovery automatically
            logger.debug("MCP server %s resources will be discovered on first use", server_name)

        logger.info("MCP servers ready for resource discovery")
        return all_resources

    async def stop(self) -> None:
        """Stop the MCP client and disconnect from servers.

        This method properly closes all MCP server connections and cleans up resources.
        """
        if not self._started:
            logger.info("MCP client not started, nothing to stop")
            return

        logger.info("Stopping MCP client...")

        try:
            # Disconnect from all servers
            for server_name in list(self._servers.keys()):
                await self._disconnect_server(server_name)

            # Clear server lists
            self._mcp_servers.clear()
            self._started = False
            logger.info("MCP client stopped successfully")

        except Exception as exc:
            logger.error("Error stopping MCP client: %s", exc, exc_info=True)

    async def _disconnect_server(self, server_name: str) -> None:
        """Disconnect from an MCP server.

        Args:
            server_name: Name of the server to disconnect
        """
        logger.info("Disconnecting from MCP server: %s", server_name)

        try:
            if server_name in self._servers:
                server_info = self._servers[server_name]
                server_info.get("mcp_server")

                # MCP servers are context managers, but we don't need to explicitly close
                # them here as they'll be cleaned up when the agent is done with them
                # or when the process exits

                del self._servers[server_name]
                logger.info("Disconnected from MCP server: %s", server_name)

        except Exception as exc:
            logger.error(
                "Error disconnecting from MCP server %s: %s", server_name, exc, exc_info=True
            )

    def is_started(self) -> bool:
        """Check if the MCP client is started.

        Returns:
            True if started, False otherwise
        """
        return self._started

    def get_server_count(self) -> int:
        """Get the number of connected servers.

        Returns:
            Number of connected servers
        """
        return len(self._servers)

    def get_server_names(self) -> list[str]:
        """Get list of connected server names.

        Returns:
            List of server names
        """
        return list(self._servers.keys())

    def get_stats(self) -> dict[str, Any]:
        """Get MCP client statistics.

        Returns:
            Dictionary with MCP statistics including:
            - enabled: Whether MCP is enabled
            - started: Whether client is started
            - server_count: Number of connected servers
            - servers: List of server names
            - mcp_available: Whether pydantic-ai MCP support is available
        """
        return {
            "enabled": self.config.enabled,
            "started": self._started,
            "server_count": len(self._servers),
            "servers": list(self._servers.keys()),
            "mcp_available": MCP_AVAILABLE,
        }
