"""The review of the AI autopilot (fake money) that a session runs every week or two. READ-ONLY: it reads the account's
record, its diary, the shared record and the function's log, and prints what happened in plain figures. It changes
nothing, it is not a visit to the dashboard, and it never prints the account's address.

    python3 check-tools/autopilot_review.py                       the only account with the autopilot switched on, last 14 days
    python3 check-tools/autopilot_review.py --days 7
    python3 check-tools/autopilot_review.py --account <address>   when more than one account has it on (or the one wanted is off)
    python3 check-tools/autopilot_review.py --out check-tools/reviews/review-2026-10-26.txt

What it is for, and how to read it: site-overview.md section 8c, "The review every week or two". In short: judge by
dollars and by the average per trade against the margin of error, never by the share of trades that ended up; a group
with fewer than 30 finished trades says nothing yet; an idea that comes out of a review is replayed on saved prices
first and then tried live beside the current rule, never adopted from hindsight.

Where the figures come from: table stockiq-ai-trader (the account's item, and _brain, the record every account learns
from), table stockiq-ai-trader-journal (the diary, never trimmed; it starts on 12 Oct 2026), table
stockiq-paper-portfolios (what each holding cost), and the log group /aws/lambda/stockiq-ai-trader.
"""
import argparse, base64, importlib.util, json, math, os, sys, zlib
from datetime import datetime, timedelta, timezone
import boto3
from boto3.dynamodb.conditions import Key

HERE = os.path.dirname(os.path.abspath(__file__))
MIN_GROUP = 30                                              # fewer finished trades than this in a group: no reading
BAR = 300                                                   # the number of finished trades the panel's own "bar to clear" asks for
FAULTS = ['check-in failed', 'not worked out', 'not sent', 'not written', 'learning failed', 'not read', 'not shared', 'Task timed out', 'Traceback']
# The goals the owner asked for on 12 Oct 2026 ("month 1 it improves x amount month 2 y amount"). Targets to measure against,
# not forecasts: site-overview.md section 8c, "The goals, month by month". Each: the day it is due, its name, the number of
# finished trades in all by then, the average result a trade after costs of the trades finished in that month, and the
# account's value. The start: 12 Oct 2026, five finished trades averaging -1.03%, the account at about $98,600.
# The owner had the first two raised the same day ("this is negative? we want positive. profit not loss"): every month's
# goal is a profit; the first versions asked month 1 only to stop losing (-0.2% a trade, $98,000).
GOALS_START = '2026-10-12'
GOALS = [('2026-11-12', 'Month 1: in profit', 100, 0.0, 100000),
         ('2026-12-12', 'Month 2: in profit, and more of it', 300, 0.2, 101000),
         ('2027-01-12', 'Month 3: clearly ahead, or a decision', 500, 0.3, 102000)]
EXITS = {'stop': 'at the loss limit', 'take': 'at the gain mark', 'trail': 'by the stop that followed it', 'cut': 'by its trailing stop before it had risen',
         'time': 'at the time limit', 'signal': 'signal or score turned', 'fade': 'slipped down the ranking', 'ai': 'by the AI review', 'hand': 'by the owner'}
out_lines = []


def say(text=''):
    out_lines.append(text); print(text)


