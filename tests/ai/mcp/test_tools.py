"""Tests for MCP tool manager.

Tests cover:
- MCPToolManager initialization
- Tool discovery from servers
- Tool execution
- Tool information retrieval
- Error handling
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from feishu_webhook_bot.ai.mcp.base import ServerInfo
from feishu_webhook_bot.ai.mcp.tools import MCPToolManager

pytestmark = pytest.mark.anyio(backends=["asyncio"])


class TestMCPToolManagerInitialization:
    """Tests for MCPToolManager initialization."""

    def test_create_tool_manager(self):
        """Test creating a tool manager."""
        manager = MCPToolManager()
        assert manager is not None


class TestToolDiscovery:
    """Tests for tool discovery functionality."""

    async def test_discover_tools_empty_servers(self):
        """Test discovering tools with no servers."""
        manager = MCPToolManager()
        servers: dict[str, ServerInfo] = {}

        tools = await manager.discover_tools(servers)

        assert tools == []

    async def test_discover_tools_server_without_mcp_server(self):
        """Test discovering tools when server has no mcp_server."""
        manager = MCPToolManager()
        servers: dict[str, ServerInfo] = {
            "test-server": {
                "config": {"name": "test-server"},
                "mcp_server": None,
                "connected": False,
            }
        }

        tools = await manager.discover_tools(servers)

        assert tools == []

    async def test_discover_tools_with_list_tools_method(self):
        """Test discovering tools using list_tools method."""
        manager = MCPToolManager()

        # Create mock tools
        tool1 = MagicMock()
        tool1.name = "tool1"
        tool1.description = "Tool 1 description"
        tool1.inputSchema = {"properties": {"param1": {"type": "string"}}}

        tool2 = MagicMock()
        tool2.name = "tool2"
        tool2.description = "Tool 2 description"
        tool2.inputSchema = {"properties": {"param2": {"type": "number"}}}

        mock_server = MagicMock()
        mock_server.list_tools = AsyncMock(return_value=[tool1, tool2])

        servers: dict[str, ServerInfo] = {
            "test-server": {
                "config": {"name": "test-server"},
                "mcp_server": mock_server,
                "connected": True,
            }
        }

        tools = await manager.discover_tools(servers)

        assert len(tools) == 2
        assert tools[0]["name"] == "tool1"
        assert tools[0]["server"] == "test-server"
        assert tools[0]["description"] == "Tool 1 description"
        assert "parameters" in tools[0]
        assert tools[1]["name"] == "tool2"

    async def test_discover_tools_with_get_capabilities_method(self):
        """Test discovering tools using get_capabilities method."""
        manager = MCPToolManager()

        # Mock server without list_tools but with get_capabilities
        mock_server = MagicMock(spec=["get_capabilities"])
        mock_server.get_capabilities = AsyncMock(
            return_value={
                "tools": {
                    "weather": {
                        "description": "Get weather info",
                        "parameters": {"location": {"type": "string"}},
                    },
                    "search": {
                        "description": "Search the web",
                        "parameters": {"query": {"type": "string"}},
                    },
                }
            }
        )

        servers: dict[str, ServerInfo] = {
            "api-server": {
                "config": {"name": "api-server"},
                "mcp_server": mock_server,
                "connected": True,
            }
        }

        tools = await manager.discover_tools(servers)

        assert len(tools) == 2
        tool_names = {tool["name"] for tool in tools}
        assert "weather" in tool_names
        assert "search" in tool_names

    async def test_discover_tools_server_without_tool_methods(self):
        """Test discovering tools from server without standard methods."""
        manager = MCPToolManager()

        # Mock server without list_tools or get_capabilities
        mock_server = MagicMock(spec=["other_method"])

        servers: dict[str, ServerInfo] = {
            "basic-server": {
                "config": {"name": "basic-server"},
                "mcp_server": mock_server,
                "connected": True,
            }
        }

        tools = await manager.discover_tools(servers)

        assert tools == []

    async def test_discover_tools_handles_server_error(self):
        """Test discovering tools handles server errors gracefully."""
        manager = MCPToolManager()

        mock_server = MagicMock()
        mock_server.list_tools = AsyncMock(side_effect=RuntimeError("Connection failed"))

        servers: dict[str, ServerInfo] = {
            "broken-server": {
                "config": {"name": "broken-server"},
                "mcp_server": mock_server,
                "connected": True,
            }
        }

        # Should not raise, just return empty list
        tools = await manager.discover_tools(servers)

        assert isinstance(tools, list)

    async def test_discover_tools_multiple_servers(self):
        """Test discovering tools from multiple servers."""
        manager = MCPToolManager()

        # Server 1 with list_tools
        tool1 = MagicMock()
        tool1.name = "tool_from_server1"
        tool1.description = "Tool from server 1"
        tool1.inputSchema = {}

        mock_server1 = MagicMock()
        mock_server1.list_tools = AsyncMock(return_value=[tool1])

        # Server 2 with get_capabilities
        mock_server2 = MagicMock(spec=["get_capabilities"])
        mock_server2.get_capabilities = AsyncMock(
            return_value={
                "tools": {
                    "tool_from_server2": {
                        "description": "Tool from server 2",
                        "parameters": {},
                    }
                }
            }
        )

        servers: dict[str, ServerInfo] = {
            "server1": {
                "config": {"name": "server1"},
                "mcp_server": mock_server1,
                "connected": True,
            },
            "server2": {
                "config": {"name": "server2"},
                "mcp_server": mock_server2,
                "connected": True,
            },
        }

        tools = await manager.discover_tools(servers)

        assert len(tools) == 2
        tool_names = {tool["name"] for tool in tools}
        assert "tool_from_server1" in tool_names
        assert "tool_from_server2" in tool_names


class TestToolExecution:
    """Tests for tool execution functionality."""

    async def test_call_tool_server_not_found(self):
        """Test calling tool on non-existent server."""
        manager = MCPToolManager()
        servers: dict[str, ServerInfo] = {}

        result = await manager.call_tool(servers, "unknown-server", "tool", {})

        assert result["success"] is False
        assert "not found" in result["error"].lower()
        assert result["server"] == "unknown-server"
        assert result["tool"] == "tool"

    async def test_call_tool_server_not_connected(self):
        """Test calling tool when server has no mcp_server."""
        manager = MCPToolManager()
        servers: dict[str, ServerInfo] = {
            "test-server": {
                "config": {"name": "test-server"},
                "mcp_server": None,
                "connected": False,
            }
        }

        result = await manager.call_tool(servers, "test-server", "tool", {})

        assert result["success"] is False
        assert "not connected" in result["error"].lower()

    async def test_call_tool_success_with_call_tool_method(self):
        """Test successful tool execution using call_tool method."""
        manager = MCPToolManager()

        mock_server = MagicMock()
        mock_server.call_tool = AsyncMock(return_value={"result": "success"})

        servers: dict[str, ServerInfo] = {
            "test-server": {
                "config": {"name": "test-server"},
                "mcp_server": mock_server,
                "connected": True,
            }
        }

        result = await manager.call_tool(servers, "test-server", "my_tool", {"param": "value"})

        assert result["success"] is True
        assert result["result"] == {"result": "success"}
        assert result["server"] == "test-server"
        assert result["tool"] == "my_tool"
        mock_server.call_tool.assert_called_once_with("my_tool", {"param": "value"})

    async def test_call_tool_success_with_execute_tool_method(self):
        """Test successful tool execution using execute_tool method."""
        manager = MCPToolManager()

        mock_server = MagicMock()
        del mock_server.call_tool  # Remove call_tool
        mock_server.execute_tool = AsyncMock(return_value="execution result")

        servers: dict[str, ServerInfo] = {
            "exec-server": {
                "config": {"name": "exec-server"},
                "mcp_server": mock_server,
                "connected": True,
            }
        }

        result = await manager.call_tool(servers, "exec-server", "tool_x", {})

        assert result["success"] is True
        assert result["result"] == "execution result"

    async def test_call_tool_success_with_invoke_tool_method(self):
        """Test successful tool execution using invoke_tool method."""
        manager = MCPToolManager()

        mock_server = MagicMock()
        del mock_server.call_tool
        del mock_server.execute_tool
        mock_server.invoke_tool = AsyncMock(return_value="invoke result")

        servers: dict[str, ServerInfo] = {
            "invoke-server": {
                "config": {"name": "invoke-server"},
                "mcp_server": mock_server,
                "connected": True,
            }
        }

        result = await manager.call_tool(servers, "invoke-server", "tool_y", {})

        assert result["success"] is True
        assert result["result"] == "invoke result"

    async def test_call_tool_no_execution_method(self):
        """Test calling tool when server has no execution method."""
        manager = MCPToolManager()

        mock_server = MagicMock(spec=["list_tools"])

        servers: dict[str, ServerInfo] = {
            "broken-server": {
                "config": {"name": "broken-server"},
                "mcp_server": mock_server,
                "connected": True,
            }
        }

        result = await manager.call_tool(servers, "broken-server", "tool", {})

        assert result["success"] is False
        assert "Tool not found" in result["error"] or "does not support" in result["error"]

    async def test_call_tool_execution_error(self):
        """Test tool execution that raises an error."""
        manager = MCPToolManager()

        mock_server = MagicMock()
        mock_server.call_tool = AsyncMock(side_effect=RuntimeError("Tool execution failed"))

        servers: dict[str, ServerInfo] = {
            "error-server": {
                "config": {"name": "error-server"},
                "mcp_server": mock_server,
                "connected": True,
            }
        }

        result = await manager.call_tool(servers, "error-server", "bad_tool", {})

        assert result["success"] is False
        assert "Tool execution failed" in result["error"]


class TestToolInfoRetrieval:
    """Tests for tool information retrieval."""

    def test_get_tool_info_server_not_found(self):
        """Test getting tool info for non-existent server."""
        manager = MCPToolManager()
        servers: dict[str, ServerInfo] = {}

        info = manager.get_tool_info(servers, "unknown-server", "tool")

        assert info is None

    def test_get_tool_info_server_not_connected(self):
        """Test getting tool info when server has no mcp_server."""
        manager = MCPToolManager()
        servers: dict[str, ServerInfo] = {
            "test-server": {
                "config": {"name": "test-server"},
                "mcp_server": None,
                "connected": False,
            }
        }

        info = manager.get_tool_info(servers, "test-server", "tool")

        assert info is None

    def test_get_tool_info_from_tools_dict(self):
        """Test getting tool info from server tools dictionary."""
        manager = MCPToolManager()

        mock_server = MagicMock()
        mock_server.tools = {
            "my_tool": {
                "description": "My tool description",
                "parameters": {"arg1": {"type": "string"}},
            }
        }

        servers: dict[str, ServerInfo] = {
            "test-server": {
                "config": {"name": "test-server"},
                "mcp_server": mock_server,
                "connected": True,
            }
        }

        info = manager.get_tool_info(servers, "test-server", "my_tool")

        assert info is not None
        assert info["name"] == "my_tool"
        assert info["server"] == "test-server"
        assert info["description"] == "My tool description"
        assert info["parameters"] == {"arg1": {"type": "string"}}

    def test_get_tool_info_from_get_tool_method(self):
        """Test getting tool info using get_tool method."""
        manager = MCPToolManager()

        mock_tool = MagicMock()
        mock_tool.description = "Tool from get_tool method"
        mock_tool.parameters = {"x": {"type": "number"}}

        mock_server = MagicMock()
        mock_server.tools = {}  # Empty tools dict
        mock_server.get_tool = MagicMock(return_value=mock_tool)

        servers: dict[str, ServerInfo] = {
            "method-server": {
                "config": {"name": "method-server"},
                "mcp_server": mock_server,
                "connected": True,
            }
        }

        info = manager.get_tool_info(servers, "method-server", "tool_from_method")

        assert info is not None
        assert info["name"] == "tool_from_method"
        assert info["server"] == "method-server"
        assert info["description"] == "Tool from get_tool method"

    def test_get_tool_info_not_found(self):
        """Test getting info for non-existent tool."""
        manager = MCPToolManager()

        mock_server = MagicMock()
        mock_server.tools = {}
        mock_server.get_tool = MagicMock(return_value=None)

        servers: dict[str, ServerInfo] = {
            "test-server": {
                "config": {"name": "test-server"},
                "mcp_server": mock_server,
                "connected": True,
            }
        }

        info = manager.get_tool_info(servers, "test-server", "non_existent_tool")

        assert info is None

    def test_get_tool_info_handles_error(self):
        """Test getting tool info handles errors gracefully."""
        manager = MCPToolManager()

        mock_server = MagicMock(spec=["other_method"])

        servers: dict[str, ServerInfo] = {
            "error-server": {
                "config": {"name": "error-server"},
                "mcp_server": mock_server,
                "connected": True,
            }
        }

        # Should handle error gracefully
        info = manager.get_tool_info(servers, "error-server", "tool")

        assert info is None


class TestToolManagerIntegration:
    """Integration tests for tool manager."""

    async def test_full_tool_workflow(self):
        """Test complete workflow: discover, get info, call tool."""
        manager = MCPToolManager()

        # Create mock tool
        tool = MagicMock()
        tool.name = "calculate"
        tool.description = "Perform calculation"
        tool.inputSchema = {"properties": {"expression": {"type": "string"}}}

        mock_server = MagicMock()
        mock_server.list_tools = AsyncMock(return_value=[tool])
        mock_server.call_tool = AsyncMock(return_value=42)
        mock_server.tools = {
            "calculate": {
                "description": "Perform calculation",
                "parameters": {"expression": {"type": "string"}},
            }
        }

        servers: dict[str, ServerInfo] = {
            "calc-server": {
                "config": {"name": "calc-server"},
                "mcp_server": mock_server,
                "connected": True,
            }
        }

        # Step 1: Discover tools
        tools = await manager.discover_tools(servers)
        assert len(tools) == 1
        assert tools[0]["name"] == "calculate"

        # Step 2: Get tool info
        info = manager.get_tool_info(servers, "calc-server", "calculate")
        assert info is not None
        assert info["description"] == "Perform calculation"

        # Step 3: Call the tool
        result = await manager.call_tool(servers, "calc-server", "calculate", {"expression": "2+2"})
        assert result["success"] is True
        assert result["result"] == 42
