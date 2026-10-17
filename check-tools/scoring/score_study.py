"""Candidate screener scores, tested on four years of saved prices (17 Oct 2026; the owner: "go ahead and look into improving it").

Reads what the replay already holds (check-tools/replay/panel.json: the live worker's score and key figures for the 101 S&P 100
shares on every trading day from 17 Oct 2022) and the saved prices, and asks of each candidate score: did the shares it ranked
highest do better over the next 5 and 20 trading days than the shares it ranked lowest, and than the list as a whole?

Honest by construction:
  - each candidate is written down here before its result is seen, with the reason to believe it;
  - judged on the first 60% of the days AND on the last 40% separately (a score that only works in one half is luck);
  - again with the seven chip / AI names that led this period left out;
  - a portfolio test: the top 10 by the score, changed weekly, 0.1% taken off each buy and sale, against an S&P 500 fund and
    against an equal amount in every share.
Limits: 101 large US shares that are today's members (flatters "buy what rose"); one mostly rising market; no company figures
over time (there is no history of them here), so a score built on them cannot be tested this way: only forward.

  python3 check-tools/scoring/score_study.py
"""
import json, os, math, statistics, datetime, bisect
HERE = os.path.dirname(os.path.abspath(__file__)); CT = os.path.dirname(HERE)
panel = json.load(open(os.path.join(CT, 'replay', 'panel.json')))
prices = json.load(open(os.path.join(CT, 'paper-test', 'data', 'prices.json')))
day = lambda ts: datetime.datetime.fromtimestamp(ts, datetime.UTC).strftime('%Y-%m-%d')
closes = {s: {day(b[0]): b[4] for b in v} for s, v in prices.items()}
opens = {s: {day(b[0]): b[1] for b in v} for s, v in prices.items()}
days = sorted(panel)
CHIPS = {'SNDK', 'MU', 'AMD', 'ANET', 'NVDA', 'PLTR', 'DELL'}
# panel row: 0 score, 1 signal, 2 RSI, 3 30-day change, 4 % above 52-week low, 5 rank, 6 one-year change, 7 90-day change,
#            8 daily range %, 9 % under 52-week high (0 at the high, negative below)

def mom12_1(r):        # the year's rise without the last month (the classic momentum measure: the last month tends to reverse)
    return ((1 + r[6] / 100) / (1 + r[3] / 100) - 1) * 100

CANDIDATES = {
    # name: (function of a row, reason written before the result)
    'live score (as it is)': (lambda r: r[0], 'the baseline'),
    'one-year rise without the last month': (mom12_1, 'momentum over 6-12 months is the best-documented price effect in shares (Jegadeesh and Titman 1993)'),
    'close to the 52-week high': (lambda r: r[9], 'shares near their year high keep rising (George and Hwang 2004); found pointing the right way in the factor study'),
    'far above the 52-week low': (lambda r: r[4], 'pointed the right way in both halves of the factor study (11 Oct 2026); lost in a 10-a-side live trial'),
    '90-day rise': (lambda r: r[7], 'medium-term momentum; looked good in the replay on the second half'),
    'one-year rise without the last month, per unit of jumpiness': (lambda r: mom12_1(r) / max(0.5, r[8]), 'momentum per unit of risk, so that it does not simply buy the jumpiest shares'),
    'blend: 12-1 rise + near the year high, ranked': (None, 'two documented momentum measures together, each as a rank so neither swamps the other'),
    'blend: live score + 12-1 rise, ranked': (None, 'keep the live score and give momentum over months its due'),
}

def ranks(vals):        # 0 = lowest, 1 = highest
    order = sorted(vals, key=lambda kv: kv[1]); n = len(order)
    return {s: i / max(1, n - 1) for i, (s, _) in enumerate(order)}

def scored(d, name, keep=lambda s: True):
    rows = {s: r for s, r in panel[d].items() if keep(s)}
    if name.startswith('blend: 12-1'):
        a, b = ranks([(s, mom12_1(r)) for s, r in rows.items()]), ranks([(s, r[9]) for s, r in rows.items()])
        return {s: a[s] + b[s] for s in rows}
    if name.startswith('blend: live'):
        a, b = ranks([(s, r[0]) for s, r in rows.items()]), ranks([(s, mom12_1(r)) for s, r in rows.items()])
        return {s: a[s] + b[s] for s in rows}
    f = CANDIDATES[name][0]
    return {s: f(r) for s, r in rows.items()}

