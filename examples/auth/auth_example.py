"""Example: Using the authentication system with NiceGUI and FastAPI.

This example demonstrates:
1. Setting up authentication with NiceGUI
2. Creating login and registration pages
3. Protecting pages with authentication
4. Using FastAPI authentication endpoints
"""

from nicegui import ui

from feishu_webhook_bot.auth.middleware import get_current_nicegui_user, logout_user, require_auth
from feishu_webhook_bot.auth.ui import AuthUI


def setup_authentication_example():
    """Setup authentication example with NiceGUI."""

    # Initialize authentication system
    auth_ui = AuthUI(database_url="sqlite:///./example_auth.db")

    # Public home page
    @ui.page("/")
    def home_page():
        """Public home page."""
        ui.colors(primary="#5898d4")

        with ui.header().classes("items-center justify-between"):
            ui.label("Feishu Webhook Bot").classes("text-h5")

            with ui.row():
                current_user = get_current_nicegui_user()
                if current_user:
                    ui.label(f"Welcome, {current_user['username']}!").classes("q-mr-md")
                    ui.button("Dashboard", on_click=lambda: ui.navigate.to("/dashboard")).props(
                        "flat"
                    )
                    ui.button("Logout", on_click=handle_logout).props("flat")
                else:
                    ui.button("Login", on_click=lambda: ui.navigate.to("/login")).props("flat")
                    ui.button("Register", on_click=lambda: ui.navigate.to("/register")).props(
                        "flat"
                    )

        with ui.column().classes("items-center q-mt-xl"):
            ui.label("Welcome to Feishu Webhook Bot").classes("text-h3 q-mb-md")
            ui.label("A powerful bot framework with authentication").classes(
                "text-subtitle1 text-grey-7"
            )

            with ui.card().classes("q-mt-xl").style("width: 600px; padding: 30px"):
                ui.label("Features").classes("text-h5 q-mb-md")

                features = [
                    "🔐 Secure user authentication",
                    "📨 Rich messaging capabilities",
                    "⏰ Task scheduling",
                    "🔌 Extensible plugin system",
                    "🎨 Beautiful web interface",
                ]

                for feature in features:
                    ui.label(feature).classes("q-mb-sm")

    # Login page
    @ui.page("/login")
    def login_page():
        """Login page."""
        # Check if already logged in
        current_user = get_current_nicegui_user()
        if current_user:
            ui.navigate.to("/dashboard")
            return

        auth_ui.build_login_page()

    # Registration page
    @ui.page("/register")
    def register_page():
        """Registration page."""
        # Check if already logged in
        current_user = get_current_nicegui_user()
        if current_user:
            ui.navigate.to("/dashboard")
            return

        auth_ui.build_registration_page()

    # Protected dashboard page
    @require_auth
    @ui.page("/dashboard")
    def dashboard_page():
        """Protected dashboard page (requires authentication)."""
        ui.colors(primary="#5898d4")

        current_user = get_current_nicegui_user()

        with ui.header().classes("items-center justify-between"):
            ui.label("Dashboard").classes("text-h5")

            with ui.row():
                ui.label(f"Welcome, {current_user['username']}!").classes("q-mr-md")
                ui.button("Home", on_click=lambda: ui.navigate.to("/")).props("flat")
                ui.button("Logout", on_click=handle_logout).props("flat")

        with ui.column().classes("q-pa-md"):
            ui.label("User Dashboard").classes("text-h4 q-mb-md")

            # User info card
            with ui.card().classes("q-mb-md").style("width: 100%; max-width: 600px"):
                ui.label("Account Information").classes("text-h6 q-mb-md")

                with ui.grid(columns=2).classes("w-full"):
                    ui.label("Username:").classes("font-bold")
                    ui.label(current_user["username"])

                    ui.label("Email:").classes("font-bold")
                    ui.label(current_user["email"])

                    ui.label("Account Status:").classes("font-bold")
                    status = "Active" if current_user["is_active"] else "Inactive"
                    ui.label(status).classes(
                        "text-positive" if current_user["is_active"] else "text-negative"
                    )

                    ui.label("Email Verified:").classes("font-bold")
                    verified = "Yes" if current_user["is_verified"] else "No"
                    ui.label(verified).classes(
                        "text-positive" if current_user["is_verified"] else "text-warning"
                    )

            # Actions card
            with ui.card().style("width: 100%; max-width: 600px"):
                ui.label("Quick Actions").classes("text-h6 q-mb-md")

                with ui.row().classes("gap-2"):
                    ui.button("Send Message", icon="send").props("color=primary")
                    ui.button("View Logs", icon="list").props("color=secondary")
                    ui.button("Settings", icon="settings").props("color=grey")

    # Protected settings page
    @require_auth
    @ui.page("/settings")
    def settings_page():
        """Protected settings page."""
        ui.colors(primary="#5898d4")

        current_user = get_current_nicegui_user()

        with ui.header().classes("items-center justify-between"):
            ui.label("Settings").classes("text-h5")

            with ui.row():
                ui.label(f"{current_user['username']}").classes("q-mr-md")
                ui.button("Dashboard", on_click=lambda: ui.navigate.to("/dashboard")).props("flat")
                ui.button("Logout", on_click=handle_logout).props("flat")

        with ui.column().classes("q-pa-md"):
            ui.label("Account Settings").classes("text-h4 q-mb-md")

            with ui.card().style("width: 100%; max-width: 600px"):
                ui.label("Change Password").classes("text-h6 q-mb-md")

                ui.input(label="Current Password", password=True).props("outlined").classes(
                    "w-full"
                )

                ui.input(label="New Password", password=True).props("outlined").classes("w-full")

                ui.input(label="Confirm New Password", password=True).props("outlined").classes(
                    "w-full"
                )

                ui.button("Update Password", icon="lock").props("color=primary").classes("q-mt-md")

    def handle_logout():
        """Handle user logout."""
        logout_user()
        ui.notify("Logged out successfully", type="positive")
        ui.navigate.to("/")


def run_example():
    """Run the authentication example."""
    setup_authentication_example()

    # Run the NiceGUI app
    ui.run(
        host="127.0.0.1",
        port=8080,
        title="Feishu Webhook Bot - Authentication Example",
        show=True,
    )


if __name__ == "__main__":
    print("Starting authentication example...")
    print("Open your browser at http://127.0.0.1:8080")
    print("\nFeatures:")
    print("- Public home page")
    print("- User registration at /register")
    print("- User login at /login")
    print("- Protected dashboard at /dashboard")
    print("- Protected settings at /settings")
    print("\nPress Ctrl+C to stop")

    run_example()
