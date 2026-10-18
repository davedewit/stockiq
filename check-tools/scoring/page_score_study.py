"""Does the stock pages' 0-100 score sort shares by what they did next? (18 Oct 2026; the owner's daily review, proposal 2: "it marks
down the rises the screeners now reward"). The score is the single-stock report's and the stock pages' own (stock_metrics.py,
compute_analysis), run on each share's last 252 daily prices at a date, without company figures (there is no history of them here:
the technical part only, which is most of its points). Compared with the year's rise without the last month (the momentum the
screeners' trend score rewards) on the same dates.

Written down before the result: the score passes if its top fifth beats its bottom fifth over the next 20 trading days in both
halves of the period, in most of the 9 lists. Prices: research-data/prices (five years, fetched through the price function on AWS).
  python3 check-tools/scoring/page_score_study.py            writes results-page-score-<date>.txt beside this file
"""
import json, math, os, statistics, sys
from datetime import date
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import types
from stock_metrics import compute_analysis

# The candidate written down before it was run (18 Oct 2026): the score's points that bet against the trend turned round,
# everything else as it is. RSI: -5 over 80 only (as the trend score); the year's rise graded upward; near the high +5, near the low -5.
SWAPS = [
    ('        if rsi < 30:\n            score += 15\n            score_breakdown.append("RSI Oversold: +15 (Oversold reading)")\n'
     '        elif rsi > 70:\n            score -= 15\n            score_breakdown.append("RSI Overbought: -15 (Caution signal)")',
     '        if rsi > 80:\n            score -= 5\n            score_breakdown.append("RSI Very High: -5")'),
    ('    if ytd_change > 100:\n        score -= 15', '    if ytd_change > 100:\n        score += 12'),
    ('    elif ytd_change > 50:\n        score -= 8', '    elif ytd_change > 50:\n        score += 10'),
    ('    elif ytd_change > 30:\n        score += 3', '    elif ytd_change > 30:\n        score += 8'),
    ('    if range_position > 95:\n        score -= 5', '    if range_position > 95:\n        score += 5'),
    ('    elif range_position < 5:\n        score += 5', '    elif range_position < 5:\n        score -= 5'),
]


def variant():
    src = open(os.path.join(ROOT, 'stock_metrics.py')).read()
    for a, b in SWAPS:
        assert src.count(a) == 1, a[:40]
        src = src.replace(a, b)
    m = types.ModuleType('variant')
    exec(compile(src, 'variant', 'exec'), m.__dict__)
    return m.compute_analysis


compute_variant = variant()

LISTS = ['sp400_600', 'ftse100', 'dax40', 'cac40', 'aex', 'smi', 'nikkei225', 'asx200', 'tsx60']
STEP, AHEAD, WINDOW = 10, 20, 252


def series(bars):
    return [b[4] for b in bars], [b[2] for b in bars], [b[3] for b in bars], [b[5] or 0 for b in bars], [b[0] for b in bars]


def tstat(xs):
    if len(xs) < 3:
        return 0.0
    sd = statistics.stdev(xs)
    return statistics.mean(xs) / (sd / math.sqrt(len(xs))) if sd else 0.0


def study(name):
    data = json.load(open(os.path.join(ROOT, 'research-data', 'prices', name + '.json')))
    days = sorted({b[0] // 86400 for bars in data.values() for b in bars})
    pos = {s: {b[0] // 86400: i for i, b in enumerate(bars)} for s, bars in data.items()}
    rows = []                                                # per date: (day, [(score, mom, fwd)])
    for k in range(WINDOW + 30, len(days) - AHEAD, STEP):
        d, d2 = days[k], days[k + AHEAD]
        out = []
        for s, bars in data.items():
            i, j = pos[s].get(d), pos[s].get(d2)
            if i is None or j is None or i < WINDOW:
                continue
            c, h, l, v, _ = series(bars[i - WINDOW + 1:i + 1])
            if min(c) <= 0:
                continue
            score = compute_analysis(c, h, l, v, {})['score']
            mom = c[-22] / c[0] - 1                           # the year's rise without the last month
            out.append((score, mom, bars[j][4] / c[-1] - 1, compute_variant(c, h, l, v, {})['score']))
        if len(out) >= 15:
            rows.append((d, out))
    return rows


def spread(out, key):
    o = sorted(out, key=key)
    n = max(1, len(o) // 5)
    return statistics.mean(x[2] for x in o[-n:]) - statistics.mean(x[2] for x in o[:n])


lines = [f'Stock-page score against what shares did over the next {AHEAD} trading days (top fifth minus bottom fifth, in % points;'
         f' a date every {STEP} trading days; t = mean / standard error over the dates, which overlap little at this step)', '']
total = {'score': [0, 0], 'mom': [0, 0], 'new': [0, 0]}
for name in LISTS:
    rows = study(name)
    half = len(rows) // 2
    res = {}
    for label, key in (('score', lambda x: x[0]), ('mom', lambda x: x[1]), ('new', lambda x: x[3])):
        parts = [[spread(o, key) * 100 for _, o in rows[:half]], [spread(o, key) * 100 for _, o in rows[half:]]]
        res[label] = parts
        total[label][0] += sum(1 for p in parts if statistics.mean(p) > 0); total[label][1] += 2
    f = lambda p: f"{statistics.mean(p):+.2f} (t {tstat(p):+.1f})"
    lines.append(f"{name:10} {len(rows):3} dates | score: first half {f(res['score'][0])}, second {f(res['score'][1])}"
                 f" | momentum: first {f(res['mom'][0])}, second {f(res['mom'][1])}"
                 f" | turned round: first {f(res['new'][0])}, second {f(res['new'][1])}")
lines += ['', f"Half-periods where the top fifth beat the bottom fifth: score {total['score'][0]} of {total['score'][1]},"
          f" momentum {total['mom'][0]} of {total['mom'][1]}, the score turned round {total['new'][0]} of {total['new'][1]}.",
          'Limits: today\'s index members (flatters momentum); no company figures in the score (no history of them here);'
          ' before costs; a mostly rising period.']
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'results-page-score-{date.today().isoformat()}.txt')
open(out, 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
