#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${CDP_URL:-}" ]]; then
  BASE_URL="${CDP_URL%/}"
else
  CDP_HOST="${CDP_HOST:-127.0.0.1}"
  CDP_PORT="${CDP_PORT:-9222}"
  BASE_URL="http://${CDP_HOST}:${CDP_PORT}"
fi
URL="${BASE_URL}/json/version"

if command -v curl >/dev/null 2>&1; then
  curl --fail --silent --show-error --max-time 8 "$URL" >/dev/null
else
  python3 - "$URL" <<'PY2'
import sys, urllib.request
url = sys.argv[1]
with urllib.request.urlopen(url, timeout=8) as response:
    if response.status >= 400:
        raise SystemExit(response.status)
PY2
fi

echo "CDP ready: $URL"
