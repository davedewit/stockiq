#!/usr/bin/env python3
"""
Add a daily data snapshot and 0-100 score to each stock page, and decide which
pages Google should index.

This script:
1. Downloads 1 year of daily prices for every symbol in stocks.txt (yfinance, batched)
2. Reads fundamentals and share counts from a local cache (yfinance .info, capped per
   run): refreshed weekly for stocks near or above the index threshold, monthly otherwise
3. Works out each market cap in USD daily (cached shares x today's price x FX rate)
4. For stocks with market cap >= $10B: scores them with the same 0-100 model as the
   app's single-stock report (stock_metrics.py, copied from the Lambda), writes the
   snapshot between <!-- ANALYSIS_SECTION_START/END -->, updates the meta description
   and sets robots to "index, follow"
5. For all other stocks: empties the snapshot section and sets robots to "noindex, follow"
5. Writes indexable_stocks.txt (used by update_sitemap.py)

Pages are only written when their content changes.

Usage:
    python3 update_stock_analysis.py                 # All stocks (daily run)
    python3 update_stock_analysis.py AAPL 7203.T     # Only these symbols
    python3 update_stock_analysis.py --max-info 0    # No cap on fundamentals refreshes (first fill)
    python3 update_stock_analysis.py --dry-run       # Compute and report, write nothing

Input:  /Users/dave/VSCODE/website/stocks.txt
Output: /Users/dave/VSCODE/website/stocks/*.html
        /Users/dave/VSCODE/stockiq/indexable_stocks.txt
Cache:  /Users/dave/VSCODE/stockiq/.analysis_cache/
"""

import argparse
import csv
import html
import json
import math
import os
import re
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

warnings.filterwarnings("ignore")

import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stock_metrics import compute_analysis, score_label

WEBSITE_DIR = '/Users/dave/VSCODE/website'
STOCKS_FILE = os.path.join(WEBSITE_DIR, 'stocks.txt')
STOCKS_DIR = os.path.join(WEBSITE_DIR, 'stocks')
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
INDEXABLE_FILE = os.path.join(SCRIPTS_DIR, 'indexable_stocks.txt')
CACHE_DIR = os.path.join(SCRIPTS_DIR, '.analysis_cache')
INFO_DIR = os.path.join(CACHE_DIR, 'info')

INDEX_MIN_MARKET_CAP_USD = 10e9
INFO_MAX_AGE_DAYS = 7           # stocks near or above the index threshold
INFO_MAX_AGE_SMALL_DAYS = 30    # everything else (only needed to spot threshold crossings)
NEAR_THRESHOLD_USD = 5e9
DEFAULT_MAX_INFO = 600          # fundamentals refreshes per daily run (~2s each)
MIN_PRICE_ROWS = 50             # need enough history for 50-day average and MACD
STALE_BLOCK_DAYS = 10           # drop a snapshot whose data is older than this
PRICE_BATCH = 150

# Yahoo quotes some markets in minor units; prices are divided by 100 for display
# and market cap. Yahoo's marketCap itself is already in the major unit.
MINOR_UNITS = {'GBp': 'GBP', 'GBX': 'GBP', 'ZAc': 'ZAR', 'ZAC': 'ZAR', 'ILA': 'ILS'}

START = '<!-- ANALYSIS_SECTION_START -->'
END = '<!-- ANALYSIS_SECTION_END -->'


def load_stocks():
    """Load symbols, names and sectors from stocks.txt (csv handles quoted names)."""
    stocks = []
    with open(STOCKS_FILE, 'r') as f:
        for row in csv.reader(f):
            if len(row) >= 3:
                stocks.append({'symbol': row[0].strip(), 'name': row[1].strip(), 'sector': row[2].strip()})
    return stocks


def clean(v):
    """Return a float, or None for missing/NaN values."""
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) or math.isinf(v) else v


# ---------- Fundamentals cache ----------

def info_path(symbol):
    return os.path.join(INFO_DIR, f"{symbol}.json")


