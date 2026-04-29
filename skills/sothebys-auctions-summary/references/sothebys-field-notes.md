# Sotheby's Field Notes

## Login-enhanced result rules

Sotheby's public pages may show `Log in to view results`. Treat that as a failed precondition for login-enhanced reporting unless the logged-in page/API exposes actual final results.

Never infer final price from:

- visible estimate
- current/starting bid
- bid ask
- reserve state
- recommended item cards

## Date matching

Use the effective auction close/result time.

- Timed/Online: use closing/end time.
- Live: use the live auction/session date.
- Multi-day auctions: include the auction when its effective result/close date overlaps the requested date range.

## Category matching

Start from Sotheby's results category filter. For lots:

- Prefer lot-level departments/object/category metadata when available.
- If absent, keep lots from a category-matched auction and set `category_match_method="auction_listing"`.

## Currency

Keep source currency per lot and aggregate totals by currency. Do not convert currencies without explicit user request and exchange-rate source.
