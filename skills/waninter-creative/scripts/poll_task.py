#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from waninter_utils import create_output_dir, download_file, extract_result_urls, extract_task, guess_extension_from_url, load_config, request_json, write_json

SUCCESS = {"succeeded", "success", "completed", "complete", "done", "finished"}
FAILURE = {"failed", "failure", "error", "cancelled", "canceled"}


def poll(cfg, task_id: str, timeout: int, interval: int):
    deadline = time.time() + timeout
    last = {}
    while True:
        path = cfg["generation_task_path"].replace("{task_id}", task_id)
        envelope = request_json(cfg, "GET", path, None)
        task = extract_task(envelope)
        last = task
        status = str(task.get("status") or "unknown").lower()
        if status in SUCCESS or extract_result_urls(task):
            return "succeeded", task
        if status in FAILURE:
            return "failed", task
        if time.time() >= deadline:
            return "timeout", task
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Poll a Waninter Creative generation task")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--output", default="./outputs")
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--interval", type=int)
    parser.add_argument("--download", action="store_true", default=True)
    parser.add_argument("--no-download", dest="download", action="store_false")
    args = parser.parse_args()

    cfg = load_config()
    out_dir = create_output_dir(args.output, "task-")
    status, task = poll(cfg, args.task_id, args.timeout or int(cfg["poll_timeout_seconds"]), args.interval or int(cfg["poll_interval_seconds"]))
    write_json(out_dir / "task.json", task)

    files = []
    urls = extract_result_urls(task)
    if args.download:
        for idx, url in enumerate(urls, start=1):
            ext = guess_extension_from_url(url, ".mp4" if task.get("type") == "video" else ".png")
            files.append(str(download_file(url, out_dir / f"result-{idx}{ext}")))
    result = {"type": task.get("type", "task"), "status": status, "task_id": args.task_id, "files": files, "urls": urls, "task": task, "output_dir": str(out_dir)}
    write_json(out_dir / "metadata.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if status in {"failed", "timeout"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
