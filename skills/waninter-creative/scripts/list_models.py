#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from waninter_utils import get_models, load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="List available Waninter Creative models")
    parser.add_argument("--type", choices=["image", "video"], help="Filter by media type")
    args = parser.parse_args()
    cfg = load_config()
    models = get_models(cfg)
    if args.type:
        models = [m for m in models if m.get("type") == args.type or m.get("model_type") == args.type]
    print(json.dumps({"status": "succeeded", "models": models}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
