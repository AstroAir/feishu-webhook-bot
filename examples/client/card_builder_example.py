#!/usr/bin/env python3
"""Card Builder Example.

This example demonstrates the CardBuilder for creating interactive cards:
- Building cards with fluent API
- Header styles and templates
- Content elements (text, images, dividers)
- Interactive elements (buttons, selects)
- Layout options (columns, fields)
- Card templates for common use cases

The CardBuilder provides a convenient way to create Feishu interactive cards.
"""

from typing import Any

from feishu_webhook_bot.core import CardBuilder, LoggingConfig, get_logger, setup_logging

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)


# =============================================================================
# Demo 1: Basic Card Structure
# =============================================================================
def demo_basic_card() -> None:
    """Demonstrate basic card structure."""
    print("\n" + "=" * 60)
    print("Demo 1: Basic Card Structure")
    print("=" * 60)

    # Create a simple card
    card = (
        CardBuilder()
        .set_header("Welcome Message", template="blue")
        .add_text("Hello! Welcome to our service.")
        .build()
    )

    print("Basic card structure:")
    print_json(card)


# =============================================================================
# Demo 2: Header Styles
# =============================================================================
def demo_header_styles() -> None:
    """Demonstrate different header styles."""
    print("\n" + "=" * 60)
    print("Demo 2: Header Styles")
    print("=" * 60)

    templates = ["blue", "green", "orange", "red", "purple", "grey"]

    print("Available header templates:")
    for template in templates:
        card = (
            CardBuilder()
            .set_header(f"{template.title()} Header", template=template)
            .add_text(f"This is a {template} themed card.")
            .build()
        )
        print(f"\n  {template}:")
        print(f"    Header template: {card['header']['template']}")


# =============================================================================
# Demo 3: Text Elements
# =============================================================================
def demo_text_elements() -> None:
    """Demonstrate text elements."""
    print("\n" + "=" * 60)
    print("Demo 3: Text Elements")
    print("=" * 60)

    card = (
        CardBuilder()
        .set_header("Text Elements Demo")
        # Plain text
        .add_text("This is plain text.")
        # Markdown text
        .add_markdown("**Bold** and *italic* text with `code`.")
        # Text with fields
        .add_fields(
            [
                {"title": "Status", "value": "Active"},
                {"title": "Priority", "value": "High"},
            ],
            is_short=True,
        )
        .build()
    )

    print("Card with text elements:")
    print_json(card)


# =============================================================================
# Demo 4: Dividers and Spacing
# =============================================================================
def demo_dividers() -> None:
    """Demonstrate dividers and spacing."""
    print("\n" + "=" * 60)
    print("Demo 4: Dividers and Spacing")
    print("=" * 60)

    card = (
        CardBuilder()
        .set_header("Dividers Demo")
        .add_text("Section 1 content")
        .add_divider()
        .add_text("Section 2 content")
        .add_divider()
        .add_text("Section 3 content")
        .build()
    )

    print("Card with dividers:")
    print_json(card)


# =============================================================================
# Demo 5: Buttons and Actions
# =============================================================================
def demo_buttons() -> None:
    """Demonstrate buttons and actions."""
    print("\n" + "=" * 60)
    print("Demo 5: Buttons and Actions")
    print("=" * 60)

    card = (
        CardBuilder()
        .set_header("Actions Demo", template="blue")
        .add_text("Choose an action:")
        .add_button(
            text="Primary Button",
            button_type="primary",
            url="https://example.com/action1",
        )
        .add_button(
            text="Default Button",
            button_type="default",
            value={"action": "default_clicked"},
        )
        .add_button(
            text="Danger Button",
            button_type="danger",
            confirm={
                "title": "Confirm",
                "text": "Are you sure?",
            },
        )
        .build()
    )

    print("Card with buttons:")
    print_json(card)


# =============================================================================
# Demo 6: Images
# =============================================================================
def demo_images() -> None:
    """Demonstrate image elements."""
    print("\n" + "=" * 60)
    print("Demo 6: Images")
    print("=" * 60)

    card = (
        CardBuilder()
        .set_header("Image Demo")
        .add_image(
            img_key="img_v2_example_key",
            alt="Example image",
        )
        .add_text("Image caption goes here.")
        .build()
    )

    print("Card with image:")
    print_json(card)


