
# 🐳 Environment & Docker Guide

Configuration guide for development and production environments.

## 📋 Table of Contents

- [Overview](#overview)
- [Environment Files](#environment-files)
- [Docker Configuration](#docker-configuration)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

### File Structure

```
1min-gateway/
├── .env.example          # Production template
├── .env.local            # Development template
├── .env                  # Your actual config (gitignored)
├── .dockerignore         # Docker build optimization
├── docker-compose.yml    # Container orchestration
└── Dockerfile            # Image build instructions
```

---

## 📁 Environment Files

### Production Template (`.env.example`)

```bash
# === REQUIRED ===
ONE_MIN_AI_API_KEY=sk-your-api-key-here

# === APPLICATION ===
APP_ENV=production
DEBUG=False
LOG_LEVEL=INFO
SECRET_KEY=generate-a-secure-key

# === RATE LIMITING ===
RATELIMIT_ENABLED=True
MEMCACHED_HOST=memcached
MEMCACHED_PORT=11211

# === DOCKER (for Watchtower) ===
DOCKER_USER=your-dockerhub-username
DOCKER_TOKEN=dckr_pat_your-access-token
```

### Development Template (`.env.local`)

```bash
# === REQUIRED ===
ONE_MIN_AI_API_KEY=sk-your-api-key-here

# === DEVELOPMENT SETTINGS ===
APP_ENV=development
DEBUG=True
LOG_LEVEL=DEBUG
RATELIMIT_ENABLED=False
```

### Setup

```bash
# Production
cp .env.example .env
nano .env  # Fill in your credentials

# Development
cp .env.local .env
nano .env  # Add your API key
```

### Security

```bash
# Restrict permissions
chmod 600 .env

# Verify gitignored
grep "^\.env$" .gitignore
```

---

## 🐳 Docker Configuration

### Docker Compose Features

| Feature | Description |
|---------|-------------|
| Healthchecks | Ensures app is ready before traffic |
| Resource Limits | Prevents memory/CPU exhaustion |
| Log Rotation | Max 10MB × 3 files per container |
| Auto-updates | Watchtower pulls new images |
| Network Isolation | Dedicated bridge network |

### Healthcheck Configuration

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Resource Limits

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 1G
    reservations:
      cpus: '0.5'
      memory: 256M
```

### Log Rotation

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
    compress: "true"
```

### Commands

```bash
# Start all services
make up
# or: docker compose up -d

# View logs
make logs
# or: docker compose logs -f

# Restart
make restart
# or: docker compose restart

# Stop
make down
# or: docker compose down

# Check health
docker ps  # Shows (healthy) or (unhealthy)

# Force Watchtower update
docker exec watchtower /watchtower --run-once
```

---

## 🔐 Security Best Practices

### ❌ Never Do

```bash
# Commit .env file
git add .env  # DANGER: Secrets exposed!

# Use password instead of token
DOCKER_TOKEN=my_password  # Use access token!

# Hardcode secrets in code
api_key = "sk-real-key"  # Use environment variables!
```

### ✅ Always Do

```bash
# Use access tokens
DOCKER_TOKEN=dckr_pat_AbCdEfGhIjKlMnOpQrStUvWxYz

# Generate secure keys
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Rotate secrets every 90 days
```

### Secret Scanning

```bash
# Pre-commit hook detects secrets automatically
# For manual scan:
detect-secrets scan > .secrets.baseline
detect-secrets audit .secrets.baseline
```

---

## 🔧 .dockerignore Optimization

### Impact

```bash
# Before optimization
Sending build context to Docker daemon  52.3MB

# After optimization
Sending build context to Docker daemon  21.1MB
```

### Key Exclusions

```
# Git
.git/
.gitignore

# Python
__pycache__/
*.pyc
.venv/
venv/

# IDE
.vscode/
.idea/

# Logs & temp
logs/
*.log

# Secrets (critical!)
.env
.secrets.baseline
```

---

## 🐛 Troubleshooting

### Container Shows "unhealthy"

```bash
# Check health logs
docker inspect 1min-gateway --format='{{json .State.Health}}' | jq

# Check app logs
docker logs 1min-gateway

# Test endpoint manually
curl http://localhost:5001/health

# Increase start_period if app is slow
start_period: 60s  # Instead of 40s
```

### Memcached Connection Error

```bash
# Check if memcached is running
docker ps | grep memcached

# Test connection
docker exec 1min-gateway sh -c "nc -zv memcached 11211"

# Check network
docker network inspect 1min-gateway-network
```

### Watchtower Not Updating

```bash
# Check logs
docker logs watchtower

# Verify Docker credentials
echo $DOCKER_TOKEN | docker login -u $DOCKER_USER --password-stdin

# Check label on container
docker inspect 1min-gateway | grep watchtower
# Should show: "com.centurylinklabs.watchtower.enable=true"
```

### "version is obsolete" Warning

```yaml
# Remove this line from docker-compose.yml
version: '3.8'  # ← Delete this line
```

---

## 📊 Maintenance Commands

```bash
# Update all services
docker compose pull
docker compose up -d

# Clean old images
docker image prune -a

# Check disk usage
docker system df

# Backup logs
tar -czf logs-backup-$(date +%Y%m%d).tar.gz logs/

# Full cleanup (caution!)
docker system prune -af --volumes
```

---

## ✅ Pre-launch Checklist

- [ ] `.env` created with real credentials
- [ ] `ONE_MIN_AI_API_KEY` tested
- [ ] `DOCKER_TOKEN` is an access token (not password)
- [ ] `chmod 600 .env` executed
- [ ] `.env` in `.gitignore`
- [ ] `docker compose up -d` works
- [ ] All containers show `(healthy)`
- [ ] `curl http://localhost:5001/health` returns 200
