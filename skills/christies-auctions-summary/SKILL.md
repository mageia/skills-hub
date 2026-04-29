---
name: christies-auctions-summary
description: Use when an agent needs a login-enhanced Christie's Jewellery auction summary from the results page for a date range through a configurable Chrome CDP endpoint, especially when public pages hide final results and the task must produce raw lot data, realized prices, sale totals, report.md, all-lots.csv, and source links.
---

# Christie's Auctions Summary

## Overview

Use a logged-in Chrome session exposed through CDP to collect Christie's auction, lot, and realized-result data for a date range. Version 1 starts from the **results page** main entry and is limited to the `Jewellery` category.

This skill is for the **login-enhanced** workflow only. Do not silently downgrade to public-only data, fabricate realized values, or claim success when Christie's still hides results for the active account.

## Version 1 Scope

Supported in v1:

- Christie's only
- Results page main entry: `https://www.christies.com/en/results/`
- Single category: `Jewellery`
- Logged-in CDP Chrome workflow
- Output files: `report.md`, `all-lots.csv`, `raw-data.json`

Explicitly out of scope in v1:

- `Watches`
- `Handbags`
- Multi-category runs
- Silent fallback to public pages when login-enhanced data is unavailable
- Mock or simulated success paths
- Currency conversion

## Preconditions

Before collecting data:

1. Use a Chrome session that is already logged in to Christie's.
2. Reuse the same authenticated Chrome profile through CDP.
   - Default local endpoint: `http://127.0.0.1:9222`
   - Remote example: `https://cdp.cs.waypeak.work`
3. If local CDP is unavailable, only auto-launch a local browser when the runtime has a real `user_data_dir` and `profile_directory` for the authenticated profile.
4. Verify login state with **positive logged-in markers** before collection.
5. If Christie's still hides results for the active account, fail explicitly or record the affected lots as hidden. Never invent `Sale Total` or `Realized` values.

## Dependency Bootstrap

This skill depends on `agent-browser`.

Run the bootstrap script once after installing or copying the skill:

```bash
./.codex/skills/christies-auctions-summary/scripts/bootstrap.sh
```

If `agent-browser` is missing, `run_christies_summary.py` should also attempt to bootstrap it automatically.

## Standard Workflow

1. Normalize the input config.
   - Convert documented preset ranges such as `last_week` to absolute `from` / `to` dates before collection.
   - Reject unsupported categories immediately.
2. Ensure `agent-browser` is installed.
3. Check CDP readiness with `scripts/verify_cdp_ready.sh`.
4. If local CDP is unavailable and `auto_launch=true`, launch the authenticated local browser with `scripts/launch_cdp_chrome.sh`.
5. Re-check CDP readiness. Treat a second failure as fatal.
6. Verify Christie's login with `scripts/verify_christies_login.py`.
   - Accept only when explicit logged-in markers are present.
   - Treat logged-out or ambiguous state as a fatal failure.
7. Open the Christie's **results page** main entry and discover candidate auctions with `scripts/fetch_christies_auctions.py`.
   - Filter to `Jewellery`.
   - Match by realized / closing date, not publish date or calendar display date.
8. Open each matched auction or result detail page.
   - Prefer client-side cache, preloaded JSON, or other structured page state.
   - Use page text only as a secondary source.
9. Extract both auction-level and lot-level outcomes.
   - Auction level: `Sale Total`
   - Lot level: `Realized`, estimate, sold state, reserve state, bids, and original lot URL
10. Write the canonical outputs with `scripts/analyze_christies_auctions.py`.
    - `raw-data.json`
    - `all-lots.csv`
    - `report.md`
11. Keep failures visible.
    - Fatal failures stop the run.
    - Auction- or lot-level gaps are written into `errors[]` without fabrication.

Use the orchestrator when possible:

```bash
python3 ./.codex/skills/christies-auctions-summary/scripts/run_christies_summary.py \
  --config config.json
```

## Input Contract

Read `references/input-contract.md` when building or validating configuration.

Minimal preset example:

