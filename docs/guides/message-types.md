# Message Types Guide

Complete guide to all message types supported by the Feishu Webhook Bot.

## Table of Contents

- [Overview](#overview)
- [Text Messages](#text-messages)
- [Markdown Messages](#markdown-messages)
- [Rich Text (Post)](#rich-text-post)
- [Interactive Cards](#interactive-cards)
- [Image Messages](#image-messages)
- [File Sharing](#file-sharing)
- [Message Templates](#message-templates)
- [Best Practices](#best-practices)

## Overview

The framework supports multiple message types for different use cases:

| Type | Use Case | Rich Formatting | Interactive |
|------|----------|-----------------|-------------|
| Text | Simple notifications | ❌ | ❌ |
| Markdown | Formatted text | ✅ | ❌ |
| Rich Text | Complex formatting | ✅ | ❌ |
| Card | Interactive UI | ✅ | ✅ |
| Image | Visual content | ❌ | ❌ |

## Text Messages

The simplest message type for plain text notifications.

### Basic Usage

```python
from feishu_webhook_bot import FeishuBot

bot = FeishuBot.from_config("config.yaml")

# Simple text
bot.send_text("Hello, World!")

# With webhook selection
bot.send_text("Alert!", webhook="alerts")
```

### Mentions

```python
# Mention all users
bot.send_text("Attention @all: Important update!")

# Mention specific user (by user_id)
bot.send_text("Hello <at user_id=\"ou_xxx\">John</at>!")
```

### Character Limits

- Maximum length: ~4000 characters
- For longer content, use rich text or split into multiple messages

## Markdown Messages

Formatted text with Markdown syntax support.

### Basic Usage

```python
bot.send_markdown("""
# Heading

**Bold text** and *italic text*

- List item 1
- List item 2

[Link text](https://example.com)

`inline code`
""")
```

### Supported Syntax

| Element | Syntax | Example |
|---------|--------|---------|
| Bold | `**text**` | **bold** |
| Italic | `*text*` | *italic* |
| Strikethrough | `~~text~~` | ~~strikethrough~~ |
| Link | `[text](url)` | [link](https://example.com) |
| Inline code | `` `code` `` | `code` |
| Heading | `# text` | Heading |
| List | `- item` | • item |
| Ordered list | `1. item` | 1. item |

### Code Blocks

```python
bot.send_markdown("""
```python
def hello():
    print("Hello!")
```

""")

```

## Rich Text (Post)

Rich text format for complex formatting with multiple elements.

### Using RichTextBuilder

```python
from feishu_webhook_bot.core.client import RichTextBuilder

# Build rich text message
rich_text = (
    RichTextBuilder()
    .set_title("Daily Report")
    .add_text("Today's summary: ")
    .add_link("View details", "https://example.com")
    .new_line()
    .add_text("Status: ")
    .add_text("✅ Complete", bold=True)
    .new_line()
    .add_at_all()
    .build()
)

bot.send_rich_text(rich_text)
```

### Available Elements

```python
builder = RichTextBuilder()

# Text with styling
builder.add_text("Normal text")
builder.add_text("Bold text", bold=True)
builder.add_text("Italic text", italic=True)
builder.add_text("Underline", underline=True)
builder.add_text("Strikethrough", strikethrough=True)

# Links
builder.add_link("Click here", "https://example.com")

# Mentions
builder.add_at("ou_xxx", "John")  # Mention user
builder.add_at_all()              # Mention all

# Images (inline)
builder.add_image("img_v2_xxx")

# Line breaks
builder.new_line()

# Multiple paragraphs
builder.new_paragraph()
```

### Multi-language Support

```python
rich_text = (
    RichTextBuilder()
    .set_title("通知", lang="zh_cn")
    .set_title("Notification", lang="en_us")
    .add_text("中文内容", lang="zh_cn")
    .add_text("English content", lang="en_us")
    .build()
)
```

## Interactive Cards

The most powerful message type with rich UI components and interactivity.

### Using CardBuilder

```python
from feishu_webhook_bot.core.client import CardBuilder

card = (
    CardBuilder()
    .set_header("🔔 Notification", template="blue")
    .add_markdown("**Important:** System update scheduled")
    .add_divider()
    .add_fields([
        {"title": "Time", "value": "2025-01-15 10:00"},
        {"title": "Duration", "value": "30 minutes"},
    ])
    .add_button("View Details", url="https://example.com")
    .add_button("Acknowledge", callback="ack_notification")
    .build()
)

bot.send_card(card)
```

### Header Templates

Available color templates for card headers:

| Template | Color |
|----------|-------|
| `blue` | Blue |
| `wathet` | Light blue |
| `turquoise` | Turquoise |
| `green` | Green |
| `yellow` | Yellow |
| `orange` | Orange |
| `red` | Red |
| `carmine` | Carmine |
| `violet` | Violet |
| `purple` | Purple |
| `indigo` | Indigo |
| `grey` | Grey |

```python
card = CardBuilder().set_header("Error Alert", template="red")
```

### Card Elements

#### Markdown Content

```python
card.add_markdown("""
**Status Report**

| Metric | Value |
|--------|-------|
| CPU | 45% |
| Memory | 62% |
""")
```

#### Divider

```python
card.add_divider()
```

#### Fields (Grid Layout)

```python
card.add_fields([
    {"title": "Server", "value": "prod-01"},
    {"title": "Region", "value": "us-east-1"},
    {"title": "Status", "value": "🟢 Healthy"},
    {"title": "Uptime", "value": "99.9%"},
], columns=2)  # 2-column layout
```

#### Buttons

```python
# URL button
card.add_button("Open Dashboard", url="https://dashboard.example.com")

# Callback button (for event handling)
card.add_button("Approve", callback="approve_request", value={"id": "123"})

# Button with style
card.add_button("Delete", callback="delete", style="danger")
card.add_button("Confirm", callback="confirm", style="primary")
```

#### Images

```python
card.add_image("img_v2_xxx", alt="Screenshot")
```

#### Note (Footer)

```python
card.add_note("Last updated: 2025-01-15 10:30")
```

### Complete Card Example

```python
from feishu_webhook_bot.core.client import CardBuilder

card = (
    CardBuilder()
    # Header
    .set_header("🚨 Alert: High CPU Usage", template="red")
    
    # Content
    .add_markdown("""
**Server:** prod-web-01
**Time:** 2025-01-15 10:30:00

CPU usage has exceeded the threshold.
    """)
    
    .add_divider()
    
    # Metrics
    .add_fields([
        {"title": "CPU", "value": "95%"},
        {"title": "Memory", "value": "72%"},
        {"title": "Disk", "value": "45%"},
        {"title": "Network", "value": "Normal"},
    ], columns=2)
    
    .add_divider()
    
    # Actions
    .add_button("View Dashboard", url="https://monitor.example.com")
    .add_button("Acknowledge", callback="ack_alert", style="primary")
    .add_button("Escalate", callback="escalate", style="danger")
    
    # Footer
    .add_note("Alert ID: ALT-2025-001")
    
    .build()
)

bot.send_card(card)
```

### Card JSON (Advanced)

For complex cards, you can use raw JSON:

```python
card_json = {
    "config": {"wide_screen_mode": True},
    "header": {
        "title": {"tag": "plain_text", "content": "Custom Card"},
        "template": "blue"
    },
    "elements": [
        {
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**Hello World**"}
        }
    ]
}

bot.send_card(card_json)
```

## Image Messages

Send images directly in messages.

### Using Image Key

```python
# Send image by key (already uploaded)
bot.send_image("img_v2_xxx")
```

### Upload and Send

```python
from feishu_webhook_bot.core import ImageUploader

# Create uploader with app credentials
uploader = ImageUploader(
    app_id="cli_xxx",
    app_secret="xxx"
)

# Upload image
image_key = uploader.upload("path/to/image.png")

# Send
bot.send_image(image_key)
```

### Supported Formats

- PNG
- JPEG/JPG
- GIF
- BMP
- WebP

### Size Limits

- Maximum file size: 10MB
- Recommended: < 2MB for faster delivery

## File Sharing

Share files via Feishu.

### Share File Link

```python
bot.send_markdown("""
📎 **File Available**

[Download Report.pdf](https://example.com/files/report.pdf)
""")
```

### Using Card with File

```python
card = (
    CardBuilder()
    .set_header("📄 Document Shared")
    .add_markdown("**Report Q4 2024**\n\nClick below to download.")
    .add_button("Download PDF", url="https://example.com/report.pdf")
    .build()
)

bot.send_card(card)
```

## Message Templates

Pre-defined message templates for consistent formatting.

### Define Templates

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

  daily_report:
    type: card
    header:
      title: "📊 Daily Report - {date}"
      template: "blue"
    elements:
      - type: markdown
        content: |
          **Summary**
          {summary}
          
          **Key Metrics**
          - Active Users: {users}
          - Revenue: {revenue}
```

### Use Templates

```python
# Send alert
bot.send_template("alert",
    level="WARNING",
    title="High Memory Usage",
    color="yellow",
    message="Memory usage on server-01 is at 85%",
    timestamp="2025-01-15 10:30",
    source="monitoring-system"
)

# Send daily report
bot.send_template("daily_report",
    date="2025-01-15",
    summary="All systems operational",
    users="1,234",
    revenue="$12,345"
)
```

## Best Practices

### Choose the Right Type

| Scenario | Recommended Type |
|----------|------------------|
| Simple notification | Text |
| Formatted content | Markdown |
| Complex layout | Rich Text |
| Interactive UI | Card |
| Visual content | Image |

### Message Design

1. **Keep it concise** - Users scan messages quickly
2. **Use formatting** - Bold for emphasis, lists for structure
3. **Include context** - Time, source, action items
4. **Add actions** - Buttons for next steps

### Performance Tips

1. **Batch messages** - Use message queue for high volume
2. **Optimize images** - Compress before sending
3. **Cache templates** - Pre-compile frequently used templates
4. **Rate limiting** - Respect Feishu's rate limits

### Error Handling

```python
from feishu_webhook_bot.core import SendResult

result = bot.send_text("Hello")

if result.success:
    print(f"Message sent: {result.message_id}")
else:
    print(f"Failed: {result.error}")
```

## See Also

- [Templates Guide](templates-guide.md) - Advanced template usage
- [Examples](../resources/examples.md) - More code examples
- [API Reference](../reference/api.md) - Complete API documentation
