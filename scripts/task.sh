#!/usr/bin/env bash
set -euo pipefail
# Wrapper to run cross-platform tasks via uv + Python
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
uv run python "$SCRIPT_DIR/tasks.py" "$@"
