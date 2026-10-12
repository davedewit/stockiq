"""The autopilot's own rules, replayed over years of daily prices in a few seconds: the fast way to try an idea before it trades.

What it does
  1. Scores every stock of the list on every past day with the live screener worker's own code, on the prices it would have had
     that day (as check-tools/paper-test does). That takes about two minutes once and is kept in panel.json.
  2. Runs the autopilot's rules over those days as it would have run them: the shortlist (top of the ranking, positive score and
     signal, the level's RSI and 30-day limits), equal holdings out of a fixed budget, at most 3 buys a day, and the sales (loss
     limit, gain mark, the stop that keeps part of a gain, the longest holding time, signal turned negative, slipped down the
     ranking). The level tables, the pace and the gain-protection rule are imported from the deployed function, not copied.
  3. Takes a trading cost off every buy and every sale.
  4. Keeps the test honest: an idea is chosen on the FIRST part of the period only and then judged on the LAST part, which it has
     never seen; and it is compared with luck (the same rules buying stocks at random) and with simply holding an S&P 500 fund.

What it is not: decisions are taken once a day at the close and traded at the next morning's open (the live autopilot checks in
more often); the AI model's choice among the shortlist and its review of holdings are not replayed (buys go by rank); the list
is today's members (which flatters any result); no dividends. Shares only: there are no saved coin prices.

  python3 check-tools/replay/replay.py                 # the five levels, the search and its out-of-sample test
  python3 check-tools/replay/replay.py --rebuild       # score the days again (after the worker's scoring changed)
"""
import sys, os, json, glob, io, bisect, contextlib, importlib.util, datetime, itertools, random, math, statistics
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
PAPER = os.path.join(os.path.dirname(HERE), 'paper-test')
COST = 0.1                      # percent taken off each buy and each sale
BUDGET = 10000.0
LEARN_SHARE = 0.6               # the first 60% of the days is for finding an idea, the last 40% for judging it
START = '2022-10-17'

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
trader = load_module('trader', os.path.join(ROOT, 'lambda-sync', 'stockiq-ai-trader', 'lambda_function.py'))

universe = {l.split(':')[0]: l.split(':')[1].split() for l in open(os.path.join(PAPER, 'frozen_lists.txt')) if ':' in l and not l.startswith('#')}['sp100']
prices = json.load(open(os.path.join(PAPER, 'data', 'prices.json')))
day_of = lambda ts: datetime.datetime.fromtimestamp(ts, datetime.UTC).strftime('%Y-%m-%d')
bars = {s: [{'timestamp': b[0], 'open': b[1], 'high': b[2], 'low': b[3], 'close': b[4], 'volume': int(b[5])} for b in prices[s]] for s in universe + ['SPY'] if s in prices}
dates = {s: [day_of(b['timestamp']) for b in v] for s, v in bars.items()}
at = {s: {d: i for i, d in enumerate(dates[s])} for s in bars}
calendar = [d for d in dates['SPY'] if d >= START]

def build_panel():
    """Every stock's screener figures on every day, from the worker's own code."""
    worker = load_module('worker', os.path.join(ROOT, 'workers', 'stock_worker.py'))      # one file for every share screener since 11 Oct 2026
    now = {'d': None}
    def get_stock_data(symbol, period='1y'):
        symbol = symbol.upper()
        if symbol not in bars: return None
        i = bisect.bisect_right(dates[symbol], now['d']); data = bars[symbol][max(0, i - 252):i]
        return data if len(data) >= 20 else None
    worker.get_stock_data = get_stock_data
    worker.check_earnings_risk = lambda symbol: 'HIGH' if int(now['d'][5:7]) in (1, 4, 7, 10) else 'LOW'
    codes = {'STRONG_BUY': 3, 'BUY': 2, 'MODERATE_BUY': 1, 'HOLD': 0, 'MODERATE_SELL': -1, 'SELL': -2, 'STRONG_SELL': -3}
    panel = {}
    for n, d in enumerate(calendar):
        now['d'] = d; out = {}
        with contextlib.redirect_stdout(io.StringIO()):
            for s in universe:
                if s not in bars or d not in at[s]: continue
                r = worker.analyze_stock_advanced(s)
                if r: out[s] = [round(r['score'], 3), codes.get(r.get('recommendation'), 0), round(r.get('rsi') or 50, 1), round(r.get('change_30d') or 0, 2), round(r.get('distance_from_52w_low') or 0, 1), 0,
                               round(r.get('change_1yr') or 0, 1), round(r.get('change_90d') or 0, 1), round(100 * r['atr'] / r['price'], 2) if r.get('atr') and r.get('price') else 0.0, round(r.get('distance_from_52w_high') or 0, 1)]
        ranked = sorted(out, key=lambda s: -out[s][0])
        panel[d] = {s: out[s][:5] + [k + 1] + out[s][6:] for k, s in enumerate(ranked)}      # 0 score, 1 signal, 2 RSI, 3 30-day change, 4 % above 52-week low, 5 rank, 6 one-year change, 7 90-day change, 8 daily range %, 9 % under 52-week high
        if n % 100 == 0: print(f'  scored {n} of {len(calendar)} days', file=sys.stderr)
    json.dump(panel, open(os.path.join(HERE, 'panel.json'), 'w'))
    return panel

