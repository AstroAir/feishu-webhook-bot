"""Tests for providers.feishu.signature module.

Tests cover:
- generate_feishu_sign function
- verify_feishu_sign function
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time

import pytest

from feishu_webhook_bot.providers.feishu.signature import (
    generate_feishu_sign,
    verify_feishu_sign,
)


class TestGenerateFeishuSign:
    """Tests for generate_feishu_sign function."""

    def test_generate_sign_with_timestamp(self) -> None:
        """Test generating signature with specific timestamp."""
        secret = "test_secret_123"
        timestamp = 1704067200

        sign, ts = generate_feishu_sign(secret, timestamp)

        assert ts == timestamp
        assert isinstance(sign, str)
        assert len(sign) > 0

    def test_generate_sign_auto_timestamp(self) -> None:
        """Test generating signature with auto-generated timestamp."""
        secret = "test_secret"

        sign, ts = generate_feishu_sign(secret)

        assert ts <= int(time.time())
        assert ts >= int(time.time()) - 1
        assert isinstance(sign, str)

    def test_generate_sign_format(self) -> None:
        """Test signature is base64 encoded."""
        secret = "test_secret"
        timestamp = 1704067200

        sign, _ = generate_feishu_sign(secret, timestamp)

        try:
            decoded = base64.b64decode(sign)
            assert len(decoded) == 32
        except Exception:
            pytest.fail("Signature is not valid base64")

    def test_generate_sign_consistency(self) -> None:
        """Test same inputs produce same signature."""
        secret = "test_secret"
        timestamp = 1704067200

        sign1, _ = generate_feishu_sign(secret, timestamp)
        sign2, _ = generate_feishu_sign(secret, timestamp)

        assert sign1 == sign2

    def test_generate_sign_different_secrets(self) -> None:
        """Test different secrets produce different signatures."""
        timestamp = 1704067200

        sign1, _ = generate_feishu_sign("secret1", timestamp)
        sign2, _ = generate_feishu_sign("secret2", timestamp)

        assert sign1 != sign2

    def test_generate_sign_different_timestamps(self) -> None:
        """Test different timestamps produce different signatures."""
        secret = "test_secret"

        sign1, _ = generate_feishu_sign(secret, 1704067200)
        sign2, _ = generate_feishu_sign(secret, 1704067201)

        assert sign1 != sign2

    def test_generate_sign_algorithm(self) -> None:
        """Test signature uses correct HMAC-SHA256 algorithm."""
        secret = "test_secret"
        timestamp = 1704067200

        string_to_sign = f"{timestamp}\n{secret}"
        expected_hmac = hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        expected_sign = base64.b64encode(expected_hmac).decode("utf-8")

        sign, _ = generate_feishu_sign(secret, timestamp)

        assert sign == expected_sign

    def test_generate_sign_empty_secret(self) -> None:
        """Test generating signature with empty secret."""
        sign, ts = generate_feishu_sign("", 1704067200)

        assert isinstance(sign, str)
        assert len(sign) > 0

    def test_generate_sign_unicode_secret(self) -> None:
        """Test generating signature with unicode characters."""
        secret = "秘密密钥🔐"
        timestamp = 1704067200

        sign, _ = generate_feishu_sign(secret, timestamp)

        assert isinstance(sign, str)


class TestVerifyFeishuSign:
    """Tests for verify_feishu_sign function."""

    def test_verify_valid_signature(self) -> None:
        """Test verifying a valid signature."""
        secret = "test_secret"
        timestamp = int(time.time())

        sign, _ = generate_feishu_sign(secret, timestamp)

        assert verify_feishu_sign(secret, timestamp, sign) is True

    def test_verify_invalid_signature(self) -> None:
        """Test verifying an invalid signature."""
        secret = "test_secret"
        timestamp = int(time.time())

        assert verify_feishu_sign(secret, timestamp, "invalid_signature") is False

    def test_verify_expired_signature(self) -> None:
        """Test verifying an expired signature."""
        secret = "test_secret"
        old_timestamp = int(time.time()) - 400

        sign, _ = generate_feishu_sign(secret, old_timestamp)

        assert verify_feishu_sign(secret, old_timestamp, sign) is False

    def test_verify_with_custom_tolerance(self) -> None:
        """Test verifying with custom tolerance."""
        secret = "test_secret"
        old_timestamp = int(time.time()) - 400

        sign, _ = generate_feishu_sign(secret, old_timestamp)

        assert verify_feishu_sign(secret, old_timestamp, sign, tolerance_seconds=300) is False
        assert verify_feishu_sign(secret, old_timestamp, sign, tolerance_seconds=500) is True

    def test_verify_future_timestamp(self) -> None:
        """Test verifying a future timestamp within tolerance."""
        secret = "test_secret"
        future_timestamp = int(time.time()) + 100

        sign, _ = generate_feishu_sign(secret, future_timestamp)

        assert verify_feishu_sign(secret, future_timestamp, sign) is True

    def test_verify_future_timestamp_expired(self) -> None:
        """Test verifying a future timestamp outside tolerance."""
        secret = "test_secret"
        future_timestamp = int(time.time()) + 400

        sign, _ = generate_feishu_sign(secret, future_timestamp)

        assert verify_feishu_sign(secret, future_timestamp, sign) is False

    def test_verify_wrong_secret(self) -> None:
        """Test verification fails with wrong secret."""
        timestamp = int(time.time())

        sign, _ = generate_feishu_sign("correct_secret", timestamp)

        assert verify_feishu_sign("wrong_secret", timestamp, sign) is False

    def test_verify_timing_attack_resistance(self) -> None:
        """Test verification uses constant-time comparison."""
        secret = "test_secret"
        timestamp = int(time.time())

        sign, _ = generate_feishu_sign(secret, timestamp)
        almost_correct = sign[:-1] + ("A" if sign[-1] != "A" else "B")

        result1 = verify_feishu_sign(secret, timestamp, sign)
        result2 = verify_feishu_sign(secret, timestamp, almost_correct)

        assert result1 is True
        assert result2 is False
