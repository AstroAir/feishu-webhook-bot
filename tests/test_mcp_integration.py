"""Comprehensive tests for MCP (Model Context Protocol) integration.

This module tests:
- MCP client initialization with different transport types
- Lazy MCP initialization in AIAgent
- MCP server registration as toolsets
- Error handling and graceful degradation
- Integration with built-in tools
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from feishu_webhook_bot.ai import AIAgent, AIConfig
from feishu_webhook_bot.ai.config import MCPConfig
from feishu_webhook_bot.ai.mcp_client import MCP_AVAILABLE, MCPClient

# Use anyio for async tests with asyncio backend only
pytestmark = pytest.mark.anyio(backends=["asyncio"])


class TestMCPConfig:
    """Test MCP configuration."""

    def test_mcp_config_defaults(self):
        """Test default MCP configuration values."""
        config = MCPConfig()
        assert config.enabled is False
        assert config.servers == []
        assert config.timeout_seconds == 30

    def test_mcp_config_with_stdio_server(self):
        """Test MCP config with stdio transport server."""
        config = MCPConfig(
            enabled=True,
            servers=[
                {
                    "name": "python-runner",
                    "command": "uv",
                    "args": "run mcp-run-python stdio",
                }
            ],
            timeout_seconds=60,
        )
        assert config.enabled is True
        assert len(config.servers) == 1
        assert config.servers[0]["name"] == "python-runner"
        assert config.servers[0]["command"] == "uv"
        assert config.timeout_seconds == 60

    def test_mcp_config_with_http_server(self):
        """Test MCP config with HTTP transport server."""
        config = MCPConfig(
            enabled=True,
            servers=[
                {
                    "name": "weather-api",
                    "url": "http://localhost:3001/mcp",
                }
            ],
        )
        assert config.enabled is True
        assert len(config.servers) == 1
        assert config.servers[0]["name"] == "weather-api"
        assert config.servers[0]["url"] == "http://localhost:3001/mcp"

    def test_mcp_config_with_multiple_servers(self):
        """Test MCP config with multiple servers of different types."""
        config = MCPConfig(
            enabled=True,
            servers=[
                {
                    "name": "python-runner",
                    "command": "uv",
                    "args": ["run", "mcp-run-python", "stdio"],
                },
                {
                    "name": "weather-api",
                    "url": "http://localhost:3001/mcp",
                },
                {
                    "name": "legacy-api",
                    "url": "http://localhost:3002/sse",
                },
            ],
        )
        assert config.enabled is True
        assert len(config.servers) == 3


class TestMCPClientInitialization:
    """Test MCP client initialization."""

    def test_mcp_client_disabled(self):
        """Test MCP client when disabled."""
        config = MCPConfig(enabled=False)
        client = MCPClient(config)

        assert client.config.enabled is False
        assert not client.is_started()
        assert client.get_server_count() == 0

    async def test_mcp_client_start_when_disabled(self):
        """Test starting MCP client when disabled does nothing."""
        config = MCPConfig(enabled=False)
        client = MCPClient(config)

        await client.start()

        assert not client.is_started()
        assert client.get_server_count() == 0

    def test_mcp_client_stats(self):
        """Test MCP client statistics."""
        config = MCPConfig(
            enabled=True,
            servers=[
                {
                    "name": "test-server",
                    "command": "test",
                    "args": "args",
                }
            ],
        )
        client = MCPClient(config)

        stats = client.get_stats()
        assert stats["enabled"] is True
        assert stats["started"] is False
        assert stats["server_count"] == 0
        assert stats["mcp_available"] == MCP_AVAILABLE

    def test_mcp_client_get_server_names(self):
        """Test getting server names."""
        config = MCPConfig(enabled=False)
        client = MCPClient(config)

        names = client.get_server_names()
        assert names == []


@pytest.mark.skipif(
    not MCP_AVAILABLE,
    reason="pydantic-ai MCP support not installed",
)
class TestMCPClientWithMCPSupport:
    """Test MCP client when pydantic-ai MCP support is available."""

    async def test_mcp_client_start_with_invalid_server(self):
        """Test MCP client handles invalid server configuration gracefully."""
        config = MCPConfig(
            enabled=True,
            servers=[
                {
                    "name": "invalid-server",
                    # Missing both command and url
                }
            ],
        )
        client = MCPClient(config)

        # Should raise ValueError for invalid config
        with pytest.raises(ValueError, match="must have either 'command' or 'url'"):
            await client.start()

    async def test_mcp_client_get_mcp_servers_before_start(self):
        """Test getting MCP servers before starting returns empty list."""
        config = MCPConfig(
            enabled=True,
            servers=[
                {
                    "name": "test-server",
                    "command": "echo",
                    "args": "test",
                }
            ],
        )
        client = MCPClient(config)

        servers = client.get_mcp_servers()
        assert servers == []

    async def test_mcp_client_discover_tools_not_started(self):
        """Test discovering tools when client not started."""
        config = MCPConfig(enabled=True)
        client = MCPClient(config)

        tools = await client.discover_tools()
        assert tools == []

    async def test_mcp_client_discover_resources_not_started(self):
        """Test discovering resources when client not started."""
        config = MCPConfig(enabled=True)
        client = MCPClient(config)

        resources = await client.discover_resources()
        assert resources == []

    async def test_mcp_client_stop_when_not_started(self):
        """Test stopping MCP client when not started."""
        config = MCPConfig(enabled=False)
        client = MCPClient(config)

        # Should not raise any errors
        await client.stop()
        assert not client.is_started()


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set - required for Agent initialization",
)
class TestAIAgentMCPIntegration:
    """Test AI agent integration with MCP."""

    async def test_ai_agent_with_mcp_disabled(self):
        """Test AI agent with MCP disabled."""
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            mcp=MCPConfig(enabled=False),
        )

        agent = AIAgent(config)
        agent.start()

        try:
            # MCP should not be initialized
            assert not agent.mcp_client.is_started()

            stats = await agent.get_stats()
            assert stats["mcp_stats"]["enabled"] is False
            assert stats["mcp_stats"]["started"] is False
        finally:
            await agent.stop()

    async def test_ai_agent_lazy_mcp_initialization(self):
        """Test that MCP is initialized lazily on first chat."""
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            mcp=MCPConfig(
                enabled=True,
                servers=[],  # No servers to avoid actual connection
            ),
        )

        agent = AIAgent(config)
        agent.start()

        try:
            # MCP should not be started yet
            assert not agent.mcp_client.is_started()

            # Mock the agent run to avoid actual API call
            with patch.object(agent._agent, "run", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = MagicMock(
                    output="Test response",
                    new_messages=lambda: [],
                    usage=lambda: None,
                )

                # First chat should trigger MCP initialization
                await agent.chat("user1", "Hello")

                # MCP should now be started (even with no servers)
                assert agent.mcp_client.is_started()
        finally:
            await agent.stop()

    async def test_ai_agent_mcp_initialization_failure_graceful(self):
        """Test that agent continues working even if MCP initialization fails."""
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            mcp=MCPConfig(
                enabled=True,
                servers=[
                    {
                        "name": "invalid",
                        # Invalid config to trigger error
                    }
                ],
            ),
        )

        agent = AIAgent(config)
        agent.start()

        try:
            # Mock the agent run to avoid actual API call
            with patch.object(agent._agent, "run", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = MagicMock(
                    output="Test response",
                    new_messages=lambda: [],
                    usage=lambda: None,
                )

                # Chat should work despite MCP failure
                response = await agent.chat("user1", "Hello")
                assert response == "Test response"

                # MCP should not be started due to error
                assert not agent.mcp_client.is_started()
        finally:
            await agent.stop()


class TestMCPTransportTypes:
    """Test different MCP transport types."""

    def test_stdio_transport_config(self):
        """Test stdio transport configuration."""
        config = MCPConfig(
            enabled=True,
            servers=[
                {
                    "name": "python-runner",
                    "command": "uv",
                    "args": "run mcp-run-python stdio",
                }
            ],
        )

        assert config.servers[0]["command"] == "uv"
        assert "args" in config.servers[0]

    def test_stdio_transport_with_list_args(self):
        """Test stdio transport with list arguments."""
        config = MCPConfig(
            enabled=True,
            servers=[
                {
                    "name": "filesystem",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                }
            ],
        )

        assert isinstance(config.servers[0]["args"], list)
        assert len(config.servers[0]["args"]) == 3

    def test_http_streamable_transport_config(self):
        """Test HTTP streamable transport configuration."""
        config = MCPConfig(
            enabled=True,
            servers=[
                {
                    "name": "weather-api",
                    "url": "http://localhost:3001/mcp",
                }
            ],
        )

        assert config.servers[0]["url"] == "http://localhost:3001/mcp"
        assert not config.servers[0]["url"].endswith("/sse")

    def test_sse_transport_config(self):
        """Test SSE transport configuration (deprecated)."""
        config = MCPConfig(
            enabled=True,
            servers=[
                {
                    "name": "legacy-api",
                    "url": "http://localhost:3002/sse",
                }
            ],
        )

        assert config.servers[0]["url"].endswith("/sse")


class TestMCPErrorHandling:
    """Test MCP error handling and edge cases."""

    async def test_mcp_client_double_start(self):
        """Test starting MCP client twice."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        if MCP_AVAILABLE:
            await client.start()
            assert client.is_started()

            # Second start should be a no-op
            await client.start()
            assert client.is_started()

            await client.stop()

    async def test_mcp_client_double_stop(self):
        """Test stopping MCP client twice."""
        config = MCPConfig(enabled=True, servers=[])
        client = MCPClient(config)

        if MCP_AVAILABLE:
            await client.start()
            await client.stop()
            assert not client.is_started()

            # Second stop should be a no-op
            await client.stop()
            assert not client.is_started()

    def test_mcp_config_validation(self):
        """Test MCP configuration validation."""
        # Valid configs
        config1 = MCPConfig(enabled=True, timeout_seconds=60)
        assert config1.timeout_seconds == 60

        # Timeout must be >= 1
        with pytest.raises(ValueError):  # Pydantic validation error
            MCPConfig(enabled=True, timeout_seconds=0)

    async def test_mcp_client_without_pydantic_ai_support(self):
        """Test MCP client behavior when pydantic-ai MCP support is not available."""
        config = MCPConfig(
            enabled=True,
            servers=[
                {
                    "name": "test-server",
                    "command": "test",
                    "args": "args",
                }
            ],
        )
        client = MCPClient(config)

        if not MCP_AVAILABLE:
            # Should raise RuntimeError when trying to start
            with pytest.raises(RuntimeError, match="pydantic-ai MCP support not available"):
                await client.start()


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set - required for Agent initialization",
)
class TestMCPWithBuiltInTools:
    """Test MCP integration with built-in tools."""

    async def test_mcp_with_web_search_enabled(self):
        """Test that MCP works alongside web search."""
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            tools_enabled=True,
            web_search_enabled=True,
            mcp=MCPConfig(enabled=True, servers=[]),
        )

        agent = AIAgent(config)
        agent.start()

        try:
            stats = await agent.get_stats()
            assert stats["tools_enabled"] is True
            assert stats["web_search_enabled"] is True
            assert stats["mcp_stats"]["enabled"] is True
        finally:
            await agent.stop()

    async def test_mcp_with_streaming_enabled(self):
        """Test that MCP works with streaming responses."""
        from feishu_webhook_bot.ai.config import StreamingConfig

        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            streaming=StreamingConfig(enabled=True, debounce_ms=100),
            mcp=MCPConfig(enabled=True, servers=[]),
        )

        agent = AIAgent(config)
        agent.start()

        try:
            stats = await agent.get_stats()
            assert stats["streaming_enabled"] is True
            assert stats["mcp_stats"]["enabled"] is True
        finally:
            await agent.stop()

    async def test_mcp_with_multi_agent_enabled(self):
        """Test that MCP works with multi-agent orchestration."""
        from feishu_webhook_bot.ai.config import MultiAgentConfig

        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            multi_agent=MultiAgentConfig(enabled=True, orchestration_mode="sequential"),
            mcp=MCPConfig(enabled=True, servers=[]),
        )

        agent = AIAgent(config)
        agent.start()

        try:
            stats = await agent.get_stats()
            assert stats["mcp_stats"]["enabled"] is True
            # Multi-agent stats should be available
            assert "orchestrator_stats" in stats
        finally:
            await agent.stop()


class TestMCPClientLifecycle:
    """Test MCP client lifecycle management."""

    async def test_mcp_client_full_lifecycle(self):
        """Test complete MCP client lifecycle."""
        config = MCPConfig(
            enabled=True,
            servers=[],
            timeout_seconds=30,
        )
        client = MCPClient(config)

        # Initial state
        assert not client.is_started()
        assert client.get_server_count() == 0

        if MCP_AVAILABLE:
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

    async def test_mcp_client_server_management(self):
        """Test MCP client server management."""
        config = MCPConfig(
            enabled=True,
            servers=[
                {
                    "name": "server1",
                    "command": "test1",
                    "args": "args1",
                },
                {
                    "name": "server2",
                    "url": "http://localhost:3001/mcp",
                },
            ],
        )
        client = MCPClient(config)

        # Before start
        assert client.get_server_names() == []

        if MCP_AVAILABLE:
            # After start (will fail to connect but should track servers)
            from contextlib import suppress

            with suppress(Exception):
                await client.start()

            # After stop
            await client.stop()
            assert client.get_server_names() == []
