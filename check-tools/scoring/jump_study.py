"""Do shares that jumped the day before being bought do worse? (12 Nov 2026; question 36, asked 19 Oct after coins that jumped 10% or
more the day before entering the top 10 fell 13.8% on average afterwards.)
Written down BEFORE the result was seen. Five years of daily prices for the nine lists (fetch_wide.py), the trend score live since
17 Oct 2026. Each week the top 30 of a list by the trend score (the autopilot's candidates at 50 holdings) are split by their rise on
the decision day itself (close against the previous close): 5% or more ("jumped") against the rest. Bought at the next close, held 20
trading days, measured against SPY over the same days. A rule "pass over a share that rose 5% or more the day before" is worth a trial
only if the jumped shares did worse than the rest in at least 6 of 9 lists in BOTH halves and the pooled gap (rest minus jumped) is
more than twice its margin of error in both. Also run at 3% and 8%.
Limits: today's members; the top 30 is a small group on a 5% day (a few hundred cases in all); no costs (same both ways).
  python3 check-tools/scoring/jump_study.py"""
import os, math, datetime, json, statistics
from depth_rsi_study import load, trend, LISTS, DATA, mean_se, HOLD, STEP

spy = {datetime.datetime.fromtimestamp(b[0], datetime.UTC).strftime('%Y-%m-%d'): b[1] for b in json.load(open(os.path.join(DATA, 'spy.json')))['SPY'] if b[1]}
lines = []; say = lambda x='': (print(x), lines.append(x))
for cut in (5.0, 3.0, 8.0):
    say(f'\nJump of {cut:g}% or more on the decision day, among the top 30 by trend; 20-day result against SPY')
    ok_halves = {'first': 0, 'second': 0}; pool = {h: ([], []) for h in ('first', 'second')}; n_lists = 0
    for name in LISTS:
        series, cal, index, closes = load(name)
        if len(series) < 30: continue
        n_lists += 1; half = cal[len(cal) // 2]; res = {h: ([], []) for h in ('first', 'second')}
        for t in range(260, len(cal) - HOLD - 2, STEP):
            d, d1, dn = cal[t], cal[t + 1], cal[t + 1 + HOLD]
            if d1 not in spy or dn not in spy: continue
            sc = []
            for s, rows in series.items():
                i, j, k = index[s].get(d), index[s].get(d1), index[s].get(dn)
                if i is None or j is None or k is None or i < 1 or rows[j][1] <= 0: continue
                tr = trend(closes[s], i)
                if tr: sc.append((tr[0], (closes[s][i] / closes[s][i - 1] - 1) * 100, (rows[k][1] / rows[j][1] - 1) * 100 - (spy[dn] / spy[d1] - 1) * 100))
            if len(sc) < 30: continue
            for _, jump, rel in sorted(sc, key=lambda x: -x[0])[:30]:
                res['first' if d < half else 'second'][0 if jump >= cut else 1].append(rel)
        for h in ('first', 'second'):
            j_, r_ = res[h]
            if j_ and r_ and statistics.mean(j_) < statistics.mean(r_): ok_halves[h] += 1
            pool[h][0].extend(j_); pool[h][1].extend(r_)
            say(f'  {name:10s} {h:6s} jumped {statistics.mean(j_) if j_ else float("nan"):+6.2f} ({len(j_)}) | the rest {statistics.mean(r_) if r_ else float("nan"):+6.2f} ({len(r_)})')
    passes = True
    for h in ('first', 'second'):
        (mj, sj), (mr, sr) = mean_se(pool[h][0]), mean_se(pool[h][1])
        gap, margin = mr - mj, 2 * math.sqrt(sj ** 2 + sr ** 2)
        say(f'  pooled {h}: jumped {mj:+.2f} (se {sj:.2f}, {len(pool[h][0])}) | the rest {mr:+.2f} (se {sr:.2f}, {len(pool[h][1])}): rest minus jumped {gap:+.2f} (margin {margin:.2f})')
        passes &= ok_halves[h] >= 6 and gap > margin
    say(f'  jumped did worse in {ok_halves["first"]} (first half) and {ok_halves["second"]} (second half) of {n_lists} lists -> ' + ('PASSES the bar' if passes else 'does NOT pass the bar'))
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f'results-jump-{datetime.datetime.now(datetime.UTC).date().isoformat()}.txt'), 'w').write('\n'.join(lines) + '\n')
