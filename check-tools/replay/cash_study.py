#!/usr/bin/env python3
"""Would holding more cash when the market looks risky have helped? (18 Oct 2026, the owner's idea: "a range display ... very low
to very high of market risk ... based on the risk depends how much is held in cash", and "if for example a massive drop in prices
across the board it would suck to have no cash to buy up".)

Five years of daily closes of an S&P 500 fund (SPY) and of the VIX (the market's own measure of expected swings, "the fear
gauge"), from research-data/prices/sectors/ (fetched through stockiq-price-proxy). Read-only, no downloads.

THE RULES, written down before the result was seen:
  The risk gauge at each close, 0 (very low) to 4 (very high), one point each for:
    the fund below its 200-day average; the fund below its 50-day average; the VIX above 20; the VIX above 30.
  It is known at the close and acted on from the next day. Every change of the cash share costs 0.1% of what is moved.
  A  "caution":      cash 0, 5, 10, 20, 30% at gauge 0..4 (more cash when the risk is high)
  B  "a reserve for a crash" (the owner's second idea): 10% cash at gauge 0-1, 5% at 2, none at 3-4 (spend the reserve when
     prices have fallen and fear is high)
  C  "trend only":   30% cash while the fund is below its 200-day average, none otherwise
  against 100% in the fund all the time. Price only, no dividends (the fund pays about 1.3% a year, all rules alike); cash earns
  nothing in the practice account, so the main run gives it 0%, and a second run gives it 4% a year (what it could earn really).
  Judged on both halves of the period, on the end result and on the worst fall from a high.
"""
import json, os

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'research-data', 'prices', 'sectors')


def closes(name):
    r = json.load(open(os.path.join(D, name + '.json')))['chart']['result'][0]
    return {t // 86400: c for t, c in zip(r['timestamp'], r['indicators']['quote'][0]['close']) if c}


spy, vix = closes('SPY'), closes('VIX')
days = sorted(d for d in spy if d in vix)
px = [spy[d] for d in days]; vx = [vix[d] for d in days]


def avg(i, n):
    return sum(px[i - n + 1:i + 1]) / n


gauge = [None] * len(days)
for i in range(199, len(days)):
    gauge[i] = (px[i] < avg(i, 200)) + (px[i] < avg(i, 50)) + (vx[i] > 20) + (vx[i] > 30)
start = 199

RULES = {'A caution': [0, 5, 10, 20, 30], 'B reserve for a crash': [10, 10, 5, 0, 0], 'C trend only': None}


def cash_of(rule, i):
    if rule == 'C trend only':
        return 30 if px[i] < avg(i, 200) else 0
    return RULES[rule][gauge[i]]


def run(rule, lo, hi, cash_rate):
    value, peak, worst, cash_pct = 1.0, 1.0, 0.0, None
    daily_cash = (1 + cash_rate) ** (1 / 252) - 1
    for i in range(lo, hi):
        want = 0 if rule is None else cash_of(rule, i - 1)        # yesterday's gauge, acted on today
        if cash_pct is not None and want != cash_pct:
            value *= 1 - abs(want - cash_pct) / 100 * 0.001
        cash_pct = want
        r = px[i] / px[i - 1] - 1
        value *= 1 + (1 - cash_pct / 100) * r + cash_pct / 100 * daily_cash
        peak = max(peak, value); worst = min(worst, value / peak - 1)
    return (value - 1) * 100, worst * 100


def iso(d):
    import datetime
    return datetime.date.fromordinal(datetime.date(1970, 1, 1).toordinal() + d).isoformat()


half = (start + 1 + len(days)) // 2
parts = [('first half', start + 1, half), ('second half', half, len(days)), ('all', start + 1, len(days))]
print(f"S&P 500 fund and VIX, {iso(days[start])} to {iso(days[-1])} ({len(days) - start} trading days); halves split at {iso(days[half])}")
counts = [sum(1 for g in gauge[start:] if g == k) for k in range(5)]
print('days at each gauge level 0 (very low) .. 4 (very high): ' + ', '.join(f'{k}: {c} ({c / sum(counts) * 100:.0f}%)' for k, c in enumerate(counts)))
for rate in (0.0, 0.04):
    print(f"\ncash earns {rate * 100:.0f}% a year")
    print(f"  {'':24s}" + ''.join(f"{name:>28s}" for name, _, _ in parts))
    for rule in [None] + list(RULES):
        cells = []
        for name, lo, hi in parts:
            ret, worst = run(rule, lo, hi, rate)
            cells.append(f"{ret:+7.1f}%, worst fall {worst:5.1f}%")
        print(f"  {rule or 'all in the fund':24s}" + ''.join(f"{c:>28s}" for c in cells))
print("\nRead: a rule is only worth having if it is ahead of 'all in the fund' in both halves, or gives up little and cuts the worst fall clearly."
      "\nFive years hold one real fall (2022) and a few sharp drops: few events, so treat any lead as a lead, not a finding.")
