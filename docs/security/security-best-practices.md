# Security Best Practices

Comprehensive security guide for deploying and operating the Feishu Webhook Bot.

## Table of Contents

- [Overview](#overview)
- [Secrets Management](#secrets-management)
- [Webhook Security](#webhook-security)
- [Authentication Security](#authentication-security)
- [Network Security](#network-security)
- [Data Protection](#data-protection)
- [Logging and Auditing](#logging-and-auditing)
- [Dependency Security](#dependency-security)
- [Security Checklist](#security-checklist)

## Overview

Security is critical when operating a bot that handles messages and potentially sensitive data. This guide covers best practices for securing your Feishu Webhook Bot deployment.

### Security Principles

1. **Defense in Depth** - Multiple layers of security
2. **Least Privilege** - Minimal permissions required
3. **Secure by Default** - Safe default configurations
4. **Fail Securely** - Handle errors without exposing information

## Secrets Management

### Never Hardcode Secrets

```yaml
# ❌ BAD - Secrets in config file
webhooks:
  - name: default
    url: "https://open.feishu.cn/..."
    secret: "my-secret-key"

ai:
  api_key: "sk-1234567890abcdef"
```

```yaml
# ✅ GOOD - Use environment variables
webhooks:
  - name: default
    url: "${FEISHU_WEBHOOK_URL}"
    secret: "${FEISHU_SECRET}"

ai:
  api_key: "${OPENAI_API_KEY}"
```

### Environment Variables

```bash
# .env file (never commit to git!)
FEISHU_WEBHOOK_URL=https://open.feishu.cn/...
FEISHU_SECRET=your-signing-secret
OPENAI_API_KEY=sk-...
JWT_SECRET=your-jwt-secret
```

```bash
# Add to .gitignore
echo ".env" >> .gitignore
echo "*.env" >> .gitignore
```

### Secret Rotation

```python
# Implement secret rotation
class SecretManager:
    def __init__(self):
        self.secrets = {}
        self.rotation_interval = 86400  # 24 hours

    async def get_secret(self, name: str) -> str:
        if self.should_rotate(name):
            await self.rotate_secret(name)
        return self.secrets[name]

    async def rotate_secret(self, name: str):
        # Implement rotation logic
        new_secret = await generate_new_secret()
        await update_external_systems(name, new_secret)
        self.secrets[name] = new_secret
```

### Using Secret Managers

```python
# AWS Secrets Manager
import boto3

def get_secret_from_aws(secret_name: str) -> str:
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']

# HashiCorp Vault
import hvac

def get_secret_from_vault(path: str) -> str:
    client = hvac.Client(url='https://vault.example.com')
    secret = client.secrets.kv.read_secret_version(path=path)
    return secret['data']['data']['value']
```

## Webhook Security

### Enable Signature Verification

```yaml
webhooks:
  - name: default
    url: "${FEISHU_WEBHOOK_URL}"
    secret: "${FEISHU_SECRET}"  # Required for signature verification
```

### Signature Verification Implementation

```python
import hmac
import hashlib
import time

def verify_signature(timestamp: str, nonce: str, body: str, signature: str, secret: str) -> bool:
    """Verify Feishu webhook signature."""
    # Check timestamp freshness (within 5 minutes)
    if abs(time.time() - int(timestamp)) > 300:
        return False

    # Calculate expected signature
    string_to_sign = f"{timestamp}\n{nonce}\n{body}"
    expected = hmac.new(
        secret.encode(),
        string_to_sign.encode(),
        hashlib.sha256
    ).hexdigest()

    # Constant-time comparison
    return hmac.compare_digest(expected, signature)
```

### Request Validation

```python
from fastapi import Request, HTTPException

async def validate_webhook_request(request: Request):
    # Check content type
    if request.headers.get("content-type") != "application/json":
        raise HTTPException(400, "Invalid content type")

    # Check required headers
    timestamp = request.headers.get("X-Lark-Request-Timestamp")
    nonce = request.headers.get("X-Lark-Request-Nonce")
    signature = request.headers.get("X-Lark-Signature")

    if not all([timestamp, nonce, signature]):
        raise HTTPException(400, "Missing required headers")

    # Verify signature
    body = await request.body()
    if not verify_signature(timestamp, nonce, body.decode(), signature, SECRET):
        raise HTTPException(401, "Invalid signature")
```

## Authentication Security

### Strong Password Policy

```yaml
auth:
  password:
    min_length: 12
    require_uppercase: true
    require_lowercase: true
    require_digit: true
    require_special: true
    max_age_days: 90
    history_count: 5  # Prevent reuse of last 5 passwords
```

### JWT Security

```yaml
auth:
  jwt_secret: "${JWT_SECRET}"  # Use strong random secret
  jwt_algorithm: "HS256"
  access_token_expire_minutes: 15  # Short-lived tokens
  refresh_token_expire_days: 7
```

```python
# Generate strong JWT secret
import secrets

jwt_secret = secrets.token_urlsafe(32)
print(f"JWT_SECRET={jwt_secret}")
```

### Rate Limiting

```yaml
auth:
  rate_limiting:
    enabled: true
    max_attempts: 5
    lockout_minutes: 15
    window_minutes: 5
```

```python
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_attempts: int = 5, window_minutes: int = 5):
        self.attempts = defaultdict(list)
        self.max_attempts = max_attempts
        self.window = timedelta(minutes=window_minutes)

    def is_allowed(self, identifier: str) -> bool:
        now = datetime.now()
        # Clean old attempts
        self.attempts[identifier] = [
            t for t in self.attempts[identifier]
            if now - t < self.window
        ]

        if len(self.attempts[identifier]) >= self.max_attempts:
            return False

        self.attempts[identifier].append(now)
        return True
```

### Session Security

```python
# Secure session configuration
session_config = {
    "secret_key": os.environ["SESSION_SECRET"],
    "cookie_name": "session",
    "cookie_secure": True,  # HTTPS only
    "cookie_httponly": True,  # No JavaScript access
    "cookie_samesite": "strict",  # CSRF protection
    "max_age": 3600,  # 1 hour
}
```

## Network Security

### HTTPS Only

```yaml
# Nginx configuration
server {
    listen 443 ssl http2;
    server_name bot.example.com;

    ssl_certificate /etc/letsencrypt/live/bot.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bot.example.com/privkey.pem;

    # Strong SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

### Firewall Rules

```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 443/tcp  # HTTPS
sudo ufw allow 22/tcp   # SSH (restrict to specific IPs)
sudo ufw enable
```

### IP Allowlisting

```python
from fastapi import Request, HTTPException

ALLOWED_IPS = [
    "1.2.3.4",  # Feishu servers
    "5.6.7.8",
]

async def check_ip_allowlist(request: Request):
    client_ip = request.client.host
    if client_ip not in ALLOWED_IPS:
        raise HTTPException(403, "IP not allowed")
```

### Security Headers

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

## Data Protection

### Sensitive Data Handling

```python
import re

def sanitize_log_message(message: str) -> str:
    """Remove sensitive data from log messages."""
    patterns = [
        (r'api_key["\']?\s*[:=]\s*["\']?[\w-]+', 'api_key=***'),
        (r'password["\']?\s*[:=]\s*["\']?[\w-]+', 'password=***'),
        (r'secret["\']?\s*[:=]\s*["\']?[\w-]+', 'secret=***'),
        (r'token["\']?\s*[:=]\s*["\']?[\w-]+', 'token=***'),
    ]

    for pattern, replacement in patterns:
        message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)

    return message
```

### Data Encryption

```python
from cryptography.fernet import Fernet

class DataEncryptor:
    def __init__(self, key: bytes):
        self.fernet = Fernet(key)

    def encrypt(self, data: str) -> str:
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        return self.fernet.decrypt(encrypted.encode()).decode()

# Generate encryption key
key = Fernet.generate_key()
```

### Database Security

```yaml
# Use encrypted connection
auth:
  database:
    url: "postgresql://user:pass@localhost/db?sslmode=require"
```

```python
# Parameterized queries (prevent SQL injection)
async def get_user(user_id: str):
    query = "SELECT * FROM users WHERE id = $1"
    return await db.fetchrow(query, user_id)  # Safe

# ❌ Never do this
# query = f"SELECT * FROM users WHERE id = '{user_id}'"  # SQL injection!
```

### Data Retention

```yaml
# Configure data retention
message_tracking:
  retention_days: 30  # Delete old data

logging:
  retention_days: 90
```

```python
# Implement data cleanup
async def cleanup_old_data():
    cutoff = datetime.now() - timedelta(days=30)
    await db.execute("DELETE FROM messages WHERE created_at < $1", cutoff)
```

## Logging and Auditing

### Security Event Logging

```python
import logging
from datetime import datetime

security_logger = logging.getLogger("security")

def log_security_event(event_type: str, details: dict):
    security_logger.info({
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "details": details,
    })

# Log authentication events
log_security_event("login_success", {"user_id": user_id, "ip": client_ip})
log_security_event("login_failure", {"username": username, "ip": client_ip})
log_security_event("permission_denied", {"user_id": user_id, "resource": resource})
```

### Audit Trail

```python
from sqlalchemy import Column, String, DateTime, JSON

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    user_id = Column(String)
    action = Column(String, nullable=False)
    resource = Column(String)
    details = Column(JSON)
    ip_address = Column(String)

async def audit_action(user_id: str, action: str, resource: str, details: dict):
    log = AuditLog(
        id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        user_id=user_id,
        action=action,
        resource=resource,
        details=details,
    )
    await db.add(log)
```

### Log Protection

```yaml
logging:
  # Secure log storage
  log_file: "/var/log/feishu-bot/bot.log"
  file_permissions: "0640"

  # Log rotation
  max_bytes: 10485760
  backup_count: 10
```

## Dependency Security

### Keep Dependencies Updated

```bash
# Check for vulnerabilities
pip install safety
safety check

# Update dependencies
uv sync --upgrade
```

### Dependency Pinning

```toml
# pyproject.toml - Pin exact versions
[project]
dependencies = [
    "httpx==0.27.0",
    "pydantic==2.5.0",
    "cryptography==41.0.0",
]
```

### Security Scanning

```yaml
# GitHub Actions workflow
name: Security Scan

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Bandit
        run: |
          pip install bandit
          bandit -r src/

      - name: Run Safety
        run: |
          pip install safety
          safety check
```

## Security Checklist

### Pre-Deployment

- [ ] All secrets stored in environment variables
- [ ] Strong passwords configured
- [ ] JWT secret is random and secure
- [ ] HTTPS enabled
- [ ] Firewall configured
- [ ] Dependencies updated and scanned

### Configuration

- [ ] Webhook signature verification enabled
- [ ] Rate limiting configured
- [ ] Session security configured
- [ ] Logging configured (without sensitive data)
- [ ] Data retention policies set

### Monitoring

- [ ] Security event logging enabled
- [ ] Audit trail configured
- [ ] Alerting for security events
- [ ] Regular security reviews scheduled

### Ongoing

- [ ] Regular dependency updates
- [ ] Security patch monitoring
- [ ] Access review (quarterly)
- [ ] Secret rotation (as needed)
- [ ] Penetration testing (annually)

## See Also

- [Authentication](authentication.md) - Authentication system details
- [Deployment Guide](../deployment/deployment.md) - Secure deployment
- [Configuration Reference](../guides/configuration-reference.md) - Security settings
