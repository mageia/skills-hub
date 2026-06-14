# Troubleshooting

## Missing config

Run:

```bash
python3 scripts/configure_api_key.py
```

## Invalid API key

Re-run the configuration script and verify the key was copied from the Waninter Creative console. Do not paste the key into chat if avoidable.

## Wrong endpoint or model

Open `~/.config/waninter-creative/config.json` and check:

- `base_url`
- `image_generation_path`
- `image_edit_path`
- `video_generation_path`
- `task_status_path`
- `default_image_model`
- `default_video_model`

## Video task timeout

If a video generation times out but a task ID was returned, poll again:

```bash
python3 scripts/poll_task.py --task-id <task_id>
```

## Provider returns an unsupported response shape

Inspect the JSON response saved in `metadata.json` when available, then patch the result extraction logic in `scripts/waninter_utils.py`.