cache = os.path.join(HERE, 'panel.json')
panel = json.load(open(cache)) if os.path.exists(cache) and '--rebuild' not in sys.argv else build_panel()
if len(next(iter(next(iter(panel.values())).values()))) < 10: panel = build_panel()      # kept from before the extra figures were added
days = [d for d in calendar if d in panel]

def rules_of(level, **change):
    """One level's rules as the function has them (holdings, how far down the ranking, limits, loss limit, gain mark, pace)."""
    r = dict(trader.RISK[level]); r.setdefault('trail', 0.5)
    r.update(hold=trader.PACE[level]['maxHoldDays'], picker='rank', signal_exit=True, keep_gain=True, level=level)
    r.update(change); return r

def open_after(s, d):
    i = at[s].get(d)
    return bars[s][i + 1]['open'] if i is not None and i + 1 < len(bars[s]) and bars[s][i + 1]['open'] else None
def close_on(s, d):
    i = at[s].get(d)
    return bars[s][i]['close'] if i is not None else None

def run(rules, period, rng=None):
    """The rules over a run of days. Decisions at each day's close, trades at the next morning's open, a cost on each.
    `rng`: buy at random from the whole list instead of from the shortlist (the same selling rules): what luck would give."""
    slot, cash, held, trades, sold_on, curve = BUDGET / rules['positions'], BUDGET, {}, [], {}, []
    for n, d in enumerate(period):
        rows = panel[d]
        # ---- what is sold (decided at this close, done at the next open)
        for s in list(held):
            h = held[s]; px = close_on(s, d)
            if px is None: continue
            change = (px / h['buy'] - 1) * 100; h['peak'] = max(h['peak'], change); h['days'] += 1
            row = rows.get(s); why = None
            arm = trader.gain_arm(rules, rules['hold']); floor = trader.gain_floor(rules, rules['hold'], h['peak'])
            # 'scaled': (a, b): the loss limit is a times, the gain mark b times, what this share normally moves in a day (as it was when bought)
            stop, take = (-rules['scaled'][0] * h['range'], rules['scaled'][1] * h['range']) if rules.get('scaled') and h['range'] > 0 else (rules['stop'], rules['take'])
            if change <= stop: why = 'stop'
            elif change >= take: why = 'take'
            elif rules['keep_gain'] and h['peak'] >= arm and floor is not None and change <= floor: why = 'trail'
            elif h['days'] >= rules['hold']: why = 'time'
            elif rules['signal_exit'] and row and (row[1] < 0 or row[0] < 0): why = 'signal'
            elif rules['signal_exit'] and row and row[5] > trader.FADE * rules['top'] and row[0] < 0.5 * h['score']: why = 'fade'
            if why or n == len(period) - 1:
                out = open_after(s, d) or px
                gross = (out / h['buy'] - 1) * 100; net = ((1 + gross / 100) * (1 - COST / 100) ** 2 - 1) * 100
                spy = ((open_after('SPY', d) or close_on('SPY', d)) / h['spy'] - 1) * 100
                trades.append({'s': s, 'in': h['d'], 'out': d, 'pct': net, 'vs': net - spy, 'days': h['days'], 'why': why or 'end'})
                cash += slot * (1 + net / 100); del held[s]; sold_on[s] = n
        # ---- what is bought
        if n < len(period) - 1:
            if rng is None and rules.get('rank_by') is not None:      # another ranking than the screener's score: its top N, whatever the signal
                key, sign = rules['rank_by']; short = sorted(rows, key=lambda s: -sign * rows[s][key])[:rules['top']]
            elif rng is None:
                short = [s for s, r in rows.items() if r[1] > 0 and r[0] > 0 and r[5] <= rules['top'] and r[2] < rules['max_rsi'] and abs(r[3]) <= rules['max_move30']]
                short.sort(key=(lambda s: -rows[s][4]) if rules['picker'] == 'low52' else (lambda s: rows[s][5]))
            else:
                short = list(rows); rng.shuffle(short)
            bought = 0
            for s in short:
                if bought >= trader.MAX_BUYS_PER_CHECK or len(held) >= rules['positions'] or cash < slot - 0.01: break
                if s in held or n - sold_on.get(s, -99) < min(2, 2 * rules['hold']): continue
                px, spy = open_after(s, d), open_after('SPY', d)
                if not px or not spy: continue
                held[s] = {'buy': px, 'spy': spy, 'd': d, 'days': 0, 'peak': 0.0, 'score': rows[s][0], 'range': rows[s][8]}; cash -= slot; bought += 1
        curve.append(cash + sum(slot * ((close_on(s, d) or h['buy']) / h['buy']) for s, h in held.items()))
    return trades, curve

