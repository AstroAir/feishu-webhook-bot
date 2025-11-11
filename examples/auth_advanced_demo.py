#!/usr/bin/env python
"""Advanced Authentication Scenarios Demo.

This example demonstrates advanced authentication scenarios:
- Token refresh workflow
- Multiple concurrent sessions
- Token expiration handling
- Security best practices
- Error handling patterns
- Database session management
- User account management

Run this example:
    python examples/auth_advanced_demo.py
"""

import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from feishu_webhook_bot.auth import AuthService, User, create_access_token
from feishu_webhook_bot.auth.database import init_database
from feishu_webhook_bot.auth.security import decode_access_token, update_security_config
from feishu_webhook_bot.auth.service import AuthenticationError, RegistrationError


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def demo_token_refresh_workflow() -> None:
    """Demonstrate token refresh workflow."""
    print_section("1. Token Refresh Workflow")

    # Configure security
    update_security_config(
        secret_key="demo-secret-key",
        token_expire_minutes=1,  # Short expiration for demo
    )

    user_data = {"sub": "user@example.com", "username": "user", "user_id": 1}

    # Create access token (short-lived)
    print("Creating short-lived access token (1 minute expiration)...")
    access_token = create_access_token(user_data, expires_delta=timedelta(minutes=1))
    print(f"Access token: {access_token[:50]}...")

    # Create refresh token (long-lived)
    print("\nCreating long-lived refresh token (7 days expiration)...")
    refresh_token = create_access_token(
        {**user_data, "type": "refresh"}, expires_delta=timedelta(days=7)
    )
    print(f"Refresh token: {refresh_token[:50]}...")

    # Validate access token
    print("\n--- Validating Access Token ---")
    payload = decode_access_token(access_token)
    if payload:
        print("✓ Access token is valid")
        print(f"  Expires at: {datetime.fromtimestamp(payload['exp'], tz=UTC)}")
    else:
        print("✗ Access token is invalid")

    # Simulate token expiration
    print("\nWaiting for access token to expire (61 seconds)...")
    print("(In production, you would check token expiration before waiting)")
    time.sleep(61)

    # Try to use expired access token
    print("\n--- Using Expired Access Token ---")
    payload = decode_access_token(access_token)
    if payload:
        print("✓ Access token is still valid")
    else:
        print("✗ Access token has expired (expected)")

    # Use refresh token to get new access token
    print("\n--- Using Refresh Token to Get New Access Token ---")
    refresh_payload = decode_access_token(refresh_token)
    if refresh_payload and refresh_payload.get("type") == "refresh":
        print("✓ Refresh token is valid")

        # Create new access token
        new_access_token = create_access_token(user_data, expires_delta=timedelta(minutes=30))
        print(f"✓ New access token created: {new_access_token[:50]}...")

        # Validate new token
        new_payload = decode_access_token(new_access_token)
        if new_payload:
            print("✓ New access token is valid")
            print(f"  Expires at: {datetime.fromtimestamp(new_payload['exp'], tz=UTC)}")
    else:
        print("✗ Refresh token is invalid")


def demo_concurrent_sessions() -> None:
    """Demonstrate handling multiple concurrent sessions."""
    print_section("2. Multiple Concurrent Sessions")

    # Initialize database
    db = init_database("sqlite:///:memory:")
    auth_service = AuthService(db)

    # Register a user
    user = auth_service.register_user(
        email="multiuser@example.com",
        username="multiuser",
        password="SecureP@ss123",
        password_confirm="SecureP@ss123",
    )
    print(f"User registered: {user.username}")

    # Simulate multiple login sessions
    print("\n--- Creating Multiple Sessions ---")
    sessions = []

    for i in range(3):
        user, token = auth_service.authenticate_user("multiuser@example.com", "SecureP@ss123")
        session_id = f"session_{i + 1}"
        sessions.append({"session_id": session_id, "token": token, "user": user})
        print(f"✓ Session {i + 1} created: {token[:30]}...")

    # Validate all sessions
    print("\n--- Validating All Sessions ---")
    for session in sessions:
        payload = decode_access_token(session["token"])
        if payload:
            print(f"✓ {session['session_id']}: Valid (user: {payload.get('username')})")
        else:
            print(f"✗ {session['session_id']}: Invalid")

    print("\nNote: In production, you might want to:")
    print("  • Track active sessions in database")
    print("  • Implement session revocation")
    print("  • Limit concurrent sessions per user")
    print("  • Add device/IP tracking for security")


