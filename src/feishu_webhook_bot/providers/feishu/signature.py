"""Signature generation utilities for Feishu webhook security.

This module provides HMAC-SHA256 signature generation for securing
Feishu webhook requests.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time


def generate_feishu_sign(secret: str, timestamp: int | None = None) -> tuple[str, int]:
    """Generate HMAC-SHA256 signature for Feishu webhook.

    The signature is computed as:
    sign = base64(hmac-sha256(secret, "{timestamp}\\n{secret}"))

    Args:
        secret: Webhook secret key.
        timestamp: Unix timestamp in seconds. If None, current time is used.

    Returns:
        Tuple of (signature, timestamp).

    Example:
        ```python
        sign, ts = generate_feishu_sign("my_secret")
        payload["sign"] = sign
        payload["timestamp"] = str(ts)
        ```
    """
    if timestamp is None:
        timestamp = int(time.time())

    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    signature = base64.b64encode(hmac_code).decode("utf-8")
    return signature, timestamp


def verify_feishu_sign(
    secret: str,
    timestamp: int,
    signature: str,
    tolerance_seconds: int = 300,
) -> bool:
    """Verify Feishu webhook signature.

    Args:
        secret: Webhook secret key.
        timestamp: Timestamp from request.
        signature: Signature from request.
        tolerance_seconds: Maximum age of signature in seconds.

    Returns:
        True if signature is valid and not expired.
    """
    # Check timestamp is within tolerance
    current_time = int(time.time())
    if abs(current_time - timestamp) > tolerance_seconds:
        return False

    # Generate expected signature
    expected_sign, _ = generate_feishu_sign(secret, timestamp)

    # Constant-time comparison
    return hmac.compare_digest(expected_sign, signature)
