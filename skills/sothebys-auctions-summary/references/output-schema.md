# Output Schema

The workflow writes `raw-data.json` and `report.md` into the configured output directory.

## raw-data.json

```json
{
  "query": {
    "date_from": "2026-04-20",
    "date_to": "2026-04-26",
    "category": "Jewelry"
  },
  "auctions": [],
  "lots": [],
  "summary": {},
  "errors": []
}
```

## Auction object

```json
{
  "auction_id": "string",
  "title": "string",
  "url": "string",
  "category": "Jewelry",
  "location": "Hong Kong",
  "sales_type": "Live",
  "date_text": "23 APRIL 2026 | 11:00 AM HKT | HONG KONG",
  "start_at": "2026-04-23",
  "end_at": "2026-04-23",
  "matched_by_date_range": true,
  "sale_total": 256867760,
  "sale_total_currency": "HKD"
}
```

## Lot object

```json
{
  "auction_id": "string",
  "lot_id": "string",
  "lot_number": "1601",
  "title": "Pair of Diamond and Emerald Cufflinks",
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
  "url": "https://www.sothebys.com/...",
  "category_match_method": "auction_listing",
  "number_of_bids": 22
}
```

Allowed `sold_state` values: `sold`, `unsold`, `withdrawn`, `hidden`, `unknown`.

Allowed `category_match_method` values: `lot_metadata`, `auction_listing`.

## Summary object

Expected aggregate fields:

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

## Report contract

`report.md` includes:

1. 查询条件
2. 核心摘要
3. 拍卖列表（含拍卖原始链接和 sale total）
4. 成交额（按原币种）
5. 估价区间表现
6. 品牌 / 作者分布
7. 地点分布
8. 销售类型分布
9. 数据异常与缺口
10. `All lots` 完整表格（放在最下方，包含 lot 原始链接与 realized）

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

Use `level="fatal"` only for runs that stop before producing complete outputs.
