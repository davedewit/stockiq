#!/usr/bin/env python3
"""Why did each trade end as it did: up, flat or down? (23 Oct 2026; the owner: "a stock drops in price, why? has this happened before? is there a pattern?
was it news? was it a country failing at something?") Read-only: the account's finished trades, and one price request per index.

Each losing trade of the period is put down to one cause, in this order:
  one event      three or more sales set off by the price (loss limit, stop, gain mark) in one region within 24 hours, the same way
  its market     its own index fell too over the days it was held, by 1% or more and by at least half the loss
  the share      the rest: its market held up and the share fell by itself (news, results, its sector: headlines at the sale are
                 not recorded yet, experiment idea "loss-news")
and the dollars are summed by cause (losses and gains apart), each trade is set against its own index over the same days (the part that
was the pick, not the market: the owner: "and same for it increasing same for it staying stagnant"), and the dollars lost are summed by cause, region and kind of sale. Repeats (a share that lost more than once) are listed.
At the end, plain findings: which cause dominates and which idea or question in the register it bears on.

    python3 check-tools/trade_causes.py [--days 14] [--account <address>]     (part 4b of autopilot_review.py runs it)
"""
import os, sys, json, re, datetime, urllib.request, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location('trader', os.path.join(ROOT, 'lambda-sync', 'stockiq-ai-trader', 'lambda_function.py'))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def home_index():
    """The screeners' own indexes, from practice-portfolio.js (HOME_INDEX), so that the two never disagree."""
    src = open(os.path.join(os.path.dirname(ROOT), 'website', 'practice-portfolio.js'), encoding='utf-8').read()
    block = src[src.index('const HOME_INDEX'):]; block = block[:block.index('};')]
    return {k: (sym, name) for k, sym, name in re.findall(r"'([\w-]+)':\s*\['([^']+)',\s*'([^']+)'\]", block)}

def closes(symbol, cache={}):
    if symbol not in cache:
        try:
            url = m.PRICE_URL + urllib.parse.quote(symbol) + '&range=6mo'
            r = json.load(urllib.request.urlopen(url, timeout=30))['chart']['result'][0]
            cache[symbol] = [(datetime.datetime.utcfromtimestamp(t), c) for t, c in zip(r['timestamp'], r['indicators']['quote'][0]['close']) if c]
        except Exception:
            cache[symbol] = []
    return cache[symbol]

def at(series, when):
    before = [c for t, c in series if t <= when]
    return before[-1] if before else None

