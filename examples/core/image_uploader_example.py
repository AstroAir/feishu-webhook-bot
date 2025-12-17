#!/usr/bin/env python3
"""Image Uploader Example.

This example demonstrates the Feishu image upload functionality:
- Uploading images to Feishu Open Platform
- Getting image_key for use in messages
- Permission checking and error handling
- Creating image cards
- Base64 image handling
- Browser-based authorization

Note: Image upload requires a Feishu application with appropriate permissions.
"""

import base64
import os
import tempfile
from pathlib import Path
from typing import Any

from feishu_webhook_bot.core import LoggingConfig, get_logger, setup_logging
from feishu_webhook_bot.core.image_uploader import (
    FeishuImageUploader,
    FeishuImageUploaderError,
    FeishuPermissionChecker,
    FeishuPermissionDeniedError,
    create_image_card,
)

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)


# =============================================================================
# Demo 1: Permission Checker
# =============================================================================
def demo_permission_checker() -> None:
    """Demonstrate Feishu permission checking."""
    print("\n" + "=" * 60)
    print("Demo 1: Permission Checker")
    print("=" * 60)

    app_id = os.environ.get("FEISHU_APP_ID", "cli_demo_app_id")

    print("FeishuPermissionChecker helps manage Feishu API permissions.")

    # Show available permission scopes
    print("\nAvailable permission scopes:")
    for feature, permissions in FeishuPermissionChecker.PERMISSIONS.items():
        print(f"  {feature}:")
        for perm in permissions:
            print(f"    - {perm}")

    # Generate authorization URL
    print("\n--- Generating authorization URL ---")
    permissions = FeishuPermissionChecker.PERMISSIONS["image_upload"]
    auth_url = FeishuPermissionChecker.get_auth_url(app_id, permissions)
    print("Auth URL for image upload:")
    print(f"  {auth_url}")

    # Get app config URL
    print("\n--- App configuration URL ---")
    config_url = FeishuPermissionChecker.get_app_config_url(app_id)
    print(f"App config URL: {config_url}")

    # Parse permission error (simulated)
    print("\n--- Parsing permission error ---")
    error_response = {
        "code": 99991672,
        "msg": "permission denied",
    }
    perm_error = FeishuPermissionChecker.parse_permission_error(error_response, app_id)
    if perm_error:
        print("Permission error detected:")
        print(f"  Code: {perm_error.code}")
        print(f"  Message: {perm_error.message}")
        print(f"  Required permissions: {perm_error.required_permissions}")


# =============================================================================
# Demo 2: Image Uploader Setup
# =============================================================================
def demo_image_uploader_setup() -> None:
    """Demonstrate image uploader setup."""
    print("\n" + "=" * 60)
    print("Demo 2: Image Uploader Setup")
    print("=" * 60)

    # Get credentials from environment
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")

    if not app_id or not app_secret:
        print("Note: FEISHU_APP_ID and FEISHU_APP_SECRET not set.")
        print("Using demo values for illustration.")
        app_id = "cli_demo_app_id"
        app_secret = "demo_app_secret"

    print("Creating FeishuImageUploader...")
    print(f"  App ID: {app_id[:10]}...")

    # Create uploader (won't actually connect without valid credentials)
    try:
        uploader = FeishuImageUploader(
            app_id=app_id,
            app_secret=app_secret,
        )
        print("Uploader created successfully")
        print(f"  API Base URL: {uploader.api_base_url}")
    except Exception as e:
        print(f"Error creating uploader: {e}")


# =============================================================================
# Demo 3: Create Image Card
# =============================================================================
def demo_create_image_card() -> None:
    """Demonstrate creating image cards."""
    print("\n" + "=" * 60)
    print("Demo 3: Create Image Card")
    print("=" * 60)

    # Create a simple image card
    print("--- Simple image card ---")
    image_key = "img_v2_example_key"
    card = create_image_card(image_key)

    print("Card structure:")
    print_json(card, indent=2)

    # Create image card with title
    print("\n--- Image card with title ---")
    card_with_title = create_image_card(
        image_key=image_key,
        title="My Image",
    )
    print("Card with title:")
    print_json(card_with_title, indent=2)

    # Create image card with alt text
    print("\n--- Image card with alt text ---")
    card_with_alt = create_image_card(
        image_key=image_key,
        alt_text="A beautiful landscape photo",
    )
    print("Card with alt text:")
    print_json(card_with_alt, indent=2)

    # Create image card with all options
    print("\n--- Full featured image card ---")
    full_card = create_image_card(
        image_key=image_key,
        title="Project Screenshot",
        alt_text="Screenshot of the project dashboard",
        compact_width=False,
    )
    print("Full featured card:")
    print_json(full_card, indent=2)


