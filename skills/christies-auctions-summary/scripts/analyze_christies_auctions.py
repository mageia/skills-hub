#!/usr/bin/env python3
"""Generate Christie's auction summary metrics and report outputs from raw JSON."""
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
    parser.add_argument('--write-summary', action='store_true', help='Update summary in raw-data.json')
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


def estimate_display(lot: dict[str, Any]) -> str:
    low = money_value(lot.get('estimate_low'))
    high = money_value(lot.get('estimate_high'))
    currency = lot.get('currency')
    if low is None or high is None:
        return 'N/A'
    currency_suffix = f' {currency}' if currency else ''
    return f'{low:,.0f} - {high:,.0f}{currency_suffix}'


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


def lot_sort_key(lot: dict[str, Any]) -> tuple[int, str]:
    lot_number = str(lot.get('lot_number') or '')
    if lot_number.isdigit():
        return int(lot_number), lot_number
    return 10**9, lot_number


def build_summary(data: dict[str, Any]) -> dict[str, Any]:
    auctions = list(data.get('auctions', []))
    lots = list(data.get('lots', []))
    valid_lots = [lot for lot in lots if not lot.get('withdrawn')]
    visible_realized_lots = [
        lot
        for lot in valid_lots
        if lot.get('result_visibility') == 'visible' and money_value(lot.get('final_price')) is not None
    ]

    realized_by_currency: dict[str, float] = defaultdict(float)
    estimate_low_by_currency: dict[str, float] = defaultdict(float)
    estimate_high_by_currency: dict[str, float] = defaultdict(float)
    sale_totals_by_currency: dict[str, float] = defaultdict(float)

    for lot in lots:
        currency = lot.get('currency') or 'UNKNOWN'
        low = money_value(lot.get('estimate_low'))
        high = money_value(lot.get('estimate_high'))
        if low is not None:
            estimate_low_by_currency[currency] += low
        if high is not None:
            estimate_high_by_currency[currency] += high

    for lot in visible_realized_lots:
        realized_by_currency[(lot.get('currency') or 'UNKNOWN')] += money_value(lot.get('final_price')) or 0.0

    for auction in auctions:
        amount = money_value(auction.get('sale_total'))
        currency = auction.get('sale_total_currency') or 'UNKNOWN'
        if amount is not None:
            sale_totals_by_currency[currency] += amount

    return {
        'auction_count': len(auctions),
        'lot_count': len(lots),
        'visible_realized_lot_count': len(visible_realized_lots),
        'hidden_result_count': sum(1 for lot in lots if lot.get('result_visibility') == 'hidden'),
        'withdrawn_count': sum(1 for lot in lots if lot.get('withdrawn')),
        'total_realized_by_currency': dict(sorted(realized_by_currency.items())),
        'estimate_total_low_by_currency': dict(sorted(estimate_low_by_currency.items())),
        'estimate_total_high_by_currency': dict(sorted(estimate_high_by_currency.items())),
        'auction_sale_totals_by_currency': dict(sorted(sale_totals_by_currency.items())),
        'estimate_position_counts': dict(Counter(estimate_position(lot) for lot in lots)),
        'creators': dict(Counter((lot.get('creator') or 'Unknown').strip() for lot in lots).most_common(20)),
        'categories': dict(Counter((auction.get('category') or data.get('query', {}).get('category') or 'Unknown').strip() for auction in auctions).most_common()),
        'locations': dict(Counter((auction.get('location') or 'Unknown').strip() for auction in auctions).most_common()),
        'sales_types': dict(Counter((auction.get('sales_type') or 'Unknown').strip() for auction in auctions).most_common()),
    }


def write_csv(data: dict[str, Any], report_path: Path) -> Path:
    csv_path = report_path.with_name('all-lots.csv')
    headers = [
        'auction_title',
        'auction_date',
        'auction_location',
        'lot_number',
        'creator',
        'title',
        'estimate_low',
        'estimate_high',
        'currency',
        'final_price',
        'variance_pct',
        'sold_state',
        'reserve_met',
        'number_of_bids',
        'category_match_method',
        'url',
    ]
    auctions_by_id = {str(auction.get('auction_id')): auction for auction in data.get('auctions', [])}
    lots = sorted(data.get('lots', []), key=lot_sort_key)

    with csv_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for lot in lots:
            auction = auctions_by_id.get(str(lot.get('auction_id')), {})
            writer.writerow(
                {
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
                }
            )
    return csv_path


def render_distribution_section(title: str, values: dict[str, int]) -> list[str]:
    lines = [f'### {title}', '']
    if not values:
        lines.append('- N/A')
        return lines
    for key, count in values.items():
        lines.append(f'- {key}: {count}')
    return lines


