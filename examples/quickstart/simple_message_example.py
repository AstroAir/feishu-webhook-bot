#!/usr/bin/env python3
"""Simple Message Sending Example.

This example demonstrates the simplest way to send messages:
- Quick setup with minimal code
- Sending text messages
- Sending formatted messages
- Common use cases

This is the fastest way to get started with the bot.
"""

import os

from feishu_webhook_bot.core import (
    FeishuWebhookClient,
    LoggingConfig,
    get_logger,
    setup_logging,
)

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)


# =============================================================================
# Demo 1: Simplest Possible Setup
# =============================================================================
def demo_simplest_setup() -> None:
    """Demonstrate the simplest possible setup."""
    print("\n" + "=" * 60)
    print("Demo 1: Simplest Possible Setup")
    print("=" * 60)

    print("The simplest way to send a message:")
    print("""
from feishu_webhook_bot.core import FeishuWebhookClient

# Create client with webhook URL
client = FeishuWebhookClient(
    webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
)

# Send a message
client.send_text("Hello, World!")
""")

    # Actual demo if URL is available
    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL")
    if webhook_url:
        client = FeishuWebhookClient(webhook_url=webhook_url)
        result = client.send_text("Hello from Simple Message Example!")
        print(f"\nMessage sent: {result}")
    else:
        print("\nSet FEISHU_WEBHOOK_URL to send actual messages.")


# =============================================================================
# Demo 2: Send Text Message
# =============================================================================
def demo_send_text() -> None:
    """Demonstrate sending text messages."""
    print("\n" + "=" * 60)
    print("Demo 2: Send Text Message")
    print("=" * 60)

    print("Text message examples:")

    print("\n1. Simple text:")
    print('   client.send_text("Hello, team!")')

    print("\n2. Multi-line text:")
    print('''   client.send_text("""
   Daily Report:
   - Tasks completed: 10
   - Tasks pending: 5
   - Status: On track
   """)''')

    print("\n3. Text with emoji:")
    print('   client.send_text("✅ Build successful! 🎉")')

    print("\n4. Text with mentions:")
    print('   client.send_text("<at user_id=\\"all\\">All</at> Please review")')


# =============================================================================
# Demo 3: Send Rich Text
# =============================================================================
def demo_send_rich_text() -> None:
    """Demonstrate sending rich text messages."""
    print("\n" + "=" * 60)
    print("Demo 3: Send Rich Text")
    print("=" * 60)

    print("Rich text message structure:")
    print("""
client.send_rich_text(
    title="Project Update",
    content=[
        # Paragraph 1
        [
            {"tag": "text", "text": "Status: "},
            {"tag": "text", "text": "Completed", "style": ["bold"]},
        ],
        # Paragraph 2 - with link
        [
            {"tag": "text", "text": "Details: "},
            {"tag": "a", "text": "View Report", "href": "https://example.com"},
        ],
        # Paragraph 3 - mention all
        [
            {"tag": "at", "user_id": "all", "user_name": "All"},
            {"tag": "text", "text": " Please review"},
        ],
    ]
)
""")

    print("Rich text tags:")
    print("  - text: Plain text with optional styles (bold, italic, underline)")
    print("  - a: Hyperlink")
    print("  - at: Mention user (@someone)")
    print("  - img: Inline image")


# =============================================================================
# Demo 4: Send Card Message
# =============================================================================
def demo_send_card() -> None:
    """Demonstrate sending card messages."""
    print("\n" + "=" * 60)
    print("Demo 4: Send Card Message")
    print("=" * 60)

    print("Simple card example:")
    print("""
card = {
    "header": {
        "title": {"tag": "plain_text", "content": "Notification"},
        "template": "blue"  # blue, green, orange, red, etc.
    },
    "elements": [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**Important:** Your task is due tomorrow"
            }
        },
        {"tag": "hr"},  # Horizontal line
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "View Task"},
                    "type": "primary",
                    "url": "https://example.com/task"
                }
            ]
        }
    ]
}

client.send_card(card)
""")

    print("Card header templates:")
    print("  - blue: Information")
    print("  - green: Success")
    print("  - orange: Warning")
    print("  - red: Error/Alert")
    print("  - purple, turquoise, yellow, grey, etc.")


# =============================================================================
# Demo 5: Common Use Cases
# =============================================================================
def demo_common_use_cases() -> None:
    """Demonstrate common use cases."""
    print("\n" + "=" * 60)
    print("Demo 5: Common Use Cases")
    print("=" * 60)

    print("1. Alert Notification:")
    print("""
def send_alert(title: str, message: str, severity: str = "warning"):
    colors = {"info": "blue", "warning": "orange", "error": "red"}
    card = {
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": colors.get(severity, "blue")
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": message}}
        ]
    }
    client.send_card(card)

# Usage
send_alert("Server Alert", "CPU usage exceeded 90%", "error")
""")

    print("\n2. Build Notification:")
    print("""
def notify_build_result(project: str, status: str, url: str):
    emoji = "✅" if status == "success" else "❌"
    color = "green" if status == "success" else "red"
    
    card = {
        "header": {
            "title": {"tag": "plain_text", "content": f"{emoji} Build {status.title()}"},
            "template": color
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**Project:** {project}"}},
            {"tag": "action", "actions": [
                {"tag": "button", "text": {"tag": "plain_text", "content": "View Details"},
                 "url": url}
            ]}
        ]
    }
    client.send_card(card)
""")

    print("\n3. Daily Report:")
    print("""
def send_daily_report(stats: dict):
    content = [
        [{"tag": "text", "text": f"📊 Daily Report - {datetime.now().strftime('%Y-%m-%d')}"}],
        [{"tag": "text", "text": f"Active Users: {stats['users']}"}],
        [{"tag": "text", "text": f"Orders: {stats['orders']}"}],
        [{"tag": "text", "text": f"Revenue: ${stats['revenue']:,.2f}"}],
    ]
    client.send_rich_text(title="Daily Report", content=content)
""")


