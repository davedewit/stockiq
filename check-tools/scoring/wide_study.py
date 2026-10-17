"""The candidate scores on shares the first study never saw (17 Oct 2026): US mid and small caps (S&P 400 + 600) and the UK, German,
French, Dutch, Swiss, Japanese, Australian and Canadian indexes, five years of daily prices (fetch_wide.py).

Fixed BEFORE the result was seen (written down here on 17 Oct 2026, after score_study.py on the S&P 100):
  live      the share screeners' score exactly as the workers compute it today (workers/stock_worker.py, run on each day's prices)
  low52     how far the price stands above its 52-week low (%)                       best in score_study.py, both halves
  mom12_1   the year's rise without the last month (%)                                 the textbook momentum measure
  trend     a per-share score (each worker scores its shares alone, so it cannot rank them against each other):
              min(2, above-low / 50) + clip(12-1 rise / 40, -1.5, 1.5) + 0.5 if above its 200-day average else -0.5
              + 0.5 if the 50-day average is above the 200-day else -0.5, and -0.5 when RSI is over 80
What is measured, each list on its own and all together, on the first half of the days and the second half separately:
  each week (every 5th trading day), the top tenth by the score against the whole list over the next 5 and 20 trading days
  (bought at the next day's open); and $100,000 in the top 10 of each list, changed weekly, 0.1% off each buy and sale,
  against the same money spread over the whole list.
Limits: today's members (flatters buying what rose, more so for small companies); no company figures over time.
  python3 check-tools/scoring/wide_study.py
"""
import json, os, sys, io, math, bisect, statistics, datetime, contextlib, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, 'research-data', 'prices')
day = lambda ts: datetime.datetime.fromtimestamp(ts, datetime.UTC).strftime('%Y-%m-%d')
spec = importlib.util.spec_from_file_location('worker', os.path.join(ROOT, 'workers', 'stock_worker.py'))
worker = importlib.util.module_from_spec(spec); spec.loader.exec_module(worker)
spy = json.load(open(os.path.join(DATA, 'spy.json')))['SPY']

def study(name):
    raw = json.load(open(os.path.join(DATA, name + '.json')))
    bars = {s: [{'timestamp': b[0], 'open': b[1], 'high': b[2], 'low': b[3], 'close': b[4], 'volume': int(b[5] or 0)} for b in v] for s, v in raw.items() if len(v) > 300}
    bars['SPY'] = [{'timestamp': b[0], 'open': b[1], 'high': b[2], 'low': b[3], 'close': b[4], 'volume': int(b[5] or 0)} for b in spy]
    dates = {s: [day(b['timestamp']) for b in v] for s, v in bars.items()}
    cal = sorted({d for s, ds in dates.items() if s != 'SPY' for d in ds})
    cal = [d for d in cal if sum(1 for s in bars if s != 'SPY' and d in dates[s]) > 0.6 * (len(bars) - 1)]
    now = {'d': None}
    def get_stock_data(symbol, period='1y'):
        symbol = symbol.upper()
        if symbol not in bars: return None
        i = bisect.bisect_right(dates[symbol], now['d']); data = bars[symbol][max(0, i - 252):i]
        return data if len(data) >= 20 else None
    worker.get_stock_data = get_stock_data
    worker.check_earnings_risk = lambda symbol: 'HIGH' if int(now['d'][5:7]) in (1, 4, 7, 10) else 'LOW'
    def price_on(s, d, field):         # the bar on day d or, if none, None
        i = bisect.bisect_left(dates[s], d)
        return bars[s][i][field] if i < len(dates[s]) and dates[s][i] == d else None
    test_days = cal[260::5]
    rows = {}
    for n, d in enumerate(test_days):
        now['d'] = d; market = None
        with contextlib.redirect_stdout(io.StringIO()):
            market = worker.get_market_context()
            out = {}
            for s in bars:
                if s == 'SPY' or d not in set(dates[s][-1300:]): continue
                r = worker.analyze_stock_advanced(s, market)
                if not r: continue
                hist = get_stock_data(s); cl = [b['close'] for b in hist]
                ma200 = sum(cl[-200:]) / min(200, len(cl)); ma50 = sum(cl[-50:]) / min(50, len(cl))
                m = ((1 + r['change_1yr'] / 100) / (1 + r['change_30d'] / 100) - 1) * 100
                low = r['distance_from_52w_low']
                trend = min(2, max(0, low) / 50) + max(-1.5, min(1.5, m / 40)) + (0.5 if cl[-1] > ma200 else -0.5) + (0.5 if ma50 > ma200 else -0.5) - (0.5 if r['rsi'] > 80 else 0)
                out[s] = {'live': r['score'], 'low52': low, 'mom12_1': m, 'trend': trend}
        rows[d] = out
    # next-period returns, bought at the next trading day's open
    def fwd(s, d, h):
        i = bisect.bisect_right(cal, d)
        if i + h - 1 >= len(cal): return None
        o, c = price_on(s, cal[i], 'open'), price_on(s, cal[i + h - 1], 'close')
        return (c / o - 1) * 100 if o and c and o > 0 else None
    return rows, fwd, test_days

