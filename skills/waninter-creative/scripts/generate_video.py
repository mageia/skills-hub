#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from waninter_utils import create_output_dir, defaults_from_model, download_file, extract_result_urls, extract_task, file_to_data_url, guess_extension_from_url, load_config, pick_model, request_json, write_json


def split_csv_values(values: list[str] | None) -> list[str]:
    items: list[str] = []
    for value in values or []:
        for part in str(value).split(','):
            trimmed = part.strip()
            if trimmed:
                items.append(trimmed)
    return items
from poll_task import poll


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a video with Waninter Creative")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--image", help="Optional local input image for image-to-video")
    parser.add_argument("--image-url", action="append", help="Optional public input image URL. Repeat or pass comma-separated URLs.")
    parser.add_argument("--reference-image-url", action="append", help="Public reference image URL(s). Repeat or pass comma-separated URLs. Sent as reference_asset_urls.")
    parser.add_argument("--model")
    parser.add_argument("--duration")
    parser.add_argument("--aspect-ratio")
    parser.add_argument("--resolution")
    parser.add_argument("--output", default="./outputs")
    parser.add_argument("--no-wait", action="store_true")
    parser.add_argument("--timeout", type=int)
    args = parser.parse_args()

    cfg = load_config()
    model = pick_model(cfg, "video", args.model)
    params = defaults_from_model(cfg, model)
    if args.duration:
        params["duration"] = str(args.duration)
    if args.aspect_ratio:
        params["aspect_ratio"] = args.aspect_ratio
    if args.resolution:
        params["resolution"] = args.resolution
    image_urls = split_csv_values(args.image_url)
    reference_image_urls = split_csv_values(args.reference_image_url)
    if args.image:
        # The backend accepts local image guidance in params for image-to-video capable models.
        params["image"] = file_to_data_url(args.image)
    if image_urls:
        params["image_url"] = image_urls[0]
        params["reference_asset_url"] = image_urls[0]
        params["reference_asset_urls"] = image_urls
    if reference_image_urls:
        params["reference_asset_url"] = reference_image_urls[0]
        params["reference_asset_urls"] = reference_image_urls

    payload = {"type": "video", "model": model, "prompt": args.prompt, "params": params}
    out_dir = create_output_dir(args.output, "video-")
    envelope = request_json(cfg, "POST", cfg["generation_tasks_path"], payload)
    task = extract_task(envelope)
    write_json(out_dir / "initial_task.json", task)
    task_id = str(task.get("id") or "")
    status = str(task.get("status") or "submitted").lower()

    if task_id and not args.no_wait and not extract_result_urls(task):
        status, task = poll(cfg, task_id, args.timeout or int(cfg["poll_timeout_seconds"]), int(cfg["poll_interval_seconds"]))
        write_json(out_dir / "final_task.json", task)

    urls = extract_result_urls(task)
    files = []
    for idx, url in enumerate(urls, start=1):
        ext = guess_extension_from_url(url, ".mp4")
        files.append(str(download_file(url, out_dir / f"video-{idx}{ext}")))
    safe_params = {k: v for k, v in params.items() if k != "image"}
    result = {"type": "video", "status": status, "task_id": task_id or None, "files": files, "urls": urls, "prompt": args.prompt, "model": model, "parameters": safe_params, "output_dir": str(out_dir)}
    write_json(out_dir / "metadata.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if status in {"failed", "timeout"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
