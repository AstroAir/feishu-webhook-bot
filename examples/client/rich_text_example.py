#!/usr/bin/env python3
"""Rich Text Message Example.

This example demonstrates rich text (post) message formatting:
- Basic rich text structure
- Text styling (bold, italic, underline)
- Links and mentions
- Images in rich text
- Multi-paragraph content
- Common patterns and templates

Rich text messages provide more formatting options than plain text.
"""

from typing import Any

from feishu_webhook_bot.core import LoggingConfig, get_logger, setup_logging

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)


# =============================================================================
# Demo 1: Basic Rich Text Structure
# =============================================================================
def demo_basic_structure() -> None:
    """Demonstrate basic rich text structure."""
    print("\n" + "=" * 60)
    print("Demo 1: Basic Rich Text Structure")
    print("=" * 60)

    # Rich text structure
    rich_text = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": "Message Title",
                    "content": [
                        # Each inner list is a paragraph
                        [
                            {"tag": "text", "text": "First paragraph content."}
                        ],
                        [
                            {"tag": "text", "text": "Second paragraph content."}
                        ],
                    ]
                }
            }
        }
    }

    print("Basic rich text structure:")
    print_json(rich_text)

    print("\nKey points:")
    print("  - msg_type: 'post' for rich text")
    print("  - content.post.zh_cn: Chinese content (use en_us for English)")
    print("  - title: Message title")
    print("  - content: Array of paragraphs, each paragraph is an array of elements")


# =============================================================================
# Demo 2: Text Styling
# =============================================================================
def demo_text_styling() -> None:
    """Demonstrate text styling options."""
    print("\n" + "=" * 60)
    print("Demo 2: Text Styling")
    print("=" * 60)

    content = [
        # Bold text
        [
            {"tag": "text", "text": "Normal text, "},
            {"tag": "text", "text": "bold text", "style": ["bold"]},
        ],
        # Italic text
        [
            {"tag": "text", "text": "Normal text, "},
            {"tag": "text", "text": "italic text", "style": ["italic"]},
        ],
        # Underline text
        [
            {"tag": "text", "text": "Normal text, "},
            {"tag": "text", "text": "underlined text", "style": ["underline"]},
        ],
        # Combined styles
        [
            {"tag": "text", "text": "Combined: "},
            {"tag": "text", "text": "bold and italic", "style": ["bold", "italic"]},
        ],
        # Strikethrough
        [
            {"tag": "text", "text": "Normal text, "},
            {"tag": "text", "text": "strikethrough", "style": ["lineThrough"]},
        ],
    ]

    print("Text styling examples:")
    for i, paragraph in enumerate(content, 1):
        print(f"\n  Paragraph {i}:")
        for element in paragraph:
            style = element.get("style", ["normal"])
            print(f"    '{element['text']}' - style: {style}")


# =============================================================================
# Demo 3: Links
# =============================================================================
def demo_links() -> None:
    """Demonstrate link elements."""
    print("\n" + "=" * 60)
    print("Demo 3: Links")
    print("=" * 60)

    content = [
        # Simple link
        [
            {"tag": "text", "text": "Visit our "},
            {"tag": "a", "text": "website", "href": "https://example.com"},
            {"tag": "text", "text": " for more info."},
        ],
        # Multiple links
        [
            {"tag": "text", "text": "Resources: "},
            {"tag": "a", "text": "Documentation", "href": "https://docs.example.com"},
            {"tag": "text", "text": " | "},
            {"tag": "a", "text": "GitHub", "href": "https://github.com/example"},
        ],
    ]

    print("Link examples:")
    print_json({"content": content})

    print("\nLink element structure:")
    print('  {"tag": "a", "text": "Display Text", "href": "https://..."}')


# =============================================================================
# Demo 4: Mentions
# =============================================================================
def demo_mentions() -> None:
    """Demonstrate mention elements."""
    print("\n" + "=" * 60)
    print("Demo 4: Mentions")
    print("=" * 60)

    content = [
        # Mention specific user
        [
            {"tag": "at", "user_id": "ou_xxx", "user_name": "John"},
            {"tag": "text", "text": " Please review this PR."},
        ],
        # Mention all
        [
            {"tag": "at", "user_id": "all", "user_name": "All"},
            {"tag": "text", "text": " Team meeting in 10 minutes!"},
        ],
    ]

    print("Mention examples:")
    print_json({"content": content})

    print("\nMention element structure:")
    print('  {"tag": "at", "user_id": "ou_xxx", "user_name": "Name"}')
    print('  {"tag": "at", "user_id": "all", "user_name": "All"}  # Mention everyone')


