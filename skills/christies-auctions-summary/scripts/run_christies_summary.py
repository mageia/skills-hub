#!/usr/bin/env python3
from __future__ import annotations

import argparse
import calendar
import json
import os
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

CATEGORY_NAMES = {
    'jewellery': 'Jewellery',
}
SUPPORTED_FORMATS = {'markdown', 'json', 'csv'}


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value)))


def run(command: list[str], env: dict[str, str] | None = None) -> None:
    completed = subprocess.run(command, text=True, env=env, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def ensure_agent_browser() -> None:
    if shutil.which('agent-browser') is not None:
        return
    bootstrap = script_dir() / 'bootstrap.sh'
    completed = subprocess.run([str(bootstrap)], text=True, check=False)
    if completed.returncode != 0 or shutil.which('agent-browser') is None:
        raise SystemExit('agent-browser is required and bootstrap installation failed')


def cdp_ready(host: str, port: int, url: str | None = None) -> bool:
    env = os.environ.copy()
    if url:
        env.update({'CDP_URL': url})
    else:
        env.update({'CDP_HOST': host, 'CDP_PORT': str(port)})
    completed = subprocess.run([str(script_dir() / 'verify_cdp_ready.sh')], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return completed.returncode == 0


def previous_week(today: date) -> tuple[str, str]:
    start = today - timedelta(days=today.weekday() + 7)
    end = start + timedelta(days=6)
    return start.isoformat(), end.isoformat()


def previous_month(today: date) -> tuple[str, str]:
    year = today.year
    month = today.month - 1
    if month == 0:
        year -= 1
        month = 12
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1).isoformat(), date(year, month, last_day).isoformat()


def normalize_dates(date_range: dict[str, Any]) -> tuple[str, str]:
    if 'preset' in date_range:
        today = date.today()
        preset = str(date_range['preset']).lower()
        if preset == 'last_week':
            return previous_week(today)
        if preset == 'last_month':
            return previous_month(today)
        raise SystemExit(f"Unsupported date_range preset: {date_range['preset']}")
    if 'from' in date_range and 'to' in date_range:
        from_date = date.fromisoformat(str(date_range['from'])).isoformat()
        to_date = date.fromisoformat(str(date_range['to'])).isoformat()
        if from_date > to_date:
            raise SystemExit('date_range.from must be <= date_range.to')
        return from_date, to_date
    raise SystemExit('date_range must contain preset or from/to')


def normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    category_key = str(config.get('category', '')).strip().lower()
    if category_key not in CATEGORY_NAMES:
        raise SystemExit(f"Unsupported category: {config.get('category')}")

    date_from, date_to = normalize_dates(config.get('date_range') or {})
    cdp = config.get('cdp') or {}
    output = config.get('output') or {}
    formats = set(output.get('format') or ['markdown', 'json', 'csv'])
    unsupported = formats - SUPPORTED_FORMATS
    if unsupported:
        raise SystemExit(f'Unsupported output formats: {sorted(unsupported)}')

    cdp_url = cdp.get('url')
    profile_dir = expand_path(cdp.get('user_data_dir', '~/.chrome-debug-profile'))
    if not cdp_url and not profile_dir.is_dir():
        raise SystemExit(f'Chrome profile directory does not exist: {profile_dir}')

    return {
        'date_from': date_from,
        'date_to': date_to,
        'category': CATEGORY_NAMES[category_key],
        'cdp': {
            'host': cdp.get('host', '127.0.0.1'),
            'port': int(cdp.get('port', 9222)),
            'url': cdp.get('url', 'http://127.0.0.1:9222'),
            'user_data_dir': str(profile_dir),
            'profile_directory': cdp.get('profile_directory', 'Default'),
            'auto_launch': bool(cdp.get('auto_launch', True)),
            'chrome_command': cdp.get('chrome_command') or '',
        },
        'output_dir': expand_path(output.get('dir', './outputs/christies-auctions-summary')),
    }


def ensure_cdp(config: dict[str, Any]) -> None:
    cdp = config['cdp']
    if cdp_ready(cdp['host'], cdp['port'], cdp.get('url')):
        return
    if cdp.get('url') and not str(cdp.get('url')).startswith('http://127.0.0.1') and not str(cdp.get('url')).startswith('http://localhost'):
        raise SystemExit('Remote CDP URL is not ready; auto-launch is only supported for local Chrome')
    if not cdp['auto_launch']:
        raise SystemExit('CDP is not ready and auto_launch=false')

    env = os.environ.copy()
    env.update({
        'CDP_PORT': str(cdp['port']),
        'USER_DATA_DIR': cdp['user_data_dir'],
        'PROFILE_DIRECTORY': cdp['profile_directory'],
        'CHROME_COMMAND': cdp.get('chrome_command') or '',
    })
    run([str(script_dir() / 'launch_cdp_chrome.sh')], env=env)
    for _ in range(10):
        if cdp_ready(cdp['host'], cdp['port'], cdp.get('url')):
            return
        subprocess.run(['sleep', '1'], check=False)
    raise SystemExit('CDP is still unavailable after Chrome launch')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, help='JSON config path')
    args = parser.parse_args()

    config = normalize_config(json.loads(Path(args.config).read_text(encoding='utf-8')))
    ensure_agent_browser()
    ensure_cdp(config)
    output_dir = config['output_dir']
    raw_path = output_dir / 'raw-data.json'
    report_path = output_dir / 'report.md'
    csv_path = output_dir / 'all-lots.csv'

    login_cmd = [sys.executable, str(script_dir() / 'verify_christies_login.py'), '--cdp-port', str(config['cdp']['port'])]
    if config['cdp'].get('url'):
        login_cmd.extend(['--cdp-url', config['cdp']['url']])
    run(login_cmd)
    run([
        sys.executable,
        str(script_dir() / 'fetch_christies_auctions.py'),
        '--cdp-port', str(config['cdp']['port']),
        *( ['--cdp-url', config['cdp']['url']] if config['cdp'].get('url') else []),
        '--category', config['category'],
        '--from-date', config['date_from'],
        '--to-date', config['date_to'],
        '--output', str(raw_path),
    ])
    run([
        sys.executable,
        str(script_dir() / 'analyze_christies_auctions.py'),
        '--input', str(raw_path),
        '--output', str(report_path),
        '--write-summary',
    ])
    print(json.dumps({'raw_data': str(raw_path), 'report': str(report_path), 'csv': str(csv_path)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
