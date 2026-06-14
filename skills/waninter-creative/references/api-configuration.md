# Waninter Creative API Configuration

Config file path:

```text
~/.config/waninter-creative/config.json
```

The API key must be stored in this config file, not in environment variables or project files.

## Standard config

```json
{
  "api_key": "YOUR_API_KEY",
  "base_url": "https://creative-studio.waninter.com",
  "auth_header": "Authorization",
  "auth_scheme": "Bearer",
  "default_image_model": "wan-image",
  "default_video_model": "wan-video",
  "image_generation_path": "/v1/images/generations",
  "image_edit_path": "/v1/images/edits",
  "video_generation_path": "/v1/videos/generations",
  "task_status_path": "/v1/tasks/{task_id}",
  "request_timeout_seconds": 120,
  "poll_interval_seconds": 5,
  "poll_timeout_seconds": 1800
}
```

## API compatibility assumptions

The scripts support common OpenAI-style and generic media API shapes:

- Request auth defaults to `Authorization: Bearer <api_key>`.
- Image generation sends JSON with `model`, `prompt`, `size`, `n`, and optional `response_format`.
- Image edit sends multipart form data with `image`, `model`, `prompt`, and optional `size`.
- Video generation sends JSON with `model`, `prompt`, `duration`, `aspect_ratio`, and optional base64 `image`.
- Async video APIs may return `task_id`, `id`, `status`, `url`, `output`, `data`, or nested result fields.

If the provider uses different field names, update config with custom paths and patch the scripts rather than storing credentials elsewhere.

## Optional config fields

```json
{
  "extra_headers": {
    "X-Provider-Version": "2026-01-01"
  },
  "image_response_format": "b64_json",
  "default_image_size": "1024x1024",
  "default_video_duration": 5,
  "default_video_aspect_ratio": "16:9"
}
```

`extra_headers` must never contain the API key unless the provider specifically requires a custom auth header and the file permissions are still `600`.
