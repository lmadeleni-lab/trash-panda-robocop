#!/usr/bin/env bash
set -euo pipefail

if command -v uv >/dev/null 2>&1; then
  exec uv run python -m raccoon_guardian.app
fi

exec python3 -m raccoon_guardian.app

