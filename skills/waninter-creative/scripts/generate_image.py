#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from waninter_utils import create_output_dir, defaults_from_model, download_file, extract_result_urls, extract_task, file_to_data_url, guess_extension_from_url, load_config, pick_model, request_json, write_json
from poll_task import poll

ASPECT_TO_SIZE = {"1:1": "1024x1024", "16:9": "1536x864", "9:16": "864x1536", "4:3": "1365x1024", "3:4": "1024x1365"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an image with Waninter Creative")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--input", help="Optional input image for image-to-image/editing if the selected model supports it")
    parser.add_argument("--model")
    parser.add_argument("--size")
    parser.add_argument("--aspect-ratio")
    parser.add_argument("--quality")
    parser.add_argument("--output-format", default="png")
    parser.add_argument("--output", default="./outputs")
    parser.add_argument("--no-wait", action="store_true")
    parser.add_argument("--timeout", type=int)
    args = parser.parse_args()

    cfg = load_config()
    model = pick_model(cfg, "image", args.model)
    params = defaults_from_model(cfg, model)
    if args.size:
        params["size"] = args.size
    elif args.aspect_ratio and "size" in params:
        params["size"] = ASPECT_TO_SIZE.get(args.aspect_ratio, params.get("size"))
    elif args.aspect_ratio and "aspectRatio" in params:
        params["aspectRatio"] = args.aspect_ratio
    if args.quality and "quality" in params:
        params["quality"] = args.quality
    if args.output_format and "output_format" in params:
        params["output_format"] = args.output_format
    params.setdefault("n", 1)

    if args.input:
        params["image"] = file_to_data_url(args.input)

    payload = {"type": "image", "model": model, "prompt": args.prompt, "params": params}
    out_dir = create_output_dir(args.output, "image-")
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
        ext = guess_extension_from_url(url, f".{args.output_format or 'png'}")
        files.append(str(download_file(url, out_dir / f"image-{idx}{ext}")))
    result = {"type": "image", "status": status, "task_id": task_id or None, "files": files, "urls": urls, "prompt": args.prompt, "model": model, "parameters": {k:v for k,v in params.items() if k != "image"}, "output_dir": str(out_dir)}
    write_json(out_dir / "metadata.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if status in {"failed", "timeout"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
