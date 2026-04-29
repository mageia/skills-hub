---
name: sothebys-auctions-summary
description: Use when an agent needs a login-enhanced Sotheby's auction summary for a date range and category through a configurable Chrome CDP endpoint, especially when public pages hide final results and the task must produce raw lot data, realized prices, and a report with source links.
---

# Sotheby's Auctions Summary

## Overview

Use a logged-in Chrome session exposed through CDP to collect Sotheby's auction, lot, and realized-result data for a date range and category. Produce both raw JSON and a Markdown report with auction links and a full all-lots table.

This skill is for the **login-enhanced** workflow only. Do not silently downgrade to public-only data.

## Preconditions

Before collecting data:

1. Use a Chrome session that is already logged in to Sotheby's.
2. Connect to a configurable CDP endpoint.
   - Default: `http://127.0.0.1:9222`
   - Remote example: `https://cdp.cs.waypeak.work`
3. Verify login state before data collection.
4. Preserve failures. Do not mock success, fabricate final prices, or treat `bid_ask` as `final_price`.

## Dependency bootstrap

This skill depends on `agent-browser`.

Run the bootstrap script once after installing or copying the skill:

```bash
./.codex/skills/sothebys-auctions-summary/scripts/bootstrap.sh
```

If `agent-browser` is missing, `run_sothebys_summary.py` will also attempt to bootstrap it automatically.

## Standard Workflow

1. Normalize input.
   - Convert presets such as `last_week` to absolute dates.
   - Normalize category names using the supported category map.
2. Ensure `agent-browser` is installed.
3. Check CDP readiness with `scripts/verify_cdp_ready.sh`.
4. If CDP is unavailable and `auto_launch=true`, launch local Chrome with `scripts/launch_cdp_chrome.sh`.
5. Re-check CDP readiness. Fail if still unavailable.
6. Verify Sotheby's login with `scripts/verify_sothebys_login.py`.
7. Collect auctions and lots with `scripts/fetch_sothebys_auctions.py`.
8. Analyze collected JSON with `scripts/analyze_sothebys_auctions.py`.
9. Return paths to `raw-data.json` and `report.md`, plus a brief summary.

Use the orchestrator when possible:

```bash
python3 ./.codex/skills/sothebys-auctions-summary/scripts/run_sothebys_summary.py \
  --config config.json
```

## Input Contract

Read `references/input-contract.md` when building or validating configuration.

Minimal example:

```json
{
  "date_range": { "preset": "last_week" },
  "category": "Jewelry",
  "cdp": {
    "url": "http://127.0.0.1:9222",
    "auto_launch": true
  },
  "output": {
    "dir": "./outputs/sothebys-auctions-summary",
    "format": ["markdown", "json"]
  }
}
```

Remote example:

```json
{
  "date_range": { "from": "2026-04-20", "to": "2026-04-29" },
  "category": "Jewelry",
  "cdp": {
    "url": "https://cdp.cs.waypeak.work",
    "auto_launch": false
  },
  "output": {
    "dir": "./outputs/sothebys-auctions-summary",
    "format": ["markdown", "json"]
  }
}
```

## Output Contract

Read `references/output-schema.md` before consuming or extending generated data.

The workflow writes:

- `raw-data.json`: query, auctions, lots, summary, errors.
- `report.md`: human-readable auction summary with auction links and a full `All lots` table at the end.

## Data Source Strategy

- Use the results page to identify candidate auctions for the category/date range.
- Use the logged-in auction page Apollo cache to extract all `LotCard` and `BidState` data.
- Prefer Apollo-derived realized prices (`ResultVisible -> premiums.finalPriceV2`) over brittle DOM scraping.
- Include original lot links in the final report.

## Result Semantics

- `final_price` is only valid when a real final result is visible to the logged-in account.
- Hidden result: set `result_visibility="hidden"`, keep `final_price=null`, and record an error/warning.
- `bid_ask` is auxiliary and must never be copied into `final_price` unless the page/API explicitly identifies it as the final realized result.
- Do not auto-convert currencies. Keep Sotheby's source currency.

## Failure Rules

Fatal errors: stop the whole run.

- CDP unavailable and cannot be launched.
- `agent-browser` is unavailable and bootstrap fails.
- Sotheby's login is not valid.
- Category or date input is invalid.
- Key Sotheby's pages cannot be reached.
- Auction Apollo cache returns zero lots for a matched auction.

Non-fatal errors: record in `errors[]` and continue.

- A single auction page fails.
- A single lot has missing optional fields.
- A single lot result is hidden for the current account.
- A lot is withdrawn or hidden.
- A price field is incomplete.

No-data result: if input is valid but no auctions match, write empty JSON/report and do not fail.

## Script Quick Reference

| Script | Purpose |
|---|---|
| `scripts/bootstrap.sh` | Check and install `agent-browser` if missing. |
| `scripts/run_sothebys_summary.py` | Orchestrate bootstrap, config validation, CDP checks, collection, and reporting. |
| `scripts/launch_cdp_chrome.sh` | Launch local Chrome with CDP and configured profile. |
| `scripts/verify_cdp_ready.sh` | Check CDP `/json/version`. |
| `scripts/verify_sothebys_login.py` | Verify login state through CDP/browser automation. |
| `scripts/fetch_sothebys_auctions.py` | Collect raw Sotheby's auction and lot data from results page + Apollo cache. |
| `scripts/analyze_sothebys_auctions.py` | Build summary metrics and Markdown report from raw JSON. |
| `scripts/validate_skill.py` | Validate this skill's relative structure and frontmatter. |

## Validation

After editing this skill, run:

```bash
python3 ./.codex/skills/sothebys-auctions-summary/scripts/validate_skill.py
python3 -m py_compile ./.codex/skills/sothebys-auctions-summary/scripts/*.py
bash -n ./.codex/skills/sothebys-auctions-summary/scripts/*.sh
python3 ./.codex/skills/sothebys-auctions-summary/tests/test_skill_runtime.py
```
