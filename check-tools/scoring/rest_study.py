"""Does resting a screener after its recent trades lagged the S&P 500 help? (12 Nov 2026; Admin #8's last stage, question 22/23 family.)
The live rule (`review_resting` in stockiq-ai-trader): a screener rests for 14 days when its last 12 finished trades (at least 8) average
1.5% or more behind an S&P 500 fund over the same days; only trades closed after the rest count towards resting it again.
Live today: S&P 500 rested to 13 Nov, Nikkei to 18 Nov, ASX 200 to 23 Nov, TSX 60 to 25 Nov.

Written down BEFORE the result was seen. Five years of daily prices for the nine lists (fetch_wide.py), the trend score live since 17 Oct
2026. Each week the top 3 of a list by the trend score are bought at the next close and sold 5 trading days later (the autopilot's
Balanced pace: about 3 buys a market a week, a 5-day hold), each trade measured against SPY over the same days. Three rules:
  R0  the live rule: the last 12 finished trades (at least 8) average <= -1.5% -> skip this week and the next (14 days)
  R1  one bad night counts once: the MEDIAN of the last 5 weekly groups' averages (at least 3 groups) <= -1.5% -> same rest
  R2  never rest (every week traded)
The rule is worth keeping as it is only if the weeks it skips did WORSE than the weeks it trades (against SPY) in at least 6 of 9 lists
in BOTH halves, and the pooled gap (traded minus skipped) is more than twice its margin of error. R1 replaces R0 only if it passes that
bar and R0 does not. If neither passes, resting is a coin flip that costs trades: say so and the rule goes to the owner's page as an idea
to remove (it also acted on one night's six Asian losses on 22-23 Oct, which is what R1 is for).
Limits: today's members (flatters buying what rose); weekly decisions, 5-day holds with no stops (live holdings sell on stops and
signals, so live trades end on different days); 3 trades a week is a replay's stand-in for the live pace; no costs (same both ways).
  python3 check-tools/scoring/rest_study.py"""
import os, statistics, math, datetime, json
from depth_rsi_study import load, trend, LISTS, DATA, mean_se

HOLD, STEP, TOP = 5, 5, 3
LOOK, NEED, BELOW, REST_STEPS = 12, 8, -1.5, 2
spy = {datetime.datetime.fromtimestamp(b[0], datetime.UTC).strftime('%Y-%m-%d'): b[1] for b in json.load(open(os.path.join(DATA, 'spy.json')))['SPY'] if b[1]}
lines = []; say = lambda x='': (print(x), lines.append(x))


def cohorts(name):
    """[(decision index, exit index, date, [relative returns of the top TOP in %])] for every week."""
    series, cal, index, closes = load(name)
    out = []
    for t in range(260, len(cal) - HOLD - 2, STEP):
        d, d1, dn = cal[t], cal[t + 1], cal[t + 1 + HOLD]
        if d1 not in spy or dn not in spy: continue
        sc = []
        for s, rows in series.items():
            i, j, k = index[s].get(d), index[s].get(d1), index[s].get(dn)
            if i is None or j is None or k is None or rows[j][1] <= 0: continue
            tr = trend(closes[s], i)
            if tr: sc.append((tr[0], (rows[k][1] / rows[j][1] - 1) * 100 - (spy[dn] / spy[d1] - 1) * 100))
        if len(sc) < 10: continue
        out.append((t, t + 1 + HOLD, d, [x[1] for x in sorted(sc, key=lambda x: -x[0])[:TOP]]))
    return out, cal


def run(coh, rule):
    """Which weeks the rule skips. A week's trades count towards the rule once they have closed (exit index <= the decision index) and
    only if they closed after the last rest ended; trades of skipped weeks are not trades and are never counted."""
    traded, skipped, until, since = [], [], -1, -1
    for n, (t, ex, d, rel) in enumerate(coh):
        if t < until:
            skipped.append(n); continue
        fired = False
        if rule != 'R2':
            done = [(e, r) for (tt, e, dd, r), k in zip(coh[:n], range(n)) if k in set(traded) and e <= t and e > since]
            if rule == 'R0':
                tr = [x for e, r in done for x in r][-LOOK:]
                fired = len(tr) >= NEED and sum(tr) / len(tr) <= BELOW
            else:
                g = [sum(r) / len(r) for e, r in done][-5:]
                fired = len(g) >= 3 and statistics.median(g) <= BELOW
        if fired:
            skipped.append(n); until = t + REST_STEPS * STEP; since = until
        else:
            traded.append(n)
    return traded, skipped


res = {r: {'first': [], 'second': []} for r in ('R0', 'R1')}
pooled = {r: {'first': ([], []), 'second': ([], [])} for r in ('R0', 'R1')}
for name in LISTS:
    coh, cal = cohorts(name)
    if len(coh) < 60: continue
    half = cal[len(cal) // 2]
    for rule in ('R0', 'R1', 'R2'):
        traded, skipped = run(coh, rule)
        if rule == 'R2': continue
        for h in ('first', 'second'):
            keep = [x for n in traded if (coh[n][2] < half) == (h == 'first') for x in coh[n][3]]
            skip = [x for n in skipped if (coh[n][2] < half) == (h == 'first') for x in coh[n][3]]
            mk, ms = (statistics.mean(keep) if keep else float('nan')), (statistics.mean(skip) if skip else float('nan'))
            res[rule][h].append((name, mk, ms, len(keep), len(skip)))
            pooled[rule][h][0].extend(keep); pooled[rule][h][1].extend(skip)
for rule, label in (('R0', 'R0 the live rule'), ('R1', 'R1 the median of weekly groups')):
    say(f'\n{label}')
    wins = {}
    for h in ('first', 'second'):
        wins[h] = 0
        for name, mk, ms, nk, ns in res[rule][h]:
            if ns and ms < mk: wins[h] += 1
            say(f'  {name:10s} {h:6s} traded weeks {mk:+6.2f} ({nk} trades) | skipped weeks {ms:+6.2f} ({ns} trades)')
        keep, skip = pooled[rule][h]
        (mk, sk), (ms, ss) = mean_se(keep), mean_se(skip)
        gap, se = mk - ms, math.sqrt(sk ** 2 + ss ** 2) if skip else float('nan')
        say(f'  pooled {h}: traded {mk:+.2f} (se {sk:.2f}, {len(keep)}), skipped {ms:+.2f} (se {ss:.2f}, {len(skip)}): traded minus skipped {gap:+.2f} (margin {2 * se:.2f})')
        wins[h] = (wins[h], gap > 2 * se if skip else False)
    ok = all(w[0] >= 6 and w[1] for w in wins.values())
    say(f'  skipped weeks worse than traded weeks in {wins["first"][0]} (first half) and {wins["second"][0]} (second half) of 9 lists; '
        f'pooled gap beyond twice its margin: {wins["first"][1]} / {wins["second"][1]} -> ' + ('PASSES the bar' if ok else 'does NOT pass the bar'))
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f'results-rest-{datetime.datetime.now(datetime.UTC).date().isoformat()}.txt'), 'w').write('\n'.join(lines) + '\n')
