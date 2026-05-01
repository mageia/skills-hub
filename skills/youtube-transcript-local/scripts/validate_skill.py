#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

REQUIRED_FILES = [
    'SKILL.md',
    'agents/openai.yaml',
    'references/workflow.md',
    'references/dependencies.md',
    'references/output-format.md',
    'scripts/bootstrap.sh',
    'scripts/check_env.py',
    'scripts/run_youtube_transcript.py',
    'tests/test_skill_structure.py',
    'tests/test_runtime_helpers.py',
    'tests/test_check_env.py',
]


def main() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    skill_md = skill_dir / 'SKILL.md'
    if not skill_md.exists():
        raise SystemExit('SKILL.md not found')
    text = skill_md.read_text(encoding='utf-8')
    match = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
    if not match:
        raise SystemExit('Invalid or missing YAML frontmatter')
    front = match.group(1)
    if not re.search(r'^name:\s+[a-z0-9-]+\s*$', front, re.MULTILINE):
        raise SystemExit('Missing or invalid name in frontmatter')
    if not re.search(r'^description:\s+Use when .+$', front, re.MULTILINE):
        raise SystemExit('Description must start with "Use when"')
    for rel in REQUIRED_FILES:
        if not (skill_dir / rel).exists():
            raise SystemExit(f'Missing required file: {rel}')
    print('Skill is valid!')


if __name__ == '__main__':
    main()
