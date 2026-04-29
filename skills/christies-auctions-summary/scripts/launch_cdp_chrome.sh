#!/usr/bin/env bash
set -euo pipefail

CDP_PORT="${CDP_PORT:-9222}"
USER_DATA_DIR="${USER_DATA_DIR:-$HOME/.chrome-debug-profile}"
PROFILE_DIRECTORY="${PROFILE_DIRECTORY:-Default}"
CHROME_COMMAND="${CHROME_COMMAND:-}"

if [[ ! -d "$USER_DATA_DIR" ]]; then
  echo "Chrome user data dir does not exist: $USER_DATA_DIR" >&2
  echo "Create it and log in to Christie's with this profile before running login-enhanced collection." >&2
  exit 3
fi

if [[ -n "$CHROME_COMMAND" ]]; then
  eval "$CHROME_COMMAND --remote-debugging-port=\"$CDP_PORT\" --user-data-dir=\"$USER_DATA_DIR\" --profile-directory=\"$PROFILE_DIRECTORY\"" >/dev/null 2>&1 &
  echo "Chrome launch requested using CHROME_COMMAND on CDP port $CDP_PORT"
  exit 0
fi

if command -v open >/dev/null 2>&1; then
  open -na "Google Chrome" --args \
    --remote-debugging-port="$CDP_PORT" \
    --user-data-dir="$USER_DATA_DIR" \
    --profile-directory="$PROFILE_DIRECTORY" \
    >/dev/null 2>&1
  echo "Chrome launch requested with macOS open on CDP port $CDP_PORT"
  exit 0
fi

for candidate in google-chrome chromium-browser chromium chrome; do
  if command -v "$candidate" >/dev/null 2>&1; then
    "$candidate" \
      --remote-debugging-port="$CDP_PORT" \
      --user-data-dir="$USER_DATA_DIR" \
      --profile-directory="$PROFILE_DIRECTORY" \
      >/dev/null 2>&1 &
    echo "Chrome launch requested with $candidate on CDP port $CDP_PORT"
    exit 0
  fi
done

echo "Could not find a Chrome-compatible launcher. Set CHROME_COMMAND explicitly." >&2
exit 2
