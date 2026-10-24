"""Fed decision days: is there anything the autopilot should do differently around them?

The owner asked on 24 Oct 2026 whether the autopilot is "clued in" for announcements such as the Fed's
interest-rate decision (28 Oct 2026). Questions written down before the result:
  1. Do prices move more on a decision day (more chance of a loss limit or a stop being hit)?
  2. Is there a direction: the day before (the "pre-FOMC drift" of the research), the day, the day after?
  3. Does a share bought at the open of a decision day do worse over the next 5 days than one bought on
     any other day? (A rule "no new buys on a Fed day" would need this.)
Data: research-data/prices (daily bars, Oct 2021 to Oct 2026): the S&P 500 fund (SPY), the VIX, and the
shares of the S&P 400+600, FTSE 100, DAX 40 and the rest saved there. Read-only, no downloads.
Run: python3 check-tools/replay/fed_study.py
"""
import json, os, math, statistics as st
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PRICES = os.path.join(HERE, '..', '..', 'research-data', 'prices')

# Scheduled FOMC decision days (the second day of each meeting), from the Fed's calendars.
FOMC = '''2021-11-03 2021-12-15 2022-01-26 2022-03-16 2022-05-04 2022-06-15 2022-07-27 2022-09-21 2022-11-02
2022-12-14 2023-02-01 2023-03-22 2023-05-03 2023-06-14 2023-07-26 2023-09-20 2023-11-01 2023-12-13 2024-01-31
2024-03-20 2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18 2025-01-29 2025-03-19 2025-05-07
2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10 2026-01-28 2026-03-18 2026-04-29 2026-06-17 2026-07-29
2026-09-16'''.split()


def day(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%d')


def series(bars):
    """{date: (open, close)} and the dates in order."""
    out = {}
    for b in bars:
        if b and len(b) >= 5 and b[1] and b[4]:
            out[day(b[0])] = (float(b[1]), float(b[4]))
    return out, sorted(out)


def line(name, a, b):
    """Average of group a against group b, with the difference over its margin of error."""
    ma, mb = st.mean(a), st.mean(b)
    se = math.sqrt(st.pvariance(a) / len(a) + st.pvariance(b) / len(b))
    t = (ma - mb) / se if se else 0
    print(f'  {name:<44} {ma:+7.3f}% ({len(a):>5})  others {mb:+7.3f}% ({len(b):>6})  t {t:+5.2f}')


def main():
    spy = json.load(open(os.path.join(PRICES, 'spy.json')))
    s, dates = series(spy['SPY'])
    fed = [d for d in FOMC if d in s]
    idx = {d: i for i, d in enumerate(dates)}
    cc = {dates[i]: (s[dates[i]][1] / s[dates[i - 1]][1] - 1) * 100 for i in range(1, len(dates))}
    print(f'Fed decision days in the data: {len(fed)} ({fed[0]} to {fed[-1]})\n')

    print('1. The S&P 500 fund, close to close')
    for name, shift in (('the day before', -1), ('the decision day', 0), ('the day after', 1)):
        on = [cc[dates[idx[d] + shift]] for d in fed if 0 < idx[d] + shift < len(dates)]
        off = [v for k, v in cc.items() if k not in {dates[idx[d] + shift] for d in fed if 0 < idx[d] + shift < len(dates)}]
        line(name, on, off)
        line(name + ' (size of the move)', [abs(x) for x in on], [abs(x) for x in off])
    vix = json.load(open(os.path.join(PRICES, 'sectors', 'VIX.json')))
    r = vix['chart']['result'][0]
    q = r['indicators']['quote'][0]
    v, vd = series([[t, o, 0, 0, c] for t, o, c in zip(r['timestamp'], q['open'], q['close'])])
    vchg = {vd[i]: v[vd[i]][1] - v[vd[i - 1]][1] for i in range(1, len(vd))}
    on = [vchg[d] for d in fed if d in vchg]
    line('VIX change on the decision day (points)', on, [x for k, x in vchg.items() if k not in fed])

    print('\n2. Shares (every saved list): bought at the open, held 5 trading days, against the S&P 500 fund')
    files = [f for f in os.listdir(PRICES) if f.endswith('.json') and f != 'spy.json']
    fedset, before = set(fed), {dates[idx[d] - 1] for d in fed}
    on, pre, off, moves_on, moves_off, daily = [], [], [], [], [], []
    for f in files:
        data = json.load(open(os.path.join(PRICES, f)))
        for sym, bars in data.items():
            p, pd = series(bars)
            for i in range(1, len(pd) - 5):
                d = pd[i]
                if d not in s or pd[i + 5] not in s:
                    continue
                r = (p[pd[i + 5]][1] / p[d][0] - 1) * 100 - (s[pd[i + 5]][1] / s[d][0] - 1) * 100
                if abs(r) > 60:
                    continue
                m = abs(p[d][1] / p[pd[i - 1]][1] - 1) * 100
                daily.append((d, r))
                if d in fedset:
                    on.append(r); moves_on.append(m)
                else:
                    off.append(r); moves_off.append(m)
                    if d in before:
                        pre.append(r)
    print('  (counted share by share: shares on one day move together, so the t-values above overstate; see 3)')
    line('bought on a decision day', on, off)
    line('bought the day before', pre, off)
    line("a share's own move on a decision day (size)", moves_on, moves_off)

    print('\n3. The same, one figure a day (the average share that day): 40 events, not 64,000')
    byday = {}
    for d, r in daily:
        byday.setdefault(d, []).append(r)
    avg = {d: st.mean(v) for d, v in byday.items() if len(v) >= 50}
    for name, group in (('bought on a decision day', fedset), ('bought the day before', before)):
        a = [avg[d] for d in sorted(avg) if d in group]
        b = [avg[d] for d in avg if d not in fedset and d not in before]
        line(name, a, b)
        half = len(a) // 2
        line('   first half of those days', a[:half], b)
        line('   second half', a[half:], b)

if __name__ == '__main__':
    main()
