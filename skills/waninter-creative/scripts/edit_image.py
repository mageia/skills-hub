#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Edit or transform an image with Waninter Creative")
    parser.add_argument("--input", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--model")
    parser.add_argument("--size")
    parser.add_argument("--aspect-ratio")
    parser.add_argument("--quality")
    parser.add_argument("--output", default="./outputs")
    args = parser.parse_args()
    script = Path(__file__).with_name("generate_image.py")
    cmd = [sys.executable, str(script), "--input", args.input, "--prompt", args.prompt, "--output", args.output]
    for flag in ("model", "size", "aspect_ratio", "quality"):
        val = getattr(args, flag)
        if val:
            cmd += ["--" + flag.replace("_", "-"), val]
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
