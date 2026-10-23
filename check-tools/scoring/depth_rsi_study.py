"""Three questions the live record raised (23 Oct 2026; the owner: "if something is always doing shit and something else is always
doing better, the shit thing really needs to be improved or removed"). Five years of daily prices for nine lists (fetch_wide.py),
ranked each week by the screeners' trend score (the "trend" of wide_study.py, the score live since 17 Oct 2026).

Written down BEFORE the result was seen:
  1. DEPTH. With 50 holdings the autopilot buys down to rank 30 of a screener. Live: rank 1-3 -0.12% a trade (52), 4-10 +1.18%
     (23), 11-20 -2.07% (18). Question: over 20 trading days, do ranks 11-30 do worse than ranks 1-10, against the whole list?
     A change is worth a trial only if ranks 11-30 trail ranks 1-10 in at least 7 of the 9 lists in BOTH halves.
  2. RSI WHEN BOUGHT. Live: RSI under 50 -3.02% a trade (20), 50-65 -0.07% (47), 65-75 +1.53% (28). Question: among the top 30
     by the trend score, do shares with RSI under 50 do worse over 20 days than those with RSI 50 or more? Same bar (7 of 9, both
     halves). Momentum research says a falling short-term trend inside a rising long-term one is a weak spot; this tests it here.
  3. A GAP DOWN AT THE OPEN. Live: 7 of 8 sales at the loss limit were Asian shares sold at the first check-in after an overnight
     fall, -14.3% against a -10% limit. Question: when a share opens 8% or more below the previous close, is the open the worst
     price of the next days: what do the same day's close and the next day's close give back against selling at the open?
     A rule "wait one check-in after a gap" is worth a trial only if the close beats the open on average in BOTH halves, by more
     than twice the margin of error.
Limits: today's members (flatters buying what rose); weekly decisions at the close, trades at the next open; no costs in 1 and 2
(they are the same for both groups); daily prices only, so "the open" is the day's first price, not the price 10 minutes in.
  python3 check-tools/scoring/depth_rsi_study.py
"""
import json, os, math, statistics, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, 'research-data', 'prices')
LISTS = ['sp400_600', 'ftse100', 'dax40', 'cac40', 'aex', 'smi', 'nikkei225', 'asx200', 'tsx60']
HOLD, STEP = 20, 5


def rsi(closes, n=14):
    if len(closes) < n + 1:
        return None
    gains = [max(0, closes[i] - closes[i - 1]) for i in range(1, len(closes))]
    losses = [max(0, closes[i - 1] - closes[i]) for i in range(1, len(closes))]
    g, l = sum(gains[:n]) / n, sum(losses[:n]) / n
    for i in range(n, len(gains)):
        g, l = (g * (n - 1) + gains[i]) / n, (l * (n - 1) + losses[i]) / n
    return 100.0 if l == 0 else 100 - 100 / (1 + g / l)


def trend(c, i):
    """The study's trend score on one share's closes up to day i (wide_study.py)."""
    if i < 253:
        return None
    year = c[i - 251:i + 1]; low = min(year); price = c[i]
    above = (price / low - 1) * 100 if low > 0 else 0
    mom = (c[i - 21] / c[i - 252] - 1) * 100 if c[i - 252] > 0 else 0
    ma200, ma50 = sum(c[i - 199:i + 1]) / 200, sum(c[i - 49:i + 1]) / 50
    r = rsi(c[i - 119:i + 1])
    return (min(2, above / 50) + max(-1.5, min(1.5, mom / 40)) + (0.5 if price > ma200 else -0.5) + (0.5 if ma50 > ma200 else -0.5)
            - (0.5 if r and r > 80 else 0)), r


def mean_se(v):
    if len(v) < 2:
        return (sum(v) / len(v) if v else float('nan')), float('nan')
    return statistics.mean(v), statistics.stdev(v) / math.sqrt(len(v))


def load(name):
    raw = json.load(open(os.path.join(DATA, name + '.json')))
    series = {}
    for s, v in raw.items():
        rows = [(datetime.datetime.fromtimestamp(b[0], datetime.UTC).strftime('%Y-%m-%d'), b[1], b[4]) for b in v if b[1] and b[4]]
        if len(rows) > 300:
            series[s] = rows
    cal = sorted({d for rows in series.values() for d, _, _ in rows})
    count = {}
    for rows in series.values():
        for d, _, _ in rows:
            count[d] = count.get(d, 0) + 1
    cal = [d for d in cal if count[d] > 0.6 * len(series)]
    index = {s: {d: i for i, (d, _, _) in enumerate(rows)} for s, rows in series.items()}
    closes = {s: [r[2] for r in rows] for s, rows in series.items()}
    return series, cal, index, closes