def figures(trades, curve, period):
    n = len(trades)
    if n < 2: return {'n': n}
    vs = [t['vs'] for t in trades]; se = statistics.stdev(vs) / math.sqrt(n)
    peak, worst = curve[0], 0.0
    for v in curve: peak = max(peak, v); worst = min(worst, (v / peak - 1) * 100)
    spy = (close_on('SPY', period[-1]) / open_after('SPY', period[0]) - 1) * 100
    return {'n': n, 'up': 100 * sum(t['pct'] > 0 for t in trades) / n, 'avg': statistics.mean(t['pct'] for t in trades), 'vs': statistics.mean(vs), 't': statistics.mean(vs) / se if se else 0.0,
            'total': (curve[-1] / BUDGET - 1) * 100, 'spy': spy, 'worst': worst, 'held': statistics.mean(t['days'] for t in trades)}
def line(label, f):
    if f.get('n', 0) < 2: return f"{label:<46} too few trades ({f.get('n', 0)})"
    return (f"{label:<46} {f['n']:>5} trades, {f['up']:>3.0f}% ended up, {f['avg']:+6.2f}% a trade after costs, {f['vs']:+6.2f} against the fund (t {f['t']:+5.2f}); "
            f"account {f['total']:+7.1f}% (the fund {f['spy']:+6.1f}%), worst fall {f['worst']:6.1f}%, held {f['held']:.0f} days")
def name(r):
    base = trader.RISK[r['level']]
    return (f"{base['name']}, held up to {r['hold']:g} days" + (', furthest above its 52-week low first' if r['picker'] == 'low52' else '') + ('' if r['signal_exit'] else ', no sale on the signal')
            + ('' if r['keep_gain'] else ', no stop that keeps a gain') + (f", top {r['top']}" if r['top'] != base['top'] else ''))

out = []
say = lambda text='': (print(text), out.append(text))
split = int(len(days) * LEARN_SHARE); learn, test = days[:split], days[split:]

if '--limits' in sys.argv:
    # One question, asked the honest way (12 Oct 2026, the owner: "it is making similar decisions for every stock?"): would a loss
    # limit and a gain mark set from each share's own movement do better than the same two numbers for every share? The multiples
    # are chosen on the first part of the period and judged on the last, which the choice never saw.   python3 replay.py --limits
    ranges = sorted(r[8] for d in days[::20] for r in panel[d].values() if r[8] > 0)
    print(f"What these {len(universe)} shares normally move in a day: a calm one {ranges[len(ranges) // 10]:.1f}%, a middling one {ranges[len(ranges) // 2]:.1f}%, a jumpy one {ranges[9 * len(ranges) // 10]:.1f}%")
    grid = [(a, b) for a in (1.5, 2, 3, 4, 6) for b in (2, 3, 5, 8, 12)]
    for level in (1, 2, 3, 4):
        base = rules_of(level); fixed_learn, fixed_test = figures(*run(base, learn), learn), figures(*run(base, test), test)
        print(f"\n{trader.RISK[level]['name']} (the same for every share: {base['stop']}% / +{base['take']}%, held up to {base['hold']:g} days)")
        print(line('   fixed limits, first part', fixed_learn)); print(line('   fixed limits, last part', fixed_test))
        tried = sorted(((figures(*run(rules_of(level, scaled=g), learn), learn), g) for g in grid), key=lambda x: -x[0].get('vs', -99))
        ahead = sum(1 for f, g in tried if f.get('vs', -99) > fixed_learn['vs'])
        best_f, best = tried[0]; judged = figures(*run(rules_of(level, scaled=best), test), test)
        print(f"   {ahead} of the {len(grid)} pairs of multiples did better than the fixed limits on the first part. The best: loss limit {best[0]:g}x, gain mark {best[1]:g}x a day's movement")
        print(line('   that pair, first part (chosen here)', best_f)); print(line('   that pair, last part (never seen)', judged))
        middle = figures(*run(rules_of(level, scaled=(3, 5)), test), test)
        print(line('   a plain pair (3x / 5x), last part', middle))
        print(f"   on the last part: fixed {fixed_test['vs']:+.2f} against the fund a trade, the chosen pair {judged['vs']:+.2f}, the plain pair {middle['vs']:+.2f}")
    sys.exit()