# =============================================================================
# Demo 7: Multi-Column Layout
# =============================================================================
def demo_multi_column() -> None:
    """Demonstrate multi-column layout."""
    print("\n" + "=" * 60)
    print("Demo 7: Multi-Column Layout")
    print("=" * 60)

    card = (
        CardBuilder()
        .set_header("Multi-Column Layout")
        .add_column_set(
            columns=[
                {
                    "width": "weighted",
                    "weight": 1,
                    "elements": [
                        {"tag": "div", "text": {"tag": "plain_text", "content": "Column 1"}}
                    ],
                },
                {
                    "width": "weighted",
                    "weight": 1,
                    "elements": [
                        {"tag": "div", "text": {"tag": "plain_text", "content": "Column 2"}}
                    ],
                },
            ]
        )
        .build()
    )

    print("Card with columns:")
    print_json(card)


# =============================================================================
# Demo 8: Select Menus
# =============================================================================
def demo_select_menus() -> None:
    """Demonstrate select menu elements."""
    print("\n" + "=" * 60)
    print("Demo 8: Select Menus")
    print("=" * 60)

    card = (
        CardBuilder()
        .set_header("Select Menu Demo")
        .add_text("Choose an option:")
        .add_select(
            name="priority",
            placeholder="Select priority",
            options=[
                {"text": "High", "value": "high"},
                {"text": "Medium", "value": "medium"},
                {"text": "Low", "value": "low"},
            ],
        )
        .build()
    )

    print("Card with select menu:")
    print_json(card)


# =============================================================================
# Demo 9: Alert Card Template
# =============================================================================
def demo_alert_template() -> None:
    """Demonstrate alert card template."""
    print("\n" + "=" * 60)
    print("Demo 9: Alert Card Template")
    print("=" * 60)

    def create_alert_card(
        title: str,
        message: str,
        severity: str = "info",
        details: dict[str, str] | None = None,
        action_url: str | None = None,
    ) -> dict[str, Any]:
        """Create an alert card."""
        colors = {
            "info": "blue",
            "success": "green",
            "warning": "orange",
            "error": "red",
        }
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
        }

        builder = (
            CardBuilder()
            .set_header(f"{icons.get(severity, '')} {title}", template=colors.get(severity, "blue"))
            .add_markdown(message)
        )

        if details:
            builder.add_divider()
            fields = [{"title": k, "value": v} for k, v in details.items()]
            builder.add_fields(fields, is_short=True)

        if action_url:
            builder.add_divider()
            builder.add_button("View Details", button_type="primary", url=action_url)

        return builder.build()

    # Create different alert types
    alerts = [
        ("Info Alert", "System update scheduled for tonight.", "info"),
        ("Success Alert", "Deployment completed successfully!", "success"),
        ("Warning Alert", "Disk usage is at 85%.", "warning"),
        ("Error Alert", "Database connection failed.", "error"),
    ]

    print("Alert card templates:")
    for title, message, severity in alerts:
        card = create_alert_card(title, message, severity)
        print(f"\n  {severity.upper()}:")
        print(f"    Header: {card['header']['title']['content']}")
        print(f"    Template: {card['header']['template']}")


