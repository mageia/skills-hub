#!/usr/bin/env python3
"""Generate Sotheby's auction summary metrics and Markdown report from raw JSON."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
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


def build_summary(data: dict[str, Any]) -> dict[str, Any]:
    auctions = data.get('auctions', [])
    lots = data.get('lots', [])
    valid_lots = [lot for lot in lots if not lot.get('withdrawn')]
    sold_lots = [lot for lot in valid_lots if lot.get('sold_state') == 'sold' and money_value(lot.get('final_price')) is not None]

    totals_by_currency: dict[str, float] = defaultdict(float)
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
        'creators': dict(Counter(lot.get('creator') or 'Unknown' for lot in lots).most_common(20)),
        'locations': dict(Counter(auction.get('location') or 'Unknown' for auction in auctions).most_common()),
        'sales_types': dict(Counter(auction.get('sales_type') or 'Unknown' for auction in auctions).most_common()),
    }


def money_display(amount: float) -> str:
    return f'{amount:,.0f}'


def render_report(data: dict[str, Any], summary: dict[str, Any]) -> str:
    query = data.get('query', {})
    auctions = data.get('auctions', [])
    lots = sorted(data.get('lots', []), key=lambda lot: int(lot.get('lot_number')) if str(lot.get('lot_number', '')).isdigit() else 10**9)
    errors = data.get('errors', [])
    lines = [
        "# Sotheby's Auctions Summary",
        '',
        '## 查询条件',
        '',
        f"- 日期范围：{query.get('date_from', '')} 至 {query.get('date_to', '')}",
        f"- 分类：{query.get('category', '')}",
        '',
        '## 核心摘要',
        '',
        f"- 拍卖场次：{summary['auction_count']}",
        f"- Lot 总数：{summary['total_lots']}",
        f"- 有效 Lot 数：{summary['valid_lot_count']}",
        f"- 已成交 Lot 数：{summary['sold_count']}",
        f"- 隐藏结果 Lot 数：{summary['hidden_result_count']}",
        f"- 撤拍 Lot 数：{summary['withdrawn_count']}",
        f"- 成交率：{summary['sell_through_rate']:.2%}" if summary['sell_through_rate'] is not None else '- 成交率：N/A',
        '',
        '## 拍卖列表',
        '',
    ]

    if auctions:
        lines.append('| 拍卖 | 日期 | 地点 | Sale Total | 链接 |')
        lines.append('|---|---|---|---:|---|')
        for auction in auctions:
            sale_total = money_value(auction.get('sale_total'))
            sale_total_text = f"{money_display(sale_total)} {auction.get('sale_total_currency') or ''}" if sale_total is not None else ''
            title = str(auction.get('title') or '').replace('|', '/').strip()
            lines.append(f"| {title} | {auction.get('end_at') or ''} | {auction.get('location') or ''} | {sale_total_text} | [原始链接]({auction.get('url')}) |")
    else:
        lines.append('无命中拍卖。')

    lines.extend(['', '## 成交额（按原币种）', ''])
    totals = summary.get('total_realized_by_currency', {})
    if totals:
        lines.extend(f"- {currency}: {money_display(amount)}" for currency, amount in totals.items())
    else:
        lines.append('- 无可见成交额')

    lines.extend(['', '## 估价区间表现', ''])
    for key, value in summary.get('estimate_position_counts', {}).items():
        lines.append(f'- {key}: {value}')

    lines.extend(['', '## 品牌 / 作者分布', ''])
    for creator, count in summary.get('creators', {}).items():
        lines.append(f'- {creator}: {count}')

    lines.extend(['', '## 地点分布', ''])
    for location, count in summary.get('locations', {}).items():
        lines.append(f'- {location}: {count}')

    lines.extend(['', '## 销售类型分布', ''])
    for sales_type, count in summary.get('sales_types', {}).items():
        lines.append(f'- {sales_type}: {count}')

    lines.extend(['', '## 数据异常与缺口', ''])
    if errors:
        for error in errors[:50]:
            lines.append(f"- [{error.get('level', 'warning')}] {error.get('scope', 'run')}: {error.get('message', '')}")
    else:
        lines.append('无记录异常。')

    lines.extend(['', '## All lots', ''])
    lines.append('| Lot | Creator | Low | High | Realized | Currency | Status | Link | Title |')
    lines.append('|---|---|---:|---:|---:|---|---|---|---|')
    for lot in lots:
        title = str(lot.get('title') or '').replace('|', '/').strip()
        realized = lot.get('final_price') if lot.get('final_price') is not None else 'N/A'
        lines.append(
            f"| {lot.get('lot_number') or ''} | {lot.get('creator') or ''} | {lot.get('estimate_low') or ''} | "
            f"{lot.get('estimate_high') or ''} | {realized} | {lot.get('currency') or ''} | {lot.get('sold_state') or ''} | "
            f"[原始链接]({lot.get('url')}) | {title} |"
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
    if args.write_summary:
        input_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'report': str(output_path), 'summary': summary}, ensure_ascii=False))


if __name__ == '__main__':
    main()
