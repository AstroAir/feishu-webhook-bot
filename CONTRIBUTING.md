# Contributing

Thanks for your interest in contributing!

## Development setup

- Install [uv](https://docs.astral.sh/uv/)
- Sync dependencies (including dev tools):
  - `uv sync --all-groups`
- Run tests: `uv run pytest`
- Run linters: `uv run ruff check` and `uv run black --check .`
- Type check: `uv run mypy .`

## Pull requests

1. Fork and create a topic branch from `master`.
2. Ensure CI is green locally: lint, type-check, test, and build.
3. Update README/docs/changelog as needed.
4. Open a PR with a clear description of changes and motivation.
