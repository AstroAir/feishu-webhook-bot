#!/usr/bin/env env python
"""Comprehensive Authentication Demo for Feishu Webhook Bot.

This example demonstrates all authentication features including:
- User registration with validation
- Password strength checking
- User login/authentication
- JWT token generation and validation
- Token refresh workflow
- Account lockout after failed attempts
- Email verification
- Database operations

Run this example:
    python examples/auth_demo.py
"""

import sys
from datetime import timedelta
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from feishu_webhook_bot.auth import (
    AuthService,
    create_access_token,
    get_password_hash,
    validate_password_strength,
    verify_password,
)
from feishu_webhook_bot.auth.database import init_database
from feishu_webhook_bot.auth.security import (
    calculate_password_strength,
    decode_access_token,
    update_security_config,
)
from feishu_webhook_bot.auth.service import AuthenticationError, RegistrationError


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def demo_password_validation() -> None:
    """Demonstrate password validation and strength checking."""
    print_section("1. Password Validation and Strength Checking")

    # Test various passwords
    test_passwords = [
        "weak",
        "WeakPass",
        "WeakPass123",
        "StrongP@ss123",
        "VeryStr0ng!P@ssw0rd",
    ]

    for password in test_passwords:
        print(f"Testing password: '{password}'")

        # Check if password meets requirements
        is_valid, errors = validate_password_strength(password)
        print(f"  Valid: {is_valid}")
        if not is_valid:
            print("  Errors:")
            for error in errors:
                print(f"    - {error}")

        # Calculate strength score
        strength = calculate_password_strength(password)
        print(f"  Strength: {strength['score']}% ({strength['level']})")
        if strength["feedback"]:
            print(f"  Suggestions: {', '.join(strength['feedback'])}")
        print()


def demo_password_hashing() -> None:
    """Demonstrate password hashing and verification."""
    print_section("2. Password Hashing and Verification")

    password = "MySecureP@ss123"
    print(f"Original password: {password}")

    # Hash the password
    hashed = get_password_hash(password)
    print(f"Hashed password: {hashed[:50]}...")

    # Verify correct password
    is_correct = verify_password(password, hashed)
    print(f"\nVerify correct password: {is_correct}")

    # Verify incorrect password
    is_incorrect = verify_password("WrongPassword", hashed)
    print(f"Verify incorrect password: {is_incorrect}")


def demo_jwt_tokens() -> None:
    """Demonstrate JWT token creation and validation."""
    print_section("3. JWT Token Generation and Validation")

    # Configure security settings (normally done at app startup)
    update_security_config(
        secret_key="demo-secret-key-change-in-production",
        token_expire_minutes=30,
    )

    # Create a token with user data
    user_data = {
        "sub": "user@example.com",
        "username": "demo_user",
        "user_id": 1,
    }

    print("Creating access token with data:")
    print(f"  {user_data}")

    token = create_access_token(user_data)
    print(f"\nGenerated token: {token[:50]}...")

    # Decode and validate the token
    print("\nDecoding token...")
    payload = decode_access_token(token)
    if payload:
        print("Token is valid!")
        print(f"Payload: {payload}")
    else:
        print("Token is invalid or expired")

    # Test with custom expiration
    print("\n--- Custom Token Expiration ---")
    short_lived_token = create_access_token(user_data, expires_delta=timedelta(seconds=1))
    print("Created token with 1-second expiration")

    # Immediate decode should work
    payload = decode_access_token(short_lived_token)
    print(f"Immediate decode: {'Valid' if payload else 'Invalid'}")

    # Wait and try again
    print("Waiting 2 seconds...")
    import time

    time.sleep(2)
    payload = decode_access_token(short_lived_token)
    print(f"After expiration: {'Valid' if payload else 'Invalid (as expected)'}")


def demo_user_registration() -> None:
    """Demonstrate user registration with validation."""
    print_section("4. User Registration")

    # Initialize database (use in-memory for demo)
    db = init_database("sqlite:///:memory:")
    auth_service = AuthService(db)

    # Successful registration
    print("--- Successful Registration ---")
    try:
        user = auth_service.register_user(
            email="alice@example.com",
            username="alice",
            password="SecureP@ss123",
            password_confirm="SecureP@ss123",
        )
        print("✓ User registered successfully!")
        print(f"  ID: {user.id}")
        print(f"  Username: {user.username}")
        print(f"  Email: {user.email}")
        print(f"  Active: {user.is_active}")
        print(f"  Verified: {user.is_verified}")
    except RegistrationError as e:
        print(f"✗ Registration failed: {e}")

    # Failed registration - weak password
    print("\n--- Failed Registration (Weak Password) ---")
    try:
        user = auth_service.register_user(
            email="bob@example.com",
            username="bob",
            password="weak",
            password_confirm="weak",
        )
        print(f"✓ User registered: {user.username}")
    except RegistrationError as e:
        print(f"✗ Registration failed (expected): {e}")

    # Failed registration - passwords don't match
    print("\n--- Failed Registration (Passwords Don't Match) ---")
    try:
        user = auth_service.register_user(
            email="charlie@example.com",
            username="charlie",
            password="SecureP@ss123",
            password_confirm="DifferentP@ss123",
        )
        print(f"✓ User registered: {user.username}")
    except RegistrationError as e:
        print(f"✗ Registration failed (expected): {e}")

    # Failed registration - duplicate email
    print("\n--- Failed Registration (Duplicate Email) ---")
    try:
        user = auth_service.register_user(
            email="alice@example.com",  # Already registered
            username="alice2",
            password="SecureP@ss123",
            password_confirm="SecureP@ss123",
        )
        print(f"✓ User registered: {user.username}")
    except RegistrationError as e:
        print(f"✗ Registration failed (expected): {e}")

    return auth_service


