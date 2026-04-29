# Christie's Field Notes

## Main entry and discovery path

Christie's version 1 starts from the **results page main entry**:

- `https://www.christies.com/en/results/`

Use the results listing as the primary discovery surface for candidate auctions.

Workflow expectation:

1. Open the results page.
2. Filter or identify `Jewellery` entries.
3. Match by realized / closing date.
4. Open the auction detail or result page.
5. Extract auction-level sale totals and lot-level realized outcomes.

Calendar-oriented pages may help with research, but they are not the primary entry point for this skill.

## Date matching semantics

Date filtering is based on **realized / closing date**.

- Live auctions: use the actual sale date.
- Online or timed auctions: use the closing or results date.
- Multi-day auctions: include them when the effective sale window overlaps the requested absolute range.

Do not match by:

- publish date
- marketing date text when it differs from the actual result date
- calendar-listing display date alone

## Category matching

Version 1 supports only `Jewellery`.

Matching guidance:

- Start from the Christie's results-page category or department listing.
- Prefer explicit lot- or auction-level metadata when it confirms `Jewellery`.
- If the lot lacks richer metadata but the auction is clearly a `Jewellery` result, keep the lot and mark `category_match_method="auction_listing"`.
- Reject all non-`Jewellery` categories instead of silently widening the scope.

## Login-enhanced verification

Christie's must use **positive login verification**.

Accept the session only when there is an explicit logged-in marker, such as:

- `LOG OUT`
- `SIGN OUT`
- `MY ACCOUNT`
- account-menu UI that clearly identifies an authenticated session

Treat the session as invalid when there is an explicit logged-out marker, such as:

- `SIGN IN`
- `LOG IN`
- prompts to sign in to view results
- anonymous account or preferred-access prompts

If the page is ambiguous, fail the login check. Do not infer a valid session merely because a logged-out string is absent.

## Preferred extraction sources

Prefer structured page state over brittle DOM text.

Priority order:

1. Apollo cache
2. Redux or equivalent client state
3. `__NEXT_DATA__`
4. site-injected JSON payloads
5. stable logged-in API responses
6. visible page text as a fallback source of last resort

The core rule is to keep `Realized` and `Sale Total` tied to explicit source data rather than inferred rendering text.

## Result visibility and price semantics

- `sale_total` is valid only when Christie's explicitly exposes an auction-level sale total.
- `final_price` is valid only when the logged-in page exposes a true lot-level realized result.
- If the current account cannot see the result, use:
  - `result_visibility="hidden"`
  - `final_price=null`
  - a warning entry in `errors[]`
- Never substitute `bid_ask`, opening bid, estimate, or reserve state for `final_price`.

## Link preservation and reporting

Always preserve source URLs.

- Auction URLs are required for the auction list table.
- Lot URLs are required for `all-lots.csv` and the `All lots` appendix.
- `report.md` should render those links as compact `[查看]` links instead of long raw URLs.

## Currency

Keep Christie's source currency for both sale totals and realized prices. Do not auto-convert currencies in version 1.
