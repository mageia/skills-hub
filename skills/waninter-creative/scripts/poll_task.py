#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from waninter_utils import (
    create_output_dir,
    download_file,
    extract_media_url,
    extract_status,
    fail,
    guess_extension_from_url,
    load_config,
    request_json,
    write_json,
)

SUCCESS = {"succeeded", "success", "completed", "complete", "done", "finished"}
FAILURE = {"failed", "failure", "error", "cancelled", "canceled"}
RUNNING = {"queued", "pending", "running", "processing", "in_progress", "starting"}


def poll(cfg, task_id: str, timeout: int, interval: int):
    path_template = cfg["task_status_path"]
    deadline = time.time() + timeout
    last = None
    while True:
        path = path_template.replace("{task_id}", task_id)
        data = request_json(cfg, "GET", path, None)
        last = data
        status = extract_status(data) or "unknown"
        if status in SUCCESS or extract_media_url(data):
            return "succeeded", data
        if status in FAILURE:
            return "failed", data
        if time.time() >= deadline:
            return "timeout", data
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Poll a Waninter Creative async task")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--output", default="./outputs")
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--interval", type=int)
    parser.add_argument("--download", action="store_true", default=True)
    parser.add_argument("--no-download", dest="download", action="store_false")
    args = parser.parse_args()

    cfg = load_config()
    out_dir = create_output_dir(args.output, "task-")
    timeout = args.timeout or int(cfg.get("poll_timeout_seconds", 1800))
    interval = args.interval or int(cfg.get("poll_interval_seconds", 5))
    status, data = poll(cfg, args.task_id, timeout, interval)
    write_json(out_dir / "response.json", data)

    media_url = extract_media_url(data)
    file_path = None
    if args.download and media_url:
        ext = guess_extension_from_url(media_url, ".mp4")
        file_path = download_file(media_url, out_dir / f"result{ext}")

    result = {
        "type": "task",
        "status": status,
        "task_id": args.task_id,
        "file": str(file_path) if file_path else None,
        "url": media_url,
        "output_dir": str(out_dir),
    }
    write_json(out_dir / "metadata.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if status in {"failed", "timeout"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