def read_info(symbol):
    try:
        with open(info_path(symbol)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def info_is_stale(entry):
    if not entry:
        return True
    fetched = datetime.fromisoformat(entry['fetched'])
    if entry.get('failed'):
        max_age = timedelta(days=1)
    elif (entry.get('last_mcap_usd') or 0) >= NEAR_THRESHOLD_USD or entry.get('last_mcap_usd') is None:
        max_age = timedelta(days=INFO_MAX_AGE_DAYS)
    else:
        max_age = timedelta(days=INFO_MAX_AGE_SMALL_DAYS)
    return datetime.now(timezone.utc) - fetched > max_age


def fetch_info(symbol):
    """Fetch the fields we use from yfinance .info and cache them."""
    i = yf.Ticker(symbol).info or {}
    entry = {
        'fetched': datetime.now(timezone.utc).isoformat(),
        'failed': False,
        'currency': i.get('currency'),
        'shares': clean(i.get('sharesOutstanding')),
        'market_cap': clean(i.get('marketCap')),
        'pe_ratio': clean(i.get('trailingPE')),
        'profit_margin': clean(i.get('profitMargins')),
        'revenue_growth': clean(i.get('revenueGrowth')),
        'debt_to_equity': clean(i.get('debtToEquity')),
        'current_ratio': clean(i.get('currentRatio')),
        'return_on_equity': clean(i.get('returnOnEquity')),
        'price_to_book': clean(i.get('priceToBook')),
    }
    previous = read_info(symbol) or {}
    if previous.get('last_mcap_usd') is not None:
        entry['last_mcap_usd'] = previous['last_mcap_usd']
    with open(info_path(symbol), 'w') as f:
        json.dump(entry, f)
    return entry


def refresh_info(symbols, max_fetch):
    """Refresh stale fundamentals, oldest first, up to max_fetch (0 = no limit)."""
    stale = [s for s in symbols if info_is_stale(read_info(s))]
    stale.sort(key=lambda s: (read_info(s) or {}).get('fetched', ''))
    if max_fetch:
        stale = stale[:max_fetch]
    if not stale:
        print("✅ Fundamentals cache is up to date")
        return
    print(f"📥 Refreshing fundamentals for {len(stale)} symbols...")
    done = failed = 0
    rate_limited = False
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(fetch_info, s): s for s in stale}
        for fut in as_completed(futures):
            try:
                fut.result()
                done += 1
            except Exception as e:
                failed += 1
                if 'Rate' in type(e).__name__ or 'Too Many Requests' in str(e):
                    rate_limited = True
                else:
                    # Remember the failure (e.g. delisted symbol) so it is retried tomorrow, not every run
                    previous = read_info(futures[fut]) or {}
                    previous.update({'fetched': datetime.now(timezone.utc).isoformat(), 'failed': True})
                    with open(info_path(futures[fut]), 'w') as f:
                        json.dump(previous, f)
            if (done + failed) % 200 == 0:
                print(f"   {done + failed}/{len(stale)}...")
            if rate_limited:
                print("⚠️  Yahoo rate limit hit - stopping fundamentals refresh (the rest will retry next run)")
                for f in futures:
                    f.cancel()
                break
    print(f"   Fundamentals: {done} refreshed, {failed} failed")


def to_model_fundamentals(entry):
    """Convert Yahoo fields to the units the Lambda's Finnhub data uses (percent, D/E ratio)."""
    if not entry:
        return {}
    pct = lambda v: v * 100 if v is not None else None
    return {
        'pe_ratio': entry.get('pe_ratio'),
        'revenue_growth': pct(entry.get('revenue_growth')),
        'profit_margin': pct(entry.get('profit_margin')),
        'debt_to_equity': entry['debt_to_equity'] / 100 if entry.get('debt_to_equity') is not None else None,
        'current_ratio': entry.get('current_ratio'),
        'return_on_equity': pct(entry.get('return_on_equity')),
        'price_to_book': entry.get('price_to_book'),
    }


# ---------- Prices and FX ----------

def download_prices(symbols):
    """Return {symbol: (dates, closes, highs, lows, volumes)} for 1 year of daily bars."""
    out = {}
    for i in range(0, len(symbols), PRICE_BATCH):
        batch = symbols[i:i + PRICE_BATCH]
        try:
            data = yf.download(batch, period='1y', interval='1d', group_by='ticker',
                               auto_adjust=False, progress=False, threads=True)
        except Exception as e:
            print(f"⚠️  Price download failed for batch {i // PRICE_BATCH + 1}: {str(e)[:80]}")
            continue
        for s in batch:
            try:
                df = data[s] if s in data.columns.get_level_values(0) else None
            except Exception:
                df = None
            if df is None:
                continue
            df = df.dropna(subset=['Close', 'High', 'Low'])
            if len(df) < MIN_PRICE_ROWS:
                continue
            out[s] = (
                df.index[-1].date(),
                [float(x) for x in df['Close']],
                [float(x) for x in df['High']],
                [float(x) for x in df['Low']],
                [0.0 if math.isnan(x) else float(x) for x in df['Volume']],
            )
        print(f"   Prices: {min(i + PRICE_BATCH, len(symbols))}/{len(symbols)} symbols requested, {len(out)} usable")
    return out


