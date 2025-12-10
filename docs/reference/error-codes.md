# Error Codes Reference

Complete reference for all error codes and exceptions in the Feishu Webhook Bot framework.

## Table of Contents

- [Error Code Format](#error-code-format)
- [HTTP Status Codes](#http-status-codes)
- [Feishu API Errors](#feishu-api-errors)
- [Framework Exceptions](#framework-exceptions)
- [Plugin Errors](#plugin-errors)
- [AI Errors](#ai-errors)
- [Authentication Errors](#authentication-errors)
- [Configuration Errors](#configuration-errors)

## Error Code Format

Error codes follow the format: `CATEGORY_CODE`

| Category | Range | Description |
|----------|-------|-------------|
| `HTTP_` | 1xx-5xx | HTTP status codes |
| `FEISHU_` | 10000-19999 | Feishu API errors |
| `BOT_` | 20000-29999 | Bot framework errors |
| `PLUGIN_` | 30000-39999 | Plugin system errors |
| `AI_` | 40000-49999 | AI feature errors |
| `AUTH_` | 50000-59999 | Authentication errors |
| `CONFIG_` | 60000-69999 | Configuration errors |

## HTTP Status Codes

Standard HTTP status codes returned by the framework:

| Code | Name | Description |
|------|------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid request format |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Permission denied |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 502 | Bad Gateway | Upstream service error |
| 503 | Service Unavailable | Service temporarily unavailable |
| 504 | Gateway Timeout | Upstream timeout |

## Feishu API Errors

Errors returned by the Feishu API:

### Authentication Errors (10000-10999)

| Code | Name | Description | Solution |
|------|------|-------------|----------|
| 10001 | `INVALID_APP_ID` | Invalid app ID | Check app credentials |
| 10002 | `INVALID_APP_SECRET` | Invalid app secret | Verify app secret |
| 10003 | `TOKEN_EXPIRED` | Access token expired | Refresh token |
| 10004 | `INVALID_TOKEN` | Invalid access token | Re-authenticate |

### Webhook Errors (19000-19999)

| Code | Name | Description | Solution |
|------|------|-------------|----------|
| 19001 | `INVALID_WEBHOOK_URL` | Webhook URL invalid | Check URL format |
| 19002 | `WEBHOOK_NOT_FOUND` | Webhook not found | Verify webhook exists |
| 19021 | `SIGN_MATCH_FAIL` | Signature verification failed | Check signing secret |
| 19022 | `TIMESTAMP_EXPIRED` | Request timestamp expired | Check server time |

### Message Errors (11000-11999)

| Code | Name | Description | Solution |
|------|------|-------------|----------|
| 11001 | `MESSAGE_TOO_LARGE` | Message exceeds size limit | Reduce message size |
| 11002 | `INVALID_MESSAGE_TYPE` | Unsupported message type | Use valid message type |
| 11003 | `INVALID_CONTENT` | Invalid message content | Check content format |
| 11004 | `CHAT_NOT_FOUND` | Chat/group not found | Verify chat ID |
| 11005 | `BOT_NOT_IN_CHAT` | Bot not in chat | Add bot to chat |

### Rate Limiting (12000-12999)

| Code | Name | Description | Solution |
|------|------|-------------|----------|
| 12001 | `RATE_LIMIT_EXCEEDED` | Too many requests | Implement backoff |
| 12002 | `QUOTA_EXCEEDED` | API quota exceeded | Upgrade plan or wait |

## Framework Exceptions

### Base Exceptions

```python
from feishu_webhook_bot.core.exceptions import (
    FeishuBotError,
    ConfigurationError,
    WebhookError,
    MessageError,
    PluginError,
)
```

### BOT_20000 - General Bot Errors

| Code | Exception | Description |
|------|-----------|-------------|
| 20001 | `BotNotInitializedError` | Bot not properly initialized |
| 20002 | `BotAlreadyRunningError` | Bot is already running |
| 20003 | `BotNotRunningError` | Bot is not running |
| 20004 | `ComponentNotFoundError` | Required component not found |

### BOT_21000 - Webhook Errors

| Code | Exception | Description |
|------|-----------|-------------|
| 21001 | `WebhookNotFoundError` | Webhook name not configured |
| 21002 | `WebhookConnectionError` | Failed to connect to webhook |
| 21003 | `WebhookTimeoutError` | Webhook request timed out |
| 21004 | `WebhookSignatureError` | Signature verification failed |

```python
from feishu_webhook_bot.core.exceptions import WebhookError

try:
    client.send_text("Hello")
except WebhookError as e:
    print(f"Webhook error {e.code}: {e.message}")
```

### BOT_22000 - Message Errors

| Code | Exception | Description |
|------|-----------|-------------|
| 22001 | `MessageSendError` | Failed to send message |
| 22002 | `MessageFormatError` | Invalid message format |
| 22003 | `TemplateNotFoundError` | Message template not found |
| 22004 | `TemplateRenderError` | Failed to render template |

### BOT_23000 - Scheduler Errors

| Code | Exception | Description |
|------|-----------|-------------|
| 23001 | `SchedulerNotRunningError` | Scheduler not started |
| 23002 | `JobNotFoundError` | Scheduled job not found |
| 23003 | `InvalidScheduleError` | Invalid schedule configuration |
| 23004 | `JobExecutionError` | Job execution failed |

### BOT_24000 - Provider Errors

| Code | Exception | Description |
|------|-----------|-------------|
| 24001 | `ProviderNotFoundError` | Provider not configured |
| 24002 | `ProviderConnectionError` | Failed to connect to provider |
| 24003 | `ProviderAuthError` | Provider authentication failed |
| 24004 | `UnsupportedProviderError` | Provider type not supported |

## Plugin Errors

### PLUGIN_30000 - Plugin System Errors

| Code | Exception | Description |
|------|-----------|-------------|
| 30001 | `PluginLoadError` | Failed to load plugin |
| 30002 | `PluginNotFoundError` | Plugin not found |
| 30003 | `PluginDependencyError` | Missing plugin dependency |
| 30004 | `PluginConfigError` | Invalid plugin configuration |
| 30005 | `PluginDisabledError` | Plugin is disabled |

```python
from feishu_webhook_bot.plugins.exceptions import PluginError

try:
    plugin_manager.load_plugin("my_plugin")
except PluginError as e:
    print(f"Plugin error {e.code}: {e.message}")
```

### PLUGIN_31000 - Plugin Lifecycle Errors

| Code | Exception | Description |
|------|-----------|-------------|
| 31001 | `PluginEnableError` | Failed to enable plugin |
| 31002 | `PluginDisableError` | Failed to disable plugin |
| 31003 | `PluginReloadError` | Failed to reload plugin |
| 31004 | `PluginInitError` | Plugin initialization failed |

## AI Errors

### AI_40000 - General AI Errors

| Code | Exception | Description |
|------|-----------|-------------|
| 40001 | `AINotEnabledError` | AI features not enabled |
| 40002 | `AIProviderError` | AI provider error |
| 40003 | `AIModelNotFoundError` | AI model not found |
| 40004 | `AIConfigError` | Invalid AI configuration |

### AI_41000 - API Errors

| Code | Exception | Description |
|------|-----------|-------------|
| 41001 | `AIAuthError` | AI API authentication failed |
| 41002 | `AIRateLimitError` | AI API rate limit exceeded |
| 41003 | `AIQuotaError` | AI API quota exceeded |
| 41004 | `AITimeoutError` | AI API request timed out |

```python
from feishu_webhook_bot.ai.exceptions import AIError

try:
    response = await agent.chat(user_id, message)
except AIError as e:
    if e.code == 41002:
        await asyncio.sleep(60)  # Wait before retry
```

### AI_42000 - Tool Errors

| Code | Exception | Description |
|------|-----------|-------------|
| 42001 | `ToolNotFoundError` | Tool not registered |
| 42002 | `ToolExecutionError` | Tool execution failed |
| 42003 | `ToolTimeoutError` | Tool execution timed out |
| 42004 | `ToolValidationError` | Invalid tool parameters |

### AI_43000 - MCP Errors

| Code | Exception | Description |
|------|-----------|-------------|
| 43001 | `MCPServerError` | MCP server error |
| 43002 | `MCPConnectionError` | Failed to connect to MCP server |
| 43003 | `MCPToolError` | MCP tool execution failed |

## Authentication Errors

### AUTH_50000 - Authentication Errors

| Code | Exception | Description |
|------|-----------|-------------|
| 50001 | `AuthNotEnabledError` | Authentication not enabled |
| 50002 | `InvalidCredentialsError` | Invalid username or password |
| 50003 | `UserNotFoundError` | User not found |
| 50004 | `UserExistsError` | User already exists |
| 50005 | `AccountLockedError` | Account locked due to failed attempts |

### AUTH_51000 - Token Errors

| Code | Exception | Description |
|------|-----------|-------------|
| 51001 | `TokenExpiredError` | JWT token expired |
| 51002 | `TokenInvalidError` | Invalid JWT token |
| 51003 | `TokenRevokedError` | Token has been revoked |
| 51004 | `RefreshTokenError` | Failed to refresh token |

```python
from feishu_webhook_bot.auth.exceptions import AuthError

try:
    user = await auth_service.authenticate(username, password)
except AuthError as e:
    if e.code == 50005:
        print("Account locked. Try again later.")
```

### AUTH_52000 - Permission Errors

| Code | Exception | Description |
|------|-----------|-------------|
| 52001 | `PermissionDeniedError` | Permission denied |
| 52002 | `InsufficientPrivilegesError` | Insufficient privileges |
| 52003 | `RoleNotFoundError` | Role not found |

## Configuration Errors

### CONFIG_60000 - Configuration Errors

| Code | Exception | Description |
|------|-----------|-------------|
| 60001 | `ConfigNotFoundError` | Configuration file not found |
| 60002 | `ConfigParseError` | Failed to parse configuration |
| 60003 | `ConfigValidationError` | Configuration validation failed |
| 60004 | `ConfigMissingFieldError` | Required field missing |

```python
from feishu_webhook_bot.core.exceptions import ConfigurationError

try:
    config = BotConfig.from_yaml("config.yaml")
except ConfigurationError as e:
    print(f"Config error {e.code}: {e.message}")
    print(f"Field: {e.field}")  # Which field caused the error
```

### CONFIG_61000 - Environment Errors

| Code | Exception | Description |
|------|-----------|-------------|
| 61001 | `EnvVarNotFoundError` | Environment variable not found |
| 61002 | `EnvVarInvalidError` | Invalid environment variable value |

## Error Handling Examples

### Basic Error Handling

```python
from feishu_webhook_bot.core.exceptions import FeishuBotError

try:
    bot.send_text("Hello")
except FeishuBotError as e:
    logger.error(f"Bot error: {e.code} - {e.message}")
```

### Specific Error Handling

```python
from feishu_webhook_bot.core.exceptions import (
    WebhookError,
    WebhookTimeoutError,
    WebhookSignatureError,
)

try:
    client.send_text("Hello")
except WebhookTimeoutError:
    # Retry with backoff
    await retry_with_backoff(client.send_text, "Hello")
except WebhookSignatureError:
    # Log security event
    logger.warning("Signature verification failed")
except WebhookError as e:
    # Handle other webhook errors
    logger.error(f"Webhook error: {e}")
```

### Error Response Format

API error responses follow this format:

```json
{
    "error": {
        "code": 21001,
        "message": "Webhook not found",
        "details": {
            "webhook_name": "invalid_webhook"
        }
    }
}
```

### Custom Error Handler

```python
from feishu_webhook_bot.core.exceptions import FeishuBotError

class ErrorHandler:
    def __init__(self, bot):
        self.bot = bot
    
    async def handle(self, error: FeishuBotError):
        # Log error
        logger.error(f"Error {error.code}: {error.message}")
        
        # Notify if critical
        if error.code >= 50000:
            await self.notify_admin(error)
        
        # Return user-friendly message
        return self.get_user_message(error)
    
    def get_user_message(self, error: FeishuBotError) -> str:
        messages = {
            21003: "Service temporarily unavailable. Please try again.",
            41002: "AI service is busy. Please wait a moment.",
            50002: "Invalid credentials. Please check and try again.",
        }
        return messages.get(error.code, "An error occurred.")
```

## See Also

- [Troubleshooting](../resources/troubleshooting.md) - Common issues
- [API Reference](api.md) - API documentation
- [FAQ](../resources/faq.md) - Frequently asked questions
