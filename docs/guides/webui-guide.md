# Web UI Guide

This guide explains how to use the NiceGUI-based web interface for configuring and controlling the Feishu Webhook Bot.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Starting the Web UI](#starting-the-web-ui)
- [Interface Overview](#interface-overview)
- [Configuration Management](#configuration-management)
- [Bot Control](#bot-control)
- [Log Viewer](#log-viewer)
- [Authentication](#authentication)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)

## Overview

The Web UI provides a browser-based interface for:

- Editing bot configuration with validation
- Starting, stopping, and restarting the bot
- Viewing real-time logs
- Managing plugins
- Monitoring bot status

## Installation

The Web UI requires NiceGUI:

```bash
# Using pip
pip install nicegui

# Using uv
uv add nicegui
```

## Starting the Web UI

### Via CLI

```bash
# Default settings (localhost:8080)
feishu-webhook-bot webui

# Custom host and port
feishu-webhook-bot webui --host 0.0.0.0 --port 9000

# With custom config
feishu-webhook-bot webui -c production.yaml
```

### Via Python

```python
from feishu_webhook_bot.config_ui import run_ui

# Start with defaults
run_ui(config_path="config.yaml")

# Custom settings
run_ui(
    config_path="config.yaml",
    host="0.0.0.0",
    port=8080,
)
```

### Via Module

```bash
python -m feishu_webhook_bot.config_ui --config config.yaml --host 127.0.0.1 --port 8080
```

## Interface Overview

The Web UI consists of several sections:

### Header

- Bot name and version
- Status indicator (Running/Stopped)
- Quick action buttons

### Navigation

- **Configuration**: Edit bot settings
- **Plugins**: Manage plugins
- **Logs**: View real-time logs
- **Status**: Monitor bot status

### Main Content Area

Displays the currently selected section.

## Configuration Management

### Editing Configuration

The configuration editor provides:

- **Syntax highlighting**: YAML syntax highlighting
- **Validation**: Real-time validation with error messages
- **Auto-save**: Optional auto-save on changes
- **Reset**: Revert to last saved configuration

### Configuration Sections

#### Webhooks

Configure webhook endpoints:

```yaml
webhooks:
  - name: default
    url: https://open.feishu.cn/...
    secret: your-secret
```

- Add/remove webhooks
- Edit URL and secret
- Test webhook connectivity

#### Scheduler

Configure the scheduler:

```yaml
scheduler:
  enabled: true
  timezone: Asia/Shanghai
  job_store_type: memory
```

- Enable/disable scheduler
- Set timezone
- Configure job persistence

#### Plugins

Configure plugin settings:

```yaml
plugins:
  enabled: true
  plugin_dir: plugins
  auto_reload: true
```

- Enable/disable plugins
- Set plugin directory
- Toggle hot-reload

#### Logging

Configure logging:

```yaml
logging:
  level: INFO
  log_file: logs/bot.log
  max_bytes: 10485760
  backup_count: 5
```

- Set log level
- Configure log file
- Set rotation settings

#### AI Configuration

Configure AI settings (if enabled):

```yaml
ai:
  enabled: true
  model: openai:gpt-4o
  api_key: ${OPENAI_API_KEY}
```

- Enable/disable AI
- Select model
- Configure API settings

### Saving Configuration

1. Make changes in the editor
2. Click "Save" button
3. Configuration is validated
4. If valid, changes are saved
5. Optionally restart bot to apply changes

## Bot Control

### Start Bot

1. Click "Start" button
2. Bot initializes with current configuration
3. Status changes to "Running"
4. Logs show startup messages

### Stop Bot

1. Click "Stop" button
2. Bot gracefully shuts down
3. Status changes to "Stopped"
4. Logs show shutdown messages

### Restart Bot

1. Click "Restart" button
2. Bot stops and starts with current configuration
3. Useful after configuration changes

### Status Indicators

| Status | Color | Description |
|--------|-------|-------------|
| Running | Green | Bot is active |
| Stopped | Red | Bot is not running |
| Starting | Yellow | Bot is initializing |
| Error | Red | Bot encountered an error |

## Log Viewer

### Features

- **Real-time updates**: Logs stream in real-time
- **Filtering**: Filter by log level
- **Search**: Search log messages
- **Auto-scroll**: Automatically scroll to new logs
- **Clear**: Clear log display

### Log Levels

| Level | Color | Description |
|-------|-------|-------------|
| DEBUG | Gray | Detailed debug information |
| INFO | Blue | General information |
| WARNING | Yellow | Warning messages |
| ERROR | Red | Error messages |
| CRITICAL | Red (bold) | Critical errors |

### Filtering Logs

1. Select log level from dropdown
2. Only logs at or above selected level are shown
3. Use search box for text filtering

## Authentication

When authentication is enabled, the Web UI requires login.

### Login Page

1. Navigate to Web UI URL
2. Enter username/email and password
3. Click "Login"
4. Redirected to main interface

### Registration

If registration is enabled:

1. Click "Register" link
2. Enter email, username, and password
3. Password must meet strength requirements
4. Click "Register"
5. Redirected to login or main interface

### Protected Pages

All configuration and control pages require authentication when enabled.

### Logout

1. Click user menu in header
2. Select "Logout"
3. Session is cleared
4. Redirected to login page

## Customization

### Custom Theme

The Web UI uses NiceGUI's theming system:

```python
from nicegui import ui

# Set dark mode
ui.dark_mode().enable()

# Custom colors
ui.colors(primary='#1976D2', secondary='#424242')
```

### Custom Pages

Add custom pages to the Web UI:

```python
from nicegui import ui
from feishu_webhook_bot.config_ui import app

@ui.page('/custom')
def custom_page():
    ui.label('Custom Page')
    ui.button('Custom Action', on_click=lambda: ui.notify('Clicked!'))
```

### Embedding in Existing App

```python
from fastapi import FastAPI
from nicegui import ui
from feishu_webhook_bot.config_ui import setup_config_ui

app = FastAPI()

# Add config UI routes
setup_config_ui(app, config_path="config.yaml")

# Add your own routes
@app.get("/api/custom")
def custom_api():
    return {"status": "ok"}
```

## Troubleshooting

### Web UI Not Starting

**Problem**: `ModuleNotFoundError: No module named 'nicegui'`

**Solution**: Install NiceGUI:

```bash
pip install nicegui
```

### Port Already in Use

**Problem**: `Address already in use`

**Solution**: Use a different port:

```bash
feishu-webhook-bot webui --port 9000
```

### Configuration Not Saving

**Problem**: Changes not persisting

**Solutions**:

1. Check file permissions
2. Verify config path is correct
3. Check for validation errors

### Bot Not Starting from UI

**Problem**: Bot fails to start

**Solutions**:

1. Check logs for error messages
2. Verify configuration is valid
3. Check webhook URL is correct
4. Ensure required dependencies are installed

### Authentication Issues

**Problem**: Cannot login

**Solutions**:

1. Verify credentials are correct
2. Check if account is locked
3. Reset password if needed
4. Check auth database connection

### Logs Not Updating

**Problem**: Log viewer not showing new logs

**Solutions**:

1. Check if bot is running
2. Verify log file path in config
3. Refresh the page
4. Check browser console for errors

## Best Practices

### Security

1. **Use authentication** in production
2. **Bind to localhost** unless remote access is needed
3. **Use HTTPS** with a reverse proxy for production
4. **Change default JWT secret** in production

### Performance

1. **Limit log history** to prevent memory issues
2. **Use log file** instead of in-memory logging
3. **Enable auto-save** cautiously

### Deployment

1. **Use reverse proxy** (nginx, Caddy) for production
2. **Configure SSL/TLS** for secure connections
3. **Set up monitoring** for the Web UI process
4. **Use systemd** or similar for process management

### Example nginx Configuration

```nginx
server {
    listen 443 ssl;
    server_name bot.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## See Also

- [CLI Reference](../reference/cli-reference.md) - Command-line interface
- [Authentication](../security/authentication.md) - Authentication system
- [YAML Configuration](yaml-configuration-guide.md) - Configuration reference
- [NiceGUI Documentation](https://nicegui.io/) - NiceGUI framework