def load_fx(currencies):
    """Return {currency: USD rate} for major-unit currencies, cached per day."""
    today = datetime.now().strftime('%Y-%m-%d')
    path = os.path.join(CACHE_DIR, f"fx_{today}.json")
    rates = {'USD': 1.0}
    if os.path.exists(path):
        with open(path) as f:
            rates.update(json.load(f))
    needed = sorted(c for c in currencies if c and c not in rates)
    for c in needed:
        try:
            df = yf.download(f"{c}USD=X", period='5d', interval='1d', auto_adjust=False, progress=False)
            closes = df['Close'].dropna()
            if len(closes):
                rates[c] = float(closes.iloc[-1].iloc[0] if hasattr(closes.iloc[-1], 'iloc') else closes.iloc[-1])
        except Exception as e:
            print(f"⚠️  FX rate for {c} unavailable: {str(e)[:60]}")
    with open(path, 'w') as f:
        json.dump({k: v for k, v in rates.items() if k != 'USD'}, f)
    for old in os.listdir(CACHE_DIR):
        if old.startswith('fx_') and old != os.path.basename(path):
            os.remove(os.path.join(CACHE_DIR, old))
    return rates


def usd_market_cap(entry, price, rates):
    """Market cap in USD: shares x latest price (major unit) x FX; falls back to cached marketCap."""
    if not entry or not entry.get('currency'):
        return None
    cur = entry['currency']
    major = MINOR_UNITS.get(cur, cur)
    rate = rates.get(major)
    if rate is None:
        return None
    if entry.get('shares') and price:
        price_major = price / 100 if cur in MINOR_UNITS else price
        return entry['shares'] * price_major * rate
    if entry.get('market_cap'):
        return entry['market_cap'] * rate
    return None


# ---------- Rendering ----------

def fmt_num(v, decimals=2):
    return f"{v:,.{decimals}f}"


def fmt_usd_big(v):
    if v >= 1e12:
        return f"${v / 1e12:.2f}T"
    if v >= 1e9:
        return f"${v / 1e9:.1f}B"
    return f"${v / 1e6:.0f}M"


def display_currency(cur):
    return {'GBp': 'GBX', 'ZAc': 'ZAc', 'ILA': 'ILA'}.get(cur, cur or '')


def breakdown_line(text):
    """Drop the app's trailing advice wording, e.g. 'RSI Oversold: +15 (Strong buy signal)' -> 'RSI Oversold: +15'."""
    text = text.replace('% YTD)', '% over 1 year)')  # the model's "YTD" figure is a 1-year change
    return re.sub(r'\s*\([^()]*\)\s*$', '', text) if re.search(r':\s*[+-]\d+\s*\(', text) else text


