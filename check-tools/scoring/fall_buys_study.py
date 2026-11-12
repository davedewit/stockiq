"""Do shares bought right after an S&P 500 fall of 1% or more do worse than shares bought on other days? (12 Nov 2026; question 23.)
Live lead: of 239 finished trades, the 56 bought right after an S&P 500 session that fell 1% or more averaged -1.79% a trade against the
fund (+-0.68), the 116 bought after small rises -0.72%; the gap, -1.07 +-0.97, is inside the margin, and the 56 were mostly one fall week.
Written down BEFORE the result was seen. Five years of daily prices for the nine lists (fetch_wide.py), the trend score live since 17 Oct
2026. Decision days are every day SPY closed down 1% or more ("fall days") and, for comparison, every day it closed within +-0.5%
("quiet days"). On each, the top 3 of a list by the trend score are bought at the next close and sold 5 trading days later (the
autopilot's Balanced pace), each measured against SPY over the same days. A rule "wait a day after a market fall of 1% or more"
is worth a trial only if the fall-day buys did worse than the quiet-day buys in at least 6 of the lists in BOTH halves and the
pooled gap (quiet minus fall) is more than twice its margin of error in both halves.
Limits: today's members; fall days are clustered (2022, spring 2025), so the cases are far fewer than they look; no costs.
  python3 check-tools/scoring/fall_buys_study.py"""
import os, math, datetime, json, statistics
from depth_rsi_study import load, trend, LISTS, DATA, mean_se

HOLD, TOP = 5, 3
ts = [(datetime.datetime.fromtimestamp(b[0], datetime.UTC).strftime('%Y-%m-%d'), b[1]) for b in json.load(open(os.path.join(DATA, 'spy.json')))['SPY'] if b[1]]
spy = dict(ts); order = [d for d, _ in ts]; pos = {d: i for i, d in enumerate(order)}
chg = {order[i]: (spy[order[i]] / spy[order[i - 1]] - 1) * 100 for i in range(1, len(order))}
lines = []; say = lambda x='': (print(x), lines.append(x))
say(f'SPY days: {sum(1 for v in chg.values() if v <= -1)} fell 1% or more, {sum(1 for v in chg.values() if abs(v) <= 0.5)} within +-0.5%, of {len(chg)}')
pool = {h: {'fall': [], 'quiet': []} for h in ('first', 'second')}; ok = {'first': 0, 'second': 0}; n_lists = 0
for name in LISTS:
    series, cal, index, closes = load(name)
    if len(series) < 30: continue
    n_lists += 1; half = cal[len(cal) // 2]; res = {h: {'fall': [], 'quiet': []} for h in ('first', 'second')}
    quiet_seen = 0
    for t in range(260, len(cal) - HOLD - 2):
        d = cal[t]
        if d not in chg: continue
        kind = 'fall' if chg[d] <= -1 else 'quiet' if abs(chg[d]) <= 0.5 else None
        if not kind: continue
        if kind == 'quiet':
            quiet_seen += 1
            if quiet_seen % 4: continue                       # a quarter of the quiet days is plenty (and quicker)
        d1, dn = cal[t + 1], cal[t + 1 + HOLD]
        if d1 not in spy or dn not in spy: continue
        sc = []
        for s, rows in series.items():
            i, j, k = index[s].get(d), index[s].get(d1), index[s].get(dn)
            if i is None or j is None or k is None or rows[j][1] <= 0: continue
            tr = trend(closes[s], i)
            if tr: sc.append((tr[0], (rows[k][1] / rows[j][1] - 1) * 100 - (spy[dn] / spy[d1] - 1) * 100))
        if len(sc) < 10: continue
        res['first' if d < half else 'second'][kind].extend(x[1] for x in sorted(sc, key=lambda x: -x[0])[:TOP])
    for h in ('first', 'second'):
        f, q = res[h]['fall'], res[h]['quiet']
        if f and q and statistics.mean(f) < statistics.mean(q): ok[h] += 1
        pool[h]['fall'].extend(f); pool[h]['quiet'].extend(q)
        say(f'  {name:10s} {h:6s} after a fall {statistics.mean(f) if f else float("nan"):+6.2f} ({len(f)}) | quiet days {statistics.mean(q) if q else float("nan"):+6.2f} ({len(q)})')
passes = True
for h in ('first', 'second'):
    (mf, sf), (mq, sq) = mean_se(pool[h]['fall']), mean_se(pool[h]['quiet'])
    gap, margin = mq - mf, 2 * math.sqrt(sf ** 2 + sq ** 2)
    say(f'  pooled {h}: after a fall {mf:+.2f} (se {sf:.2f}, {len(pool[h]["fall"])}) | quiet days {mq:+.2f} (se {sq:.2f}, {len(pool[h]["quiet"])}): quiet minus fall {gap:+.2f} (margin {margin:.2f})')
    passes &= ok[h] >= 6 and gap > margin
say(f'  fall-day buys did worse than quiet-day buys in {ok["first"]} (first half) and {ok["second"]} (second half) of {n_lists} lists -> ' + ('PASSES the bar' if passes else 'does NOT pass the bar'))
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f'results-fall-buys-{datetime.datetime.now(datetime.UTC).date().isoformat()}.txt'), 'w').write('\n'.join(lines) + '\n')
