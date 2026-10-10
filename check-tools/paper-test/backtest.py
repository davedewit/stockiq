"""Fake-money test of a screener: replay the screener worker's OWN scoring code over daily prices.
For every trading day from the start date: score every stock in the list using only prices up to that day,
take the top 10, then see what those 10 did afterwards compared with the whole list and with the S&P 500 (SPY).
Also runs a ,000 paper account that re-invests in the top 10 every week.
The screeners use only daily price and volume, so this reproduces exactly what the live screener would have
shown at each day's close (checked on 10 Oct 2026: the replay's top 10 matched the live Dow 30 report).
Usage: python3 fetch.py && python3 backtest.py <dow30|sp100> [first test date YYYY-MM-DD, default 2023-01-01]
Fair forward test: use a start date on or after the date in frozen_lists.txt."""
import importlib.util, io, contextlib, json, sys, bisect, datetime, pickle, os, statistics, time
HERE = os.path.dirname(os.path.abspath(__file__)); MIRROR = '/Users/dave/VSCODE/stockiq/lambda-sync/'
import glob
WORKERS = {'dow30': 'stockiq-option-3-8-worker-*/lambda_function.py', 'sp100': 'stockiq-option-3-1-worker-*/advanced_lambda.py'}
name = sys.argv[1]; worker_path = glob.glob(MIRROR + WORKERS[name])[0]
start_date = sys.argv[2] if len(sys.argv) > 2 else '2023-01-01'
universe = {l.split(':')[0]: l.split(':')[1].split() for l in open(os.path.join(HERE, 'frozen_lists.txt')) if ':' in l and not l.startswith('#')}[name]
os.chdir(os.path.join(HERE, 'data')); prices = json.load(open('prices.json'))
spec = importlib.util.spec_from_file_location('worker', worker_path); w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)

def day(ts): return datetime.datetime.fromtimestamp(ts, datetime.UTC).strftime('%Y-%m-%d')
bars = {s: [{'timestamp': b[0], 'open': b[1], 'high': b[2], 'low': b[3], 'close': b[4], 'volume': int(b[5])} for b in prices[s]] for s in universe + ['SPY'] if s in prices}
dates = {s: [day(b['timestamp']) for b in v] for s, v in bars.items()}
close_on = {s: dict(zip(dates[s], [b['close'] for b in bars[s]])) for s in bars}
calendar = dates['SPY']

NOW = {'d': None}
def get_stock_data(symbol, period='1y'):          # same shape as the worker's own function, but only up to the simulated day
    symbol = symbol.upper()
    if symbol not in bars: return None
    i = bisect.bisect_right(dates[symbol], NOW['d'])
    data = bars[symbol][max(0, i - 252):i]
    return data if len(data) >= 20 else None
def check_earnings_risk(symbol):
    return 'HIGH' if int(NOW['d'][5:7]) in (1, 4, 7, 10) else 'LOW'
w.get_stock_data = get_stock_data; w.check_earnings_risk = check_earnings_risk
def no_network(*a, **k): raise RuntimeError('network call during backtest')
w.urllib.request.urlopen = no_network

if True:
    scores = {}; t0 = time.time(); test_days = [d for d in calendar if d >= start_date]
    for n, d in enumerate(test_days):
        NOW['d'] = d; row = {}
        with contextlib.redirect_stdout(io.StringIO()):
            for s in universe:
                if s not in bars or d not in close_on[s]: continue
                r = w.analyze_stock_advanced(s)
                if r: row[s] = (r['score'], r.get('recommendation'))
        scores[d] = row
        if n % 100 == 0: print(f'  scored {n}/{len(test_days)} days ({time.time() - t0:.0f}s)', file=sys.stderr, flush=True)

pos = {d: i for i, d in enumerate(calendar)}
def fwd(s, d, h):
    i = pos[d] + h
    if i >= len(calendar): return None
    a, b = close_on[s].get(d), close_on[s].get(calendar[i])
    return (b / a - 1) * 100 if a and b else None
