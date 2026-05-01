#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil

which = shutil.which


def detect_runtime() -> dict[str, object]:
    gpu_detected = which('nvidia-smi') is not None
    if gpu_detected:
        return {
            'device': 'cuda',
            'compute_type': 'float16',
            'gpu_detected': True,
        }
    return {
        'device': 'cpu',
        'compute_type': 'int8',
        'gpu_detected': False,
    }


def main() -> None:
    print(json.dumps(detect_runtime(), ensure_ascii=False))


if __name__ == '__main__':
    main()
