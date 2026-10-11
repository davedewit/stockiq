"""What does a change to the share-screener worker do to its figures? The same saved prices through the copy that is live
and through workers/stock_worker.py, and every figure that differs.

    python3 workers/prove.py --fetch     # once: two years of daily prices for a small sample of each market (48 downloads, slowly)
    python3 workers/prove.py             # the comparison (no downloads; about two minutes)
    python3 workers/prove.py --old DIR   # compare with the code files in DIR instead of the mirror (lambda-sync/)

"The copy that is live" is the one copy per worker group that lambda-sync/ keeps (refresh it with sync-all-lambdas.sh).
Each distinct copy is run on the stocks its screeners see: US copies on the S&P 100 and Dow 30 stocks of
check-tools/paper-test/data/prices.json (run check-tools/paper-test/fetch.py if it is missing) and a few NASDAQ-only
names; the ASX / Nikkei copy on Australian and Japanese shares; the FTSE copy on London shares.

Both copies are fed through their own price-reading code: the web call is replaced by a stand-in that answers in Yahoo's
own format, for every fifth trading day, with the prices each would have had that day. Nothing live is called.

How to read it: for each live copy it first puts that copy's own RSI into the new file. What still differs then is every
other difference between the two, and should be explainable line by line. Then, with the new file as it is, how far
scores, signals and each day's top 10 move.
"""
import sys, os, json, glob, io, ast, contextlib, importlib.util, datetime, hashlib, collections, statistics, time, urllib.request, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
US_PRICES = os.path.join(ROOT, 'check-tools', 'paper-test', 'data', 'prices.json')
SAMPLE = os.path.join(HERE, 'data', 'sample.json')
EVERY = 5                                   # every fifth trading day
SAMPLES = {
    'asx': 'BHP.AX CBA.AX CSL.AX NAB.AX WBC.AX ANZ.AX WES.AX MQG.AX WOW.AX TLS.AX RIO.AX FMG.AX'.split(),
    'london': 'IMB.L AZN.L HSBA.L SHEL.L ULVR.L BP.L GSK.L RIO.L LLOY.L BARC.L VOD.L BT-A.L'.split(),
    'tokyo': '7203.T 6758.T 9984.T 8306.T 6861.T 9432.T 7974.T 6501.T 8035.T 4063.T 6098.T 9983.T'.split(),
    'nasdaq': 'CRWD ZS DDOG MSTR TEAM LULU MELI PDD ASML ARM CSX KHC'.split(),
}
GROUPS = ['stockiq-option-3-1-worker', 'stockiq-option-3-2-worker', 'stockiq-option-3-4-worker', 'stockiq-option-3-5-worker', 'stockiq-option-3-6-worker',
          'stockiq-option-3-7-worker', 'stockiq-option-3-8-worker', 'stockiq-asia-5-1-worker', 'stockiq-asia-5-2-worker', 'stockiq-asia-5-3-worker',
          'stockiq-asia-5-4-worker', 'stockiq-asia-5-5-worker', 'stockiq-europe-4-1-worker']
SEES = {'stockiq-asia-5-1-worker': ['asx'], 'stockiq-asia-5-2-worker': ['asx'], 'stockiq-asia-5-3-worker': ['asx'], 'stockiq-asia-5-4-worker': ['asx'],
        'stockiq-asia-5-5-worker': ['tokyo'], 'stockiq-europe-4-1-worker': ['london']}          # every other group: US shares
CODES = ['STRONG_SELL', 'SELL', 'MODERATE_SELL', 'HOLD', 'MODERATE_BUY', 'BUY', 'STRONG_BUY']

def fetch():
    os.makedirs(os.path.dirname(SAMPLE), exist_ok=True)
    have = json.load(open(SAMPLE)) if os.path.exists(SAMPLE) else {}
    for symbol in [s for v in SAMPLES.values() for s in v]:
        if symbol in have: continue
        req = urllib.request.Request(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=2y&interval=1d&includePrePost=false", headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        try:
            have[symbol] = json.loads(urllib.request.urlopen(req, timeout=20).read())['chart']['result'][0]
            print(symbol, len(have[symbol]['timestamp']), 'days')
        except Exception as e:
            print(symbol, 'NOT FETCHED:', e)
            if '429' in str(e): print('Yahoo is refusing this machine: stop, and try again in an hour'); break
        json.dump(have, open(SAMPLE, 'w')); time.sleep(2)

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); mod = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(mod)
    return mod

