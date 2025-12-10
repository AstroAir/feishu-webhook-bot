"""Example demonstrating MCP tool discovery and execution capabilities.

This example shows how to:
1. Discover tools available from MCP servers
2. Get detailed information about specific tools
3. Call tools programmatically
4. Handle errors gracefully
"""

import asyncio
from feishu_webhook_bot.ai.config import MCPConfig
from feishu_webhook_bot.ai.mcp_client import MCPClient


async def example_discover_tools():
    """Discover all tools from configured MCP servers."""
    config = MCPConfig(
        enabled=True,
        servers=[
            {
                "name": "python-runner",
                "command": "uv",
                "args": ["run", "mcp-run-python", "stdio"],
            },
            {
                "name": "filesystem",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            },
        ],
    )

    client = MCPClient(config)

    try:
        # Start the MCP client
        await client.start()

        # Discover all tools
        tools = await client.discover_tools()

        print(f"Discovered {len(tools)} tools from all MCP servers:\n")

        for tool in tools:
            print(f"Server: {tool['server']}")
            print(f"  Tool: {tool['name']}")
            print(f"  Description: {tool['description']}")
            if tool.get("parameters"):
                print(f"  Parameters: {tool['parameters']}")
            print()

    finally:
        await client.stop()


async def example_get_tool_info():
    """Get detailed information about specific tools."""
    config = MCPConfig(
        enabled=True,
        servers=[
            {
                "name": "python-runner",
                "command": "uv",
                "args": ["run", "mcp-run-python", "stdio"],
            }
        ],
    )

    client = MCPClient(config)

    try:
        await client.start()

        # Discover tools first to populate cache
        await client.discover_tools()

        # Get info for a specific tool
        tool_info = client.get_tool_info("python-runner", "execute_python")

        if tool_info:
            print(f"Tool Information for: {tool_info['name']}")
            print(f"Server: {tool_info['server']}")
            print(f"Description: {tool_info['description']}")
            print(f"Parameters: {tool_info.get('parameters', {})}")
        else:
            print("Tool not found")

    finally:
        await client.stop()


async def example_call_tool():
    """Call a tool on an MCP server."""
    config = MCPConfig(
        enabled=True,
        servers=[
            {
                "name": "python-runner",
                "command": "uv",
                "args": ["run", "mcp-run-python", "stdio"],
            }
        ],
    )

    client = MCPClient(config)

    try:
        await client.start()

        # Call a tool with specific arguments
        result = await client.call_tool(
            server_name="python-runner",
            tool_name="execute_python",
            arguments={"code": "print('Hello from MCP!')"},
        )

        if result["success"]:
            print(f"Tool execution succeeded!")
            print(f"Result: {result['result']}")
        else:
            print(f"Tool execution failed!")
            print(f"Error: {result['error']}")

    finally:
        await client.stop()


async def example_error_handling():
    """Demonstrate error handling in tool operations."""
    config = MCPConfig(
        enabled=True,
        servers=[
            {
                "name": "test-server",
                "command": "echo",
                "args": ["test"],
            }
        ],
    )

    client = MCPClient(config)

    try:
        await client.start()

        # Try to get info for non-existent server
        info = client.get_tool_info("non-existent-server", "some-tool")
        if info is None:
            print("Server not found - handled gracefully")

        # Try to call tool on non-existent server
        result = await client.call_tool(
            "non-existent-server",
            "some-tool",
            {"arg": "value"},
        )

        if not result["success"]:
            print(f"Call failed as expected: {result['error']}")

    finally:
        await client.stop()


async def example_list_all_tools():
    """List all available tools grouped by server."""
    config = MCPConfig(
        enabled=True,
        servers=[
            {
                "name": "python-runner",
                "command": "uv",
                "args": ["run", "mcp-run-python", "stdio"],
            },
        ],
    )

    client = MCPClient(config)

    try:
        await client.start()

        # Get server names
        server_names = client.get_server_names()
        print(f"Connected to {len(server_names)} servers:\n")

        # Discover and organize tools by server
        tools = await client.discover_tools()
        tools_by_server = {}

        for tool in tools:
            server = tool["server"]
            if server not in tools_by_server:
                tools_by_server[server] = []
            tools_by_server[server].append(tool)

        # Display organized results
        for server, server_tools in tools_by_server.items():
            print(f"Server: {server}")
            print(f"  Tools ({len(server_tools)}):")
            for tool in server_tools:
                print(f"    - {tool['name']}: {tool['description']}")
            print()

    finally:
        await client.stop()


async def main():
    """Run all examples."""
    print("=" * 60)
    print("MCP Tool Discovery Examples")
    print("=" * 60)
    print()

    # Note: These examples require actual MCP servers to be running
    # or will show how to handle the errors gracefully

    print("1. Error Handling Example (Safe to run without MCP servers)")
    print("-" * 60)
    try:
        await example_error_handling()
    except Exception as e:
        print(f"Example failed: {e}")

    print()
    print("2. Discovery Example (Requires MCP servers)")
    print("-" * 60)
    print("This example requires MCP servers to be running.")
    print("Install: pip install 'pydantic-ai-slim[mcp]'")
    print("Example skipped for demo purposes")
    print()

    print("=" * 60)
    print("Examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