```json
{
  "date_range": { "preset": "last_week" },
  "category": "Jewellery"
}
```

Full example:

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

## Output Contract

Read `references/output-schema.md` before consuming or extending generated data.

Successful runs always materialize these three files in the configured output directory:

- `raw-data.json`: query, auctions, lots, summary, errors.
- `all-lots.csv`: machine-friendly lot export with realized values and source links.
- `report.md`: human-readable summary including auction sale totals and a full `All lots` table at the bottom.

## Data Source Strategy

- Use the Christie's **results page** as the main discovery surface.
- Treat calendar-style pages as auxiliary only, not as the primary entry point.
- Match auctions by effective realized / closing date.
- Prefer structured page state over brittle DOM-only scraping:
  - Apollo cache
  - Redux or equivalent client state
  - `__NEXT_DATA__`
  - injected JSON blobs
  - stable logged-in API responses, if available
- Preserve original auction and lot URLs so the report can render compact `[查看]` links.

## Result Semantics

- `sale_total` is valid only when Christie's explicitly exposes an auction-level sale total.
- `final_price` is valid only when a logged-in page or structured payload exposes the realized result for that lot.
- If a lot result is hidden, set `result_visibility="hidden"`, keep `final_price=null`, render `Realized` as `N/A` in the report, and record the issue in `errors[]`.
- `bid_ask` is auxiliary and must never be copied into `final_price` unless Christie's explicitly labels it as the final realized result.
- Keep Christie's source currency. Do not auto-convert currencies.

## Failure Rules

Fatal errors: stop the whole run.

- CDP is unavailable and the authenticated local browser cannot be launched.
- `agent-browser` is unavailable and bootstrap fails.
- Christie's login is invalid, logged out, or ambiguous.
- Input dates are invalid.
- `category` is anything other than `Jewellery`.
- The Christie's results page cannot be reached or parsed.
- Candidate discovery fails completely for an otherwise valid request.

Non-fatal errors: record them in `errors[]` and continue.

- One auction detail page fails after discovery.
- One lot is missing optional metadata.
- One lot result is hidden for the current account.
- A lot is withdrawn or has incomplete pricing fields.
- A page exposes partial results but not the full final state.

No-data result: if the input is valid but no `Jewellery` auctions match the requested date range, write empty `report.md`, header-only `all-lots.csv`, and `raw-data.json`.

## Script Quick Reference

| Script | Purpose |
|---|---|
| `scripts/bootstrap.sh` | Check and install `agent-browser` if missing. |
| `scripts/run_christies_summary.py` | Orchestrate bootstrap, config validation, CDP checks, collection, and reporting. |
| `scripts/launch_cdp_chrome.sh` | Launch local Chrome with CDP and the configured authenticated profile. |
| `scripts/verify_cdp_ready.sh` | Check CDP `/json/version`. |
| `scripts/verify_christies_login.py` | Verify login state through CDP/browser automation with positive markers. |
| `scripts/fetch_christies_auctions.py` | Collect raw Christie's auction and lot data from the results page plus logged-in detail pages. |
| `scripts/analyze_christies_auctions.py` | Build summary metrics, `report.md`, and `all-lots.csv` from raw JSON. |
| `scripts/validate_skill.py` | Validate this skill's relative structure and frontmatter. |

## References

- `references/input-contract.md`: supported config shape and validation rules.
- `references/output-schema.md`: canonical output files, fields, tables, and error shape.
- `references/christies-field-notes.md`: Christie's-specific entry points, field semantics, login rules, and extraction preferences.

## Validation

After editing this skill, run:

```bash
python3 ./.codex/skills/christies-auctions-summary/scripts/validate_skill.py
python3 -m py_compile ./.codex/skills/christies-auctions-summary/scripts/*.py
bash -n ./.codex/skills/christies-auctions-summary/scripts/*.sh
python3 ./.codex/skills/christies-auctions-summary/tests/test_runtime_helpers.py
python3 ./.codex/skills/christies-auctions-summary/tests/test_login.py
python3 ./.codex/skills/christies-auctions-summary/tests/test_data_pipeline.py
```
