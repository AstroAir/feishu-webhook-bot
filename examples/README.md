# Examples

This directory contains comprehensive examples demonstrating the Feishu Webhook Bot's capabilities, organized by category for easy navigation.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start Examples](#quick-start-examples)
- [Core Module Examples](#core-module-examples)
- [Provider Examples](#provider-examples)
- [AI Module Examples](#ai-module-examples)
- [Plugin System Examples](#plugin-system-examples)
- [Client Examples](#client-examples)
- [Authentication Examples](#authentication-examples)
- [MCP Integration Examples](#mcp-integration-examples)
- [Scheduler Examples](#scheduler-examples)
- [Automation Examples](#automation-examples)
- [Running the Examples](#running-the-examples)
- [Troubleshooting](#troubleshooting)

## Directory Structure

```text
examples/
├── quickstart/           # 快速入门示例
│   ├── quickstart.py
│   ├── basic_bot_example.py
│   └── simple_message_example.py
├── core/                 # 核心模块示例
│   ├── circuit_breaker_example.py
│   ├── message_queue_example.py
│   ├── message_tracker_example.py
│   ├── message_tracker_usage.py
│   ├── config_watcher_example.py
│   ├── config_validation_example.py
│   ├── image_uploader_example.py
│   ├── logging_example.py
│   └── event_server_demo.py
├── providers/            # 消息提供者示例
│   ├── feishu_provider_example.py
│   ├── qq_napcat_provider_example.py
│   ├── multi_provider_example.py
│   └── multi_provider_ai_example.py
├── ai/                   # AI模块示例
│   ├── conversation_manager_example.py
│   ├── multi_agent_example.py
│   ├── tool_registry_example.py
│   ├── ai_retry_example.py
│   ├── ai_agent_advanced_example.py
│   ├── ai_bot_example.py
│   ├── ai_capabilities_demo.py
│   ├── ai_features_demo.py
│   ├── ai_powered_tasks_example.py
│   ├── ai_bot_config.yaml
│   └── ai_tasks_config.yaml
├── plugins/              # 插件系统示例
│   ├── plugin_config_schema_example.py
│   ├── plugin_dependency_example.py
│   ├── plugin_manifest_example.py
│   ├── plugin_demo.py
│   ├── plugin_setup_wizard_example.py
│   ├── use_calendar_plugin.py
│   └── feishu_calendar_config.yaml
├── client/               # 客户端示例
│   ├── card_builder_example.py
│   └── rich_text_example.py
├── auth/                 # 认证系统示例
│   ├── auth_demo.py
│   ├── auth_api_demo.py
│   ├── auth_advanced_demo.py
│   └── auth_example.py
├── mcp/                  # MCP集成示例
│   ├── complete_mcp_bot_example.py
│   ├── mcp_integration_example.py
│   ├── mcp_tool_discovery_example.py
│   └── mcp_transport_examples.py
├── scheduler/            # 调度器示例
│   ├── scheduler_demo.py
│   └── task_manager_demo.py
└── automation/           # 自动化引擎示例
    └── automation_demo.py
```

## Prerequisites

### Required Environment Variables

All AI-enabled examples require:

```bash
export OPENAI_API_KEY='your-openai-api-key-here'
```

For Feishu bot examples, you also need:

```bash
export FEISHU_APP_ID='your-app-id'
export FEISHU_APP_SECRET='your-app-secret'
export FEISHU_VERIFICATION_TOKEN='your-verification-token'
export FEISHU_ENCRYPT_KEY='your-encrypt-key'  # Optional
```

### Required Dependencies

Install all dependencies:

```bash
# Basic dependencies
pip install feishu-webhook-bot

# For MCP support
pip install 'pydantic-ai-slim[mcp]'

# For web search
pip install duckduckgo-search
```

Or using uv:

```bash
uv add pydantic-ai duckduckgo-search
```

### MCP Servers

For MCP examples, you'll need MCP servers installed:

```bash
# Python code execution
uv tool install mcp-run-python

# Filesystem access
npm install -g @modelcontextprotocol/server-filesystem

# Or use npx (no installation needed)
npx -y @modelcontextprotocol/server-filesystem /tmp
```

## Quick Start Examples

### Basic Bot Example

**File:** `quickstart/basic_bot_example.py`

Complete introduction to creating a Feishu bot.

```bash
python examples/quickstart/basic_bot_example.py
```

**What it demonstrates:**

- Creating a bot from code and YAML configuration
- Sending different message types
- Using the scheduler
- Plugin integration basics
- Event handling

### Simple Message Example

**File:** `quickstart/simple_message_example.py`

The fastest way to send messages to Feishu.

```bash
python examples/quickstart/simple_message_example.py
```

**What it demonstrates:**

- Simplest possible setup
- Text, rich text, and card messages
- Common use cases and templates
- Error handling patterns
- Environment variable configuration

## Core Module Examples

### Circuit Breaker Example

**File:** `core/circuit_breaker_example.py`

Demonstrates fault tolerance with the circuit breaker pattern.

```bash
python examples/core/circuit_breaker_example.py
```

**What it demonstrates:**

- Basic circuit breaker usage
- State transitions (CLOSED → OPEN → HALF_OPEN)
- Decorator-based usage
- Registry management
- Excluded exceptions
- Real-world patterns

### Message Queue Example

**File:** `core/message_queue_example.py`

Demonstrates reliable message delivery with queuing.

```bash
python examples/core/message_queue_example.py
```

**What it demonstrates:**

- Basic queue operations
- Batch processing
- Retry mechanisms with exponential backoff
- Statistics and monitoring
- Multi-provider queue integration

### Message Tracker Example

**File:** `core/message_tracker_example.py`

Demonstrates message delivery tracking.

```bash
python examples/core/message_tracker_example.py
```

**What it demonstrates:**

- Basic message tracking
- Status transitions
- Duplicate detection
- SQLite persistence
- Automatic cleanup
- Statistics and monitoring

### Config Watcher Example

**File:** `core/config_watcher_example.py`

Demonstrates configuration hot-reload.

```bash
python examples/core/config_watcher_example.py
```

**What it demonstrates:**

- Watching configuration files
- Automatic reload on modification
- Validation before reload
- Debouncing rapid changes
- Error recovery

### Config Validation Example

**File:** `core/config_validation_example.py`

Demonstrates configuration validation utilities.

```bash
python examples/core/config_validation_example.py
```

**What it demonstrates:**

- JSON schema generation
- YAML configuration validation
- Custom validation functions
- Schema for IDE support

### Image Uploader Example

**File:** `core/image_uploader_example.py`

Demonstrates Feishu image upload functionality.

```bash
python examples/core/image_uploader_example.py
```

**What it demonstrates:**

- Permission checking
- Image upload workflow
- Creating image cards
- Base64 image handling
- Error handling

### Logging Example

**File:** `core/logging_example.py`

Demonstrates the logging system.

```bash
python examples/core/logging_example.py
```

**What it demonstrates:**

- Different log levels
- Named loggers
- Custom log formats
- File logging
- Performance logging
- Structured logging patterns

## Provider Examples

### Feishu Provider Example

**File:** `providers/feishu_provider_example.py`

Demonstrates the Feishu messaging provider.

```bash
python examples/providers/feishu_provider_example.py
```

**What it demonstrates:**

- Provider configuration
- Sending text, rich text, and card messages
- HMAC-SHA256 signed webhooks
- Circuit breaker integration
- Message tracking

### QQ Napcat Provider Example

**File:** `providers/qq_napcat_provider_example.py`

Demonstrates the QQ Napcat provider (OneBot11 protocol).

```bash
python examples/providers/qq_napcat_provider_example.py
```

**What it demonstrates:**

- Provider configuration
- Private and group messages
- CQ code format
- Target format (private:QQ号, group:群号)
- Circuit breaker integration

### Multi-Provider Example

**File:** `providers/multi_provider_example.py`

Demonstrates multi-provider orchestration.

```bash
python examples/providers/multi_provider_example.py
```

**What it demonstrates:**

- Provider registry
- Multi-platform messaging
- Provider-specific formatting
- Failover strategies
- Load balancing
- Unified message interface

## AI Module Examples

### Conversation Manager Example

**File:** `ai/conversation_manager_example.py`

Demonstrates conversation management for AI.

```bash
python examples/ai/conversation_manager_example.py
```

**What it demonstrates:**

- Conversation state management
- Multi-turn dialogue
- Token tracking
- Conversation cleanup
- Export/import conversations

### Multi-Agent Example

**File:** `ai/multi_agent_example.py`

Demonstrates multi-agent orchestration (A2A).

```bash
python examples/ai/multi_agent_example.py
```

**What it demonstrates:**

- Specialized agents
- Sequential, concurrent, hierarchical orchestration
- Agent-to-agent communication
- Error handling in multi-agent systems

### Tool Registry Example

**File:** `ai/tool_registry_example.py`

Demonstrates the tool registry for AI agents.

```bash
python examples/ai/tool_registry_example.py
```

**What it demonstrates:**

- Registering custom tools
- Tool with parameters
- Async tool support
- Tool categories
- Tool validation
- Built-in web search tool

### AI Retry Example

**File:** `ai/ai_retry_example.py`

Demonstrates retry mechanisms for AI operations.

```bash
python examples/ai/ai_retry_example.py
```

**What it demonstrates:**

- Exponential backoff
- Circuit breaker for AI
- Rate limit handling
- Timeout management
- Error classification
- Retry policies

## Plugin System Examples

### Plugin Config Schema Example

**File:** `plugins/plugin_config_schema_example.py`

Demonstrates plugin configuration schemas.

```bash
python examples/plugins/plugin_config_schema_example.py
```

**What it demonstrates:**

- Configuration field types
- Field validation
- Environment variable fallbacks
- Sensitive field handling
- Schema documentation generation

### Plugin Dependency Example

**File:** `plugins/plugin_dependency_example.py`

Demonstrates plugin dependency checking.

```bash
python examples/plugins/plugin_dependency_example.py
```

**What it demonstrates:**

- Dependency declaration
- Version compatibility checking
- Dependency resolution order
- Missing dependency handling
- Optional dependencies with fallback

### Plugin Manifest Example

**File:** `plugins/plugin_manifest_example.py`

Demonstrates plugin manifests.

```bash
python examples/plugins/plugin_manifest_example.py
```

**What it demonstrates:**

- Plugin metadata
- Dependencies declaration
- Permissions and capabilities
- Manifest validation
- Version compatibility

## Client Examples

### Card Builder Example

**File:** `client/card_builder_example.py`

Demonstrates the CardBuilder for interactive cards.

```bash
python examples/client/card_builder_example.py
```

**What it demonstrates:**

- Building cards with fluent API
- Header styles and templates
- Text, image, and button elements
- Multi-column layouts
- Alert and report card templates

### Rich Text Example

**File:** `client/rich_text_example.py`

Demonstrates rich text (post) message formatting.

```bash
python examples/client/rich_text_example.py
```

**What it demonstrates:**

- Rich text structure
- Text styling (bold, italic, underline)
- Links and mentions
- Images in rich text
- Multi-language support
- Common templates

## Scheduler Examples

### Scheduler Demo

**File:** `scheduler/scheduler_demo.py`

Comprehensive demonstration of the task scheduler.

```bash
python examples/scheduler/scheduler_demo.py
```

**What it demonstrates:**

- Scheduling tasks with cron expressions
- Interval-based scheduling
- Job management (add, remove, pause, resume)
- Persistent vs in-memory job stores
- Timezone-aware scheduling
- Job decorators (@job)
- Error handling and retry logic

### Task Manager Demo

**File:** `scheduler/task_manager_demo.py`

Demonstrates the task manager for automated task execution.

```bash
python examples/scheduler/task_manager_demo.py
```

**What it demonstrates:**

- Automated task execution
- Task dependencies and retry logic
- Task conditions (time, day, environment)
- Integration with plugins
- Cron-based scheduling
- Multiple actions per task

## Automation Examples

### Automation Demo

**File:** `automation/automation_demo.py`

Comprehensive demonstration of the automation engine.

```bash
python examples/automation/automation_demo.py
```

**What it demonstrates:**

- Declarative workflow definitions
- Schedule-based triggers
- Action types (send messages, HTTP requests, Python code, plugin calls)
- Template rendering with variable substitution
- Conditional execution

---

## Additional Examples

The following are additional examples organized by category:

### Plugin System Demo

**File:** `plugins/plugin_demo.py`

Comprehensive demonstration of the plugin system.

```bash
python examples/plugins/plugin_demo.py
```

**What it demonstrates:**

- Creating custom plugins
- Plugin lifecycle (load, enable, disable, unload)
- Registering scheduled jobs from plugins
- Accessing bot resources (client, config, scheduler)
- Plugin configuration and settings
- Event handling in plugins
- Hot-reload functionality
- Plugin loading priority

### Plugin Setup Wizard

**File:** `plugins/plugin_setup_wizard_example.py`

Interactive plugin setup wizard.

```bash
python examples/plugins/plugin_setup_wizard_example.py
```

### Calendar Plugin Example

**File:** `plugins/use_calendar_plugin.py`

Demonstrates using the Feishu calendar plugin.

```bash
python examples/plugins/use_calendar_plugin.py
```

### Event Server Demo

**File:** `core/event_server_demo.py`

Demonstrates the event server for receiving webhooks.

```bash
python examples/core/event_server_demo.py
```

**What it demonstrates:**

- Receiving Feishu webhook events
- Token verification
- Signature validation
- URL verification challenge
- Event dispatching to plugins
- Health check endpoint

### AI Advanced Examples

**File:** `ai/ai_agent_advanced_example.py`

Advanced AI agent examples.

```bash
python examples/ai/ai_agent_advanced_example.py
```

### AI Bot Example

**File:** `ai/ai_bot_example.py`

Complete AI-powered bot example.

```bash
python examples/ai/ai_bot_example.py
```

### AI Capabilities Demo

**File:** `ai/ai_capabilities_demo.py`

Demonstrates advanced AI capabilities.

```bash
python examples/ai/ai_capabilities_demo.py
```

**What it demonstrates:**

- Structured output validation
- Streaming responses with debouncing
- Result validators and retry logic
- Custom model settings
- Multi-agent orchestration

### AI Features Demo

**File:** `ai/ai_features_demo.py`

Demonstrates all AI features.

```bash
python examples/ai/ai_features_demo.py
```

**What it demonstrates:**

- Web search with caching
- Conversation management with token tracking
- Tool registry and custom tools
- Circuit breaker for rate limiting
- Conversation export/import

### AI Powered Tasks

**File:** `ai/ai_powered_tasks_example.py`

Demonstrates AI-powered automated tasks.

```bash
python examples/ai/ai_powered_tasks_example.py
```

### Multi-Provider AI Example

**File:** `providers/multi_provider_ai_example.py`

Demonstrates AI with multiple providers.

```bash
python examples/providers/multi_provider_ai_example.py
```

---

## Authentication Examples

### Auth Demo

**File:** `auth/auth_demo.py`

Comprehensive demonstration of authentication features.

```bash
python examples/auth/auth_demo.py
```

**What it demonstrates:**

- Password validation and strength checking
- Password hashing with bcrypt
- JWT token generation and validation
- User registration with validation
- User authentication and login
- Account lockout after failed attempts

### Auth API Demo

**File:** `auth/auth_api_demo.py`

Demonstrates authentication integration with FastAPI.

```bash
python examples/auth/auth_api_demo.py
```

**What it demonstrates:**

- Setting up authentication routes
- Using authentication middleware
- Protected endpoints with JWT tokens
- Token-based API access

### Auth Advanced Demo

**File:** `auth/auth_advanced_demo.py`

Demonstrates advanced authentication scenarios.

```bash
python examples/auth/auth_advanced_demo.py
```

**What it demonstrates:**

- Token refresh workflow
- Multiple concurrent sessions
- Token expiration handling
- Comprehensive error handling

### Auth Example (NiceGUI)

**File:** `auth/auth_example.py`

Demonstrates authentication with NiceGUI web interface.

```bash
python examples/auth/auth_example.py
```

---

## MCP Integration Examples

### Complete MCP Bot Example

**File:** `mcp/complete_mcp_bot_example.py`

End-to-end example of a Feishu bot with full MCP integration.

```bash
python examples/mcp/complete_mcp_bot_example.py
```

**What it demonstrates:**

- Complete bot setup with MCP
- Multiple MCP servers (stdio and HTTP)
- Combining MCP tools with built-in tools
- Error recovery and graceful degradation

### MCP Transport Examples

**File:** `mcp/mcp_transport_examples.py`

Demonstrates each MCP transport type.

```bash
python examples/mcp/mcp_transport_examples.py
```

**What it demonstrates:**

- stdio transport (subprocess-based)
- HTTP streamable transport
- SSE transport (deprecated)
- Multiple transports simultaneously

### MCP Integration Example

**File:** `mcp/mcp_integration_example.py`

Original MCP integration examples.

```bash
python examples/mcp/mcp_integration_example.py
```

### MCP Tool Discovery

**File:** `mcp/mcp_tool_discovery_example.py`

Demonstrates MCP tool discovery.

```bash
python examples/mcp/mcp_tool_discovery_example.py
```

---

## Running the Examples

### General Steps

1. **Set environment variables:**

   ```bash
   export OPENAI_API_KEY='your-key'
   # Add Feishu variables if needed
   ```

2. **Install dependencies:**

   ```bash
   pip install 'pydantic-ai-slim[mcp]' duckduckgo-search
   ```

3. **Install MCP servers (if needed):**

   ```bash
   uv tool install mcp-run-python
   ```

4. **Run the example:**

   ```bash
   python examples/example_name.py
   ```

### Running Specific Examples

#### For AI-only examples (no Feishu)

```bash
export OPENAI_API_KEY='your-key'
python examples/advanced_ai_features.py
```

#### For MCP examples

```bash
export OPENAI_API_KEY='your-key'
uv tool install mcp-run-python
python examples/mcp_transport_examples.py
```

#### For complete bot examples

```bash
export OPENAI_API_KEY='your-key'
export FEISHU_APP_ID='your-app-id'
export FEISHU_APP_SECRET='your-app-secret'
export FEISHU_VERIFICATION_TOKEN='your-token'
python examples/complete_mcp_bot_example.py
```

## Troubleshooting

### Common Issues

#### 1. Authentication Database Issues

**Error:** `sqlite3.OperationalError: database is locked`

**Solution:**

- Close any other processes using the database
- Use a different database file for each example
- For production, use PostgreSQL or MySQL instead of SQLite

#### 2. Password Validation Errors

**Error:** `Password must contain at least one uppercase letter`

**Solution:**

Ensure your password meets all requirements:

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (!@#$%^&*(),.?":{}|<>)

Example valid password: `SecureP@ss123`

#### 3. JWT Token Errors

**Error:** `Invalid or expired token`

**Solution:**

- Check that the SECRET_KEY is consistent across requests
- Verify token hasn't expired (default: 30 minutes)
- Ensure token is passed in Authorization header: `Bearer YOUR_TOKEN`
- For production, use a strong secret key (min 32 characters)

#### 4. Account Lockout

**Error:** `Account is locked due to too many failed attempts`

**Solution:**

- Wait 30 minutes for automatic unlock
- Or manually unlock using `auth_service.unlock_account(user_id)`
- Check failed login attempts: `user.failed_login_attempts`

#### 5. Plugin Loading Errors

**Error:** `No plugin class found in: plugin_file.py`

**Solution:**

- Ensure plugin class extends `BasePlugin`
- Plugin class must be defined in the same file
- Plugin file must not start with underscore (_)
- Check for import errors in plugin code

#### 6. Scheduler Job Store Errors

**Error:** `SQLAlchemy is not installed`

**Solution:**

```bash
# Install SQLAlchemy for persistent job store
pip install sqlalchemy
# or
uv add sqlalchemy
```

For in-memory job store, set `job_store_type: "memory"` in config.

#### 7. Automation Rule Errors

**Error:** `Template not found: template-name`

**Solution:**

- Ensure template is defined in `templates` section of config
- Check template name matches exactly (case-sensitive)
- Verify template type is correct (text, rich_text, card)

#### 8. Task Execution Errors

**Error:** `Task condition not met`

**Solution:**

- Check environment variables match task conditions
- Verify time/day conditions are correct
- Review task logs for condition evaluation details

#### 9. Event Server Port Conflicts

**Error:** `Address already in use`

**Solution:**

- Change port in EventServerConfig
- Kill process using the port: `lsof -ti:8080 | xargs kill` (Unix) or `netstat -ano | findstr :8080` (Windows)
- Use a different port for each demo

#### 10. Missing API Key

**Error:** `OPENAI_API_KEY not set`

**Solution:**

```bash
export OPENAI_API_KEY='your-key-here'
```

#### 11. MCP Server Not Found

**Error:** `Failed to start MCP server` or `Command not found`

**Solution:**

```bash
# For Python MCP server
uv tool install mcp-run-python

# For filesystem server
npm install -g @modelcontextprotocol/server-filesystem

# Or use npx (no installation)
# The example will use npx automatically
```

#### 12. Import Errors

**Error:** `ModuleNotFoundError: No module named 'pydantic_ai'`

**Solution:**

```bash
pip install 'pydantic-ai-slim[mcp]'
```

#### 13. MCP Connection Timeout

**Error:** `MCP server connection timeout`

**Solution:**

- Increase timeout in configuration:

  ```python
  mcp=MCPConfig(
      enabled=True,
      timeout_seconds=60,  # Increase from default 30
      servers=[...]
  )
  ```

- Check if MCP server is running
- Verify server command and arguments

#### 14. Feishu Webhook Not Receiving Events

**Error:** Bot starts but doesn't respond to messages

**Solution:**

1. Verify webhook URL is configured in Feishu app settings
2. Check that the bot is listening on the correct port
3. Ensure firewall allows incoming connections
4. Verify verification token matches

### Getting Help

For more help:

- Check the main [README.md](../README.md)
- Review [MCP Integration Guide](../docs/MCP_INTEGRATION.md)
- Review [Advanced AI Features](../ADVANCED_AI_FEATURES.md)
- Check the [Troubleshooting section](../README.md#troubleshooting) in main README

### Testing Without Real Servers

If you don't have MCP servers installed, you can still test:

1. **Disable MCP:**

   ```python
   mcp=MCPConfig(enabled=False)
   ```

2. **Use built-in tools only:**

   ```python
   config = AIConfig(
       enabled=True,
       tools_enabled=True,
       web_search_enabled=True,
       mcp=MCPConfig(enabled=False),  # Disable MCP
   )
   ```

3. **Mock MCP servers in tests:**
   See `tests/test_mcp_integration.py` for examples

## Example Output

### Successful MCP Bot Startup

```text
=== Feishu Bot with MCP Integration ===

Creating bot configuration...
Creating bot instance...
Starting bot...

=== Test 1: Basic Conversation ===
Response: Hello! I'm an AI assistant integrated with Feishu...

=== Test 2: Web Search ===
Response: Here are the latest news about AI...

=== Test 3: Python Code Execution (MCP) ===
Response: The factorial of 10 is 3628800...

=== AI Agent Statistics ===
Model: openai:gpt-4o
Tools enabled: True
Web search enabled: True
MCP enabled: True
MCP started: True
MCP servers: 1

=== Bot is running ===
Event server: http://0.0.0.0:8080/webhook
Configure this URL in your Feishu app settings
Press Ctrl+C to stop
```

## Next Steps

After running the examples:

1. **Customize for your use case:**
   - Modify system prompts
   - Add custom tools
   - Configure specialized agents

2. **Deploy to production:**
   - Use environment-specific configuration
   - Set up proper logging
   - Configure monitoring

3. **Extend functionality:**
   - Add more MCP servers
   - Create custom plugins
   - Implement advanced workflows

Happy coding! 🚀
