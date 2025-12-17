"""Comprehensive tests for enhanced MCP tool discovery functionality.

This module re-exports tests from the mcp/ subpackage for backward compatibility.
For new tests, add them to tests/ai/mcp/test_tools.py.

This module tests:
- discover_tools() method with actual tool discovery
- call_tool() method for tool execution
- get_tool_info() method for tool information retrieval
- Error handling for missing servers and tools
- Multiple transport type support
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from feishu_webhook_bot.ai.config import MCPConfig
from feishu_webhook_bot.ai.mcp import MCP_AVAILABLE, MCPClient

# Use anyio for async tests with asyncio backend only
pytestmark = pytest.mark.anyio(backends=["asyncio"])


class TestToolDiscovery:
    """Test tool discovery functionality."""

    async def test_discover_tools_not_started(self):
        """Test discovering tools when client not started."""
        config = MCPConfig(enabled=True)
        client = MCPClient(config)

        tools = await client.discover_tools()
        assert tools == []

    async def test_discover_tools_empty_servers(self):
        """Test discovering tools with no servers."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        if MCP_AVAILABLE:
            await client.start()
            try:
                tools = await client.discover_tools()
                assert isinstance(tools, list)
                assert tools == []
            finally:
                await client.stop()

    async def test_discover_tools_with_mock_server(self):
        """Test discovering tools from a mock MCP server."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        if MCP_AVAILABLE:
            await client.start()

            try:
                # Create proper mock tools
                tool1 = MagicMock()
                tool1.name = "test_tool_1"
                tool1.description = "Test tool 1"
                tool1.inputSchema = {"properties": {"param1": {"type": "string"}}}

                tool2 = MagicMock()
                tool2.name = "test_tool_2"
                tool2.description = "Test tool 2"
                tool2.inputSchema = {"properties": {"param2": {"type": "number"}}}

                # Mock an MCP server with tools
                mock_server = MagicMock()
                mock_server.list_tools = AsyncMock(return_value=[tool1, tool2])

                # Inject mock server
                client._servers["mock-server"] = {
                    "config": {"name": "mock-server"},
                    "mcp_server": mock_server,
                    "connected": True,
                }

                tools = await client.discover_tools()

                # Should discover tools from mock server
                assert len(tools) == 2
                assert tools[0]["name"] == "test_tool_1"
                assert tools[0]["server"] == "mock-server"
                assert tools[0]["description"] == "Test tool 1"
                assert "parameters" in tools[0]

                assert tools[1]["name"] == "test_tool_2"
                assert tools[1]["server"] == "mock-server"

            finally:
                await client.stop()

    async def test_discover_tools_with_capabilities(self):
        """Test discovering tools via get_capabilities method."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        if MCP_AVAILABLE:
            await client.start()

            try:
                # Mock an MCP server with capabilities
                # Mock server without list_tools to force use of get_capabilities
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

                client._servers["api-server"] = {
                    "config": {"name": "api-server"},
                    "mcp_server": mock_server,
                    "connected": True,
                }

                tools = await client.discover_tools()

                assert len(tools) == 2
                tool_names = {tool["name"] for tool in tools}
                assert "weather" in tool_names
                assert "search" in tool_names

            finally:
                await client.stop()

    async def test_discover_tools_server_error(self):
        """Test handling of errors during tool discovery."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        if MCP_AVAILABLE:
            await client.start()

            try:
                # Mock a server that raises an error
                mock_server = MagicMock()
                mock_server.list_tools = AsyncMock(side_effect=RuntimeError("Connection failed"))

                client._servers["broken-server"] = {
                    "config": {"name": "broken-server"},
                    "mcp_server": mock_server,
                    "connected": True,
                }

                # Should handle error gracefully
                tools = await client.discover_tools()
                assert isinstance(tools, list)

            finally:
                await client.stop()


class TestCallTool:
    """Test tool calling functionality."""

    async def test_call_tool_not_started(self):
        """Test calling tool when client not started."""
        config = MCPConfig(enabled=True)
        client = MCPClient(config)

        with pytest.raises(RuntimeError, match="MCP client not started"):
            await client.call_tool("server", "tool", {})

    async def test_call_tool_server_not_found(self):
        """Test calling tool on non-existent server."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        if MCP_AVAILABLE:
            await client.start()
            try:
                result = await client.call_tool("unknown-server", "tool", {})

                assert result["success"] is False
                assert "not found" in result["error"].lower()
                assert result["server"] == "unknown-server"
                assert result["tool"] == "tool"

            finally:
                await client.stop()

    async def test_call_tool_success(self):
        """Test successful tool execution."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        if MCP_AVAILABLE:
            await client.start()

            try:
                # Mock a server with call_tool method
                mock_server = MagicMock()
                mock_server.call_tool = AsyncMock(return_value={"result": "success"})

                client._servers["test-server"] = {
                    "config": {"name": "test-server"},
                    "mcp_server": mock_server,
                    "connected": True,
                }

                result = await client.call_tool("test-server", "my_tool", {"param": "value"})

                assert result["success"] is True
                assert result["result"] == {"result": "success"}
                assert result["server"] == "test-server"
                assert result["tool"] == "my_tool"

                # Verify the tool was called with correct arguments
                mock_server.call_tool.assert_called_once_with("my_tool", {"param": "value"})

            finally:
                await client.stop()

    async def test_call_tool_execute_tool_method(self):
        """Test tool execution using execute_tool method."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        if MCP_AVAILABLE:
            await client.start()

            try:
                # Mock a server with execute_tool method instead of call_tool
                mock_server = MagicMock()
                del mock_server.call_tool  # Remove call_tool
                mock_server.execute_tool = AsyncMock(return_value="execution result")

                client._servers["exec-server"] = {
                    "config": {"name": "exec-server"},
                    "mcp_server": mock_server,
                    "connected": True,
                }

                result = await client.call_tool("exec-server", "tool_x", {})

                assert result["success"] is True
                assert result["result"] == "execution result"

            finally:
                await client.stop()

    async def test_call_tool_no_matching_method(self):
        """Test tool execution when server has no execution method."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        if MCP_AVAILABLE:
            await client.start()

            try:
                # Create server with no execution methods
                mock_server = MagicMock(spec=["list_tools"])

                client._servers["broken-server"] = {
                    "config": {"name": "broken-server"},
                    "mcp_server": mock_server,
                    "connected": True,
                }

                result = await client.call_tool("broken-server", "tool", {})

                assert result["success"] is False
                # Either error message is acceptable since both indicate execution failed
                assert "Tool not found" in result["error"] or "does not support" in result["error"]

            finally:
                await client.stop()

    async def test_call_tool_with_error(self):
        """Test tool execution that raises an error."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        if MCP_AVAILABLE:
            await client.start()

            try:
                # Mock a server that raises an error
                mock_server = MagicMock()
                mock_server.call_tool = AsyncMock(side_effect=RuntimeError("Tool execution failed"))

                client._servers["error-server"] = {
                    "config": {"name": "error-server"},
                    "mcp_server": mock_server,
                    "connected": True,
                }

                result = await client.call_tool("error-server", "bad_tool", {})

                assert result["success"] is False
                assert "Tool execution failed" in result["error"]

            finally:
                await client.stop()


