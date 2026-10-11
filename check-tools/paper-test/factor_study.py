"""Which parts of the screener score pointed the right way? A test of every factor of the S&P 100 screener on saved prices.

The screener worker's OWN scoring code is replayed for every trading day (as backtest.py does), but instead of only the
final score this keeps each of its 12 weighted factors and the raw figures behind them, and asks of each one:
did the stocks it liked go on to do better than the stocks it disliked, over the next day, week and month?

Then two more questions the owner asked (11 Oct 2026):
  - what share of trades end up (the "win rate") under the autopilot's selling rules, and is a high share the same as profit?
  - would a differently weighted score have done better? Weights are chosen on the first half of the period and judged
    only on the second half, which the choice never saw.

Nothing here touches the live site and nothing is downloaded: it reads data/prices.json (python3 fetch.py made it).
Usage: python3 factor_study.py [first test date, default 2022-10-17] > results-factors-<date>.txt
Limits to state with any result: today's index members for the whole period (flatters every number), no dividends,
one mostly rising market, 101 large US stocks only (nothing here says anything about coins)."""
import importlib.util, io, contextlib, json, sys, bisect, datetime, os, statistics, re, glob, random
HERE = os.path.dirname(os.path.abspath(__file__))
worker_path = glob.glob('/Users/dave/VSCODE/stockiq/lambda-sync/stockiq-option-3-1-worker-*/advanced_lambda.py')[0]
start_date = sys.argv[1] if len(sys.argv) > 1 else '2022-10-17'
universe = {l.split(':')[0]: l.split(':')[1].split() for l in open(os.path.join(HERE, 'frozen_lists.txt')) if ':' in l and not l.startswith('#')}['sp100']
prices = json.load(open(os.path.join(HERE, 'data', 'prices.json')))
spec = importlib.util.spec_from_file_location('worker', worker_path); w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)

def day(ts): return datetime.datetime.fromtimestamp(ts, datetime.UTC).strftime('%Y-%m-%d')
bars = {s: [{'timestamp': b[0], 'open': b[1], 'high': b[2], 'low': b[3], 'close': b[4], 'volume': int(b[5])} for b in prices[s]] for s in universe + ['SPY'] if s in prices}
dates = {s: [day(b['timestamp']) for b in v] for s, v in bars.items()}
at = {s: {d: i for i, d in enumerate(dates[s])} for s in bars}
calendar = dates['SPY']; pos = {d: i for i, d in enumerate(calendar)}
NOW = {'d': None}
def get_stock_data(symbol, period='1y'):
    symbol = symbol.upper()
    if symbol not in bars: return None
    i = bisect.bisect_right(dates[symbol], NOW['d']); data = bars[symbol][max(0, i - 252):i]
    return data if len(data) >= 20 else None
w.get_stock_data = get_stock_data
w.check_earnings_risk = lambda symbol: 'HIGH' if int(NOW['d'][5:7]) in (1, 4, 7, 10) else 'LOW'
def no_network(*a, **k): raise RuntimeError('network call during the study')
w.urllib.request.urlopen = no_network

FACTORS = ['RSI', 'MACD', 'Short Momentum', 'Medium Momentum', 'Long Momentum', 'Volume', 'Financial', 'Bollinger', 'Sentiment', 'Market', 'Risk', 'MA Trend']
LINE = re.compile(r'^(' + '|'.join(FACTORS) + r'): (-?[\d.]+) × (\d+)% = (-?[\d.]+)')
RAW = ['rsi', 'change_24h', 'change_5d', 'change_10d', 'change_30d', 'change_90d', 'change_200d', 'change_1yr', 'price_vs_ma20', 'price_vs_ma50', 'price_vs_ma200',
       'distance_from_52w_high', 'distance_from_52w_low', 'volume_ratio', 'stoch_k', 'profit_probability']
CODES = {'STRONG_BUY': 3, 'BUY': 2, 'MODERATE_BUY': 1, 'HOLD': 0, 'MODERATE_SELL': -1, 'SELL': -2, 'STRONG_SELL': -3}

test_days = [d for d in calendar if d >= start_date]
rows = {}                                              # day -> {symbol: {'score', 'code', factor..., raw...}}
for d in test_days:
    NOW['d'] = d; out = {}
    with contextlib.redirect_stdout(io.StringIO()):
        for s in universe:
            if s not in bars or d not in at[s]: continue
            r = w.analyze_stock_advanced(s)
            if not r: continue
            row = {'score': r['score'], 'code': CODES.get(r.get('recommendation'), 0), 'atr_pct': 100 * r['atr'] / r['price'] if r.get('atr') and r.get('price') else None}
            for item in r.get('score_breakdown') or []:
                m = LINE.match(item)
                if m: row['f:' + m.group(1)] = float(m.group(4))
            for k in RAW: row[k] = r.get(k)
            out[s] = row
    rows[d] = out
