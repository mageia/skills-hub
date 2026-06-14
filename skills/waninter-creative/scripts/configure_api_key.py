#!/usr/bin/env python3
from __future__ import annotations

import getpass
import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "waninter-creative"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "base_url": "https://creative-studio.waninter.com",
    "auth_header": "Authorization",
    "auth_scheme": "Bearer",
    "models_path": "/v1/models",
    "generation_tasks_path": "/v1/generation-tasks",
    "generation_task_path": "/v1/generation-tasks/{task_id}",
    "default_image_model": "nano-banana-3-1",
    "fallback_image_model": "gpt-image-2",
    "default_video_model": "sd2-720p",
    "fallback_video_model": "doubao-seedance-2-0-fast-260128",
    "request_timeout_seconds": 120,
    "poll_interval_seconds": 5,
    "poll_timeout_seconds": 1800,
}


def main() -> None:
    print("Waninter Creative API configuration")
    print(f"Config file: {CONFIG_FILE}")
    print("Only your API Key is required. Models and API endpoints are preconfigured and can be auto-discovered later.")
    api_key = getpass.getpass("Enter your Waninter Creative API Key: ").strip()
    if not api_key:
        raise SystemExit("API key is required.")

    config = {"api_key": api_key, **DEFAULT_CONFIG}
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(CONFIG_FILE, 0o600)
    print(f"Config saved to: {CONFIG_FILE}")
    print("Done. You can now generate images and videos with Waninter Creative.")


if __name__ == "__main__":
    main()
