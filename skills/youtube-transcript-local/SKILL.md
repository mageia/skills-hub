---
name: youtube-transcript-local
description: Use when an agent needs a low-cost local transcript workflow for a YouTube URL that should extract existing subtitles first and only fall back to local ASR when no subtitles are available, writing transcript.txt, transcript.srt, metadata.json, and process.log.
---

# YouTube Transcript Local

## Overview

Use this skill to turn a single YouTube URL into local transcript artifacts with a stable output contract.

The workflow is strict:
1. Check dependencies with bootstrap.
2. Probe existing subtitles through `yt-dlp`.
3. If any manual or auto subtitles exist, extract them directly.
4. If no subtitles exist, download audio and run local `faster-whisper` ASR.
5. Always write `transcript.txt`, `transcript.srt`, `metadata.json`, and `process.log` under `outputs/<video_id>/`.

Do not silently swap to cloud APIs. Do not claim success without the required output files.

## Dependency Bootstrap

Run once before the first use:

```bash
./.codex/skills/youtube-transcript-local/scripts/bootstrap.sh
```

Bootstrap checks:
- `python3`
- `yt-dlp`
- `ffmpeg`
- Python package `faster-whisper`

## Standard Workflow

```bash
python3 ./.codex/skills/youtube-transcript-local/scripts/run_youtube_transcript.py \
  "https://www.youtube.com/watch?v=VIDEO_ID"
```

Optional flags:

```bash
python3 ./.codex/skills/youtube-transcript-local/scripts/run_youtube_transcript.py \
  "https://www.youtube.com/watch?v=VIDEO_ID" \
  --output-root ./.codex/skills/youtube-transcript-local/outputs \
  --force
```

## Output Contract

Successful runs always materialize:
- `transcript.txt`
- `transcript.srt`
- `metadata.json`
- `process.log`

Read these references when you need details:
- `references/workflow.md`
- `references/dependencies.md`
- `references/output-format.md`

## Failure Rules

- Invalid YouTube URL: fail explicitly.
- Subtitle probe failure: if probing succeeds but no subtitles exist, continue to ASR.
- Audio download, ffmpeg conversion, or ASR failure: fail explicitly and keep `process.log`.
- Existing output directory without `--force`: fail explicitly.

## Validation

After editing this skill, run:

```bash
python3 ./.codex/skills/youtube-transcript-local/scripts/validate_skill.py
python3 -m unittest discover ./.codex/skills/youtube-transcript-local/tests -v
python3 -m py_compile ./.codex/skills/youtube-transcript-local/scripts/*.py
bash -n ./.codex/skills/youtube-transcript-local/scripts/bootstrap.sh
```
