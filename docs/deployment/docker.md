# Docker Deployment Guide

Complete guide for deploying Feishu Webhook Bot using Docker and Docker Compose.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Dockerfile](#dockerfile)
- [Docker Compose](#docker-compose)
- [Configuration](#configuration)
- [Volumes and Persistence](#volumes-and-persistence)
- [Networking](#networking)
- [Health Checks](#health-checks)
- [Logging](#logging)
- [Scaling](#scaling)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+ (optional)
- 256MB+ RAM
- Network access to Feishu API

## Quick Start

```bash
# Pull and run
docker run -d \
  --name feishu-bot \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -e FEISHU_WEBHOOK_URL=https://... \
  -p 8080:8080 \
  ghcr.io/astroair/feishu-webhook-bot:latest
```

## Dockerfile

### Production Dockerfile

```dockerfile
# Dockerfile
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-editable

# Production image
FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN useradd -r -s /bin/false botuser

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/ ./src/
COPY config.example.yaml ./

# Create directories
RUN mkdir -p data logs plugins && \
    chown -R botuser:botuser /app

# Switch to non-root user
USER botuser

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port for event server
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8080/health')" || exit 1

# Default command
CMD ["python", "-m", "feishu_webhook_bot", "start", "-c", "config.yaml"]
```

### Development Dockerfile

```dockerfile
# Dockerfile.dev
FROM python:3.12-slim

WORKDIR /app

# Install uv and dev tools
RUN pip install uv

# Copy all files
COPY . .

# Install all dependencies including dev
RUN uv sync --all-groups

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Expose ports
EXPOSE 8080 8081

# Development command with auto-reload
CMD ["uv", "run", "python", "-m", "feishu_webhook_bot", "start", "--debug"]
```

### Multi-Architecture Build

```bash
# Build for multiple architectures
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/astroair/feishu-webhook-bot:latest \
  --push .
```

## Docker Compose

### Basic Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  feishu-bot:
    build: .
    container_name: feishu-bot
    restart: unless-stopped
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ./plugins:/app/plugins:ro
      - bot-data:/app/data
      - bot-logs:/app/logs
    environment:
      - FEISHU_WEBHOOK_URL=${FEISHU_WEBHOOK_URL}
      - FEISHU_SECRET=${FEISHU_SECRET}
      - TZ=Asia/Shanghai
    ports:
      - "8080:8080"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

volumes:
  bot-data:
  bot-logs:
```

### Full Stack with Web UI

```yaml
# docker-compose.full.yml
version: '3.8'

services:
  feishu-bot:
    build: .
    container_name: feishu-bot
    restart: unless-stopped
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ./plugins:/app/plugins:ro
      - bot-data:/app/data
      - bot-logs:/app/logs
    environment:
      - FEISHU_WEBHOOK_URL=${FEISHU_WEBHOOK_URL}
      - FEISHU_SECRET=${FEISHU_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - JWT_SECRET=${JWT_SECRET}
      - TZ=Asia/Shanghai
    ports:
      - "8080:8080"
    networks:
      - bot-network
    depends_on:
      - redis

  webui:
    build: .
    container_name: feishu-bot-ui
    restart: unless-stopped
    command: ["python", "-m", "feishu_webhook_bot", "webui", "--host", "0.0.0.0"]
    volumes:
      - ./config.yaml:/app/config.yaml
      - bot-data:/app/data
    environment:
      - JWT_SECRET=${JWT_SECRET}
      - TZ=Asia/Shanghai
    ports:
      - "8081:8080"
    networks:
      - bot-network
    depends_on:
      - feishu-bot

  redis:
    image: redis:7-alpine
    container_name: feishu-bot-redis
    restart: unless-stopped
    volumes:
      - redis-data:/data
    networks:
      - bot-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  nginx:
    image: nginx:alpine
    container_name: feishu-bot-nginx
    restart: unless-stopped
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    ports:
      - "80:80"
      - "443:443"
    networks:
      - bot-network
    depends_on:
      - feishu-bot
      - webui

volumes:
  bot-data:
  bot-logs:
  redis-data:

networks:
  bot-network:
    driver: bridge
```

### Development Setup

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  feishu-bot:
    build:
      context: .
      dockerfile: Dockerfile.dev
    container_name: feishu-bot-dev
    volumes:
      - .:/app
      - /app/.venv  # Exclude venv from mount
    environment:
      - FEISHU_WEBHOOK_URL=${FEISHU_WEBHOOK_URL}
      - FEISHU_SECRET=${FEISHU_SECRET}
      - DEBUG=1
    ports:
      - "8080:8080"
      - "8081:8081"
    command: ["uv", "run", "python", "-m", "feishu_webhook_bot", "start", "--debug"]
```

## Configuration

### Environment Variables

```bash
# .env file
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
FEISHU_SECRET=your-signing-secret
OPENAI_API_KEY=sk-xxx
JWT_SECRET=your-jwt-secret
TZ=Asia/Shanghai
```

### Config File Mounting

```yaml
services:
  feishu-bot:
    volumes:
      # Read-only config
      - ./config.yaml:/app/config.yaml:ro

      # Or use config directory
      - ./config:/app/config:ro
```

### Secrets Management

```yaml
# Using Docker secrets
services:
  feishu-bot:
    secrets:
      - feishu_secret
      - openai_key
    environment:
      - FEISHU_SECRET_FILE=/run/secrets/feishu_secret
      - OPENAI_API_KEY_FILE=/run/secrets/openai_key

secrets:
  feishu_secret:
    file: ./secrets/feishu_secret.txt
  openai_key:
    file: ./secrets/openai_key.txt
```

## Volumes and Persistence

### Data Volumes

```yaml
services:
  feishu-bot:
    volumes:
      # Named volumes (recommended for production)
      - bot-data:/app/data
      - bot-logs:/app/logs

      # Or bind mounts (for development)
      - ./data:/app/data
      - ./logs:/app/logs

volumes:
  bot-data:
    driver: local
  bot-logs:
    driver: local
```

### Backup Volumes

```bash
# Backup data volume
docker run --rm \
  -v feishu-bot_bot-data:/data:ro \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/data-$(date +%Y%m%d).tar.gz -C /data .

# Restore data volume
docker run --rm \
  -v feishu-bot_bot-data:/data \
  -v $(pwd)/backup:/backup:ro \
  alpine tar xzf /backup/data-20250115.tar.gz -C /data
```

## Networking

### Internal Network

```yaml
services:
  feishu-bot:
    networks:
      - internal
      - external

  redis:
    networks:
      - internal  # Only internal access

networks:
  internal:
    internal: true
  external:
```

### Custom DNS

```yaml
services:
  feishu-bot:
    dns:
      - 8.8.8.8
      - 8.8.4.4
    dns_search:
      - example.com
```

### Host Network Mode

```yaml
services:
  feishu-bot:
    network_mode: host
```

## Health Checks

### HTTP Health Check

```yaml
services:
  feishu-bot:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

### Python Health Check

```yaml
services:
  feishu-bot:
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8080/health').raise_for_status()"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Custom Health Script

```bash
#!/bin/bash
# healthcheck.sh
curl -sf http://localhost:8080/health || exit 1
python -c "from feishu_webhook_bot import FeishuBot; print('OK')" || exit 1
```

## Logging

### Docker Logging

```yaml
services:
  feishu-bot:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
```

### Centralized Logging

```yaml
services:
  feishu-bot:
    logging:
      driver: "fluentd"
      options:
        fluentd-address: "localhost:24224"
        tag: "feishu-bot"

  fluentd:
    image: fluent/fluentd:v1.16
    volumes:
      - ./fluent.conf:/fluentd/etc/fluent.conf
    ports:
      - "24224:24224"
```

### View Logs

```bash
# View logs
docker logs feishu-bot

# Follow logs
docker logs -f feishu-bot

# Last 100 lines
docker logs --tail 100 feishu-bot

# With timestamps
docker logs -t feishu-bot
```

## Scaling

### Docker Compose Scaling

```bash
# Scale to 3 instances
docker-compose up -d --scale feishu-bot=3
```

### Load Balancing

```yaml
services:
  feishu-bot:
    deploy:
      replicas: 3
    # Remove port mapping, use nginx

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx-lb.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "8080:80"
    depends_on:
      - feishu-bot
```

```nginx
# nginx-lb.conf
upstream feishu_bot {
    least_conn;
    server feishu-bot:8080;
}

server {
    listen 80;
    location / {
        proxy_pass http://feishu_bot;
    }
}
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs feishu-bot

# Check container status
docker inspect feishu-bot

# Run interactively
docker run -it --rm \
  -v $(pwd)/config.yaml:/app/config.yaml \
  ghcr.io/astroair/feishu-webhook-bot:latest \
  /bin/bash
```

### Permission Issues

```bash
# Fix volume permissions
docker run --rm \
  -v feishu-bot_bot-data:/data \
  alpine chown -R 1000:1000 /data
```

### Network Issues

```bash
# Test network connectivity
docker exec feishu-bot curl -v https://open.feishu.cn

# Check DNS
docker exec feishu-bot nslookup open.feishu.cn
```

### Memory Issues

```yaml
services:
  feishu-bot:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

### Debug Mode

```bash
# Run with debug
docker run -it --rm \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -e DEBUG=1 \
  ghcr.io/astroair/feishu-webhook-bot:latest \
  python -m feishu_webhook_bot start --debug
```

## See Also

- [Deployment Guide](deployment.md) - General deployment
- [Configuration Reference](../guides/configuration-reference.md) - Configuration options
- [Troubleshooting](../resources/troubleshooting.md) - Common issues
