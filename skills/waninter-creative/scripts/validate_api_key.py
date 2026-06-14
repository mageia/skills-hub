#!/usr/bin/env python3
from __future__ import annotations

import json
from waninter_utils import load_config, request_json


def main() -> None:
    cfg = load_config()
    # /v1/models is public, so validate against a protected endpoint.
    data = request_json(cfg, "GET", cfg["generation_tasks_path"] + "?limit=1", None)
    print(json.dumps({"status": "succeeded", "message": "API Key is valid for protected Waninter Creative endpoints.", "response": data}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
