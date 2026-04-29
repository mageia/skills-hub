#!/usr/bin/env python3
"""Verify Sotheby's login state through an existing CDP Chrome session using agent-browser."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from urllib.parse import urlparse
from urllib.request import urlopen

LOGGED_IN_MARKERS = [
    'LOG OUT',
    'MY ACCOUNT',
    'link "LOG OUT"',
    'button "MY ACCOUNT"',
]

LOGGED_OUT_MARKERS = [
    'LOG IN',
    'PREFERRED ACCESS',
    'Log in to view results',
    'link "LOG IN"',
    'button "Log in to view results"',
]


def resolve_cdp_target(cdp: str) -> str:
    parsed = urlparse(cdp)
    if parsed.scheme in {"http", "https"}:
        base = cdp.rstrip("/")
        try:
            with urlopen(base + "/json/list", timeout=8) as response:
                items = json.load(response)
            for item in items:
                if item.get("type") == "page" and item.get("webSocketDebuggerUrl"):
                    return item["webSocketDebuggerUrl"]
        except Exception:
            pass
        with urlopen(base + "/json/version", timeout=8) as response:
            data = json.load(response)
        ws = data.get("webSocketDebuggerUrl")
        if not ws:
            raise SystemExit(f"CDP endpoint did not return webSocketDebuggerUrl: {cdp}")
        return ws
    return cdp


def connect_agent_browser(cdp: str) -> None:
    completed = subprocess.run(
        ["agent-browser", "connect", resolve_cdp_target(cdp)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode != 0:
        sys.stderr.write(completed.stdout)
        raise SystemExit(completed.returncode)


def run_agent_browser(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["agent-browser", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def classify_login_state(snapshot_text: str, body_text: str) -> tuple[bool, str]:
    combined = f"{snapshot_text}\n{body_text}"
    found_in = [marker for marker in LOGGED_IN_MARKERS if marker in combined]
    found_out = [marker for marker in LOGGED_OUT_MARKERS if marker in combined]

    if found_in:
        return True, f"logged-in marker(s): {', '.join(found_in)}"
    if found_out:
        return False, f"logged-out marker(s): {', '.join(found_out)}"
    return False, 'login state ambiguous: no explicit logged-in marker found'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cdp-port", type=int, default=9222)
    parser.add_argument("--cdp-url", help="Full remote CDP base URL, e.g. https://cdp.example.com")
    parser.add_argument("--url", default="https://www.sothebys.com/en/results?locale=en")
    args = parser.parse_args()

    if shutil.which("agent-browser") is None:
        raise SystemExit("agent-browser is required for browser-state login verification")

    connect_agent_browser(args.cdp_url or str(args.cdp_port))

    opened = run_agent_browser(["open", args.url])
    if opened.returncode != 0:
        sys.stderr.write(opened.stdout)
        raise SystemExit(opened.returncode)

    snapshot = run_agent_browser(["snapshot", "-i", "-d", "4"])
    if snapshot.returncode != 0:
        sys.stderr.write(snapshot.stdout)
        raise SystemExit(snapshot.returncode)

    body = run_agent_browser(["eval", "document.body.innerText"])
    if body.returncode != 0:
        sys.stderr.write(body.stdout)
        raise SystemExit(body.returncode)

    try:
        body_text = json.loads(body.stdout)
        if not isinstance(body_text, str):
            body_text = str(body_text)
    except Exception:
        body_text = body.stdout

    is_logged_in, reason = classify_login_state(snapshot.stdout, body_text)
    if not is_logged_in:
        raise SystemExit(f"Sotheby's login-enhanced precondition failed; {reason}")

    print(f"Sotheby's login appears valid for login-enhanced workflow ({reason})")


if __name__ == "__main__":
    main()
