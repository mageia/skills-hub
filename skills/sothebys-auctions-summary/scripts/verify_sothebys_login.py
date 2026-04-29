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

    text = snapshot.stdout
    login_markers = ["link \"LOG IN\"", "button \"Log in to view results\"", "Log in to view results"]
    found = [marker for marker in login_markers if marker in text]
    if found:
        raise SystemExit("Sotheby's login-enhanced precondition failed; visible login marker(s): " + ", ".join(found))

    print("Sotheby's login appears valid for login-enhanced workflow")


if __name__ == "__main__":
    main()
