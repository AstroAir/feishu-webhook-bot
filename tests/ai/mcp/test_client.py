"""Tests for MCPClient main class.

Tests cover:
- MCPClient initialization
- Server connection handling
- Tool discovery delegation
- Resource discovery delegation
- Lifecycle management (start/stop)
- Statistics and status
- Error handling
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from feishu_webhook_bot.ai.config import MCPConfig
from feishu_webhook_bot.ai.mcp import MCPClient
from feishu_webhook_bot.ai.mcp.base import MCP_AVAILABLE

pytestmark = pytest.mark.anyio(backends=["asyncio"])


class TestMCPClientInitialization:
    """Tests for MCPClient initialization."""

    def test_client_creation_default_config(self):
        """Test MCPClient creation with default configuration."""
        config = MCPConfig()

        client = MCPClient(config)

        assert client.config == config
        assert client._servers == {}
        assert client._mcp_servers == []
        assert client._started is False

    def test_client_creation_with_servers(self):
        """Test MCPClient creation with server configurations."""
        config = MCPConfig(
            enabled=True,
            servers=[
                {"name": "server1", "command": "python", "args": "-m mcp_server"},
                {"name": "server2", "url": "http://localhost:3000"},
            ],
        )

        client = MCPClient(config)

        assert len(config.servers) == 2
        assert client._started is False

    def test_client_creation_disabled(self):
        """Test MCPClient creation when disabled."""
        config = MCPConfig(enabled=False)

        client = MCPClient(config)

        assert client.config.enabled is False

    def test_client_has_managers(self):
        """Test MCPClient has all required managers."""
        config = MCPConfig()
        client = MCPClient(config)

        assert client._transport_manager is not None
        assert client._tool_manager is not None
        assert client._resource_manager is not None


class TestMCPClientStart:
    """Tests for MCPClient start functionality."""

    async def test_start_when_disabled(self):
        """Test start does nothing when MCP is disabled."""
        config = MCPConfig(enabled=False)
        client = MCPClient(config)

        await client.start()

        assert client._started is False

    async def test_start_already_started(self):
        """Test start warns when already started."""
        config = MCPConfig(enabled=False)
        client = MCPClient(config)
        client._started = True

        # Should not raise
        await client.start()

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_start_with_empty_servers(self):
        """Test start with no servers configured."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        await client.start()

        assert client._started is True
        assert client.get_server_count() == 0

        await client.stop()

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_start_with_invalid_server_config(self):
        """Test start with invalid server configuration."""
        config = MCPConfig(
            enabled=True,
            servers=[{"name": "invalid"}],  # Missing command and url
        )
        client = MCPClient(config)

        with pytest.raises(ValueError, match="must have either 'command' or 'url'"):
            await client.start()

    async def test_start_without_mcp_support(self):
        """Test start raises error when MCP support not available."""
        if MCP_AVAILABLE:
            pytest.skip("MCP support is available")

        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        with pytest.raises(RuntimeError, match="pydantic-ai MCP support not available"):
            await client.start()


class TestMCPClientServerConnection:
    """Tests for MCPClient server connection."""

    def test_get_mcp_servers_empty(self):
        """Test get_mcp_servers returns empty list initially."""
        config = MCPConfig()
        client = MCPClient(config)

        servers = client.get_mcp_servers()

        assert servers == []

    def test_is_started_false_initially(self):
        """Test is_started returns False initially."""
        config = MCPConfig()
        client = MCPClient(config)

        assert client.is_started() is False

    def test_is_started_after_start(self):
        """Test is_started after start."""
        config = MCPConfig(enabled=False)
        client = MCPClient(config)
        client._started = True

        assert client.is_started() is True

    def test_get_server_count_empty(self):
        """Test get_server_count returns 0 initially."""
        config = MCPConfig()
        client = MCPClient(config)

        assert client.get_server_count() == 0

    def test_get_server_names_empty(self):
        """Test get_server_names returns empty list initially."""
        config = MCPConfig()
        client = MCPClient(config)

        assert client.get_server_names() == []


class TestMCPClientToolDiscovery:
    """Tests for MCPClient tool discovery delegation."""

    async def test_discover_tools_not_started(self):
        """Test discover_tools returns empty list when not started."""
        config = MCPConfig(enabled=True)
        client = MCPClient(config)

        tools = await client.discover_tools()

        assert tools == []

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_discover_tools_empty(self):
        """Test discover_tools returns empty list when no servers."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        await client.start()
        try:
            tools = await client.discover_tools()
            assert tools == []
        finally:
            await client.stop()

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_discover_tools_with_mock_server(self):
        """Test discover_tools with mock server."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        await client.start()
        try:
            # Create mock tool
            tool = MagicMock()
            tool.name = "test_tool"
            tool.description = "Test tool"
            tool.inputSchema = {"properties": {}}

            mock_server = MagicMock()
            mock_server.list_tools = AsyncMock(return_value=[tool])

            client._servers["mock-server"] = {
                "config": {"name": "mock-server"},
                "mcp_server": mock_server,
                "connected": True,
            }

            tools = await client.discover_tools()

            assert len(tools) == 1
            assert tools[0]["name"] == "test_tool"
        finally:
            await client.stop()


class TestMCPClientToolExecution:
    """Tests for MCPClient tool execution delegation."""

    async def test_call_tool_not_started(self):
        """Test call_tool raises error when not started."""
        config = MCPConfig(enabled=True)
        client = MCPClient(config)

        with pytest.raises(RuntimeError, match="MCP client not started"):
            await client.call_tool("server", "tool", {})

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_call_tool_server_not_found(self):
        """Test call_tool returns error for unknown server."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        await client.start()
        try:
            result = await client.call_tool("unknown-server", "tool", {})

            assert result["success"] is False
            assert "not found" in result["error"].lower()
        finally:
            await client.stop()

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_call_tool_success(self):
        """Test successful tool execution."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        await client.start()
        try:
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
        finally:
            await client.stop()


