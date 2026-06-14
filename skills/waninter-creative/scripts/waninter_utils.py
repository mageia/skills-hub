#!/usr/bin/env python3
"""Shared helpers for Waninter Creative scripts."""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

CONFIG_DIR = Path.home() / ".config" / "waninter-creative"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULTS = {
    "base_url": "https://creative-studio.waninter.com",
    "auth_header": "Authorization",
    "auth_scheme": "Bearer",
    "default_image_model": "wan-image",
    "default_video_model": "wan-video",
    "image_generation_path": "/v1/images/generations",
    "image_edit_path": "/v1/images/edits",
    "video_generation_path": "/v1/videos/generations",
    "task_status_path": "/v1/tasks/{task_id}",
    "request_timeout_seconds": 120,
    "poll_interval_seconds": 5,
    "poll_timeout_seconds": 1800,
    "image_response_format": "b64_json",
    "default_image_size": "1024x1024",
    "default_video_duration": 5,
    "default_video_aspect_ratio": "16:9",
}


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


def fail(message: str, **extra: Any) -> None:
    payload = {"status": "failed", "error": message}
    payload.update(extra)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(1)


def load_config() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        fail(
            f"Missing config file: {CONFIG_FILE}. Run: python3 scripts/configure_api_key.py"
        )
    try:
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON config: {exc}")
    cfg = {**DEFAULTS, **raw}
    if not cfg.get("api_key"):
        fail("Missing api_key in config. Run: python3 scripts/configure_api_key.py")
    return cfg


def redacted_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    safe = dict(cfg)
    if "api_key" in safe:
        safe["api_key"] = "***REDACTED***"
    return safe


def build_url(cfg: Dict[str, Any], path: str) -> str:
    base = str(cfg.get("base_url", "")).rstrip("/")
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return base + "/" + path.lstrip("/")


def headers(cfg: Dict[str, Any], content_type: Optional[str] = "application/json") -> Dict[str, str]:
    h: Dict[str, str] = {}
    if content_type:
        h["Content-Type"] = content_type
    auth_header = cfg.get("auth_header") or "Authorization"
    auth_scheme = cfg.get("auth_scheme")
    api_key = cfg["api_key"]
    h[auth_header] = f"{auth_scheme} {api_key}" if auth_scheme else api_key
    h.update(cfg.get("extra_headers") or {})
    return h


def request_json(
    cfg: Dict[str, Any],
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    url = build_url(cfg, path)
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method=method.upper(), headers=headers(cfg))
    try:
        with urllib.request.urlopen(req, timeout=timeout or int(cfg["request_timeout_seconds"])) as resp:
            data = resp.read()
            text = data.decode("utf-8", errors="replace")
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        fail(f"HTTP {exc.code} from provider", response=safe_text(text))
    except urllib.error.URLError as exc:
        fail(f"Network error: {exc}")
    except json.JSONDecodeError as exc:
        fail(f"Provider returned non-JSON response: {exc}")
    raise AssertionError("unreachable")


def safe_text(text: str, limit: int = 2000) -> str:
    return text[:limit]


def create_output_dir(root: str | Path, prefix: str = "") -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = f"{prefix}{stamp}" if prefix else stamp
    out = Path(root) / "waninter-creative" / name
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def download_file(url: str, output_path: Path, timeout: int = 300) -> Path:
    req = urllib.request.Request(url, headers={"User-Agent": "waninter-creative-skill/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        output_path.write_bytes(resp.read())
    return output_path


def decode_b64_to_file(value: str, output_path: Path) -> Path:
    if "," in value and value.strip().startswith("data:"):
        value = value.split(",", 1)[1]
    output_path.write_bytes(base64.b64decode(value))
    return output_path


def file_to_b64(path: str | Path) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def guess_extension_from_url(url: str, default: str) -> str:
    parsed = urllib.parse.urlparse(url)
    ext = Path(parsed.path).suffix
    return ext if ext else default


def extract_media_url(data: Any) -> Optional[str]:
    if isinstance(data, str) and data.startswith(("http://", "https://")):
        return data
    if isinstance(data, dict):
        for key in ("url", "download_url", "file_url", "video_url", "image_url"):
            val = data.get(key)
            if isinstance(val, str) and val.startswith(("http://", "https://")):
                return val
        for key in ("output", "result", "data", "file", "files", "images", "videos"):
            val = data.get(key)
            found = extract_media_url(val)
            if found:
                return found
    if isinstance(data, list):
        for item in data:
            found = extract_media_url(item)
            if found:
                return found
    return None


def extract_b64_image(data: Any) -> Optional[str]:
    if isinstance(data, dict):
        for key in ("b64_json", "base64", "image_base64", "data"):
            val = data.get(key)
            if isinstance(val, str) and len(val) > 100:
                return val
        for key in ("output", "result", "data", "images"):
            found = extract_b64_image(data.get(key))
            if found:
                return found
    if isinstance(data, list):
        for item in data:
            found = extract_b64_image(item)
            if found:
                return found
    return None


def extract_task_id(data: Any) -> Optional[str]:
    if isinstance(data, dict):
        for key in ("task_id", "taskId", "job_id", "jobId", "id"):
            val = data.get(key)
            if isinstance(val, (str, int)):
                return str(val)
        for key in ("task", "job", "data", "result"):
            found = extract_task_id(data.get(key))
            if found:
                return found
    return None


def extract_status(data: Any) -> Optional[str]:
    if isinstance(data, dict):
        for key in ("status", "state"):
            val = data.get(key)
            if isinstance(val, str):
                return val.lower()
        for key in ("task", "job", "data", "result"):
            found = extract_status(data.get(key))
            if found:
                return found
    return None


def multipart_request(
    cfg: Dict[str, Any],
    path: str,
    fields: Dict[str, Any],
    files: Dict[str, Path],
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    boundary = f"----WaninterCreative{int(time.time() * 1000)}"
    parts = []
    for name, value in fields.items():
        if value is None:
            continue
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        parts.append(str(value).encode())
        parts.append(b"\r\n")
    for name, path_obj in files.items():
        mime = mimetypes.guess_type(str(path_obj))[0] or "application/octet-stream"
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{path_obj.name}"\r\n'.encode()
        )
        parts.append(f"Content-Type: {mime}\r\n\r\n".encode())
        parts.append(path_obj.read_bytes())
        parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    h = headers(cfg, content_type=f"multipart/form-data; boundary={boundary}")
    req = urllib.request.Request(build_url(cfg, path), data=body, method="POST", headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout or int(cfg["request_timeout_seconds"])) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        fail(f"HTTP {exc.code} from provider", response=safe_text(text))
    except urllib.error.URLError as exc:
        fail(f"Network error: {exc}")
    except json.JSONDecodeError as exc:
        fail(f"Provider returned non-JSON response: {exc}")
    raise AssertionError("unreachable")