# =============================================================================
# Demo 4: Image Upload Workflow (Simulated)
# =============================================================================
def demo_upload_workflow() -> None:
    """Demonstrate the image upload workflow (simulated)."""
    print("\n" + "=" * 60)
    print("Demo 4: Image Upload Workflow (Simulated)")
    print("=" * 60)

    print("The image upload workflow consists of these steps:")
    print("\n1. Get tenant access token")
    print("   - POST /open-apis/auth/v3/tenant_access_token/internal")
    print("   - Requires app_id and app_secret")

    print("\n2. Upload image")
    print("   - POST /open-apis/im/v1/images")
    print("   - Requires tenant_access_token")
    print("   - Returns image_key")

    print("\n3. Use image_key in messages")
    print("   - Include image_key in card or rich text messages")

    # Simulated workflow
    print("\n--- Simulated workflow ---")

    class SimulatedUploader:
        """Simulated uploader for demonstration."""

        def __init__(self):
            self.token = "t-demo_token_xxx"
            self.uploaded_images: dict[str, str] = {}

        def get_token(self) -> str:
            print("  [1] Getting tenant access token...")
            print(f"      Token: {self.token[:20]}...")
            return self.token

        def upload_image(self, image_path: str) -> str:
            print(f"  [2] Uploading image: {image_path}")
            image_key = f"img_v2_{hash(image_path) % 10000:04d}"
            self.uploaded_images[image_path] = image_key
            print(f"      Image key: {image_key}")
            return image_key

        def create_message(self, image_key: str) -> dict[str, Any]:
            print(f"  [3] Creating message with image_key: {image_key}")
            return create_image_card(image_key, title="Uploaded Image")

    uploader = SimulatedUploader()
    uploader.get_token()
    image_key = uploader.upload_image("/path/to/image.png")
    uploader.create_message(image_key)
    print("\n  Message ready to send!")


# =============================================================================
# Demo 5: Base64 Image Handling
# =============================================================================
def demo_base64_handling() -> None:
    """Demonstrate base64 image handling."""
    print("\n" + "=" * 60)
    print("Demo 5: Base64 Image Handling")
    print("=" * 60)

    # Create a simple test image (1x1 red pixel PNG)
    # This is a minimal valid PNG file
    png_data = bytes(
        [
            0x89,
            0x50,
            0x4E,
            0x47,
            0x0D,
            0x0A,
            0x1A,
            0x0A,  # PNG signature
            0x00,
            0x00,
            0x00,
            0x0D,
            0x49,
            0x48,
            0x44,
            0x52,  # IHDR chunk
            0x00,
            0x00,
            0x00,
            0x01,
            0x00,
            0x00,
            0x00,
            0x01,  # 1x1
            0x08,
            0x02,
            0x00,
            0x00,
            0x00,
            0x90,
            0x77,
            0x53,
            0xDE,
            0x00,
            0x00,
            0x00,
            0x0C,
            0x49,
            0x44,
            0x41,
            0x54,  # IDAT chunk
            0x08,
            0xD7,
            0x63,
            0xF8,
            0xCF,
            0xC0,
            0x00,
            0x00,
            0x00,
            0x03,
            0x00,
            0x01,
            0x00,
            0x18,
            0xDD,
            0x8D,
            0xB4,
            0x00,
            0x00,
            0x00,
            0x00,
            0x49,
            0x45,
            0x4E,
            0x44,  # IEND chunk
            0xAE,
            0x42,
            0x60,
            0x82,
        ]
    )

    print("Creating a minimal test PNG image...")
    print(f"Image size: {len(png_data)} bytes")

    # Encode to base64
    b64_data = base64.b64encode(png_data).decode("utf-8")
    print(f"\nBase64 encoded length: {len(b64_data)} characters")
    print(f"Base64 preview: {b64_data[:50]}...")

    # Create data URL
    data_url = f"data:image/png;base64,{b64_data}"
    print(f"\nData URL length: {len(data_url)} characters")
    print(f"Data URL preview: {data_url[:60]}...")

    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(png_data)
        temp_path = f.name

    print(f"\nSaved to temporary file: {temp_path}")
    print(f"File size: {Path(temp_path).stat().st_size} bytes")

    # Clean up
    Path(temp_path).unlink()
    print("Temporary file cleaned up")


