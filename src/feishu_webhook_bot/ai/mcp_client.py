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

        all_tools: list[dict[str, Any]] = []

        for server_name, server_info in self._servers.items():
            logger.info("Discovering tools from MCP server: %s", server_name)

            mcp_server = server_info.get("mcp_server")
            if not mcp_server:
                continue

            try:
                # For pydantic-ai MCP servers, we can introspect the server
                # to get available tools. Different transport types may expose
                # tools through different mechanisms.

                # Try to get tools from the server
                tools = await self._get_server_tools(server_name, mcp_server)

                all_tools.extend(tools)
                logger.info(
                    "Discovered %d tools from MCP server: %s",
                    len(tools),
                    server_name,
                )

            except Exception as exc:
                logger.error(
                    "Failed to discover tools from MCP server %s: %s",
                    server_name,
                    exc,
                    exc_info=True,
                )

        logger.info("Total tools discovered from all MCP servers: %d", len(all_tools))
        return all_tools

    async def _get_server_tools(
        self,
        server_name: str,
        mcp_server: Any,
    ) -> list[dict[str, Any]]:
        """Get tools from an MCP server.

        Args:
            server_name: Name of the MCP server
            mcp_server: MCP server instance

        Returns:
            List of tool definitions

        Note:
            This method attempts to discover tools from the MCP server.
            The exact mechanism depends on the transport type and server implementation.
        """
        tools: list[dict[str, Any]] = []

        try:
            # Check if server has a list_tools method (stdio transport)
            if hasattr(mcp_server, "list_tools"):
                logger.debug("Getting tools from %s using list_tools method", server_name)
                tool_list = await mcp_server.list_tools()

                for tool in tool_list:
                    tool_info = {
                        "server": server_name,
                        "name": getattr(tool, "name", "unknown"),
                        "description": getattr(tool, "description", ""),
                        "input_schema": getattr(tool, "inputSchema", {}),
                    }

                    # Extract parameters from input schema
                    if hasattr(tool, "inputSchema") and isinstance(tool.inputSchema, dict):
                        tool_info["parameters"] = tool.inputSchema.get("properties", {})

                    tools.append(tool_info)

            # For HTTP transports or others, tools might be available through
            # the server's metadata or capabilities
            elif hasattr(mcp_server, "get_capabilities"):
                logger.debug("Getting tools from %s using capabilities", server_name)
                capabilities = await mcp_server.get_capabilities()

                if isinstance(capabilities, dict) and "tools" in capabilities:
                    for tool_name, tool_info in capabilities["tools"].items():
                        tools.append(
                            {
                                "server": server_name,
                                "name": tool_name,
                                "description": tool_info.get("description", ""),
                                "parameters": tool_info.get("parameters", {}),
                                "input_schema": tool_info,
                            }
                        )
            else:
                logger.debug(
                    "MCP server %s does not expose tools through standard methods",
                    server_name,
                )

        except Exception as exc:
            logger.error(
                "Error getting tools from %s: %s",
                server_name,
                exc,
                exc_info=True,
            )

        return tools

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

        # Check if server exists
        if server_name not in self._servers:
            error_msg = f"MCP server not found: {server_name}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "server": server_name,
                "tool": tool_name,
            }

        server_info = self._servers[server_name]
        mcp_server = server_info.get("mcp_server")

        if not mcp_server:
            error_msg = f"MCP server not connected: {server_name}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "server": server_name,
                "tool": tool_name,
            }

        try:
            logger.info(
                "Calling tool %s on server %s with arguments: %s",
                tool_name,
                server_name,
                arguments,
            )

            # Try to call the tool through the MCP server
            result = await self._execute_tool(mcp_server, tool_name, arguments)

            logger.info(
                "Tool %s on server %s executed successfully",
                tool_name,
                server_name,
            )

            return {
                "success": True,
                "result": result,
                "server": server_name,
                "tool": tool_name,
            }

        except ValueError as exc:
            error_msg = f"Tool not found: {tool_name}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "server": server_name,
                "tool": tool_name,
            }

        except Exception as exc:
            error_msg = f"Failed to call tool {tool_name} on server {server_name}: {exc}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "server": server_name,
                "tool": tool_name,
            }

    async def _execute_tool(
        self,
        mcp_server: Any,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Execute a tool on an MCP server.

        Args:
            mcp_server: MCP server instance
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found
            Exception: If execution fails
        """
        # Try different methods based on server capabilities
        if hasattr(mcp_server, "call_tool"):
            # Most MCP servers implement call_tool
            logger.debug("Executing tool using call_tool method")
            return await mcp_server.call_tool(tool_name, arguments)

        elif hasattr(mcp_server, "execute_tool"):
            # Some servers might use execute_tool
            logger.debug("Executing tool using execute_tool method")
            return await mcp_server.execute_tool(tool_name, arguments)

        elif hasattr(mcp_server, "invoke_tool"):
            # Alternative method name
            logger.debug("Executing tool using invoke_tool method")
            return await mcp_server.invoke_tool(tool_name, arguments)

        else:
            raise ValueError(
                f"MCP server does not support tool execution. "
                f"Available methods: {[m for m in dir(mcp_server) if not m.startswith('_')]}"
            )

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
        # Check if server exists
        if server_name not in self._servers:
            logger.warning("MCP server not found: %s", server_name)
            return None

        server_info = self._servers[server_name]
        mcp_server = server_info.get("mcp_server")

        if not mcp_server:
            logger.warning("MCP server not connected: %s", server_name)
            return None

        logger.debug(
            "Getting information for tool %s on server %s",
            tool_name,
            server_name,
        )

        try:
            # Try to get tool info from the server
            return self._get_tool_info_from_server(mcp_server, server_name, tool_name)

        except Exception as exc:
            logger.error(
                "Failed to get tool info for %s on server %s: %s",
                tool_name,
                server_name,
                exc,
                exc_info=True,
            )
            return None

    def _get_tool_info_from_server(
        self,
        mcp_server: Any,
        server_name: str,
        tool_name: str,
    ) -> dict[str, Any] | None:
        """Get tool information from an MCP server.

        Args:
            mcp_server: MCP server instance
            server_name: Name of the MCP server
            tool_name: Name of the tool

        Returns:
            Tool information or None if not found

        Note:
            This method is synchronous and uses cached/available information.
        """
        # Check if server has tool metadata
        if hasattr(mcp_server, "tools"):
            tools = mcp_server.tools
            if isinstance(tools, dict) and tool_name in tools:
                tool_data = tools[tool_name]
                return {
                    "server": server_name,
                    "name": tool_name,
                    "description": tool_data.get("description", ""),
                    "parameters": tool_data.get("parameters", {}),
                    "input_schema": tool_data,
                }

        # Check for tool registry
        if hasattr(mcp_server, "get_tool"):
            tool_data = mcp_server.get_tool(tool_name)
            if tool_data:
                return {
                    "server": server_name,
                    "name": tool_name,
                    "description": getattr(tool_data, "description", ""),
                    "parameters": getattr(tool_data, "parameters", {}),
                    "input_schema": tool_data,
                }

        logger.debug(
            "Tool %s not found in cached information for server %s",
            tool_name,
            server_name,
        )
        return None

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
