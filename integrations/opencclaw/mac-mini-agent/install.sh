#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="${OPENCLAW_WORKSPACE_DIR:-$HOME/.openclaw/workspace-trash-panda-robocop}"

mkdir -p "$WORKSPACE_DIR"

install -m 0644 "$SCRIPT_DIR/AGENTS.md" "$WORKSPACE_DIR/AGENTS.md"
install -m 0644 "$SCRIPT_DIR/SOUL.md" "$WORKSPACE_DIR/SOUL.md"
install -m 0644 "$SCRIPT_DIR/TOOLS.md" "$WORKSPACE_DIR/TOOLS.md"
install -m 0644 "$SCRIPT_DIR/HEARTBEAT.md" "$WORKSPACE_DIR/HEARTBEAT.md"

printf 'Installed trash-panda Robocop agent pack to %s\n' "$WORKSPACE_DIR"
