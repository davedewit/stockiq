"""What would following the screener have done? Uses scores.pkl (replay.py) and the same daily closes."""
import pickle, json, glob, os, math, statistics as st, datetime as dt, sys
from replay import load, DATA, CAL
load()
P = pickle.load(open('scores.pkl', 'rb')); scores = P['scores']; universe = P['universe']; order = {s: i for i, s in enumerate(universe)}
days = sorted(scores); idx = {d: i for i, d in enumerate(CAL)}
close = {s: {r['day']: r['close'] for r in rows} for s, rows in DATA.items()}
def fwd(sym, day, h):
    i = idx[day] + h
    if i >= len(CAL): return None
    a = close[sym].get(day); b = close[sym].get(CAL[i])
    return (b / a - 1) if a and b else None
def mean(x): return sum(x) / len(x) if x else float('nan')
def ranked(day): return sorted(scores[day], key=lambda s: (-scores[day][s][0], order[s]))     # ties: list order
out = {}
print(f'Period replayed: {days[0]} to {days[-1]} ({len(days)} trading days), {len(universe)} stocks')
ties = [sum(1 for s in scores[d] if scores[d][s][0] == scores[d][ranked(d)[9]][0]) for d in days]
print(f'Stocks sharing the 10th-place score on a typical day: median {st.median(ties):.0f}')

print('\n1. AVERAGE PRICE CHANGE AFTER A STOCK IS RANKED (all days, percent)')
print(f"{'group':34} {'next day':>9} {'1 week':>9} {'1 month':>9}")
groups = {'Top 10 by score': lambda r: r[:10], 'Top 50 by score': lambda r: r[:50], 'Bottom 50 by score': lambda r: r[-50:], 'Bottom 10 by score': lambda r: r[-10:], 'All ~500 stocks (average stock)': lambda r: r}
series = {g: {h: [] for h in (1, 5, 21)} for g in groups}; spy = {h: [] for h in (1, 5, 21)}; used = {h: [] for h in (1, 5, 21)}
for d in days:
    r = ranked(d)
    for h in (1, 5, 21):
        if idx[d] + h >= len(CAL): continue
        used[h].append(d); spy[h].append(fwd('SPY', d, h))
        for g, pick in groups.items():
            v = [x for x in (fwd(s, d, h) for s in pick(r)) if x is not None]
            series[g][h].append(mean(v))
for g in groups: print(f"{g:34} " + ' '.join(f"{mean(series[g][h]) * 100:>+9.2f}" for h in (1, 5, 21)))
print(f"{'S&P 500 index fund (SPY)':34} " + ' '.join(f"{mean(spy[h]) * 100:>+9.2f}" for h in (1, 5, 21)))

print('\n2. TOP 10 MINUS THE AVERAGE STOCK (is the gap real or luck?)')
for h, name in ((1, 'next day'), (5, '1 week'), (21, '1 month')):
    diff = [a - b for a, b in zip(series['Top 10 by score'][h], series['All ~500 stocks (average stock)'][h])]
    ind = diff[::h]                                    # periods that do not overlap
    t = mean(ind) / (st.stdev(ind) / math.sqrt(len(ind))) if len(ind) > 2 else float('nan')
    print(f"   {name:9}: average gap {mean(diff) * 100:+.2f}%  | top 10 ahead on {sum(x > 0 for x in diff) / len(diff) * 100:.0f}% of days | t-statistic {t:+.2f} over {len(ind)} separate periods (beyond about ±2 is unlikely to be luck)")
    out[f'gap_{h}'] = (mean(diff), t)

print('\n3. BY THE LABEL SHOWN TO USERS (average change over the next week, percent)')
by = {}
for d in used[5]:
    for s, (sc, rec, _) in scores[d].items():
        x = fwd(s, d, 5)
        if x is not None: by.setdefault(rec, []).append(x)
labels = {'STRONG_BUY': 'Strongly positive', 'BUY': 'Positive', 'MODERATE_BUY': 'Slightly positive', 'HOLD': 'Mixed', 'MODERATE_SELL': 'Slightly negative', 'SELL': 'Negative', 'STRONG_SELL': 'Strongly negative'}
for k in labels:
    if k in by: print(f"   {labels[k]:18} {mean(by[k]) * 100:+.2f}%   ({len(by[k]):>6} stock-days, {len(by[k]) / sum(len(v) for v in by.values()) * 100:.0f}% of all)")

print('\n4. FAKE MONEY: $100,000 following the top 10 (prices at the close, no dividends)')
def run(hold, cost):
    """Every `hold` trading days put the whole account equally into that day's top 10. cost = fraction lost per side on what changes."""
    value = 100000.0; prev = set(); n = 0
    for k in range(0, len(days) - hold, hold):
        d = days[k]; picks = [s for s in ranked(d)[:10]]
        rets = [fwd(s, d, hold) for s in picks]; rets = [x if x is not None else 0.0 for x in rets]
        turnover = len(set(picks) - prev) / 10.0
        value *= (1 - 2 * cost * turnover); value *= 1 + mean(rets); prev = set(picks); n += 1
    return value, n
def bench(sym_or_all, hold=1):
    value = 100000.0
    for k in range(0, len(days) - hold, hold):
        d = days[k]
        if sym_or_all == 'ALL':
            v = [x for x in (fwd(s, d, hold) for s in scores[d]) if x is not None]; value *= 1 + mean(v)
        else: value *= 1 + (fwd(sym_or_all, d, hold) or 0)
    return value
years = len(days) / 252
print(f"   over {years:.1f} years{'':22} {'no trading costs':>18} {'0.1% cost per trade':>22}")
for hold, name in ((1, 'new top 10 every day'), (5, 'new top 10 every week'), (21, 'new top 10 every month')):
    a, n = run(hold, 0.0); b, _ = run(hold, 0.001)
    print(f"   {name:32} ${a:>12,.0f}       ${b:>12,.0f}      ({n} changes)")
    out[f'port_{hold}'] = (a, b)
print(f"   {'index fund (SPY), buy and hold':32} ${bench('SPY'):>12,.0f}")
print(f"   {'equal amount in every stock':32} ${bench('ALL'):>12,.0f}")
out['spy'] = bench('SPY'); out['all'] = bench('ALL')

print('\n5. SAME TEST, HALF BY HALF (a real effect should show in both)')
half = len(days) // 2
for nm, sub in (('first half', days[:half]), ('second half', days[half:])):
    g = []; 
    for d in sub:
        if idx[d] + 5 >= len(CAL): continue
        r = ranked(d); a = mean([x for x in (fwd(s, d, 5) for s in r[:10]) if x is not None]); b = mean([x for x in (fwd(s, d, 5) for s in r) if x is not None]); g.append(a - b)
    print(f"   {nm:12} {sub[0]} to {sub[-1]}: top 10 minus average stock over the next week {mean(g) * 100:+.2f}%")
json.dump(out, open('summary.json', 'w'))
