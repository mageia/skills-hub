#!/usr/bin/env python3
"""Collect Christie's Jewellery auction and lot data from a logged-in CDP Chrome session."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen

RESULTS_URL = 'https://www.christies.com/en/results/'
CHRISTIES_BASE_URL = 'https://www.christies.com'
ONLINE_ONLY_BASE_URL = 'https://onlineonly.christies.com'
SUPPORTED_CATEGORY = 'Jewellery'
JEWELLERY_KEYWORDS = ('JEWEL', 'JEWELLERY', 'JEWELS')
REJECTED_CATEGORY_KEYWORDS = ('WATCH', 'HANDBAG', 'HANDBAGS')
LOT_ROW_MARKERS = {
    'lot_number',
    'lot_id',
    'lot_id_txt',
    'online_only_static_lot_data',
    'price_realised',
    'title_primary_txt',
}


def resolve_cdp_target(cdp: str) -> str:
    parsed = urlparse(cdp)
    if parsed.scheme in {'http', 'https'}:
        base = cdp.rstrip('/')
        try:
            with urlopen(base + '/json/list', timeout=8) as response:
                items = json.load(response)
            for item in items:
                if item.get('type') == 'page' and item.get('webSocketDebuggerUrl'):
                    return item['webSocketDebuggerUrl']
        except Exception:
            pass
        with urlopen(base + '/json/version', timeout=8) as response:
            payload = json.load(response)
        websocket = payload.get('webSocketDebuggerUrl')
        if not websocket:
            raise RuntimeError(f'CDP endpoint did not return webSocketDebuggerUrl: {cdp}')
        return websocket
    return cdp


def connect_agent_browser(cdp: str) -> None:
    completed = run_agent_browser(['connect', resolve_cdp_target(cdp)])
    if completed.returncode != 0:
        raise RuntimeError(completed.stdout.strip())


def run_agent_browser(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ['agent-browser', *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def run_agent_browser_text(args: list[str]) -> str:
    completed = run_agent_browser(args)
    if completed.returncode != 0:
        raise RuntimeError(completed.stdout.strip())
    return completed.stdout


def decode_eval_output(output: str) -> Any:
    value = json.loads(output)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(('{', '[')):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                return value
    return value


def eval_json(script: str) -> Any:
    return decode_eval_output(run_agent_browser_text(['eval', script]))


def require_supported_category(category: str) -> str:
    if category.strip().lower() != SUPPORTED_CATEGORY.lower():
        raise SystemExit(f'Unsupported category: {category}. v1 only supports {SUPPORTED_CATEGORY}.')
    return SUPPORTED_CATEGORY


def money_value(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    cleaned = ''.join(ch for ch in text if ch.isdigit() or ch in '.-')
    if not cleaned or cleaned in {'-', '.', '-.', '.-'}:
        return None
    return float(cleaned)


def parse_money_with_currency(text: Any) -> tuple[float | None, str | None]:
    if text is None:
        return None, None
    raw = str(text).strip()
    if not raw:
        return None, None
    patterns = [
        re.compile(r'([A-Z]{3})\s*([0-9][0-9,]*(?:\.[0-9]+)?)'),
        re.compile(r'([0-9][0-9,]*(?:\.[0-9]+)?)\s*([A-Z]{3})'),
    ]
    for pattern in patterns:
        match = pattern.search(raw)
        if match:
            groups = match.groups()
            if pattern is patterns[0]:
                currency, amount = groups[0], groups[1]
            else:
                amount, currency = groups[0], groups[1]
            return float(amount.replace(',', '')), currency
    return money_value(raw), None


def iso_date(value: Any) -> str | None:
    if value is None:
        return None
    match = re.search(r'(20\d{2}-\d{2}-\d{2})', str(value))
    return match.group(1) if match else None


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def find_nested_dicts(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from find_nested_dicts(value)
    elif isinstance(node, list):
        for item in node:
            yield from find_nested_dicts(item)


def find_list_candidates(node: Any, key_name: str, required_keys: set[str]) -> list[list[dict[str, Any]]]:
    matches: list[list[dict[str, Any]]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == key_name and isinstance(value, list):
                dict_items = [item for item in value if isinstance(item, dict)]
                if dict_items and any(required_keys & set(item.keys()) for item in dict_items):
                    matches.append(dict_items)
            matches.extend(find_list_candidates(value, key_name, required_keys))
    elif isinstance(node, list):
        for item in node:
            matches.extend(find_list_candidates(item, key_name, required_keys))
    return matches


def candidate_text(record: dict[str, Any]) -> str:
    return ' '.join(
        str(first_non_empty(record.get(field), ''))
        for field in ('title_txt', 'subtitle_txt', 'landing_url', 'filter_ids')
    ).upper()


def is_jewellery_candidate(record: dict[str, Any]) -> bool:
    text = candidate_text(record)
    if any(keyword in text for keyword in REJECTED_CATEGORY_KEYWORDS):
        return False
    if any(keyword in text for keyword in JEWELLERY_KEYWORDS):
        return True
    return False


def sales_type_for_event(event: dict[str, Any]) -> str:
    if event.get('is_live') is True:
        return 'Live'
    if event.get('is_live') is False:
        return 'Online'
    subtitle = str(event.get('subtitle_txt') or '').upper()
    if 'LIVE AUCTION' in subtitle:
        return 'Live'
    if 'ONLINE AUCTION' in subtitle:
        return 'Online'
    return 'Unknown'


def parse_sale_total(record: dict[str, Any]) -> tuple[float | None, str | None]:
    for key in ('sale_total_value_txt', 'sale_total_txt', 'sale_total'):
        amount, currency = parse_money_with_currency(record.get(key))
        if amount is not None:
            return amount, currency
    return None, None


def extract_results_candidates(
    payload: dict[str, Any],
    category: str,
    from_date: str,
    to_date: str,
) -> list[dict[str, Any]]:
    require_supported_category(category)
    event_lists = find_list_candidates(payload, 'events', {'event_id', 'landing_url', 'title_txt'})
    candidates: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for events in event_lists:
        for event in events:
            end_at = iso_date(first_non_empty(event.get('end_date'), event.get('date_display_txt')))
            if end_at is None or not (from_date <= end_at <= to_date):
                continue
            if not is_jewellery_candidate(event):
                continue
            url = str(first_non_empty(event.get('landing_url'), ''))
            if not url or url in seen_urls:
                continue
            sale_total, sale_total_currency = parse_sale_total(event)
            candidates.append(
                {
                    'auction_id': str(first_non_empty(event.get('event_id'), url.rstrip('/').split('/')[-1])),
                    'title': str(first_non_empty(event.get('title_txt'), '')).strip(),
                    'url': url,
                    'category': SUPPORTED_CATEGORY,
                    'location': str(first_non_empty(event.get('location_txt'), '')).strip() or None,
                    'sales_type': sales_type_for_event(event),
                    'date_text': str(first_non_empty(event.get('date_display_txt'), '')).strip(),
                    'start_at': iso_date(event.get('start_date')) or end_at,
                    'end_at': end_at,
                    'matched_by_date_range': True,
                    'sale_total': sale_total,
                    'sale_total_currency': sale_total_currency,
                }
            )
            seen_urls.add(url)

    candidates.sort(key=lambda item: (item.get('end_at') or '', item.get('title') or ''))
    return candidates


def parse_bid_count(raw: dict[str, Any]) -> int | None:
    direct = raw.get('number_of_bids')
    if isinstance(direct, int):
        return direct
    bid_count_text = first_non_empty(raw.get('bid_count_txt'), raw.get('number_of_bids_txt'))
    if bid_count_text is None:
        return None
    match = re.search(r'(\d+)', str(bid_count_text))
    return int(match.group(1)) if match else None


def currency_from_record(raw: dict[str, Any], fallback: str | None = None) -> str | None:
    direct = first_non_empty(raw.get('currency'), raw.get('currency_code'), raw.get('currencyCode'))
    if isinstance(direct, str) and direct.strip():
        return direct.strip().upper()
    for field in ('price_realised_txt', 'estimate_txt', 'header_price', 'current_bid_txt', 'next_bid_text'):
        _, currency = parse_money_with_currency(raw.get(field))
        if currency:
            return currency
    return fallback


def absolute_lot_url(url: Any) -> str | None:
    if url is None:
        return None
    text = str(url).strip()
    if not text:
        return None
    if text.startswith('http://') or text.startswith('https://'):
        return text
    base = ONLINE_ONLY_BASE_URL if text.startswith('/s/') else CHRISTIES_BASE_URL
    return urljoin(base, text)


def build_page_sale_context(payload: dict[str, Any], auction_context: dict[str, Any] | None) -> dict[str, Any]:
    sale_data = {}
    bri_data = payload.get('briDataModel') if isinstance(payload.get('briDataModel'), dict) else {}
    if isinstance(bri_data, dict):
        raw_sale_data = bri_data.get('saleData')
        if isinstance(raw_sale_data, dict):
            sale_data = raw_sale_data

    sale_total = None
    sale_total_currency = None
    for node in find_nested_dicts(payload):
        if 'sale_total_value_txt' in node:
            sale_total, sale_total_currency = parse_money_with_currency(node.get('sale_total_value_txt'))
            if sale_total is not None:
                break

    auction_id = first_non_empty(
        sale_data.get('saleId'),
        sale_data.get('sale_id'),
        auction_context.get('auction_id') if auction_context else None,
    )
    location = first_non_empty(
        sale_data.get('location'),
        auction_context.get('location') if auction_context else None,
    )
    title = first_non_empty(
        sale_data.get('saleTitle'),
        auction_context.get('title') if auction_context else None,
    )
    return {
        'auction_id': str(auction_id) if auction_id is not None else None,
        'location': str(location).strip() if isinstance(location, str) and location.strip() else location,
        'title': str(title).strip() if isinstance(title, str) and title.strip() else title,
        'sale_total': sale_total if sale_total is not None else auction_context.get('sale_total') if auction_context else None,
        'sale_total_currency': sale_total_currency or auction_context.get('sale_total_currency') if auction_context else sale_total_currency,
    }


def normalize_lot_row(
    raw: dict[str, Any],
    category: str,
    sale_context: dict[str, Any],
    auction_context: dict[str, Any] | None,
) -> dict[str, Any]:
    require_supported_category(category)
    static_data = raw.get('online_only_static_lot_data') if isinstance(raw.get('online_only_static_lot_data'), dict) else {}
    dynamic_data = raw.get('online_only_dynamic_lot_data') if isinstance(raw.get('online_only_dynamic_lot_data'), dict) else {}
    lot_id = first_non_empty(
        static_data.get('lot_id'),
        raw.get('lot_id'),
        raw.get('lotId'),
        raw.get('object_id'),
    )
    title = first_non_empty(raw.get('title_primary_txt'), raw.get('title'), raw.get('title_txt'))
    creator = first_non_empty(
        raw.get('title_secondary_txt'),
        raw.get('creator'),
        raw.get('creator_txt'),
        raw.get('maker_name'),
        raw.get('artist_name'),
        'Unknown',
    )
    estimate_low = money_value(first_non_empty(raw.get('estimate_low'), raw.get('estimateLow')))
    estimate_high = money_value(first_non_empty(raw.get('estimate_high'), raw.get('estimateHigh')))
    final_price = money_value(first_non_empty(raw.get('price_realised'), raw.get('final_price')))
    bid_ask = money_value(first_non_empty(raw.get('current_bid'), dynamic_data.get('next_bid'), raw.get('bid_ask')))
    currency = currency_from_record(raw, auction_context.get('sale_total_currency') if auction_context else None)
    lot_state = first_non_empty(dynamic_data.get('item_status'), raw.get('lot_state'), raw.get('status'), 'Unknown')
    withdrawn = bool(first_non_empty(raw.get('lot_withdrawn'), raw.get('withdrawn'), False))
    reserve_met = first_non_empty(raw.get('reserve_met'), raw.get('reserveMet'))
    number_of_bids = parse_bid_count(raw)

    if withdrawn:
        result_visibility = 'not_applicable'
        sold_state = 'withdrawn'
    elif final_price is not None:
        result_visibility = 'visible'
        sold_state = 'sold'
    elif raw.get('is_unsold') is True:
        result_visibility = 'visible'
        sold_state = 'unsold'
    elif str(lot_state).strip().lower() == 'closed':
        result_visibility = 'hidden'
        sold_state = 'hidden'
    else:
        result_visibility = 'unknown'
        sold_state = 'unknown'

    return {
        'auction_id': first_non_empty(sale_context.get('auction_id'), auction_context.get('auction_id') if auction_context else None),
        'lot_id': str(lot_id) if lot_id is not None else None,
        'lot_number': str(first_non_empty(raw.get('lot_number'), raw.get('lot_id_txt'), raw.get('lotNumber')) or ''),
        'title': str(title).strip() if title is not None else '',
        'creator': str(creator).strip() if creator is not None else 'Unknown',
        'estimate_low': estimate_low,
        'estimate_high': estimate_high,
        'currency': currency,
        'bid_ask': bid_ask,
        'final_price': final_price,
        'result_visibility': result_visibility,
        'lot_state': str(lot_state).strip() if lot_state is not None else 'Unknown',
        'sold_state': sold_state,
        'reserve_met': reserve_met,
        'withdrawn': withdrawn,
        'url': absolute_lot_url(first_non_empty(raw.get('url'), raw.get('landing_url'))),
        'category_match_method': 'auction_listing',
        'number_of_bids': number_of_bids,
    }


def lot_sort_key(lot: dict[str, Any]) -> tuple[int, str]:
    lot_number = str(lot.get('lot_number') or '')
    if lot_number.isdigit():
        return int(lot_number), lot_number
    return 10**9, lot_number


def extract_lots_from_cache(
    payload: dict[str, Any],
    category: str,
    auction_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    require_supported_category(category)
    sale_context = build_page_sale_context(payload, auction_context)
    lot_lists = find_list_candidates(payload, 'lots', LOT_ROW_MARKERS)
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()

    for lot_list in lot_lists:
        for raw in lot_list:
            row = normalize_lot_row(raw, category, sale_context, auction_context)
            dedupe_key = '|'.join(
                str(first_non_empty(row.get(field), ''))
                for field in ('auction_id', 'lot_id', 'url', 'lot_number')
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            normalized.append(row)

    normalized.sort(key=lot_sort_key)
    return normalized


def load_all_pages_if_needed(max_clicks: int = 20) -> None:
    script = r'''(() => {
  const clickable = Array.from(document.querySelectorAll('button,a')).find((element) => {
    const text = ((element.innerText || element.textContent || '').replace(/\s+/g, ' ').trim()).toUpperCase();
    const label = ((element.getAttribute('aria-label') || '').replace(/\s+/g, ' ').trim()).toUpperCase();
    const disabled = element.disabled || element.getAttribute('aria-disabled') === 'true';
    return !disabled && (/LOAD MORE|SHOW MORE/.test(text) || /NEXT PAGE|GO TO NEXT PAGE/.test(label));
  });
  if (!clickable) return 'DONE';
  clickable.click();
  return 'CLICKED';
})()'''
    for _ in range(max_clicks):
        result = eval_json(script)
        if result != 'CLICKED':
            return
        run_agent_browser_text(['wait', '1500'])


def collect_results_payload() -> dict[str, Any]:
    data = eval_json(
        'JSON.stringify(window.chrComponents && window.chrComponents.calendar ? window.chrComponents.calendar.data : null)'
    )
    if not isinstance(data, dict):
        raise RuntimeError('Christie\'s results page did not expose structured calendar data')
    return data


def collect_auction_page_payload() -> dict[str, Any]:
    payload = eval_json(
        'JSON.stringify({'
        'href: location.href,'
        'pathname: location.pathname,'
        'chrComponents: window.chrComponents || null,'
        'briDataModel: window.briDataModel || null,'
        'chrGlobal: window.chrGlobal || null,'
        'bodyText: (document.body && document.body.innerText ? document.body.innerText.slice(0, 5000) : "")'
        '})'
    )
    if not isinstance(payload, dict):
        raise RuntimeError('Christie\'s auction page did not expose structured page state')
    return payload


def merge_auction_with_page(candidate: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    sale_context = build_page_sale_context(payload, candidate)
    merged = dict(candidate)
    if sale_context.get('auction_id'):
        merged['auction_id'] = str(sale_context['auction_id'])
    if sale_context.get('title'):
        merged['title'] = sale_context['title']
    if sale_context.get('location'):
        merged['location'] = sale_context['location']
    if sale_context.get('sale_total') is not None:
        merged['sale_total'] = sale_context['sale_total']
    if sale_context.get('sale_total_currency'):
        merged['sale_total_currency'] = sale_context['sale_total_currency']
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cdp-port', type=int, default=9222)
    parser.add_argument('--cdp-url', help='Full remote CDP base URL, e.g. https://cdp.example.com')
    parser.add_argument('--category', required=True)
    parser.add_argument('--from-date', required=True)
    parser.add_argument('--to-date', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    category = require_supported_category(args.category)
    if shutil.which('agent-browser') is None:
        raise SystemExit('agent-browser is required for CDP collection')

    cdp_target = args.cdp_url or f'http://127.0.0.1:{args.cdp_port}'
    connect_agent_browser(cdp_target)
    run_agent_browser_text(['open', RESULTS_URL])
    run_agent_browser_text(['wait', '2000'])

    results_payload = collect_results_payload()
    candidates = extract_results_candidates(results_payload, category, args.from_date, args.to_date)
    if not candidates:
        raise SystemExit('Christie\'s results page candidate discovery returned no Jewellery auctions in range')

    auctions: list[dict[str, Any]] = []
    lots: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for candidate in candidates:
        try:
            run_agent_browser_text(['open', candidate['url']])
            run_agent_browser_text(['wait', '2500'])
            load_all_pages_if_needed()
            page_payload = collect_auction_page_payload()
            auction = merge_auction_with_page(candidate, page_payload)
            auction_lots = extract_lots_from_cache(page_payload, category, auction)
            if not auction_lots:
                raise RuntimeError('No structured lot rows found in Christies page state')
            auctions.append(auction)
            lots.extend(auction_lots)
        except Exception as exc:  # noqa: BLE001 - explicit non-fatal collection path
            errors.append(
                {
                    'level': 'warning',
                    'scope': 'auction',
                    'auction_id': candidate.get('auction_id'),
                    'url': candidate.get('url'),
                    'message': str(exc),
                }
            )
            auctions.append(candidate)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_data = {
        'query': {
            'date_from': args.from_date,
            'date_to': args.to_date,
            'category': category,
        },
        'auctions': auctions,
        'lots': sorted(lots, key=lot_sort_key),
        'summary': {},
        'errors': errors,
    }
    output_path.write_text(json.dumps(raw_data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(
        json.dumps(
            {
                'raw_data': str(output_path),
                'auction_count': len(auctions),
                'lot_count': len(lots),
                'error_count': len(errors),
            },
            ensure_ascii=False,
        )
    )


if __name__ == '__main__':
    main()
