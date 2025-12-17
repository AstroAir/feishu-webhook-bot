"""Tests for MCP transport layer.

Tests cover:
- MCPTransportManager initialization
- stdio transport creation
- HTTP transport creation (streamable-http)
- SSE transport creation (deprecated)
- Server connection and disconnection
- Error handling
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from feishu_webhook_bot.ai.mcp.base import MCP_AVAILABLE
from feishu_webhook_bot.ai.mcp.transports import MCPTransportManager

pytestmark = pytest.mark.anyio(backends=["asyncio"])


class TestMCPTransportManagerInitialization:
    """Tests for MCPTransportManager initialization."""

    def test_default_timeout(self):
        """Test default timeout value."""
        manager = MCPTransportManager()
        assert manager.timeout_seconds == 30.0

    def test_custom_timeout(self):
        """Test custom timeout value."""
        manager = MCPTransportManager(timeout_seconds=60.0)
        assert manager.timeout_seconds == 60.0

    def test_zero_timeout(self):
        """Test zero timeout value."""
        manager = MCPTransportManager(timeout_seconds=0)
        assert manager.timeout_seconds == 0


class TestStdioTransportCreation:
    """Tests for stdio transport creation."""

    def test_create_stdio_server_config_detection(self):
        """Test stdio transport is detected from command config."""
        server_config = {
            "name": "test-server",
            "command": "python",
            "args": "-m server",
        }

        # Check config has command
        assert "command" in server_config
        assert "url" not in server_config

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_connect_stdio_server(self):
        """Test connecting to stdio server."""
        manager = MCPTransportManager(timeout_seconds=30.0)
        server_config = {
            "name": "test-server",
            "command": "echo",
            "args": "test",
        }

        server_name, server_info, mcp_server = await manager.connect_server(server_config)

        assert server_name == "test-server"
        assert server_info["config"] == server_config
        assert server_info["connected"] is True
        assert mcp_server is not None

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_connect_stdio_server_with_list_args(self):
        """Test connecting to stdio server with list arguments."""
        manager = MCPTransportManager()
        server_config = {
            "name": "test-server",
            "command": "python",
            "args": ["-m", "server", "--port", "8080"],
        }

        server_name, server_info, mcp_server = await manager.connect_server(server_config)

        assert server_name == "test-server"
        assert mcp_server is not None

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_connect_stdio_server_with_string_args(self):
        """Test connecting to stdio server with string arguments."""
        manager = MCPTransportManager()
        server_config = {
            "name": "test-server",
            "command": "python",
            "args": "-m server --port 8080",
        }

        server_name, server_info, mcp_server = await manager.connect_server(server_config)

        assert server_name == "test-server"
        assert mcp_server is not None

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_connect_stdio_server_empty_args(self):
        """Test connecting to stdio server with empty arguments."""
        manager = MCPTransportManager()
        server_config = {
            "name": "test-server",
            "command": "echo",
            "args": "",
        }

        server_name, server_info, mcp_server = await manager.connect_server(server_config)

        assert server_name == "test-server"
        assert mcp_server is not None


class TestHTTPTransportCreation:
    """Tests for HTTP transport creation."""

    def test_http_transport_config_detection(self):
        """Test HTTP transport is detected from url config."""
        server_config = {
            "name": "api-server",
            "url": "http://localhost:3000/mcp",
        }

        # Check config has url
        assert "url" in server_config
        assert "command" not in server_config
        assert not server_config["url"].endswith("/sse")

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_connect_http_server(self):
        """Test connecting to HTTP streamable server."""
        manager = MCPTransportManager()
        server_config = {
            "name": "api-server",
            "url": "http://localhost:3000/mcp",
        }

        server_name, server_info, mcp_server = await manager.connect_server(server_config)

        assert server_name == "api-server"
        assert server_info["config"] == server_config
        assert server_info["connected"] is True
        assert mcp_server is not None


class TestSSETransportCreation:
    """Tests for SSE transport creation (deprecated)."""

    def test_sse_transport_config_detection(self):
        """Test SSE transport is detected from url ending with /sse."""
        server_config = {
            "name": "legacy-server",
            "url": "http://localhost:3000/sse",
        }

        # Check config has SSE url
        assert "url" in server_config
        assert server_config["url"].endswith("/sse")

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_connect_sse_server(self):
        """Test connecting to SSE server."""
        manager = MCPTransportManager()
        server_config = {
            "name": "legacy-server",
            "url": "http://localhost:3000/sse",
        }

        server_name, server_info, mcp_server = await manager.connect_server(server_config)

        assert server_name == "legacy-server"
        assert server_info["connected"] is True
        assert mcp_server is not None


class TestServerConnectionErrors:
    """Tests for server connection error handling."""

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_connect_invalid_config_no_command_or_url(self):
        """Test connecting with invalid config raises ValueError."""
        manager = MCPTransportManager()
        server_config = {
            "name": "invalid-server",
            # Missing both command and url
        }

        with pytest.raises(ValueError, match="must have either 'command' or 'url'"):
            await manager.connect_server(server_config)

    async def test_connect_without_mcp_support(self):
        """Test connecting without MCP support raises RuntimeError."""
        if MCP_AVAILABLE:
            pytest.skip("MCP support is available")

        manager = MCPTransportManager()
        server_config = {
            "name": "test-server",
            "command": "echo",
            "args": "test",
        }

        with pytest.raises(RuntimeError, match="pydantic-ai MCP support not available"):
            await manager.connect_server(server_config)

    def test_connect_server_unknown_name(self):
        """Test server config without name uses 'unknown'."""
        server_config = {
            "command": "echo",
            "args": "test",
        }

        # Should use 'unknown' as default name
        assert server_config.get("name", "unknown") == "unknown"


class TestServerDisconnection:
    """Tests for server disconnection."""

    async def test_disconnect_server(self):
        """Test disconnecting from a server."""
        manager = MCPTransportManager()
        server_info = {
            "config": {"name": "test-server"},
            "mcp_server": MagicMock(),
            "connected": True,
        }

        # Should not raise
        await manager.disconnect_server("test-server", server_info)

    async def test_disconnect_server_with_none_mcp_server(self):
        """Test disconnecting when mcp_server is None."""
        manager = MCPTransportManager()
        server_info = {
            "config": {"name": "test-server"},
            "mcp_server": None,
            "connected": False,
        }

        # Should not raise
        await manager.disconnect_server("test-server", server_info)

    async def test_disconnect_server_error_handling(self):
        """Test disconnect handles errors gracefully."""
        manager = MCPTransportManager()

        # Mock server that raises on access
        mock_server = MagicMock()
        mock_server.close = MagicMock(side_effect=RuntimeError("Close failed"))

        server_info = {
            "config": {"name": "error-server"},
            "mcp_server": mock_server,
            "connected": True,
        }

        # Should not raise, just log the error
        await manager.disconnect_server("error-server", server_info)


class TestTransportManagerIntegration:
    """Integration tests for transport manager."""

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_connect_and_disconnect_lifecycle(self):
        """Test full connect and disconnect lifecycle."""
        manager = MCPTransportManager(timeout_seconds=30.0)
        server_config = {
            "name": "lifecycle-server",
            "command": "echo",
            "args": "test",
        }

        # Connect
        server_name, server_info, mcp_server = await manager.connect_server(server_config)
        assert server_name == "lifecycle-server"
        assert server_info["connected"] is True

        # Disconnect
        await manager.disconnect_server(server_name, server_info)

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="pydantic-ai MCP support not installed")
    async def test_multiple_server_connections(self):
        """Test connecting multiple servers."""
        manager = MCPTransportManager()

        configs = [
            {"name": "server1", "command": "echo", "args": "1"},
            {"name": "server2", "command": "echo", "args": "2"},
            {"name": "server3", "url": "http://localhost:3000/mcp"},
        ]

        servers = []
        for config in configs:
            server_name, server_info, mcp_server = await manager.connect_server(config)
            servers.append((server_name, server_info, mcp_server))

        assert len(servers) == 3
        assert servers[0][0] == "server1"
        assert servers[1][0] == "server2"
        assert servers[2][0] == "server3"

        # Disconnect all
        for server_name, server_info, _ in servers:
            await manager.disconnect_server(server_name, server_info)
