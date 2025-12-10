# Configuration Reference

Complete reference for all configuration options in the Feishu Webhook Bot framework.

## Table of Contents

- [Configuration File](#configuration-file)
- [General Settings](#general-settings)
- [Webhooks](#webhooks)
- [Providers](#providers)
- [Scheduler](#scheduler)
- [Plugins](#plugins)
- [Automation](#automation)
- [Tasks](#tasks)
- [AI Configuration](#ai-configuration)
- [Authentication](#authentication)
- [Event Server](#event-server)
- [Logging](#logging)
- [HTTP Client](#http-client)
- [Message Queue](#message-queue)
- [Message Tracking](#message-tracking)
- [Circuit Breaker](#circuit-breaker)
- [Environment Variables](#environment-variables)

## Configuration File

The bot uses YAML configuration files. Default location: `config.yaml`

```yaml
# Minimal configuration
webhooks:
  - name: default
    url: "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_URL"
```

### Loading Configuration

```python
from feishu_webhook_bot.core import BotConfig

# From YAML file
config = BotConfig.from_yaml("config.yaml")

# From JSON file
config = BotConfig.from_json("config.json")

# From dictionary
config = BotConfig(**config_dict)
```

## General Settings

```yaml
general:
  name: "My Feishu Bot"
  description: "A powerful Feishu bot"
  version: "1.0.0"
  debug: false
  timezone: "Asia/Shanghai"
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | string | "Feishu Bot" | Bot display name |
| `description` | string | "" | Bot description |
| `version` | string | "1.0.0" | Bot version |
| `debug` | bool | false | Enable debug mode |
| `timezone` | string | "Asia/Shanghai" | Default timezone |

## Webhooks

Configure Feishu webhook endpoints:

```yaml
webhooks:
  - name: default
    url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
    secret: "signing-secret"
    enabled: true
    timeout: 10.0
    retry:
      max_retries: 3
      retry_delay: 1.0
      backoff_factor: 2.0

  - name: alerts
    url: "https://open.feishu.cn/open-apis/bot/v2/hook/yyy"
    secret: "another-secret"
```

### Webhook Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | string | Required | Unique webhook identifier |
| `url` | string | Required | Feishu webhook URL |
| `secret` | string | None | HMAC-SHA256 signing secret |
| `enabled` | bool | true | Whether webhook is active |
| `timeout` | float | 10.0 | Request timeout in seconds |
| `retry.max_retries` | int | 3 | Maximum retry attempts |
| `retry.retry_delay` | float | 1.0 | Initial retry delay |
| `retry.backoff_factor` | float | 2.0 | Exponential backoff multiplier |

## Providers

Configure multi-platform message providers:

```yaml
providers:
  - provider_type: feishu
    name: feishu-main
    enabled: true
    url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
    secret: "secret"
    timeout: 10.0

  - provider_type: qq_napcat
    name: qq-group
    enabled: true
    http_url: "http://127.0.0.1:3000"
    access_token: "token"
    default_target: "group:123456"

default_provider: feishu-main
```

### Provider Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `provider_type` | string | Required | Provider type (feishu, qq_napcat) |
| `name` | string | Required | Unique provider identifier |
| `enabled` | bool | true | Whether provider is active |
| `timeout` | float | 10.0 | Request timeout |

See [Multi-Provider Guide](providers-guide.md) for detailed provider configuration.

## Scheduler

Configure the APScheduler-based task scheduler:

```yaml
scheduler:
  enabled: true
  timezone: "Asia/Shanghai"
  job_store_type: "sqlite"
  job_store_path: "data/jobs.db"
  executors:
    default:
      type: threadpool
      max_workers: 10
    processpool:
      type: processpool
      max_workers: 5
  job_defaults:
    coalesce: true
    max_instances: 3
    misfire_grace_time: 60
```

### Scheduler Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | true | Enable scheduler |
| `timezone` | string | "Asia/Shanghai" | Scheduler timezone |
| `job_store_type` | string | "memory" | Job store type (memory, sqlite) |
| `job_store_path` | string | None | SQLite database path |
| `job_defaults.coalesce` | bool | true | Combine missed runs |
| `job_defaults.max_instances` | int | 3 | Max concurrent job instances |
| `job_defaults.misfire_grace_time` | int | 60 | Grace time for misfires |

## Plugins

Configure the plugin system:

```yaml
plugins:
  enabled: true
  plugin_dir: "plugins"
  auto_reload: true
  reload_interval: 5.0
  disabled_plugins:
    - "example_plugin"
  plugin_settings:
    system-monitor:
      check_interval: 60
      cpu_threshold: 80
    reminder:
      default_webhook: "default"
```

### Plugin Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | true | Enable plugin system |
| `plugin_dir` | string | "plugins" | Plugin directory path |
| `auto_reload` | bool | true | Enable hot-reload |
| `reload_interval` | float | 5.0 | Hot-reload check interval |
| `disabled_plugins` | list | [] | Plugins to disable |
| `plugin_settings` | dict | {} | Per-plugin configuration |

## Automation

Configure declarative automation rules:

```yaml
automation:
  enabled: true
  rules:
    - name: "daily-report"
      enabled: true
      trigger:
        type: schedule
        cron: "0 9 * * *"
      action:
        type: send_text
        text: "Good morning! Daily report time."
        webhooks: ["default"]

    - name: "http-health-check"
      trigger:
        type: schedule
        interval: 300
      action:
        type: http_request
        request:
          method: GET
          url: "https://api.example.com/health"
      conditions:
        - type: time_range
          start_time: "09:00"
          end_time: "18:00"
```

### Automation Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | true | Enable automation |
| `rules` | list | [] | Automation rules |

See [Automation Guide](automation-guide.md) for detailed automation configuration.

## Tasks

Configure advanced task execution:

```yaml
tasks:
  - name: "data-pipeline"
    description: "Fetch and process data"
    enabled: true
    schedule:
      mode: cron
      arguments:
        hour: "8"
        minute: "0"
    actions:
      - type: http_request
        request:
          url: "https://api.example.com/data"
          save_as: "data"
      - type: python_code
        code: |
          processed = transform(context['data'])
          context['result'] = processed
      - type: send_message
        message: "Pipeline complete: ${result}"
    error_handling:
      retry_on_failure: true
      max_retries: 3
      on_failure_action: notify
      notification_webhook: alerts
```

See [Task System Guide](tasks-guide.md) for detailed task configuration.

## AI Configuration

Configure AI features:

```yaml
ai:
  enabled: true
  model: "openai:gpt-4o"
  api_key: "${OPENAI_API_KEY}"
  api_base: null
  temperature: 0.7
  max_tokens: 2000
  system_prompt: "You are a helpful assistant."
  
  # Conversation management
  conversation:
    max_history: 20
    max_tokens: 4000
    ttl: 3600
  
  # Tool calling
  tools:
    enabled: true
    web_search: true
    code_execution: false
  
  # MCP integration
  mcp:
    enabled: true
    servers:
      - name: "filesystem"
        command: "npx"
        args: ["-y", "@anthropic/mcp-server-filesystem", "/path"]
```

### AI Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | false | Enable AI features |
| `model` | string | Required | Model identifier (provider:model) |
| `api_key` | string | Required | API key |
| `api_base` | string | None | Custom API base URL |
| `temperature` | float | 0.7 | Response randomness |
| `max_tokens` | int | 2000 | Max response tokens |
| `system_prompt` | string | None | Default system prompt |

See [AI Multi-Provider Guide](../ai/multi-provider.md) for detailed AI configuration.

## Authentication

Configure user authentication:

```yaml
auth:
  enabled: true
  jwt_secret: "${JWT_SECRET}"
  jwt_algorithm: "HS256"
  access_token_expire_minutes: 30
  refresh_token_expire_days: 7
  
  database:
    url: "sqlite:///data/auth.db"
  
  password:
    min_length: 8
    require_uppercase: true
    require_lowercase: true
    require_digit: true
    require_special: false
  
  rate_limiting:
    enabled: true
    max_attempts: 5
    lockout_minutes: 15
```

### Auth Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | false | Enable authentication |
| `jwt_secret` | string | Required | JWT signing secret |
| `jwt_algorithm` | string | "HS256" | JWT algorithm |
| `access_token_expire_minutes` | int | 30 | Access token TTL |
| `refresh_token_expire_days` | int | 7 | Refresh token TTL |

See [Authentication Guide](../security/authentication.md) for detailed auth configuration.

## Event Server

Configure the event server for receiving webhooks:

```yaml
event_server:
  enabled: true
  host: "0.0.0.0"
  port: 8080
  path: "/webhook"
  verification_token: "${FEISHU_VERIFICATION_TOKEN}"
  encrypt_key: "${FEISHU_ENCRYPT_KEY}"
```

### Event Server Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | false | Enable event server |
| `host` | string | "0.0.0.0" | Bind host |
| `port` | int | 8080 | Bind port |
| `path` | string | "/webhook" | Webhook endpoint path |
| `verification_token` | string | None | Feishu verification token |
| `encrypt_key` | string | None | Message encryption key |

## Logging

Configure logging:

```yaml
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  log_file: "logs/bot.log"
  max_bytes: 10485760
  backup_count: 5
  console: true
  json_format: false
```

### Logging Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `level` | string | "INFO" | Log level |
| `format` | string | See above | Log format string |
| `log_file` | string | None | Log file path |
| `max_bytes` | int | 10485760 | Max log file size |
| `backup_count` | int | 5 | Number of backup files |
| `console` | bool | true | Log to console |
| `json_format` | bool | false | Use JSON format |

## HTTP Client

Configure the HTTP client:

```yaml
http_client:
  timeout: 30.0
  max_connections: 100
  max_keepalive_connections: 20
  keepalive_expiry: 5.0
  http2: true
  verify_ssl: true
  proxy: null
```

### HTTP Client Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `timeout` | float | 30.0 | Request timeout |
| `max_connections` | int | 100 | Max connections |
| `max_keepalive_connections` | int | 20 | Max keepalive connections |
| `http2` | bool | true | Enable HTTP/2 |
| `verify_ssl` | bool | true | Verify SSL certificates |
| `proxy` | string | None | Proxy URL |

## Message Queue

Configure the message queue:

```yaml
message_queue:
  enabled: true
  max_size: 1000
  batch_size: 10
  flush_interval: 1.0
  retry_failed: true
  max_retries: 3
  dead_letter_queue: true
```

### Message Queue Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | true | Enable message queue |
| `max_size` | int | 1000 | Maximum queue size |
| `batch_size` | int | 10 | Batch processing size |
| `flush_interval` | float | 1.0 | Flush interval in seconds |
| `retry_failed` | bool | true | Retry failed messages |
| `max_retries` | int | 3 | Max retry attempts |
| `dead_letter_queue` | bool | true | Enable dead letter queue |

## Message Tracking

Configure message tracking:

```yaml
message_tracking:
  enabled: true
  db_path: "data/messages.db"
  retention_days: 30
  track_delivery: true
  track_read: false
```

### Message Tracking Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | false | Enable tracking |
| `db_path` | string | "data/messages.db" | Database path |
| `retention_days` | int | 30 | Data retention period |
| `track_delivery` | bool | true | Track delivery status |
| `track_read` | bool | false | Track read status |

## Circuit Breaker

Configure circuit breaker for fault tolerance:

```yaml
circuit_breaker:
  enabled: true
  failure_threshold: 5
  success_threshold: 2
  reset_timeout: 30.0
  half_open_max_calls: 3
```

### Circuit Breaker Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | true | Enable circuit breaker |
| `failure_threshold` | int | 5 | Failures before opening |
| `success_threshold` | int | 2 | Successes to close |
| `reset_timeout` | float | 30.0 | Time before half-open |
| `half_open_max_calls` | int | 3 | Test calls in half-open |

## Environment Variables

Use environment variables in configuration:

```yaml
webhooks:
  - name: default
    url: "${FEISHU_WEBHOOK_URL}"
    secret: "${FEISHU_SECRET}"

ai:
  api_key: "${OPENAI_API_KEY}"
```

### Environment Variable Syntax

| Syntax | Description |
|--------|-------------|
| `${VAR}` | Required variable |
| `${VAR:-default}` | Variable with default |
| `${VAR:?error}` | Required with error message |

### Common Environment Variables

| Variable | Description |
|----------|-------------|
| `FEISHU_WEBHOOK_URL` | Default webhook URL |
| `FEISHU_SECRET` | Webhook signing secret |
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `JWT_SECRET` | JWT signing secret |

## Configuration Validation

The framework validates configuration on load:

```python
from feishu_webhook_bot.core import BotConfig
from pydantic import ValidationError

try:
    config = BotConfig.from_yaml("config.yaml")
except ValidationError as e:
    print(f"Configuration error: {e}")
```

## Hot Reload

Configuration can be reloaded at runtime:

```python
# Enable config watcher
from feishu_webhook_bot.core import ConfigWatcher

watcher = ConfigWatcher("config.yaml", on_change=reload_callback)
watcher.start()
```

## See Also

- [YAML Configuration Guide](yaml-configuration-guide.md) - YAML-specific features
- [Enhanced YAML Features](enhanced-yaml-features.md) - Advanced YAML features
- [Core Reference](../reference/core-reference.md) - Core component details