# =============================================================================
# Demo 6: Error Handling
# =============================================================================
def demo_error_handling() -> None:
    """Demonstrate error handling for image upload."""
    print("\n" + "=" * 60)
    print("Demo 6: Error Handling")
    print("=" * 60)

    print("Common errors when uploading images to Feishu:")

    # Permission denied error
    print("\n--- Permission Denied Error ---")
    try:
        raise FeishuPermissionDeniedError(
            "Permission denied: im:resource scope required",
            required_permissions=["im:resource", "im:resource:upload"],
            auth_url="https://open.feishu.cn/app/xxx/auth",
        )
    except FeishuPermissionDeniedError as e:
        print(f"Error: {e}")
        print(f"Required permissions: {e.required_permissions}")
        print(f"Auth URL: {e.auth_url}")

    # General uploader error
    print("\n--- General Uploader Error ---")
    try:
        raise FeishuImageUploaderError("Failed to upload image: file too large")
    except FeishuImageUploaderError as e:
        print(f"Error: {e}")

    # Error handling pattern
    print("\n--- Recommended error handling pattern ---")
    print(
        """
try:
    image_key = uploader.upload_image("image.png")
except FeishuPermissionDeniedError as e:
    print(f"Permission error: {e}")
    print(f"Please grant permissions at: {e.auth_url}")
    # Optionally open browser
    # webbrowser.open(e.auth_url)
except FeishuImageUploaderError as e:
    print(f"Upload failed: {e}")
    # Handle other errors (network, file not found, etc.)
"""
    )


# =============================================================================
# Demo 7: Integration with Webhook Client
# =============================================================================
def demo_webhook_integration() -> None:
    """Demonstrate integration with webhook client."""
    print("\n" + "=" * 60)
    print("Demo 7: Integration with Webhook Client")
    print("=" * 60)

    print("Example: Sending an image via webhook")
    print(
        """
from feishu_webhook_bot import FeishuBot
from feishu_webhook_bot.core.image_uploader import (
    FeishuImageUploader,
    create_image_card,
)

# Setup
bot = FeishuBot.from_config("config.yaml")
uploader = FeishuImageUploader(
    app_id=os.environ["FEISHU_APP_ID"],
    app_secret=os.environ["FEISHU_APP_SECRET"],
)

# Upload image
image_key = uploader.upload_image("screenshot.png")

# Create and send card
card = create_image_card(
    image_key=image_key,
    title="Daily Report Screenshot",
    alt_text="Screenshot of the daily metrics dashboard",
)

# Send via webhook
bot.client.send_card(card)
"""
    )

    # Show the card structure that would be sent
    print("\n--- Card structure for image message ---")
    sample_card = create_image_card(
        image_key="img_v2_example_xxx",
        title="Daily Report Screenshot",
        alt_text="Screenshot of the daily metrics dashboard",
    )
    print_json(sample_card, indent=2)


# =============================================================================
# Demo 8: Rich Text with Images
# =============================================================================
def demo_rich_text_images() -> None:
    """Demonstrate using images in rich text messages."""
    print("\n" + "=" * 60)
    print("Demo 8: Rich Text with Images")
    print("=" * 60)

    print("Images can also be included in rich text (post) messages:")

    # Rich text structure with image
    rich_text = {
        "title": "Report with Images",
        "content": [
            [
                {"tag": "text", "text": "Here is the dashboard screenshot:"},
            ],
            [
                {
                    "tag": "img",
                    "image_key": "img_v2_example_xxx",
                    "width": 600,
                    "height": 400,
                },
            ],
            [
                {"tag": "text", "text": "And here is the trend chart:"},
            ],
            [
                {
                    "tag": "img",
                    "image_key": "img_v2_example_yyy",
                    "width": 600,
                    "height": 300,
                },
            ],
            [
                {"tag": "text", "text": "Please review and provide feedback."},
            ],
        ],
    }

    print("\nRich text structure with images:")
    print_json(rich_text, indent=2)

    print(
        """
Usage:
    client.send_rich_text(
        title=rich_text["title"],
        content=rich_text["content"],
    )
"""
    )


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
    """Run all image uploader demonstrations."""
    print("=" * 60)
    print("Image Uploader Examples")
    print("=" * 60)

    demos = [
        ("Permission Checker", demo_permission_checker),
        ("Image Uploader Setup", demo_image_uploader_setup),
        ("Create Image Card", demo_create_image_card),
        ("Image Upload Workflow", demo_upload_workflow),
        ("Base64 Image Handling", demo_base64_handling),
        ("Error Handling", demo_error_handling),
        ("Webhook Integration", demo_webhook_integration),
        ("Rich Text with Images", demo_rich_text_images),
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
