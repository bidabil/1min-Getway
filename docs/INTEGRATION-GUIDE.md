
# 🚀 Integration Guide - 1min-Gateway

Complete guide to set up and use the 1min-Gateway DevOps ecosystem.

## 📋 Table of Contents

- [Overview](#overview)
- [Step-by-Step Installation](#step-by-step-installation)
- [GitHub Configuration](#github-configuration)
- [First Release](#first-release)
- [Daily Workflow](#daily-workflow)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

The 1min-Gateway DevOps ecosystem provides:

```
Local Development          GitHub Actions              Production
─────────────────         ────────────────            ──────────────
Pre-commit hooks    →     CI/CD Pipeline       →      Docker Registry
  │                         │                            │
  ├─ Commitlint             ├─ Tests                     ├─ Docker Hub
  ├─ Ruff (lint+format)     ├─ Security Scan             └─ GHCR
  ├─ detect-secrets         ├─ Semantic Release
  └─ hadolint               └─ Multi-arch Build    →    Watchtower
                                                          Auto-deploy
```

---

## 📦 Step-by-Step Installation

### Step 1: Clone and Setup

```bash
# Clone repository
git clone https://github.com/BillelAttafi/1min-gateway.git
cd 1min-gateway

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install everything
make install
```

### Step 2: Verify Installation

```bash
# Check pre-commit hooks
pre-commit run --all-files

# Run tests
make test

# Verify Docker build
make docker-build
```

### Step 3: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env
```

**Required variables:**

```bash
ONE_MIN_AI_API_KEY=sk-your-1min-ai-key
```

---

## ⚙️ GitHub Configuration

### 1. Repository Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Description | Where to get it |
|--------|-------------|-----------------|
| `DOCKER_USERNAME` | Docker Hub username | Your Docker Hub account |
| `DOCKER_PASSWORD` | Docker Hub access token | [Create token](https://hub.docker.com/settings/security) |

> ⚠️ Use an **Access Token**, not your password!

### 2. Branch Protection

Go to **Settings → Branches → Add rule**:

```
Branch name pattern: main

☑️ Require a pull request before merging
   ☑️ Require approvals: 1

☑️ Require status checks to pass before merging
   ☑️ Require branches to be up to date
   Select: "test"

☑️ Allow auto-merge
```

### 3. Enable Dependabot

Go to **Settings → Code security → Dependabot**:

```
☑️ Dependabot alerts: Enabled
☑️ Dependabot security updates: Enabled
☑️ Dependabot version updates: Enabled
```

---

## 🎯 First Release

### Test 1: Verify Local Hooks

```bash
# Create a test file
echo "print('test')" > test_commit.py

# Commit (hooks will run automatically)
git add test_commit.py
git commit -m ":sparkles: feat(Core): add test file"

# Clean up
rm test_commit.py
git reset --hard HEAD~1
```

### Test 2: Documentation Commit (No Release)

```bash
git commit -m ":memo: docs(Config): update README"
git push origin main

# Expected result:
# ✅ Tests pass
# ⏭️ No version created (docs type)
# ⏭️ No Docker build
```

### Test 3: Feature Commit (Creates Release)

```bash
git commit -m ":sparkles: feat(Gateway): add health endpoint"
git push origin main

# Expected result:
# ✅ Tests pass
# 🎉 Version v1.0.0 created
# 🐳 Docker image built and pushed
# 🔒 Image signed with Cosign
# 📦 CHANGELOG.md updated
```

### Verify Release

1. **GitHub Actions** → Check workflow status
2. **GitHub Releases** → v1.0.0 should appear
3. **Docker Hub** → Tags `1.0.0` and `latest`
4. **Security tab** → Trivy scan results

---

## 🔄 Daily Workflow

### Feature Development

```bash
# 1. Create feature branch
git checkout -b feat/new-feature

# 2. Code your changes
# ...

# 3. Test locally
make test
make lint

# 4. Commit
git add .
git commit -m ":sparkles: feat(Core): add new feature"

# 5. Push and create PR
git push origin feat/new-feature
# Create PR on GitHub

# 6. After merge, release is automatic
```

### Handling Dependabot PRs

**Patch updates** (auto-merged):
```
PR: "⬆️ chore(deps): Bump fastapi 0.109.0 → 0.109.1"
→ Tests pass → Auto-merged ✅
```

**Minor updates** (manual review):
```
PR: "⬆️ chore(deps): Bump pydantic 2.5.0 → 2.6.0"
→ Tests pass → Approved, needs manual merge ⏸️
```

**Major updates** (requires attention):
```
PR: "⬆️ chore(deps): Bump fastapi 0.x → 1.0.0"
→ Comment: "⚠️ MAJOR UPDATE"
→ Review changelog, test locally, then merge
```

### Force a Release

```bash
git commit --allow-empty -m ":rocket: chore(release): trigger new version"
git push origin main
```

---

## 🐛 Troubleshooting

### Pre-commit Hooks Fail

```bash
# Reinstall hooks
pre-commit clean
pre-commit install --install-hooks

# Run manually
pre-commit run --all-files
```

### Commitlint Rejects Commit

```bash
# ❌ Wrong
git commit -m "fix bug"

# ✅ Correct format
git commit -m ":bug: fix(Core): resolve authentication issue"
```

### No Release Created

**Check commit type:**
- `docs`, `style`, `chore`, `refactor` → No release
- `feat` → Minor release
- `fix` → Patch release

**Check `.releaserc.json`** is properly configured.

### Docker Build Fails

```bash
# Test locally
make docker-build

# Check secrets are configured
# Settings → Secrets → DOCKER_USERNAME, DOCKER_PASSWORD
```

### Watchtower Not Updating

```bash
# Check Watchtower logs
docker logs watchtower

# Verify label on container
docker inspect 1min-gateway | grep watchtower

# Label should be:
# "com.centurylinklabs.watchtower.enable=true"
```

---

## 📊 Useful Commands

```bash
# Development
make dev              # Start development server
make test             # Run tests
make lint             # Check code quality
make format           # Format code

# Docker
make up               # Docker Compose up
make down             # Docker Compose down
make logs             # View logs
make restart          # Restart services

# Maintenance
make clean            # Clean artifacts
make update           # Update dependencies
```

---

## 📚 Related Documentation

- [CI/CD Documentation](CI-CD-DOCUMENTATION.md) - Pipeline details
- [CI/CD Cheatsheet](CI-CD-CHEATSHEET.md) - Quick reference
- [Dependabot Guide](DEPENDABOT-DOCUMENTATION.md) - Dependency management
- [Docker Guide](ENV-DOCKER-GUIDE.md) - Container configuration

---

**Setup complete! Your project is production-ready.** 🎉