days = sorted(rows)

def close(s, d, h=0):
    i = pos[d] + h
    if i >= len(calendar): return None
    j = at[s].get(calendar[i])
    return bars[s][j]['close'] if j is not None else None
def fwd(s, d, h):
    a, b = close(s, d), close(s, d, h)
    return (b / a - 1) * 100 if a and b else None
FWD = {h: {d: {s: v for s, v in ((s, fwd(s, d, h)) for s in rows[d]) if v is not None} for d in days} for h in (1, 5, 20)}
mean = statistics.mean
def tstat(xs, h):                                      # overlapping periods only count as about len/h separate ones
    if len(xs) < 3 * h + 3: return 0.0
    n = len(xs) / h; sd = statistics.stdev(xs)
    return mean(xs) / (sd / n ** 0.5) if sd else 0.0

def spread_series(key, h, sign_split):
    """For each day: what the stocks this figure liked did next, minus what the ones it disliked did (percentage points)."""
    out = []
    for d in days:
        f = FWD[h][d]; have = [(rows[d][s].get(key), f[s]) for s in f if rows[d][s].get(key) is not None]
        if len(have) < 40: continue
        if sign_split:                                 # a factor's contribution: liked = above the day's middle value, disliked = below
            mid = statistics.median(v for v, _ in have)
            hi = [r for v, r in have if v > mid + 1e-9]; lo = [r for v, r in have if v < mid - 1e-9]
            if len(hi) < 5 or len(lo) < 5: continue
        else:                                          # a raw figure: the top fifth against the bottom fifth
            have.sort(key=lambda x: x[0]); k = len(have) // 5
            lo, hi = [r for _, r in have[:k]], [r for _, r in have[-k:]]
        out.append((d, mean(hi) - mean(lo)))
    return out

