# Authentication System

The Feishu Webhook Bot includes a complete and secure authentication system for user management and access control.

## Features

- **User Registration**: Secure user registration with email and username
- **User Login**: JWT-based authentication with session management
- **Password Security**:
  - Bcrypt password hashing
  - Password strength validation
  - Password strength indicator in UI
- **Security Features**:
  - Rate limiting to prevent brute force attacks
  - Account lockout after failed login attempts
  - Email validation
  - Input sanitization
  - CSRF protection (when using session-based auth)
- **NiceGUI Integration**: Beautiful login and registration pages
- **FastAPI Endpoints**: RESTful API for authentication

## Quick Start

### 1. Enable Authentication

Add authentication configuration to your `config.yaml`:

```yaml
auth:
  enabled: true
  database_url: "sqlite:///./auth.db"
  jwt_secret_key: "your-super-secret-key-change-in-production"
  jwt_algorithm: "HS256"
  access_token_expire_minutes: 30
  max_failed_attempts: 5
  lockout_duration_minutes: 30
  require_email_verification: false
```

**Important**: Always change the `jwt_secret_key` in production! Use a strong, random secret key.

### 2. Initialize the Database

The authentication system uses SQLAlchemy with SQLite by default. The database will be automatically created when you first use the authentication features.

To manually initialize:

```python
from feishu_webhook_bot.auth.database import init_database

# Initialize with default SQLite database
db = init_database()

# Or specify a custom database URL
db = init_database("postgresql://user:pass@localhost/dbname")
```

### 3. Add Authentication Routes to Your App

If you're using the web UI, authentication routes are automatically available:

```python
from feishu_webhook_bot.auth.ui import AuthUI

# Initialize authentication UI
auth_ui = AuthUI(database_url="sqlite:///./auth.db")

# Register pages
@ui.page("/register")
def register_page():
    auth_ui.build_registration_page()

@ui.page("/login")
def login_page():
    auth_ui.build_login_page()
```

For FastAPI applications:

```python
from fastapi import FastAPI
from feishu_webhook_bot.auth.routes import setup_auth_routes

app = FastAPI()
setup_auth_routes(app)
```

## Configuration Options

### AuthConfig

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | `false` | Enable authentication system |
| `database_url` | str | `"sqlite:///./auth.db"` | Database URL (SQLAlchemy format) |
| `jwt_secret_key` | str | `"change-this..."` | Secret key for JWT signing |
| `jwt_algorithm` | str | `"HS256"` | JWT signing algorithm |
| `access_token_expire_minutes` | int | `30` | Token expiration time |
| `max_failed_attempts` | int | `5` | Max failed login attempts |
| `lockout_duration_minutes` | int | `30` | Account lockout duration |
| `require_email_verification` | bool | `false` | Require email verification |

## Password Requirements

Passwords must meet the following criteria:

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (!@#$%^&*(),.?":{}|<>)

## API Endpoints

### POST /api/auth/register

Register a new user.

**Request Body:**

```json
{
  "email": "user@example.com",
  "username": "username",
  "password": "StrongPass123!",
  "password_confirm": "StrongPass123!"
}
```

**Response (201 Created):**

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "username",
    "is_active": true,
    "is_verified": false,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

**Rate Limit:** 5 requests per minute

### POST /api/auth/login

Authenticate a user.

**Request Body:**

```json
{
  "login": "user@example.com",
  "password": "StrongPass123!",
  "remember_me": false
}
```

**Response (200 OK):**

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "username",
    "is_active": true,
    "is_verified": false
  }
}
```

**Rate Limit:** 10 requests per minute

### POST /api/auth/check-password-strength

Check password strength.

**Request Body:**

```json
{
  "password": "MyPassword123!"
}
```

**Response:**

```json
{
  "score": 85,
  "level": "strong",
  "feedback": []
}
```

## Using Authentication in Your Code

### Programmatic User Registration

```python
from feishu_webhook_bot.auth.service import AuthService

