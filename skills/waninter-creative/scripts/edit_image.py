#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from waninter_utils import (
    create_output_dir,
    decode_b64_to_file,
    download_file,
    extract_b64_image,
    extract_media_url,
    extract_task_id,
    fail,
    guess_extension_from_url,
    load_config,
    multipart_request,
    write_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Edit an image with Waninter Creative")
    parser.add_argument("--input", required=True, help="Input image path")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--model")
    parser.add_argument("--size")
    parser.add_argument("--output", default="./outputs")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        fail(f"Input image not found: {input_path}")

    cfg = load_config()
    out_dir = create_output_dir(args.output, "edit-")
    model = args.model or cfg["default_image_model"]
    fields = {"model": model, "prompt": args.prompt, "size": args.size or cfg.get("default_image_size")}
    data = multipart_request(cfg, cfg["image_edit_path"], fields, {"image": input_path})
    write_json(out_dir / "response.json", data)

    file_path = None
    media_url = extract_media_url(data)
    if media_url:
        ext = guess_extension_from_url(media_url, ".png")
        file_path = download_file(media_url, out_dir / f"edited{ext}")
    else:
        b64 = extract_b64_image(data)
        if b64:
            file_path = decode_b64_to_file(b64, out_dir / "edited.png")

    task_id = extract_task_id(data)
    result = {
        "type": "image_edit",
        "status": "succeeded" if file_path or media_url or task_id else "unknown",
        "file": str(file_path) if file_path else None,
        "url": media_url,
        "task_id": task_id,
        "input": str(input_path),
        "prompt": args.prompt,
        "model": model,
        "parameters": {"size": args.size},
        "output_dir": str(out_dir),
    }
    write_json(out_dir / "metadata.json", result)
    if not (file_path or media_url or task_id):
        fail("Could not find edited image URL, base64 image, or task id in provider response", output_dir=str(out_dir))
    print_json(result)


def print_json(data):
    import json
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
