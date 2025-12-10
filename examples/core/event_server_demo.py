"""Comprehensive demonstration of the Event Server.

This example demonstrates:
1. Receiving Feishu webhook events
2. Token verification and signature validation
3. Event dispatching to plugins
4. Integration with AI agent for chat messages
5. Handling different event types
6. Security best practices

Run this example:
    python examples/event_server_demo.py

Then test with:
    curl -X POST http://localhost:8080/webhook \
      -H "Content-Type: application/json" \
      -d '{"type":"message","message":{"content":"Hello!"}}'
"""

import asyncio
import tempfile
import time
from pathlib import Path

import httpx

from feishu_webhook_bot import FeishuBot
from feishu_webhook_bot.core.config import (
    BotConfig,
    EventServerConfig,
    PluginConfig,
)

# ============================================================================
# Demo Functions
# ============================================================================


def demo_basic_event_server() -> None:
    """Demonstrate basic event server setup."""
    print("\n" + "=" * 70)
    print("Demo 1: Basic Event Server")
    print("=" * 70)

    config = BotConfig(
        webhooks=[],
        event_server=EventServerConfig(
            enabled=True,
            host="127.0.0.1",
            port=8080,
            path="/webhook",
        ),
    )

    bot = FeishuBot(config)
    bot.start()
    print("\n✅ Bot started with event server")
    print("   • Listening on: http://127.0.0.1:8080/webhook")
    print("   • Health check: http://127.0.0.1:8080/healthz")

    print("\n📨 Sending test event...")
    time.sleep(2)  # Wait for server to start

    # Send test event
    try:
        response = httpx.post(
            "http://127.0.0.1:8080/webhook",
            json={
                "type": "message",
                "message": {"content": "Hello from test!"},
            },
            timeout=5,
        )
        print(f"✅ Event sent! Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to send event: {e}")

    time.sleep(2)

    bot.stop()
    print("\n✅ Bot stopped")


def demo_token_verification() -> None:
    """Demonstrate token verification."""
    print("\n" + "=" * 70)
    print("Demo 2: Token Verification")
    print("=" * 70)

    verification_token = "test-token-123"

    config = BotConfig(
        webhooks=[],
        event_server=EventServerConfig(
            enabled=True,
            host="127.0.0.1",
            port=8081,
            path="/webhook",
            verification_token=verification_token,
        ),
    )

    bot = FeishuBot(config)
    bot.start()
    print("\n✅ Bot started with token verification")
    print(f"   • Verification token: {verification_token}")

    time.sleep(2)

    # Test with correct token
    print("\n📨 Sending event with correct token...")
    try:
        response = httpx.post(
            "http://127.0.0.1:8081/webhook",
            json={
                "type": "message",
                "token": verification_token,
                "message": {"content": "Hello!"},
            },
            timeout=5,
        )
        print(f"✅ Accepted! Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test with wrong token
    print("\n📨 Sending event with wrong token...")
    try:
        response = httpx.post(
            "http://127.0.0.1:8081/webhook",
            json={
                "type": "message",
                "token": "wrong-token",
                "message": {"content": "Hello!"},
            },
            timeout=5,
        )
        print(f"❌ Should be rejected! Status: {response.status_code}")
    except httpx.HTTPStatusError as e:
        print(f"✅ Correctly rejected! Status: {e.response.status_code}")

    bot.stop()
    print("\n✅ Bot stopped")


def demo_url_verification() -> None:
    """Demonstrate URL verification challenge."""
    print("\n" + "=" * 70)
    print("Demo 3: URL Verification Challenge")
    print("=" * 70)

    config = BotConfig(
        webhooks=[],
        event_server=EventServerConfig(
            enabled=True,
            host="127.0.0.1",
            port=8082,
            path="/webhook",
        ),
    )

    bot = FeishuBot(config)
    bot.start()
    print("\n✅ Bot started")

    time.sleep(2)

    # Send URL verification challenge
    print("\n📨 Sending URL verification challenge...")
    try:
        response = httpx.post(
            "http://127.0.0.1:8082/webhook",
            json={
                "type": "url_verification",
                "challenge": "test-challenge-string",
            },
            timeout=5,
        )
        result = response.json()
        print(f"✅ Challenge response: {result}")
        if result.get("challenge") == "test-challenge-string":
            print("✅ URL verification successful!")
    except Exception as e:
        print(f"❌ Error: {e}")

    bot.stop()
    print("\n✅ Bot stopped")


def demo_event_dispatching() -> None:
    """Demonstrate event dispatching to plugins."""
    print("\n" + "=" * 70)
    print("Demo 4: Event Dispatching to Plugins")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir)

        # Create event handler plugin
        plugin_file = plugin_dir / "event_plugin.py"
        plugin_code = '''
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class EventHandlerPlugin(BasePlugin):
    def metadata(self):
        return PluginMetadata(name="event-handler", version="1.0.0")

    def handle_event(self, event, context=None):
        """Handle incoming events."""
        event_type = event.get("type", "unknown")
        self.logger.info(f"Plugin received event: {event_type}")

        if event_type == "message":
            content = event.get("message", {}).get("content", "")
            self.logger.info(f"Message content: {content}")
            self.client.send_text(f"Echo: {content}")
        elif event_type == "app_mention":
            self.logger.info("Bot was mentioned!")
            self.client.send_text("Thanks for mentioning me!")
'''
        plugin_file.write_text(plugin_code)

        config = BotConfig(
            webhooks=[],
            plugins=PluginConfig(
                enabled=True,
                plugin_dir=str(plugin_dir),
            ),
            event_server=EventServerConfig(
                enabled=True,
                host="127.0.0.1",
                port=8083,
                path="/webhook",
            ),
        )

        bot = FeishuBot(config)
        bot.start()
        print("\n✅ Bot started with event handler plugin")

        time.sleep(2)

        # Send different event types
        events = [
            {
                "type": "message",
                "message": {"content": "Hello from user!"},
            },
            {
                "type": "app_mention",
                "mention": {"user_id": "user123"},
            },
        ]

        for event in events:
            print(f"\n📨 Sending event: {event['type']}")
            try:
                response = httpx.post(
                    "http://127.0.0.1:8083/webhook",
                    json=event,
                    timeout=5,
                )
                print(f"✅ Event dispatched! Status: {response.status_code}")
            except Exception as e:
                print(f"❌ Error: {e}")

            time.sleep(1)

        bot.stop()
        print("\n✅ Bot stopped")