say(f"The autopilot's rules replayed on the S&P 100 list: {len(universe)} stocks, {len(days)} trading days ({days[0]} to {days[-1]}), ${BUDGET:,.0f}, {COST}% taken off each buy and each sale.")
say("Decisions once a day at the close, traded at the next open; buys by rank (the AI model is not replayed); today's index members; no dividends.")
say(); say("1. The five levels as they are, over the whole period")
for level in sorted(trader.RISK):
    r = rules_of(level); say('   ' + line(name(r), figures(*run(r, days), days)))
say(); say(f"2. Looking for something better, honestly: found on the first {len(learn)} days ({learn[0]} to {learn[-1]}), judged on the last {len(test)} ({test[0]} to {test[-1]})")
grid = [rules_of(level, hold=hold, picker=picker, signal_exit=sig, keep_gain=keep) for level in sorted(trader.RISK) for hold in (2, 5, 10, 20, 40, 60) for picker in ('rank', 'low52') for sig in (True, False) for keep in (True, False)]
scored = []
for r in grid:
    f = figures(*run(r, learn), learn)
    if f.get('n', 0) >= 40: scored.append((f['t'], f, r))
scored.sort(key=lambda x: -x[0])
say(f"   {len(grid)} variants of the rules tried on the first part. The five that looked best there (by how clearly they beat the fund per trade), and what each then did on the part it had not seen:")
kept = []
for t, f, r in scored[:5]:
    g = figures(*run(r, test), test); kept.append((r, f, g))
    say('   found: ' + line(name(r), f)); say('   then:  ' + line('', g))
ahead = sum(1 for t, f, r in scored if f['vs'] > 0)
later = [figures(*run(r, test), test) for t, f, r in scored]
say(f"   Of all {len(scored)} variants with 40 or more trades: {ahead} were ahead of the fund per trade on the first part; on the second part {sum(1 for g in later if g.get('vs', -1) > 0)} were, "
    f"and {sum(1 for g in later if g.get('t', 0) >= 2)} clearly so (t of 2 or more). The link between how a variant did on the first part and on the second: "
    f"{statistics.correlation([f['vs'] for t, f, r in scored], [g.get('vs', 0) for g in later]):+.2f} (1 = what worked kept working, 0 = no link).")
say(); say("3. Against luck: the best-looking variant's rules, buying stocks at random instead, 200 times, on the second part")
best, f_learn, f_test = kept[0]
lucky = [figures(*run(best, test, random.Random(seed)), test) for seed in range(200)]
say(f"   the variant: account {f_test['total']:+.1f}%, {f_test['vs']:+.2f} against the fund a trade. Random buying under the same rules: account {statistics.mean(x['total'] for x in lucky):+.1f}% on average, "
    f"and {100 * sum(x['total'] > f_test['total'] for x in lucky) / len(lucky):.0f}% of the random runs did better than the variant.")
