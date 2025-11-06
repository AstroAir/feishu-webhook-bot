"""Quick start example for Feishu Webhook Bot.

This example demonstrates how to:
1. Create a bot with configuration
2. Send different types of messages
3. Use the CardBuilder
"""

from feishu_webhook_bot import FeishuBot
from feishu_webhook_bot.core import BotConfig, FeishuWebhookClient, WebhookConfig
from feishu_webhook_bot.core.client import CardBuilder


def example_send_messages():
    """Example: Send different types of messages."""
    # Create webhook config
    config = WebhookConfig(
        url="https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL",
        secret=None,  # Add your secret if enabled
        name="demo",
    )

    # Create client
    with FeishuWebhookClient(config) as client:
        # 1. Send simple text message
        print("Sending text message...")
        client.send_text("Hello from Feishu Bot! 👋")

        # 2. Send rich text message
        print("Sending rich text message...")
        content = [
            [
                {"tag": "text", "text": "This is "},
                {"tag": "a", "text": "a link", "href": "https://github.com"},
                {"tag": "text", "text": " in rich text."},
            ]
        ]
        client.send_rich_text("Rich Text Example", content)

        # 3. Send interactive card using CardBuilder
        print("Sending interactive card...")
        card = (
            CardBuilder()
            .set_config(wide_screen_mode=True)
            .set_header("🎉 Welcome to Feishu Bot!", template="blue")
            .add_markdown(
                "This is an **interactive card** built with `CardBuilder`.\n\n"
                "Features:\n"
                "- Easy to use\n"
                "- Rich formatting\n"
                "- Buttons and actions"
            )
            .add_divider()
            .add_text("Click the button below to learn more!")
            .add_button(
                "Visit GitHub", url="https://github.com/AstroAir/feishu-webhook-bot"
            )
            .add_note("Powered by Feishu Webhook Bot Framework")
            .build()
        )
        client.send_card(card)

        print("✓ All messages sent successfully!")


def example_start_bot():
    """Example: Start bot with configuration."""
    # Create configuration programmatically
    config = BotConfig(
        webhooks=[
            WebhookConfig(
                url="https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL",
                name="default",
            )
        ],
        scheduler={
            "enabled": True,
            "timezone": "Asia/Shanghai",
            "job_store_type": "memory",
        },
        plugins={"enabled": True, "plugin_dir": "plugins", "auto_reload": True},
        logging={"level": "INFO", "log_file": "logs/bot.log"},
    )

    # Create and start bot
    bot = FeishuBot(config)

    print("Starting bot...")
    print("Press Ctrl+C to stop")

    try:
        bot.start()
    except KeyboardInterrupt:
        print("\nStopping bot...")
        bot.stop()


def example_card_templates():
    """Example: Different card templates."""
    config = WebhookConfig(
        url="https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL"
    )

    with FeishuWebhookClient(config) as client:
        # Success card (green)
        success_card = (
            CardBuilder()
            .set_header("✅ Success", template="green")
            .add_markdown("Operation completed successfully!")
            .build()
        )
        client.send_card(success_card)

        # Error card (red)
        error_card = (
            CardBuilder()
            .set_header("❌ Error", template="red")
            .add_markdown("An error occurred. Please check the logs.")
            .build()
        )
        client.send_card(error_card)

        # Warning card (orange)
        warning_card = (
            CardBuilder()
            .set_header("⚠️ Warning", template="orange")
            .add_markdown("This action requires attention.")
            .build()
        )
        client.send_card(warning_card)

        # Info card (blue)
        info_card = (
            CardBuilder()
            .set_header("ℹ️ Information", template="blue")
            .add_markdown("Here is some useful information.")
            .build()
        )
        client.send_card(info_card)


if __name__ == "__main__":
    print("Feishu Webhook Bot - Quick Start Examples")
    print("=" * 50)
    print()
    print("Available examples:")
    print("1. Send different message types")
    print("2. Start bot with configuration")
    print("3. Card template examples")
    print()

    choice = input("Enter example number (1-3) or 'q' to quit: ")

    if choice == "1":
        example_send_messages()
    elif choice == "2":
        example_start_bot()
    elif choice == "3":
        example_card_templates()
    elif choice.lower() == "q":
        print("Goodbye!")
    else:
        print("Invalid choice!")
