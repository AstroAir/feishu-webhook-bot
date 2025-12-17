"""NiceGUI authentication pages for login and registration."""

from __future__ import annotations

import re
from typing import Any

from nicegui import app, ui

from ..core.logger import get_logger
from .database import init_database
from .security import calculate_password_strength
from .service import AuthenticationError, AuthService, RegistrationError

logger = get_logger("auth.ui")


class AuthUI:
    """Authentication UI manager for NiceGUI pages."""

    def __init__(self, database_url: str | None = None) -> None:
        """Initialize authentication UI.

        Args:
            database_url: Database URL for authentication (defaults to sqlite:///./auth.db)
        """
        # Initialize database
        self.db_manager = init_database(database_url)
        self.auth_service = AuthService(self.db_manager)

        # Store current user in app storage
        if not hasattr(app.storage, "user"):
            app.storage.user = {"authenticated": False, "user_data": None, "token": None}  # type: ignore[misc,assignment]

    def build_registration_page(self) -> None:
        """Build the registration page with NiceGUI components."""
        ui.colors(primary="#5898d4")

        with ui.card().classes("absolute-center").style("width: 450px; padding: 30px"):
            ui.label("Create Account").classes("text-h4 text-center q-mb-md")
            ui.label("Register for Feishu Webhook Bot").classes(
                "text-subtitle2 text-center text-grey-7 q-mb-lg"
            )

            # Email field
            email_input = (
                ui.input(
                    label="Email",
                    placeholder="your.email@example.com",
                    validation={"Invalid email format": lambda value: self._validate_email(value)},
                )
                .props("outlined")
                .classes("w-full")
            )

            # Username field
            username_input = (
                ui.input(
                    label="Username",
                    placeholder="username",
                    validation={
                        "Username must be 3-50 characters": lambda value: 3 <= len(value) <= 50,
                        "Only letters, numbers, hyphens, and underscores allowed": (
                            lambda value: bool(re.match(r"^[a-zA-Z0-9_-]+$", value))
                        ),
                    },
                )
                .props("outlined")
                .classes("w-full")
            )

            # Password field with visibility toggle
            password_visible = {"value": False}

            with ui.row().classes("w-full items-center"):
                password_input = (
                    ui.input(
                        label="Password",
                        placeholder="Enter password",
                        password=True,
                    )
                    .props("outlined")
                    .classes("flex-grow")
                )

                ui.button(
                    icon="visibility" if not password_visible["value"] else "visibility_off",
                    on_click=lambda: self._toggle_password_visibility(
                        password_input, password_visible
                    ),
                ).props("flat round").classes("q-ml-sm")

            # Password strength indicator
            strength_label = ui.label("").classes("text-caption q-mt-xs")
            strength_bar = ui.linear_progress(value=0, show_value=False).classes("q-mt-xs")

            # Update password strength on input
            password_input.on(
                "input",
                lambda e: self._update_password_strength(
                    e.sender.value, strength_label, strength_bar
                ),
            )

            # Password confirmation field
            password_confirm_input = (
                ui.input(
                    label="Confirm Password",
                    placeholder="Re-enter password",
                    password=True,
                    validation={
                        "Passwords must match": lambda value: value == password_input.value
                    },
                )
                .props("outlined")
                .classes("w-full")
            )

            # Error message display
            error_label = ui.label("").classes("text-negative text-caption q-mt-sm")
            error_label.visible = False

            # Loading state
            loading = {"value": False}

            # Register button
            async def handle_register() -> None:
                """Handle registration form submission."""
                error_label.visible = False
                loading["value"] = True

                try:
                    # Validate all fields
                    if not email_input.value or not username_input.value:
                        raise ValueError("Please fill in all fields")

                    if not password_input.value or not password_confirm_input.value:
                        raise ValueError("Please enter and confirm your password")

                    # Attempt registration
                    user = self.auth_service.register_user(
                        email=email_input.value,
                        username=username_input.value,
                        password=password_input.value,
                        password_confirm=password_confirm_input.value,
                    )

                    # Authenticate the user
                    user_obj, token = self.auth_service.authenticate_user(
                        user.email, password_input.value
                    )

                    # Store user session
                    app.storage.user = {  # type: ignore[misc,assignment]
                        "authenticated": True,
                        "user_data": user_obj.to_dict(),
                        "token": token,
                    }

                    ui.notify("Registration successful! Welcome!", type="positive")
                    logger.info(f"User registered via UI: {username_input.value}")

                    # Redirect to main page after short delay
                    await ui.run_javascript("setTimeout(() => window.location.href = '/', 1500)")

                except RegistrationError as e:
                    error_label.text = str(e)
                    error_label.visible = True
                    ui.notify(str(e), type="negative")
                except ValueError as e:
                    error_label.text = str(e)
                    error_label.visible = True
                except Exception as e:
                    logger.error(f"Registration error: {str(e)}", exc_info=True)
                    error_label.text = "An unexpected error occurred"
                    error_label.visible = True
                    ui.notify("Registration failed", type="negative")
                finally:
                    loading["value"] = False

            ui.button(
                "Create Account",
                on_click=handle_register,
            ).props("unelevated color=primary").classes("w-full q-mt-md").bind_enabled_from(
                loading, "value", backward=lambda x: not x
            )

            # Link to login page
            with ui.row().classes("w-full justify-center q-mt-md"):
                ui.label("Already have an account?").classes("text-caption")
                ui.link("Sign in", "/login").classes("text-caption text-primary")

    def build_login_page(self) -> None:
        """Build the login page with NiceGUI components."""
        ui.colors(primary="#5898d4")

        with ui.card().classes("absolute-center").style("width: 400px; padding: 30px"):
            ui.label("Welcome Back").classes("text-h4 text-center q-mb-md")
            ui.label("Sign in to your account").classes(
                "text-subtitle2 text-center text-grey-7 q-mb-lg"
            )

            # Login field (email or username)
            login_input = (
                ui.input(label="Email or Username", placeholder="Enter your email or username")
                .props("outlined")
                .classes("w-full")
            )

            # Password field with visibility toggle
            password_visible = {"value": False}

            with ui.row().classes("w-full items-center"):
                password_input = (
                    ui.input(label="Password", placeholder="Enter password", password=True)
                    .props("outlined")
                    .classes("flex-grow")
                )

                ui.button(
                    icon="visibility" if not password_visible["value"] else "visibility_off",
                    on_click=lambda: self._toggle_password_visibility(
                        password_input, password_visible
                    ),
                ).props("flat round").classes("q-ml-sm")

            # Remember me checkbox
            remember_me = ui.checkbox("Remember me").classes("q-mt-sm")

            # Error message display
            error_label = ui.label("").classes("text-negative text-caption q-mt-sm")
            error_label.visible = False

            # Loading state
            loading = {"value": False}

            # Login button
            async def handle_login() -> None:
                """Handle login form submission."""
                error_label.visible = False
                loading["value"] = True

                try:
                    if not login_input.value or not password_input.value:
                        raise ValueError("Please enter your credentials")

                    # Attempt authentication
                    user, token = self.auth_service.authenticate_user(
                        login_input.value, password_input.value
                    )

                    # Store user session
                    app.storage.user = {  # type: ignore[misc,assignment]
                        "authenticated": True,
                        "user_data": user.to_dict(),
                        "token": token,
                        "remember_me": remember_me.value,
                    }

                    ui.notify(f"Welcome back, {user.username}!", type="positive")
                    logger.info(f"User logged in via UI: {user.username}")

                    # Redirect to main page
                    await ui.run_javascript("setTimeout(() => window.location.href = '/', 1000)")

                except AuthenticationError as e:
                    error_label.text = str(e)
                    error_label.visible = True
                    ui.notify(str(e), type="negative")
                except ValueError as e:
                    error_label.text = str(e)
                    error_label.visible = True
                except Exception as e:
                    logger.error(f"Login error: {str(e)}", exc_info=True)
                    error_label.text = "An unexpected error occurred"
                    error_label.visible = True
                    ui.notify("Login failed", type="negative")
                finally:
                    loading["value"] = False

            ui.button("Sign In", on_click=handle_login).props("unelevated color=primary").classes(
                "w-full q-mt-md"
            ).bind_enabled_from(loading, "value", backward=lambda x: not x)

            # Link to registration page
            with ui.row().classes("w-full justify-center q-mt-md"):
                ui.label("Don't have an account?").classes("text-caption")
                ui.link("Create one", "/register").classes("text-caption text-primary")

    # Helper methods
    def _validate_email(self, email: str) -> bool:
        """Validate email format.

        Args:
            email: Email address to validate

        Returns:
            True if valid, False otherwise
        """
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def _toggle_password_visibility(self, password_input: Any, visible_state: dict) -> None:
        """Toggle password visibility.

        Args:
            password_input: Password input component
            visible_state: Dictionary tracking visibility state
        """
        visible_state["value"] = not visible_state["value"]
        password_input.password = not visible_state["value"]

    def _update_password_strength(self, password: str, label: Any, progress_bar: Any) -> None:
        """Update password strength indicator.

        Args:
            password: Current password value
            label: Label component to update
            progress_bar: Progress bar component to update
        """
        if not password:
            label.text = ""
            progress_bar.value = 0
            return

        result = calculate_password_strength(password)
        score = result["score"]
        level = result["level"]

        # Update label
        if level == "weak":
            label.text = "Weak password"
            label.classes("text-negative", remove="text-warning text-positive")
        elif level == "medium":
            label.text = "Medium password"
            label.classes("text-warning", remove="text-negative text-positive")
        else:
            label.text = "Strong password"
            label.classes("text-positive", remove="text-negative text-warning")

        # Update progress bar
        progress_bar.value = score / 100