def render_block(stock, a, entry, mcap_usd, asof):
    sym = html.escape(stock['symbol'])
    name = html.escape(stock['name'])
    cur = display_currency(entry.get('currency') if entry else '')
    label = score_label(a['score'])
    asof_text = asof.strftime('%-d %b %Y')

    def row(label_, value):
        return (f'<div style="padding: 12px; background: var(--bg-secondary); border-radius: 8px;">'
                f'<div style="font-size: 0.8em; color: var(--text-secondary);">{label_}</div>'
                f'<div style="font-weight: 600; color: var(--text-primary);">{value}</div></div>')

    rows = [
        row('Last close', f"{fmt_num(a['price'])} {cur} ({a['pct_change']:+.2f}%)"),
        row('52-week range', f"{fmt_num(a['year_low'])} &ndash; {fmt_num(a['year_high'])}"),
        row('Position in range', f"{a['range_position']:.0f}%"),
        row('1-year change', f"{a['year_change']:+.1f}%"),
    ]
    if mcap_usd:
        rows.append(row('Market cap (USD)', fmt_usd_big(mcap_usd)))
    if entry and entry.get('pe_ratio'):
        rows.append(row('P/E (trailing)', fmt_num(entry['pe_ratio'], 1)))
    if a['rsi'] is not None:
        rows.append(row('RSI (14-day)', f"{a['rsi']:.0f}"))
    if a['ma200']:
        rel = (a['price'] - a['ma200']) / a['ma200'] * 100
        rows.append(row('vs 200-day average', f"{rel:+.1f}%"))
    if a['macd_bullish'] is not None:
        rows.append(row('MACD', 'Above signal line' if a['macd_bullish'] else 'Below signal line'))

    # Plain-English summary built from the numbers
    parts = [f"{name} scores {a['score']:.0f}/100 on StockIQ's model, which reads as {label.lower()} signals overall."]
    trend = []
    if a['ma200']:
        trend.append(f"{'above' if a['price'] > a['ma200'] else 'below'} its 200-day average")
    trend.append(f"at {a['range_position']:.0f}% of its 52-week range")
    parts.append(f"The price is {' and '.join(trend)}, {'up' if a['year_change'] >= 0 else 'down'} {abs(a['year_change']):.1f}% over the past year.")
    fm = to_model_fundamentals(entry)
    facts = []
    if fm.get('profit_margin') is not None:
        facts.append(f"a profit margin of {fm['profit_margin']:.1f}%")
    if fm.get('return_on_equity') is not None:
        facts.append(f"return on equity of {fm['return_on_equity']:.1f}%")
    if fm.get('revenue_growth') is not None:
        facts.append(f"revenue growth of {fm['revenue_growth']:+.1f}%")
    if facts:
        parts.append(f"Latest reported figures show {', '.join(facts[:-1]) + ' and ' + facts[-1] if len(facts) > 1 else facts[0]}.")
    summary = ' '.join(parts)

    drivers = ''.join(f'<li style="padding: 4px 0;">{html.escape(breakdown_line(b))}</li>' for b in a['breakdown'])

    return f'''{START}
        <section class="stock-snapshot" data-asof="{asof.isoformat()}" style="background: var(--card-bg); border-radius: 12px; padding: 30px; margin-bottom: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h2 style="margin: 0 0 5px 0;">{sym} snapshot</h2>
            <p style="margin: 0 0 20px 0; font-size: 0.9em; color: var(--text-secondary);">Data as of {asof_text} close. Updated daily.</p>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 20px;">
                {''.join(rows)}
            </div>
            <div style="border-left: 4px solid #007bff; padding: 10px 15px; margin-bottom: 15px;">
                <div style="font-size: 1.2em; font-weight: 600; color: var(--text-primary);">StockIQ score: {a['score']:.0f}/100 &middot; {label} signals</div>
                <p style="margin: 8px 0 0 0; color: var(--text-secondary);">{summary}</p>
            </div>
            <details style="margin-bottom: 15px;">
                <summary style="cursor: pointer; color: var(--text-primary);">What is driving the score</summary>
                <ul style="margin: 10px 0 0 0; color: var(--text-secondary);">{drivers}</ul>
            </details>
            <p style="margin: 0; font-size: 0.85em; color: var(--text-secondary);">Automated, general information only &ndash; not financial advice. Scores can be wrong. <a href="../about.html" style="color: #007bff;">How the score works</a></p>
        </section>
        {END}'''


def meta_description(stock, a, entry, asof):
    cur = display_currency(entry.get('currency') if entry else '')
    d = (f"{stock['name']} ({stock['symbol']}) stock: StockIQ score {a['score']:.0f}/100 "
         f"({score_label(a['score']).lower()} signals), last close {fmt_num(a['price'])} {cur}, "
         f"52-week range {fmt_num(a['year_low'])}-{fmt_num(a['year_high'])}. Updated {asof.strftime('%-d %b %Y')}.")
    return html.escape(d, quote=True)


# ---------- Page updates ----------

def set_robots(page, value):
    return re.sub(r'<meta name="robots" content="[^"]*">', f'<meta name="robots" content="{value}">', page, count=1)


def set_description(page, desc):
    page = re.sub(r'(<meta name="description" content=")[^"]*(">)', lambda m: m.group(1) + desc + m.group(2), page, count=1)
    page = re.sub(r'(<meta property="og:description" content=")[^"]*(">)', lambda m: m.group(1) + desc + m.group(2), page, count=1)
    page = re.sub(r'(<meta name="twitter:description" content=")[^"]*(">)', lambda m: m.group(1) + desc + m.group(2), page, count=1)
    return page


def set_date_modified(page, asof):
    return re.sub(r'("dateModified": ")[^"]*(")', lambda m: m.group(1) + asof.isoformat() + m.group(2), page, count=1)


