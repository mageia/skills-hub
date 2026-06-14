#!/usr/bin/env python3
"""Shared helpers for Waninter Creative scripts."""
from __future__ import annotations

import base64
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

CONFIG_DIR = Path.home() / ".config" / "waninter-creative"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULTS = {
    "base_url": "https://creative-studio.waninter.com",
    "auth_header": "Authorization",
    "auth_scheme": "Bearer",
    "models_path": "/v1/models",
    "generation_tasks_path": "/v1/generation-tasks",
    "generation_task_path": "/v1/generation-tasks/{task_id}",
    "default_image_model": "nano-banana-3-1",
    "fallback_image_model": "gpt-image-2",
    "default_video_model": "sd2-720p",
    "fallback_video_model": "doubao-seedance-2-0-fast-260128",
    "request_timeout_seconds": 120,
    "poll_interval_seconds": 5,
    "poll_timeout_seconds": 1800,
}


def fail(message: str, **extra: Any) -> None:
    payload = {"status": "failed", "error": message}
    payload.update(extra)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(1)


def load_config() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        fail(f"Missing config file: {CONFIG_FILE}. Run: python3 scripts/configure_api_key.py")
    try:
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON config: {exc}")
    cfg = {**DEFAULTS, **raw}
    if not cfg.get("api_key"):
        fail("Missing api_key in config. Run: python3 scripts/configure_api_key.py")
    return cfg


def build_url(cfg: Dict[str, Any], path: str) -> str:
    base = str(cfg.get("base_url", "")).rstrip("/")
    if path.startswith(("http://", "https://")):
        return path
    return base + "/" + path.lstrip("/")


def headers(cfg: Dict[str, Any], content_type: Optional[str] = "application/json") -> Dict[str, str]:
    h: Dict[str, str] = {"Accept": "application/json"}
    if content_type:
        h["Content-Type"] = content_type
    auth_header = cfg.get("auth_header") or "Authorization"
    auth_scheme = cfg.get("auth_scheme")
    api_key = cfg["api_key"]
    h[auth_header] = f"{auth_scheme} {api_key}" if auth_scheme else api_key
    h.update(cfg.get("extra_headers") or {})
    return h


def request_json(cfg: Dict[str, Any], method: str, path: str, payload: Optional[Dict[str, Any]] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(build_url(cfg, path), data=body, method=method.upper(), headers=headers(cfg))
    try:
        with urllib.request.urlopen(req, timeout=timeout or int(cfg["request_timeout_seconds"])) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        fail(f"HTTP {exc.code} from Waninter Creative", response=text[:2000])
    except urllib.error.URLError as exc:
        fail(f"Network error: {exc}")
    except json.JSONDecodeError as exc:
        fail(f"Waninter Creative returned non-JSON response: {exc}")
    raise AssertionError("unreachable")


def api_data(envelope: Any) -> Any:
    if isinstance(envelope, dict) and "data" in envelope:
        return envelope["data"]
    return envelope


def create_output_dir(root: str | Path, prefix: str = "") -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(root) / "waninter-creative" / f"{prefix}{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def download_file(url: str, output_path: Path, timeout: int = 300) -> Path:
    req = urllib.request.Request(url, headers={"User-Agent": "waninter-creative-skill/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        output_path.write_bytes(resp.read())
    return output_path


def file_to_data_url(path: str | Path) -> str:
    path_obj = Path(path)
    suffix = path_obj.suffix.lower()
    mime = "image/png"
    if suffix in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    elif suffix == ".webp":
        mime = "image/webp"
    data = base64.b64encode(path_obj.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def guess_extension_from_url(url: str, default: str) -> str:
    ext = Path(urllib.parse.urlparse(url).path).suffix
    return ext if ext else default


def get_models(cfg: Dict[str, Any]) -> list[dict[str, Any]]:
    data = api_data(request_json(cfg, "GET", cfg["models_path"], None))
    if isinstance(data, list):
        return [m for m in data if isinstance(m, dict)]
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return [m for m in data["items"] if isinstance(m, dict)]
    return []


def pick_model(cfg: Dict[str, Any], media_type: str, requested: Optional[str] = None) -> str:
    if requested:
        return requested
    preferred = cfg.get(f"default_{media_type}_model")
    fallback = cfg.get(f"fallback_{media_type}_model")
    try:
        models = get_models(cfg)
        typed = [m for m in models if m.get("type") == media_type or m.get("model_type") == media_type]
        ids = {str(m.get("id")) for m in typed if m.get("id")}
        if preferred in ids:
            return str(preferred)
        if fallback in ids:
            return str(fallback)
        if typed and typed[0].get("id"):
            return str(typed[0]["id"])
    except SystemExit:
        raise
    except Exception:
        pass
    return str(preferred or fallback)


def defaults_from_model(cfg: Dict[str, Any], model_id: str) -> Dict[str, Any]:
    try:
        for model in get_models(cfg):
            if model.get("id") != model_id:
                continue
            params: Dict[str, Any] = {}
            for spec in model.get("params_schema") or []:
                if isinstance(spec, dict) and "key" in spec and "default" in spec:
                    params[str(spec["key"])] = spec["default"]
            return params
    except Exception:
        return {}
    return {}


def extract_task(data: Any) -> Dict[str, Any]:
    d = api_data(data)
    if isinstance(d, dict):
        return d
    return {}


def extract_result_urls(task: Dict[str, Any]) -> list[str]:
    urls = task.get("result_urls") or task.get("resultUrls") or task.get("urls") or []
    if isinstance(urls, str):
        return [urls]
    if isinstance(urls, list):
        return [u for u in urls if isinstance(u, str)]
    return []
