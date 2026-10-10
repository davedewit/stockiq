"""Does the autopilot panel describe what the autopilot function really does?
The panel (practice-autopilot.js, buildUp) works out for the chosen settings how many holdings it builds up to, how
much of the budget that is and after how long. This replays the Lambda's own rules for 3,780 combinations of settings
and compares. Nothing real is touched (stand-in storage, prices and screener results).

   python3 check-tools/autopilot_plan_check.py lambda-sync/stockiq-ai-trader/lambda_function.py ../website/practice-autopilot.js [N]

N (optional, e.g. 150): also run that many of the combinations as whole check-ins through run_user(). Slower."""
import importlib.util, json, subprocess, datetime as dt, itertools, os, math, sys, copy, random, tempfile
os.environ['AI_TRADER_USERS'] = 'tester@x.com'
spec = importlib.util.spec_from_file_location('tr', sys.argv[1]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
HERE = os.path.dirname(os.path.abspath(__file__)) + '/'
class T:
    def __init__(s): s.rows = {}
    def get_item(s, Key): r = s.rows.get(Key['userId']); return {'Item': copy.deepcopy(r)} if r else {}
    def put_item(s, Item, **k): s.rows[Item['userId']] = copy.deepcopy(Item)
class DB:
    def __init__(s): s.t = {}
    def Table(s, n): return s.t.setdefault(n, T())
cases = []
for b, p, e, h, r, coins in itertools.product((10000, 2500, 77777), (1, 10, 30), m.EVERY_HOURS, (0.5, 1, 3, 6, 24, 48, 480), (1, 2, 3, 4, 5), (False, True)):
    R = m.RISK[r]; cases.append(dict(budgetUsd=b, periodDays=p, everyHours=e, maxHoldDays=h / 24, risk=r, positions=R['positions'], coins=coins, limit=b))      # only coins ticked: the whole budget may go into coins (coin_share)
t0 = dt.datetime(2026, 1, 5)
def checkins(c): return math.ceil(c['periodDays'] * 24 / c['everyHours']) + m.RISK[c['risk']]['positions'] + 2
def light(c):
    """The function's own allowance() and review_sells(), with the buying lines of run_user() written out."""
    settings = dict(m.DEFAULTS, **{k: c[k] for k in ('budgetUsd', 'periodDays', 'everyHours', 'maxHoldDays', 'risk')}); state = {'startedAt': m.iso(t0)}
    R = m.RISK[c['risk']]; p = {'cash': 1e9, 'holdings': [], 'closed': []}; size = c['budgetUsd'] / R['positions']
    first = peak = count = hours = 0
    for n in range(checkins(c)):
        now = t0 + dt.timedelta(hours=n * c['everyHours'])
        for h, price, reason in m.review_sells(p, settings, {}, {'X': {'price': 10.0}, 'X-USD': {'price': 10.0}}, now, {}, None, {}): p['holdings'].remove(h)
        room, invested = m.allowance(p, settings, state, now)
        crypto_room = c['budgetUsd'] * (1.0 if c['coins'] else R['crypto']) - sum(h['costUsd'] for h in p['holdings'] if h['symbol'].endswith('-USD'))
        for i in range(min(m.MAX_BUYS_PER_CHECK, int((room + 0.01 * R['positions']) // size))):
            amount = min(size, p['cash'], room)
            if c['coins']: amount = min(amount, crypto_room)
            if amount < m.MIN_TRADE_USD: continue
            p['holdings'].append({'id': f'{n}-{i}', 'symbol': 'X-USD' if c['coins'] else 'X', 'by': 'ai', 'costUsd': round(amount, 2), 'buyPrice': 10.0, 'currency': 'USD', 'boughtAt': m.iso(now), 'screener': '7-1' if c['coins'] else '3-100'})
            room -= round(amount, 2)
            if c['coins']: crypto_room -= amount
            if n == 0: first += 1
        inv = sum(h['costUsd'] for h in p['holdings'])
        if inv > peak + 0.05: peak, count, hours = inv, len(p['holdings']), n * c['everyHours']
    return {'first': first, 'peak': peak, 'count': count, 'hours': hours}
def full(c):
    """Whole check-ins through run_user() with stand-in storage, prices and screener results (always something new to buy)."""
    D = DB(); m._db = D; key = '7-1' if c['coins'] else '3-100'; kind = 'crypto' if c['coins'] else 'stock'
    rec = {'settings': dict(m.DEFAULTS, enabled=True, screeners=[key], **{k: c[k] for k in ('budgetUsd', 'periodDays', 'everyHours', 'maxHoldDays', 'risk')}), 'state': {'startedAt': m.iso(t0)}, 'log': [], 'history': []}
    first = peak = count = hours = 0; step = [0]
    def snapshot(k): return [dict(symbol=f'N{step[0]}I{i}' + ('-USD' if c['coins'] else ''), label=f'N{step[0]}I{i}', kind=kind, screener=key, price=10.0, score=4.0 - i * 0.1, signal='BUY', rsi=50, d1=1.0, d7=3.0, d30=5.0, volume=1.2, from_high=-5.0, macd='BULLISH', position=i, rank=i + 1) for i in range(5)]
    quote = lambda sym: {'price': 10.0, 'currency': 'USD', 'name': sym}
    for n in range(checkins(c)):
        step[0] = n; now = t0 + dt.timedelta(hours=n * c['everyHours'])
        s = m.run_user('tester@x.com', rec, now, snapshot=snapshot, quote=quote, model=lambda prompt: None)
        if n == 0: first = s['bought']
        row = D.Table(m.PORTFOLIO_TABLE).rows.get('tester@x.com'); held = [h for h in json.loads(row['data'])['holdings'] if h.get('by') == 'ai'] if row else []; inv = sum(h['costUsd'] for h in held)
        if inv > c['budgetUsd'] + 0.001: return {'over budget': inv}
        if inv > peak + 0.05: peak, count, hours = inv, len(held), n * c['everyHours']
    return {'first': first, 'peak': peak, 'count': count, 'hours': hours}
with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f: json.dump(cases, f)
ours = json.loads(subprocess.run(['node', HERE + 'autopilot_plan_check.js', sys.argv[2], f.name], capture_output=True, text=True, check=True).stdout); os.unlink(f.name)
same = lambda a, b: 'peak' in b and a['first'] == b['first'] and a['count'] == b['count'] and a['hours'] == b['hours'] and abs(a['peak'] - b['peak']) < 0.1
show = lambda c: ({k: c[k] for k in ('budgetUsd', 'periodDays', 'everyHours', 'risk', 'coins')}, 'hold hours', c['maxHoldDays'] * 24)
bad = [(c, a, s) for c, a, s in ((c, a, light(c)) for c, a in zip(cases, ours)) if not same(a, s)]
print('budget and selling rules replayed for', len(cases), 'combinations of settings | panel differs from the function in:', len(bad))
for c, a, s in bad[:6]: print('  ', *show(c), '\n     panel', a, '\n     function', s)
k = int(sys.argv[3]) if len(sys.argv) > 3 else 0
if k:
    random.seed(7); pick = random.sample([i for i, c in enumerate(cases) if checkins(c) <= 500], k)
    bad = [(cases[i], ours[i], s) for i, s in ((i, full(cases[i])) for i in pick) if not same(ours[i], s)]
    print('whole check-ins replayed for', k, 'of them | panel differs from the function in:', len(bad))
    for c, a, s in bad[:6]: print('  ', *show(c), '\n     panel', a, '\n     function', s)
