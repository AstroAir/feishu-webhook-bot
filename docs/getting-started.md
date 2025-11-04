# Getting started

This project uses [uv](https://docs.astral.sh/uv/) for Python and dependency management.

## Prerequisites

- Python 3.12 or newer
- uv installed

## Install dependencies

```powershell
uv sync --all-groups
```

## Run the CLI

```powershell
uv run feishu-webhook-bot --name Alice
```

## Run tests

```powershell
uv run pytest -q
```
