# MCP (Model Context Protocol) Integration Guide

This guide explains how to use Model Context Protocol (MCP) with the Feishu Webhook Bot framework.

## Table of Contents

- [What is MCP?](#what-is-mcp)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Transport Types](#transport-types)
- [Configuration](#configuration)
- [Examples](#examples)
- [Available MCP Servers](#available-mcp-servers)
- [Troubleshooting](#troubleshooting)

## What is MCP?

[Model Context Protocol (MCP)](https://modelcontextprotocol.io/) is an open protocol that standardizes how applications provide context to Large Language Models (LLMs). It enables:

- **Standardized Tool Access**: Expose tools and functions to AI models in a consistent way
- **Resource Management**: Provide structured access to data sources and APIs
- **Server Ecosystem**: Use pre-built MCP servers for common tasks
- **Extensibility**: Build custom MCP servers for your specific needs

The Feishu Webhook Bot framework integrates MCP using [pydantic-ai's MCP support](https://ai.pydantic.dev/mcp/), which automatically registers MCP servers as toolsets with AI agents.

## Installation

Install pydantic-ai with MCP support:

```bash
pip install 'pydantic-ai-slim[mcp]'
```

Or using uv:

```bash
uv add 'pydantic-ai-slim[mcp]'
```

## Quick Start

Here's a minimal example using an MCP server:

```python
from feishu_webhook_bot.ai import AIAgent, AIConfig, MCPConfig

# Configure MCP with a Python code execution server
config = AIConfig(
    enabled=True,
    model="openai:gpt-4o",
    mcp=MCPConfig(
        enabled=True,
        servers=[
            {
                "name": "python-runner",
                "command": "uv",
                "args": "run mcp-run-python stdio",
            }
        ],
    ),
)

# Create and start agent
agent = AIAgent(config)
agent.start()

# The AI can now execute Python code via MCP
response = await agent.chat(
    user_id="user1",
    message="Calculate the factorial of 10 using Python"
)
print(response)

await agent.stop()
```

## Transport Types

MCP supports three transport types. The framework automatically detects the type based on configuration:

### 1. stdio (Recommended)

Runs the MCP server as a subprocess and communicates via standard input/output.

**Configuration:**
```python
{
    "name": "server-name",
    "command": "command-to-run",
    "args": "arguments"  # Can be string or list
}
```

**Examples:**
```python
# String args
{
    "name": "python-runner",
    "command": "uv",
    "args": "run mcp-run-python stdio"
}

# List args
{
    "name": "filesystem",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
}
```

### 2. Streamable HTTP

Modern HTTP-based transport using streaming.

**Configuration:**
```python
{
    "name": "server-name",
    "url": "http://localhost:3001/mcp"
}
```

### 3. SSE (Deprecated)

HTTP Server-Sent Events transport. Still supported but deprecated.

**Configuration:**
```python
{
    "name": "server-name",
    "url": "http://localhost:3001/sse"  # Must end with /sse
}
```

## Configuration

### Basic Configuration

```yaml
ai:
  enabled: true
  model: "openai:gpt-4o"
  mcp:
    enabled: true
    timeout_seconds: 30
    servers:
      - name: "python-runner"
        command: "uv"
        args: "run mcp-run-python stdio"
```

### Multiple Servers

```yaml
ai:
  mcp:
    enabled: true
    servers:
      # stdio transport
      - name: "python-runner"
        command: "uv"
        args: "run mcp-run-python stdio"
      
      # stdio with list args
      - name: "filesystem"
        command: "npx"
        args:
          - "-y"
          - "@modelcontextprotocol/server-filesystem"
          - "/tmp"
      
      # HTTP transport
      - name: "weather-api"
        url: "http://localhost:3001/mcp"
```

### Python Configuration

```python
from feishu_webhook_bot.ai import MCPConfig

mcp_config = MCPConfig(
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
        }
    ],
    timeout_seconds=30,
)
```

## Examples

### Example 1: Python Code Execution

```python
from feishu_webhook_bot.ai import AIAgent, AIConfig, MCPConfig

config = AIConfig(
    enabled=True,
    model="openai:gpt-4o",
    mcp=MCPConfig(
        enabled=True,
        servers=[
            {
                "name": "python-runner",
                "command": "uv",
                "args": "run mcp-run-python stdio",
            }
        ],
    ),
)

agent = AIAgent(config)
agent.start()

# Ask AI to solve problems using Python
response = await agent.chat(
    user_id="user1",
    message="Calculate the first 10 Fibonacci numbers using Python"
)
print(response)

await agent.stop()
```

### Example 2: File System Access

```python
config = AIConfig(
    enabled=True,
    model="openai:gpt-4o",
    mcp=MCPConfig(
        enabled=True,
        servers=[
            {
                "name": "filesystem",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            }
        ],
    ),
)

agent = AIAgent(config)
agent.start()

# AI can now read/write files in /tmp
response = await agent.chat(
    user_id="user1",
    message="List all .txt files in the directory and show their contents"
)
print(response)

await agent.stop()
```

### Example 3: Combining MCP with Built-in Tools

```python
config = AIConfig(
    enabled=True,
    model="openai:gpt-4o",
    tools_enabled=True,
    web_search_enabled=True,
    mcp=MCPConfig(
        enabled=True,
        servers=[
            {
                "name": "python-runner",
                "command": "uv",
                "args": "run mcp-run-python stdio",
            }
        ],
    ),
)

agent = AIAgent(config)
agent.start()

# AI can use both MCP tools and built-in tools
response = await agent.chat(
    user_id="user1",
    message="Search for the current Bitcoin price, then calculate its value in EUR using Python"
)
print(response)

await agent.stop()
```

### Example 4: Feishu Bot with MCP

```python
from feishu_webhook_bot import FeishuBot, BotConfig
from feishu_webhook_bot.ai import AIConfig, MCPConfig

# Configure MCP
mcp_config = MCPConfig(
    enabled=True,
    servers=[
        {
            "name": "python-runner",
            "command": "uv",
            "args": "run mcp-run-python stdio",
        }
    ],
)

# Configure AI with MCP
ai_config = AIConfig(
    enabled=True,
    model="openai:gpt-4o",
    tools_enabled=True,
    web_search_enabled=True,
    mcp=mcp_config,
    system_prompt="You are a helpful assistant in a Feishu workspace. "
                 "You can execute Python code and search the web.",
)

# Configure bot
bot_config = BotConfig(
    app_id="your-app-id",
    app_secret="your-app-secret",
    verification_token="your-verification-token",
    encrypt_key="your-encrypt-key",
    ai_config=ai_config,
)

# Create and start bot
bot = FeishuBot(bot_config)
bot.start()
```

## Available MCP Servers

Here are some popular MCP servers you can use:

### Official MCP Servers

1. **@modelcontextprotocol/server-filesystem**
   - File system operations
   - Install: `npx -y @modelcontextprotocol/server-filesystem <directory>`

2. **@modelcontextprotocol/server-github**
   - GitHub API access
   - Install: `npx -y @modelcontextprotocol/server-github`

3. **@modelcontextprotocol/server-postgres**
   - PostgreSQL database access
   - Install: `npx -y @modelcontextprotocol/server-postgres`

### Community MCP Servers

1. **mcp-run-python**
   - Safe Python code execution
   - Install: `uv tool install mcp-run-python`

2. **mcp-server-sqlite**
   - SQLite database access
   - Install: `npx -y @modelcontextprotocol/server-sqlite`

For a complete list, visit: https://github.com/modelcontextprotocol/servers

## Troubleshooting

### MCP Server Not Found

**Error:** `Failed to connect to MCP server: command not found`

**Solution:** Make sure the MCP server is installed:
```bash
# For Python-based servers
uv tool install mcp-run-python

# For Node.js-based servers
npm install -g @modelcontextprotocol/server-filesystem
```

### Connection Timeout

**Error:** `MCP server connection timeout`

**Solution:** Increase the timeout in configuration:
```python
mcp=MCPConfig(
    enabled=True,
    timeout_seconds=60,  # Increase from default 30
    servers=[...]
)
```

### Import Error

**Error:** `ImportError: cannot import name 'MCPServerStdio'`

**Solution:** Install pydantic-ai with MCP support:
```bash
pip install 'pydantic-ai-slim[mcp]'
```

### Agent Works Without MCP

If MCP initialization fails, the agent will continue to work with built-in tools only. Check logs for MCP errors:

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Testing MCP Configuration

Test your MCP configuration without the full bot:

```python
from feishu_webhook_bot.ai.mcp_client import MCPClient, MCPConfig

config = MCPConfig(
    enabled=True,
    servers=[
        {
            "name": "test-server",
            "command": "uv",
            "args": "run mcp-run-python stdio",
        }
    ],
)

client = MCPClient(config)
await client.start()

# Check stats
print(client.get_stats())

await client.stop()
```

## Advanced Features

### MCP Sampling

MCP servers can make LLM calls via the client (sampling). This is automatically supported when using pydantic-ai's MCP integration.

### MCP Elicitation

MCP servers can request structured input from the client. This is also automatically supported.

### Custom Tool Prefixes

To avoid naming conflicts between multiple MCP servers, pydantic-ai automatically prefixes tool names with the server name.

## Best Practices

1. **Use stdio transport** for local MCP servers (most reliable)
2. **Set appropriate timeouts** based on server response times
3. **Test MCP servers independently** before integrating with the bot
4. **Monitor MCP stats** using `agent.get_stats()['mcp_stats']`
5. **Handle failures gracefully** - the agent continues working even if MCP fails
6. **Use specific directories** for filesystem servers to limit access
7. **Keep MCP servers updated** for security and bug fixes

## Further Reading

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Pydantic-AI MCP Documentation](https://ai.pydantic.dev/mcp/)
- [Official MCP Servers](https://github.com/modelcontextprotocol/servers)
- See `examples/mcp_integration_example.py` in the repository for a complete example