base = rules_of(3); f_base = figures(*run(base, test), test); lucky3 = [figures(*run(base, test, random.Random(seed)), test) for seed in range(200)]
say(f"   the Balanced level as it is: account {f_base['total']:+.1f}%; random buying under its rules {statistics.mean(x['total'] for x in lucky3):+.1f}% on average, {100 * sum(x['total'] > f_base['total'] for x in lucky3) / len(lucky3):.0f}% of the random runs did better.")
say(); say("4. The variants that were ahead on BOTH parts (the only ones worth a second look), each checked against luck and without the seven chip / AI names")
CHIPS = {'SNDK', 'MU', 'AMD', 'ANET', 'NVDA', 'PLTR', 'DELL'}       # the names that carried the S&P 100 result in the earlier backtest
both = sorted(((min(f['t'], g.get('t', -9)), r, f, g) for (t, f, r), g in zip(scored, later) if f['vs'] > 0 and g.get('vs', -1) > 0), key=lambda x: -x[0])[:4]
whole = panel
for _, r, f, g in both:
    luck = [figures(*run(r, test, random.Random(seed)), test) for seed in range(200)]
    panel = {d: {s: v for s, v in rows.items() if s not in CHIPS} for d, rows in whole.items()}
    for d in panel:                                        # rank again without them
        for k, s_ in enumerate(sorted(panel[d], key=lambda x: -panel[d][x][0])): panel[d][s_] = panel[d][s_][:5] + [k + 1]
    without = figures(*run(r, test), test); panel = whole
    say(f"   {name(r)}")
    say(f"      first part {f['vs']:+.2f} a trade against the fund (t {f['t']:+.2f}), second part {g['vs']:+.2f} (t {g['t']:+.2f}), account on the second part {g['total']:+.1f}% (the fund {g['spy']:+.1f}%)")
    say(f"      random buying under the same rules did better in {100 * sum(x['total'] > g['total'] for x in luck) / len(luck):.0f}% of 200 runs; without the seven chip / AI names: {without.get('vs', 0):+.2f} a trade against the fund (t {without.get('t', 0):+.2f}), account {without.get('total', 0):+.1f}%")
say(); say("5. How long it holds, everything else as the Balanced level has it (whole period)")
for hold in (1, 2, 5, 10, 20, 40, 60):
    r = rules_of(3, hold=hold); say('   ' + line(f"held up to {hold} days", figures(*run(r, days), days)))
say("   and without selling on the screener's signal:")
for hold in (5, 20, 60):
    r = rules_of(3, hold=hold, signal_exit=False); say('   ' + line(f"held up to {hold} days, no sale on the signal", figures(*run(r, days), days)))
say(); say("6. Better inputs? The same rules (Balanced: 8 holdings from the top 10, sold at -10%, +18% or the time limit, never on the signal), ranking the list by something else than the screener's score")
RANKINGS = [("the screener's score (as now)", None), ('furthest above its 52-week low', (4, 1)), ('biggest rise over a year', (6, 1)), ('biggest rise over 90 days', (7, 1)),
            ('biggest rise over 30 days', (3, 1)), ('biggest fall over 30 days (a rebound)', (3, -1)), ('calmest (smallest daily range)', (8, -1)), ('jumpiest (largest daily range)', (8, 1)), ('lowest RSI', (2, -1))]
for hold in (20, 60):
    say(f"   kept up to {hold} days:   [first part -> second part: against the fund per trade (t); account against the fund's; share of 200 random runs that did better on the second part]")
    for label, key in RANKINGS:
        r = rules_of(3, hold=hold, signal_exit=False, keep_gain=False, rank_by=key) if key else rules_of(3, hold=hold, signal_exit=False, keep_gain=False)
        a, b = figures(*run(r, learn), learn), figures(*run(r, test), test)
        luck = [figures(*run(r, test, random.Random(seed)), test) for seed in range(200)]
        say(f"   {label:<40} {a['vs']:+5.2f} (t {a['t']:+5.2f}) -> {b['vs']:+5.2f} (t {b['t']:+5.2f});  account {a['total']:+6.1f}% vs {a['spy']:+5.1f}% -> {b['total']:+6.1f}% vs {b['spy']:+5.1f}%;  luck better in {100 * sum(x['total'] > b['total'] for x in luck) / len(luck):3.0f}%")
say("   None of these uses anything about the company itself (profit, debt, growth): there are no past figures of that kind on this machine to replay, and the screeners have none either.")
say(); say("How to read it: a variant is worth a trial with the fake money only if it was ahead on BOTH parts and random buying rarely beat it. Past results; they promise nothing.")
stamp = datetime.date.today().isoformat()
open(os.path.join(HERE, f'results-replay-{stamp}.txt'), 'w').write('\n'.join(out) + '\n')
