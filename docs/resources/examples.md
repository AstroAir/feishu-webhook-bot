# Examples

A collection of practical examples for the Feishu Webhook Bot framework.

## Table of Contents

- [Basic Examples](#basic-examples)
- [Message Types](#message-types)
- [Plugin Examples](#plugin-examples)
- [Automation Examples](#automation-examples)
- [Chat Controller Examples](#chat-controller-examples)
- [AI Examples](#ai-examples)
- [Integration Examples](#integration-examples)
- [Advanced Patterns](#advanced-patterns)

## Basic Examples

### Hello World Bot

```python
from feishu_webhook_bot import FeishuBot

# Create bot from config
bot = FeishuBot.from_config("config.yaml")

# Send a simple message
bot.send_text("Hello, World!")

# Start the bot (enables scheduler and plugins)
bot.start()
```

### Send Message with Client

```python
from feishu_webhook_bot.core import FeishuWebhookClient, WebhookConfig

# Create client
config = WebhookConfig(
    name="default",
    url="https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
    secret="your-secret",
)

with FeishuWebhookClient(config) as client:
    # Send text
    client.send_text("Hello!")

    # Send markdown
    client.send_markdown("**Bold** and *italic*")
```

## Message Types

### Text Message

```python
# Simple text
bot.send_text("Hello, Feishu!")

# With mentions
bot.send_text("Hello @all, important update!")
```

### Markdown Message

```python
# Basic markdown
bot.send_markdown("""
# Title

**Bold text** and *italic text*

- Item 1
- Item 2

[Link](https://example.com)
""")
```

### Rich Text (Post)

```python
from feishu_webhook_bot.core.client import RichTextBuilder

# Build rich text
rich_text = (
    RichTextBuilder()
    .set_title("Notification")
    .add_text("Hello ")
    .add_link("click here", "https://example.com")
    .add_text(" for details.")
    .new_line()
    .add_at_all()
    .build()
)

bot.send_rich_text(rich_text)
```

### Interactive Card

```python
from feishu_webhook_bot.core.client import CardBuilder

# Build card
card = (
    CardBuilder()
    .set_header("🔔 Alert", template="red")
    .add_markdown("**Server Status**: Critical")
    .add_divider()
    .add_fields([
        {"title": "CPU", "value": "95%"},
        {"title": "Memory", "value": "87%"},
    ])
    .add_button("View Dashboard", url="https://dashboard.example.com")
    .add_button("Acknowledge", callback="ack_alert")
    .build()
)

bot.send_card(card)
```

### Image Message

```python
# Send image by key
bot.send_image("img_v2_xxx")

# Upload and send image
from feishu_webhook_bot.core import ImageUploader

uploader = ImageUploader(app_id="xxx", app_secret="xxx")
image_key = uploader.upload("path/to/image.png")
bot.send_image(image_key)
```

### Template Message

```yaml
# config.yaml
templates:
  alert:
    type: card
    header:
      title: "⚠️ {level}: {title}"
      template: "{color}"
    elements:
      - type: markdown
        content: "{message}"
      - type: divider
      - type: fields
        fields:
          - title: "Time"
            value: "{timestamp}"
          - title: "Source"
            value: "{source}"
```

```python
# Use template
bot.send_template("alert",
    level="WARNING",
    title="High CPU Usage",
    color="yellow",
    message="CPU usage exceeded 80%",
    timestamp="2025-01-15 10:30:00",
    source="server-01",
)
```

## Plugin Examples

### Simple Greeting Plugin

```python
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class GreetingPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="greeting",
            version="1.0.0",
            description="Sends daily greetings",
        )

    def on_enable(self) -> None:
        self.register_job(
            self.morning_greeting,
            trigger='cron',
            hour=9,
            minute=0,
        )
        self.register_job(
            self.evening_greeting,
            trigger='cron',
            hour=18,
            minute=0,
        )

    def morning_greeting(self) -> None:
        self.client.send_text("☀️ Good morning! Have a productive day!")

    def evening_greeting(self) -> None:
        self.client.send_text("🌙 Good evening! Time to wrap up!")
```

### System Monitor Plugin

```python
import psutil
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata
from feishu_webhook_bot.core.client import CardBuilder

class SystemMonitorPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="system-monitor",
            version="1.0.0",
            description="Monitors system resources",
        )

    def on_enable(self) -> None:
        self.cpu_threshold = self.get_config("cpu_threshold", 80)
        self.memory_threshold = self.get_config("memory_threshold", 80)

        self.register_job(
            self.check_resources,
            trigger='interval',
            minutes=5,
        )

    def check_resources(self) -> None:
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent

        if cpu > self.cpu_threshold or memory > self.memory_threshold:
            self.send_alert(cpu, memory)

    def send_alert(self, cpu: float, memory: float) -> None:
        card = (
            CardBuilder()
            .set_header("⚠️ Resource Alert", template="red")
            .add_fields([
                {"title": "CPU", "value": f"{cpu}%"},
                {"title": "Memory", "value": f"{memory}%"},
            ])
            .build()
        )
        self.client.send_card(card)
```

### Weather Plugin

```python
import httpx
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class WeatherPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="weather",
            version="1.0.0",
            description="Daily weather updates",
        )

    def on_enable(self) -> None:
        self.api_key = self.get_config("api_key")
        self.city = self.get_config("city", "Shanghai")

        self.register_job(
            self.send_weather,
            trigger='cron',
            hour=7,
            minute=30,
        )

    def send_weather(self) -> None:
        weather = self.fetch_weather()
        message = f"""
🌤️ **Weather for {self.city}**

Temperature: {weather['temp']}°C
Condition: {weather['condition']}
Humidity: {weather['humidity']}%
        """
        self.client.send_markdown(message)

    def fetch_weather(self) -> dict:
        # Implement weather API call
        response = httpx.get(
            f"https://api.weather.com/v1/current",
            params={"city": self.city, "key": self.api_key}
        )
        return response.json()
```

## Automation Examples

### Daily Report

```yaml
automation:
  rules:
    - name: "daily-report"
      trigger:
        type: schedule
        cron: "0 9 * * 1-5"  # Weekdays at 9 AM
      action:
        type: send_template
        template: "daily_report"
        parameters:
          date: "${event_date}"
        webhooks: ["default"]
```

### Health Check

```yaml
automation:
  rules:
    - name: "api-health-check"
      trigger:
        type: schedule
        interval: 300  # Every 5 minutes
      action:
        type: http_request
        request:
          method: GET
          url: "https://api.example.com/health"
          timeout: 10
          expected_status: 200
      on_failure:
        type: send_text
        text: "⚠️ API health check failed!"
        webhooks: ["alerts"]
```

### Event-Driven Notification

```yaml
automation:
  rules:
    - name: "deployment-notification"
      trigger:
        type: event
        event_type: "deployment"
        filters:
          environment: "production"
      action:
        type: send_template
        template: "deployment"
        parameters:
          version: "${event.version}"
          deployer: "${event.user}"
        webhooks: ["default", "devops"]
```

### Conditional Automation

```yaml
automation:
  rules:
    - name: "business-hours-alert"
      trigger:
        type: event
        event_type: "alert"
      conditions:
        - type: time_range
          start_time: "09:00"
          end_time: "18:00"
        - type: day_of_week
          days: ["monday", "tuesday", "wednesday", "thursday", "friday"]
      action:
        type: send_text
        text: "🚨 Alert: ${event.message}"
        webhooks: ["default"]
```

## Chat Controller Examples

### Basic Chat Controller

```python
from feishu_webhook_bot.chat import create_chat_controller, ChatConfig
from feishu_webhook_bot.ai import AIAgent, AIConfig
from feishu_webhook_bot.providers import FeishuProvider

# Create AI agent
ai_config = AIConfig(enabled=True, model="openai:gpt-4o")
ai_agent = AIAgent(ai_config)

# Create provider
provider = FeishuProvider(config=feishu_config)

# Create chat controller
controller = create_chat_controller(
    ai_agent=ai_agent,
    providers={"feishu": provider},
    config=ChatConfig(
        require_at_in_groups=True,
        max_message_length=2000,
    ),
    available_models=["gpt-4o", "gpt-4o-mini", "claude-3-sonnet"],
)

# Handle incoming message
await controller.handle_incoming(message)
```

### Multi-Platform Chat

```python
from feishu_webhook_bot.chat import ChatController, ChatConfig
from feishu_webhook_bot.providers import FeishuProvider, NapcatProvider
from feishu_webhook_bot.core.message_parsers import FeishuMessageParser, QQMessageParser

# Create providers
feishu_provider = FeishuProvider(config=feishu_config)
qq_provider = NapcatProvider(config=napcat_config)

# Create parsers
feishu_parser = FeishuMessageParser(bot_open_id="ou_bot_xxx")
qq_parser = QQMessageParser(bot_qq="123456789")

# Create controller
controller = ChatController(
    ai_agent=ai_agent,
    providers={
        "feishu": feishu_provider,
        "qq": qq_provider,
    },
    config=ChatConfig(enable_in_groups=True),
)

# Handle Feishu event
@app.post("/feishu/webhook")
async def feishu_webhook(payload: dict):
    message = feishu_parser.parse(payload)
    if message:
        await controller.handle_incoming(message)

# Handle QQ event
@app.post("/qq/webhook")
async def qq_webhook(payload: dict):
    message = qq_parser.parse(payload)
    if message:
        await controller.handle_incoming(message)
```

### Chat with Middleware

```python
from feishu_webhook_bot.chat import ChatController, ChatContext

controller = ChatController(ai_agent=ai_agent, providers=providers)

# Logging middleware
@controller.middleware
async def log_messages(ctx: ChatContext) -> bool:
    logger.info("Message from %s: %s", ctx.user_key, ctx.message.content[:50])
    return True

# Rate limiting middleware
from collections import defaultdict
from datetime import datetime, timedelta

rate_limits = defaultdict(list)

@controller.middleware
async def rate_limit(ctx: ChatContext) -> bool:
    now = datetime.now()
    user_key = ctx.user_key

    # Clean old entries
    rate_limits[user_key] = [
        t for t in rate_limits[user_key]
        if now - t < timedelta(minutes=1)
    ]

    if len(rate_limits[user_key]) >= 10:
        await controller.send_reply(ctx.message, "请稍后再试")
        return False

    rate_limits[user_key].append(now)
    return True
```

### Custom Commands

```python
from feishu_webhook_bot.ai.commands import CommandHandler, CommandResult

# Get command handler from controller
handler = controller.command_handler

# Register custom command
@handler.register("/weather")
async def weather_cmd(handler, message, args):
    if not args:
        return CommandResult(False, "用法: /weather <城市>")

    city = args[0]
    weather = await fetch_weather(city)

    return CommandResult(
        success=True,
        response=f"**{city}天气:** {weather['temp']}°C, {weather['condition']}",
    )

# Register admin command
@handler.register("/admin")
async def admin_cmd(handler, message, args):
    if message.sender_id not in ADMIN_IDS:
        return CommandResult(False, "无权限")

    # Admin operations...
    return CommandResult(True, "操作完成")
```

## AI Examples

### Simple Chat

```python
from feishu_webhook_bot import FeishuBot

bot = FeishuBot.from_config("config.yaml")

# Chat with AI
response = bot.ai_agent.chat("user123", "What is Python?")
print(response)

# Continue conversation
response = bot.ai_agent.chat("user123", "Give me an example")
print(response)
```

### AI with Custom System Prompt

```python
response = bot.ai_agent.chat(
    user_id="user123",
    message="Analyze this code",
    system_prompt="You are a senior code reviewer. Be concise and focus on issues.",
)
```

### AI-Powered Task

```yaml
tasks:
  - name: "ai-summary"
    schedule:
      mode: cron
      arguments: { hour: "18", minute: "0" }
    actions:
      - type: http_request
        request:
          url: "https://api.example.com/daily-logs"
          save_as: "logs"

      - type: ai_query
        ai_prompt: |
          Summarize these logs and highlight any issues:
          ${logs}
        ai_save_response_as: "summary"

      - type: send_message
        message: |
          📊 Daily Summary

          ${summary}
        webhooks: ["default"]
```

### Multi-Agent Workflow

```python
from feishu_webhook_bot.ai import MultiAgentOrchestrator

orchestrator = MultiAgentOrchestrator(config)

# Define agents
orchestrator.add_agent("researcher", system_prompt="You are a researcher...")
orchestrator.add_agent("writer", system_prompt="You are a technical writer...")
orchestrator.add_agent("reviewer", system_prompt="You are an editor...")

# Run workflow
result = await orchestrator.run_workflow([
    {"agent": "researcher", "task": "Research topic X"},
    {"agent": "writer", "task": "Write article based on research"},
    {"agent": "reviewer", "task": "Review and improve article"},
])
```

## Integration Examples

### GitHub Webhook Handler

```python
from fastapi import FastAPI, Request
from feishu_webhook_bot import FeishuBot

app = FastAPI()
bot = FeishuBot.from_config("config.yaml")

@app.post("/github-webhook")
async def github_webhook(request: Request):
    event = request.headers.get("X-GitHub-Event")
    payload = await request.json()

    if event == "push":
        message = f"""
📦 **New Push to {payload['repository']['name']}**

Branch: {payload['ref']}
Commits: {len(payload['commits'])}
Pusher: {payload['pusher']['name']}
        """
        bot.send_markdown(message)

    elif event == "pull_request":
        pr = payload['pull_request']
        message = f"""
🔀 **Pull Request {payload['action'].title()}**

Title: {pr['title']}
Author: {pr['user']['login']}
URL: {pr['html_url']}
        """
        bot.send_markdown(message)

    return {"status": "ok"}
```

### Slack to Feishu Bridge

```python
from slack_bolt import App
from feishu_webhook_bot import FeishuBot

slack_app = App(token="xoxb-...")
feishu_bot = FeishuBot.from_config("config.yaml")

@slack_app.message()
def forward_to_feishu(message, say):
    # Forward Slack messages to Feishu
    feishu_bot.send_text(f"[Slack] {message['user']}: {message['text']}")
```

### Database Alert System

```python
import asyncio
from feishu_webhook_bot import FeishuBot
from feishu_webhook_bot.core.client import CardBuilder

bot = FeishuBot.from_config("config.yaml")

async def monitor_database():
    while True:
        # Check database metrics
        metrics = await get_db_metrics()

        if metrics['connections'] > 100:
            card = (
                CardBuilder()
                .set_header("🗄️ Database Alert", template="yellow")
                .add_markdown(f"High connection count: {metrics['connections']}")
                .add_button("View Dashboard", url="https://db.example.com")
                .build()
            )
            bot.send_card(card)

        await asyncio.sleep(60)

asyncio.run(monitor_database())
```

## Advanced Patterns

### Circuit Breaker Pattern

```python
from feishu_webhook_bot.core import CircuitBreaker, CircuitBreakerConfig

# Configure circuit breaker
config = CircuitBreakerConfig(
    failure_threshold=5,
    reset_timeout=30.0,
)
breaker = CircuitBreaker("external-api", config)

async def call_external_api():
    async with breaker:
        response = await httpx.get("https://api.example.com")
        return response.json()
```

### Message Queue Pattern

```python
from feishu_webhook_bot.core import MessageQueue

# Create queue
queue = MessageQueue(max_size=1000, batch_size=10)

# Add messages
await queue.enqueue({"type": "text", "content": "Hello"})
await queue.enqueue({"type": "text", "content": "World"})

# Process in batches
async for batch in queue.consume():
    for message in batch:
        await send_message(message)
```

### Retry with Backoff

```python
from feishu_webhook_bot.core import retry_with_backoff

@retry_with_backoff(max_retries=3, base_delay=1.0)
async def send_important_message(message: str):
    response = await client.send_text(message)
    if not response.success:
        raise Exception("Send failed")
    return response
```

### Plugin Communication

```python
# Plugin A
class ProducerPlugin(BasePlugin):
    def produce_data(self):
        data = {"value": 42}
        self.emit_event("data_ready", data)

# Plugin B
class ConsumerPlugin(BasePlugin):
    def on_enable(self):
        self.subscribe_event("data_ready", self.handle_data)

    def handle_data(self, data):
        self.client.send_text(f"Received: {data['value']}")
```

### Custom Provider

```python
from feishu_webhook_bot.core.provider import BaseProvider, Message, SendResult

class CustomProvider(BaseProvider):
    def send_message(self, message: Message, target: str) -> SendResult:
        # Custom sending logic
        try:
            response = self._send_to_custom_api(message, target)
            return SendResult(success=True, message_id=response.id)
        except Exception as e:
            return SendResult(success=False, error=str(e))
```

## See Also

- [Quick Start](../getting-started/quickstart.md) - Get started quickly
- [Plugin Development](../guides/plugin-guide.md) - Create plugins
- [Automation Guide](../guides/automation-guide.md) - Automation rules
- [AI Features](../ai/multi-provider.md) - AI integration