def functions(path):
    """Each function of a file, as its syntax tree with the comments and docstrings left out"""
    out = {}
    for node in ast.parse(open(path).read()).body:
        if isinstance(node, ast.FunctionDef):
            for sub in ast.walk(node):
                if isinstance(sub, (ast.FunctionDef, ast.Module)) and sub.body and isinstance(sub.body[0], ast.Expr) and isinstance(getattr(sub.body[0], 'value', None), ast.Constant) and isinstance(sub.body[0].value.value, str):
                    sub.body = sub.body[1:] or [ast.Pass()]
            out[node.name] = ast.dump(node)
    return out

# ---- the prices, and the stand-in for the web call ----
day = lambda ts: datetime.datetime.fromtimestamp(ts, datetime.UTC).strftime('%Y-%m-%d')
def us_charts():
    prices = json.load(open(US_PRICES))
    return {s: {'meta': {'currency': 'USD', 'gmtoffset': -14400}, 'timestamp': [b[0] for b in rows],
                'indicators': {'quote': [{k: [b[i + 1] for b in rows] for i, k in enumerate(['open', 'high', 'low', 'close', 'volume'])}]}} for s, rows in prices.items()}

def cut(chart, until, real_end=False):
    """The chart as Yahoo would have sent it at `until` (a time): the year before it. On the last day of a downloaded chart the
    answer is left exactly as Yahoo sent it (a session sent twice, the quote that came with it)."""
    ts = chart['timestamp']; q = chart['indicators']['quote'][0]
    keep = [i for i, t in enumerate(ts) if until - 365 * 86400 <= t <= until]
    if not keep: return None
    meta = dict(chart['meta'])
    if not real_end:
        days_seen = set(); once = []
        for i in keep:                                           # a past day: one bar a day, as the series was then
            d = (ts[i] + (meta.get('gmtoffset') or 0)) // 86400
            if d not in days_seen: days_seen.add(d); once.append(i)
        keep = once
        last = max((i for i in keep if q['close'][i] is not None), default=keep[-1])
        meta.update(regularMarketPrice=q['close'][last], regularMarketTime=ts[last], regularMarketDayHigh=q['high'][last], regularMarketDayLow=q['low'][last], regularMarketVolume=q['volume'][last])
    return {'meta': meta, 'timestamp': [ts[i] for i in keep], 'indicators': {'quote': [{k: [q[k][i] for i in keep] for k in ('open', 'high', 'low', 'close', 'volume')}]}}

class Answer:
    def __init__(self, body): self.body = body
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def getcode(self): return 200
    def read(self): return self.body

class Feed:
    """Stands in for urllib.request.urlopen: answers a chart request from the saved prices, as at self.until"""
    def __init__(self, charts): self.charts = charts; self.until = 0; self.real_end = set(); self.calls = collections.Counter(); self.cache = {}
    def at(self, until, real_end=()): self.until = until; self.real_end = set(real_end); self.cache = {}
    def __call__(self, req, timeout=None):
        url = req.full_url if hasattr(req, 'full_url') else req
        symbol = urllib.parse.unquote(url.split('/chart/')[1].split('?')[0]); self.calls[symbol] += 1
        if symbol not in self.cache:
            chart = self.charts.get(symbol)
            result = cut(chart, self.until, symbol in self.real_end) if chart else None
            self.cache[symbol] = json.dumps({'chart': {'result': [result] if result else None}}).encode()
        return Answer(self.cache[symbol])

def run(mod, symbols, month):
    mod.check_earnings_risk = lambda symbol: 'HIGH' if month in (1, 4, 7, 10) else 'LOW'
    out = {}
    with contextlib.redirect_stdout(io.StringIO()):
        for s in symbols:
            r = mod.analyze_stock_advanced(s)
            if r: out[s] = r
    return out