def fwd(s, d, h):       # bought at the next day's open, valued at the close h trading days later
    i = bisect.bisect_right(days, d)
    if i + h >= len(days): return None
    o, c = opens.get(s, {}).get(days[i]), closes.get(s, {}).get(days[i + h - 1])
    return (c / o - 1) * 100 if o and c else None

def spread(name, h, part, keep):
    """Per day: average next-h-day return of the top fifth minus the bottom fifth, and top fifth minus the whole list."""
    cut = int(len(days) * 0.6); span = days[:cut] if part == 0 else days[cut:]
    span = span[::h]                                     # days h apart, so the samples do not overlap
    tb, ta = [], []
    for d in span:
        sc = scored(d, name, keep); ok = [(s, v, fwd(s, d, h)) for s, v in sc.items()]; ok = [x for x in ok if x[2] is not None]
        if len(ok) < 20: continue
        ok.sort(key=lambda x: -x[1]); k = len(ok) // 5
        top, bot, allr = [x[2] for x in ok[:k]], [x[2] for x in ok[-k:]], [x[2] for x in ok]
        tb.append(statistics.mean(top) - statistics.mean(bot)); ta.append(statistics.mean(top) - statistics.mean(allr))
    t = lambda xs: statistics.mean(xs) / (statistics.stdev(xs) / math.sqrt(len(xs))) if len(xs) > 2 and statistics.stdev(xs) > 0 else 0
    return statistics.mean(tb), t(tb), statistics.mean(ta), t(ta), len(tb)

def portfolio(name, keep, start, end, n=10, cost=0.1):
    """$100,000 in the top n, changed every 5 trading days at the next open, cost taken off each buy and sale."""
    val, held = 100000.0, {}
    span = [d for d in days if start <= d <= end]
    for i in range(0, len(span) - 5, 5):
        d = span[i]; sc = scored(d, name, keep); top = sorted(sc, key=lambda s: -sc[s])[:n]
        nd = days[bisect.bisect_right(days, d)]; ed = span[i + 5] if i + 5 < len(span) else span[-1]
        new = set(top); turnover = len(new - set(held)) / n if held else 1.0
        val *= 1 - 2 * cost / 100 * turnover
        rets = [closes[s][ed] / opens[s][nd] - 1 for s in top if opens.get(s, {}).get(nd) and closes.get(s, {}).get(ed)]
        val *= 1 + (statistics.mean(rets) if rets else 0); held = {s: 1 for s in new}
    return val

def bench(start, end, which):
    span = [d for d in days if start <= d <= end]; a = days[bisect.bisect_right(days, span[0])]; b = span[-1]
    if which == 'spy': return 100000 * closes['SPY'][b] / opens['SPY'][a]
    rs = [closes[s][b] / opens[s][a] for s in panel[span[0]] if opens.get(s, {}).get(a) and closes.get(s, {}).get(b)]
    return 100000 * statistics.mean(rs)

if __name__ == '__main__':
    cut = days[int(len(days) * 0.6)]
    print(f'{len(days)} trading days, {days[0]} to {days[-1]}; first part to {cut}, then the part that was not looked at first\n')
    print('Top fifth minus bottom fifth (and minus the whole list), average per period in percentage points, t in brackets')
    print('(t of 2 or more both times, same sign: worth taking seriously; under 1: nothing)\n')
    for keep_name, keep in (('all 101 shares', lambda s: True), ('without the seven chip / AI names', lambda s: s not in CHIPS)):
        print(f'== {keep_name}')
        for name, (_, why) in CANDIDATES.items():
            line = f'{name}\n    ({why})\n'
            for h in (5, 20):
                cells = []
                for part in (0, 1):
                    tb, ttb, ta, tta, n = spread(name, h, part, keep)
                    cells.append(f'{"first" if part == 0 else "last "}: {tb:+.2f} (t {ttb:+.1f}), vs list {ta:+.2f}')
                line += f'    {h:2d} days: ' + ' | '.join(cells) + '\n'
            print(line)
    print('== $100,000 in the top 10, changed weekly, 0.1% a trade (first part | last part)')
    for p, (a, b) in enumerate(((days[0], cut), (cut, days[-1]))):
        print(f'  {"first" if p == 0 else "last "} part {a} to {b}: S&P 500 fund ${bench(a, b, "spy"):,.0f}; an equal amount in every share ${bench(a, b, "all"):,.0f}')
    for name in CANDIDATES:
        cells = [f'${portfolio(name, lambda s: True, a, b):,.0f} / without chips ${portfolio(name, lambda s: s not in CHIPS, a, b):,.0f}' for a, b in ((days[0], cut), (cut, days[-1]))]
        print(f'  {name}: ' + ' | '.join(cells))
