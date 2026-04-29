#!/usr/bin/env bash
set -euo pipefail

if command -v agent-browser >/dev/null 2>&1; then
  echo "agent-browser already installed: $(agent-browser --version)"
  exit 0
fi

if command -v npm >/dev/null 2>&1; then
  echo "Installing agent-browser with npm..."
  npm install -g agent-browser
  echo "agent-browser installed: $(agent-browser --version)"
  exit 0
fi

cat >&2 <<'MSG'
agent-browser is required but not installed, and npm is unavailable.
Install it manually, for example:
  npm install -g agent-browser
MSG
exit 2