def demo_user_authentication(auth_service: AuthService) -> None:
    """Demonstrate user authentication and login."""
    print_section("5. User Authentication and Login")

    # Successful login
    print("--- Successful Login ---")
    try:
        user, token = auth_service.authenticate_user("alice@example.com", "SecureP@ss123")
        print("✓ Authentication successful!")
        print(f"  User: {user.username}")
        print(f"  Token: {token[:50]}...")

        # Decode token to show contents
        payload = decode_access_token(token)
        print(f"  Token payload: {payload}")
    except AuthenticationError as e:
        print(f"✗ Authentication failed: {e}")

    # Failed login - wrong password
    print("\n--- Failed Login (Wrong Password) ---")
    try:
        user, token = auth_service.authenticate_user("alice@example.com", "WrongPassword")
        print(f"✓ Authentication successful: {user.username}")
    except AuthenticationError as e:
        print(f"✗ Authentication failed (expected): {e}")

    # Failed login - non-existent user
    print("\n--- Failed Login (Non-existent User) ---")
    try:
        user, token = auth_service.authenticate_user("nobody@example.com", "AnyPassword")
        print(f"✓ Authentication successful: {user.username}")
    except AuthenticationError as e:
        print(f"✗ Authentication failed (expected): {e}")


def demo_account_lockout(auth_service: AuthService) -> None:
    """Demonstrate account lockout after failed login attempts."""
    print_section("6. Account Lockout Protection")

    # Register a test user
    try:
        auth_service.register_user(
            email="locktest@example.com",
            username="locktest",
            password="TestP@ss123",
            password_confirm="TestP@ss123",
        )
        print("Test user created: locktest@example.com")
    except RegistrationError:
        pass  # User might already exist from previous run

    # Attempt multiple failed logins
    print("\nAttempting 5 failed logins to trigger lockout...")
    for i in range(1, 6):
        try:
            auth_service.authenticate_user("locktest@example.com", "WrongPassword")
        except AuthenticationError as e:
            print(f"  Attempt {i}: {e}")

    # Try to login with correct password (should be locked)
    print("\nTrying to login with correct password after lockout...")
    try:
        user, token = auth_service.authenticate_user("locktest@example.com", "TestP@ss123")
        print(f"✓ Login successful: {user.username}")
    except AuthenticationError as e:
        print(f"✗ Login failed (account locked): {e}")

    # Manually unlock the account
    print("\nManually unlocking account...")
    user = auth_service.get_user_by_email("locktest@example.com")
    if user:
        success = auth_service.unlock_account(user.id)
        print(f"  Unlock {'successful' if success else 'failed'}")

        # Try login again
        print("\nTrying to login after manual unlock...")
        try:
            user, token = auth_service.authenticate_user("locktest@example.com", "TestP@ss123")
            print(f"✓ Login successful: {user.username}")
        except AuthenticationError as e:
            print(f"✗ Login failed: {e}")


def demo_user_operations(auth_service: AuthService) -> None:
    """Demonstrate various user operations."""
    print_section("7. User Operations")

    # Get user by email
    print("--- Get User by Email ---")
    user = auth_service.get_user_by_email("alice@example.com")
    if user:
        print(f"Found user: {user.username}")
        print(f"  User dict: {user.to_dict()}")
    else:
        print("User not found")

    # Get user by username
    print("\n--- Get User by Username ---")
    user = auth_service.get_user_by_username("alice")
    if user:
        print(f"Found user: {user.email}")
    else:
        print("User not found")

    # Verify email
    print("\n--- Email Verification ---")
    if user:
        print(f"Before verification: is_verified = {user.is_verified}")
        success = auth_service.verify_email(user.id)
        print(f"Verification {'successful' if success else 'failed'}")

        # Refresh user data
        user = auth_service.get_user_by_id(user.id)
        print(f"After verification: is_verified = {user.is_verified}")


def main() -> None:
    """Run all authentication demos."""
    print("\n" + "=" * 70)
    print("  FEISHU WEBHOOK BOT - AUTHENTICATION DEMO")
    print("=" * 70)

    # Run all demos
    demo_password_validation()
    demo_password_hashing()
    demo_jwt_tokens()
    auth_service = demo_user_registration()
    demo_user_authentication(auth_service)
    demo_account_lockout(auth_service)
    demo_user_operations(auth_service)

    print_section("Demo Complete!")
    print("All authentication features demonstrated successfully.")
    print("\nKey takeaways:")
    print("  • Always validate password strength before hashing")
    print("  • Use bcrypt for secure password hashing")
    print("  • JWT tokens provide stateless authentication")
    print("  • Account lockout protects against brute force attacks")
    print("  • Email verification adds an extra security layer")
    print("\nFor production use:")
    print("  • Change the SECRET_KEY in security.py")
    print("  • Use a production database (PostgreSQL, MySQL)")
    print("  • Enable HTTPS for all authentication endpoints")
    print("  • Implement rate limiting on login endpoints")
    print("  • Add email verification workflow")
    print("  • Consider adding 2FA for enhanced security")


if __name__ == "__main__":
    main()
