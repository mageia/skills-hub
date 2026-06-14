---
name: waninter-creative
description: Configure a Waninter Creative API key and generate or edit AI media through the real Waninter Creative API. Use when the user asks Codex or another agent to set up a Waninter Creative API key, list available models, generate images, edit images, create text-to-video or image-to-video outputs, poll media generation jobs, or produce creative visual assets from prompts.
---

# Waninter Creative

Use this skill to generate images and videos through Waninter Creative. The user only needs an API Key; endpoints and default models are preconfigured, and scripts can discover available models with `/v1/models`.

## Configuration first

Before generation, check:

```text
~/.config/waninter-creative/config.json
```

If missing, ask the user to get an API Key from Waninter Creative, then run:

```bash
python3 scripts/configure_api_key.py
```

The setup script asks only for the API Key, then validates it against a protected endpoint. Do not ask beginner users to choose endpoints, model IDs, or task paths. If validation returns 401/UNAUTHORIZED, tell the user to create or copy a valid API Key from the Waninter Creative /api page, usually starting with sk_live_.

## Task routing

- Validate configured API Key: `scripts/validate_api_key.py`
- List available models: `scripts/list_models.py` or `scripts/list_models.py --type image|video`
- Text-to-image: `scripts/generate_image.py --prompt "..."`
- Image-to-image or image editing: `scripts/edit_image.py --input image.png --prompt "..."`
- Text-to-video: `scripts/generate_video.py --prompt "..."`
- Image-to-video: `scripts/generate_video.py --image image.png --prompt "..."`
- Existing task status: `scripts/poll_task.py --task-id <id>`

Scripts save outputs under:

```text
./outputs/waninter-creative/YYYYMMDD-HHMMSS/
```

Each script prints JSON. Return the generated file paths or URLs, task ID, model, prompt, parameters, and warnings.

## Defaults

- API base URL: `https://creative-studio.waninter.com`
- Models endpoint: `GET /v1/models`
- Create task endpoint: `POST /v1/generation-tasks`
- Poll task endpoint: `GET /v1/generation-tasks/{task_id}`
- Preferred image model: `nano-banana-3-1`, fallback `gpt-image-2`
- Preferred video model: `sd2-720p`, fallback `doubao-seedance-2-0-fast-260128`

If a preferred model is unavailable, the scripts auto-select an available model of the requested media type.

## Prompt handling

Improve vague prompts before calling the API. Preserve intent but add production details such as subject, style, composition, lighting, camera motion, aspect ratio, duration, and format.

Read `references/prompt-guidelines.md` when the user asks for higher quality, a specific style, or video motion/camera direction.

## Output parameters

Common arguments:

- Image: `--aspect-ratio 16:9`, `--size 1024x1024`, `--quality medium`
- Video: `--duration 5`, `--aspect-ratio 16:9`, `--resolution 720p`
- Model override for advanced users: `--model <model-id>`

Read `references/output-formats.md` for parameter mapping.

## Error handling

If a script fails:

1. Do not expose the API Key.
2. Report the human-readable error.
3. If a task ID exists, provide it so the user can resume polling.
4. Read `references/troubleshooting.md` for common fixes.

## Examples

```bash
python3 scripts/list_models.py --type image
```

```bash
python3 scripts/generate_image.py --prompt "A cinematic sci-fi city poster at sunset" --aspect-ratio 16:9
```

```bash
python3 scripts/edit_image.py --input ./source.png --prompt "Remove the background and keep a clean transparent product cutout"
```

```bash
python3 scripts/generate_video.py --prompt "A golden retriever running through a sunflower field, cinematic slow motion" --duration 5 --aspect-ratio 16:9
```

```bash
python3 scripts/generate_video.py --image ./input.png --prompt "Animate this image with a slow cinematic push-in" --duration 5
```
