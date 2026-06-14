---
name: waninter-creative
description: Configure a Waninter Creative API key and generate or edit AI media through API calls. Use when the user asks Codex or another agent to set up a Waninter Creative API key, generate images, edit images, create text-to-video or image-to-video outputs, poll media generation jobs, or produce creative visual assets from prompts.
---

# Waninter Creative

Use this skill to generate images and videos through a configured Waninter Creative-compatible API. The skill stores API credentials only in a local config file and provides scripts for image generation, image editing, video generation, and async task polling.

## Configuration first

Before any generation, check the config file:

```text
~/.config/waninter-creative/config.json
```

If it is missing or incomplete, guide the user to obtain an API key from the Waninter Creative service console, then run:

```bash
python3 scripts/configure_api_key.py
```

Never ask the user to place the API key in a project file. Never print, echo, or include the API key in metadata.

For detailed config fields, read `references/api-configuration.md`.

## Task routing

Choose the script by task:

- Text-to-image: `scripts/generate_image.py --prompt "..."`
- Image-to-image or image editing: `scripts/edit_image.py --input image.png --prompt "..."`
- Text-to-video: `scripts/generate_video.py --prompt "..."`
- Image-to-video: `scripts/generate_video.py --image image.png --prompt "..."`
- Existing async task status: `scripts/poll_task.py --task-id <id>`

Save or expect outputs under:

```text
./outputs/waninter-creative/YYYYMMDD-HHMMSS/
```

Each script prints JSON so the agent can parse the result. Return the generated file path or URL, task ID when available, model, prompt, parameters, and warnings.

## Prompt handling

Improve vague user prompts before calling the API. Preserve user intent but add useful production details such as subject, style, composition, lighting, camera motion, aspect ratio, duration, and format.

Read `references/prompt-guidelines.md` when the user asks for higher quality, a specific style, or a video with motion/camera direction.

## Output parameters

Map user requests to common arguments:

- Image size: `--size 1024x1024`, `--size 1536x1024`, or `--aspect-ratio 16:9`
- Video duration: `--duration 5` or `--duration 10`
- Video aspect ratio: `--aspect-ratio 16:9`, `9:16`, or `1:1`
- Output directory: `--output ./outputs`
- Model override: `--model <model-name>`

Read `references/output-formats.md` for parameter mapping.

## Error handling

If a script fails:

1. Do not expose the API key.
2. Report the human-readable error.
3. If a task ID exists, provide it so the user can resume polling.
4. Read `references/troubleshooting.md` for common fixes.

## Script examples

```bash
python3 scripts/generate_image.py \
  --prompt "A cinematic sci-fi city poster at sunset, ultra detailed" \
  --aspect-ratio 16:9
```

```bash
python3 scripts/edit_image.py \
  --input ./source.png \
  --prompt "Remove the background and keep a clean transparent product cutout"
```

```bash
python3 scripts/generate_video.py \
  --prompt "A golden retriever running through a sunflower field, cinematic slow motion" \
  --duration 5 \
  --aspect-ratio 16:9
```

```bash
python3 scripts/generate_video.py \
  --image ./input.png \
  --prompt "Animate this image with a slow cinematic push-in" \
  --duration 5
```
