# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Feishu Webhook Bot.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Installation Issues](#installation-issues)
- [Configuration Issues](#configuration-issues)
- [Message Sending Issues](#message-sending-issues)
- [Plugin Issues](#plugin-issues)
- [Scheduler Issues](#scheduler-issues)
- [AI Feature Issues](#ai-feature-issues)
- [Authentication Issues](#authentication-issues)
- [Performance Issues](#performance-issues)
- [Network Issues](#network-issues)
- [Getting Help](#getting-help)

## Quick Diagnostics

### Check Bot Status

```bash
# Check if bot is running
feishu-webhook-bot --version

# Validate configuration
python -c "from feishu_webhook_bot.core import BotConfig; BotConfig.from_yaml('config.yaml'); print('Config OK')"

# Test webhook connectivity
feishu-webhook-bot send -w "YOUR_WEBHOOK_URL" -t "Test message"
```

### Enable Debug Logging

```bash
# Start with debug mode
feishu-webhook-bot start --debug

# Or set in config
logging:
  level: DEBUG
```

### Check Logs

```bash
# View recent logs
tail -f logs/bot.log

# Search for errors
grep -i error logs/bot.log | tail -20
```

## Installation Issues

### Python Version Error

**Error:**

```text
ERROR: Package requires Python >=3.10
```

**Solution:**

```bash
# Check Python version
python --version

# Install Python 3.12 using pyenv
pyenv install 3.12
pyenv local 3.12

# Or use system package manager
sudo apt install python3.12
```

### Dependency Conflicts

**Error:**

```text
ERROR: Cannot install package due to conflicting dependencies
```

**Solution:**

```bash
# Create fresh virtual environment
python -m venv venv
source venv/bin/activate

# Install with clean dependencies
pip install --no-cache-dir feishu-webhook-bot
```

### Permission Denied

**Error:**

```text
PermissionError: [Errno 13] Permission denied
```

**Solution:**

```bash
# Use virtual environment instead of system Python
python -m venv venv
source venv/bin/activate
pip install feishu-webhook-bot

# Or use --user flag
pip install --user feishu-webhook-bot
```

### Missing System Dependencies

**Error:**

```text
error: command 'gcc' failed
```

**Solution:**

```bash
# Ubuntu/Debian
sudo apt-get install python3-dev build-essential

# CentOS/RHEL
sudo yum install python3-devel gcc

# macOS
xcode-select --install
```

## Configuration Issues

### Invalid YAML Syntax

**Error:**

```text
yaml.scanner.ScannerError: mapping values are not allowed here
```

**Solution:**

```yaml
# Wrong - missing space after colon
webhooks:
  - name:default  # Error!

# Correct
webhooks:
  - name: default
```

### Missing Required Field

**Error:**

```text
pydantic.ValidationError: 1 validation error for BotConfig
webhooks -> 0 -> url
  field required
```

**Solution:**

```yaml
webhooks:
  - name: default
    url: "https://open.feishu.cn/..."  # Add required field
```

### Environment Variable Not Found

**Error:**

```text
KeyError: 'FEISHU_WEBHOOK_URL'
```

**Solution:**

```bash
# Set environment variable
export FEISHU_WEBHOOK_URL="https://..."

# Or use .env file
echo 'FEISHU_WEBHOOK_URL=https://...' >> .env

# Or use default value in config
url: "${FEISHU_WEBHOOK_URL:-https://default-url}"
```

### Invalid Configuration Value

**Error:**

```text
pydantic.ValidationError: value is not a valid integer
```

**Solution:**

```yaml
# Wrong
scheduler:
  job_store_type: 123  # Should be string

# Correct
scheduler:
  job_store_type: "sqlite"
```

## Message Sending Issues

### Webhook URL Invalid

**Error:**

```text
httpx.HTTPStatusError: 400 Bad Request
```

**Causes & Solutions:**

1. **Invalid URL format**

   ```yaml
   # Wrong
   url: "open.feishu.cn/..."
   
   # Correct
   url: "https://open.feishu.cn/..."
   ```

2. **Expired webhook**
   - Create a new webhook in Feishu

3. **Bot removed from group**
   - Re-add the bot to the group

### Signature Verification Failed

**Error:**

```text
{"code": 19021, "msg": "sign match fail"}
```

**Solution:**

```yaml
# Ensure secret matches Feishu configuration
webhooks:
  - name: default
    url: "https://..."
    secret: "exact-secret-from-feishu"  # Must match exactly
```

### Message Too Large

**Error:**

```text
{"code": 9499, "msg": "message too large"}
```

**Solution:**

```python
# Split large messages
def send_large_message(text, max_length=4000):
    for i in range(0, len(text), max_length):
        bot.send_text(text[i:i+max_length])
```

### Rate Limited

**Error:**

```text
{"code": 9499, "msg": "request too frequent"}
```

**Solution:**

```yaml
# Enable message queue with rate limiting
message_queue:
  enabled: true
  batch_size: 5
  flush_interval: 1.0  # 1 second between batches
```

### Connection Timeout

**Error:**

```text
httpx.ConnectTimeout: Connection timeout
```

**Solution:**

```yaml
# Increase timeout
webhooks:
  - name: default
    timeout: 30.0  # Increase from default 10s

# Or check network
ping open.feishu.cn
```

## Plugin Issues

### Plugin Not Loading

**Error:**

```text
WARNING: Failed to load plugin 'my_plugin'
```

**Causes & Solutions:**

1. **Syntax error in plugin**

   ```bash
   python -m py_compile plugins/my_plugin.py
   ```

2. **Missing BasePlugin inheritance**

   ```python
   # Wrong
   class MyPlugin:
       pass
   
   # Correct
   from feishu_webhook_bot.plugins import BasePlugin
   class MyPlugin(BasePlugin):
       pass
   ```

3. **Missing metadata method**

   ```python
   def metadata(self) -> PluginMetadata:
       return PluginMetadata(
           name="my-plugin",
           version="1.0.0",
       )
   ```

### Plugin Dependencies Missing

**Error:**

```text
ModuleNotFoundError: No module named 'some_package'
```

**Solution:**

```bash
# Install missing dependency
pip install some_package

# Or add to plugin requirements
# plugins/my_plugin.py
"""
Requirements:
    some_package>=1.0.0
"""
```

### Plugin Configuration Error

**Error:**

```text
KeyError: 'my_setting'
```

**Solution:**

```yaml
# Add plugin settings to config
plugins:
  plugin_settings:
    my-plugin:
      my_setting: "value"
```

### Hot Reload Not Working

**Causes & Solutions:**

1. **Hot reload disabled**

   ```yaml
   plugins:
     auto_reload: true
   ```

2. **File watcher issue**

   ```bash
   # Check file permissions
   ls -la plugins/
   ```

## Scheduler Issues

### Jobs Not Running

**Causes & Solutions:**

1. **Scheduler disabled**

   ```yaml
   scheduler:
     enabled: true
   ```

2. **Wrong timezone**

   ```yaml
   scheduler:
     timezone: "Asia/Shanghai"  # Set correct timezone
   ```

3. **Job paused**

   ```python
   scheduler.resume_job('job-id')
   ```

### Missed Jobs

**Solution:**

```yaml
scheduler:
  job_defaults:
    misfire_grace_time: 300  # 5 minutes grace period
    coalesce: true  # Combine missed runs
```

### Job Store Errors

**Error:**

```text
sqlite3.OperationalError: database is locked
```

**Solution:**

```yaml
# Use memory store for development
scheduler:
  job_store_type: "memory"

# Or ensure single instance for SQLite
scheduler:
  job_store_path: "/tmp/jobs.db"  # Use unique path
```

## AI Feature Issues

### API Key Invalid

**Error:**

```text
openai.AuthenticationError: Invalid API key
```

**Solution:**

```bash
# Verify API key
echo $OPENAI_API_KEY

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Model Not Found

**Error:**

```text
openai.NotFoundError: model 'gpt-5' not found
```

**Solution:**

```yaml
ai:
  model: "openai:gpt-4o"  # Use valid model name
```

### Rate Limit Exceeded

**Error:**

```text
openai.RateLimitError: Rate limit exceeded
```

**Solution:**

```yaml
ai:
  # Add rate limiting
  rate_limit:
    requests_per_minute: 20
    tokens_per_minute: 40000
```

### Context Too Long

**Error:**

```text
openai.BadRequestError: maximum context length exceeded
```

**Solution:**

```yaml
ai:
  conversation:
    max_history: 10  # Reduce history
    max_tokens: 4000  # Limit context
```

## Authentication Issues

### Login Failed

**Error:**

```text
401 Unauthorized: Invalid credentials
```

**Solution:**

```bash
# Reset password
feishu-webhook-bot auth reset-password user@example.com

# Check user exists
feishu-webhook-bot auth list-users
```

### JWT Token Expired

**Error:**

```text
401 Unauthorized: Token expired
```

**Solution:**

```yaml
auth:
  access_token_expire_minutes: 60  # Increase TTL
  refresh_token_expire_days: 30
```

### Database Locked

**Error:**

```text
sqlite3.OperationalError: database is locked
```

**Solution:**

```bash
# Check for other processes
lsof data/auth.db

# Or use PostgreSQL for production
auth:
  database:
    url: "postgresql://user:pass@localhost/auth"
```

## Performance Issues

### High Memory Usage

**Causes & Solutions:**

1. **Large conversation history**

   ```yaml
   ai:
     conversation:
       max_history: 10
   ```

2. **Too many queued messages**

   ```yaml
   message_queue:
     max_size: 500
   ```

3. **Memory leak in plugin**
   - Review plugin code for leaks
   - Use memory profiler

### Slow Response Times

**Causes & Solutions:**

1. **Network latency**

   ```yaml
   http_client:
     timeout: 30.0
     http2: true  # Enable HTTP/2
   ```

2. **Too many retries**

   ```yaml
   webhooks:
     - name: default
       retry:
         max_retries: 2  # Reduce retries
   ```

3. **Blocking operations**
   - Use async operations
   - Move heavy tasks to background

### CPU Spikes

**Causes & Solutions:**

1. **Too frequent jobs**

   ```yaml
   # Increase interval
   schedule:
     interval: 60  # Every minute instead of every second
   ```

2. **Inefficient plugin code**
   - Profile plugin code
   - Optimize hot paths

## Network Issues

### SSL Certificate Error

**Error:**

```text
ssl.SSLCertVerificationError: certificate verify failed
```

**Solution:**

```yaml
# For development only - not recommended for production
http_client:
  verify_ssl: false

# Better: Install CA certificates
pip install certifi
```

### Proxy Issues

**Error:**

```text
httpx.ProxyError: Unable to connect to proxy
```

**Solution:**

```yaml
http_client:
  proxy: "http://proxy.example.com:8080"

# Or set environment variable
export HTTP_PROXY="http://proxy.example.com:8080"
export HTTPS_PROXY="http://proxy.example.com:8080"
```

### DNS Resolution Failed

**Error:**

```text
httpx.ConnectError: Name or service not known
```

**Solution:**

```bash
# Check DNS
nslookup open.feishu.cn

# Use IP address temporarily
# Or configure DNS servers
```

## Getting Help

### Collect Diagnostic Information

```bash
# System info
python -c "import platform; print(platform.platform())"
python --version

# Package versions
pip show feishu-webhook-bot

# Configuration (remove secrets!)
cat config.yaml | grep -v secret | grep -v api_key

# Recent logs
tail -100 logs/bot.log
```

### Report an Issue

1. Search [existing issues](https://github.com/AstroAir/feishu-webhook-bot/issues)
2. Create a new issue with:
   - Python version
   - Package version
   - Configuration (sanitized)
   - Error message and stack trace
   - Steps to reproduce

### Community Support

- GitHub Discussions
- Issue Tracker

## See Also

- [FAQ](faq.md) - Frequently asked questions
- [Configuration Reference](../guides/configuration-reference.md) - All options
- [Deployment Guide](../deployment/deployment.md) - Production deployment
