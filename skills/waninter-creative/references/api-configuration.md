# Waninter Creative API Configuration

Config file path:

```text
~/.config/waninter-creative/config.json
```

Beginner users only need to provide an API Key. The setup script preconfigures the real Waninter Creative API endpoints and default models.

## Default config

```json
{
  "api_key": "YOUR_API_KEY",
  "base_url": "https://creative-studio.waninter.com",
  "models_path": "/v1/models",
  "generation_tasks_path": "/v1/generation-tasks",
  "generation_task_path": "/v1/generation-tasks/{task_id}",
  "default_image_model": "nano-banana-3-1",
  "fallback_image_model": "gpt-image-2",
  "default_video_model": "sd2-720p",
  "fallback_video_model": "doubao-seedance-2-0-fast-260128"
}
```

## Model discovery

Use:

```bash
python3 scripts/list_models.py
python3 scripts/list_models.py --type image
python3 scripts/list_models.py --type video
```

Generation scripts automatically call `/v1/models` and choose the first available model of the requested type if the configured default is unavailable.

## Real platform endpoints

- `GET /v1/models` lists available image and video models.
- `POST /v1/generation-tasks` creates image/video tasks.
- `GET /v1/generation-tasks/{task_id}` polls task status and result URLs.

Do not ask beginner users to edit these paths.
