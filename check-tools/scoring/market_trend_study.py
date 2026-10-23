"""Should the autopilot leave a market while it is falling? (23 Oct 2026, the owner's AI / Manual choice of markets.)
Written down BEFORE the result: for each of the nine lists, the "market" is the equal-weighted average of its shares. Each week,
the top 10 by the trend score, held 20 trading days, against SPY over the same days; split by whether the market stood above or
below its own 200-day average that week. The rule "leave a market while it is below its 200-day average" is worth building only
if the top 10 did worse against SPY in the below-weeks than in the above-weeks in at least 6 of 9 lists, in BOTH halves.
  python3 check-tools/scoring/market_trend_study.py"""
import json, os, statistics, datetime
from depth_rsi_study import load, trend, LISTS, HOLD, STEP, DATA
spy = {datetime.datetime.fromtimestamp(b[0], datetime.UTC).strftime('%Y-%m-%d'): b[1] for b in json.load(open(os.path.join(DATA, 'spy.json')))['SPY'] if b[1]}
lines = []; say = lambda x='': (print(x), lines.append(x))
wins = {'first': 0, 'second': 0}; n = 0
for name in LISTS:
    series, cal, index, closes = load(name)
    if len(series) < 20: continue
    n += 1; half = cal[len(cal) // 2]
    mkt = []
    for d in cal:
        v = [closes[s][index[s][d]] / closes[s][max(0, index[s][d] - 1)] - 1 for s in series if d in index[s] and index[s][d] > 0]
        mkt.append((mkt[-1] if mkt else 1.0) * (1 + (statistics.mean(v) if v else 0)))
    res = {h: {'up': [], 'down': []} for h in ('first', 'second')}
    for t in range(260, len(cal) - HOLD - 1, STEP):
        d, d1, dn = cal[t], cal[t + 1], cal[t + 1 + HOLD]
        if d1 not in spy or dn not in spy: continue
        sc = []
        for s, rows in series.items():
            i, j, k = index[s].get(d), index[s].get(d1), index[s].get(dn)
            if i is None or j is None or k is None or rows[j][1] <= 0: continue
            tr = trend(closes[s], i)
            if tr: sc.append((tr[0], (rows[k][1] / rows[j][1] - 1) * 100))
        if len(sc) < 10: continue
        top = statistics.mean(x[1] for x in sorted(sc, key=lambda x: -x[0])[:10]) - (spy[dn] / spy[d1] - 1) * 100
        above = mkt[t] > statistics.mean(mkt[t - 199:t + 1])
        res['first' if d < half else 'second']['up' if above else 'down'].append(top)
    for h in ('first', 'second'):
        u, dn_ = res[h]['up'], res[h]['down']
        mu, md = (statistics.mean(u) if u else float('nan')), (statistics.mean(dn_) if dn_ else float('nan'))
        if dn_ and u and md < mu: wins[h] += 1
        say(f"  {name:10s} {h:6s} market above its 200-day: top 10 vs SPY {mu:+6.2f} ({len(u)} weeks) | below: {md:+6.2f} ({len(dn_)} weeks)")
say(f"\n  worse when below, in {wins['first']} of {n} lists (first half) and {wins['second']} of {n} (second half) -> "
    + ('PASSES (6 of 9, both halves): build it' if wins['first'] >= 6 and wins['second'] >= 6 else 'does NOT pass the bar'))
open(os.path.join(os.path.dirname(__file__), f'results-market-trend-{datetime.date.today()}.txt'), 'w').write('\n'.join(lines) + '\n')