def compare(label, old, new, symbols, days, feed, real_end_day=None):
    """Run both over the days; return the rows that differ and the figures for the summary"""
    fields = collections.Counter(); same = total = 0; moves = []; flips = collections.Counter(); overlap = []; missing = collections.Counter(); examples = {}
    for when in days:
        feed.at(when, symbols if when == real_end_day else ()); month = int(day(when)[5:7])
        a = run(old, symbols, month); feed.cache = {}; b = run(new, symbols, month)
        for s in symbols:
            if (s in a) != (s in b): missing['only the live copy answers' if s in a else 'only the new file answers'] += 1; continue
            if s not in a: continue
            total += 1; diff = [k for k in set(a[s]) | set(b[s]) if a[s].get(k) != b[s].get(k) and k != 'currency']
            if not diff: same += 1
            for k in diff:
                fields[k] += 1
                if k not in examples: examples[k] = f"{s} {day(when)}: {a[s].get(k)!r} -> {b[s].get(k)!r}"[:230]
            moves.append(b[s]['score'] - a[s]['score'])
            if a[s]['recommendation'] != b[s]['recommendation']: flips[CODES.index(b[s]['recommendation']) - CODES.index(a[s]['recommendation'])] += 1
        both = [s for s in symbols if s in a and s in b]
        if len(both) >= 30:
            top = lambda r: {s for s, _ in sorted(((s, r[s]['score']) for s in both), key=lambda x: -x[1])[:10]}
            overlap.append(len(top(a) & top(b)))
    return {'label': label, 'total': total, 'same': same, 'fields': fields, 'moves': moves, 'flips': flips, 'overlap': overlap, 'missing': missing, 'examples': examples}

def report(r, detail=True):
    print(f"   {r['total']:,} stock-days; identical in every figure: {r['same']:,} ({100 * r['same'] / max(1, r['total']):.1f}%)" + (f"; {dict(r['missing'])}" if r['missing'] else ''))
    if r['fields']:
        print('   figures that differ, and on how many stock-days: ' + ', '.join(f"{k} {n:,}" for k, n in r['fields'].most_common()))
        if detail:
            for k, n in r['fields'].most_common(6): print(f"      e.g. {k}: {r['examples'][k]}")
    m = [abs(x) for x in r['moves']]
    if any(m):
        print(f"   score (it runs from about -2 to +3): unchanged on {100 * sum(1 for x in m if x < 0.05) / len(m):.0f}% of stock-days; moved by 0.5 or more on {100 * sum(1 for x in m if x >= 0.5) / len(m):.1f}%; "
              f"average move {statistics.mean(m):.2f}, largest {max(m):.1f}; average direction {statistics.mean(r['moves']):+.3f}")
        n = sum(r['flips'].values())
        print(f"   signal label: changed on {100 * n / len(m):.1f}% of stock-days ({', '.join(f'{k:+d} step: {v:,}' for k, v in sorted(r['flips'].items()))})")
        if r['overlap']: print(f"   each day's top 10: {statistics.mean(r['overlap']):.1f} of 10 the same on average (fewest {min(r['overlap'])})")

