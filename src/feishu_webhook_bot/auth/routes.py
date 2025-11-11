"""FastAPI routes for authentication endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..core.logger import get_logger
from .security import calculate_password_strength
from .service import AuthenticationError, AuthService, RegistrationError

logger = get_logger("auth.routes")

# Rate limiter for authentication endpoints
limiter = Limiter(key_func=get_remote_address)

# Create router
router = APIRouter(prefix="/api/auth", tags=["authentication"])


# Request/Response models
class RegisterRequest(BaseModel):
    """Request model for user registration."""

    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(..., min_length=3, max_length=50, description="Desired username")
    password: str = Field(..., min_length=8, description="Password")
    password_confirm: str = Field(..., min_length=8, description="Password confirmation")


class LoginRequest(BaseModel):
    """Request model for user login."""

    login: str = Field(..., description="Email or username")
    password: str = Field(..., description="Password")
    remember_me: bool = Field(default=False, description="Remember me option")


class AuthResponse(BaseModel):
    """Response model for successful authentication."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: dict[str, Any] = Field(..., description="User information")


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str = Field(..., description="Response message")
    success: bool = Field(..., description="Success status")


class PasswordStrengthResponse(BaseModel):
    """Response model for password strength check."""

    score: int = Field(..., description="Password strength score (0-100)")
    level: str = Field(..., description="Strength level (weak/medium/strong)")
    feedback: list[str] = Field(..., description="Improvement suggestions")


# Dependency to get auth service
def get_auth_service() -> AuthService:
    """Get authentication service instance.

    Returns:
        AuthService instance
    """
    return AuthService()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")  # Limit to 5 registration attempts per minute
async def register(
    request: Request, data: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)
) -> AuthResponse:
    """Register a new user.

    Args:
        request: FastAPI request object (for rate limiting)
        data: Registration data
        auth_service: Authentication service

    Returns:
        AuthResponse with access token and user info

    Raises:
        HTTPException: If registration fails
    """
    try:
        user = auth_service.register_user(
            email=data.email,
            username=data.username,
            password=data.password,
            password_confirm=data.password_confirm,
        )

        # Authenticate the newly registered user
        _, access_token = auth_service.authenticate_user(user.email, data.password)

        logger.info(f"User registered and authenticated: {user.username}")

        return AuthResponse(access_token=access_token, token_type="bearer", user=user.to_dict())

    except RegistrationError as e:
        logger.warning(f"Registration failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration",
        ) from e


@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/minute")  # Limit to 10 login attempts per minute
async def login(
    request: Request, data: LoginRequest, auth_service: AuthService = Depends(get_auth_service)
) -> AuthResponse:
    """Authenticate a user and return access token.

    Args:
        request: FastAPI request object (for rate limiting)
        data: Login credentials
        auth_service: Authentication service

    Returns:
        AuthResponse with access token and user info

    Raises:
        HTTPException: If authentication fails
    """
    try:
        user, access_token = auth_service.authenticate_user(data.login, data.password)

        logger.info(f"User logged in: {user.username}")

        return AuthResponse(access_token=access_token, token_type="bearer", user=user.to_dict())

    except AuthenticationError as e:
        logger.warning(f"Login failed for {data.login}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login",
        ) from e


@router.post("/check-password-strength", response_model=PasswordStrengthResponse)
async def check_password_strength(
    password: str = Field(..., min_length=1)
) -> PasswordStrengthResponse:
    """Check password strength and provide feedback.

    Args:
        password: Password to check

    Returns:
        PasswordStrengthResponse with score and feedback
    """
    result = calculate_password_strength(password)
    return PasswordStrengthResponse(**result)


@router.get("/health", response_model=MessageResponse)
async def health_check() -> MessageResponse:
    """Health check endpoint for authentication service.

    Returns:
        MessageResponse indicating service status
    """
    return MessageResponse(message="Authentication service is running", success=True)


def setup_auth_routes(app: Any) -> None:
    """Setup authentication routes on a FastAPI app.

    Args:
        app: FastAPI application instance

    Example:
        ```python
        from fastapi import FastAPI
        from feishu_webhook_bot.auth.routes import setup_auth_routes

        app = FastAPI()
        setup_auth_routes(app)
        ```
    """
    app.include_router(router)
    logger.info("Authentication routes registered")
