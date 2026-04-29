#!/usr/bin/env python3
"""Collect Sotheby's auction and lot data from a logged-in CDP Chrome session."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

CATEGORY_FILTERS = {
    "jewelry": "00000164-609b-d1db-a5e6-e9ff0ccd0000",
    "watches": "00000164-609a-d1db-a5e6-e9fffc050000",
    "contemporary art": "00000164-609b-d1db-a5e6-e9ff01230000",
}

MONTHS = {
    "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4, "MAY": 5, "JUNE": 6,
    "JULY": 7, "AUGUST": 8, "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12,
}


def resolve_cdp_target(cdp: str) -> str:
    parsed = urlparse(cdp)
    if parsed.scheme in {"http", "https"}:
        base = cdp.rstrip("/")
        try:
            with urlopen(base + "/json/list", timeout=8) as response:
                items = json.load(response)
            for item in items:
                if item.get("type") == "page" and item.get("webSocketDebuggerUrl"):
                    return item["webSocketDebuggerUrl"]
        except Exception:
            pass
        with urlopen(base + "/json/version", timeout=8) as response:
            data = json.load(response)
        ws = data.get("webSocketDebuggerUrl")
        if not ws:
            raise RuntimeError(f"CDP endpoint did not return webSocketDebuggerUrl: {cdp}")
        return ws
    return cdp


def connect_ab(cdp: str) -> None:
    completed = subprocess.run(
        ["agent-browser", "connect", resolve_cdp_target(cdp)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stdout.strip())


def run_ab(args: list[str]) -> str:
    completed = subprocess.run(
        ["agent-browser", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stdout.strip())
    return completed.stdout


def decode_eval_output(out: str) -> Any:
    value = json.loads(out)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("{", "[", '"')) or stripped in {"true", "false", "null"} or stripped[:1].isdigit() or stripped[:1] == '-':
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
    return value


def eval_json(script: str) -> Any:
    out = run_ab(["eval", script])
    return decode_eval_output(out)


def parse_card_date(text: str) -> str | None:
    normalized = text.upper().replace("–", "-")
    match = re.search(r"(?:(\d{1,2})-)?(\d{1,2})\s+([A-Z]+)\s+(20\d{2})", normalized)
    if not match:
        return None
    day = int(match.group(2))
    month = MONTHS.get(match.group(3))
    year = int(match.group(4))
    if not month:
        return None
    return date(year, month, day).isoformat()


def within_range(date_text: str | None, from_date: str, to_date: str) -> bool:
    return date_text is not None and from_date <= date_text <= to_date


def extract_sale_total(card_text: str) -> tuple[float | None, str | None]:
    match = re.search(r"SALE TOTAL:\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*([A-Z]{3})", card_text, re.IGNORECASE)
    if not match:
        return None, None
    return float(match.group(1).replace(',', '')), match.group(2)


def auction_cards() -> list[dict[str, str]]:
    script = r'''
JSON.stringify(Array.from(document.querySelectorAll('a[href*="/en/buy/auction/"]')).map(a => ({
  text: (a.innerText || a.textContent || '').replace(/\s+/g, ' ').trim(),
  href: a.href || a.getAttribute('href') || ''
})).filter(x => x.text.includes('Type: auction')).reduce((acc, item) => {
  if (!acc.some(existing => existing.href === item.href)) acc.push(item);
  return acc;
}, []))
'''
    cards = eval_json(script)
    if not isinstance(cards, list):
        raise RuntimeError(f"Unexpected auction card payload type: {type(cards).__name__}")
    return cards




def page_body_text() -> str:
    text = eval_json('document.body.innerText')
    return text if isinstance(text, str) else str(text)


def expected_result_count_from_page() -> int | None:
    text = page_body_text()
    match = re.search(r'(\d+)\s+results sorted by', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def wait_for_apollo_lots(expected_count: int | None, retries: int = 12) -> dict[str, Any]:
    best: dict[str, Any] = {}
    best_count = -1
    for _ in range(retries):
        apollo = extract_apollo_cache()
        count = sum(1 for key in apollo if key.startswith('LotCard:'))
        if count > best_count:
            best = apollo
            best_count = count
        if expected_count is not None and count >= expected_count:
            return apollo
        if expected_count is None and count > 0:
            return apollo
        run_ab(['wait', '1000'])
    return best



def click_button_by_label(label: str) -> str:
    script = f'''(() => {{
  const btn = Array.from(document.querySelectorAll("button")).find(b => (b.getAttribute("aria-label") || "") === {json.dumps(label)});
  if (!btn) return "NOT_FOUND";
  if (btn.disabled || btn.getAttribute("aria-disabled") === "true") return "DISABLED";
  btn.click();
  return "CLICKED";
}})()'''
    return str(eval_json(script))


def go_to_first_page_if_needed() -> None:
    current = eval_json(r'''(() => {
  const btn = Array.from(document.querySelectorAll("button")).find(b => /Current page, page 1\./.test(b.getAttribute("aria-label") || ""));
  return btn ? "ALREADY" : "NEEDS_RESET";
})()''')
    if current == 'ALREADY':
        return
    result = click_button_by_label('Go to page 1.')
    if result == 'CLICKED':
        run_ab(['wait', '1500'])


def load_all_pagination_pages() -> None:
    go_to_first_page_if_needed()
    for _ in range(100):
        result = click_button_by_label('Go to next page.')
        if result != 'CLICKED':
            return
        run_ab(['wait', '1500'])

def extract_apollo_cache() -> dict[str, Any]:
    data = eval_json('JSON.stringify(window.__APOLLO_CLIENT__ ? window.__APOLLO_CLIENT__.extract() : {})')
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected Apollo cache payload type: {type(data).__name__}")
    return data


def amount_value(amount_obj: dict[str, Any] | None) -> tuple[float | None, str | None]:
    if not amount_obj:
        return None, None
    amount = amount_obj.get('amount')
    currency = amount_obj.get('currency')
    return (float(amount) if amount is not None else None), currency


def extract_lots_from_apollo(apollo: dict[str, Any], category: str) -> list[dict[str, Any]]:
    rows = []
    for key, card in apollo.items():
        if not key.startswith('LotCard:'):
            continue
        bid_ref = (card.get('bidState') or {}).get('__ref')
        bid_state = apollo.get(bid_ref, {}) if bid_ref else {}
        sold_state_data = bid_state.get('sold') or {}
        final_price, final_currency = amount_value(((sold_state_data.get('premiums') or {}).get('finalPriceV2')))
        bid_ask, bid_ask_currency = amount_value(bid_state.get('currentBidV2'))
        low_estimate, estimate_currency_low = amount_value(((card.get('estimateV2') or {}).get('lowEstimate')))
        high_estimate, estimate_currency_high = amount_value(((card.get('estimateV2') or {}).get('highEstimate')))
        auction = card.get('auction') or {}
        slug = card.get('slug') or {}
        auction_slug = auction.get('slug') or {}
        year = auction_slug.get('year')
        auction_name = auction_slug.get('name')
        lot_slug = slug.get('lotSlug')
        lot_url = None
        if year and auction_name and lot_slug:
            lot_url = f'https://www.sothebys.com/en/buy/auction/{year}/{auction_name}/{lot_slug}'

        sold_type = sold_state_data.get('__typename')
        if sold_type == 'ResultVisible' and sold_state_data.get('isSold') is True:
            result_visibility = 'visible'
            sold_state = 'sold'
        elif sold_type == 'ResultHidden':
            result_visibility = 'hidden'
            sold_state = 'hidden'
        else:
            result_visibility = 'unknown'
            sold_state = 'unknown'

        rows.append({
            'auction_id': auction.get('auctionId'),
            'lot_id': card.get('lotId'),
            'lot_number': (card.get('lotNumber') or {}).get('lotDisplayNumber'),
            'title': card.get('title'),
            'creator': card.get('creatorsDisplayTitle') or 'Unknown',
            'estimate_low': low_estimate,
            'estimate_high': high_estimate,
            'currency': final_currency or bid_ask_currency or estimate_currency_low or estimate_currency_high or auction.get('currency'),
            'bid_ask': bid_ask,
            'final_price': final_price,
            'result_visibility': result_visibility,
            'lot_state': 'Closed' if auction.get('state') == 'Closed' else auction.get('state', 'unknown'),
            'sold_state': sold_state,
            'reserve_met': bid_state.get('reserveMet'),
            'withdrawn': ((card.get('withdrawnState') or {}).get('state') == 'Withdrawn'),
            'url': lot_url,
            'category_match_method': 'auction_listing',
            'number_of_bids': bid_state.get('numberOfBids'),
        })
    rows.sort(key=lambda x: int(x['lot_number']) if str(x.get('lot_number', '')).isdigit() else 10**9)
    return rows




def parse_auction_title(card_text: str) -> str:
    title = re.sub(r'^Type: auction\s+CATEGORY:\s+', '', card_text, flags=re.IGNORECASE).strip()
    title = re.sub(r'^(PAST AUCTION|AUCTION CLOSING|CLOSING|SELLING EXHIBITION)\s+', '', title, flags=re.IGNORECASE).strip()
    title = re.sub(r'\s+(?:(?:\d{1,2}[–-])?\d{1,2}\s+[A-Z]+\s+20\d{2}).*$', '', title, flags=re.IGNORECASE).strip()
    return title or card_text

def normalize_location(card_text: str) -> str | None:
    if '|' not in card_text:
        return None
    tail = card_text.split('|')[-1].strip()
    return re.sub(r'\s+SALE TOTAL:.*$', '', tail).strip() or None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cdp-port', type=int, default=9222)
    parser.add_argument('--cdp-url', help='Full remote CDP base URL, e.g. https://cdp.example.com')
    parser.add_argument('--category', required=True)
    parser.add_argument('--from-date', required=True)
    parser.add_argument('--to-date', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    if shutil.which('agent-browser') is None:
        raise SystemExit('agent-browser is required for CDP collection')

    category_key = args.category.strip().lower()
    if category_key not in CATEGORY_FILTERS:
        raise SystemExit(f'Unsupported category: {args.category}')

    connect_ab(args.cdp_url or str(args.cdp_port))
    url = f'https://www.sothebys.com/en/results?locale=en&f2={CATEGORY_FILTERS[category_key]}'
    run_ab(['open', url])
    run_ab(['wait', '2000'])

    auctions: list[dict[str, Any]] = []
    lots: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for card in auction_cards():
        card_date = parse_card_date(card['text'])
        if not within_range(card_date, args.from_date, args.to_date):
            continue
        sale_total, sale_total_currency = extract_sale_total(card['text'])
        auction = {
            'auction_id': card['href'].rstrip('/').split('/')[-1],
            'title': parse_auction_title(card['text']),
            'url': card['href'],
            'category': args.category,
            'location': normalize_location(card['text']),
            'sales_type': 'Online' if 'ONLINE' in card['text'].upper() else 'Live',
            'date_text': card['text'],
            'start_at': card_date,
            'end_at': card_date,
            'matched_by_date_range': True,
            'sale_total': sale_total,
            'sale_total_currency': sale_total_currency,
        }
        auctions.append(auction)
        try:
            run_ab(['open', card['href'] + '?lotFilter=AllLots'])
            run_ab(['wait', '2500'])
            expected_count = expected_result_count_from_page()
            apollo = wait_for_apollo_lots(expected_count)
            current_count = sum(1 for key in apollo if key.startswith('LotCard:'))
            if expected_count is not None and current_count < expected_count:
                load_all_pagination_pages()
                apollo = wait_for_apollo_lots(expected_count)
            auction_lots = extract_lots_from_apollo(apollo, args.category)
            if not auction_lots:
                raise RuntimeError('Apollo cache returned zero lots')
            if expected_count is not None and len(auction_lots) < expected_count:
                raise RuntimeError(f'Apollo cache incomplete: expected {expected_count} lots, got {len(auction_lots)}')
            lots.extend(auction_lots)
        except Exception as exc:
            errors.append({'level': 'warning', 'scope': 'auction', 'auction_id': auction['auction_id'], 'message': str(exc)})

    data = {
        'query': {'date_from': args.from_date, 'date_to': args.to_date, 'category': args.category},
        'auctions': auctions,
        'lots': lots,
        'summary': {},
        'errors': errors,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'raw_data': str(output_path), 'auction_count': len(auctions), 'lot_count': len(lots), 'errors': len(errors)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
