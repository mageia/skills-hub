# Output Formats

## Images

Common sizes:

- `1024x1024` for square images
- `1536x1024` for landscape images
- `1024x1536` for portrait images

Aspect ratio mapping:

- `1:1` -> `1024x1024`
- `16:9` -> `1536x864`
- `9:16` -> `864x1536`
- `3:4` -> `1024x1365`
- `4:3` -> `1365x1024`

Preferred output format: PNG unless the provider returns a different format.

## Videos

Common settings:

- Duration: `5` or `10` seconds
- Aspect ratio: `16:9`, `9:16`, `1:1`
- Format: MP4

For social media vertical video, prefer `9:16` and 5-10 seconds.
For website hero loops, prefer `16:9`, 5 seconds, and smooth camera motion.
