#!/usr/bin/env python3
"""How often should the themes part change its funds? (18 Oct 2026; the owner: "should it be checked in more often to pickup on
changes in market news"; questions.md 28.) The live rule: the 3 strongest of 14 sector and theme funds by their rise over the past
year without the last month, changed every 28 days (about 21 trading days). Here the same rule changed every 5, 10, 21, 42 and 63
trading days, with 0.1% off every change, over the same two halves of the period, with and without the chip fund (SMH), against
the S&P 500 fund held. Also the 3-month rise, changed weekly: the quickest-reacting variant, closest to "follow the news".
Prices: research-data/prices/sectors/ (not in git). Read-only.
"""
import json, os
from datetime import datetime, timezone
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'research-data', 'prices', 'sectors')
ALL = 'XLK XLE XLF XLV XLI XLY XLP XLU XLB XLRE XLC SMH GLD TLT'.split()
COST = 0.001


def load(s):
    r = json.load(open(os.path.join(D, s + '.json')))['chart']['result'][0]
    return dict((t, c) for t, c in zip(r['timestamp'], r['indicators']['quote'][0]['close']) if c)


px = {s: load(s) for s in ALL + ['SPY']}
days = sorted(set.intersection(*[set(v) for v in px.values()]))
first, last = 260, len(days) - 1
mid = (first + last) // 2


def run(lo, hi, every, look, skip, funds):
    v, held = 1.0, set()
    for a in range(lo, hi, every):
        b = min(a + every, hi)
        now = sorted(funds, key=lambda s: -(px[s][days[a - skip]] / px[s][days[a - look]] - 1))[:3]
        v *= 1 - COST * len(set(now) ^ held) / 3
        v *= 1 + sum(px[s][days[b]] / px[s][days[a]] - 1 for s in now) / 3
        held = set(now)
    return v - 1


when = lambda i: datetime.fromtimestamp(days[i], timezone.utc).strftime('%d %b %Y')
print(f"Halves: {when(first)} to {when(mid)}, and {when(mid)} to {when(last)}")
spy = [px['SPY'][days[hi]] / px['SPY'][days[lo]] - 1 for lo, hi in ((first, mid), (mid, last))]
print(f"  S&P 500 fund held: {spy[0]:+.1%} / {spy[1]:+.1%}")
for label, funds in (('all 14 funds', ALL), ('without the chip fund (SMH)', [s for s in ALL if s != 'SMH'])):
    print(f"\n{label}: top 3, changed every N trading days (first half / second half; ahead of the S&P 500 fund?)")
    for name, look, skip in (('past year less the last month', 252, 21), ('past 3 months', 63, 0)):
        for every in (5, 10, 21, 42, 63):
            r = [run(lo, hi, every, look, skip, funds) for lo, hi in ((first, mid), (mid, last))]
            mark = 'ahead in both' if all(x > s for x, s in zip(r, spy)) else 'behind in both' if all(x < s for x, s in zip(r, spy)) else 'mixed'
            print(f"  {name:31s} every {every:2d} days: {r[0]:+7.1%} / {r[1]:+7.1%}   {mark}" + ('   <- the live rule' if every == 21 and look == 252 and funds is ALL else ''))
print("\n20 variants a list: a few look good by luck. Read the pattern across the paces, not the best single line.")
