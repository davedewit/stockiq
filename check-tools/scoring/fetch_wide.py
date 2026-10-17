"""Five years of daily prices for shares the score study has not seen (17 Oct 2026), through the site's own price function on AWS
(stockiq-price-proxy, &range=5y), so that this machine's Yahoo allowance is not used. The lists are the coordinator's.
Writes research-data/prices/<list>.json ({symbol: [[ts, o, h, l, c, v], ...]}); a symbol already fetched is skipped.
  python3 check-tools/scoring/fetch_wide.py"""
import json, os, sys, time, importlib.util, urllib.request
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'research-data', 'prices'); os.makedirs(OUT, exist_ok=True)
PROXY = 'https://dohdeb4vpu67fa2tq3ax56ls4i0rshvm.lambda-url.us-east-1.on.aws/'
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
spec = importlib.util.spec_from_file_location('coord', os.path.join(ROOT, 'lambda-sync', 'stockiq-screener-coordinator', 'lambda_function.py'))
coord = importlib.util.module_from_spec(spec); spec.loader.exec_module(coord)
LISTS = {'sp400_600': '3-2', 'ftse100': '5-ftse100', 'dax40': '5-dax40', 'cac40': '5-cac40', 'aex': '5-aex', 'smi': '5-smi',
         'nikkei225': '5-nikkei225', 'asx200': '4-200', 'tsx60': '5-tsx60', 'spy': None}

def get(sym):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(f'{PROXY}?symbol={urllib.parse.quote(sym)}&range=5y', timeout=30) as r:
                d = json.load(r)['chart']['result'][0]
            q = d['indicators']['quote'][0]; out = []
            for i, ts in enumerate(d.get('timestamp') or []):
                row = [q[k][i] for k in ('open', 'high', 'low', 'close', 'volume')]
                if None not in row[:4]: out.append([ts] + [round(x, 6) for x in row[:4]] + [row[4] or 0])
            return sym, out
        except Exception as e:
            time.sleep(2 + 3 * attempt)
    return sym, None

import urllib.parse
for name, key in LISTS.items():
    path = os.path.join(OUT, name + '.json'); have = json.load(open(path)) if os.path.exists(path) else {}
    syms = ['SPY', '^GSPC'] if key is None else [s for s in coord.STOCK_UNIVERSES[key] if s not in have]
    with ThreadPoolExecutor(max_workers=6) as pool:
        for sym, bars in pool.map(get, syms):
            if bars: have[sym] = bars
    json.dump(have, open(path, 'w'))
    print(f'{name}: {len(have)} of {len(coord.STOCK_UNIVERSES[key]) if key else 2} symbols', flush=True)
