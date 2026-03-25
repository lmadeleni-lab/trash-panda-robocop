#!/usr/bin/env bash
set -euo pipefail

if command -v uv >/dev/null 2>&1; then
  uv run ruff check .
  uv run mypy src
  exec uv run pytest
fi

ruff check .
mypy src
exec pytest

