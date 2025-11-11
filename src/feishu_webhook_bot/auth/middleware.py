"""Authentication middleware for FastAPI and NiceGUI."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from nicegui import app, ui

from ..core.logger import get_logger
from .security import decode_access_token
from .service import AuthService

logger = get_logger("auth.middleware")

# HTTP Bearer token scheme for FastAPI
security = HTTPBearer()


def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(lambda: AuthService()),
) -> dict[str, Any]:
    """Get current user from JWT token (FastAPI dependency).

    Args:
        credentials: HTTP Bearer credentials
        auth_service: Authentication service

    Returns:
        User data dictionary

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Decode token
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user_email = payload.get("sub")
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = auth_service.get_user_by_email(user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user.to_dict()


def require_auth(func: Callable) -> Callable:
    """Decorator for NiceGUI pages that require authentication.

    This decorator checks if the user is authenticated and redirects
    to the login page if not.

    Args:
        func: Page function to protect

    Returns:
        Wrapped function with authentication check

    Example:
        ```python
        @require_auth
        def protected_page():
            ui.label("This page requires authentication")
        ```
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Check if user is authenticated
        if not hasattr(app.storage, "user") or not app.storage.user.get("authenticated", False):
            logger.warning("Unauthenticated access attempt to protected page")
            ui.navigate.to("/login")
            return None

        # Check if token is still valid
        token = app.storage.user.get("token")
        if token:
            payload = decode_access_token(token)
            if payload is None:
                logger.warning("Expired or invalid token, redirecting to login")
                app.storage.user = {"authenticated": False, "user_data": None, "token": None}  # type: ignore[misc,assignment]
                ui.navigate.to("/login")
                return None

        return func(*args, **kwargs)

    return wrapper


def get_current_nicegui_user() -> dict[str, Any] | None:
    """Get current authenticated user from NiceGUI app storage.

    Returns:
        User data dictionary if authenticated, None otherwise
    """
    if not hasattr(app.storage, "user"):
        return None

    if not app.storage.user.get("authenticated", False):
        return None

    return app.storage.user.get("user_data")


def logout_user() -> None:
    """Logout the current user (clear session).

    This function clears the user session from app storage.
    """
    if hasattr(app.storage, "user"):
        app.storage.user = {"authenticated": False, "user_data": None, "token": None}  # type: ignore[misc,assignment]
        logger.info("User logged out")


class AuthMiddleware:
    """Middleware for FastAPI to handle authentication.

    This middleware can be used to protect entire routes or
    add user context to requests.
    """

    def __init__(self, app: Any) -> None:
        """Initialize the middleware.

        Args:
            app: FastAPI application
        """
        self.app = app

    async def __call__(self, request: Request, call_next: Callable) -> Any:
        """Process request through middleware.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response from next handler
        """
        # Skip authentication for public endpoints
        public_paths = [
            "/api/auth/register",
            "/api/auth/login",
            "/api/auth/health",
            "/api/auth/check-password-strength",
            "/login",
            "/register",
            "/healthz",
        ]

        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)

        # For protected endpoints, verify token if present
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = decode_access_token(token)

            if payload:
                # Add user info to request state
                request.state.user = payload
            else:
                logger.warning(f"Invalid token in request to {request.url.path}")

        response = await call_next(request)
        return response


def setup_auth_middleware(app: Any) -> None:
    """Setup authentication middleware on FastAPI app.

    Args:
        app: FastAPI application

    Example:
        ```python
        from fastapi import FastAPI
        from feishu_webhook_bot.auth.middleware import setup_auth_middleware

        app = FastAPI()
        setup_auth_middleware(app)
        ```
    """
    app.middleware("http")(AuthMiddleware(app))
    logger.info("Authentication middleware registered")