# =============================================================================
# Demo 5: Images in Rich Text
# =============================================================================
def demo_images() -> None:
    """Demonstrate image elements in rich text."""
    print("\n" + "=" * 60)
    print("Demo 5: Images in Rich Text")
    print("=" * 60)

    content = [
        [
            {"tag": "text", "text": "Here is the screenshot:"},
        ],
        [
            {
                "tag": "img",
                "image_key": "img_v2_xxx",
                "width": 600,
                "height": 400,
            },
        ],
        [
            {"tag": "text", "text": "Please check the highlighted area."},
        ],
    ]

    print("Image in rich text:")
    print_json({"content": content})

    print("\nImage element structure:")
    print('  {"tag": "img", "image_key": "img_v2_xxx", "width": 600, "height": 400}')
    print("\nNote: image_key must be obtained by uploading image first.")


# =============================================================================
# Demo 6: Code Blocks
# =============================================================================
def demo_code_blocks() -> None:
    """Demonstrate code in rich text."""
    print("\n" + "=" * 60)
    print("Demo 6: Code Blocks")
    print("=" * 60)

    # Note: Feishu rich text doesn't have native code blocks
    # Use monospace styling or cards for code

    print("For code in messages, consider:")
    print("\n1. Inline code (using text):")
    content_inline = [
        [
            {"tag": "text", "text": "Run "},
            {"tag": "text", "text": "pip install feishu-webhook-bot"},
            {"tag": "text", "text": " to install."},
        ],
    ]
    print_json({"content": content_inline})

    print("\n2. Code block (using card with markdown):")
    print("""
card = {
    "elements": [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "```python\\nprint('Hello')\\n```"
            }
        }
    ]
}
""")


# =============================================================================
# Demo 7: Multi-Language Support
# =============================================================================
def demo_multi_language() -> None:
    """Demonstrate multi-language rich text."""
    print("\n" + "=" * 60)
    print("Demo 7: Multi-Language Support")
    print("=" * 60)

    rich_text = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": "系统通知",
                    "content": [
                        [{"tag": "text", "text": "系统将于今晚进行维护。"}],
                    ]
                },
                "en_us": {
                    "title": "System Notice",
                    "content": [
                        [{"tag": "text", "text": "System maintenance tonight."}],
                    ]
                },
                "ja_jp": {
                    "title": "システム通知",
                    "content": [
                        [{"tag": "text", "text": "今夜システムメンテナンスを行います。"}],
                    ]
                }
            }
        }
    }

    print("Multi-language rich text:")
    print_json(rich_text)

    print("\nSupported languages:")
    print("  - zh_cn: Simplified Chinese")
    print("  - en_us: English")
    print("  - ja_jp: Japanese")


# =============================================================================
# Demo 8: Common Templates
# =============================================================================
def demo_common_templates() -> None:
    """Demonstrate common rich text templates."""
    print("\n" + "=" * 60)
    print("Demo 8: Common Templates")
    print("=" * 60)

    # Template 1: Notification
    def create_notification(title: str, message: str, link: str | None = None) -> dict:
        content = [[{"tag": "text", "text": message}]]
        if link:
            content.append([
                {"tag": "text", "text": "Details: "},
                {"tag": "a", "text": "View", "href": link},
            ])
        return {"title": title, "content": content}

    # Template 2: Alert with mention
    def create_alert(message: str, mention_all: bool = False) -> dict:
        content = []
        if mention_all:
            content.append([
                {"tag": "at", "user_id": "all", "user_name": "All"},
            ])
        content.append([{"tag": "text", "text": message}])
        return {"title": "⚠️ Alert", "content": content}

    # Template 3: Report
    def create_report(title: str, sections: list[tuple[str, str]]) -> dict:
        content = []
        for section_title, section_content in sections:
            content.append([
                {"tag": "text", "text": section_title, "style": ["bold"]},
            ])
            content.append([
                {"tag": "text", "text": section_content},
            ])
        return {"title": title, "content": content}

    print("Template 1 - Notification:")
    notification = create_notification(
        "Build Complete",
        "Your build has finished successfully.",
        "https://ci.example.com/build/123"
    )
    print_json(notification)

    print("\nTemplate 2 - Alert:")
    alert = create_alert("Server CPU usage is at 95%!", mention_all=True)
    print_json(alert)

    print("\nTemplate 3 - Report:")
    report = create_report("Daily Summary", [
        ("Users:", "1,234 active users today"),
        ("Revenue:", "$12,345 total revenue"),
        ("Issues:", "3 new issues reported"),
    ])
    print_json(report)


