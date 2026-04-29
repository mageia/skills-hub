# Input Contract

The skill accepts a JSON configuration object.

## Canonical v1 example

```json
{
  "date_range": {
    "from": "2026-04-20",
    "to": "2026-04-29"
  },
  "category": "Jewellery",
  "cdp": {
    "url": "http://127.0.0.1:9222",
    "auto_launch": true,
    "user_data_dir": "~/.chrome-debug-profile",
    "profile_directory": "Default",
    "chrome_command": ""
  },
  "output": {
    "dir": "./outputs/christies-auctions-summary",
    "format": ["markdown", "json", "csv"]
  }
}
```

## Required fields

```json
{
  "date_range": { "from": "2026-04-20", "to": "2026-04-29" },
  "category": "Jewellery"
}
```

### `date_range`

Supported input shapes in v1:

Explicit absolute range:

```json
{ "from": "2026-04-20", "to": "2026-04-29" }
```

Preset range:

```json
{ "preset": "last_week" }
```

Rules:

- Convert presets to absolute `from` / `to` dates before collection starts.
- Use ISO `YYYY-MM-DD` dates.
- `from` must be earlier than or equal to `to`.
- Date matching is against realized / closing date, not publish date.

### `category`

Version 1 supports exactly one category value:

- `Jewellery`

Invalid examples that must fail immediately:

- `Jewelry`
- `Watches`
- `Handbags`
- any mixed, pluralized, localized, or inferred alternative

The runtime must not silently remap or downgrade category intent.

## Optional fields and defaults

```json
{
  "cdp": {
    "url": "http://127.0.0.1:9222",
    "auto_launch": true,
    "user_data_dir": "~/.chrome-debug-profile",
    "profile_directory": "Default",
    "chrome_command": ""
  },
  "output": {
    "dir": "./outputs/christies-auctions-summary",
    "format": ["markdown", "json", "csv"]
  }
}
```

### `cdp`

Rules:

- `cdp.url` is the preferred endpoint selector.
- Default local endpoint is `http://127.0.0.1:9222`.
- Remote CDP sessions are allowed when `url` points to a reachable remote CDP base URL or websocket target.
- `auto_launch=true` only applies to local CDP workflows.
- Local auto-launch requires a real authenticated `user_data_dir` and `profile_directory` so the browser session keeps the Christie's login.
- `chrome_command` is optional and only relevant when the local environment needs an explicit browser executable.
- Paths may use `~` or environment variables, but they must be expanded before validation.

### `output`

Rules:

- `output.dir` is the directory where all generated files are written.
- `output.format` documents the canonical renderings for v1 and should contain exactly:
  - `markdown`
  - `json`
  - `csv`
- A successful run writes all three canonical files:
  - `report.md`
  - `all-lots.csv`
  - `raw-data.json`

## Invalid input

Fail immediately for:

- invalid or reversed dates
- unsupported categories
- missing authenticated local profile details when local auto-launch is requested
- unreachable or malformed CDP endpoints
- unsupported output format values

Do not silently rewrite user intent, do not invent defaults that break the authenticated workflow, and do not continue once the request has fallen outside the documented v1 contract.
