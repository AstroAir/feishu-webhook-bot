# AI Tools Guide

Complete guide to AI tool calling and the tool registry in Feishu Webhook Bot.

## Table of Contents

- [Overview](#overview)
- [Built-in Tools](#built-in-tools)
- [Creating Custom Tools](#creating-custom-tools)
- [Tool Registry](#tool-registry)
- [Tool Execution](#tool-execution)
- [MCP Tools](#mcp-tools)
- [Best Practices](#best-practices)

## Overview

The AI tool system allows the AI agent to perform actions and retrieve information through function calling. Tools extend the AI's capabilities beyond text generation.

### How Tools Work

```text
User Message → AI Agent → Tool Selection → Tool Execution → Response
                  ↓              ↓
            Tool Registry   Tool Functions
```

### Tool Types

| Type | Description | Example |
|------|-------------|---------|
| Information | Retrieve data | Web search, database query |
| Action | Perform operations | Send message, create task |
| Computation | Calculate results | Math operations, data analysis |
| Integration | External services | API calls, file operations |

## Built-in Tools

### Web Search

```python
from feishu_webhook_bot.ai.tools import web_search

# Tool is automatically available to AI agent
# AI can call: web_search(query="latest Python news")
```

Configuration:

```yaml
ai:
  tools:
    web_search:
      enabled: true
      provider: "duckduckgo"  # or "google", "bing"
      max_results: 5
      cache_ttl: 3600
```

### Current Time

```python
# AI can get current time
# Tool: get_current_time(timezone="Asia/Shanghai")
```

### Calculator

```python
# AI can perform calculations
# Tool: calculate(expression="2 + 2 * 3")
```

### Send Message

```python
# AI can send messages
# Tool: send_message(text="Hello!", webhook="default")
```

### HTTP Request

```python
# AI can make HTTP requests
# Tool: http_request(url="https://api.example.com", method="GET")
```

## Creating Custom Tools

### Basic Tool Definition

```python
from feishu_webhook_bot.ai.tools import tool, ToolRegistry

@tool(
    name="get_weather",
    description="Get current weather for a location",
)
def get_weather(location: str) -> str:
    """Get weather information.
    
    Args:
        location: City name or coordinates
    
    Returns:
        Weather description
    """
    # Implementation
    weather_data = fetch_weather_api(location)
    return f"Weather in {location}: {weather_data['condition']}, {weather_data['temp']}°C"
```

### Async Tools

```python
@tool(
    name="search_database",
    description="Search the database for records",
)
async def search_database(query: str, limit: int = 10) -> list[dict]:
    """Search database records.
    
    Args:
        query: Search query
        limit: Maximum results to return
    
    Returns:
        List of matching records
    """
    results = await db.search(query, limit=limit)
    return results
```

### Tools with Complex Parameters

```python
from pydantic import BaseModel, Field
from typing import Optional

class SearchParams(BaseModel):
    query: str = Field(description="Search query")
    filters: Optional[dict] = Field(default=None, description="Filter criteria")
    sort_by: str = Field(default="relevance", description="Sort field")
    limit: int = Field(default=10, ge=1, le=100, description="Max results")

@tool(
    name="advanced_search",
    description="Perform advanced search with filters",
    parameters=SearchParams,
)
async def advanced_search(params: SearchParams) -> list[dict]:
    return await perform_search(params)
```

### Tool with Context

```python
@tool(
    name="get_user_info",
    description="Get information about the current user",
    requires_context=True,
)
async def get_user_info(context: ToolContext) -> dict:
    """Get user information from context."""
    user_id = context.user_id
    return await fetch_user_info(user_id)
```

## Tool Registry

### Registering Tools

```python
from feishu_webhook_bot.ai.tools import ToolRegistry

registry = ToolRegistry()

# Register single tool
registry.register(get_weather)

# Register multiple tools
registry.register_all([
    get_weather,
    search_database,
    send_notification,
])

# Register from module
from myapp import tools
registry.register_module(tools)
```

### Tool Categories

```python
# Organize tools by category
registry.register(get_weather, category="information")
registry.register(send_message, category="action")
registry.register(calculate, category="computation")

# Get tools by category
info_tools = registry.get_by_category("information")
```

### Enabling/Disabling Tools

```python
# Disable specific tool
registry.disable("dangerous_tool")

# Enable tool
registry.enable("safe_tool")

# Check if enabled
if registry.is_enabled("web_search"):
    # Tool is available
    pass
```

### Tool Configuration

```yaml
ai:
  tools:
    enabled: true
    
    # Global settings
    timeout: 30
    max_retries: 3
    
    # Per-tool settings
    web_search:
      enabled: true
      max_results: 10
    
    http_request:
      enabled: true
      allowed_domains:
        - "api.example.com"
        - "*.internal.com"
    
    send_message:
      enabled: true
      require_confirmation: false
```

## Tool Execution

### Execution Flow

```python
from feishu_webhook_bot.ai import AIAgent

agent = AIAgent(config)

# AI decides to use tools based on user message
response = await agent.chat(
    user_id="user123",
    message="What's the weather in Tokyo?"
)

# Behind the scenes:
# 1. AI analyzes message
# 2. AI selects get_weather tool
# 3. Tool executes with location="Tokyo"
# 4. AI formats response with tool result
```

### Manual Tool Execution

```python
# Execute tool directly
result = await registry.execute("get_weather", location="Tokyo")

# Execute with context
result = await registry.execute(
    "get_user_info",
    context=ToolContext(user_id="user123")
)
```

### Tool Chaining

```python
@tool(name="analyze_and_notify")
async def analyze_and_notify(data_source: str, threshold: float) -> str:
    """Analyze data and send notification if threshold exceeded."""
    
    # Chain multiple operations
    data = await registry.execute("fetch_data", source=data_source)
    analysis = await registry.execute("analyze", data=data)
    
    if analysis["value"] > threshold:
        await registry.execute(
            "send_message",
            text=f"Alert: Value {analysis['value']} exceeds threshold {threshold}"
        )
        return "Alert sent"
    
    return "No alert needed"
```

### Error Handling

```python
from feishu_webhook_bot.ai.tools import ToolError, ToolTimeoutError

@tool(name="risky_operation")
async def risky_operation(param: str) -> str:
    try:
        result = await external_api_call(param)
        return result
    except ConnectionError:
        raise ToolError("Failed to connect to external service")
    except TimeoutError:
        raise ToolTimeoutError("Operation timed out")
```

### Execution Hooks

```python
# Before tool execution
@registry.before_execute
async def log_tool_call(tool_name: str, params: dict):
    logger.info(f"Executing tool: {tool_name} with {params}")

# After tool execution
@registry.after_execute
async def log_tool_result(tool_name: str, result: any, duration: float):
    logger.info(f"Tool {tool_name} completed in {duration}s")

# On error
@registry.on_error
async def handle_tool_error(tool_name: str, error: Exception):
    logger.error(f"Tool {tool_name} failed: {error}")
    await notify_admin(f"Tool error: {tool_name}")
```

## MCP Tools

### MCP Integration

MCP (Model Context Protocol) provides standardized tool access:

```yaml
ai:
  mcp:
    enabled: true
    servers:
      - name: "filesystem"
        command: "npx"
        args: ["-y", "@anthropic/mcp-server-filesystem", "/data"]
      
      - name: "database"
        command: "python"
        args: ["-m", "mcp_server_sqlite", "--db", "data.db"]
```

### Using MCP Tools

```python
from feishu_webhook_bot.ai import MCPClient

mcp = MCPClient(config)

# List available tools from MCP server
tools = await mcp.list_tools("filesystem")

# Execute MCP tool
result = await mcp.call_tool(
    server="filesystem",
    tool="read_file",
    arguments={"path": "/data/config.json"}
)
```

### Custom MCP Server

```python
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("my-tools")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="my_tool",
            description="My custom tool",
            inputSchema={
                "type": "object",
                "properties": {
                    "param": {"type": "string"}
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "my_tool":
        result = process(arguments["param"])
        return [TextContent(type="text", text=result)]
```

## Best Practices

### Tool Design

1. **Single Responsibility** - Each tool does one thing well
2. **Clear Descriptions** - Help AI understand when to use the tool
3. **Typed Parameters** - Use type hints and Pydantic models
4. **Error Handling** - Return meaningful errors

```python
# ✅ Good tool design
@tool(
    name="get_stock_price",
    description="Get the current stock price for a given ticker symbol. Use this when the user asks about stock prices or market data.",
)
async def get_stock_price(ticker: str) -> dict:
    """Get stock price.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'GOOGL')
    
    Returns:
        Dictionary with price, change, and volume
    """
    if not ticker.isalpha():
        raise ToolError(f"Invalid ticker symbol: {ticker}")
    
    data = await fetch_stock_data(ticker.upper())
    return {
        "ticker": ticker.upper(),
        "price": data["price"],
        "change": data["change"],
        "volume": data["volume"],
    }
```

### Security

```python
# Validate inputs
@tool(name="execute_query")
async def execute_query(query: str) -> list:
    # Sanitize input
    if any(keyword in query.lower() for keyword in ["drop", "delete", "truncate"]):
        raise ToolError("Dangerous query detected")
    
    # Use parameterized queries
    return await db.fetch(query)

# Limit scope
@tool(name="read_file")
async def read_file(path: str) -> str:
    # Restrict to allowed directories
    allowed_dirs = ["/data", "/public"]
    if not any(path.startswith(d) for d in allowed_dirs):
        raise ToolError("Access denied")
    
    return await read_file_content(path)
```

### Performance

```python
from functools import lru_cache
import asyncio

# Cache expensive operations
@tool(name="get_exchange_rate")
@lru_cache(maxsize=100)
async def get_exchange_rate(from_currency: str, to_currency: str) -> float:
    return await fetch_rate(from_currency, to_currency)

# Set timeouts
@tool(name="slow_operation", timeout=10)
async def slow_operation(param: str) -> str:
    return await long_running_task(param)

# Batch operations
@tool(name="batch_lookup")
async def batch_lookup(ids: list[str]) -> list[dict]:
    # Process in parallel
    tasks = [lookup_single(id) for id in ids]
    return await asyncio.gather(*tasks)
```

### Testing

```python
import pytest
from feishu_webhook_bot.ai.tools import ToolRegistry

@pytest.fixture
def registry():
    reg = ToolRegistry()
    reg.register(get_weather)
    return reg

@pytest.mark.asyncio
async def test_get_weather(registry):
    result = await registry.execute("get_weather", location="Tokyo")
    assert "Tokyo" in result
    assert "°C" in result

@pytest.mark.asyncio
async def test_invalid_location(registry):
    with pytest.raises(ToolError):
        await registry.execute("get_weather", location="")
```

## See Also

- [AI Multi-Provider Guide](multi-provider.md) - AI configuration
- [MCP Integration](mcp-integration.md) - MCP details
- [Examples](../resources/examples.md) - Tool examples
