"""MCP (Model Context Protocol) client implementation.

This module provides the main MCPClient class that integrates with MCP servers
using pydantic-ai's MCP support.
"""

from __future__ import annotations

from typing import Any

from ...core.logger import get_logger
from ..config import MCPConfig
from .base import MCP_AVAILABLE, MCPServerType, ServerInfo
from .resources import MCPResourceManager
from .tools import MCPToolManager
from .transports import MCPTransportManager

logger = get_logger("ai.mcp.client")


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
        self._servers: dict[str, ServerInfo] = {}
        self._mcp_servers: list[MCPServerType] = []  # List of pydantic-ai MCP server instances
        self._started = False

        # Initialize managers
        self._transport_manager = MCPTransportManager(timeout_seconds=config.timeout_seconds)
        self._tool_manager = MCPToolManager()
        self._resource_manager = MCPResourceManager()

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
                server_name, server_info, mcp_server = await self._transport_manager.connect_server(
                    server_config
                )
                self._servers[server_name] = server_info
                self._mcp_servers.append(mcp_server)

            self._started = True
            logger.info("MCP client started successfully with %d servers", len(self._servers))

        except Exception as exc:
            logger.error("Failed to start MCP client: %s", exc, exc_info=True)
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

        This method discovers tools from all connected MCP servers and provides
        detailed information about each tool including its name, description, and
        expected parameters.

        Returns:
            List of tool definitions with:
            - server: Server name
            - name: Tool name
            - description: Tool description
            - parameters: Tool input schema (dict)
            - input_schema: Full input schema for the tool

        Raises:
            RuntimeError: If MCP client is not started

        Example:
            ```python
            client = MCPClient(config)
            await client.start()
            tools = await client.discover_tools()
            for tool in tools:
                print(f"Server: {tool['server']}, Tool: {tool['name']}")
            ```
        """
        if not self._started:
            logger.warning("MCP client not started, cannot discover tools")
            return []

        return await self._tool_manager.discover_tools(self._servers)

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Call a specific tool on an MCP server.

        This method allows programmatic execution of MCP tools with error handling
        and logging.

        Args:
            server_name: Name of the MCP server containing the tool
            tool_name: Name of the tool to call
            arguments: Dictionary of arguments to pass to the tool

        Returns:
            Dictionary with:
            - success: Whether the call was successful (bool)
            - result: Tool execution result (if successful)
            - error: Error message (if failed)
            - server: Server name
            - tool: Tool name

        Raises:
            ValueError: If server or tool not found
            RuntimeError: If MCP client is not started

        Example:
            ```python
            client = MCPClient(config)
            await client.start()
            result = await client.call_tool(
                "python-runner",
                "execute_python",
                {"code": "print('Hello World')"}
            )
            if result["success"]:
                print(result["result"])
            else:
                print(result["error"])
            ```
        """
        if not self._started:
            raise RuntimeError("MCP client not started")

        return await self._tool_manager.call_tool(self._servers, server_name, tool_name, arguments)

    def get_tool_info(
        self,
        server_name: str,
        tool_name: str,
    ) -> dict[str, Any] | None:
        """Get information about a specific tool.

        This is a synchronous method that retrieves cached tool information.
        For up-to-date information, call discover_tools() first.

        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool

        Returns:
            Tool information dict with:
            - server: Server name
            - name: Tool name
            - description: Tool description
            - parameters: Tool parameters
            - input_schema: Full input schema
            Returns None if tool not found

        Example:
            ```python
            client = MCPClient(config)
            await client.start()
            await client.discover_tools()  # Discover tools first

            tool_info = client.get_tool_info("python-runner", "execute_python")
            if tool_info:
                print(f"Tool: {tool_info['name']}")
                print(f"Description: {tool_info['description']}")
            ```
        """
        return self._tool_manager.get_tool_info(self._servers, server_name, tool_name)

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

        return await self._resource_manager.discover_resources(self._servers)

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
                server_info = self._servers[server_name]
                await self._transport_manager.disconnect_server(server_name, server_info)
                del self._servers[server_name]

            # Clear server lists
            self._mcp_servers.clear()
            self._started = False
            logger.info("MCP client stopped successfully")

        except Exception as exc:
            logger.error("Error stopping MCP client: %s", exc, exc_info=True)

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
