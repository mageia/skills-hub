# Input Contract

The skill accepts a JSON configuration object.

## Required fields

```json
{
  "date_range": { "preset": "last_week" },
  "category": "Jewelry"
}
```

`date_range` must be one of:

```json
{ "preset": "last_week" }
```

```json
{ "from": "2026-04-20", "to": "2026-04-26" }
```

Supported presets:

- `last_week`: previous Monday through previous Sunday.
- `last_month`: first through last day of the previous calendar month.

`category` is a single Sotheby's category display name. First-version supported values:

- `Jewelry`
- `Watches`
- `Contemporary Art`

## Optional fields and defaults

```json
{
  "cdp": {
    "url": "http://127.0.0.1:9222",
    "host": "127.0.0.1",
    "port": 9222,
    "user_data_dir": "~/.chrome-debug-profile",
    "profile_directory": "Default",
    "auto_launch": true,
    "chrome_command": ""
  },
  "output": {
    "dir": "./outputs/sothebys-auctions-summary",
    "format": ["markdown", "json"]
  }
}
```

Rules:

- `cdp.url` is preferred when provided.
- Default local CDP endpoint is `http://127.0.0.1:9222`.
- `auto_launch=true` only applies to local CDP.
- `chrome_command` is optional for local launchers that need an explicit command.
- Paths may use `~` and environment variables. Expand them before validation.

## Invalid input

Fail immediately for invalid dates, unknown categories, missing local profile directories when local auto-launch is requested, or unsupported output formats. Do not silently rewrite user intent.
