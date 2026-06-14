#!/usr/bin/env python3
from __future__ import annotations

import getpass
import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "waninter-creative"
CONFIG_FILE = CONFIG_DIR / "config.json"


def ask(prompt: str, default: str) -> str:
    value = input(f"{prompt} [{default}]: ").strip()
    return value or default


def main() -> None:
    print("Waninter Creative API configuration")
    print(f"Config file: {CONFIG_FILE}")
    api_key = getpass.getpass("Enter your Waninter Creative API Key: ").strip()
    if not api_key:
        raise SystemExit("API key is required.")

    base_url = ask("Base URL", "https://creative-studio.waninter.com")
    default_image_model = ask("Default image model", "wan-image")
    default_video_model = ask("Default video model", "wan-video")
    image_generation_path = ask("Image generation path", "/v1/images/generations")
    image_edit_path = ask("Image edit path", "/v1/images/edits")
    video_generation_path = ask("Video generation path", "/v1/videos/generations")
    task_status_path = ask("Task status path", "/v1/tasks/{task_id}")

    config = {
        "api_key": api_key,
        "base_url": base_url,
        "auth_header": "Authorization",
        "auth_scheme": "Bearer",
        "default_image_model": default_image_model,
        "default_video_model": default_video_model,
        "image_generation_path": image_generation_path,
        "image_edit_path": image_edit_path,
        "video_generation_path": video_generation_path,
        "task_status_path": task_status_path,
        "request_timeout_seconds": 120,
        "poll_interval_seconds": 5,
        "poll_timeout_seconds": 1800,
        "image_response_format": "b64_json",
        "default_image_size": "1024x1024",
        "default_video_duration": 5,
        "default_video_aspect_ratio": "16:9"
    }

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(CONFIG_FILE, 0o600)
    print(f"Config saved to: {CONFIG_FILE}")
    print("API key stored locally with file mode 600.")


if __name__ == "__main__":
    main()
