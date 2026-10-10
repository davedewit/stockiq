"""Tests of the AI trader with stand-ins for the database, the screeners, prices and the AI model. Nothing real is touched."""
import importlib.util, json, sys, copy, os, datetime as dt
import boto3
from botocore.exceptions import ClientError
class T:
    def __init__(s): s.rows = {}; s.fail_next = False
    def get_item(s, Key): r = s.rows.get(Key['userId']); return {'Item': copy.deepcopy(r)} if r else {}
    def scan(s, **k): return {'Items': [copy.deepcopy(r) for r in s.rows.values()]}
    def put_item(s, Item, ConditionExpression=None, ExpressionAttributeValues=None):
        cur = s.rows.get(Item['userId'])
        if ConditionExpression and (s.fail_next or (cur is not None and cur['version'] != ExpressionAttributeValues[':v'])):
            s.fail_next = False; raise ClientError({'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'x'}}, 'PutItem')
        s.rows[Item['userId']] = copy.deepcopy(Item)
class DB:
    def __init__(s): s.t = {}
    def Table(s, n): return s.t.setdefault(n, T())
os.environ['AI_TRADER_USERS'] = 'dave@x.com, tester@x.com'
spec = importlib.util.spec_from_file_location('tr', sys.argv[1]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
D = DB(); m._db = D
U = 'tester@x.com'
ok = True
def check(name, cond, extra=''):
    global ok; ok = ok and bool(cond); print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f'   {extra}'))

def rows(kind='stock', key='3-100', n=25, **over):
    out = []
    for i in range(n):
        sym = (f'C{i:02d}-USD' if kind == 'crypto' else f'S{i:02d}')
        r = dict(symbol=sym, label=sym, kind=kind, screener=key, price=100.0 + i, score=round(4.0 - i * 0.2, 1), signal='BUY' if i < 15 else 'HOLD',
                 rsi=50 + i, d1=1.0, d7=3.0, d30=5.0 + i * 3, volume=1.2, from_high=-5.0, macd='BULLISH', position=i, rank=i + 1)
        r.update(over.get(sym, {})); out.append(r)
    return out
SNAP = {'3-100': rows(), '7-1': rows('crypto', '7-1')}
PRICES = {}
def snapshot(k): return copy.deepcopy(SNAP.get(k))
def quote(sym):
    if sym == 'SPY': return {'price': 700.0, 'currency': 'USD', 'name': 'S&P 500 fund'}
    for k in SNAP:
        for r in SNAP[k]:
            if r['symbol'] == sym: return {'price': PRICES.get(sym, r['price']), 'currency': 'USD', 'name': 'Name of ' + sym}
    return None
MODEL = {'answer': None, 'prompts': []}
def model(prompt): MODEL['prompts'].append(prompt); return copy.deepcopy(MODEL['answer'])
def call(**b): r = m.lambda_handler({'requestContext': {}, 'body': json.dumps(b)}, None); return r['statusCode'], json.loads(r['body'])
def portfolio(): it = D.Table(m.PORTFOLIO_TABLE).rows.get(U); return json.loads(it['data']) if it else None
def run(now, **settings):
    rec = m.load_item(U)
    if settings: rec['settings'].update(settings)
    s = m.run_user(U, rec, now, snapshot=snapshot, quote=quote, model=model); m.save_item(U, rec); return s, rec
t0 = dt.datetime(2026, 10, 12, 15, 0, 0)          # a Monday, US market open

# --- access and settings
check('someone not on the list is refused', call(action='get', userId='stranger@y.com')[1] == {'success': True, 'allowed': False})
check('not on the list cannot switch it on', m.clean_settings({'enabled': True}, 'stranger@y.com')['enabled'] is False)
s, b = call(action='get', userId=U); check('defaults', b['allowed'] and b['settings'] == dict(m.DEFAULTS) and '3-100' in b['options']['screeners'], b)
s, b = call(action='save', userId=U, settings={'enabled': True, 'risk': 9, 'budgetUsd': 'lots', 'periodDays': 0.2, 'everyHours': 7, 'maxHoldDays': 5, 'screeners': ['3-100', 'nope'], 'x': 1})
check('settings are cleaned', b['settings'] == {'enabled': True, 'risk': 5, 'budgetUsd': 10000.0, 'periodDays': 1, 'everyHours': 24, 'maxHoldDays': 5, 'screeners': ['3-100']} and b['state'].get('startedAt') and b['log'][-1]['text'].startswith('Autopilot on'), b['settings'])
check('run before switching on is refused', call(action='run', userId='dave@x.com')[0] == 400)
check('garbage requests', m.lambda_handler({'requestContext': {}, 'body': 'x'}, None)['statusCode'] == 400 and call(action='zzz', userId=U)[0] == 400 and call(action='get')[0] == 400)

# --- pacing: $8,000 over 4 days, daily, Balanced (8 holdings of $1,000)
D.t.clear()
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=4, everyHours=24, maxHoldDays=20, screeners=['3-100']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
MODEL['answer'] = {'picks': [{'symbol': 'S03', 'reason': 'Rank 4 with RSI 53 and steady volume'}, {'symbol': 'ZZZZ', 'reason': 'not on the list'}, {'symbol': 'S01', 'reason': 'x' * 400}]}
s, rec = run(t0); p = portfolio()
check('day 1: buys 2 x $1,000 (a quarter of the budget)', s['bought'] == 2 and len(p['holdings']) == 2 and p['cash'] == 98000 and all(h['costUsd'] == 1000 and h['by'] == 'ai' and h['screener'] == '3-100' for h in p['holdings']), (s, p and p['cash']))
check('the AI model chose, and an unlisted symbol was ignored', s['decidedBy'] == 'ai' and [h['symbol'] for h in p['holdings']] == ['S03', 'S01'] and p['holdings'][0]['note'] == 'AI: Rank 4 with RSI 53 and steady volume' and len(p['holdings'][1]['note']) <= 200, [h['symbol'] for h in p['holdings']])
check('the prompt carries the data and the limits', 'Pick exactly 2' in MODEL['prompts'][-1]['user'] and 'S00 | S&P 100 rank 1 | score +4.0' in MODEL['prompts'][-1]['user'] and 'fake' in MODEL['prompts'][-1]['system'])
check('holding fields match what the dashboard expects', set(p['holdings'][0]) == {'id', 'symbol', 'label', 'name', 'currency', 'qty', 'buyPrice', 'buyFx', 'costUsd', 'boughtAt', 'spyAtBuy', 'note', 'by', 'screener'} and abs(p['holdings'][0]['qty'] - 1000 / 103) < 1e-9 and p['holdings'][0]['spyAtBuy'] == 700)
s, rec = run(t0 + dt.timedelta(hours=1)); check('an hour later: nothing more yet', s['bought'] == 0 and 'spread over 4 days' in rec['log'][-1]['text'], rec['log'][-1])
MODEL['answer'] = None
s, rec = run(t0 + dt.timedelta(days=1)); p = portfolio()
check('day 2: 2 more, chosen by score because the model gave nothing', s['bought'] == 2 and s['decidedBy'] == 'rules' and [h['symbol'] for h in p['holdings']][2:] == ['S00', 'S02'] and 'chosen by rank' in rec['log'][-1]['text'], [h['symbol'] for h in p['holdings']])
s, rec = run(t0 + dt.timedelta(days=5)); p = portfolio()
check('never more than 3 buys in one check-in', s['bought'] == 3 and len(p['holdings']) == 7)
s, rec = run(t0 + dt.timedelta(days=6)); s2, rec = run(t0 + dt.timedelta(days=7)); p = portfolio()
check('stops at the budget: 8 holdings, $8,000', len(p['holdings']) == 8 and p['cash'] == 92000 and s2['bought'] == 0 and 'fully invested' in rec['log'][-1]['text'], (len(p['holdings']), p['cash'], rec['log'][-1]['text']))

# --- risk filters
view = lambda risk, scr=('3-100',): [c['symbol'] for c in m.shortlist(m.new_portfolio(t0), dict(m.DEFAULTS, risk=risk, screeners=list(scr)), SNAP, t0)]
check('Cautious: top 5 only, and nothing that has run 20%+ in a month', view(1) == ['S00', 'S01', 'S02', 'S03', 'S04'], view(1))
check('Adventurous looks further down, but only at positive signals', view(5) == [f'S{i:02d}' for i in range(15)], view(5))
check('coins need Balanced or above', view(2, ('3-100', '7-1')) == view(2) and any(x.startswith('C') for x in view(3, ('3-100', '7-1'))))
SNAP['3-100'][0]['rsi'] = 80; check('an overbought leader is left out at Balanced', 'S00' not in view(3) and 'S00' in view(5)); SNAP['3-100'][0]['rsi'] = 50

# --- crypto share cap: Balanced = 25% of the budget
D.t.clear(); rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=24, screeners=['7-1']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
for d in range(4): s, rec = run(t0 + dt.timedelta(days=d))
p = portfolio(); check('coins never exceed their share of the budget', abs(sum(h['costUsd'] for h in p['holdings']) - 2000) < 0.01 and all(h['symbol'].endswith('-USD') for h in p['holdings']), sum(h['costUsd'] for h in p['holdings']))

# --- sells
D.t.clear(); rec = m.load_item(U); rec['settings'].update(enabled=True, risk=5, budgetUsd=4000.0, periodDays=1, everyHours=24, maxHoldDays=5, screeners=['3-100']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
run(t0); run(t0 + dt.timedelta(hours=1)); p = portfolio(); held = [h['symbol'] for h in p['holdings']]
check('four holdings to start', held == ['S00', 'S01', 'S02', 'S03'] and p['cash'] == 96000, held)
PRICES.update({'S00': 100 * 0.79, 'S01': 101 * 1.46}); SNAP['3-100'][2].update(score=-0.5, signal='SELL')
s, rec = run(t0 + dt.timedelta(days=1)); p = portfolio(); texts = [e['text'] for e in rec['log'] if e['type'] == 'sell']
check('sells: fell past the limit, reached the mark, signal turned negative', s['sold'] == 3 and any('past the -20% limit' in t for t in texts) and any('reached the +45% mark' in t for t in texts) and any('turned negative' in t for t in texts), texts)
check('sale money returns and the freed budget is reused', len(p['closed']) == 3 and all(c['by'] == 'ai' and c['spyAtSell'] == 700 for c in p['closed']) and s['bought'] == 3 and abs(p['cash'] - (96000 + 790 + 1460 + 1000 - 3000)) < 0.02, (p['cash'], s))
check('does not buy straight back what it just sold', not ({'S00', 'S01', 'S02'} & {h['symbol'] for h in p['holdings']}), [h['symbol'] for h in p['holdings']])
s, rec = run(t0 + dt.timedelta(days=5, hours=2)); texts = [e['text'] for e in rec['log'] if e['type'] == 'sell']
check('sells what it has held for the longest allowed time', any('Held 5 days' in t for t in texts), texts[-2:])
manual = portfolio(); manual['holdings'].append({'id': 'm1', 'symbol': 'S09', 'label': 'S09', 'name': '', 'currency': 'USD', 'qty': 1, 'buyPrice': 500.0, 'buyFx': 1, 'costUsd': 500, 'boughtAt': m.iso(t0), 'spyAtBuy': 700, 'note': ''})
it = D.Table(m.PORTFOLIO_TABLE).rows[U]; it['data'] = json.dumps(manual); it['version'] += 1
s, rec = run(t0 + dt.timedelta(days=30)); check('never touches a holding the user bought', any(h['id'] == 'm1' for h in portfolio()['holdings']))

# --- a price that does not match the screener's, a clash with the user, missing data
D.t.clear(); PRICES.clear(); SNAP['3-100'] = rows(); rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=24, screeners=['3-100']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
PRICES['S00'] = 400.0; s, rec = run(t0); p = portfolio()
check('skips a symbol whose live price does not match the screener', 'S00' not in [h['symbol'] for h in p['holdings']] and any('no matching live price' in e['text'] for e in rec['log']), [h['symbol'] for h in p['holdings']])
before = json.dumps(D.Table(m.PORTFOLIO_TABLE).rows[U]); D.Table(m.PORTFOLIO_TABLE).fail_next = True
s, rec = run(t0 + dt.timedelta(days=1)); check('a clash with the user changes nothing and is retried later', s.get('conflict') and json.dumps(D.Table(m.PORTFOLIO_TABLE).rows[U]) == before and rec['state'].get('lastRun') == m.iso(t0), s)
SNAP_keep = SNAP.pop('3-100'); s, rec = run(t0 + dt.timedelta(days=2)); check('no screener data: nothing bought, says why', s['bought'] == 0 and 'Screener data was not available' in rec['log'][-1]['text'], rec['log'][-1]); SNAP['3-100'] = SNAP_keep

# --- when it runs
rec = m.load_item(U); rec['state']['lastRun'] = m.iso(t0)
check('due: only after the chosen gap', not m.due(rec, t0 + dt.timedelta(hours=5)) and m.due(rec, t0 + dt.timedelta(hours=24)))
check('due: stocks only in US market hours', not m.due(rec, dt.datetime(2026, 10, 14, 3, 0)) and not m.due(rec, dt.datetime(2026, 10, 17, 15, 0)) and m.due(rec, dt.datetime(2026, 10, 14, 15, 0)))
rec['settings']['screeners'] = ['7-1']; check('due: coins any time', m.due(rec, dt.datetime(2026, 10, 17, 3, 0)))
rec['settings']['enabled'] = False; check('due: never when off', not m.due(rec, dt.datetime(2026, 10, 14, 15, 0)))
# scheduled event end to end (with the stand-ins patched in)
m.fetch_snapshot, m.fetch_quote, m.ask_model = snapshot, quote, model
D.t.clear(); rec = m.load_item(U); rec['settings'].update(enabled=True, screeners=['7-1'], risk=4); rec['state']['startedAt'] = m.iso(dt.datetime.utcnow()); m.save_item(U, rec)
rec2 = m.load_item('stranger@y.com'); rec2['settings']['enabled'] = True; D.Table(m.SETTINGS_TABLE).put_item(Item={'userId': 'stranger@y.com', 'data': json.dumps(rec2), 'enabled': True})
r = json.loads(m.lambda_handler({'source': 'aws.events'}, None)['body'])
check('the schedule runs the due user and skips one not on the list', len(r['ran']) == 1 and r['ran'][0]['bought'] >= 1 and 'stranger@y.com' not in D.Table(m.PORTFOLIO_TABLE).rows, r)
check('"check in now" has a 10-minute gap', call(action='run', userId=U)[0] == 429)
print('ALL PASS' if ok else 'SOME FAILED')