def tstat(xs):
    return statistics.mean(xs) / (statistics.stdev(xs) / math.sqrt(len(xs))) if len(xs) > 2 and statistics.stdev(xs) > 0 else 0

def summary(name, rows, fwd, test_days, keys=('live', 'low52', 'mom12_1', 'trend')):
    half = len(test_days) // 2; res = {}
    for k in keys:
        res[k] = {}
        for h in (5, 20):
            for part, span in (('first', test_days[:half]), ('second', test_days[half:])):
                ex = []
                for d in span[::max(1, h // 5)]:
                    sc = [(s, v[k], fwd(s, d, h)) for s, v in rows[d].items()]; sc = [x for x in sc if x[2] is not None]
                    if len(sc) < 20: continue
                    sc.sort(key=lambda x: -x[1]); top = [x[2] for x in sc[:max(2, len(sc) // 10)]]
                    ex.append(statistics.mean(top) - statistics.mean(x[2] for x in sc))
                res[k][(h, part)] = (statistics.mean(ex) if ex else 0, tstat(ex), len(ex))
        for part, span in (('first', test_days[:half]), ('second', test_days[half:])):
            val, ref, held = 100000.0, 100000.0, set()
            for d in span:
                sc = [(s, v[k], fwd(s, d, 5)) for s, v in rows[d].items()]; sc = [x for x in sc if x[2] is not None]
                if len(sc) < 20: continue
                sc.sort(key=lambda x: -x[1]); top = sc[:10]; new = {x[0] for x in top}
                turn = len(new - held) / 10 if held else 1.0
                val *= (1 - 2 * 0.001 * turn) * (1 + statistics.mean(x[2] for x in top) / 100)
                ref *= 1 + statistics.mean(x[2] for x in sc) / 100; held = new
            res[k][('money', part)] = (val, ref)
    return res

if __name__ == '__main__':
    names = [n[:-5] for n in sorted(os.listdir(DATA)) if n.endswith('.json') and n != 'spy.json']
    allres = {}
    for name in names:
        rows, fwd, td = study(name)
        if not td: continue
        r = summary(name, rows, fwd, td); allres[name] = r
        print(f'== {name}: {len(next(iter(rows.values())))} shares, {len(td)} weeks from {td[0]} to {td[-1]}')
        for k in r:
            cells = '; '.join(f'{h}d {p}: {r[k][(h, p)][0]:+.2f} (t {r[k][(h, p)][1]:+.1f})' for h in (5, 20) for p in ('first', 'second'))
            m = r[k][('money', 'first')], r[k][('money', 'second')]
            print(f'  {k:8s} top tenth vs the list: {cells}\n           top 10 changed weekly, after costs: first half ${m[0][0]:,.0f} vs the list ${m[0][1]:,.0f}; second half ${m[1][0]:,.0f} vs ${m[1][1]:,.0f}')
        print(flush=True)
    print('== how often each score beat its own list (top 10, after costs), out of', 2 * len(allres), 'half-periods')
    for k in ('live', 'low52', 'mom12_1', 'trend'):
        wins = sum(1 for r in allres.values() for p in ('first', 'second') if r[k][('money', p)][0] > r[k][('money', p)][1])
        lead = statistics.mean((r[k][('money', p)][0] / r[k][('money', p)][1] - 1) * 100 for r in allres.values() for p in ('first', 'second'))
        print(f'  {k:8s} {wins} of {2 * len(allres)}; average lead {lead:+.1f}% a half-period')
