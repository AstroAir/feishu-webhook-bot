# Contributing

See the root `CONTRIBUTING.md` for full guidelines.

## Local development quickstart

- Install dependencies: `uv sync --all-groups`
- Run checks: `uv run ruff check .` and `uv run black --check .`
- Type check: `uv run mypy .`
- Run tests: `uv run pytest -q`
- Build docs: `uv run mkdocs build --strict`
- Serve docs locally: `uv run mkdocs serve -a localhost:8000`
