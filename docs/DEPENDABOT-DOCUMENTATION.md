
# 🤖 Dependabot Configuration Guide

Automated dependency updates with intelligent grouping and auto-merge capabilities.

## 📋 Table of Contents

- [Overview](#overview)
- [Configuration](#configuration)
- [Grouping Strategy](#grouping-strategy)
- [Auto-merge](#auto-merge)
- [Managing PRs](#managing-prs)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

This Dependabot configuration automates dependency updates while maintaining stability:

| Feature | Description |
|---------|-------------|
| ✅ 3 Ecosystems | Python (pip) + GitHub Actions + Docker |
| ✅ Smart Grouping | 1 PR instead of 10+ |
| ✅ Auto Labels | Easy PR filtering |
| ✅ Breaking Change Protection | Major updates blocked by default |
| ✅ Semantic Release Compatible | Commits don't trigger releases |
| ✅ Auto Assignment | You never miss a PR |

### Update Schedule

| Ecosystem | Day | Time | Timezone |
|-----------|-----|------|----------|
| Python | Monday | 09:00 | Europe/Paris |
| GitHub Actions | Monday | 10:00 | Europe/Paris |
| Docker | Tuesday | 09:00 | Europe/Paris |

---

## ⚙️ Configuration

### File Location

```
.github/dependabot.yml
```

### Customize Reviewers

```yaml
reviewers:
  - "your-github-username"  # Change this
assignees:
  - "your-github-username"  # Change this
```

### Commit Message Format

```yaml
commit-message:
  prefix: "⬆️ chore(deps)"      # Production deps
  prefix-development: "⬆️ chore(deps-dev)"  # Dev deps
```

> The `chore` type ensures Dependabot PRs don't trigger releases.

---

## 🧩 Grouping Strategy

### Why Group?

**Without grouping:**
```
PR #1: Bump pytest 7.4.0 → 7.4.1
PR #2: Bump ruff 0.1.0 → 0.1.1
PR #3: Bump httpx 0.25.0 → 0.25.1
... 15 more PRs
```

**With grouping:**
```
PR #1: ⬆️ chore(deps): Bump production-dependencies group
PR #2: ⬆️ chore(deps-dev): Bump development-dependencies group
```

### Group Configuration

#### Production Dependencies (Critical)

```yaml
production-dependencies:
  patterns:
    - "fastapi*"
    - "uvicorn*"
    - "pydantic*"
  update-types:
    - "minor"   # 1.2.0 → 1.3.0 ✅
    - "patch"   # 1.2.0 → 1.2.1 ✅
    # Major not included → requires manual review
```

#### Development Dependencies

```yaml
development-dependencies:
  patterns:
    - "pytest*"
    - "ruff"
    - "mypy"
  update-types:
    - "minor"
    - "patch"
```

---

## 🤖 Auto-merge

### Rules

| Update Type | Action |
|-------------|--------|
| Security patch | ✅ Auto-merge immediately |
| Minor (dev deps) | ✅ Auto-merge if CI passes |
| Minor (prod deps) | ⏸️ Approve only, manual merge |
| Major | ⏸️ Approve + warning comment |
| CI fails | ❌ Blocked |

### Prerequisites

1. **Enable auto-merge in GitHub:**
   - Settings → General → Pull Requests
   - ☑️ Allow auto-merge

2. **Configure branch protection:**
   - Settings → Branches → Add rule for `main`
   - ☑️ Require status checks to pass
   - Select: `test`
   - ☑️ Require approvals: 1

### Workflow File

```
.github/workflows/dependabot-auto-merge.yml
```

---

## 📬 Managing PRs

### PR Anatomy

```
Title: ⬆️ chore(deps): Bump production-dependencies group
Labels: dependencies, python, automated
Assignee: your-username

Body:
Bumps the production-dependencies group with 3 updates:
- fastapi: 0.109.0 → 0.110.0
- uvicorn: 0.25.0 → 0.26.0
- pydantic: 2.5.0 → 2.6.0
```

### Review Workflow

```bash
# 1. Checkout the branch
git fetch origin
git checkout dependabot/pip/production-dependencies-xxx

# 2. Test locally
pip install -r requirements.txt
make test

# 3. Merge if OK
gh pr merge --squash
```

### Useful Commands

```bash
# List all Dependabot PRs
gh pr list --label "dependencies"

# Approve all patch PRs
gh pr list --label "dependencies" --json number,title | \
  jq -r '.[] | select(.title | contains("patch")) | .number' | \
  xargs -I {} gh pr review {} --approve
```

---

## 🐛 Troubleshooting

### No PRs Created

**Check:**
1. Dependabot enabled in Settings → Code security
2. `.github/dependabot.yml` exists and is valid
3. Run: Insights → Dependency graph → Dependabot → "Check for updates"

### Too Many Open PRs

**Solution:**
```yaml
open-pull-requests-limit: 2  # Reduce limit
```

### Auto-merge Not Working

**Checklist:**
- [ ] "Allow auto-merge" enabled in Settings
- [ ] Branch protection configured on `main`
- [ ] Status check `test` required
- [ ] Workflow `dependabot-auto-merge.yml` exists

### Major Updates Needed

```bash
# Manual upgrade in requirements.txt
fastapi>=1.0.0

# Commit
git commit -m "⬆️ chore(deps): upgrade FastAPI to 1.x"
```

---

## 📊 Metrics

| Metric | Target |
|--------|--------|
| PRs/week | 2-4 |
| Review time | <30min |
| Auto-merge rate | >70% |
| Open vulnerabilities | 0 |

### Monitor

- **GitHub:** Insights → Dependency graph → Dependabot
- **Security:** Settings → Security → Dependabot alerts

---

## 📚 Resources

- [Dependabot Docs](https://docs.github.com/en/code-security/dependabot)
- [Grouping Configuration](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file#groups)
- [Semantic Versioning](https://semver.org/)
