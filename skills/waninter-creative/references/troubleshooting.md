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


## Unauthorized / HTTP 401

This means Waninter Creative rejected the configured API Key for protected endpoints.

Fix:

1. Open the Waninter Creative `/api` page.
2. Create or copy a valid API Key. It usually starts with `sk_live_`.
3. Re-run:

```bash
python3 scripts/configure_api_key.py
```

The configuration script validates the key after saving.

You can also validate later with:

```bash
python3 scripts/validate_api_key.py
```
