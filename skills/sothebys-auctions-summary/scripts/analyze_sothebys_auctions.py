#!/usr/bin/env python3
"""Generate Sotheby's auction summary metrics and Markdown report from raw JSON."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, help='Path to raw-data.json')
    parser.add_argument('--output', required=True, help='Path to report.md')
    parser.add_argument('--write-summary', action='store_true', help='Update summary in input JSON')
    return parser.parse_args()


def money_value(value: Any) -> float | None:
    if value is None or value == '':
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = ''.join(ch for ch in str(value) if ch.isdigit() or ch in '.-')
    return float(cleaned) if cleaned else None


def money_display(amount: float | None, currency: str | None = None) -> str:
    if amount is None:
        return 'N/A'
    suffix = f' {currency}' if currency else ''
    return f'{amount:,.0f}{suffix}'


def estimate_position(lot: dict[str, Any]) -> str:
    final_price = money_value(lot.get('final_price'))
    low = money_value(lot.get('estimate_low'))
    high = money_value(lot.get('estimate_high'))
    if final_price is None or low is None or high is None:
        return 'unclassified'
    if final_price < low:
        return 'below_estimate'
    if final_price > high:
        return 'above_estimate'
    return 'within_estimate'


def variance_pct(lot: dict[str, Any]) -> float | None:
    final_price = money_value(lot.get('final_price'))
    low = money_value(lot.get('estimate_low'))
    high = money_value(lot.get('estimate_high'))
    if final_price is None or low is None or high is None:
        return None
    midpoint = (low + high) / 2
    if midpoint == 0:
        return None
    return (final_price - midpoint) / midpoint


def pct_display(value: float | None) -> str:
    if value is None:
        return 'N/A'
    return f'{value:+.1%}'


def build_summary(data: dict[str, Any]) -> dict[str, Any]:
    auctions = data.get('auctions', [])
    lots = data.get('lots', [])
    valid_lots = [lot for lot in lots if not lot.get('withdrawn')]
    sold_lots = [lot for lot in valid_lots if lot.get('sold_state') == 'sold' and money_value(lot.get('final_price')) is not None]

    totals_by_currency: dict[str, float] = defaultdict(float)
    estimate_low_by_currency: dict[str, float] = defaultdict(float)
    estimate_high_by_currency: dict[str, float] = defaultdict(float)

    for lot in lots:
        currency = lot.get('currency') or 'UNKNOWN'
        low = money_value(lot.get('estimate_low'))
        high = money_value(lot.get('estimate_high'))
        if low is not None:
            estimate_low_by_currency[currency] += low
        if high is not None:
            estimate_high_by_currency[currency] += high

    for lot in sold_lots:
        totals_by_currency[(lot.get('currency') or 'UNKNOWN')] += money_value(lot.get('final_price')) or 0.0

    auction_totals_by_currency: dict[str, float] = defaultdict(float)
    for auction in auctions:
        amount = money_value(auction.get('sale_total'))
        currency = auction.get('sale_total_currency') or 'UNKNOWN'
        if amount is not None:
            auction_totals_by_currency[currency] += amount

    top_lots = sorted(sold_lots, key=lambda lot: money_value(lot.get('final_price')) or 0.0, reverse=True)[:20]

    return {
        'auction_count': len(auctions),
        'total_lots': len(lots),
        'valid_lot_count': len(valid_lots),
        'sold_count': len(sold_lots),
        'hidden_result_count': sum(1 for lot in lots if lot.get('result_visibility') == 'hidden'),
        'withdrawn_count': sum(1 for lot in lots if lot.get('withdrawn')),
        'sell_through_rate': (len(sold_lots) / len(valid_lots)) if valid_lots else None,
        'total_realized_by_currency': dict(sorted(totals_by_currency.items())),
        'auction_sale_totals_by_currency': dict(sorted(auction_totals_by_currency.items())),
        'estimate_total_low_by_currency': dict(sorted(estimate_low_by_currency.items())),
        'estimate_total_high_by_currency': dict(sorted(estimate_high_by_currency.items())),
        'estimate_position_counts': dict(Counter(estimate_position(lot) for lot in lots)),
        'top_lots': [
            {
                'lot_id': lot.get('lot_id'),
                'lot_number': lot.get('lot_number'),
                'title': lot.get('title'),
                'creator': lot.get('creator'),
                'final_price': lot.get('final_price'),
                'currency': lot.get('currency'),
                'url': lot.get('url'),
            }
            for lot in top_lots
        ],
        'creators': dict(Counter((lot.get('creator') or 'Unknown').strip() for lot in lots).most_common(20)),
        'locations': dict(Counter((auction.get('location') or 'Unknown').strip() for auction in auctions).most_common()),
        'sales_types': dict(Counter((auction.get('sales_type') or 'Unknown').strip() for auction in auctions).most_common()),
    }


def write_csv(data: dict[str, Any], output_path: Path) -> Path:
    csv_path = output_path.with_name('all-lots.csv')
    lots = sorted(data.get('lots', []), key=lambda lot: int(lot.get('lot_number')) if str(lot.get('lot_number', '')).isdigit() else 10**9)
    auctions_by_id = {auction.get('auction_id'): auction for auction in data.get('auctions', [])}
    headers = [
        'auction_title', 'auction_date', 'auction_location', 'lot_number', 'creator', 'title',
        'estimate_low', 'estimate_high', 'currency', 'final_price', 'variance_pct', 'sold_state',
        'reserve_met', 'number_of_bids', 'category_match_method', 'url'
    ]
    with csv_path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for lot in lots:
            auction = auctions_by_id.get(lot.get('auction_id'), {})
            writer.writerow({
                'auction_title': auction.get('title') or '',
                'auction_date': auction.get('end_at') or '',
                'auction_location': auction.get('location') or '',
                'lot_number': lot.get('lot_number') or '',
                'creator': lot.get('creator') or '',
                'title': lot.get('title') or '',
                'estimate_low': lot.get('estimate_low') if lot.get('estimate_low') is not None else '',
                'estimate_high': lot.get('estimate_high') if lot.get('estimate_high') is not None else '',
                'currency': lot.get('currency') or '',
                'final_price': lot.get('final_price') if lot.get('final_price') is not None else '',
                'variance_pct': variance_pct(lot) if variance_pct(lot) is not None else '',
                'sold_state': lot.get('sold_state') or '',
                'reserve_met': lot.get('reserve_met') if lot.get('reserve_met') is not None else '',
                'number_of_bids': lot.get('number_of_bids') if lot.get('number_of_bids') is not None else '',
                'category_match_method': lot.get('category_match_method') or '',
                'url': lot.get('url') or '',
            })
    return csv_path


def render_report(data: dict[str, Any], summary: dict[str, Any]) -> str:
    query = data.get('query', {})
    auctions = data.get('auctions', [])
    lots = sorted(data.get('lots', []), key=lambda lot: int(lot.get('lot_number')) if str(lot.get('lot_number', '')).isdigit() else 10**9)
    errors = data.get('errors', [])
    generated_at = datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')
    lines = [
        "# Sotheby's Auctions Summary",
        '',
        '## 查询条件',
        '',
        f"- 日期范围：{query.get('date_from', '')} 至 {query.get('date_to', '')}",
        f"- 分类：{query.get('category', '')}",
        f"- 生成时间：{generated_at}",
        '',
        '## 核心摘要',
        '',
        f"- 拍卖场次：{summary['auction_count']}",
        f"- 拍品总数：{summary['total_lots']}",
        f"- 可见成交拍品数：{summary['sold_count']}",
        f"- 隐藏结果拍品数：{summary['hidden_result_count']}",
        f"- 撤拍拍品数：{summary['withdrawn_count']}",
        f"- 成交率：{summary['sell_through_rate']:.2%}" if summary['sell_through_rate'] is not None else '- 成交率：N/A',
    ]

    realized_totals = summary.get('total_realized_by_currency', {})
    estimate_low_totals = summary.get('estimate_total_low_by_currency', {})
    estimate_high_totals = summary.get('estimate_total_high_by_currency', {})
    for currency, amount in realized_totals.items():
        low = estimate_low_totals.get(currency)
        high = estimate_high_totals.get(currency)
        lines.append(f"- 成交总额（{currency}）：{money_display(amount, currency)}")
        if low is not None and high is not None:
            lines.append(f"- 总估价区间（{currency}）：{money_display(low, currency)} - {money_display(high, currency)}")
    if not realized_totals:
        lines.append('- 成交总额：N/A')

    counts = summary.get('estimate_position_counts', {})
    lines.append(f"- 高于估价：{counts.get('above_estimate', 0)}")
    lines.append(f"- 估价区间内：{counts.get('within_estimate', 0)}")
    lines.append(f"- 低于估价：{counts.get('below_estimate', 0)}")
    lines.append('')
    lines.append('## 拍卖列表')
    lines.append('')

    if auctions:
        lines.append('| Auction | Date | Location | Sale Total | Link |')
        lines.append('|---|---|---|---:|---|')
        for auction in auctions:
            sale_total = money_value(auction.get('sale_total'))
            sale_total_text = money_display(sale_total, auction.get('sale_total_currency')) if sale_total is not None else 'N/A'
            title = str(auction.get('title') or '').replace('|', '/').strip()
            lines.append(f"| {title} | {auction.get('end_at') or ''} | {auction.get('location') or ''} | {sale_total_text} | [查看]({auction.get('url')}) |")
    else:
        lines.append('无命中拍卖。')

    lines.extend(['', '## 品牌 / 作者分布', ''])
    for creator, count in summary.get('creators', {}).items():
        lines.append(f'- {creator}: {count}')

    lines.extend(['', '## 地点分布', ''])
    for location, count in summary.get('locations', {}).items():
        lines.append(f'- {location}: {count}')

    lines.extend(['', '## 销售类型分布', ''])
    for sales_type, count in summary.get('sales_types', {}).items():
        lines.append(f'- {sales_type}: {count}')

    lines.extend(['', '## 数据说明 / 异常说明', ''])
    if errors:
        for error in errors[:50]:
            lines.append(f"- [{error.get('level', 'warning')}] {error.get('scope', 'run')}: {error.get('message', '')}")
    else:
        lines.append('- 无记录异常。')

    lines.extend(['', '## All lots', ''])
    lines.append('| Lot | Creator | Title | Estimate | Realized | Variance% | Status | Link |')
    lines.append('|---|---|---|---|---|---|---|---|')
    for lot in lots:
        title = str(lot.get('title') or '').replace('|', '/').strip()
        estimate = f"{money_display(money_value(lot.get('estimate_low')), lot.get('currency'))} - {money_display(money_value(lot.get('estimate_high')), lot.get('currency'))}"
        realized = money_display(money_value(lot.get('final_price')), lot.get('currency')) if lot.get('final_price') is not None else 'N/A'
        lines.append(
            f"| {lot.get('lot_number') or ''} | {lot.get('creator') or ''} | {title} | {estimate} | {realized} | {pct_display(variance_pct(lot))} | {lot.get('sold_state') or ''} | [查看]({lot.get('url')}) |"
        )
    return '\n'.join(lines) + '\n'


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    data = json.loads(input_path.read_text(encoding='utf-8'))
    summary = build_summary(data)
    data['summary'] = summary
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_report(data, summary), encoding='utf-8')
    csv_path = write_csv(data, output_path)
    if args.write_summary:
        input_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'report': str(output_path), 'csv': str(csv_path), 'summary': summary}, ensure_ascii=False))


if __name__ == '__main__':
    main()