def study_list(name):
    series, cal, index, closes = load(name)
    half = cal[len(cal) // 2]
    out = {h: {'top10': [], 'deep': [], 'rsi_lo': [], 'rsi_hi': []} for h in ('first', 'second')}
    gaps = {'first': [], 'second': []}
    for t in range(260, len(cal) - HOLD - 1, STEP):
        d, d1, dn = cal[t], cal[t + 1], cal[t + 1 + HOLD]
        scored = []
        for s, rows in series.items():
            i, j, k = index[s].get(d), index[s].get(d1), index[s].get(dn)
            if i is None or j is None or k is None:
                continue
            tr = trend(closes[s], i)
            if not tr or rows[j][1] <= 0:
                continue
            fwd = (rows[k][1] / rows[j][1] - 1) * 100             # next open to the open HOLD days later
            scored.append((tr[0], tr[1], fwd))
        if len(scored) < 30:
            continue
        avg = statistics.mean(x[2] for x in scored)
        scored.sort(key=lambda x: -x[0])
        h = 'first' if d < half else 'second'
        top, deep = scored[:10], scored[10:30]
        out[h]['top10'].append(statistics.mean(x[2] for x in top) - avg)
        out[h]['deep'].append(statistics.mean(x[2] for x in deep) - avg)
        lo, hi = [x[2] - avg for x in scored[:30] if x[1] is not None and x[1] < 50], [x[2] - avg for x in scored[:30] if x[1] is not None and x[1] >= 50]
        out[h]['rsi_lo'] += lo; out[h]['rsi_hi'] += hi
    for s, rows in series.items():                               # gaps: every day a share opened 8% or more below the previous close
        for i in range(1, len(rows) - 2):
            prev, o, c, c2 = rows[i - 1][2], rows[i][1], rows[i][2], rows[i + 1][2]
            if prev > 0 and o > 0 and o / prev - 1 <= -0.08:
                h = 'first' if rows[i][0] < half else 'second'
                gaps[h].append(((c / o - 1) * 100, (c2 / o - 1) * 100))
    return out, gaps


def main():
    lines = []
    say = lambda x='': (print(x), lines.append(x))
    say(f"DEPTH, RSI AND GAPS: {datetime.date.today()}  (each week's ranking by the trend score; 20 trading days; against the whole list)")
    wins = {'depth': {'first': 0, 'second': 0}, 'rsi': {'first': 0, 'second': 0}}
    allgaps = {'first': [], 'second': []}
    for name in LISTS:
        out, gaps = study_list(name)
        for h in ('first', 'second'):
            t, dp = mean_se(out[h]['top10']), mean_se(out[h]['deep'])
            lo, hi = mean_se(out[h]['rsi_lo']), mean_se(out[h]['rsi_hi'])
            if dp[0] < t[0]: wins['depth'][h] += 1
            if lo[0] < hi[0]: wins['rsi'][h] += 1
            say(f"  {name:10s} {h:6s}  ranks 1-10 {t[0]:+6.2f}  ranks 11-30 {dp[0]:+6.2f} | top 30: RSI<50 {lo[0]:+6.2f} ({len(out[h]['rsi_lo'])})  RSI>=50 {hi[0]:+6.2f} ({len(out[h]['rsi_hi'])})")
            allgaps[h] += gaps[h]
    say()
    for k, text in (('depth', 'ranks 11-30 behind ranks 1-10'), ('rsi', 'RSI under 50 behind RSI 50 or more, in the top 30')):
        f, s = wins[k]['first'], wins[k]['second']
        say(f"  {text}: {f} of 9 lists in the first half, {s} of 9 in the second -> {'PASSES the bar (7 of 9, both halves): worth a trial' if f >= 7 and s >= 7 else 'does not pass the bar'}")
    say()
    for h in ('first', 'second'):
        same, nxt = mean_se([g[0] for g in allgaps[h]]), mean_se([g[1] for g in allgaps[h]])
        say(f"  gaps of 8% or more down at the open, {h} half: {len(allgaps[h])}; the same day's close against the open {same[0]:+.2f}% (+-{2 * same[1]:.2f}), the next day's close {nxt[0]:+.2f}% (+-{2 * nxt[1]:.2f})")
    out_path = os.path.join(HERE, f"results-depth-rsi-{datetime.date.today()}.txt")
    open(out_path, 'w').write('\n'.join(lines) + '\n'); print('\nsaved:', out_path)


if __name__ == '__main__':
    main()