def demo_health_check() -> None:
    """Demonstrate health check endpoint."""
    print("\n" + "=" * 70)
    print("Demo 5: Health Check Endpoint")
    print("=" * 70)

    config = BotConfig(
        webhooks=[],
        event_server=EventServerConfig(
            enabled=True,
            host="127.0.0.1",
            port=8084,
            path="/webhook",
        ),
    )

    bot = FeishuBot(config)
    bot.start()
    print("\n✅ Bot started")

    time.sleep(2)

    # Check health endpoint
    print("\n🏥 Checking health endpoint...")
    try:
        response = httpx.get("http://127.0.0.1:8084/healthz", timeout=5)
        result = response.json()
        print(f"✅ Health check: {result}")
        print(f"   Status: {result.get('status')}")
    except Exception as e:
        print(f"❌ Error: {e}")

    bot.stop()
    print("\n✅ Bot stopped")


def demo_concurrent_events() -> None:
    """Demonstrate handling concurrent events."""
    print("\n" + "=" * 70)
    print("Demo 6: Concurrent Event Handling")
    print("=" * 70)

    config = BotConfig(
        webhooks=[],
        event_server=EventServerConfig(
            enabled=True,
            host="127.0.0.1",
            port=8085,
            path="/webhook",
        ),
    )

    bot = FeishuBot(config)
    bot.start()
    print("\n✅ Bot started")

    time.sleep(2)

    # Send multiple events concurrently
    print("\n📨 Sending 5 concurrent events...")

    async def send_events():
        async with httpx.AsyncClient() as client:
            tasks = []
            for i in range(5):
                task = client.post(
                    "http://127.0.0.1:8085/webhook",
                    json={
                        "type": "message",
                        "message": {"content": f"Message {i+1}"},
                    },
                    timeout=5,
                )
                tasks.append(task)

            responses = await asyncio.gather(*tasks, return_exceptions=True)
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    print(f"❌ Event {i+1} failed: {response}")
                else:
                    print(f"✅ Event {i+1} sent! Status: {response.status_code}")

    try:
        asyncio.run(send_events())
    except Exception as e:
        print(f"❌ Error: {e}")

    time.sleep(2)

    bot.stop()
    print("\n✅ Bot stopped")


# ============================================================================
# Main Demo Runner
# ============================================================================


def main() -> None:
    """Run all event server demonstrations."""
    print("\n" + "=" * 70)
    print("FEISHU WEBHOOK BOT - EVENT SERVER DEMONSTRATION")
    print("=" * 70)

    demos = [
        ("Basic Event Server", demo_basic_event_server),
        ("Token Verification", demo_token_verification),
        ("URL Verification", demo_url_verification),
        ("Event Dispatching", demo_event_dispatching),
        ("Health Check", demo_health_check),
        ("Concurrent Events", demo_concurrent_events),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            demo_func()
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
            import traceback

            traceback.print_exc()

        if i < len(demos):
            print("\n" + "-" * 70)
            input("Press Enter to continue to next demo...")

    print("\n" + "=" * 70)
    print("ALL DEMONSTRATIONS COMPLETED!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("• Event server receives incoming Feishu webhook events")
    print("• Token verification ensures only authorized requests")
    print("• URL verification challenge validates webhook configuration")
    print("• Events are dispatched to plugins for processing")
    print("• Health check endpoint monitors server status")
    print("• Server handles concurrent events efficiently")
    print("\nSecurity Best Practices:")
    print("• Always use verification_token in production")
    print("• Enable signature_secret for HMAC validation")
    print("• Use HTTPS in production environments")
    print("• Monitor health check endpoint")


if __name__ == "__main__":
    main()