# =============================================================================
# Demo 10: Report Card Template
# =============================================================================
def demo_report_template() -> None:
    """Demonstrate report card template."""
    print("\n" + "=" * 60)
    print("Demo 10: Report Card Template")
    print("=" * 60)

    def create_report_card(
        title: str,
        sections: list[dict[str, Any]],
        footer: str | None = None,
    ) -> dict[str, Any]:
        """Create a report card."""
        builder = CardBuilder().set_header(title, template="blue")

        for i, section in enumerate(sections):
            if i > 0:
                builder.add_divider()

            if "title" in section:
                builder.add_markdown(f"**{section['title']}**")

            if "content" in section:
                builder.add_text(section["content"])

            if "fields" in section:
                # Display fields as markdown since add_fields is not available
                for field in section["fields"]:
                    builder.add_markdown(f"**{field['title']}:** {field['value']}")

            if "metrics" in section:
                metrics_text = " | ".join(f"**{k}:** {v}" for k, v in section["metrics"].items())
                builder.add_markdown(metrics_text)

        if footer:
            builder.add_divider()
            builder.add_text(footer)

        return builder.build()

    # Create a sample report
    report = create_report_card(
        title="📊 Daily Report - 2024-01-15",
        sections=[
            {
                "title": "Summary",
                "metrics": {
                    "Users": "1,234",
                    "Orders": "567",
                    "Revenue": "$12,345",
                },
            },
            {
                "title": "Top Products",
                "fields": [
                    {"title": "#1", "value": "Product A (234 sales)"},
                    {"title": "#2", "value": "Product B (189 sales)"},
                ],
            },
            {
                "title": "Notes",
                "content": "All systems operational. No incidents reported.",
            },
        ],
        footer="Generated at 2024-01-15 18:00:00",
    )

    print("Report card:")
    print_json(report)


# =============================================================================
# Demo 11: Interactive Form Card
# =============================================================================
def demo_form_card() -> None:
    """Demonstrate interactive form card."""
    print("\n" + "=" * 60)
    print("Demo 11: Interactive Form Card")
    print("=" * 60)

    card = (
        CardBuilder()
        .set_header("Feedback Form", template="purple")
        .add_text("Please provide your feedback:")
        .add_select(
            name="rating",
            placeholder="Select rating",
            options=[
                {"text": "⭐⭐⭐⭐⭐ Excellent", "value": "5"},
                {"text": "⭐⭐⭐⭐ Good", "value": "4"},
                {"text": "⭐⭐⭐ Average", "value": "3"},
                {"text": "⭐⭐ Poor", "value": "2"},
                {"text": "⭐ Very Poor", "value": "1"},
            ],
        )
        .add_divider()
        .add_button("Submit Feedback", button_type="primary", value={"action": "submit"})
        .add_button("Cancel", button_type="default", value={"action": "cancel"})
        .build()
    )

    print("Form card:")
    print_json(card)


# =============================================================================
# Demo 12: Complete Card Builder API
# =============================================================================
def demo_complete_api() -> None:
    """Show complete CardBuilder API reference."""
    print("\n" + "=" * 60)
    print("Demo 12: Complete Card Builder API")
    print("=" * 60)

    print("""
CardBuilder API Reference:

# Header
.set_header(title, template="blue")

# Text Elements
.add_text(content)
.add_markdown(content)

# Layout
.add_divider()
.add_column_set(columns)

# Media
.add_image(img_key, alt="")

# Interactive Elements
.add_button(text, button_type="default", url=None, value=None, confirm=None)
.add_select(name, options, placeholder="")
.add_overflow(options)
.add_date_picker(placeholder)

# Build
.build() -> dict

# Example:
card = (
    CardBuilder()
    .set_header("Title", template="blue")
    .add_markdown("**Hello** World")
    .add_divider()
    .add_markdown("**Field 1:** Value 1")
    .add_markdown("**Field 2:** Value 2")
    .add_button("Click Me", button_type="primary", url="https://...")
    .build()
)
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
    """Run all card builder demonstrations."""
    print("=" * 60)
    print("Card Builder Examples")
    print("=" * 60)

    demos = [
        ("Basic Card Structure", demo_basic_card),
        ("Header Styles", demo_header_styles),
        ("Text Elements", demo_text_elements),
        ("Dividers and Spacing", demo_dividers),
        ("Buttons and Actions", demo_buttons),
        ("Images", demo_images),
        ("Multi-Column Layout", demo_multi_column),
        ("Select Menus", demo_select_menus),
        ("Alert Card Template", demo_alert_template),
        ("Report Card Template", demo_report_template),
        ("Interactive Form Card", demo_form_card),
        ("Complete Card Builder API", demo_complete_api),
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
