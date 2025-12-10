#!/usr/bin/env python
"""FastAPI Authentication Integration Demo.

This example demonstrates how to integrate authentication with FastAPI:
- Setting up authentication routes
- Using authentication middleware
- Protected endpoints with JWT tokens
- Token-based API access
- Rate limiting for security

Run this example:
    python examples/auth_api_demo.py

Then test with curl or a browser:
    # Register a user
    curl -X POST http://localhost:8000/api/auth/register \
      -H "Content-Type: application/json" \
      -d '{"email":"test@example.com","username":"testuser",\
"password":"SecureP@ss123","password_confirm":"SecureP@ss123"}'

    # Login
    curl -X POST http://localhost:8000/api/auth/login \
      -H "Content-Type: application/json" \
      -d '{"login":"test@example.com","password":"SecureP@ss123"}'

    # Access protected endpoint
    curl -X GET http://localhost:8000/api/protected/profile \
      -H "Authorization: Bearer YOUR_TOKEN_HERE"
"""

import sys
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from feishu_webhook_bot.auth.database import init_database
from feishu_webhook_bot.auth.middleware import (
    get_current_user_from_token,
    setup_auth_middleware,
)
from feishu_webhook_bot.auth.routes import router as auth_router
from feishu_webhook_bot.auth.security import update_security_config

# Initialize FastAPI app
app = FastAPI(
    title="Feishu Webhook Bot - Auth Demo",
    description="Demonstration of authentication features with FastAPI",
    version="1.0.0",
)

# Add CORS middleware (for web clients)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Response models
class ProfileResponse(BaseModel):
    """User profile response."""

    message: str
    user: dict[str, Any]


class ProtectedDataResponse(BaseModel):
    """Protected data response."""

    message: str
    data: dict[str, Any]
    user: dict[str, Any]


# Include authentication routes
app.include_router(auth_router)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize database and security config on startup."""
    print("Initializing authentication system...")

    # Initialize database (use SQLite for demo)
    init_database("sqlite:///./demo_auth.db")
    print("✓ Database initialized")

    # Configure JWT security
    update_security_config(
        secret_key="demo-secret-key-CHANGE-IN-PRODUCTION",
        token_expire_minutes=60,
    )
    print("✓ Security configuration updated")

    # Setup authentication middleware
    setup_auth_middleware(app)
    print("✓ Authentication middleware registered")

    print("\n" + "=" * 70)
    print("  FastAPI Authentication Demo Server")
    print("=" * 70)
    print("\nServer running at: http://localhost:8000")
    print("API docs available at: http://localhost:8000/docs")
    print("\nExample API calls:")
    print("\n1. Register a user:")
    print("   POST /api/auth/register")
    print(
        '   Body: {"email":"user@example.com","username":"user",'
        '"password":"SecureP@ss123","password_confirm":"SecureP@ss123"}'
    )
    print("\n2. Login:")
    print("   POST /api/auth/login")
    print('   Body: {"login":"user@example.com","password":"SecureP@ss123"}')
    print("\n3. Access protected endpoint:")
    print("   GET /api/protected/profile")
    print("   Header: Authorization: Bearer YOUR_TOKEN")
    print("\n" + "=" * 70 + "\n")


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "message": "Feishu Webhook Bot - Authentication Demo API",
        "docs": "/docs",
        "auth_endpoints": "/api/auth",
        "protected_endpoints": "/api/protected",
    }


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Public health check endpoint."""
    return {"status": "healthy", "service": "auth-demo"}


# Protected endpoints (require authentication)
@app.get("/api/protected/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: dict[str, Any] = Depends(get_current_user_from_token),
) -> ProfileResponse:
    """Get current user's profile (protected endpoint).

    This endpoint requires a valid JWT token in the Authorization header.

    Args:
        current_user: Current authenticated user (injected by dependency)

    Returns:
        User profile information
    """
    return ProfileResponse(
        message="Profile retrieved successfully",
        user=current_user,
    )


@app.get("/api/protected/data", response_model=ProtectedDataResponse)
async def get_protected_data(
    current_user: dict[str, Any] = Depends(get_current_user_from_token),
) -> ProtectedDataResponse:
    """Get protected data (requires authentication).

    This demonstrates how to protect any endpoint with JWT authentication.

    Args:
        current_user: Current authenticated user (injected by dependency)

    Returns:
        Protected data with user context
    """
    # Simulate fetching user-specific data
    user_data = {
        "items": [
            {"id": 1, "name": "Item 1", "value": 100},
            {"id": 2, "name": "Item 2", "value": 200},
        ],
        "total": 2,
        "user_id": current_user.get("id"),
    }

    return ProtectedDataResponse(
        message="Protected data retrieved successfully",
        data=user_data,
        user=current_user,
    )


@app.post("/api/protected/action")
async def perform_action(
    action: str,
    current_user: dict[str, Any] = Depends(get_current_user_from_token),
) -> dict[str, Any]:
    """Perform a protected action (requires authentication).

    Args:
        action: Action to perform
        current_user: Current authenticated user

    Returns:
        Action result
    """
    return {
        "message": f"Action '{action}' performed successfully",
        "performed_by": current_user.get("username"),
        "user_id": current_user.get("id"),
    }


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException) -> dict[str, Any]:
    """Custom error handler for HTTP exceptions."""
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
    }


def print_usage_examples() -> None:
    """Print usage examples for testing the API."""
    print("\n" + "=" * 70)
    print("  TESTING THE API")
    print("=" * 70)
    print("\nUsing curl:")
    print("\n# 1. Register a new user")
    print("curl -X POST http://localhost:8000/api/auth/register \\")
    print('  -H "Content-Type: application/json" \\')
    print(
        '  -d \'{"email":"demo@example.com","username":"demo",'
        '"password":"DemoP@ss123","password_confirm":"DemoP@ss123"}\''
    )

    print("\n# 2. Login to get access token")
    print("curl -X POST http://localhost:8000/api/auth/login \\")
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"login":"demo@example.com","password":"DemoP@ss123"}\'')

    print("\n# 3. Check password strength")
    print("curl -X POST http://localhost:8000/api/auth/check-password-strength \\")
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"password":"TestPassword123!"}\'')

    print("\n# 4. Access protected endpoint (replace TOKEN with actual token)")
    print("curl -X GET http://localhost:8000/api/protected/profile \\")
    print('  -H "Authorization: Bearer TOKEN"')

    print("\n# 5. Get protected data")
    print("curl -X GET http://localhost:8000/api/protected/data \\")
    print('  -H "Authorization: Bearer TOKEN"')

    print("\n" + "=" * 70)
    print("\nUsing Python requests:")
    print(
        """
import requests

# Register
response = requests.post(
    "http://localhost:8000/api/auth/register",
    json={
        "email": "demo@example.com",
        "username": "demo",
        "password": "DemoP@ss123",
        "password_confirm": "DemoP@ss123"
    }
)
print(response.json())

# Login
response = requests.post(
    "http://localhost:8000/api/auth/login",
    json={
        "login": "demo@example.com",
        "password": "DemoP@ss123"
    }
)
data = response.json()
token = data["access_token"]

# Access protected endpoint
response = requests.get(
    "http://localhost:8000/api/protected/profile",
    headers={"Authorization": f"Bearer {token}"}
)
print(response.json())
"""
    )
    print("=" * 70 + "\n")


def main() -> None:
    """Run the FastAPI demo server."""
    print_usage_examples()

    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )


if __name__ == "__main__":
    main()