def render_report(data: dict[str, Any], summary: dict[str, Any]) -> str:
    query = data.get('query', {})
    auctions = list(data.get('auctions', []))
    lots = sorted(data.get('lots', []), key=lot_sort_key)
    errors = list(data.get('errors', []))
    generated_at = datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')

    lines = [
        "# Christie's Auctions Summary",
        '',
        '## 查询条件',
        '',
        f"- 日期范围：{query.get('date_from', '')} 至 {query.get('date_to', '')}",
        f"- 分类：{query.get('category', '')}",
        f'- 生成时间：{generated_at}',
        '',
        '## 核心摘要',
        '',
        f"- 拍卖场次：{summary.get('auction_count', 0)}",
        f"- 拍品总数：{summary.get('lot_count', 0)}",
        f"- 可见成交拍品数：{summary.get('visible_realized_lot_count', 0)}",
        f"- 隐藏结果拍品数：{summary.get('hidden_result_count', 0)}",
        f"- 撤拍拍品数：{summary.get('withdrawn_count', 0)}",
    ]

    realized_totals = summary.get('total_realized_by_currency', {})
    estimate_low_totals = summary.get('estimate_total_low_by_currency', {})
    estimate_high_totals = summary.get('estimate_total_high_by_currency', {})
    sale_totals = summary.get('auction_sale_totals_by_currency', {})

    if sale_totals:
        for currency, amount in sale_totals.items():
            lines.append(f'- 拍卖 Sale Total 汇总（{currency}）：{money_display(amount, currency)}')
    else:
        lines.append('- 拍卖 Sale Total 汇总：N/A')

    if realized_totals:
        for currency, amount in realized_totals.items():
            lines.append(f'- 可见成交总额（{currency}）：{money_display(amount, currency)}')
            low = estimate_low_totals.get(currency)
            high = estimate_high_totals.get(currency)
            if low is not None and high is not None:
                lines.append(f'- 总估价区间（{currency}）：{money_display(low, currency)} - {money_display(high, currency)}')
    else:
        lines.append('- 可见成交总额：N/A')

    estimate_counts = summary.get('estimate_position_counts', {})
    lines.append(f"- 高于估价：{estimate_counts.get('above_estimate', 0)}")
    lines.append(f"- 估价区间内：{estimate_counts.get('within_estimate', 0)}")
    lines.append(f"- 低于估价：{estimate_counts.get('below_estimate', 0)}")

    lines.extend(['', '## 拍卖列表', ''])
    if auctions:
        lines.append('| Auction | Date | Location | Sale Total | Link |')
        lines.append('|---|---|---|---:|---|')
        for auction in auctions:
            sale_total = money_display(money_value(auction.get('sale_total')), auction.get('sale_total_currency'))
            title = str(auction.get('title') or '').replace('|', '/').strip()
            lines.append(
                f"| {title} | {auction.get('end_at') or ''} | {auction.get('location') or ''} | {sale_total} | [查看]({auction.get('url') or ''}) |"
            )
    else:
        lines.append('无命中拍卖。')

    lines.extend(['', '## 品牌 / 作者分布', ''])
    if summary.get('creators'):
        for creator, count in summary['creators'].items():
            lines.append(f'- {creator}: {count}')
    else:
        lines.append('- N/A')

    lines.extend(['', '## 类别 / 地点 / 销售类型分布', ''])
    lines.extend(render_distribution_section('类别', summary.get('categories', {})))
    lines.extend([''])
    lines.extend(render_distribution_section('地点', summary.get('locations', {})))
    lines.extend([''])
    lines.extend(render_distribution_section('销售类型', summary.get('sales_types', {})))

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
        realized = money_display(money_value(lot.get('final_price')), lot.get('currency'))
        if money_value(lot.get('final_price')) is None:
            realized = 'N/A'
        lines.append(
            f"| {lot.get('lot_number') or ''} | {lot.get('creator') or ''} | {title} | {estimate_display(lot)} | {realized} | {pct_display(variance_pct(lot))} | {lot.get('sold_state') or ''} | [查看]({lot.get('url') or ''}) |"
        )

    return '\n'.join(lines) + '\n'


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    report_path = Path(args.output)
    data = json.loads(input_path.read_text(encoding='utf-8'))
    summary = build_summary(data)
    data['summary'] = summary

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(data, summary), encoding='utf-8')
    csv_path = write_csv(data, report_path)

    if args.write_summary:
        input_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    print(json.dumps({'report': str(report_path), 'csv': str(csv_path), 'summary': summary}, ensure_ascii=False))


if __name__ == '__main__':
    main()
