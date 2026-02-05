# Contributing to 1min-Gateway 🚀

First off, thank you for considering contributing to **1min-Gateway**! To maintain a high standard of code quality and automation, we follow strict professional guidelines.

## 📜 Code of Conduct

By participating in this project, you agree to:

- Be respectful and inclusive.
- Use professional language (English only for code and commits).
- Ensure your contributions align with the project's goal: an OpenAI-compatible relay for 1min.ai.

## 🛠 Setup Development Environment

We use a **Makefile** to simplify the setup. Ensure you have `make` and `python 3.12+` installed.

1. **Clone the repository**:

   ```bash
   git clone [https://github.com/BillelAttafi/1min-gateway.git](https://github.com/BillelAttafi/1min-gateway.git)
   cd 1min-gateway

```

2. **Automated Installation**:
```bash
make install

```

*This command installs dependencies and sets up the mandatory git hooks for commit validation.*

## 🏗 Commit Message Guidelines

We use **Gitmoji** and **Conventional Commits**. This is required for our automated release system.

### Format

`:emoji: (scope): description`

### Rules

- **Language**: English only.
- **Scope**: Must be one of: `Core`, `Gateway`, `Docker`, `Config`, `Logging`, `CI/CD`.

### Examples

- ✅ `:sparkles: (Gateway): add streaming support for Claude 3.5`
- ✅ `:bug: (Core): fix token limit calculation`
- ❌ `fix bug` (Missing emoji, scope, and wrong format)

> **Pro Tip**: Use `make commit` to be guided through a structured prompt!

## 🧪 Testing & Quality

Before submitting a Pull Request, your code must pass the local checks:

```bash
make test

```

## 🚀 Pull Request Process

1. Create a branch: `git checkout -b feat/your-feature-name`.
2. Make your changes and commit using `make commit`.
3. Push to your fork and open a Pull Request to `main`.
4. Once CI/CD passes, your code will be reviewed and merged.

---

*Maintained with ❤️ by @BillelAttafi*