def demo_error_handling() -> None:
    """Demonstrate comprehensive error handling."""
    print_section("3. Error Handling Patterns")

    db = init_database("sqlite:///:memory:")
    auth_service = AuthService(db)

    # Test various error scenarios
    print("--- Registration Errors ---")

    # Invalid email
    try:
        auth_service.register_user(
            email="invalid-email",
            username="user1",
            password="SecureP@ss123",
            password_confirm="SecureP@ss123",
        )
    except RegistrationError as e:
        print(f"✓ Caught invalid email error: {e}")

    # Username too short
    try:
        auth_service.register_user(
            email="user@example.com",
            username="ab",
            password="SecureP@ss123",
            password_confirm="SecureP@ss123",
        )
    except RegistrationError as e:
        print(f"✓ Caught short username error: {e}")

    # Invalid username characters
    try:
        auth_service.register_user(
            email="user@example.com",
            username="user@123",
            password="SecureP@ss123",
            password_confirm="SecureP@ss123",
        )
    except RegistrationError as e:
        print(f"✓ Caught invalid username error: {e}")

    # Password too long (bcrypt limit)
    try:
        long_password = "A" * 73 + "b1!"
        auth_service.register_user(
            email="user@example.com",
            username="user1",
            password=long_password,
            password_confirm=long_password,
        )
    except (RegistrationError, ValueError) as e:
        print(f"✓ Caught password too long error: {type(e).__name__}")

    print("\n--- Authentication Errors ---")

    # Register a valid user first
    auth_service.register_user(
        email="testuser@example.com",
        username="testuser",
        password="SecureP@ss123",
        password_confirm="SecureP@ss123",
    )

    # Wrong password
    try:
        auth_service.authenticate_user("testuser@example.com", "WrongPassword")
    except AuthenticationError as e:
        print(f"✓ Caught wrong password error: {e}")

    # Non-existent user
    try:
        auth_service.authenticate_user("nobody@example.com", "AnyPassword")
    except AuthenticationError as e:
        print(f"✓ Caught non-existent user error: {e}")


def demo_database_operations() -> None:
    """Demonstrate database session management."""
    print_section("4. Database Session Management")

    db = init_database("sqlite:///:memory:")

    # Manual session management
    print("--- Manual Session Management ---")
    with db.get_session() as session:
        # Create user directly
        user = User(
            email="dbuser@example.com",
            username="dbuser",
            hashed_password="hashed_password_here",
            is_active=True,
            is_verified=False,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        print(f"✓ User created with ID: {user.id}")

    # Query user
    print("\n--- Querying Users ---")
    with db.get_session() as session:
        users = session.query(User).all()
        print(f"Total users in database: {len(users)}")
        for user in users:
            print(f"  • {user.username} ({user.email})")

    # Update user
    print("\n--- Updating User ---")
    with db.get_session() as session:
        user = session.query(User).filter(User.username == "dbuser").first()
        if user:
            print(f"Before: is_verified = {user.is_verified}")
            user.is_verified = True
            session.commit()
            print(f"After: is_verified = {user.is_verified}")

    # Transaction rollback example
    print("\n--- Transaction Rollback ---")
    try:
        with db.get_session() as session:
            user = User(
                email="rollback@example.com",
                username="rollback",
                hashed_password="hash",
                is_active=True,
            )
            session.add(user)
            print("User added to session")

            # Simulate an error
            raise Exception("Simulated error - transaction will rollback")

    except Exception as e:
        print(f"✓ Exception caught: {e}")
        print("✓ Transaction rolled back automatically")

    # Verify user was not created
    with db.get_session() as session:
        user = session.query(User).filter(User.username == "rollback").first()
        if user:
            print("✗ User was created (unexpected)")
        else:
            print("✓ User was not created (rollback successful)")


def demo_security_best_practices() -> None:
    """Demonstrate security best practices."""
    print_section("5. Security Best Practices")

    print("--- Password Security ---")
    print("✓ Use bcrypt for password hashing (automatic salt)")
    print("✓ Enforce strong password requirements")
    print("✓ Never store plain text passwords")
    print("✓ Limit password length to prevent DoS (bcrypt 72-byte limit)")

    print("\n--- Token Security ---")
    print("✓ Use strong secret keys (min 32 characters)")
    print("✓ Set appropriate token expiration times")
    print("✓ Use HTTPS for all authentication endpoints")
    print("✓ Implement token refresh mechanism")
    print("✓ Store tokens securely on client side")

    print("\n--- Account Security ---")
    print("✓ Implement account lockout after failed attempts")
    print("✓ Add email verification")
    print("✓ Log authentication events")
    print("✓ Monitor for suspicious activity")
    print("✓ Implement rate limiting")

    print("\n--- Database Security ---")
    print("✓ Use parameterized queries (SQLAlchemy ORM)")
    print("✓ Implement proper session management")
    print("✓ Use transactions for data consistency")
    print("✓ Regular backups")
    print("✓ Encrypt sensitive data at rest")

    print("\n--- API Security ---")
    print("✓ Validate all input data")
    print("✓ Use CORS properly")
    print("✓ Implement rate limiting")
    print("✓ Add request logging")
    print("✓ Use security headers")


def main() -> None:
    """Run all advanced authentication demos."""
    print("\n" + "=" * 70)
    print("  ADVANCED AUTHENTICATION SCENARIOS")
    print("=" * 70)

    # Run all demos
    demo_token_refresh_workflow()
    demo_concurrent_sessions()
    demo_error_handling()
    demo_database_operations()
    demo_security_best_practices()

    print_section("Demo Complete!")
    print("Advanced authentication scenarios demonstrated successfully.")
    print("\nFor production deployment:")
    print("  1. Use environment variables for secrets")
    print("  2. Implement proper logging and monitoring")
    print("  3. Add comprehensive error handling")
    print("  4. Use production-grade database (PostgreSQL)")
    print("  5. Enable HTTPS/TLS")
    print("  6. Implement rate limiting")
    print("  7. Add security headers")
    print("  8. Regular security audits")
    print("  9. Keep dependencies updated")
    print(" 10. Follow OWASP guidelines")


if __name__ == "__main__":
    main()
