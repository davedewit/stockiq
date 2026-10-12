#!/usr/bin/env python3
"""
Publishes the company figures the single-stock report needs for shares its first source does not cover.

The report function (Lambda stockiq-option-1-1-custom-analysis) gets company figures from Finnhub, which has
them for US shares only: until Oct 2026 every Australian, UK, Japanese, Canadian, European and Hong Kong share
was scored on price alone while the report said it included fundamentals. Yahoo's own summary cannot be read
from AWS (it answers "too many requests" to anything that is not a browser). But update_stock_analysis.py
already keeps Yahoo's figures for every stock on the site in .analysis_cache/info/ (refreshed weekly or monthly).
This script puts them in one small file, in the units the score uses, where the function can read it:

    s3://stockiq-dynamic-stock-lists/site-data/company_figures.json     (a private bucket)

    {"made": "2026-10-11", "count": 3333, "figures": {"BHP.AX": {"pe_ratio": 21.49, "revenue_growth": 18.3,
      "profit_margin": 16.7, "debt_to_equity": 0.505, "current_ratio": 1.885, "return_on_equity": 24.0,
      "price_to_book": 4.283, "as_of": "2026-10-05"}, ...}}

Units: growth, margin and return on equity in percent; debt to equity as a ratio (the same conversion as
to_model_fundamentals in update_stock_analysis.py; check-tools/report/report_test.py compares the two).

Usage:
    python3 publish_company_figures.py              # build the file and upload it
    python3 publish_company_figures.py --dry-run    # build it, say what would be uploaded (also DRY_RUN=true)

Run by deploy-to-s3.sh in the daily run, straight after update_stock_analysis.py. It never stops a deploy:
if the file cannot be built or sent, the report says "company figures were not available" for those shares.
It refuses to upload a file with fewer than 1,000 stocks (a broken cache must not wipe the good file).
"""
import glob
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
INFO_DIR = os.path.join(SCRIPTS_DIR, '.analysis_cache', 'info')
OUT = os.path.join(SCRIPTS_DIR, '.analysis_cache', 'company_figures.json')
BUCKET = 'stockiq-dynamic-stock-lists'
KEY = 'site-data/company_figures.json'
MAX_AGE_DAYS = 75          # figures older than this are left out (the cache refreshes monthly at the slowest)
MIN_STOCKS = 1000
FIGURES = ('pe_ratio', 'revenue_growth', 'profit_margin', 'debt_to_equity', 'current_ratio', 'return_on_equity', 'price_to_book')


def to_score_units(entry):
    """Yahoo's fields in the units the report's score uses (percent; debt to equity as a ratio)."""
    number = lambda v: v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    pct = lambda v: round(v * 100, 4) if number(v) is not None else None
    debt = number(entry.get('debt_to_equity'))
    out = {
        'pe_ratio': number(entry.get('pe_ratio')),
        'revenue_growth': pct(entry.get('revenue_growth')),
        'profit_margin': pct(entry.get('profit_margin')),
        'debt_to_equity': round(debt / 100, 6) if debt is not None else None,
        'current_ratio': number(entry.get('current_ratio')),
        'return_on_equity': pct(entry.get('return_on_equity')),
        'price_to_book': number(entry.get('price_to_book')),
    }
    return {k: (round(v, 4) if k != 'debt_to_equity' else v) for k, v in out.items() if v is not None}


def build(info_dir=INFO_DIR, now=None):
    """The file's contents from the cache: {'made', 'count', 'figures': {SYMBOL: {...figures, 'as_of'}}}"""
    now = now or datetime.now(timezone.utc)
    oldest = (now - timedelta(days=MAX_AGE_DAYS)).isoformat()
    figures = {}
    for path in sorted(glob.glob(os.path.join(info_dir, '*.json'))):
        try:
            with open(path) as f:
                entry = json.load(f)
        except (OSError, ValueError):
            continue
        fetched = entry.get('fetched') or ''
        if entry.get('failed') or not fetched or fetched < oldest:
            continue
        row = to_score_units(entry)
        if row:
            row['as_of'] = fetched[:10]
            figures[os.path.basename(path)[:-5].upper()] = row
    return {'made': now.strftime('%Y-%m-%d'), 'count': len(figures), 'figures': figures}


HISTORY_DIR = os.path.join(SCRIPTS_DIR, 'research-data', 'company-figures')
HISTORY_EVERY_DAYS = 7


def keep_history(data, now=None):
    """Keep a dated copy of the figures once a week (research-data/company-figures/, not in git). Yahoo gives only today's
    company figures, so there is no history of them to test an idea on; kept week after week, these copies become one
    (site-overview.md section 8c, "GO PLAY"). Never stops the run."""
    try:
        now = now or datetime.now(timezone.utc)
        os.makedirs(HISTORY_DIR, exist_ok=True)
        kept = sorted(f for f in os.listdir(HISTORY_DIR) if f.startswith('company_figures-') and f.endswith('.json'))
        if kept:
            last = datetime.strptime(kept[-1][len('company_figures-'):-5], '%Y-%m-%d').replace(tzinfo=timezone.utc)
            if (now - last).days < HISTORY_EVERY_DAYS:
                return None
        path = os.path.join(HISTORY_DIR, f"company_figures-{now.strftime('%Y-%m-%d')}.json")
        with open(path, 'w') as f:
            json.dump(data, f, separators=(',', ':'), sort_keys=True)
        print(f"    kept a dated copy for research ({len(kept) + 1} so far): {os.path.basename(path)}")
        return path
    except Exception as e:
        print(f"    (no dated copy kept: {type(e).__name__}: {e})")
        return None


def main():
    dry_run = '--dry-run' in sys.argv or os.environ.get('DRY_RUN') == 'true'
    data = build()
    with open(OUT, 'w') as f:
        json.dump(data, f, separators=(',', ':'), sort_keys=True)
    size = os.path.getsize(OUT)
    print(f"🏢 Company figures: {data['count']} stocks, {size // 1024} KB")
    if data['count'] < MIN_STOCKS:
        print(f"⚠️  Fewer than {MIN_STOCKS} stocks: not uploaded (the file on AWS is left as it is)")
        return 1
    keep_history(data)
    target = f"s3://{BUCKET}/{KEY}"
    if dry_run:
        print(f"    (dry run) upload: company_figures.json to {target}")
        return 0
    # The daily run is started by launchd, whose PATH does not hold Homebrew: "aws" alone was not found there on its
    # first daily run (12 Oct 2026) and nothing was published. The full path is the one deploy-to-s3.sh uses.
    aws = shutil.which('aws') or '/opt/homebrew/bin/aws'
    result = subprocess.run([aws, 's3', 'cp', OUT, target, '--content-type', 'application/json', '--only-show-errors',
                             '--profile', 'default', '--region', 'us-east-1'], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"⚠️  Company figures not uploaded: {(result.stderr or result.stdout).strip()[:200]}")
        return 1
    print(f"✅ Company figures published for the single-stock report")
    return 0


if __name__ == '__main__':
    sys.exit(main())
