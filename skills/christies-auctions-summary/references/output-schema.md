# Output Schema

The workflow writes three canonical files into the configured output directory:

- `report.md`
- `all-lots.csv`
- `raw-data.json`

## raw-data.json

```json
{
  "query": {
    "date_from": "2026-04-20",
    "date_to": "2026-04-29",
    "category": "Jewellery"
  },
  "auctions": [],
  "lots": [],
  "summary": {},
  "errors": []
}
```

## Auction object

Each auction entry should include at least:

```json
{
  "auction_id": "string",
  "title": "string",
  "url": "string",
  "category": "Jewellery",
  "location": "Hong Kong",
  "sales_type": "Live",
  "date_text": "29 April 2026 | Hong Kong",
  "start_at": "2026-04-29",
  "end_at": "2026-04-29",
  "matched_by_date_range": true,
  "sale_total": 1234567,
  "sale_total_currency": "HKD"
}
```

Notes:

- `sale_total` is an auction-level realized total, not an estimate.
- Keep the source URL so `report.md` can render a compact `[查看]` link.
- `matched_by_date_range` reflects the realized / closing-date match, not listing publish time.

## Lot object

Each lot entry should include at least:

```json
{
  "auction_id": "string",
  "lot_id": "string",
  "lot_number": "1601",
  "title": "Pair of Diamond Earrings",
  "creator": "Cartier",
  "estimate_low": 80000,
  "estimate_high": 160000,
  "currency": "HKD",
  "bid_ask": 190000,
  "final_price": 243200,
  "result_visibility": "visible",
  "lot_state": "Closed",
  "sold_state": "sold",
  "reserve_met": true,
  "withdrawn": false,
  "url": "https://www.christies.com/...",
  "category_match_method": "auction_listing",
  "number_of_bids": 22
}
```

Allowed `sold_state` values:

- `sold`
- `unsold`
- `withdrawn`
- `hidden`
- `unknown`

Allowed `category_match_method` values:

- `lot_metadata`
- `auction_listing`

Notes:

- `final_price` stores the realized value only when Christie's exposes a true final result.
- Hidden results keep `final_price=null` and use `result_visibility="hidden"`.
- Preserve the original lot URL so downstream outputs can link back to the source page.

## Summary object

Expected aggregate fields include:

- `auction_count`
- `total_lots`
- `valid_lot_count`
- `sold_count`
- `hidden_result_count`
- `withdrawn_count`
- `sell_through_rate`
- `total_realized_by_currency`
- `auction_sale_totals_by_currency`
- `estimate_position_counts`
- `top_lots`
- `creators`
- `locations`
- `sales_types`

## report.md contract

`report.md` is a human-readable output with this fixed section order:

1. 查询条件
2. 核心摘要
3. 拍卖列表
4. 品牌 / 作者分布
5. 类别 / 地点 / 销售类型分布
6. 数据说明 / 异常说明
7. `## All lots`

### Auction table requirements

The auction list table must use these columns:

- `Auction`
- `Date`
- `Location`
- `Sale Total`
- `Link`

Rules:

- `Sale Total` must show the real auction-level sale total, for example `256,867,760 HKD`.
- `Link` must render as a Markdown link: `[查看](<auction-url>)`.
- Each row must point to the original Christie's auction or result page.

### All lots table requirements

The full appendix table at the bottom must use these columns:

- `Lot`
- `Creator`
- `Title`
- `Estimate`
- `Realized`
- `Variance%`
- `Status`
- `Link`

Rules:

- The `All lots` table must appear at the very bottom of the report.
- Do not truncate the lot list unless the user explicitly asks for truncation.
- `Estimate` is displayed as `low - high + currency`.
- `Realized` must show the true lot-level realized value when visible; otherwise show `N/A`.
- `Variance%` is measured against the estimate midpoint.
- `Link` must render as a Markdown link: `[查看](<lot-url>)`.

## all-lots.csv contract

`all-lots.csv` is the machine-friendly export for spreadsheet and downstream processing.

Required header order:

```text
auction_title,auction_date,auction_location,lot_number,creator,title,estimate_low,estimate_high,currency,final_price,variance_pct,sold_state,reserve_met,number_of_bids,category_match_method,url
```

Field notes:

- `auction_date` should align with the realized / closing date used for matching.
- `final_price` is the realized value or empty when hidden/unavailable.
- `variance_pct` should match the report midpoint-based calculation.
- `url` is always the original lot URL.

## Error object

```json
{
  "level": "warning",
  "scope": "lot",
  "auction_id": "string",
  "lot_id": "string",
  "message": "final result hidden for current account"
}
```

Use `level="fatal"` only when the run stops before producing the full outputs.
