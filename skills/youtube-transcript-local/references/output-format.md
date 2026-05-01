# Output Format

Every successful run creates `outputs/<video_id>/` with these files.

## `transcript.txt`
Plain text transcript suitable for summarization, retrieval, and agent input.

## `transcript.srt`
Subtitle timeline in SRT format.

## `metadata.json`
Minimum fields:

```json
{
  "video_url": "https://www.youtube.com/watch?v=...",
  "video_id": "...",
  "source_method": "subtitle | asr",
  "subtitle_type": "manual | auto | null",
  "language": "en",
  "model": "small",
  "device": "cpu | cuda | null",
  "status": "success"
}
```

## `process.log`
Append-only execution log with timestamps and external command traces.
