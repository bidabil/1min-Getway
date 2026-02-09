
# 🚀 CI/CD Cheatsheet - 1min-Gateway

Quick reference for releases, Docker commands, and debugging.

---

## 📦 Triggering Releases

### Patch Release (1.2.3 → 1.2.4)

```bash
git commit -m ":bug: fix(Core): resolve authentication bug"
git push origin main
```

### Minor Release (1.2.3 → 1.3.0)

```bash
git commit -m ":sparkles: feat(Gateway): add CSV export"
git push origin main
```

### Major Release (1.2.3 → 2.0.0)

```bash
git commit -m ":boom: feat(API): incompatible API changes

BREAKING CHANGE: API v2 is incompatible with v1"
git push origin main
```

### No Release

```bash
git commit -m ":memo: docs(Config): update README"
git commit -m ":recycle: refactor(Core): simplify function"
git commit -m ":wrench: chore(deps): update dev tools"
```

---

## 🏷️ Gitmoji Reference

| Gitmoji | Code | Type | Impact |
|---------|------|------|--------|
| ✨ | `:sparkles:` | feat | Minor |
| 🐛 | `:bug:` | fix | Patch |
| ⚡ | `:zap:` | perf | Patch |
| 🔒 | `:lock:` | security | Patch |
| 💥 | `:boom:` | breaking | Major |
| 📝 | `:memo:` | docs | None |
| ♻️ | `:recycle:` | refactor | None |
| ✅ | `:white_check_mark:` | test | None |
| 🔧 | `:wrench:` | chore | None |

---

## 🐳 Docker Commands

### Pull Images

```bash
# Latest
docker pull billelattafi/1min-gateway:latest

# Specific version
docker pull billelattafi/1min-gateway:1.2.3

# From GHCR
docker pull ghcr.io/billelattafi/1min-gateway:1.2.3
```

### List Available Tags

```bash
curl -s https://hub.docker.com/v2/repositories/billelattafi/1min-gateway/tags \
  | jq -r '.results[].name'
```

### Inspect Multi-arch

```bash
docker buildx imagetools inspect billelattafi/1min-gateway:latest
```

---

## 🔐 Verify Image Signature

```bash
# Install Cosign
brew install cosign  # macOS
# or download from GitHub releases

# Verify
cosign verify \
  --certificate-identity-regexp=".*" \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  billelattafi/1min-gateway:latest
```

---

## 🛡️ Security Scanning

### Local Scan with Trivy

```bash
# Install
brew install trivy  # macOS

# Scan image
trivy image billelattafi/1min-gateway:latest

# Critical/High only
trivy image --severity CRITICAL,HIGH billelattafi/1min-gateway:latest
```

### View in GitHub

**Repository → Security → Code scanning alerts → Filter: Trivy**

---

## 🔍 Debug Workflow

### View Logs

```bash
# GitHub UI
Actions → Failed workflow → Expand failed step
```

### Re-run Failed Jobs

```bash
# GitHub UI
Actions → Failed workflow → "Re-run failed jobs"
```

### Test Locally

```bash
# Build
docker build -t test:local .

# Run tests
pytest --cov=src

# Scan
trivy image test:local
```

---

## 🚨 Rollback

### Method 1: Pull Old Version

```bash
# Old version still available on Docker Hub
docker pull billelattafi/1min-gateway:1.2.3
```

### Method 2: Revert Commit

```bash
git revert HEAD
git push origin main
# Creates new patch release
```

### Method 3: Re-tag Latest

```bash
docker pull billelattafi/1min-gateway:1.2.3
docker tag billelattafi/1min-gateway:1.2.3 billelattafi/1min-gateway:latest
docker push billelattafi/1min-gateway:latest
```

---

## 💡 Tips

### Force Release Without Code Change

```bash
git commit --allow-empty -m ":rocket: chore(release): force rebuild"
git push origin main
```

### Test PR Before Merge

```bash
git checkout feat/my-feature
docker build -t test:pr .
docker run -p 5001:5001 test:pr
pytest
```

### Speed Up Local Tests

```bash
pytest --lf   # Last failed only
pytest --ff   # Failed first
pytest -x     # Stop on first failure
```

---

## 📞 Quick Links

- [Semantic Release Docs](https://semantic-release.gitbook.io/)
- [Gitmoji](https://gitmoji.dev/)
- [Trivy](https://aquasecurity.github.io/trivy/)
- [Cosign](https://docs.sigstore.dev/cosign/)
