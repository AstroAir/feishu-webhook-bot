"""Tool discovery and execution for MCP servers.

This module handles discovering and executing tools from MCP servers.
"""

from __future__ import annotations

from typing import Any

from ...core.logger import get_logger
from .base import MCPServerType, ServerInfo

logger = get_logger("ai.mcp.tools")


class MCPToolManager:
    """Manages MCP tool discovery and execution.

    This class provides methods for discovering available tools from MCP servers
    and executing them with proper error handling.
    """

    async def discover_tools(
        self,
        servers: dict[str, ServerInfo],
    ) -> list[dict[str, Any]]:
        """Discover tools from all connected MCP servers.

        This method discovers tools from all connected MCP servers and provides
        detailed information about each tool including its name, description, and
        expected parameters.

        Args:
            servers: Dictionary of server name to server info

        Returns:
            List of tool definitions with:
            - server: Server name
            - name: Tool name
            - description: Tool description
            - parameters: Tool input schema (dict)
            - input_schema: Full input schema for the tool

        Example:
            ```python
            tools = await tool_manager.discover_tools(servers)
            for tool in tools:
                print(f"Server: {tool['server']}, Tool: {tool['name']}")
            ```
        """
        all_tools: list[dict[str, Any]] = []

        for server_name, server_info in servers.items():
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
        mcp_server: MCPServerType,
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
        servers: dict[str, ServerInfo],
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Call a specific tool on an MCP server.

        This method allows programmatic execution of MCP tools with error handling
        and logging.

        Args:
            servers: Dictionary of server name to server info
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

        Example:
            ```python
            result = await tool_manager.call_tool(
                servers,
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
        # Check if server exists
        if server_name not in servers:
            error_msg = f"MCP server not found: {server_name}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "server": server_name,
                "tool": tool_name,
            }

        server_info = servers[server_name]
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

        except ValueError:
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
        mcp_server: MCPServerType,
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
        servers: dict[str, ServerInfo],
        server_name: str,
        tool_name: str,
    ) -> dict[str, Any] | None:
        """Get information about a specific tool.

        This is a synchronous method that retrieves cached tool information.
        For up-to-date information, call discover_tools() first.

        Args:
            servers: Dictionary of server name to server info
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
            tool_info = tool_manager.get_tool_info(servers, "python-runner", "execute_python")
            if tool_info:
                print(f"Tool: {tool_info['name']}")
                print(f"Description: {tool_info['description']}")
            ```
        """
        # Check if server exists
        if server_name not in servers:
            logger.warning("MCP server not found: %s", server_name)
            return None

        server_info = servers[server_name]
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
        mcp_server: MCPServerType,
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
