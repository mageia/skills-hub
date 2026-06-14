#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from waninter_utils import (
    create_output_dir,
    download_file,
    extract_media_url,
    extract_status,
    extract_task_id,
    fail,
    file_to_b64,
    guess_extension_from_url,
    load_config,
    request_json,
    write_json,
)
from poll_task import poll

SUCCESS = {"succeeded", "success", "completed", "complete", "done", "finished"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a video with Waninter Creative")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--image", help="Optional input image for image-to-video")
    parser.add_argument("--model")
    parser.add_argument("--duration", type=int)
    parser.add_argument("--aspect-ratio")
    parser.add_argument("--output", default="./outputs")
    parser.add_argument("--no-wait", action="store_true", help="Return immediately if provider creates an async task")
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--interval", type=int)
    args = parser.parse_args()

    image_path = Path(args.image) if args.image else None
    if image_path and not image_path.exists():
        fail(f"Input image not found: {image_path}")

    cfg = load_config()
    out_dir = create_output_dir(args.output, "video-")
    model = args.model or cfg["default_video_model"]
    duration = args.duration or int(cfg.get("default_video_duration", 5))
    aspect_ratio = args.aspect_ratio or cfg.get("default_video_aspect_ratio", "16:9")
    payload = {
        "model": model,
        "prompt": args.prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
    }
    if image_path:
        payload["image"] = file_to_b64(image_path)
        payload["image_filename"] = image_path.name

    data = request_json(cfg, "POST", cfg["video_generation_path"], payload)
    write_json(out_dir / "initial_response.json", data)

    media_url = extract_media_url(data)
    task_id = extract_task_id(data)
    status = extract_status(data) or ("succeeded" if media_url else "submitted")
    final_data = data

    if task_id and not media_url and not args.no_wait:
        timeout = args.timeout or int(cfg.get("poll_timeout_seconds", 1800))
        interval = args.interval or int(cfg.get("poll_interval_seconds", 5))
        status, final_data = poll(cfg, task_id, timeout, interval)
        write_json(out_dir / "final_response.json", final_data)
        media_url = extract_media_url(final_data)

    file_path = None
    if media_url:
        ext = guess_extension_from_url(media_url, ".mp4")
        file_path = download_file(media_url, out_dir / f"video{ext}")

    result = {
        "type": "video",
        "status": status,
        "file": str(file_path) if file_path else None,
        "url": media_url,
        "task_id": task_id,
        "input_image": str(image_path) if image_path else None,
        "prompt": args.prompt,
        "model": model,
        "parameters": {"duration": duration, "aspect_ratio": aspect_ratio},
        "output_dir": str(out_dir),
    }
    write_json(out_dir / "metadata.json", result)

    if not (file_path or media_url or task_id):
        fail("Could not find video URL or task id in provider response", output_dir=str(out_dir))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if status in {"failed", "timeout"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
