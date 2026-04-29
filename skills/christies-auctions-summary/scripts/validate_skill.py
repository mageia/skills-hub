#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


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
    if not re.search(r'^description:\s+.+$', front, re.MULTILINE):
        raise SystemExit('Missing description in frontmatter')
    for rel in [
        'agents/openai.yaml',
        'references/input-contract.md',
        'references/output-schema.md',
        'references/christies-field-notes.md',
    ]:
        if not (skill_dir / rel).exists():
            raise SystemExit(f'Missing required file: {rel}')
    print('Skill is valid!')


if __name__ == '__main__':
    main()