def main():
    import boto3, urllib.parse  # noqa: F401
    days = int(sys.argv[sys.argv.index('--days') + 1]) if '--days' in sys.argv else 14
    acct = sys.argv[sys.argv.index('--account') + 1] if '--account' in sys.argv else os.environ.get('REVIEW_ACCOUNT', 'dave@dewit.com.au')
    rec = json.loads(boto3.resource('dynamodb', region_name='us-east-1').Table('stockiq-ai-trader').get_item(Key={'userId': acct})['Item']['data'])
    now = datetime.datetime.utcnow(); since = now - datetime.timedelta(days=days)
    hist = [t for t in rec.get('history') or [] if m.parse_time(t.get('t')) and m.parse_time(t['t']) >= since]
    ix = home_index()
    region = lambda t: m.SCREENERS[t['screener']][5] if t.get('screener') in m.SCREENERS else ('Sector funds' if t.get('screener') == 'themes' else 'other')
    outcome = lambda t: 'up' if t['pct'] > 0.5 else 'down' if t['pct'] < -0.5 else 'flat'
    print(f"Finished trades of the last {days} days: {len(hist)} (up {sum(outcome(t) == 'up' for t in hist)}, flat {sum(outcome(t) == 'flat' for t in hist)}, "
          f"down {sum(outcome(t) == 'down' for t in hist)}), {'+' if sum(t.get('usd') or 0 for t in hist) >= 0 else '-'}${abs(sum(t.get('usd') or 0 for t in hist)):,.0f} in all")
    if not hist:
        return
    # one event: 3+ sales in a region set off by the price (a loss limit, a stop, a gain mark), the same way, within 24 hours. Sales by
    # the holding time or the signal come in batches at a check-in because of the schedule: they are not a shock and are left out.
    BY_PRICE = {'stop', 'take', 'trail', 'cut'}
    event = set()
    for t in hist:
        if outcome(t) == 'flat' or t.get('exit') not in BY_PRICE: continue
        s = m.parse_time(t['t'])
        near = [u for u in hist if u.get('exit') in BY_PRICE and outcome(u) == outcome(t) and region(u) == region(t) and abs((m.parse_time(u['t']) - s).total_seconds()) <= 86400]
        if len(near) >= 3: event |= {id(u) for u in near}
    rows = []
    for t in hist:
        sold = m.parse_time(t['t']); bought = sold - datetime.timedelta(days=float(t.get('days') or 0))
        k = ix.get(t.get('screener')); move = None
        if k:
            sr = closes(k[0]); a, b = at(sr, bought), at(sr, sold)
            move = round((b / a - 1) * 100, 2) if a and b else None
        pct, o = t['pct'], outcome(t)
        same_way = move is not None and abs(move) >= 1 and (move * pct > 0) and abs(move) >= abs(pct) / 2
        cause = 'one event' if id(t) in event else 'its market' if same_way else 'the share' if o != 'flat' else 'flat'
        rows.append(dict(t=t, sold=sold, move=move, cause=cause, o=o, idx=k[1] if k else '', gap=None if move is None else round(pct - move, 2)))
    def table(key, which):
        out = {}
        for r in which:
            out.setdefault(key(r), [0, 0.0]); out[key(r)][0] += 1; out[key(r)][1] += (r['t'].get('usd') or 0)
        return sorted(out.items(), key=lambda kv: kv[1][1])
    for o, word in (('down', 'Losses'), ('up', 'Gains')):
        part = [r for r in rows if r['o'] == o]
        if not part: continue
        print(f"\n{word}, by cause ({len(part)} trades):")
        for c, (n, usd) in table(lambda r: r['cause'], part): print(f"  {c:12s} {n:3d} trades  {'+' if usd >= 0 else '-'}${abs(usd):8,.0f}")
    print(f"\nFlat (within 0.5%): {sum(r['o'] == 'flat' for r in rows)} trades: the trading cost is lost on each, and the money waited")
    # against its own market: the part of each result that was the pick, not the market
    print('\nAgainst its own index over the same days (the pick, not the market), by region:')
    for g in sorted({region(r['t']) for r in rows}):
        gaps = [r['gap'] for r in rows if region(r['t']) == g and r['gap'] is not None]
        if gaps:
            avg = sum(gaps) / len(gaps); beat = sum(x > 0 for x in gaps)
            print(f"  {g:22s} {len(gaps):3d} trades: {avg:+.2f}% a trade against its index, ahead in {beat} of {len(gaps)} ({beat / len(gaps) * 100:.0f}%)" + ('  (too few to read: under 30)' if len(gaps) < 30 else ''))
    print('\nOne-event days:')
    seen = {}
    for r in rows:
        if r['cause'] == 'one event': seen.setdefault((r['sold'].strftime('%a %d %b'), region(r['t']), r['o']), []).append(r['t']['symbol'])
    shown = {k: v for k, v in seen.items() if len(v) >= 3}    # a run of 24 hours can cross midnight: the days with 3 or more are listed
    for (d, g, o), syms in sorted(shown.items()): print(f"  {d}, {g}, {o}: {len(syms)} trades ({', '.join(syms[:8])})")
    if not shown: print('  none with three or more on one day')
    reps = {}
    for t in rec.get('history') or []: reps.setdefault(t['symbol'], []).append(t['pct'])
    reps = {s: v for s, v in reps.items() if len(v) >= 2}
    print('\nShares traded more than once (all time): ' + (', '.join(f"{s} ({len(v)}x: {' '.join(f'{x:+.1f}%' for x in v)})" for s, v in sorted(reps.items(), key=lambda kv: sum(kv[1]))[:12]) or 'none'))
    print('\nThe largest moves:')
    for r in sorted(rows, key=lambda r: abs(r['t'].get('usd') or 0), reverse=True)[:6]:
        t = r['t']; print(f"  {t['symbol']:10s} {t['pct']:+6.2f}%  {'+' if (t.get('usd') or 0) >= 0 else '-'}${abs(t.get('usd') or 0):7,.0f}  sold {r['sold']:%d %b} by {t.get('exit')}, {r['cause']}" + (f"; {r['idx']} {r['move']:+.2f}% over the same days" if r['move'] is not None else ''))
    gaps = [r['gap'] for r in rows if r['gap'] is not None]
    if gaps:
        avg = sum(gaps) / len(gaps); sd = (sum((x - avg) ** 2 for x in gaps) / max(1, len(gaps) - 1)) ** 0.5; se = sd / len(gaps) ** 0.5
        verdict = 'clearly ahead of their markets' if avg - 2 * se > 0 else 'clearly behind their markets' if avg + 2 * se < 0 else 'not clearly different from their markets (could be luck)'
        print(f"\nFINDING: the picks did {avg:+.2f}% a trade against their own markets over {len(gaps)} trades (probably between {avg - 2 * se:+.2f}% and {avg + 2 * se:+.2f}%): {verdict}.")
    lossrows = [r for r in rows if r['o'] == 'down']
    if lossrows:
        lead = table(lambda r: r['cause'], lossrows)[0]
        hint = {'one event': 'one shock hit many holdings together: idea asia-overnight, question 45', 'its market': 'whole markets fell: idea market-mood, questions 9 and 31',
                'the share': 'shares fell by themselves: was it news? headlines at a sale are not recorded yet (idea loss-news); the loss limit, question 11'}.get(lead[0], '')
        print(f"FINDING: most of the money lost was '{lead[0]}' (${-lead[1][1]:,.0f}): {hint}")

if __name__ == '__main__':
    main()