auth_service = AuthService()

try:
    user = auth_service.register_user(
        email="user@example.com",
        username="myusername",
        password="StrongPass123!",
        password_confirm="StrongPass123!"
    )
    print(f"User registered: {user.username}")
except RegistrationError as e:
    print(f"Registration failed: {e}")
```

### Programmatic User Authentication

```python
from feishu_webhook_bot.auth.service import AuthService

auth_service = AuthService()

try:
    user, token = auth_service.authenticate_user(
        login="user@example.com",
        password="StrongPass123!"
    )
    print(f"Authenticated: {user.username}")
    print(f"Token: {token}")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
```

### Protecting NiceGUI Pages

```python
from nicegui import ui
from feishu_webhook_bot.auth.middleware import require_auth

@require_auth
@ui.page("/protected")
def protected_page():
    ui.label("This page requires authentication")
```

### Protecting FastAPI Endpoints

```python
from fastapi import Depends
from feishu_webhook_bot.auth.middleware import get_current_user_from_token

@app.get("/api/protected")
def protected_endpoint(current_user: dict = Depends(get_current_user_from_token)):
    return {"message": f"Hello, {current_user['username']}!"}
```

## Security Best Practices

### Production Deployment

1. **Change the JWT Secret Key**: Generate a strong, random secret key

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Use HTTPS**: Always use HTTPS in production to protect credentials in transit

3. **Use a Production Database**: Switch from SQLite to PostgreSQL or MySQL for production

   ```yaml
   auth:
     database_url: "postgresql://user:password@localhost/dbname"
   ```

4. **Enable Email Verification**: Set `require_email_verification: true` and implement email sending

5. **Configure Rate Limiting**: Adjust rate limits based on your needs

6. **Regular Security Updates**: Keep all dependencies up to date

### Password Storage

- Passwords are hashed using bcrypt with automatic salt generation
- Never store plain text passwords
- Password hashes are never exposed in API responses

### Token Security

- JWT tokens are signed with HS256 algorithm
- Tokens include expiration time
- Tokens should be stored securely on the client side
- Use HTTPS to prevent token interception

### Account Lockout

- Accounts are locked after 5 failed login attempts (configurable)
- Lockout duration is 30 minutes (configurable)
- Failed attempt counter resets on successful login
- Administrators can manually unlock accounts

## Database Schema

### Users Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `email` | String(255) | Unique email address |
| `username` | String(100) | Unique username |
| `hashed_password` | String(255) | Bcrypt hashed password |
| `is_active` | Boolean | Account active status |
| `is_verified` | Boolean | Email verification status |
| `created_at` | DateTime | Account creation time |
| `updated_at` | DateTime | Last update time |
| `failed_login_attempts` | Integer | Failed login counter |
| `locked_until` | DateTime | Account lock expiration |

## Troubleshooting

### Database Connection Issues

If you encounter database connection errors:

1. Check the `database_url` in your configuration
2. Ensure the database file/server is accessible
3. Verify database permissions
4. Check SQLAlchemy logs for detailed errors

### Token Validation Failures

If tokens are not validating:

1. Verify the `jwt_secret_key` matches between token creation and validation
2. Check token expiration time
3. Ensure the token is being sent in the `Authorization` header as `Bearer <token>`

### Account Lockout Issues

If accounts are getting locked unexpectedly:

1. Check the `max_failed_attempts` setting
2. Review authentication logs
3. Use `auth_service.unlock_account(user_id)` to manually unlock

## Examples

See the complete example in `examples/auth_example.py` for a full implementation.

## Testing

Run the authentication tests:

```bash
uv run pytest tests/test_auth.py -v
```

## Support

For issues or questions about the authentication system, please:

1. Check this documentation
2. Review the code examples
3. Check the test files for usage patterns
4. Open an issue on GitHub
