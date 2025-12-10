# Contributing Guide

Thank you for your interest in contributing to Feishu Webhook Bot! This guide will help you get started.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Style Guide](#style-guide)

## Code of Conduct

Please read and follow our [Code of Conduct](https://github.com/AstroAir/feishu-webhook-bot/blob/main/CODE_OF_CONDUCT.md).

## Getting Started

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Git

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork:

```bash
git clone https://github.com/YOUR_USERNAME/feishu-webhook-bot.git
cd feishu-webhook-bot
```

## Development Setup

### Install Dependencies

```bash
# Using uv (recommended)
uv sync --all-groups

# Or using pip
pip install -e ".[dev,test,docs]"
```

### Set Up Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

### Verify Setup

```bash
# Run tests
uv run pytest -q

# Run linters
uv run ruff check .
uv run black --check .

# Type check
uv run mypy .
```

## Making Changes

### Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions/changes

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```text
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:

```text
feat(plugins): add hot-reload support
fix(scheduler): handle timezone correctly
docs(readme): update installation instructions
```

## Testing

### Run Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=feishu_webhook_bot --cov-report=html

# Specific test file
uv run pytest tests/test_bot.py

# Specific test
uv run pytest tests/test_bot.py::test_send_text
```

### Write Tests

- Place tests in `tests/` directory
- Mirror source structure (e.g., `src/feishu_webhook_bot/core/` → `tests/core/`)
- Use pytest fixtures for common setup
- Aim for high coverage on new code

Example test:

```python
import pytest
from feishu_webhook_bot.core import BotConfig

def test_config_from_yaml(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
webhooks:
  - name: default
    url: https://example.com
""")
    
    config = BotConfig.from_yaml(config_file)
    assert config.webhooks[0].name == "default"
```

## Documentation

### Build Docs

```bash
# Build
uv run mkdocs build --strict

# Serve locally
uv run mkdocs serve -a localhost:8000
```

### Documentation Style

- Use clear, concise language
- Include code examples
- Add cross-references to related docs
- Update table of contents

### Docstrings

Use Google-style docstrings:

```python
def send_message(self, text: str, webhook: str = "default") -> bool:
    """Send a text message to a webhook.
    
    Args:
        text: The message text to send.
        webhook: The webhook name to use.
    
    Returns:
        True if the message was sent successfully.
    
    Raises:
        WebhookError: If the webhook is not configured.
    
    Example:
        >>> bot.send_message("Hello!", webhook="alerts")
        True
    """
```

## Submitting Changes

### Before Submitting

1. Run all checks:

```bash
uv run ruff check .
uv run black .
uv run mypy .
uv run pytest
```

2. Update documentation if needed
3. Add tests for new features
4. Update CHANGELOG.md

### Create Pull Request

1. Push your branch:

```bash
git push origin feature/your-feature-name
```

2. Open a PR on GitHub
3. Fill out the PR template
4. Wait for review

### PR Guidelines

- Keep PRs focused and small
- Include tests
- Update documentation
- Reference related issues
- Respond to review feedback

## Style Guide

### Python Style

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use `ruff` for linting
- Use `black` for formatting

### Code Organization

```python
# Imports (stdlib, third-party, local)
from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel

from .core import BotConfig
```

### Naming Conventions

- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_leading_underscore`

## Getting Help

- [GitHub Issues](https://github.com/AstroAir/feishu-webhook-bot/issues)
- [GitHub Discussions](https://github.com/AstroAir/feishu-webhook-bot/discussions)

## See Also

- [Installation Guide](../getting-started/installation.md)
- [API Reference](../reference/api.md)
- [Changelog](changelog.md)
