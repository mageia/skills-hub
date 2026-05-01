# Workflow

## Standard entrypoint

```bash
python3 ./.codex/skills/youtube-transcript-local/scripts/run_youtube_transcript.py \
  "https://www.youtube.com/watch?v=VIDEO_ID"
```

## Decision order

1. Validate the YouTube URL and derive `video_id`.
2. Query video metadata through `yt-dlp --dump-single-json`.
3. Inspect `subtitles` first, then `automatic_captions`.
4. If any subtitle language is available:
   - download that subtitle track with `yt-dlp`
   - convert to `transcript.srt` when needed
   - derive `transcript.txt` from the SRT text
5. If no subtitles are available:
   - download WAV audio with `yt-dlp`
   - normalize to mono 16k WAV with `ffmpeg`
   - run `faster-whisper`
6. Write `metadata.json` and append `process.log`.

## Output directory

```text
outputs/
  <video_id>/
    transcript.txt
    transcript.srt
    metadata.json
    process.log
```
