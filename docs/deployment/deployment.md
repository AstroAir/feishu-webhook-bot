# Deployment Guide

This guide covers deploying the Feishu Webhook Bot to production environments.

## Table of Contents

- [Deployment Options](#deployment-options)
- [Docker Deployment](#docker-deployment)
- [Systemd Service](#systemd-service)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Cloud Platforms](#cloud-platforms)
- [Reverse Proxy](#reverse-proxy)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Monitoring](#monitoring)
- [Scaling](#scaling)
- [Security Hardening](#security-hardening)
- [Backup and Recovery](#backup-and-recovery)

## Deployment Options

| Method | Best For | Complexity |
|--------|----------|------------|
| Docker | Most deployments | Low |
| Systemd | Linux servers | Low |
| Kubernetes | Large scale | High |
| Cloud Functions | Serverless | Medium |

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy configuration and plugins
COPY config.yaml ./
COPY plugins/ ./plugins/

# Create data directory
RUN mkdir -p data logs

# Set environment
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["uv", "run", "feishu-webhook-bot", "start", "-c", "config.yaml"]
```

### Docker Compose

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
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - FEISHU_WEBHOOK_URL=${FEISHU_WEBHOOK_URL}
      - FEISHU_SECRET=${FEISHU_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    ports:
      - "8080:8080"  # Event server
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Optional: Web UI
  feishu-bot-ui:
    build: .
    container_name: feishu-bot-ui
    restart: unless-stopped
    command: ["uv", "run", "feishu-webhook-bot", "webui", "--host", "0.0.0.0"]
    volumes:
      - ./config.yaml:/app/config.yaml
    ports:
      - "8081:8080"
    depends_on:
      - feishu-bot
```

### Running with Docker

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f feishu-bot

# Stop
docker-compose down

# Rebuild after changes
docker-compose up -d --build
```

## Systemd Service

### Service File

Create `/etc/systemd/system/feishu-bot.service`:

```ini
[Unit]
Description=Feishu Webhook Bot
After=network.target

[Service]
Type=simple
User=feishu-bot
Group=feishu-bot
WorkingDirectory=/opt/feishu-bot
ExecStart=/opt/feishu-bot/.venv/bin/feishu-webhook-bot start -c config.yaml
Restart=always
RestartSec=10

# Environment
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=/opt/feishu-bot/.env

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/feishu-bot/data /opt/feishu-bot/logs

# Resource limits
MemoryMax=512M
CPUQuota=100%

[Install]
WantedBy=multi-user.target
```

### Installation Steps

```bash
# Create user
sudo useradd -r -s /bin/false feishu-bot

# Create directory
sudo mkdir -p /opt/feishu-bot
sudo chown feishu-bot:feishu-bot /opt/feishu-bot

# Install bot
cd /opt/feishu-bot
sudo -u feishu-bot python -m venv .venv
sudo -u feishu-bot .venv/bin/pip install feishu-webhook-bot

# Copy configuration
sudo cp config.yaml /opt/feishu-bot/
sudo cp -r plugins /opt/feishu-bot/

# Create environment file
sudo tee /opt/feishu-bot/.env << EOF
FEISHU_WEBHOOK_URL=https://...
FEISHU_SECRET=your-secret
EOF
sudo chmod 600 /opt/feishu-bot/.env

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable feishu-bot
sudo systemctl start feishu-bot
```

### Service Management

```bash
# Check status
sudo systemctl status feishu-bot

# View logs
sudo journalctl -u feishu-bot -f

# Restart
sudo systemctl restart feishu-bot

# Stop
sudo systemctl stop feishu-bot
```

## Kubernetes Deployment

### ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: feishu-bot-config
data:
  config.yaml: |
    webhooks:
      - name: default
        url: "${FEISHU_WEBHOOK_URL}"
        secret: "${FEISHU_SECRET}"
    scheduler:
      enabled: true
    plugins:
      enabled: true
      plugin_dir: /app/plugins
```

### Secret

```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: feishu-bot-secrets
type: Opaque
stringData:
  FEISHU_WEBHOOK_URL: "https://open.feishu.cn/..."
  FEISHU_SECRET: "your-secret"
  OPENAI_API_KEY: "sk-..."
```

### Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: feishu-bot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: feishu-bot
  template:
    metadata:
      labels:
        app: feishu-bot
    spec:
      containers:
        - name: feishu-bot
          image: ghcr.io/astroair/feishu-webhook-bot:latest
          ports:
            - containerPort: 8080
          envFrom:
            - secretRef:
                name: feishu-bot-secrets
          volumeMounts:
            - name: config
              mountPath: /app/config.yaml
              subPath: config.yaml
            - name: data
              mountPath: /app/data
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
      volumes:
        - name: config
          configMap:
            name: feishu-bot-config
        - name: data
          persistentVolumeClaim:
            claimName: feishu-bot-data
```

### Service

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: feishu-bot
spec:
  selector:
    app: feishu-bot
  ports:
    - port: 80
      targetPort: 8080
  type: ClusterIP
```

### Deploy to Kubernetes

```bash
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

## Cloud Platforms

### AWS ECS

```json
{
  "family": "feishu-bot",
  "containerDefinitions": [
    {
      "name": "feishu-bot",
      "image": "ghcr.io/astroair/feishu-webhook-bot:latest",
      "memory": 512,
      "cpu": 256,
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8080,
          "hostPort": 8080
        }
      ],
      "environment": [
        {
          "name": "FEISHU_WEBHOOK_URL",
          "value": "https://..."
        }
      ],
      "secrets": [
        {
          "name": "FEISHU_SECRET",
          "valueFrom": "arn:aws:secretsmanager:..."
        }
      ]
    }
  ]
}
```

### Google Cloud Run

```bash
gcloud run deploy feishu-bot \
  --image ghcr.io/astroair/feishu-webhook-bot:latest \
  --platform managed \
  --region asia-east1 \
  --set-env-vars FEISHU_WEBHOOK_URL=https://... \
  --set-secrets FEISHU_SECRET=feishu-secret:latest
```

### Azure Container Instances

```bash
az container create \
  --resource-group myResourceGroup \
  --name feishu-bot \
  --image ghcr.io/astroair/feishu-webhook-bot:latest \
  --cpu 1 \
  --memory 1 \
  --ports 8080 \
  --environment-variables FEISHU_WEBHOOK_URL=https://...
```

## Reverse Proxy

### Nginx

```nginx
# /etc/nginx/sites-available/feishu-bot
upstream feishu_bot {
    server 127.0.0.1:8080;
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name bot.example.com;

    ssl_certificate /etc/letsencrypt/live/bot.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bot.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    location / {
        proxy_pass http://feishu_bot;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    location /health {
        proxy_pass http://feishu_bot/health;
        access_log off;
    }
}

server {
    listen 80;
    server_name bot.example.com;
    return 301 https://$server_name$request_uri;
}
```

### Caddy

```caddyfile
# Caddyfile
bot.example.com {
    reverse_proxy localhost:8080

    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
    }

    log {
        output file /var/log/caddy/feishu-bot.log
    }
}
```

## SSL/TLS Configuration

### Let's Encrypt with Certbot

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d bot.example.com

# Auto-renewal
sudo certbot renew --dry-run
```

### Self-Signed Certificate (Development)

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/feishu-bot.key \
  -out /etc/ssl/certs/feishu-bot.crt \
  -subj "/CN=localhost"
```

## Monitoring

### Health Endpoints

The bot exposes health endpoints:

- `GET /health` - Basic health check
- `GET /ready` - Readiness check
- `GET /metrics` - Prometheus metrics (if enabled)

### Prometheus Metrics

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'feishu-bot'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: /metrics
```

### Grafana Dashboard

Import the provided Grafana dashboard for monitoring:

- Message send rate
- Error rate
- Response times
- Queue depth
- Circuit breaker status

### Alerting

```yaml
# alertmanager rules
groups:
  - name: feishu-bot
    rules:
      - alert: FeishuBotDown
        expr: up{job="feishu-bot"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Feishu bot is down"

      - alert: HighErrorRate
        expr: rate(feishu_bot_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
```

## Scaling

### Horizontal Scaling

For high-traffic scenarios:

```yaml
# kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: feishu-bot-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: feishu-bot
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

### Considerations

- Use external job store (Redis/PostgreSQL) for scheduler
- Use external message queue for high throughput
- Implement leader election for singleton tasks

## Security Hardening

### Checklist

- [ ] Use environment variables for secrets
- [ ] Enable HTTPS/TLS
- [ ] Set up firewall rules
- [ ] Use non-root user
- [ ] Enable authentication
- [ ] Rotate secrets regularly
- [ ] Keep dependencies updated
- [ ] Enable audit logging

### Firewall Rules

```bash
# Allow only necessary ports
sudo ufw allow 443/tcp
sudo ufw allow 80/tcp
sudo ufw deny 8080/tcp  # Block direct access
```

## Backup and Recovery

### Data to Backup

- Configuration files
- Plugin files
- Database files (auth, messages, jobs)
- Logs (optional)

### Backup Script

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/backup/feishu-bot/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup config
cp /opt/feishu-bot/config.yaml "$BACKUP_DIR/"

# Backup plugins
tar -czf "$BACKUP_DIR/plugins.tar.gz" /opt/feishu-bot/plugins/

# Backup data
tar -czf "$BACKUP_DIR/data.tar.gz" /opt/feishu-bot/data/

# Cleanup old backups (keep 30 days)
find /backup/feishu-bot -type d -mtime +30 -exec rm -rf {} +
```

### Recovery

```bash
# Stop service
sudo systemctl stop feishu-bot

# Restore data
tar -xzf /backup/feishu-bot/20250101/data.tar.gz -C /

# Start service
sudo systemctl start feishu-bot
```

## See Also

- [Installation Guide](../getting-started/installation.md) - Installation options
- [Configuration Reference](../guides/configuration-reference.md) - All configuration options
- [Troubleshooting](../resources/troubleshooting.md) - Common issues
- [Security](../security/authentication.md) - Authentication setup
