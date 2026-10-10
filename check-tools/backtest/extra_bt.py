import pickle, random, statistics as st
from replay import load, DATA, CAL
load()
P = pickle.load(open('scores.pkl', 'rb')); scores = P['scores']; universe = P['universe']; order = {s: i for i, s in enumerate(universe)}
days = sorted(scores); idx = {d: i for i, d in enumerate(CAL)}
close = {s: {r['day']: r['close'] for r in rows} for s, rows in DATA.items()}; opn = {s: {r['day']: r['open'] for r in rows} for s, rows in DATA.items()}
def mean(x): return sum(x) / len(x) if x else 0.0
def ranked(day): return sorted(scores[day], key=lambda s: (-scores[day][s][0], order[s]))
def ret(sym, day, hold, entry):
    i = idx[day]
    if entry == 'close':
        a = close[sym].get(day); b = close[sym].get(CAL[i + hold]) if i + hold < len(CAL) else None
    else:   # buy at the next morning's open (the first price you could really get after seeing the report), sell at the open `hold` days later
        a = opn[sym].get(CAL[i + 1]) if i + 1 < len(CAL) else None; b = opn[sym].get(CAL[i + 1 + hold]) if i + 1 + hold < len(CAL) else None
    return (b / a - 1) if a and b else None
def run(pick, hold, cost, entry):
    value = 100000.0; prev = set()
    for k in range(0, len(days) - hold - 1, hold):
        d = days[k]; picks = pick(d)
        rets = [ret(s, d, hold, entry) for s in picks]; rets = [x for x in rets if x is not None]
        value *= (1 - 2 * cost * len(set(picks) - prev) / max(1, len(picks))); value *= 1 + mean(rets); prev = set(picks)
    return value
top = lambda d: ranked(d)[:10]; bottom = lambda d: ranked(d)[-10:]; everything = lambda d: list(scores[d])
print('FAKE MONEY, $100,000, buying at the NEXT MORNING\'S OPEN (what a person could really do)')
print(f"{'':36}{'no costs':>12}{'0.03%/trade':>14}{'0.1%/trade':>13}")
for hold, name in ((1, 'top 10, changed every day'), (5, 'top 10, changed every week'), (21, 'top 10, changed every month')):
    print(f"   {name:33}" + ''.join(f"${run(top, hold, c, 'open'):>11,.0f} " for c in (0, 0.0003, 0.001)))
for hold, name in ((1, 'BOTTOM 10, changed every day'), (5, 'BOTTOM 10, changed every week'), (21, 'BOTTOM 10, changed every month')):
    print(f"   {name:33}" + ''.join(f"${run(bottom, hold, c, 'open'):>11,.0f} " for c in (0, 0.0003, 0.001)))
spy = 100000 * (opn['SPY'][CAL[idx[days[-1]]]] / opn['SPY'][CAL[idx[days[0]] + 1]])
print(f"   {'index fund (SPY), buy and hold':33}${spy:>11,.0f}")
print(f"   {'equal amount in every stock':33}${run(everything, 1, 0, 'open'):>11,.0f}")
random.seed(7)
for hold, name in ((1, 'every day'), (5, 'every week'), (21, 'every month')):
    mine = run(top, hold, 0, 'open'); sims = []
    for _ in range(300):
        sims.append(run(lambda d: random.sample(list(scores[d]), 10), hold, 0, 'open'))
    sims.sort(); beat = sum(x > mine for x in sims) / len(sims) * 100
    print(f"   10 RANDOM stocks changed {name:12}: typical ${st.median(sims):,.0f}, range of the middle 90% ${sims[15]:,.0f} to ${sims[-15]:,.0f}; {beat:.0f}% of 300 random portfolios beat the screener's ${mine:,.0f}")
