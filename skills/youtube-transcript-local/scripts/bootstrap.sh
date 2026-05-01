#!/usr/bin/env bash
set -euo pipefail

require_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo 'python3 is required but was not found in PATH.' >&2
    exit 2
  fi
}

ensure_pip() {
  if python3 -m pip --version >/dev/null 2>&1; then
    return
  fi
  echo 'pip is missing; bootstrapping with ensurepip...'
  python3 -m ensurepip --upgrade
  if ! python3 -m pip --version >/dev/null 2>&1; then
    echo 'pip is still unavailable after ensurepip.' >&2
    exit 6
  fi
}

ensure_python_package() {
  local package="$1"
  local import_name="${2:-$1}"
  if python3 - <<PY >/dev/null 2>&1
import importlib
importlib.import_module('${import_name}')
PY
  then
    echo "Python package already available: ${package}"
    return
  fi
  echo "Installing Python package: ${package}"
  python3 -m pip install --upgrade "${package}"
}

ensure_yt_dlp() {
  if command -v yt-dlp >/dev/null 2>&1; then
    echo "yt-dlp already installed: $(yt-dlp --version)"
    return
  fi
  echo 'Installing yt-dlp with pip...'
  python3 -m pip install --upgrade yt-dlp
  if ! command -v yt-dlp >/dev/null 2>&1; then
    echo 'yt-dlp installation finished but the command is still unavailable in PATH.' >&2
    echo 'Try running: python3 -m pip install --upgrade yt-dlp' >&2
    exit 3
  fi
  echo "yt-dlp installed: $(yt-dlp --version)"
}

ensure_ffmpeg() {
  if command -v ffmpeg >/dev/null 2>&1; then
    echo "ffmpeg already installed: $(ffmpeg -version | head -n 1)"
    return
  fi

  if command -v brew >/dev/null 2>&1; then
    echo 'Installing ffmpeg with Homebrew...'
    brew install ffmpeg
  elif command -v apt-get >/dev/null 2>&1 && command -v sudo >/dev/null 2>&1; then
    echo 'Installing ffmpeg with apt-get...'
    sudo apt-get update
    sudo apt-get install -y ffmpeg
  elif command -v dnf >/dev/null 2>&1 && command -v sudo >/dev/null 2>&1; then
    echo 'Installing ffmpeg with dnf...'
    sudo dnf install -y ffmpeg
  else
    cat >&2 <<'MSG'
ffmpeg is required but could not be installed automatically.
Install it manually with one of these commands:
  brew install ffmpeg
  sudo apt-get update && sudo apt-get install -y ffmpeg
  sudo dnf install -y ffmpeg
MSG
    exit 4
  fi

  if ! command -v ffmpeg >/dev/null 2>&1; then
    echo 'ffmpeg installation did not make the command available in PATH.' >&2
    exit 5
  fi
  echo "ffmpeg installed: $(ffmpeg -version | head -n 1)"
}

main() {
  require_python
  ensure_pip
  ensure_yt_dlp
  ensure_ffmpeg
  ensure_python_package 'faster-whisper' 'faster_whisper'
  echo 'youtube-transcript-local bootstrap complete.'
}

main "$@"
