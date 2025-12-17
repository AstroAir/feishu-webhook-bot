"""Comprehensive tests for authentication UI module.

Tests cover:
- AuthUI class initialization
- Email validation
- Password visibility toggle
- Password strength update
- Registration page building
- Login page building
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

# Mock nicegui before importing ui module
sys.modules["nicegui"] = MagicMock()

from feishu_webhook_bot.auth.ui import AuthUI

# ==============================================================================
# AuthUI Initialization Tests
# ==============================================================================


class TestAuthUIInitialization:
    """Tests for AuthUI initialization."""

    def test_init_with_default_database(self):
        """Test AuthUI initialization with default database."""
        with patch("feishu_webhook_bot.auth.ui.init_database") as mock_init_db:
            with patch("feishu_webhook_bot.auth.ui.AuthService") as mock_service:
                with patch("feishu_webhook_bot.auth.ui.app") as mock_app:
                    mock_db_manager = MagicMock()
                    mock_init_db.return_value = mock_db_manager
                    mock_app.storage.user = {}

                    auth_ui = AuthUI()

                    mock_init_db.assert_called_once_with(None)
                    mock_service.assert_called_once_with(mock_db_manager)
                    assert auth_ui.db_manager == mock_db_manager

    def test_init_with_custom_database_url(self):
        """Test AuthUI initialization with custom database URL."""
        with patch("feishu_webhook_bot.auth.ui.init_database") as mock_init_db:
            with patch("feishu_webhook_bot.auth.ui.AuthService"):
                with patch("feishu_webhook_bot.auth.ui.app") as mock_app:
                    mock_app.storage.user = {}

                    AuthUI(database_url="sqlite:///custom.db")

                    mock_init_db.assert_called_once_with("sqlite:///custom.db")

    def test_init_creates_storage_if_missing(self):
        """Test AuthUI creates storage.user if missing."""
        with patch("feishu_webhook_bot.auth.ui.init_database"):
            with patch("feishu_webhook_bot.auth.ui.AuthService"):
                with patch("feishu_webhook_bot.auth.ui.app") as mock_app:
                    # Simulate missing user attribute
                    del mock_app.storage.user

                    AuthUI()

                    # Should create the user storage
                    assert mock_app.storage.user == {
                        "authenticated": False,
                        "user_data": None,
                        "token": None,
                    }


# ==============================================================================
# Email Validation Tests
# ==============================================================================


class TestEmailValidation:
    """Tests for email validation."""

    def test_valid_email(self):
        """Test valid email passes validation."""
        with patch("feishu_webhook_bot.auth.ui.init_database"):
            with patch("feishu_webhook_bot.auth.ui.AuthService"):
                with patch("feishu_webhook_bot.auth.ui.app") as mock_app:
                    mock_app.storage.user = {}

                    auth_ui = AuthUI()

                    assert auth_ui._validate_email("test@example.com") is True
                    assert auth_ui._validate_email("user.name@domain.org") is True
                    assert auth_ui._validate_email("user+tag@example.co.uk") is True

    def test_invalid_email(self):
        """Test invalid email fails validation."""
        with patch("feishu_webhook_bot.auth.ui.init_database"):
            with patch("feishu_webhook_bot.auth.ui.AuthService"):
                with patch("feishu_webhook_bot.auth.ui.app") as mock_app:
                    mock_app.storage.user = {}

                    auth_ui = AuthUI()

                    assert auth_ui._validate_email("invalid") is False
                    assert auth_ui._validate_email("no-at-sign.com") is False
                    assert auth_ui._validate_email("@nodomain.com") is False
                    assert auth_ui._validate_email("spaces in@email.com") is False


# ==============================================================================
# Password Visibility Toggle Tests
# ==============================================================================


class TestPasswordVisibilityToggle:
    """Tests for password visibility toggle."""

    def test_toggle_visibility_on(self):
        """Test toggling password visibility on."""
        with patch("feishu_webhook_bot.auth.ui.init_database"):
            with patch("feishu_webhook_bot.auth.ui.AuthService"):
                with patch("feishu_webhook_bot.auth.ui.app") as mock_app:
                    mock_app.storage.user = {}

                    auth_ui = AuthUI()

                    mock_input = MagicMock()
                    mock_input.password = True
                    visible_state = {"value": False}

                    auth_ui._toggle_password_visibility(mock_input, visible_state)

                    assert visible_state["value"] is True
                    assert mock_input.password is False

    def test_toggle_visibility_off(self):
        """Test toggling password visibility off."""
        with patch("feishu_webhook_bot.auth.ui.init_database"):
            with patch("feishu_webhook_bot.auth.ui.AuthService"):
                with patch("feishu_webhook_bot.auth.ui.app") as mock_app:
                    mock_app.storage.user = {}

                    auth_ui = AuthUI()

                    mock_input = MagicMock()
                    mock_input.password = False
                    visible_state = {"value": True}

                    auth_ui._toggle_password_visibility(mock_input, visible_state)

                    assert visible_state["value"] is False
                    assert mock_input.password is True


# ==============================================================================
# Password Strength Update Tests
# ==============================================================================


class TestPasswordStrengthUpdate:
    """Tests for password strength update."""

    def test_empty_password(self):
        """Test empty password clears indicators."""
        with patch("feishu_webhook_bot.auth.ui.init_database"):
            with patch("feishu_webhook_bot.auth.ui.AuthService"):
                with patch("feishu_webhook_bot.auth.ui.app") as mock_app:
                    mock_app.storage.user = {}

                    auth_ui = AuthUI()

                    mock_label = MagicMock()
                    mock_progress = MagicMock()

                    auth_ui._update_password_strength("", mock_label, mock_progress)

                    assert mock_label.text == ""
                    assert mock_progress.value == 0

    def test_weak_password_indicator(self):
        """Test weak password shows correct indicator."""
        with patch("feishu_webhook_bot.auth.ui.init_database"):
            with patch("feishu_webhook_bot.auth.ui.AuthService"):
                with patch("feishu_webhook_bot.auth.ui.app") as mock_app:
                    with patch(
                        "feishu_webhook_bot.auth.ui.calculate_password_strength"
                    ) as mock_calc:
                        mock_app.storage.user = {}
                        mock_calc.return_value = {"score": 20, "level": "weak"}

                        auth_ui = AuthUI()

                        mock_label = MagicMock()
                        mock_progress = MagicMock()

                        auth_ui._update_password_strength("weak", mock_label, mock_progress)

                        assert mock_label.text == "Weak password"
                        assert mock_progress.value == 0.2

    def test_medium_password_indicator(self):
        """Test medium password shows correct indicator."""
        with patch("feishu_webhook_bot.auth.ui.init_database"):
            with patch("feishu_webhook_bot.auth.ui.AuthService"):
                with patch("feishu_webhook_bot.auth.ui.app") as mock_app:
                    with patch(
                        "feishu_webhook_bot.auth.ui.calculate_password_strength"
                    ) as mock_calc:
                        mock_app.storage.user = {}
                        mock_calc.return_value = {"score": 50, "level": "medium"}

                        auth_ui = AuthUI()

                        mock_label = MagicMock()
                        mock_progress = MagicMock()

                        auth_ui._update_password_strength("Medium1", mock_label, mock_progress)

                        assert mock_label.text == "Medium password"
                        assert mock_progress.value == 0.5

    def test_strong_password_indicator(self):
        """Test strong password shows correct indicator."""
        with patch("feishu_webhook_bot.auth.ui.init_database"):
            with patch("feishu_webhook_bot.auth.ui.AuthService"):
                with patch("feishu_webhook_bot.auth.ui.app") as mock_app:
                    with patch(
                        "feishu_webhook_bot.auth.ui.calculate_password_strength"
                    ) as mock_calc:
                        mock_app.storage.user = {}
                        mock_calc.return_value = {"score": 90, "level": "strong"}

                        auth_ui = AuthUI()

                        mock_label = MagicMock()
                        mock_progress = MagicMock()

                        auth_ui._update_password_strength(
                            "StrongP@ss123!", mock_label, mock_progress
                        )

                        assert mock_label.text == "Strong password"
                        assert mock_progress.value == 0.9


# ==============================================================================
# Page Building Tests
# ==============================================================================


class TestPageBuilding:
    """Tests for page building methods."""

    def test_build_registration_page_creates_components(self):
        """Test build_registration_page creates UI components."""
        with patch("feishu_webhook_bot.auth.ui.init_database"):
            with patch("feishu_webhook_bot.auth.ui.AuthService"):
                with patch("feishu_webhook_bot.auth.ui.app") as mock_app:
                    with patch("feishu_webhook_bot.auth.ui.ui") as mock_ui:
                        mock_app.storage.user = {}

                        # Setup mock context managers
                        mock_card = MagicMock()
                        mock_card.__enter__ = MagicMock(return_value=mock_card)
                        mock_card.__exit__ = MagicMock(return_value=None)
                        mock_ui.card.return_value = mock_card

                        mock_row = MagicMock()
                        mock_row.__enter__ = MagicMock(return_value=mock_row)
                        mock_row.__exit__ = MagicMock(return_value=None)
                        mock_ui.row.return_value = mock_row

                        auth_ui = AuthUI()
                        auth_ui.build_registration_page()

                        # Verify UI components were created
                        mock_ui.colors.assert_called()
                        mock_ui.card.assert_called()
                        mock_ui.label.assert_called()
                        mock_ui.input.assert_called()
                        mock_ui.button.assert_called()

    def test_build_login_page_creates_components(self):
        """Test build_login_page creates UI components."""
        with patch("feishu_webhook_bot.auth.ui.init_database"):
            with patch("feishu_webhook_bot.auth.ui.AuthService"):
                with patch("feishu_webhook_bot.auth.ui.app") as mock_app:
                    with patch("feishu_webhook_bot.auth.ui.ui") as mock_ui:
                        mock_app.storage.user = {}

                        # Setup mock context managers
                        mock_card = MagicMock()
                        mock_card.__enter__ = MagicMock(return_value=mock_card)
                        mock_card.__exit__ = MagicMock(return_value=None)
                        mock_ui.card.return_value = mock_card

                        mock_row = MagicMock()
                        mock_row.__enter__ = MagicMock(return_value=mock_row)
                        mock_row.__exit__ = MagicMock(return_value=None)
                        mock_ui.row.return_value = mock_row

                        auth_ui = AuthUI()
                        auth_ui.build_login_page()

                        # Verify UI components were created
                        mock_ui.colors.assert_called()
                        mock_ui.card.assert_called()
                        mock_ui.label.assert_called()
                        mock_ui.input.assert_called()
                        mock_ui.button.assert_called()
                        mock_ui.checkbox.assert_called()  # Remember me checkbox