order = {s: i for i, s in enumerate(universe)}
def ranked(d): return sorted(scores[d], key=lambda s: (-scores[d][s][0], order[s]))
days = sorted(scores)
print(f'\n===== {name.upper()}: {len(universe)} stocks, {len(days)} trading days tested, {days[0]} to {days[-1]} =====')
print(f'stocks scored per day: min {min(len(scores[d]) for d in days)}, max {max(len(scores[d]) for d in days)}')
res = {}
for h, label in ((1, '1 day'), (5, '1 week'), (20, '1 month'), (60, '3 months')):
    top, bot, allm, spy, diff = [], [], [], [], []
    for d in days:
        r = ranked(d)
        if len(r) < 20: continue
        f = {s: fwd(s, d, h) for s in r}; f = {s: v for s, v in f.items() if v is not None}; sp = fwd('SPY', d, h)
        t = [f[s] for s in r[:10] if s in f]; b = [f[s] for s in r[-10:] if s in f]
        if len(t) < 8 or sp is None: continue
        top.append(statistics.mean(t)); bot.append(statistics.mean(b)); allm.append(statistics.mean(f.values())); spy.append(sp); diff.append(top[-1] - allm[-1])
    if len(diff) < 2 * h + 2: continue
    n_sep = len(diff) / h                                # overlapping periods only count as about this many separate ones
    se = statistics.stdev(diff) / n_sep ** 0.5
    res[label] = dict(days=len(top), top10=statistics.mean(top), all=statistics.mean(allm), bottom10=statistics.mean(bot), spy=statistics.mean(spy),
                      edge=statistics.mean(diff), margin=1.96 * se, win=100 * sum(x > 0 for x in diff) / len(diff))
    r_ = res[label]
    verdict = 'no reliable difference' if abs(r_['edge']) < r_['margin'] else ('top 10 ahead' if r_['edge'] > 0 else 'top 10 behind')
    print(f"{label:9} later: top 10 {r_['top10']:+.2f}% | whole list {r_['all']:+.2f}% | bottom 10 {r_['bottom10']:+.2f}% | SPY {r_['spy']:+.2f}% || top 10 minus list {r_['edge']:+.2f}% (margin of error ±{r_['margin']:.2f}): {verdict}")

def portfolio(pick, every=5, cost=0.0):
    """$10,000, re-invested equally into the picked stocks every `every` trading days at the close. cost = % lost on each $ traded."""
    value, hold, curve, turnover = 10000.0, {}, [], 0.0
    for n, d in enumerate(days):
        if hold:
            value = sum(v * (close_on[s].get(d, close_on[s].get(prev)) / close_on[s].get(prev)) if close_on[s].get(prev) else v for s, v in hold.items())
            hold = {s: v * (close_on[s].get(d, close_on[s].get(prev)) / close_on[s].get(prev)) if close_on[s].get(prev) else v for s, v in hold.items()}
        if n % every == 0:
            picks = pick(d)
            target = {s: value / len(picks) for s in picks}
            traded = sum(abs(target.get(s, 0) - hold.get(s, 0)) for s in set(target) | set(hold))
            turnover += traded / value; value -= traded * cost / 100
            hold = {s: value / len(picks) for s in picks}
        prev = d; curve.append(value)
    return curve, turnover
def stats(curve):
    peak, dd = curve[0], 0
    for v in curve: peak = max(peak, v); dd = min(dd, v / peak - 1)
    yrs = len(curve) / 252
    return curve[-1], ((curve[-1] / 10000) ** (1 / yrs) - 1) * 100, dd * 100
spy_curve = [10000 * close_on['SPY'][d] / close_on['SPY'][days[0]] for d in days]
print(f'\nPaper portfolio, $10,000 at {days[0]}, re-balanced weekly (ending {days[-1]}):')
out = {}
for label, pick, cost in (('Screener top 10, no costs', lambda d: ranked(d)[:10], 0), ('Screener top 10, 0.1% cost per trade', lambda d: ranked(d)[:10], 0.1),
                          ('Whole list, equal amounts', lambda d: ranked(d), 0), ('Screener bottom 10', lambda d: ranked(d)[-10:], 0)):
    c, to = portfolio(pick, 5, cost); end, cagr, dd = stats(c); out[label] = c
    print(f'  {label:38} ${end:>9,.0f}   {cagr:+6.1f}% a year   worst fall {dd:.0f}%   traded {to / (len(days) / 252):.0f}x the account per year')
end, cagr, dd = stats(spy_curve); print(f"  {'S&P 500 fund (SPY), buy and hold':38} ${end:>9,.0f}   {cagr:+6.1f}% a year   worst fall {dd:.0f}%")
by_year = {}
for i, d in enumerate(days): by_year.setdefault(d[:4], []).append(i)
print('  by calendar year (top 10 / whole list / SPY):', '  '.join(f"{y}: {100 * (out['Screener top 10, no costs'][ix[-1]] / out['Screener top 10, no costs'][ix[0]] - 1):+.0f}% / {100 * (out['Whole list, equal amounts'][ix[-1]] / out['Whole list, equal amounts'][ix[0]] - 1):+.0f}% / {100 * (spy_curve[ix[-1]] / spy_curve[ix[0]] - 1):+.0f}%" for y, ix in sorted(by_year.items())))
import collections
codes = collections.Counter(c for d in days for s, (sc, c) in scores[d].items()); print('signal codes over the whole period:', dict(codes.most_common()))
json.dump({'name': name, 'days': days, 'curves': {**out, 'SPY': spy_curve}, 'horizons': res}, open(f'result_{name}.json', 'w'))
print('top 10 at the last close (' + days[-1] + '):', ', '.join(f'{s} {scores[days[-1]][s][0]:+.1f}' for s in ranked(days[-1])[:10]))
print('No trading costs unless stated; prices are daily closes without dividends; past results only.')