# =============================================================================
# Demo 6: Error Handling
# =============================================================================
def demo_error_handling() -> None:
    """Demonstrate error handling."""
    print("\n" + "=" * 60)
    print("Demo 6: Error Handling")
    print("=" * 60)

    print("Basic error handling:")
    print("""
from feishu_webhook_bot.core import FeishuWebhookClient

client = FeishuWebhookClient(webhook_url="https://...")

try:
    result = client.send_text("Hello!")
    if result.get("code") == 0:
        print("Message sent successfully")
    else:
        print(f"Failed: {result.get('msg')}")
except Exception as e:
    print(f"Error sending message: {e}")
""")

    print("\nWith retry logic:")
    print("""
import time

def send_with_retry(message: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            result = client.send_text(message)
            if result.get("code") == 0:
                return True
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
    return False
""")


# =============================================================================
# Demo 7: Webhook with Secret
# =============================================================================
def demo_webhook_with_secret() -> None:
    """Demonstrate using webhook with secret."""
    print("\n" + "=" * 60)
    print("Demo 7: Webhook with Secret")
    print("=" * 60)

    print("For signed webhooks (v2), include the secret:")
    print("""
client = FeishuWebhookClient(
    webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
    secret="your-webhook-secret"
)

# The client will automatically:
# 1. Generate timestamp
# 2. Create HMAC-SHA256 signature
# 3. Include signature in request

client.send_text("Secure message!")
""")

    print("\nGetting the secret:")
    print("  1. Go to Feishu Developer Console")
    print("  2. Select your bot")
    print("  3. Go to 'Webhook' settings")
    print("  4. Enable 'Signature Verification'")
    print("  5. Copy the generated secret")


# =============================================================================
# Demo 8: Environment Variables
# =============================================================================
def demo_environment_variables() -> None:
    """Demonstrate using environment variables."""
    print("\n" + "=" * 60)
    print("Demo 8: Environment Variables")
    print("=" * 60)

    print("Recommended environment variables:")
    print("""
# .env file
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
FEISHU_WEBHOOK_SECRET=your-secret-key
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
""")

    print("\nUsage in code:")
    print("""
import os
from dotenv import load_dotenv

load_dotenv()  # Load from .env file

client = FeishuWebhookClient(
    webhook_url=os.environ["FEISHU_WEBHOOK_URL"],
    secret=os.environ.get("FEISHU_WEBHOOK_SECRET")
)
""")

    print("\nCurrent environment:")
    env_vars = [
        "FEISHU_WEBHOOK_URL",
        "FEISHU_WEBHOOK_SECRET",
        "FEISHU_APP_ID",
    ]
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            # Mask sensitive values
            masked = value[:10] + "..." if len(value) > 10 else value
            print(f"  {var}: {masked}")
        else:
            print(f"  {var}: (not set)")


# =============================================================================
# Demo 9: Quick Reference
# =============================================================================
def demo_quick_reference() -> None:
    """Show quick reference for common operations."""
    print("\n" + "=" * 60)
    print("Demo 9: Quick Reference")
    print("=" * 60)

    print("""
# Quick Reference - Common Operations

# Setup
from feishu_webhook_bot.core import FeishuWebhookClient
client = FeishuWebhookClient(webhook_url="https://...")

# Send text
client.send_text("Hello!")

# Send rich text
client.send_rich_text(
    title="Title",
    content=[[{"tag": "text", "text": "Content"}]]
)

# Send card
client.send_card({
    "header": {"title": {"content": "Title", "tag": "plain_text"}},
    "elements": [{"tag": "div", "text": {"content": "Text", "tag": "plain_text"}}]
})

# Send image (requires image_key from upload)
client.send_image("img_v2_xxx")

# Mention user
client.send_text("<at user_id=\\"user_id\\">Name</at> Hello!")

# Mention all
client.send_text("<at user_id=\\"all\\">All</at> Attention!")
""")


# =============================================================================
# Main Entry Point
# =============================================================================
def main() -> None:
    """Run all simple message demonstrations."""
    print("=" * 60)
    print("Simple Message Sending Examples")
    print("=" * 60)

    demos = [
        ("Simplest Possible Setup", demo_simplest_setup),
        ("Send Text Message", demo_send_text),
        ("Send Rich Text", demo_send_rich_text),
        ("Send Card Message", demo_send_card),
        ("Common Use Cases", demo_common_use_cases),
        ("Error Handling", demo_error_handling),
        ("Webhook with Secret", demo_webhook_with_secret),
        ("Environment Variables", demo_environment_variables),
        ("Quick Reference", demo_quick_reference),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            demo_func()
        except Exception as e:
            print(f"\nDemo {i} ({name}) failed with error: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print("All demonstrations completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