class TestMCPClientToolInfo:
    """Tests for MCPClient tool info retrieval."""

    def test_get_tool_info_not_started(self):
        """Test get_tool_info returns None when not started."""
        config = MCPConfig(enabled=True)
        client = MCPClient(config)

        info = client.get_tool_info("server", "tool")

        assert info is None

    def test_get_tool_info_server_not_found(self):
        """Test get_tool_info returns None for unknown server."""
        config = MCPConfig(enabled=True)
        client = MCPClient(config)
        client._started = True

        info = client.get_tool_info("unknown-server", "tool")

        assert info is None

    def test_get_tool_info_success(self):
        """Test successful tool info retrieval."""
        config = MCPConfig(enabled=True)
        client = MCPClient(config)
        client._started = True

        mock_server = MagicMock()
        mock_server.tools = {
            "my_tool": {
                "description": "My tool",
                "parameters": {},
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


class TestMCPClientResourceDiscovery:
    """Tests for MCPClient resource discovery delegation."""

    async def test_discover_resources_not_started(self):
        """Test discover_resources returns empty list when not started."""
        config = MCPConfig(enabled=True)
        client = MCPClient(config)

        resources = await client.discover_resources()

        assert resources == []

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_discover_resources_empty(self):
        """Test discover_resources returns empty list when no servers."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        await client.start()
        try:
            resources = await client.discover_resources()
            assert resources == []
        finally:
            await client.stop()


class TestMCPClientStop:
    """Tests for MCPClient stop functionality."""

    async def test_stop_when_not_started(self):
        """Test stop does nothing when not started."""
        config = MCPConfig()
        client = MCPClient(config)

        await client.stop()

        assert client._started is False

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_stop_clears_state(self):
        """Test stop clears internal state."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        await client.start()
        client._servers = {"test": {"connected": True}}
        client._mcp_servers = [MagicMock()]

        await client.stop()

        assert client._started is False
        assert client._servers == {}
        assert client._mcp_servers == []

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_double_stop(self):
        """Test stopping twice is safe."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        await client.start()
        await client.stop()
        await client.stop()  # Should not raise

        assert client._started is False


class TestMCPClientStatus:
    """Tests for MCPClient status methods."""

    def test_get_stats_not_started(self):
        """Test get_stats when not started."""
        config = MCPConfig()
        client = MCPClient(config)

        stats = client.get_stats()

        assert stats["started"] is False
        assert stats["server_count"] == 0
        assert stats["servers"] == []
        assert stats["mcp_available"] == MCP_AVAILABLE

    def test_get_stats_started(self):
        """Test get_stats when started."""
        config = MCPConfig(enabled=True)
        client = MCPClient(config)
        client._started = True
        client._servers = {
            "server1": {"connected": True},
            "server2": {"connected": False},
        }

        stats = client.get_stats()

        assert stats["started"] is True
        assert stats["enabled"] is True
        assert stats["server_count"] == 2
        assert "server1" in stats["servers"]
        assert "server2" in stats["servers"]


class TestMCPClientConfiguration:
    """Tests for MCPClient configuration options."""

    def test_client_with_custom_timeout(self):
        """Test MCPClient with custom timeout."""
        config = MCPConfig(timeout_seconds=120.0)

        client = MCPClient(config)

        assert client.config.timeout_seconds == 120.0
        assert client._transport_manager.timeout_seconds == 120.0

    def test_client_with_multiple_servers(self):
        """Test MCPClient with multiple server configurations."""
        config = MCPConfig(
            enabled=True,
            servers=[
                {"name": "server1", "command": "cmd1"},
                {"name": "server2", "command": "cmd2"},
                {"name": "server3", "url": "http://localhost:3000"},
            ],
        )

        _ = MCPClient(config)

        assert len(config.servers) == 3


class TestMCPClientErrorHandling:
    """Tests for MCPClient error handling."""

    def test_invalid_server_config_no_command_or_url(self):
        """Test that server config without command or url is detected."""
        config = MCPConfig(
            enabled=True,
            servers=[{"name": "invalid"}],  # Missing command and url
        )

        # Client is created, but connection would fail
        _ = MCPClient(config)
        assert len(config.servers) == 1

    def test_server_config_with_empty_name(self):
        """Test server config with empty name uses 'unknown'."""
        config = MCPConfig(
            enabled=True,
            servers=[{"command": "test"}],  # Missing name
        )

        _ = MCPClient(config)

        # Server config is stored as-is
        assert config.servers[0].get("name") is None


class TestMCPClientLifecycle:
    """Tests for MCPClient lifecycle management."""

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_full_lifecycle(self):
        """Test complete MCPClient lifecycle."""
        config = MCPConfig(enabled=True, servers=[], timeout_seconds=30)
        client = MCPClient(config)

        # Initial state
        assert not client.is_started()
        assert client.get_server_count() == 0

        # Start
        await client.start()
        assert client.is_started()

        # Get stats
        stats = client.get_stats()
        assert stats["started"] is True
        assert stats["enabled"] is True

        # Stop
        await client.stop()
        assert not client.is_started()
        assert client.get_server_count() == 0

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_restart_lifecycle(self):
        """Test MCPClient can be restarted."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        # First cycle
        await client.start()
        assert client.is_started()
        await client.stop()
        assert not client.is_started()

        # Second cycle
        await client.start()
        assert client.is_started()
        await client.stop()
        assert not client.is_started()
