
# 📚 1min-Gateway Documentation

Welcome to the 1min-Gateway documentation. This index provides quick access to all guides and references.

---

## 🚀 Getting Started

| Document | Description |
|----------|-------------|
| [README](../README.md) | Project overview, features, and quick start |
| [Integration Guide](INTEGRATION-GUIDE.md) | Complete setup walkthrough |

---

## 👩‍💻 Development

| Document | Description |
|----------|-------------|
| [Contributing Guide](CONTRIBUTING.md) | Code standards, commit conventions, PR process |
| [API Parameters](API_PARAMETERS.md) | Supported API parameters and options |

---

## 🔧 DevOps & CI/CD

| Document | Description |
|----------|-------------|
| [CI/CD Documentation](CI-CD-DOCUMENTATION.md) | Pipeline architecture, configuration, security |
| [CI/CD Cheatsheet](CI-CD-CHEATSHEET.md) | Quick reference for releases and commands |
| [Dependabot Guide](DEPENDABOT-DOCUMENTATION.md) | Automated dependency management |

---

## 🐳 Infrastructure

| Document | Description |
|----------|-------------|
| [Environment & Docker Guide](ENV-DOCKER-GUIDE.md) | Configuration, Docker Compose, secrets management |

---

## 💎 Support

| Document | Description |
|----------|-------------|
| [Funding](FUNDING.yml) | Sponsorship and support options |

---

## 📋 Quick Reference

### Commit Format

```
:gitmoji: type(Scope): description
```

**Example:** `:sparkles: feat(Core): add streaming support`

### Allowed Scopes

`Core` • `Gateway` • `Docker` • `Config` • `Logging` • `CI/CD` • `deps` • `deps-dev` • `release`

### Common Gitmojis

| Emoji | Code | Type | Release |
|-------|------|------|---------|
| ✨ | `:sparkles:` | feat | Minor |
| 🐛 | `:bug:` | fix | Patch |
| 📝 | `:memo:` | docs | None |
| ♻️ | `:recycle:` | refactor | None |
| 🔧 | `:wrench:` | chore | None |

### Makefile Commands

```bash
make install    # Setup environment
make dev        # Start dev server
make test       # Run tests
make lint       # Check code quality
make up         # Docker Compose up
make down       # Docker Compose down
```

---

## 🗂 File Structure

```
1min-gateway/
├── README.md                 # Project overview
├── docs/
│   ├── index.md              # This file
│   ├── CONTRIBUTING.md       # Development guide
│   ├── API_PARAMETERS.md     # API reference
│   ├── CI-CD-DOCUMENTATION.md
│   ├── CI-CD-CHEATSHEET.md
│   ├── DEPENDABOT-DOCUMENTATION.md
│   ├── ENV-DOCKER-GUIDE.md
│   ├── INTEGRATION-GUIDE.md
│   └── FUNDING.yml
├── src/                      # Source code
├── tests/                    # Test suite
├── .github/                  # CI/CD workflows
└── docker-compose.yml        # Container config
```

---

## 🔗 External Resources

- [1min.ai Documentation](https://1min.ai/docs)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Gitmoji Reference](https://gitmoji.dev)
- [Semantic Release](https://semantic-release.gitbook.io)
- [Ruff Documentation](https://docs.astral.sh/ruff/)

---

## 🆘 Need Help?

1. Check the relevant documentation above
2. Search [existing issues](https://github.com/BillelAttafi/1min-gateway/issues)
3. Join our [Discord](https://discord.gg/GQd3DrxXyj)
4. Open a new issue with:
   - Clear description of the problem
   - Steps to reproduce
   - Environment details (OS, Python version, Docker version)

---

*Last updated: 2024*
