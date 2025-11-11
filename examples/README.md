# Examples

This directory contains comprehensive examples demonstrating the Feishu Webhook Bot's capabilities, with a focus on advanced AI features and MCP integration.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Basic Examples](#basic-examples)
- [Core Module Examples](#core-module-examples)
- [Authentication Examples](#authentication-examples)
- [Advanced AI Examples](#advanced-ai-examples)
- [MCP Integration Examples](#mcp-integration-examples)
- [Running the Examples](#running-the-examples)
- [Troubleshooting](#troubleshooting)

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

## Basic Examples

### 1. Simple Bot Example

**File:** `simple_bot_example.py`

Basic Feishu bot without AI capabilities.

```bash
python examples/simple_bot_example.py
```

**What it demonstrates:**

- Basic bot setup
- Event handling
- Webhook configuration

## Core Module Examples

### 2. Plugin System Demo

**File:** `plugin_demo.py`

Comprehensive demonstration of the plugin system.

```bash
python examples/plugin_demo.py
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

**Prerequisites:**

- None (uses temporary directories for plugins)

**Expected output:**

- 6 interactive demonstrations
- Plugin creation and loading
- Scheduled task execution
- Configuration access
- Event handling
- Hot-reload in action
- Priority-based loading

### 3. Task Scheduler Demo

**File:** `scheduler_demo.py`

Comprehensive demonstration of the task scheduler.

```bash
python examples/scheduler_demo.py
```

**What it demonstrates:**

- Scheduling tasks with cron expressions
- Interval-based scheduling
- Job management (add, remove, pause, resume)
- Persistent vs in-memory job stores
- Timezone-aware scheduling
- Job decorators (@job)
- Error handling and retry logic

**Prerequisites:**

- None (creates temporary SQLite database for persistent store demo)

**Expected output:**

- 8 interactive demonstrations
- Task scheduling with various triggers
- Job lifecycle management
- SQLite persistence
- Timezone handling
- Error recovery

### 4. Automation Engine Demo

**File:** `automation_demo.py`

Comprehensive demonstration of the automation engine.

```bash
python examples/automation_demo.py
```

**What it demonstrates:**

- Declarative workflow definitions
- Schedule-based triggers
- Action types:
  - Send messages
  - HTTP requests
  - Python code execution
  - Plugin method calls
- Template rendering with variable substitution
- Conditional execution

**Prerequisites:**

- None (uses temporary directories for plugins)

**Expected output:**

- 6 interactive demonstrations
- Automated workflows
- Template rendering
- HTTP requests to external APIs
- Python code execution
- Plugin integration
- Conditional logic

### 5. Task Manager Demo

**File:** `task_manager_demo.py`

Comprehensive demonstration of the task manager.

```bash
python examples/task_manager_demo.py
```

**What it demonstrates:**

- Automated task execution
- Task dependencies and retry logic
- Task conditions (time, day, environment)
- Integration with plugins
- Cron-based scheduling
- Multiple actions per task

**Prerequisites:**

- None (uses temporary directories for plugins)

**Expected output:**

- 7 interactive demonstrations
- Task execution with various configurations
- Dependency management
- Retry logic
- Plugin integration
- Conditional execution

### 6. Event Server Demo

**File:** `event_server_demo.py`

Comprehensive demonstration of the event server.

```bash
python examples/event_server_demo.py
```

**What it demonstrates:**

- Receiving Feishu webhook events
- Token verification
- Signature validation
- URL verification challenge
- Event dispatching to plugins
- Health check endpoint
- Concurrent event handling

**Prerequisites:**

- None (uses temporary directories for plugins)

**Expected output:**

- 6 interactive demonstrations
- HTTP server running on various ports
- Event reception and processing
- Security validation
- Plugin event handling
- Health monitoring

**How to test manually:**

```bash
# Start the demo in one terminal
python examples/event_server_demo.py

# In another terminal, send test events
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{"type":"message","message":{"content":"Hello!"}}'

# Check health
curl http://localhost:8080/healthz
```

## Authentication Examples

### 7. Authentication Demo

**File:** `auth_demo.py`

Comprehensive demonstration of all authentication features.

```bash
python examples/auth_demo.py
```

**What it demonstrates:**

- Password validation and strength checking
- Password hashing with bcrypt
- JWT token generation and validation
- User registration with validation
- User authentication and login
- Account lockout after failed attempts
- Email verification
- User operations (get by email, username, ID)

**Prerequisites:**

- None (uses in-memory SQLite database)

**Expected output:**

- Demonstrations of each authentication feature
- Success and failure scenarios
- Security best practices

### 8. FastAPI Authentication Integration

**File:** `auth_api_demo.py`

Demonstrates authentication integration with FastAPI.

```bash
python examples/auth_api_demo.py
```

**What it demonstrates:**

- Setting up authentication routes
- Using authentication middleware
- Protected endpoints with JWT tokens
- Token-based API access
- Rate limiting for security
- CORS configuration

**Prerequisites:**

- None (creates `demo_auth.db` SQLite database)

**Expected output:**

- FastAPI server running on http://localhost:8000
- Interactive API docs at http://localhost:8000/docs
- Working authentication endpoints

**How to test:**

```bash
# Register a user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"SecureP@ss123","password_confirm":"SecureP@ss123"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"test@example.com","password":"SecureP@ss123"}'

# Access protected endpoint (use token from login response)
curl -X GET http://localhost:8000/api/protected/profile \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 9. Advanced Authentication Scenarios

**File:** `auth_advanced_demo.py`

Demonstrates advanced authentication scenarios and best practices.

```bash
python examples/auth_advanced_demo.py
```

**What it demonstrates:**

- Token refresh workflow
- Multiple concurrent sessions
- Token expiration handling
- Comprehensive error handling
- Database session management
- Security best practices

**Prerequisites:**

- None (uses in-memory SQLite database)

**Expected output:**

- Token refresh demonstration (includes 61-second wait)
- Multiple session management
- Error handling examples
- Database transaction examples
- Security recommendations

**Note:** This example includes a 61-second wait to demonstrate token expiration. Be patient!

### 10. NiceGUI Authentication Example

**File:** `auth_example.py`

Demonstrates authentication with NiceGUI web interface.

```bash
python examples/auth_example.py
```

**What it demonstrates:**

- NiceGUI login and registration pages
- Protected pages with authentication
- Session management
- User interface for authentication

**Prerequisites:**

- None (creates `example_auth.db` SQLite database)

**Expected output:**

- Web interface running on http://localhost:8080
- Login and registration pages
- Protected dashboard

## Advanced AI Examples

### 11. AI Features Demo

**File:** `ai_features_demo.py`

Demonstrates all advanced AI capabilities.

```bash
python examples/ai_features_demo.py
```

**What it demonstrates:**

- Web search with caching
- Conversation management with token tracking
- Tool registry and custom tools
- Circuit breaker for rate limiting
- Conversation export/import
- Performance optimizations

**Prerequisites:**

- `OPENAI_API_KEY` environment variable

**Expected output:**

- Demonstrations of each AI feature
- Performance metrics
- Example responses

### 12. AI Capabilities Demo

**File:** `ai_capabilities_demo.py`

Demonstrates advanced AI capabilities including streaming and multi-agent orchestration.

```bash
python examples/ai_capabilities_demo.py
```

**What it demonstrates:**

- Structured output validation
- Streaming responses with debouncing
- Result validators and retry logic
- Custom model settings
- Multi-agent orchestration (sequential, concurrent, hierarchical)
- Specialized agents (search, analysis, response)
- MCP integration

**Prerequisites:**

- `OPENAI_API_KEY` environment variable

**Expected output:**

- Demonstrations of each capability
- Performance metrics
- Example responses

## MCP Integration Examples

### 13. Complete MCP Bot Example

**File:** `complete_mcp_bot_example.py`

End-to-end example of a Feishu bot with full MCP integration.

```bash
python examples/complete_mcp_bot_example.py
```

**What it demonstrates:**
- Complete bot setup with MCP
- Multiple MCP servers (stdio and HTTP)
- Combining MCP tools with built-in tools
- Error recovery and graceful degradation
- Real webhook event handling

**Prerequisites:**
- All Feishu environment variables
- `OPENAI_API_KEY`
- MCP servers (e.g., `mcp-run-python`)

**Expected output:**
- Bot starts and listens on http://0.0.0.0:8080/webhook
- Tests AI capabilities including:
  - Basic conversation
  - Web search
  - Python code execution via MCP
  - Complex multi-tool tasks

**How to use:**
1. Set all required environment variables
2. Run the example
3. Configure the webhook URL in your Feishu app settings
4. Send messages to your bot in Feishu

### 14. MCP Transport Types

**File:** `mcp_transport_examples.py`

Demonstrates each MCP transport type with examples.

```bash
python examples/mcp_transport_examples.py
```

**What it demonstrates:**
- **stdio transport**: Subprocess-based (recommended)
- **HTTP streamable transport**: Modern HTTP-based
- **SSE transport**: Server-Sent Events (deprecated)
- Multiple transports simultaneously
- Error recovery and fallback behavior

**Prerequisites:**
- `OPENAI_API_KEY`
- Various MCP servers for different transports

**Examples included:**
1. stdio with Python code execution
2. stdio with list arguments (filesystem)
3. HTTP streamable transport
4. SSE transport (deprecated)
5. Multiple transports together
6. Error recovery with invalid servers

**Note:** Comment out examples that require servers you don't have installed.

### 15. MCP Integration Example

**File:** `mcp_integration_example.py`

Original MCP integration examples from Phase 3.

```bash
python examples/mcp_integration_example.py
```

**What it demonstrates:**
- stdio MCP server (Python code execution)
- HTTP streamable MCP server
- Multiple MCP servers simultaneously
- MCP error handling
- MCP with Feishu bot integration

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

#### For AI-only examples (no Feishu):
```bash
export OPENAI_API_KEY='your-key'
python examples/advanced_ai_features.py
```

#### For MCP examples:
```bash
export OPENAI_API_KEY='your-key'
uv tool install mcp-run-python
python examples/mcp_transport_examples.py
```

#### For complete bot examples:
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

```
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