half = days[len(days) // 2]
def report(key, label, sign_split):
    cells, verdicts = [], []
    for h in (1, 5, 20):
        ser = spread_series(key, h, sign_split)
        if len(ser) < 100: cells.append('        (same for all stocks)       '); continue
        xs = [x for _, x in ser]; a = [x for d, x in ser if d < half]; b = [x for d, x in ser if d >= half]
        t = tstat(xs, h); same = (mean(a) > 0) == (mean(b) > 0)
        cells.append(f"{mean(xs):+6.2f} (t {t:+4.1f}; halves {mean(a):+5.2f} / {mean(b):+5.2f})")
        verdicts.append((t, same, mean(xs)))
    clear = [v for v in verdicts if abs(v[0]) >= 2 and v[1]]
    word = 'no reliable link' if not clear else ('pointed the RIGHT way' if all(v[2] > 0 for v in clear) else 'pointed the WRONG way' if all(v[2] < 0 for v in clear) else 'mixed')
    print(f"{label:34} | {' | '.join(cells)} | {word}")
    return verdicts

print(f"===== S&P 100 screener, factor by factor: {len(universe)} stocks, {len(days)} trading days, {days[0]} to {days[-1]} =====")
print(f"stocks scored per day: min {min(len(rows[d]) for d in days)}, max {max(len(rows[d]) for d in days)}; the second half starts {half}")
print("\nEach cell: what the stocks a figure LIKED did next, minus what the ones it DISLIKED did, in percentage points;")
print("t: how clear that is (2 or more is clear, under 2 could be chance); halves: the same thing for the first and the second half of the period.")
print("A figure is called reliable only if it is clear AND has the same sign in both halves.\n")
head = f"{'':34} | {'next day':^36} | {'next week':^36} | {'next month':^36} |"
print("A. THE SCREENER'S OWN SCORE AND ITS 12 WEIGHTED FACTORS (liked = above the day's middle value)\n" + head)
report('score', 'the final score (top 5th - bottom)', False); report('code', 'the signal label', True)
factor_verdicts = {f: report('f:' + f, f + ' factor', True) for f in FACTORS}
print("\nB. THE RAW FIGURES BEHIND THEM (the top fifth of the list minus the bottom fifth; + means higher was better)\n" + head)
raw_verdicts = {k: report(k, k, False) for k in RAW + ['atr_pct']}

# ---------------------------------------------------------------- C. the share of trades that end up, under the autopilot's selling rules
def trade(s, d, stop, take, hold):
    """Bought at the next morning's open, looked at once a day at the close: sold at the loss limit, the gain mark, or after `hold` days."""
    i = at[s].get(d)
    if i is None or i + 1 >= len(bars[s]): return None
    buy = bars[s][i + 1]['open']
    if not buy: return None
    last = min(i + hold, len(bars[s]) - 1)
    if last <= i: return None
    for j in range(i + 1, last + 1):
        change = (bars[s][j]['close'] / buy - 1) * 100
        if change <= stop or change >= take or j == last: return change
RULES = [('Cautious: -5% / +8%, 20 days', -5, 8, 20), ('Balanced: -10% / +18%, 5 days', -10, 18, 5), ('Bold: -14% / +28%, 2 days', -14, 28, 2), ('Adventurous: -20% / +45%, 1 day', -20, 45, 1),
         ('a rule built to "win" often: -15% / +2%, 20 days', -15, 2, 20), ('the opposite: -2% / +15%, 20 days', -2, 15, 20)]
def picks(d, n=10):
    ok = [s for s in rows[d] if rows[d][s]['score'] > 0 and rows[d][s]['code'] > 0]
    return sorted(ok, key=lambda s: -rows[d][s]['score'])[:n]
print("\nC. HOW OFTEN A TRADE ENDS UP, AND WHAT IT MAKES (every day's top 10 by score with a positive signal, bought at the next open,")
print("   0.2% taken off each trade for costs; 'any stock' is the same rule applied to every stock of the list on every day)")
print(f"{'selling rule':52} | {'top 10: trades':>14} | {'end up':>7} | {'average':>8} | {'any stock: end up':>17} | {'average':>8} | top 10 minus any stock")
for label, stop, take, hold in RULES:
    top = [x - 0.2 for d in days for s in picks(d) for x in [trade(s, d, stop, take, hold)] if x is not None]
    anyone = [x - 0.2 for d in days for s in rows[d] for x in [trade(s, d, stop, take, hold)] if x is not None]
    per_day = [mean(t) - mean(a) for t, a in (([x for s in picks(d) for x in [trade(s, d, stop, take, hold)] if x is not None], [x for s in rows[d] for x in [trade(s, d, stop, take, hold)] if x is not None]) for d in days) if len(t) >= 5 and a]
    print(f"{label:52} | {len(top):>14,} | {100 * sum(x > 0 for x in top) / len(top):6.1f}% | {mean(top):+7.2f}% | {100 * sum(x > 0 for x in anyone) / len(anyone):16.1f}% | {mean(anyone):+7.2f}% | {mean(per_day):+.2f} (t {tstat(per_day, hold):+.1f})")

# ---------------------------------------------------------------- D. would other weights have done better? chosen on the first half, judged on the second
def zscores(d, key):
    vals = {s: rows[d][s].get(key) for s in rows[d] if rows[d][s].get(key) is not None}
    if len(vals) < 40: return {}
    m, sd = mean(vals.values()), statistics.pstdev(vals.values())
    return {s: (v - m) / sd for s, v in vals.items()} if sd else {}
first, second = [d for d in days if d < half], [d for d in days if d >= half]
def spread_on(key, h, which, sign_split=False):
    xs = [x for d, x in spread_series(key, h, sign_split) if (d < half) == (which == 'first')]
    return (mean(xs), tstat(xs, h)) if xs else (0.0, 0.0)
chosen = {}
for k in RAW + ['atr_pct']:
    m5, t5 = spread_on(k, 5, 'first')
    if abs(t5) >= 1.5: chosen[k] = 1 if m5 > 0 else -1
def composite(d):
    z = {k: zscores(d, k) for k in chosen}; out = {}
    for s in rows[d]:
        parts = [chosen[k] * z[k][s] for k in chosen if s in z[k]]
        if len(parts) == len(chosen) and parts: out[s] = sum(parts)
    return out
def top_minus_list(rank, which_days, h, n=10):
    xs = []
    for d in which_days:
        f = FWD[h][d]; r = rank(d); names = sorted((s for s in r if s in f), key=lambda s: -r[s])[:n]
        if len(names) == n and len(f) >= 40: xs.append(mean(f[s] for s in names) - mean(f.values()))
    return (mean(xs), tstat(xs, h), 100 * sum(x > 0 for x in xs) / len(xs)) if xs else (0, 0, 0)
print("\nD. WOULD OTHER WEIGHTS HAVE DONE BETTER? (the fair way: chosen on the first half, judged on the second half only)")
print("   figures that looked clear in the first half (week ahead, t of 1.5 or more) and the direction that helped: "
      + (', '.join(f"{k} ({'higher' if v > 0 else 'lower'} was better)" for k, v in chosen.items()) or 'none'))
for label, rank in (("the screener's score as it is", lambda d: {s: rows[d][s]['score'] for s in rows[d]}), ('a score re-built from those figures', composite),
                    ('long-run rise alone (change_200d)', lambda d: {s: rows[d][s]['change_200d'] for s in rows[d] if rows[d][s].get('change_200d') is not None}),
                    ('a random top 10 (the average of 20 draws)', None)):
    cells = []
    for which, ds in (('first half', first), ('SECOND half', second)):
        for h in (5, 20):
            if rank is None:
                random.seed(11); r = [top_minus_list(lambda d, k=k: {s: random.random() for s in rows[d]}, ds, h) for k in range(20)]
                cells.append(f"{which} {'week' if h == 5 else 'month'} {mean(x[0] for x in r):+.2f}")
            else:
                m_, t_, win = top_minus_list(rank, ds, h); cells.append(f"{which} {'week' if h == 5 else 'month'} {m_:+.2f} (t {t_:+.1f})")
    print(f"   {label:42} top 10 minus the whole list: " + ' | '.join(cells))
print("\nRead the SECOND half columns: that is the only part the re-built score was not fitted to.")

# ---------------------------------------------------------------- E. is that a real edge, or just "the wildest stocks rose most in a rising market"?
print("\nE. THREE CHECKS ON THE RE-BUILT SCORE BEFORE BELIEVING IT")
AI_CHIPS = {'SNDK', 'MU', 'AMD', 'ANET', 'NVDA', 'PLTR', 'DELL'}       # the seven names that carried the S&P 100 result in section 11 of the notes
def top_vs_list(rank, which_days, h, leave_out=(), n=10):
    tops, lists = [], []
    for d in which_days:
        f = {s: v for s, v in FWD[h][d].items() if s not in leave_out}; r = rank(d); names = sorted((s for s in r if s in f), key=lambda s: -r[s])[:n]
        if len(names) == n and len(f) >= 40: tops.append(mean(f[s] for s in names)); lists.append(mean(f.values()))
    return tops, lists
for label, out in (('all 101 stocks', ()), ('without the seven chip / AI names', AI_CHIPS)):
    cells = []
    for which, ds in (('first half', first), ('second half', second)):
        t, l = top_vs_list(composite, ds, 5, out); xs = [a - b for a, b in zip(t, l)]
        cells.append(f"{which}: {mean(xs):+.2f} a week (t {tstat(xs, 5):+.1f})")
    print(f"   1. {label:36} top 10 minus the list, a week ahead: " + ' | '.join(cells))
t, l = top_vs_list(composite, days, 5); up = [(a, b) for a, b in zip(t, l) if b > 0]; down = [(a, b) for a, b in zip(t, l) if b <= 0]
print(f"   2. In the {len(up)} weeks the whole list ROSE: its top 10 {mean(a for a, b in up):+.2f}%, the list {mean(b for a, b in up):+.2f}%. "
      f"In the {len(down)} weeks the list FELL: its top 10 {mean(a for a, b in down):+.2f}%, the list {mean(b for a, b in down):+.2f}%.")
print(f"      Its top 10 moved {mean(a for a, b in up) / mean(b for a, b in up):.1f} times as far as the list in rising weeks and {mean(a for a, b in down) / mean(b for a, b in down):.1f} times as far in falling weeks: "
      "above 1 in both means it is partly just more risk.")
worst = lambda xs: min(xs)
print(f"      Worst single week: its top 10 {worst(t):+.1f}%, the list {worst(l):+.1f}%. Worst month: its top 10 {worst(top_vs_list(composite, days, 20)[0]):+.1f}%, the list {worst(top_vs_list(composite, days, 20)[1]):+.1f}%.")
def within_calm_and_wild(key, h):
    xs = []
    for d in days:
        f = FWD[h][d]; have = [(rows[d][s]['atr_pct'], rows[d][s].get(key), f[s]) for s in f if rows[d][s].get('atr_pct') is not None and rows[d][s].get(key) is not None]
        if len(have) < 60: continue
        have.sort(key=lambda x: x[0]); k = len(have) // 3; parts = []
        for group in (have[:k], have[k:2 * k], have[2 * k:]):
            group = sorted(group, key=lambda x: x[1]); q = max(3, len(group) // 5); parts.append(mean(x[2] for x in group[-q:]) - mean(x[2] for x in group[:q]))
        xs.append((d, mean(parts)))
    return xs
for key in ('distance_from_52w_low', 'change_1yr', 'score'):
    cells = []
    for h in (5, 20):
        ser = within_calm_and_wild(key, h); xs = [x for _, x in ser]; a = [x for d, x in ser if d < half]; b = [x for d, x in ser if d >= half]
        cells.append(f"{'week' if h == 5 else 'month'} {mean(xs):+.2f} (t {tstat(xs, h):+.1f}; halves {mean(a):+.2f} / {mean(b):+.2f})")
    print(f"   3. {key:22} comparing only stocks that are about equally jumpy (top fifth minus bottom fifth inside each third by how much they move): " + ' | '.join(cells))

