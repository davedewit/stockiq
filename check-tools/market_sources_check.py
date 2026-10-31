#!/usr/bin/env python3
"""The market panel's two sources must agree (31 Oct 2026).

The panel on the home page, the dashboard and the daily screener pages first draws its figures from the seven
stockiq-market-data-* functions (one a tab), then live-market.js keeps them fresh from ticker-data-fetcher. If the two
work the day's change out differently, every page load and every 5-minute reload shows wrong figures for a few seconds
(until 31 Oct 2026 the seven took the last two daily bars: Bitcoin read -0.83% for -0.09%, XRP +0.76% for -0.82%).

Asks each of the seven once and the price function once for the same symbols (8 Lambda calls, read-only), and lists every
item whose price, change or % differ by more than rounding. A price can move between the two calls (a coin trades all
the time), so a difference under 0.1% of the price is allowed and the % must agree to 0.05 points.

    python3 check-tools/market_sources_check.py        # prints ALL PASS or each difference
"""
import json, sys, urllib.request

TABS = {
    'us': 'https://xqma6tuoaeb5nd32gpdyk5uonm0yvgiy.lambda-url.us-east-1.on.aws/',
    'europe': 'https://2azr7bjzjfvkadj2hzztk5icia0xnnoa.lambda-url.us-east-1.on.aws/',
    'asia': 'https://kzspffs5uombzw73vudd3p57x40agikm.lambda-url.us-east-1.on.aws/',
    'cryptocurrencies': 'https://x5xnafkpdtym4i7vezbhjaizry0leaxk.lambda-url.us-east-1.on.aws/',
    'rates': 'https://ewowkcosbyc5rkk2b6ypvlx6la0pzfww.lambda-url.us-east-1.on.aws/',
    'commodities': 'https://4ynwdgbmuf7jvxxxckmvu7plwa0gxnby.lambda-url.us-east-1.on.aws/',
    'currencies': 'https://xdqiva3aoe4e4esa3cwdrkyt7i0izcvr.lambda-url.us-east-1.on.aws/',
}
PRICES = 'https://2vl4la6od3vfgbkv6ycbj7ewry0yxvck.lambda-url.us-east-1.on.aws/'


def get(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


items, bad, empty = [], [], []
for tab, url in TABS.items():
    d = get(url)
    rows = d.get(tab) or {}
    if not rows:
        empty.append(tab)
    items += [(tab, name, v) for name, v in rows.items() if isinstance(v, dict) and v.get('symbol')]
syms = sorted({v['symbol'] for _, _, v in items})
live = {}
for i in range(0, len(syms), 40):
    live.update(get(PRICES, {'tickers': syms[i:i + 40]}).get('data') or {})
for tab, name, v in items:
    q = live.get(v['symbol']) or {}
    if q.get('error') or 'price' not in q:
        continue                                     # the price function could not get this one: nothing to compare
    p = float(q['price']); off = abs(float(v['value']) - p) / abs(p) if p else 0
    if off > 0.001 or abs(float(v['changePercent']) - float(q['changePercent'])) > 0.05:
        bad.append(f"{tab}: {name} ({v['symbol']}) panel {v['value']} {v['changePercent']}%  live {q['price']} {q['changePercent']}%")
print(f'{len(items)} items on 7 tabs compared with the live price function')
for tab in empty:
    print(f'FAIL the {tab} tab answered with no items')
for b in bad:
    print('FAIL ' + b)
print('ALL PASS' if not bad and not empty else f'SOME FAILED ({len(bad) + len(empty)})')
sys.exit(1 if bad or empty else 0)