class TestGetToolInfo:
    """Test tool information retrieval."""

    def test_get_tool_info_not_started(self):
        """Test getting tool info when client not started."""
        config = MCPConfig(enabled=True)
        client = MCPClient(config)

        # Should not raise, just return None
        info = client.get_tool_info("server", "tool")
        assert info is None

    def test_get_tool_info_server_not_found(self):
        """Test getting tool info for non-existent server."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        info = client.get_tool_info("unknown-server", "tool")
        assert info is None

    def test_get_tool_info_from_tools_dict(self):
        """Test getting tool info from server tools dictionary."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        # Add a started flag to bypass the check
        client._started = True

        # Mock a server with tools dict
        mock_server = MagicMock()
        mock_server.tools = {
            "my_tool": {
                "description": "My tool description",
                "parameters": {"arg1": {"type": "string"}},
            }
        }

        client._servers["test-server"] = {
            "config": {"name": "test-server"},
            "mcp_server": mock_server,
            "connected": True,
        }

        info = client.get_tool_info("test-server", "my_tool")

        assert info is not None
        assert info["name"] == "my_tool"
        assert info["server"] == "test-server"
        assert info["description"] == "My tool description"
        assert info["parameters"] == {"arg1": {"type": "string"}}

    def test_get_tool_info_from_get_tool_method(self):
        """Test getting tool info using get_tool method."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        client._started = True

        # Mock a server with get_tool method
        mock_tool = MagicMock()
        mock_tool.description = "Tool from get_tool method"
        mock_tool.parameters = {"x": {"type": "number"}}

        mock_server = MagicMock()
        mock_server.tools = {}  # Empty tools dict
        mock_server.get_tool = MagicMock(return_value=mock_tool)

        client._servers["method-server"] = {
            "config": {"name": "method-server"},
            "mcp_server": mock_server,
            "connected": True,
        }

        info = client.get_tool_info("method-server", "tool_from_method")

        assert info is not None
        assert info["name"] == "tool_from_method"
        assert info["server"] == "method-server"
        assert info["description"] == "Tool from get_tool method"

    def test_get_tool_info_not_found(self):
        """Test getting info for non-existent tool."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        client._started = True

        # Mock a server without the tool
        mock_server = MagicMock()
        mock_server.tools = {}
        mock_server.get_tool = MagicMock(return_value=None)

        client._servers["test-server"] = {
            "config": {"name": "test-server"},
            "mcp_server": mock_server,
            "connected": True,
        }

        info = client.get_tool_info("test-server", "non_existent_tool")

        assert info is None

    def test_get_tool_info_with_error(self):
        """Test handling of errors when getting tool info."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        client._started = True

        # Mock a server without tools and get_tool that returns None
        mock_server = MagicMock(spec=["other_method"])

        client._servers["error-server"] = {
            "config": {"name": "error-server"},
            "mcp_server": mock_server,
            "connected": True,
        }

        # Should handle error gracefully
        info = client.get_tool_info("error-server", "tool")
        assert info is None


class TestIntegration:
    """Integration tests for tool discovery, info, and calling."""

    async def test_full_workflow(self):
        """Test complete workflow: discover, get info, call tool."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        if MCP_AVAILABLE:
            await client.start()

            try:
                # Create proper mock tool
                tool = MagicMock()
                tool.name = "calculate"
                tool.description = "Perform calculation"
                tool.inputSchema = {
                    "properties": {
                        "expression": {"type": "string"},
                    }
                }

                # Setup mock server with tools dictionary for get_tool_info
                mock_server = MagicMock()
                mock_server.list_tools = AsyncMock(return_value=[tool])
                mock_server.call_tool = AsyncMock(return_value=42)
                # Set up tools dict for get_tool_info to work
                mock_server.tools = {
                    "calculate": {
                        "description": "Perform calculation",
                        "parameters": {"expression": {"type": "string"}},
                    }
                }

                client._servers["calc-server"] = {
                    "config": {"name": "calc-server"},
                    "mcp_server": mock_server,
                    "connected": True,
                }

                # Step 1: Discover tools
                tools = await client.discover_tools()
                assert len(tools) == 1
                assert tools[0]["name"] == "calculate"

                # Step 2: Get tool info (using cached data)
                info = client.get_tool_info("calc-server", "calculate")
                assert info is not None
                assert info["description"] == "Perform calculation"

                # Step 3: Call the tool
                result = await client.call_tool("calc-server", "calculate", {"expression": "2+2"})
                assert result["success"] is True
                assert result["result"] == 42

            finally:
                await client.stop()