# =============================================================================
# Demo 9: Building Rich Text Programmatically
# =============================================================================
def demo_rich_text_builder() -> None:
    """Demonstrate building rich text programmatically."""
    print("\n" + "=" * 60)
    print("Demo 9: Building Rich Text Programmatically")
    print("=" * 60)

    class RichTextBuilder:
        """Builder for rich text messages."""

        def __init__(self, title: str = ""):
            self.title = title
            self.paragraphs: list[list[dict]] = []
            self._current_paragraph: list[dict] = []

        def add_text(self, text: str, style: list[str] | None = None) -> "RichTextBuilder":
            """Add text element."""
            element = {"tag": "text", "text": text}
            if style:
                element["style"] = style
            self._current_paragraph.append(element)
            return self

        def add_bold(self, text: str) -> "RichTextBuilder":
            """Add bold text."""
            return self.add_text(text, ["bold"])

        def add_link(self, text: str, href: str) -> "RichTextBuilder":
            """Add link element."""
            self._current_paragraph.append({
                "tag": "a",
                "text": text,
                "href": href,
            })
            return self

        def add_mention(self, user_id: str, user_name: str) -> "RichTextBuilder":
            """Add mention element."""
            self._current_paragraph.append({
                "tag": "at",
                "user_id": user_id,
                "user_name": user_name,
            })
            return self

        def mention_all(self) -> "RichTextBuilder":
            """Mention all users."""
            return self.add_mention("all", "All")

        def newline(self) -> "RichTextBuilder":
            """Start a new paragraph."""
            if self._current_paragraph:
                self.paragraphs.append(self._current_paragraph)
                self._current_paragraph = []
            return self

        def build(self) -> dict[str, Any]:
            """Build the rich text message."""
            if self._current_paragraph:
                self.paragraphs.append(self._current_paragraph)

            return {
                "title": self.title,
                "content": self.paragraphs,
            }

    # Use the builder
    message = (
        RichTextBuilder("Project Update")
        .add_bold("Status: ")
        .add_text("Completed")
        .newline()
        .add_text("View the ")
        .add_link("full report", "https://example.com/report")
        .add_text(" for details.")
        .newline()
        .mention_all()
        .add_text(" Please review by EOD.")
        .build()
    )

    print("Built rich text message:")
    print_json(message)


# =============================================================================
# Demo 10: Sending Rich Text
# =============================================================================
def demo_sending_rich_text() -> None:
    """Demonstrate sending rich text messages."""
    print("\n" + "=" * 60)
    print("Demo 10: Sending Rich Text")
    print("=" * 60)

    print("Sending rich text with the client:")
    print("""
from feishu_webhook_bot.core import FeishuWebhookClient

client = FeishuWebhookClient(webhook_url="https://...")

# Method 1: Using send_rich_text
client.send_rich_text(
    title="Message Title",
    content=[
        [{"tag": "text", "text": "Hello, "}],
        [{"tag": "text", "text": "World!", "style": ["bold"]}],
    ]
)

# Method 2: Using send_post (full control)
client.send_post({
    "zh_cn": {
        "title": "Message Title",
        "content": [
            [{"tag": "text", "text": "Content here"}],
        ]
    }
})
""")


# =============================================================================
# Helper Functions
# =============================================================================
def print_json(obj: Any, indent: int = 2) -> None:
    """Pretty print a JSON-serializable object."""
    import json

    print(json.dumps(obj, indent=indent, ensure_ascii=False))


# =============================================================================
# Main Entry Point
# =============================================================================
def main() -> None:
    """Run all rich text demonstrations."""
    print("=" * 60)
    print("Rich Text Message Examples")
    print("=" * 60)

    demos = [
        ("Basic Rich Text Structure", demo_basic_structure),
        ("Text Styling", demo_text_styling),
        ("Links", demo_links),
        ("Mentions", demo_mentions),
        ("Images in Rich Text", demo_images),
        ("Code Blocks", demo_code_blocks),
        ("Multi-Language Support", demo_multi_language),
        ("Common Templates", demo_common_templates),
        ("Building Rich Text Programmatically", demo_rich_text_builder),
        ("Sending Rich Text", demo_sending_rich_text),
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
