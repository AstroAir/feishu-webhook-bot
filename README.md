# python-quick-starter

> A professional Python project template powered by uv, pytest, ruff, black, and GitHub Actions.

## What is this?

A batteries-included starter for modern Python projects using the src/ layout, sensible toolchain, and CI.

- src-based package layout: `src/python_quick_starter`
- Testing with pytest
- Linting and import sorting with Ruff, formatting with Black
- Type checking with mypy
- uv for dependency and Python management
- GitHub Actions for CI (tests, lint, type-check, build)

## Installation

First, install uv (one-time):

```powershell
# Windows PowerShell
irm https://astral.sh/uv/install.ps1 | iex
```

Clone the repo and install dependencies (including dev tools):

```powershell
uv sync --all-groups
```

This creates a virtual environment (usually at `.venv`) and installs dependencies.

## Usage

Run the CLI:

```powershell
uv run python-quick-starter --name Alice
```

Or as a module:

```powershell
uv run python -m python_quick_starter --name Bob
```

Basic Python import:

```python
from python_quick_starter.cli import main
main(["--name", "Charlie"])  # returns 0
```

## Development

- Format: `uv run black .`
- Lint: `uv run ruff check .`
- Type-check: `uv run mypy .`
- Tests: `uv run pytest -q`
- Build: `uv build`

Common one-liner to check everything:

```powershell
uv run ruff check . ; uv run black --check . ; uv run mypy . ; uv run pytest -q ; uv build
```

## Documentation (MkDocs)

This template includes a MkDocs site using the Material theme.

- Build docs: `uv run mkdocs build --strict`
- Serve docs locally: `uv run mkdocs serve -a localhost:8000`

The configuration lives in `mkdocs.yml`; content is in the `docs/` folder. API reference is generated from the package using `mkdocstrings`.

## Automation scripts

Cross-platform task runner scripts are provided in `scripts/`:

- Python task runner: `uv run python scripts/tasks.py [task]`
- Bash wrapper (Linux/macOS): `scripts/task.sh [task]`
- PowerShell wrapper (Windows): `scripts/task.ps1 [task]`

Available tasks: `setup`, `lint`, `format`, `typecheck`, `test`, `build`, `docs:build`, `docs:serve`, `ci` (all checks).

## Project Structure

```text
.
├─ src/
│  └─ python_quick_starter/
│     ├─ __init__.py
│     ├─ __main__.py
│     └─ cli.py
├─ tests/
│  └─ test_cli.py
├─ docs/
│  └─ index.md
├─ .github/workflows/ci.yml
├─ pyproject.toml
├─ README.md
├─ LICENSE
└─ CHANGELOG.md
```

## Testing

This template uses pytest. Configuration lives in `pyproject.toml` under `tool.pytest.ini_options`.

```powershell
uv run pytest -q
```

## Contributing

See `CONTRIBUTING.md` for guidelines. Issues and PRs are welcome.

## Releasing

A release workflow template is included at `.github/workflows/release.yml` and is commented out by default. To enable publishing to PyPI:

- Create a PyPI token and save it as `PYPI_API_TOKEN` in GitHub repo secrets
- Uncomment the publish step in `release.yml`
- Push a tag like `v0.1.0`

## License

MIT — see `LICENSE`.