def main():
    if '--fetch' in sys.argv: return fetch()
    old_dir = sys.argv[sys.argv.index('--old') + 1] if '--old' in sys.argv else os.path.join(ROOT, 'lambda-sync')
    new_path = os.path.join(HERE, 'stock_worker.py')
    copies = collections.OrderedDict()                       # fingerprint of the code -> (path, [groups])
    for g in GROUPS:
        dirs = sorted(glob.glob(os.path.join(old_dir, g + '-*')))
        files = [f for d in dirs for f in glob.glob(os.path.join(d, 'stock_worker.py'))] or sorted((f for d in dirs for f in glob.glob(os.path.join(d, '*.py'))), key=os.path.getsize)[-1:]
        if not files: print(f"(no copy of {g} in {old_dir})"); continue
        h = hashlib.sha256(open(files[0], 'rb').read()).hexdigest()[:12]
        copies.setdefault(h, (files[0], []))[1].append(g)
    print(f"the new file: workers/stock_worker.py {hashlib.sha256(open(new_path, 'rb').read()).hexdigest()[:12]}")
    print(f"the live copies ({old_dir}): {len(copies)} different files for {sum(len(v[1]) for v in copies.values())} groups\n")

    new_functions = functions(new_path)
    charts = us_charts(); sample = json.load(open(SAMPLE)) if os.path.exists(SAMPLE) else {}
    charts.update(sample)
    if not sample: print('(no sample of other markets: run  python3 workers/prove.py --fetch  first; only US shares are compared)\n')
    feed = Feed(charts); real_open = urllib.request.urlopen; urllib.request.urlopen = feed
    try:
        new = load('new_worker', new_path); new_rsi = new.calculate_rsi
        us = sorted(s for s in json.load(open(US_PRICES)) if s != 'SPY') + [s for s in SAMPLES['nasdaq'] if s in sample]
        spy = charts['SPY']['timestamp']
        us_days = [t for t in spy if day(t) >= '2022-10-17'][::EVERY]
        seen_analysis = {}
        for h, (path, groups) in copies.items():
            names = ', '.join(g.replace('stockiq-', '') for g in groups)
            print(f"== {names}\n   live copy {h} ({os.path.relpath(path, ROOT)})")
            if h == hashlib.sha256(open(new_path, 'rb').read()).hexdigest()[:12]: print('   is the new file itself: nothing to compare\n'); continue
            old_functions = functions(path)
            changed = sorted(n for n in set(old_functions) | set(new_functions) if old_functions.get(n) != new_functions.get(n))
            print('   functions whose code differs from the new file: ' + ', '.join(n + ('' if n in old_functions and n in new_functions else ' (only in the live copy)' if n in old_functions else ' (new)') for n in changed))
            key = tuple(sorted((n, v) for n, v in old_functions.items() if n not in ('handle_batch_processing', 'lambda_handler', 'export_to_csv')))
            markets = SEES.get(groups[0], ['us']) if len({tuple(SEES.get(g, ['us'])) for g in groups}) == 1 else sorted({m for g in groups for m in SEES.get(g, ['us'])})
            if key in seen_analysis and seen_analysis[key][1] == markets:
                print(f"   its scoring code is the same, function for function, as the copy of {seen_analysis[key][0]}: the figures above apply\n"); continue
            seen_analysis[key] = (names, markets)
            old = load('old_' + h, path)
            for market in markets:
                if market == 'us': symbols, days, end = us, us_days, None
                else:
                    symbols = [s for s in SAMPLES[market] if s in sample]
                    if not symbols: continue
                    ts = sample[symbols[0]]['timestamp']; end = max(sample[s]['timestamp'][-1] for s in symbols)
                    days = [t + 12 * 3600 for t in ts[len(ts) // 2:-2][::EVERY]] + [end]          # the second year, then the last answer as Yahoo sent it
                print(f"   -- on {len(symbols)} {market.upper() if market == 'us' else market.capitalize()} shares, {len(days)} days ({day(days[0])} to {day(days[-1])})")
                new.calculate_rsi = old.calculate_rsi
                print("   with this copy's own RSI put into the new file (what else differs):")
                report(compare(names, old, new, symbols, days, feed, end))
                new.calculate_rsi = new_rsi
                if functions(path).get('calculate_rsi') != new_functions['calculate_rsi']:
                    print('   the new file as it is (with the one RSI for every screener):')
                    report(compare(names, old, new, symbols, days, feed, end), detail=False)
            print()

        # ---- the faults the new file fixes, each shown on a real answer ----
        print('== the faults')
        base = load('old_base', copies[next(h for h, v in copies.items() if 'stockiq-asia-5-1-worker' in v[1])][0]) if any('stockiq-asia-5-1-worker' in v[1] for v in copies.values()) else None
        for market in ('asx', 'tokyo', 'london'):
            symbols = [s for s in SAMPLES[market] if s in sample]
            if not symbols or not base: continue
            end = max(sample[s]['timestamp'][-1] for s in symbols); feed.at(end, symbols)
            twice = [s for s in symbols if len({(t + sample[s]['meta'].get('gmtoffset', 0)) // 86400 for t in sample[s]['timestamp'][-2:]}) == 1]
            a = run(base, symbols, 10); feed.cache = {}; b = run(new, symbols, 10)
            print(f"   {market.capitalize()}, the answer as Yahoo sent it on {day(end)}: last session sent twice for {len(twice)} of {len(symbols)}; 24-hour change of exactly 0: live copy {sum(1 for s in a if a[s]['change_24h'] == 0)}, new file {sum(1 for s in b if b[s]['change_24h'] == 0)}; "
                  f"currency the new file reports: {sorted({b[s]['currency'] for s in b})}")
        london = [s for s in SAMPLES['london'] if s in sample]
        if london and base:
            end = max(sample[s]['timestamp'][-1] for s in london); feed.at(end, london)
            truth = {s: sample[s]['indicators']['quote'][0]['close'][-1] for s in london}; before = {s: sample[s]['indicators']['quote'][0]['close'][-2] for s in london}
            emptied = {}
            for s in london:                                         # the latest session with empty figures, as seen on 10 Oct 2026
                c = json.loads(json.dumps(sample[s])); q = c['indicators']['quote'][0]
                for k in q: q[k][-1] = None
                emptied[s] = c
            feed.charts = dict(charts, **emptied); feed.cache = {}
            a = run(base, london, 10); feed.cache = {}; b = run(new, london, 10); feed.charts = charts
            print(f"   London with the latest session's figures emptied (as seen on 10 Oct): price is the latest session's in {sum(1 for s in b if abs(b[s]['price'] - truth[s]) < 0.01)} of {len(b)} with the new file, "
                  f"{sum(1 for s in a if abs(a[s]['price'] - truth[s]) < 0.01)} of {len(a)} with the live copy (the rest show the session before)")
        # ---- the batch: lists, empty batches, one SPY call ----
        class Ctx:
            def __init__(self, name): self.function_name = name
        feed.at(spy[-1]); feed.calls.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            r1 = new.handle_batch_processing({'worker_id': 1, 'batch_size': 10}, Ctx('stockiq-option-3-5-worker-1'))
            r88 = new.handle_batch_processing({'worker_id': 88}, Ctx('stockiq-option-3-5-worker-88')); r89 = new.handle_batch_processing({'worker_id': 89}, Ctx('stockiq-option-3-5-worker-89'))
            r2000 = new.handle_batch_processing({'worker_id': 183}, Ctx('stockiq-option-3-6-worker-183'))
            none = [new.handle_batch_processing({'worker_id': 1}, Ctx(g + '-1'))['stocks_processed'] for g in GROUPS if g not in ('stockiq-option-3-5-worker', 'stockiq-option-3-6-worker')]
            empty = new.handle_batch_processing({'worker_id': 1, 'stock_batch': []}, Ctx('stockiq-option-3-5-worker-1'))
            feed.calls.clear(); ten = new.handle_batch_processing({'worker_id': 1, 'stock_batch': us[:10]}, Ctx('stockiq-option-3-1-worker-1')); spy_calls = feed.calls['SPY']
            http = json.loads(new.lambda_handler({'body': json.dumps({'stock_batch': us[:3], 'worker_id': 7})}, Ctx('stockiq-option-3-8-worker-1'))['body'])
        lists = {l.split(':')[0]: l.split(':')[1].split() for l in open(os.path.join(HERE, 'lists.txt'))}
        print(f"   a Russell 1000 worker called with its number only takes its own ten: worker 1 {r1['stocks_processed']} (the list's first ten: {new.own_batch('stockiq-option-3-5-worker', 1) == lists['stockiq-option-3-5-worker'][:10]}), "
              f"worker 88 {r88['stocks_processed']}, worker 89 {r89['stocks_processed']}; Russell 2000 worker 183 {r2000['stocks_processed']}")
        print(f"   any other group called with a number only processes: {sorted(set(none))} stocks; a Russell worker sent an empty batch: {empty['stocks_processed']}")
        print(f"   a batch of ten: {ten['stocks_analyzed']} analysed, SPY fetched {spy_calls} time(s); through the web address: success {http.get('success')}, {http.get('stocks_analyzed')} analysed, worker_id {http.get('worker_id')}")
    finally:
        urllib.request.urlopen = real_open

if __name__ == '__main__':
    main()
