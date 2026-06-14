#!/usr/bin/env python3
from __future__ import annotations

import getpass
import json
import os
import sys
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
    print("Only your API Key is required. Models and API endpoints are preconfigured.")
    print("Tip: use a Waninter Creative API Key created on the /api page, usually starting with sk_live_.")
    api_key = getpass.getpass("Enter your Waninter Creative API Key: ").strip()
    if not api_key:
        raise SystemExit("API key is required.")

    config = {"api_key": api_key, **DEFAULT_CONFIG}
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(CONFIG_FILE, 0o600)
    print(f"Config saved to: {CONFIG_FILE}")

    # Validate against a protected endpoint. /v1/models is public and cannot prove key validity.
    scripts_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(scripts_dir))
    try:
        from waninter_utils import request_json
        request_json(config, "GET", config["generation_tasks_path"] + "?limit=1", None)
    except SystemExit:
        print("\nValidation failed. The key was saved, but Waninter Creative rejected it.")
        print("Please create/copy a valid API Key from the Waninter Creative /api page and run this script again.")
        raise
    print("Validation succeeded. API Key can access protected Waninter Creative endpoints.")
    print("Done. You can now generate images and videos with Waninter Creative.")


if __name__ == "__main__":
    main()