def parse(t):
    try: return datetime.strptime(str(t)[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
    except Exception: return None


def stats(values):
    """count, average, margin of error (one standard error), sum"""
    v = [x for x in values if isinstance(x, (int, float))]
    if not v: return 0, 0.0, 0.0
    avg = sum(v) / len(v)
    se = math.sqrt(sum((x - avg) ** 2 for x in v) / (len(v) - 1) / len(v)) if len(v) > 1 else 0.0
    return len(v), avg, se


def line(name, trades, width=34):
    n, avg, se = stats([t.get('pct') for t in trades]); usd = sum(t.get('usd') or 0 for t in trades); up = sum(1 for t in trades if (t.get('pct') or 0) > 0)
    reading = 'too few to read' if n < MIN_GROUP else ('clearly up' if avg > 2 * se else 'clearly down' if avg < -2 * se else 'inside the margin of error')
    return f"  {name[:width]:<{width}} {n:>4} trades  {up:>3} up  average {avg:+6.2f}% (± {se:4.2f})  {usd:>+11,.2f} USD   {reading}"


def breakdown(title, trades, key, order=None):
    groups = {}
    for t in trades: groups.setdefault(key(t), []).append(t)
    if not groups: return
    say(f"\n{title}")
    names = order or sorted(groups, key=lambda g: sum(x.get('usd') or 0 for x in groups[g]))     # the most money lost first
    for g in names:
        if g in groups: say(line(str(g), groups[g]))


def band(value, edges, labels):
    if not isinstance(value, (int, float)): return 'not recorded'
    for edge, label in zip(edges, labels):
        if value <= edge: return label
    return labels[-1]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--account'); ap.add_argument('--days', type=float, default=14); ap.add_argument('--out'); a = ap.parse_args()
    s = boto3.Session(profile_name='default', region_name='us-east-1'); db = s.resource('dynamodb')
    table = db.Table('stockiq-ai-trader'); now = datetime.now(timezone.utc); start = now - timedelta(days=a.days)
    spec = importlib.util.spec_from_file_location('trader', os.path.join(HERE, '..', 'lambda-sync', 'stockiq-ai-trader', 'lambda_function.py'))
    os.environ.setdefault('AI_TRADER_USERS', ''); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    name_of = lambda key: (m.SCREENERS.get(key) or (key,))[0]; group_of = lambda key: (m.SCREENERS.get(key) or (None,) * 6)[5] or 'other'

    account = a.account or os.environ.get('REVIEW_ACCOUNT')
    if not account:
        ids, more = [], {}
        while True:
            page = table.scan(ProjectionExpression='userId, #e', ExpressionAttributeNames={'#e': 'enabled'}, **more)
            ids += [r['userId'] for r in page['Items'] if not r['userId'].startswith('_') and r.get('enabled')]       # switched on: a test account that never ran is passed over
            if 'LastEvaluatedKey' not in page: break
            more = {'ExclusiveStartKey': page['LastEvaluatedKey']}
        if len(ids) != 1: sys.exit(f"{len(ids)} accounts have the autopilot switched on: name one with --account <address>")
        account = ids[0]
    item = table.get_item(Key={'userId': account}).get('Item')
    if not item: sys.exit('that account has no autopilot record')
    rec = json.loads(item['data']); settings, state = rec['settings'], rec.get('state') or {}

    diary, more = [], {}
    while True:
        page = db.Table('stockiq-ai-trader-journal').query(KeyConditionExpression=Key('userId').eq(account), **more); diary += page['Items']
        if 'LastEvaluatedKey' not in page: break
        more = {'ExclusiveStartKey': page['LastEvaluatedKey']}
    rows = lambda kind: [dict(json.loads(r['data']), _at=r['at']) for r in diary if r['kind'] == kind]
    trades = {(t.get('id'), t.get('sold')): t for t in rec.get('history', [])}
    trades.update({(t.get('id'), t.get('sold')): t for t in rows('trade')})                  # the diary is the fuller one as time goes on
    trades = sorted((t for t in trades.values() if t.get('pct') is not None), key=lambda t: str(t.get('sold')))
    inside = [t for t in trades if (parse(t.get('sold')) or now) >= start]
    lines_all = sorted(rows('log') or rec.get('log', []), key=lambda e: str(e.get('t'))); lines = [e for e in lines_all if (parse(e.get('t')) or now) >= start]

    say(f"REVIEW OF THE AI AUTOPILOT (fake money)   {start:%d %b %Y %H:%M} to {now:%d %b %Y %H:%M} UTC ({a.days:g} days)")
    say("Read-only. Past practice results; nothing here is a forecast. Judge by dollars and the average per trade, not by how many ended up.")

    say("\n1. SETTINGS")
    r = m.rules_for(settings, state)
    say(f"  now: {'ON' if settings['enabled'] else 'OFF'}, {m.RISK[settings['risk']]['name']} level, {m.holdings_of(settings)} holdings"
        f"{' (set by hand)' if settings.get('holdings') else ''}, budget ${settings['budgetUsd']:,.0f} over {settings['periodDays']:g} days, checks in every {settings['everyHours']:g} h, "
        f"keeps a holding at most {settings['maxHoldDays']:g} days; loss limit {r['stop']}%, gain mark +{r['take']}%, buys from the top {r['top']}; trailing stop '{settings.get('trailMode')}'")
    say(f"  screeners: {', '.join(name_of(k) for k in settings['screeners']) or 'none'}")
    changes = [x for x in rows('settings') if (parse(x['_at']) or now) >= start]
    say(f"  changes of the settings in the period: {len(changes)}" + ('' if rows('settings') else ' (the diary has none yet: it starts on 12 Oct 2026)'))
    last = None
    for x in changes[-12:]:
        shown = {k: x.get(k) for k in ('enabled', 'risk', 'holdings', 'budgetUsd', 'periodDays', 'everyHours', 'maxHoldDays', 'trailMode', 'stopPct', 'takePct')}; shown['screeners'] = len(x.get('screeners') or [])
        diff = {k: v for k, v in shown.items() if last is None or last.get(k) != v}; last = shown
        say(f"    {x['_at'][:16]}  " + ', '.join(f"{k} {v}" for k, v in diff.items()))
    if len(changes) > 3: say("  NOTE: the settings changed several times; trades made under different settings are not one experiment.")

    say("\n2. THE RESULT IN DOLLARS")
    say(line('finished in the period', inside)); say(line('finished, all recorded', trades))
    try:
        port = None; port = json.loads(db.Table('stockiq-paper-portfolios').get_item(Key={'userId': account})['Item']['data']); cost = {h['id']: h.get('costUsd') or 0 for h in port.get('holdings', []) if h.get('by') == 'ai'}
    except Exception: cost = {}
    held, paper = state.get('open') or {}, 0.0
    for hid, h in held.items(): paper += (cost.get(hid) or 0) * ((h.get('path') or [[0, 0]])[-1][1]) / 100
    say(f"  still held: {len(held)} holdings, ${sum(cost.get(i) or 0 for i in held):,.0f} put in, about {paper:+,.2f} USD on paper at their last check-in (not final; the dashboard has the live figure)")
    n, avg, se = stats([t.get('pct') for t in trades])
    say(f"  the bar: {BAR} finished trades whose average is clearly ahead. So far {n}. " + ("Far too few to judge anything: read what follows as a diary, not as evidence." if n < MIN_GROUP else f"Average {avg:+.2f}% ± {se:.2f}."))
    shares = [t for t in trades if group_of(t.get('screener')) != 'Coins' and isinstance(t.get('vs'), (int, float))]
    if shares:
        n, avg, se = stats([t['vs'] for t in shares]); say(f"  shares against an S&P 500 fund over the same days: {avg:+.2f}% a trade (± {se:.2f}, {n} trades)")

    say("\n3. WHERE THE MONEY WENT (finished trades, all recorded; the group that lost most first)")
    breakdown('by how it was sold', trades, lambda t: EXITS.get(t.get('exit'), str(t.get('exit'))))
    breakdown('by market', trades, lambda t: group_of(t.get('screener')))
    breakdown('by screener', trades, lambda t: name_of(t.get('screener')))
    breakdown('by place in the ranking when bought', trades, lambda t: band(t.get('rank'), [3, 10, 20, 10 ** 9], ['rank 1 to 3', 'rank 4 to 10', 'rank 11 to 20', 'rank 21 and lower']))
    breakdown('by RSI when bought', trades, lambda t: band(t.get('rsi'), [50, 65, 75, 10 ** 9], ['RSI to 50', 'RSI 50 to 65', 'RSI 65 to 75', 'RSI above 75']))
    breakdown('by how long it was held', trades, lambda t: band(t.get('days'), [0.25, 1, 5, 10 ** 9], ['under 6 hours', '6 hours to a day', '1 to 5 days', 'over 5 days']))
    breakdown('by who chose it', trades, lambda t: {'ai': 'the AI model', 'rank': 'by rank (the model did not answer)', 'order': 'furthest above its 52-week low (trial)'}.get(t.get('chosen'), str(t.get('chosen'))))
    breakdown('by headlines shown to the model when it was bought (recorded from 12 Oct 2026)', trades, lambda t: 'not recorded (bought before)' if t.get('heads') is None else 'none found' if not t['heads'] else 'newest under a day old' if (t.get('headAge') or 0) < 24 else 'newest one to three days old')
    breakdown('the patient-shares trial (from 12 Oct 2026: a patient share is not sold on the signal, nor by the AI review)', [t for t in trades if t.get('pt') is not None], lambda t: 'patient: sold by price or time only' if t.get('pt') == 1 else 'ordinary: also sold when the signal turns')
    breakdown('by risk level at the time', trades, lambda t: m.RISK.get(t.get('risk'), {}).get('name', str(t.get('risk'))))

    say("\n4. THE LOSSES, ONE BY ONE (finished in the period, worst first)")
    for t in sorted((t for t in inside if (t.get('usd') or 0) < 0), key=lambda t: t.get('usd') or 0)[:15]:
        after = f"; in the same time again after the sale it went {t['after']:+.1f}%" if isinstance(t.get('after'), (int, float)) else ''
        say(f"  {t.get('label')}: {t.get('pct'):+.2f}% ({t.get('usd'):+,.2f} USD) in {t.get('days', 0):.1f} days, sold {EXITS.get(t.get('exit'), t.get('exit'))}. "
            f"Bought at rank {t.get('rank')} of {name_of(t.get('screener'))}, score {t.get('score')}, RSI {t.get('rsi')}, 30-day move {t.get('d30')}%. Best {t.get('peak', 0):+.1f}%, worst {t.get('low', 0):+.1f}%{after}.")
        if (t.get('view') or {}).get('text'): say(f"      the AI review's last word: {t['view']['text'][:200]}")
    if not any((t.get('usd') or 0) < 0 for t in inside): say("  none")
    gave = [t for t in trades if (t.get('peak') or 0) >= 2 and (t.get('pct') or 0) <= 0]
    say(f"\n  had been up 2% or more and still ended down: {len(gave)} of {len(trades)}" + (f" ({', '.join(str(t.get('label')) for t in gave[:8])}); a stop only acts at a check-in" if gave else ''))
    later = [t for t in trades if isinstance(t.get('after'), (int, float))]
    if later:
        say("  what sold holdings did in the same length of time again (a plus means it was sold too early, a minus that selling saved money):")
        groups = {}
        for t in later: groups.setdefault(EXITS.get(t.get('exit'), str(t.get('exit'))), []).append(t['after'])
        for g, v in sorted(groups.items()): n, avg, se = stats(v); say(f"    sold {g:<42} {n:>3} trades  went on {avg:+.2f}% (± {se:.2f})")

    say("\n5. WHAT IT DID AND DID NOT DO (activity lines in the period)")
    kinds = {k: sum(1 for e in lines if e.get('type') == k) for k in ('buy', 'sell', 'note')}
    say(f"  {kinds['buy']} buys, {kinds['sell']} sales, {kinds['note']} notes" + ('' if rows('log') else ' (from the record: only its last 80 lines; the diary fills from 12 Oct 2026)'))
    idle = {}
    for e in lines:
        if e.get('type') == 'note' and e.get('key'):
            for part in str(e['key']).split('+'): idle[part] = idle.get(part, 0) + int(e.get('n', 1))
    words = {'pace': 'waiting for the next step of the budget', 'full': 'every holding filled', 'cash': 'too little practice cash', 'share': 'open markets already hold their share', 'shut': 'no market open',
             'none': 'nothing on the shortlist fit to buy', 'nodata': 'screener data not available', 'same': 'nothing changed', 'stay': 'a coin had not stayed near the top yet', 'stale': 'a share left alone: its price was old'}
    for k, c in sorted(idle.items(), key=lambda x: -x[1]): say(f"    {c:>4} check-ins: {words.get(k, k)}")
    for e in [e for e in lines if 'Left alone' in str(e.get('text'))][-3:]: say(f"    {str(e.get('t'))[:16]}  {str(e.get('text'))[:170]}")

    say("\n6. WHAT IT HAS LEARNED AND IS TRYING (the record every account learns from)")
    try:
        brain = json.loads(zlib.decompress(base64.b64decode(table.get_item(Key={'userId': '_brain'})['Item']['z'])))
    except Exception as e:
        brain = None; say(f"  the shared record could not be read: {type(e).__name__}")
    if brain:
        pool = brain.get('pool') or []; say(line('every account together', pool)); say(f"  {brain.get('count', 0)} finished trades taken in from {len(brain.get('accounts') or [])} account(s); per level: {brain.get('counts')}")
        for level, tune in sorted((brain.get('tunes') or {}).items()):
            trial = tune.get('trial')
            say(f"  level {level}: rules changed after a trial: {tune.get('values') or 'none'}; trial running: {(trial or {}).get('text') or (trial or {}).get('param') or 'none'}; earlier trials: {len(tune.get('past') or [])}")
            for p in (tune.get('past') or [])[-4:]: say(f"      {str(p.get('ended') or p.get('at'))[:10]} {p.get('param')} {p.get('from')} -> {p.get('to')}: {'kept' if p.get('kept') else 'not kept'}{' (put back)' if p.get('undone') else ''} {str(p.get('why') or '')[:110]}")
        order = (brain.get('state') or {}).get('order') or {}
        if order:
            sides = {o: [t for t in pool if t.get('o') == o] for o in ('low52', 'rank')}
            say(f"  trial of which share to buy: {order.get('mode')} since {str(order.get('since'))[:10]}")
            for o, label in (('low52', 'furthest above its 52-week low'), ('rank', 'as ranked')): say(line('  ' + label, sides[o]))
        rest = (brain.get('state') or {}).get('rest') or {}
        say(f"  screeners rested: {', '.join(f'{name_of(k)} until {str(v)[:10]}' for k, v in rest.items()) or 'none'}")
        for level, prog in sorted((brain.get('progress') or {}).items()):
            for rep in (prog.get('reports') or [])[-2:]: say(f"  progress report, level {level}, batch {rep.get('no')}: average {rep.get('avg')}%, verdict {rep.get('verdict')}; did: {'; '.join(map(str, rep.get('actions') or [])) [:200] or 'carried on'}")
        for note in ((brain.get('state') or {}).get('lessons') or {}).get('items', []): say(f"  note: {note}")
    pat = [h for h in held.values() if h.get('pt') == 1]; plain = [h for h in held.values() if h.get('pt') == 0]
    now_at = lambda group: (sum((h.get('path') or [[0, 0]])[-1][1] for h in group) / len(group)) if group else 0.0
    say(f"  the patient-shares trial, still held: {len(pat)} patient (on paper {now_at(pat):+.2f}% on average at their last check-in), {len(plain)} ordinary ({now_at(plain):+.2f}%). "
        "A fair comparison counts both: what was sold and what is still held, for buys of the same weeks.")
    say(f"  this account: trial of the buying order '{(state.get('order') or {}).get('mode')}', {(state.get('order') or {}).get('buys', 0)} share buys counted; AI calls today {((state.get('ai') or {}).get('n'))}; early sells by the AI review {'paused' if (state.get('aiSell') or {}).get('until') else 'allowed'}")

    say("\n7. FAULTS IN THE FUNCTION'S LOG (the period)")
    logs, found, token = s.client('logs'), [], None
    try:
        for _ in range(40):
            page = logs.filter_log_events(logGroupName='/aws/lambda/stockiq-ai-trader', startTime=int(start.timestamp() * 1000), filterPattern=' '.join(f'?"{f}"' for f in FAULTS), **({'nextToken': token} if token else {}))
            found += page.get('events', []); token = page.get('nextToken')
            if not token: break
        counts = {}
        for e in found:
            for f in FAULTS:
                if f in e['message']: counts[f] = counts.get(f, 0) + 1
        say(f"  {len(found)} lines" + (': ' + ', '.join(f"'{k}' {v}" for k, v in sorted(counts.items(), key=lambda x: -x[1])) if found else ': none'))
        for e in found[-6:]: say(f"    {datetime.fromtimestamp(e['timestamp'] / 1000, timezone.utc):%d %b %H:%M}  {e['message'].strip()[:190]}")
    except Exception as e:
        say(f"  the log could not be read: {type(e).__name__}: {e}")

    say("\n8. THE RECORD ITSELF")
    size = len(item['data'].encode()); kept = len(rec.get('history', []))
    say(f"  the account's record is {size / 1024:.0f} KB (a row can hold 400 KB): {kept} of {m.HISTORY_KEEP} finished trades kept, {len(rec.get('log', []))} of {m.LOG_KEEP} activity lines, {len(held)} holdings remembered"
        + ('   WARNING: over 300 KB, look at what is growing' if size > 300 * 1024 else ''))
    say(f"  the diary: {len(diary)} rows in all ({sum(1 for r in diary if r['kind'] == 'log')} activity lines, {sum(1 for r in diary if r['kind'] == 'trade')} finished trades, {sum(1 for r in diary if r['kind'] == 'settings')} settings), first {min((r['at'] for r in diary), default='none')[:16]}")
    unsent = sum(1 for e in rec.get('log', []) if not e.get('j')) + sum(1 for t in rec.get('history', []) if t.get('pct') is not None and not t.get('j'))
    say(f"  not yet in the diary: {unsent} (they go with the record's next save)")

    say("\n9. AGAINST THE GOALS (targets set on 12 Oct 2026, not forecasts)")
    value = (port['cash'] + sum(h.get('costUsd') or 0 for h in port.get('holdings', [])) + paper) if port else None
    today, before = now.strftime('%Y-%m-%d'), GOALS_START
    for due, name, want_n, want_avg, want_value in GOALS:
        month = [t for t in trades if before <= str(t.get('sold'))[:10] < due]
        n_m, avg_m, se_m = stats([(t.get('pct') or 0) - (0 if t.get('c') else 0.2) for t in month])      # a trade from before costs were taken off is charged them here
        if today >= due and due != GOALS[-1][0]:
            say(f"  {name} (due {due}): past. It ended with {len([t for t in trades if str(t.get('sold'))[:10] < due])} finished trades and {avg_m:+.2f}% a trade in its month ({n_m} trades).")
            before = due; continue
        span = (parse(due + 'T00:00:00') - parse(before + 'T00:00:00')).days; gone = max(0, (now - parse(before + 'T00:00:00')).days)
        start_n = len([t for t in trades if str(t.get('sold'))[:10] < before]); pace = start_n + (want_n - start_n) * min(1, gone / span)
        say(f"  {name}. Due {due} ({max(0, span - gone)} days left).")
        say(f"    finished trades in all:           {len(trades):>5}   target {want_n}   " + ('reached' if len(trades) >= want_n else 'on course' if len(trades) >= pace - 0.5 else f'behind (about {pace:.0f} by today at an even pace)'))
        say(f"    average a trade this month:       {avg_m:+5.2f}% (± {se_m:.2f}, {n_m} trades, after costs)   target {want_avg:+.1f}% or better   " + ('too few to read' if n_m < MIN_GROUP else 'reached' if avg_m >= want_avg else 'not yet'))
        if value is not None: say(f"    the account, about:            ${value:>10,.0f}   target ${want_value:,.0f} or more   " + ('reached' if value >= want_value else 'not yet'))
        break
    say("  If a month's goal is missed: say so first thing, say why, and bring the changes that follow from it (the notes, same part).")
    say("\nWHAT TO DO WITH THIS: site-overview.md section 8c, 'The review every week or two'.")
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True); open(a.out, 'w').write('\n'.join(out_lines) + '\n'); print(f"\nsaved as {a.out}")


if __name__ == '__main__':
    main()
