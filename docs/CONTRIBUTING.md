
# Contributing to 1min-Gateway

Thank you for contributing to **1min-Gateway**! This guide covers our development workflow and standards.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Development Setup](#development-setup)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Code Quality](#code-quality)

---

## 📜 Code of Conduct

- Be respectful and inclusive
- Use English for code, commits, and documentation
- Follow the project's coding standards

---

## 🛠 Development Setup

### Prerequisites

- Python 3.12+
- Node.js 18+ (for commit hooks)
- Docker (optional, for containerized testing)

### Installation

```bash
# Clone the repository
git clone https://github.com/BillelAttafi/1min-gateway.git
cd 1min-gateway

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies and hooks
make install
```

This command:
- Installs Python dependencies
- Installs Node.js dependencies (commitlint)
- Configures pre-commit hooks

---

## 📝 Commit Guidelines

We use **Gitmoji + Conventional Commits** for semantic versioning.

### Format

```
:gitmoji: type(Scope): description
```

### Components

| Component | Description | Example |
|-----------|-------------|---------|
| **Gitmoji** | Emoji code (not Unicode) | `:sparkles:` |
| **Type** | Change category | `feat`, `fix`, `docs` |
| **Scope** | Affected area (PascalCase) | `Core`, `Gateway`, `Config` |
| **Description** | Brief summary | `add streaming support` |

### Allowed Scopes

`Core` • `Gateway` • `Docker` • `Config` • `Logging` • `CI/CD` • `deps` • `deps-dev` • `release`

### Examples

```bash
# ✅ Correct
:sparkles: feat(Gateway): add streaming support for Claude 3.5
:bug: fix(Core): resolve token calculation error
:memo: docs(Config): update environment variables guide
:wrench: chore(deps): update FastAPI to 0.110.0

# ❌ Incorrect
fix bug                           # Missing gitmoji, scope, format
✨ feat: add feature              # Missing scope, using Unicode
:sparkles: feat(core): feature    # Scope not PascalCase
```

### Release Impact

| Gitmoji | Type | Version Bump |
|---------|------|--------------|
| `:sparkles:` | `feat` | Minor (1.0.0 → 1.1.0) |
| `:bug:` | `fix` | Patch (1.0.0 → 1.0.1) |
| `:zap:` | `perf` | Patch |
| `:lock:` | `security` | Patch |
| `:boom:` | breaking | Major (1.0.0 → 2.0.0) |
| `:memo:` | `docs` | No release |
| `:recycle:` | `refactor` | Patch |
| `:wrench:` | `chore` | No release |

### Commit Example

```bash
git commit -m ":sparkles: feat(Gateway): your description here"
```

---

## 🔀 Pull Request Process

### 1. Create a Feature Branch

```bash
git checkout -b feat/your-feature-name
```

Branch naming conventions:
- `feat/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation
- `refactor/description` - Code refactoring

### 2. Make Changes

```bash
# Code your changes...

# Run quality checks
make lint
make test
```

### 3. Commit Changes

```bash
git add .
git commit -m ":sparkles: feat(Core): your feature description"
```

Pre-commit hooks will automatically:
- Format code with Ruff
- Check for lint errors
- Detect potential secrets
- Validate commit message format

### 4. Push and Create PR

```bash
git push origin feat/your-feature-name
```

Then create a Pull Request on GitHub.

### 5. CI/CD Validation

Your PR will automatically run:
- ✅ Unit tests with coverage
- ✅ Lint checks (Ruff)
- ✅ Docker build validation
- ✅ Security scanning (Trivy)

### 6. Review and Merge

Once approved and CI passes, merge your PR. If it contains `feat` or `fix` commits, a new release will be created automatically.

---

## 🧪 Code Quality

### Running Tests

```bash
# All tests with coverage
make test

# Specific test file
pytest tests/test_domain/test_ports.py -v

# With coverage report
pytest --cov=src --cov-report=html
```

### Code Formatting

```bash
# Check formatting
make lint

# Auto-fix issues
make format
```

### Pre-commit Hooks

Hooks run automatically on commit:

| Hook | Description |
|------|-------------|
| **ruff** | Linting (replaces flake8, isort) |
| **ruff-format** | Formatting (replaces black) |
| **detect-secrets** | Prevent secret leaks |
| **commitlint** | Validate commit format |
| **hadolint** | Dockerfile linting |

Run manually:

```bash
pre-commit run --all-files
```

---

## 🏗 Project Structure

```
1min-gateway/
├── src/
│   ├── domain/           # Business logic, models, ports
│   │   └── services/     # Domain services
│   ├── application/      # Use cases
│   ├── adapters/         # Interface adapters
│   ├── infrastructure/   # External services (Memcached, etc.)
│   │   └── adapters/
│   └── api/              # FastAPI routes, schemas
├── tests/
│   ├── test_domain/
│   ├── test_application/
│   ├── test_adapters/
│   ├── test_infrastructure/
│   └── test_integration/
├── docs/                 # Documentation
├── deploy.sh             # Automated server deployment
└── .github/              # CI/CD workflows
```

---

## 📚 Resources

- [Gitmoji Reference](https://gitmoji.dev)
- [Conventional Commits](https://conventionalcommits.org)
- [Semantic Release](https://semantic-release.gitbook.io)
- [Ruff Documentation](https://docs.astral.sh/ruff/)

---

*Maintained with ❤️ by [@BillelAttafi](https://github.com/BillelAttafi)*