def existing_block_date(page):
    m = re.search(r'class="stock-snapshot" data-asof="([0-9-]+)"', page)
    return datetime.strptime(m.group(1), '%Y-%m-%d').date() if m else None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('symbols', nargs='*')
    parser.add_argument('--max-info', type=int, default=DEFAULT_MAX_INFO)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--pages-dir', default=STOCKS_DIR, help='stock pages folder (for testing on a copy)')
    parser.add_argument('--indexable-file', default=INDEXABLE_FILE)
    args = parser.parse_args()

    os.makedirs(INFO_DIR, exist_ok=True)
    stocks = load_stocks()
    if args.symbols:
        wanted = {s.upper() for s in args.symbols}
        stocks = [s for s in stocks if s['symbol'].upper() in wanted]
        if not stocks:
            print("❌ None of those symbols are in stocks.txt")
            return
    symbols = [s['symbol'] for s in stocks]
    print(f"📊 Stock analysis for {len(symbols)} symbol(s)")

    refresh_info(symbols, args.max_info)
    prices = download_prices(symbols)
    infos = {s: read_info(s) for s in symbols}
    rates = load_fx({MINOR_UNITS.get(e['currency'], e['currency']) for e in infos.values() if e and e.get('currency')})

    indexable = set()
    if args.symbols and os.path.exists(args.indexable_file):
        with open(args.indexable_file) as f:
            indexable = {line.strip() for line in f if line.strip()} - set(symbols)

    stats = {'written': 0, 'unchanged': 0, 'no_markers': 0, 'no_data': 0, 'kept_old': 0, 'indexed': 0, 'no_mcap': 0}
    today = datetime.now().date()
    for stock in stocks:
        sym = stock['symbol']
        path = os.path.join(args.pages_dir, f"{sym}.html")
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8') as f:
            page = f.read()
        if START not in page or END not in page:
            stats['no_markers'] += 1
            continue
        new = page
        entry = infos.get(sym)

        if sym in prices:
            asof, closes, highs, lows, volumes = prices[sym]
            mcap = usd_market_cap(entry, closes[-1], rates)
            if entry is not None and not args.dry_run and entry.get('last_mcap_usd') != mcap:
                entry['last_mcap_usd'] = mcap
                with open(info_path(sym), 'w') as f:
                    json.dump(entry, f)
            if entry and entry.get('currency') and mcap is None:
                stats['no_mcap'] += 1
            index = mcap is not None and mcap >= INDEX_MIN_MARKET_CAP_USD
            if index:
                a = compute_analysis(closes, highs, lows, volumes, to_model_fundamentals(entry))
                block = render_block(stock, a, entry, mcap, asof)
                new = re.sub(re.escape(START) + r'.*?' + re.escape(END), lambda m: block, new, count=1, flags=re.S)
                new = set_description(new, meta_description(stock, a, entry, asof))
                new = set_date_modified(new, asof)
            else:
                new = re.sub(re.escape(START) + r'.*?' + re.escape(END), lambda m: f"{START}\n        {END}", new, count=1, flags=re.S)
                if 'StockIQ score' in new.split('</head>')[0]:
                    new = set_description(new, html.escape(f"{stock['name']} ({sym}) stock on StockIQ. Run a free analysis for the latest score and full breakdown.", quote=True))
        else:
            # No fresh prices today: keep a recent snapshot, drop a stale one
            old_date = existing_block_date(page)
            if old_date and (today - old_date).days <= STALE_BLOCK_DAYS:
                stats['kept_old'] += 1
                index = sym in indexable or 'content="index, follow"' in page
            else:
                stats['no_data'] += 1
                new = re.sub(re.escape(START) + r'.*?' + re.escape(END), lambda m: f"{START}\n        {END}", new, count=1, flags=re.S)
                index = False

        new = set_robots(new, 'index, follow' if index else 'noindex, follow')
        if index:
            indexable.add(sym)
            stats['indexed'] += 1
        if new != page:
            stats['written'] += 1
            if not args.dry_run:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new)
        else:
            stats['unchanged'] += 1

    if not args.dry_run:
        with open(args.indexable_file, 'w') as f:
            f.write('\n'.join(sorted(indexable)) + '\n')

    print(f"\n✅ Pages written: {stats['written']}, unchanged: {stats['unchanged']}"
          f"{' (dry run - nothing written)' if args.dry_run else ''}")
    print(f"   Indexable (market cap >= $10B): {stats['indexed']} this run, {len(indexable)} total in list")
    print(f"   No price data: {stats['no_data']}, kept yesterday's snapshot: {stats['kept_old']}, "
          f"no market cap (ETF or missing FX): {stats['no_mcap']}, missing ANALYSIS markers: {stats['no_markers']}")
    if stats['no_markers']:
        print("   ⚠️  Run generate-stock-pages.py to add ANALYSIS markers to those pages")


if __name__ == '__main__':
    main()
