#!/usr/bin/env python3
"""Would following the strongest sectors and themes beat simply holding the S&P 500? (18 Oct 2026; the owner: "if it seems AI is
taking off or debt problems or inflation problems or oil crisis as there is now, it should also base off that".) A theme shows up
first as a whole sector moving, so the test is sector momentum: each month hold the 2 or 3 strongest of 14 sector and theme funds
(US SPDR sectors, chips SMH, gold GLD, long bonds TLT), ranked by their rise over 3, 6 or 12 months (the 12 without the last month).
0.1% is taken off every change. Against: SPY held, all 14 funds equally, and 1,000 random picks at the same dates. Two halves of
the five years, each judged on its own; price only for every side (dividends left out of all of them).
Prices: research-data/prices/sectors/<SYMBOL>.json, five years from the site's price function (fetched 18 Oct 2026; not in git).
    python3 check-tools/replay/sector_study.py
"""
import json, os, random, statistics
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'research-data', 'prices', 'sectors')
FUNDS = 'XLK XLE XLF XLV XLI XLY XLP XLU XLB XLRE XLC SMH GLD TLT'.split()
COST = 0.001

def load(s):
    r = json.load(open(os.path.join(D, s + '.json')))['chart']['result'][0]
    return dict((t, c) for t, c in zip(r['timestamp'], r['indicators']['quote'][0]['close']) if c)

px = {s: load(s) for s in FUNDS + ['SPY']}
days = sorted(set.intersection(*[set(v) for v in px.values()]))
months = days[260::21]          # a decision every 21 trading days, once a year of history exists

def ret(s, a, b): return px[s][b] / px[s][a] - 1
def mom(s, i, look, skip=0):
    j = days.index(months[i]); return px[s][days[j - skip]] / px[s][days[j - look]] - 1

def run(pick, part):
    """pick(i) -> list of funds held from months[i] to months[i+1]; part 0 / 1 = first / second half of the decisions."""
    half = len(months) // 2
    idx = range(0, half) if part == 0 else range(half, len(months) - 1)
    v, held = 1.0, set()
    for i in idx:
        now = pick(i); turnover = len(set(now) ^ held) / max(1, len(now))
        v *= 1 - COST * turnover
        v *= 1 + sum(ret(s, months[i], months[i + 1]) for s in now) / len(now)
        held = set(now)
    return v - 1

def top(look, skip, n):
    return lambda i: sorted(FUNDS, key=lambda s: -mom(s, i, look, skip))[:n]

lines = []
for part in (0, 1):
    a, b = (months[0], months[len(months) // 2]) if part == 0 else (months[len(months) // 2], months[-1])
    from datetime import datetime, timezone
    when = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime('%d %b %Y')
    spy, eq = run(lambda i: ['SPY'], part), run(lambda i: FUNDS, part)
    rnd = sorted(run(lambda i, r=random.Random(k): r.sample(FUNDS, 3), part) for k in range(1000))
    lines.append(f"\n{'First' if part == 0 else 'Second'} half: {when(a)} to {when(b)}")
    lines.append(f"  S&P 500 (SPY) held:            {spy:+7.1%}")
    lines.append(f"  all 14 funds, equal:           {eq:+7.1%}")
    lines.append(f"  3 funds at random (median):    {rnd[500]:+7.1%}")
    for name, look, skip in (('3 months', 63, 0), ('6 months', 126, 0), ('12 months less the last', 252, 21)):
        for n in (2, 3):
            r = run(top(look, skip, n), part); beat = sum(x < r for x in rnd) / 10
            lines.append(f"  top {n} by {name:<24} {r:+7.1%}   {'AHEAD of' if r > spy else 'behind'} the S&P 500 by {abs(r - spy):.1%}; random 3 did worse {beat:.0f}% of the time")
lines.append("\n12 variants tried on 14 funds; with that many tries a few look good by luck. A variant counts only if it is ahead in both halves.")
print('\n'.join(lines))

# What carried the two variants that were ahead in both halves, how deep they fell, and whether they hold without the chip fund
def detail(pick, label, funds=None):
    from collections import Counter
    v, peak, worst, held, cnt = 1.0, 1.0, 0.0, set(), Counter()
    for i in range(len(months) - 1):
        now = pick(i); cnt.update(now)
        v *= 1 - COST * len(set(now) ^ held) / len(now)
        a, b = days.index(months[i]), days.index(months[i + 1])
        for j in range(a + 1, b + 1):        # day by day inside the month, for the worst fall
            day_v = v * (1 + sum(px[s][days[j]] / px[s][days[a]] - 1 for s in now) / len(now))
            peak = max(peak, day_v); worst = min(worst, day_v / peak - 1)
        v *= 1 + sum(ret(s, months[i], months[i + 1]) for s in now) / len(now); held = set(now)
    print(f"  {label}: whole period {v - 1:+.1%}, worst fall {worst:.1%}; held most: " + ', '.join(f"{s} {n}" for s, n in cnt.most_common(5)))

def spy_worst():
    peak, worst = 0, 0
    for t in days[days.index(months[0]):days.index(months[-1]) + 1]:
        peak = max(peak, px['SPY'][t]); worst = min(worst, px['SPY'][t] / peak - 1)
    return worst
print(f"\nThe whole period: S&P 500 {px['SPY'][months[-1]] / px['SPY'][months[0]] - 1:+.1%}, worst fall {spy_worst():.1%}")
detail(top(126, 0, 3), 'top 3 by 6 months')
detail(top(252, 21, 3), 'top 3 by 12 months less the last')
FULL = FUNDS[:]; FUNDS[:] = [s for s in FULL if s != 'SMH']
print('Without the chip fund (SMH):')
for part in (0, 1):
    spy = run(lambda i: ['SPY'], part)
    print(f"  {'first' if part == 0 else 'second'} half: top 3 by 6 months {run(top(126, 0, 3), part) - spy:+.1%} against the S&P 500; top 3 by 12 less 1 {run(top(252, 21, 3), part) - spy:+.1%}")
FUNDS[:] = FULL
