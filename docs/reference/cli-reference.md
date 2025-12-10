# CLI Reference

This document provides complete reference for the Feishu Webhook Bot command-line interface.

## Table of Contents

- [Overview](#overview)
- [Global Options](#global-options)
- [Commands](#commands)
  - [start](#start)
  - [init](#init)
  - [send](#send)
  - [plugins](#plugins)
  - [webui](#webui)
  - [plugin](#plugin)

## Overview

The CLI provides commands for managing and operating the Feishu Webhook Bot.

```bash
feishu-webhook-bot [OPTIONS] COMMAND [ARGS]
```

## Global Options

| Option | Description |
|--------|-------------|
| `-v, --version` | Show version number and exit |
| `-h, --help` | Show help message and exit |

## Commands

### start

Start the bot with a configuration file.

```bash
feishu-webhook-bot start [OPTIONS]
```

#### Options

| Option | Default | Description |
|--------|---------|-------------|
| `-c, --config` | config.yaml | Path to configuration file |
| `--host` | 127.0.0.1 | Host to bind server to |
| `-p, --port` | 8080 | Port to bind server to |
| `-d, --debug` | false | Enable debug logging |

#### Examples

```bash
# Start with default config
feishu-webhook-bot start

# Start with custom config
feishu-webhook-bot start -c my-config.yaml

# Start with debug logging
feishu-webhook-bot start --debug

# Start with custom host and port
feishu-webhook-bot start --host 0.0.0.0 --port 9000
```

#### Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success or graceful shutdown |
| 1 | Error (config not found, startup failure) |

### init

Generate a default configuration file.

```bash
feishu-webhook-bot init [OPTIONS]
```

#### Options

| Option | Default | Description |
|--------|---------|-------------|
| `-o, --output` | config.yaml | Output file path |

#### Examples

```bash
# Generate default config
feishu-webhook-bot init

# Generate config with custom name
feishu-webhook-bot init -o my-bot-config.yaml

# Generate config in subdirectory
feishu-webhook-bot init -o configs/production.yaml
```

#### Output

Creates a YAML configuration file with default settings:

```yaml
webhooks:
  - name: default
    url: https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL

scheduler:
  enabled: true
  timezone: Asia/Shanghai

plugins:
  enabled: true
  plugin_dir: plugins
  auto_reload: true

logging:
  level: INFO
  log_file: null
```

### send

Send a test message to a webhook.

```bash
feishu-webhook-bot send [OPTIONS]
```

#### Options

| Option | Required | Description |
|--------|----------|-------------|
| `-w, --webhook` | Yes | Webhook URL |
| `-t, --text` | No | Message text (default: "Hello from Feishu Bot!") |
| `-s, --secret` | No | Webhook signing secret |

#### Examples

```bash
# Send default message
feishu-webhook-bot send -w "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"

# Send custom message
feishu-webhook-bot send -w "https://..." -t "Hello, World!"

# Send with signing
feishu-webhook-bot send -w "https://..." -t "Signed message" -s "my-secret"
```

### plugins

List loaded plugins from configuration.

```bash
feishu-webhook-bot plugins [OPTIONS]
```

#### Options

| Option | Default | Description |
|--------|---------|-------------|
| `-c, --config` | config.yaml | Path to configuration file |

#### Examples

```bash
# List plugins
feishu-webhook-bot plugins

# List plugins from custom config
feishu-webhook-bot plugins -c production.yaml
```

#### Output

```text
Loaded Plugins:
  - daily-greeting (v1.0.0) - Sends daily greeting messages
  - system-monitor (v1.0.0) - Monitors system resources
  - reminder (v1.0.0) - Sends customizable reminders
```

### webui

Launch the NiceGUI web configuration interface.

```bash
feishu-webhook-bot webui [OPTIONS]
```

#### Options

| Option | Default | Description |
|--------|---------|-------------|
| `-c, --config` | config.yaml | Path to configuration file |
| `--host` | 127.0.0.1 | Bind host |
| `--port` | 8080 | Bind port |

#### Examples

```bash
# Start web UI with defaults
feishu-webhook-bot webui

# Start on all interfaces
feishu-webhook-bot webui --host 0.0.0.0

# Start on custom port
feishu-webhook-bot webui --port 9000

# Start with custom config
feishu-webhook-bot webui -c production.yaml --host 0.0.0.0 --port 8888
```

#### Features

The web UI provides:

- Configuration editing with validation
- Bot start/stop/restart controls
- Real-time log viewing
- Plugin management
- Status monitoring

### plugin

Plugin management commands.

```bash
feishu-webhook-bot plugin SUBCOMMAND [OPTIONS]
```

#### Subcommands

##### plugin setup

Interactive configuration wizard for a plugin.

```bash
feishu-webhook-bot plugin setup PLUGIN_NAME [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `-c, --config` | config.yaml | Configuration file |
| `--non-interactive` | false | Use defaults without prompting |

```bash
# Interactive setup
feishu-webhook-bot plugin setup system-monitor

# Non-interactive setup
feishu-webhook-bot plugin setup system-monitor --non-interactive
```

##### plugin list

List available plugins and their configuration status.

```bash
feishu-webhook-bot plugin list [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `-c, --config` | config.yaml | Configuration file |
| `--check-deps` | false | Check dependency status |

```bash
# List plugins
feishu-webhook-bot plugin list

# List with dependency check
feishu-webhook-bot plugin list --check-deps
```

##### plugin validate

Validate plugin configurations.

```bash
feishu-webhook-bot plugin validate [PLUGIN_NAME] [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `-c, --config` | config.yaml | Configuration file |
| `PLUGIN_NAME` | (all) | Specific plugin to validate |

```bash
# Validate all plugins
feishu-webhook-bot plugin validate

# Validate specific plugin
feishu-webhook-bot plugin validate system-monitor
```

##### plugin info

Show detailed plugin information.

```bash
feishu-webhook-bot plugin info PLUGIN_NAME [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `-c, --config` | config.yaml | Configuration file |

```bash
feishu-webhook-bot plugin info system-monitor
```

##### plugin template

Generate configuration template for a plugin.

```bash
feishu-webhook-bot plugin template PLUGIN_NAME [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `-c, --config` | config.yaml | Configuration file |
| `-o, --output` | (stdout) | Output file |

```bash
# Print template to stdout
feishu-webhook-bot plugin template system-monitor

# Save template to file
feishu-webhook-bot plugin template system-monitor -o system-monitor.yaml
```

## Environment Variables

The CLI respects these environment variables:

| Variable | Description |
|----------|-------------|
| `FEISHU_BOT_*` | Configuration overrides (see config docs) |
| `FEISHU_WEBHOOK_URL` | Default webhook URL |
| `FEISHU_WEBHOOK_SECRET` | Default webhook secret |

## Configuration File

The CLI uses YAML configuration files. See [YAML Configuration Guide](../guides/yaml-configuration-guide.md) for details.

### Minimal Configuration

```yaml
webhooks:
  - name: default
    url: "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_URL"
```

### Full Configuration

See `config.example.yaml` or `config.enhanced.example.yaml` for complete examples.

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |

## Examples

### Quick Start

```bash
# 1. Generate config
feishu-webhook-bot init -o config.yaml

# 2. Edit config.yaml with your webhook URL

# 3. Create plugins directory
mkdir plugins

# 4. Start bot
feishu-webhook-bot start
```

### Development Workflow

```bash
# Start with debug logging
feishu-webhook-bot start --debug

# Or use web UI for configuration
feishu-webhook-bot webui
```

### Production Deployment

```bash
# Use production config
feishu-webhook-bot start -c config.production.yaml

# Or with systemd service
# See deployment documentation
```

### Testing Messages

```bash
# Test webhook connectivity
feishu-webhook-bot send -w "$FEISHU_WEBHOOK_URL" -t "Test message"

# Test with signing
feishu-webhook-bot send -w "$FEISHU_WEBHOOK_URL" -s "$FEISHU_SECRET" -t "Signed test"
```

## Troubleshooting

### Config Not Found

```text
Error: Configuration file not found: config.yaml
```

**Solution**: Run `feishu-webhook-bot init` to create a default config.

### Invalid Webhook URL

```text
Error: Webhook URL cannot be empty
```

**Solution**: Edit config.yaml and add your webhook URL.

### Plugin Not Loading

```text
Warning: Plugin 'my-plugin' failed to load
```

**Solution**: Check plugin file for syntax errors, verify it inherits from `BasePlugin`.

### Web UI Not Starting

```text
Error: NiceGUI not installed
```

**Solution**: Install NiceGUI: `pip install nicegui`

## See Also

- [Getting Started](../getting-started/first-steps.md) - Quick start guide
- [Web UI Guide](../guides/webui-guide.md) - Web interface documentation
- [Plugin Development](../guides/plugin-guide.md) - Creating plugins
- [YAML Configuration](../guides/yaml-configuration-guide.md) - Configuration reference
