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
rec = m.load_item(U); rec['state']['lastRun'] = m.iso(t0); rec['state']['lastRunBy'] = {'us': m.iso(t0), 'crypto': m.iso(t0)}
check('due: only after the chosen gap', not m.due(rec, t0 + dt.timedelta(hours=5)) and m.due(rec, t0 + dt.timedelta(hours=24)))
check('due: stocks only in US market hours', not m.due(rec, dt.datetime(2026, 10, 14, 3, 0)) and not m.due(rec, dt.datetime(2026, 10, 17, 15, 0)) and m.due(rec, dt.datetime(2026, 10, 14, 15, 0)))
rec['settings']['screeners'] = ['7-1']; check('due: coins any time', m.due(rec, dt.datetime(2026, 10, 17, 3, 0)))
rec['settings']['enabled'] = False; check('due: never when off', not m.due(rec, dt.datetime(2026, 10, 14, 15, 0)))
# --- every screener, other markets and currencies
s, b = call(action='get', userId=U)
check('all 15 screeners are offered, in groups', len(b['options']['screeners']) == 15 and b['options']['screeners']['4-200'] == {'name': 'ASX 200', 'kind': 'stock', 'group': 'Australian shares'} and {v['group'] for v in b['options']['screeners'].values()} == {'US shares', 'Australian shares', 'UK shares', 'Japanese shares', 'Coins'}, b['options']['screeners'])
check('settings accept the new screeners', m.clean_settings({'screeners': ['4-200', '5-ftse100', '3-6', 'nope']}, U)['screeners'] == ['3-6', '4-200', '5-ftse100'])
mon = lambda h, mi=40, day=12: dt.datetime(2026, 10, day, h, mi)                      # 12 Oct 2026 is a Monday
check('market hours: Sydney, Tokyo, London, New York, coins', m.market_open('au', mon(1)) and not m.market_open('au', mon(6)) and m.market_open('jp', mon(5)) and m.market_open('uk', mon(9)) and not m.market_open('uk', mon(16))
      and m.market_open('us', mon(15)) and not m.market_open('us', mon(1)) and not m.market_open('au', dt.datetime(2026, 10, 17, 1, 40)) and m.market_open('crypto', dt.datetime(2026, 10, 17, 1, 40)))
def au_rows(): return [dict(r, symbol=r['symbol'] + '.AX', label=r['label'] + '.AX', screener='4-200') for r in rows(key='4-200', n=12)]
def uk_rows(): return [dict(r, symbol=r['symbol'] + '.L', label=r['label'] + '.L', screener='5-ftse100', price=r['price'] * 10) for r in rows(key='5-ftse100', n=12)]
FX = {'AUDUSD=X': 0.70, 'GBPUSD=X': 1.30}
def quote2(sym):
    if sym in FX: return {'price': FX[sym], 'currency': 'USD', 'name': sym}
    if sym.endswith('.AX'): r = next((x for x in SNAP['4-200'] if x['symbol'] == sym), None); return r and {'price': PRICES.get(sym, r['price']), 'currency': 'AUD', 'name': 'Aussie ' + sym}
    if sym.endswith('.L'): r = next((x for x in SNAP['5-ftse100'] if x['symbol'] == sym), None); return r and {'price': PRICES.get(sym, r['price']), 'currency': 'GBp', 'name': 'UK ' + sym}
    return quote(sym)
def run2(now, markets=None, **settings):
    rec = m.load_item(U)
    if settings: rec['settings'].update(settings)
    s = m.run_user(U, rec, now, snapshot=snapshot, quote=quote2, model=model, markets=markets); m.save_item(U, rec); return s, rec
D.t.clear(); PRICES.clear(); MODEL['answer'] = None; SNAP.update({'3-100': rows(), '4-200': au_rows(), '5-ftse100': uk_rows()})
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=5, budgetUsd=4000.0, periodDays=1, everyHours=24, maxHoldDays=20, screeners=['3-100', '4-200', '5-ftse100']); rec['state']['startedAt'] = m.iso(mon(0)); m.save_item(U, rec)
check('due per market: Sydney open, the others shut', m.due_markets(m.load_item(U), mon(1)) == ['au'] and m.due_markets(m.load_item(U), mon(9)) == ['uk'] and m.due_markets(m.load_item(U), mon(15)) == ['us'] and m.due_markets(m.load_item(U), mon(22)) == [])
s, rec = run2(mon(1), markets=['au']); p = portfolio(); h = p['holdings'][0]
check('Sydney check-in buys only Australian shares, in dollars at the exchange rate', s['bought'] == 3 and all(x['symbol'].endswith('.AX') and x['currency'] == 'AUD' and x['buyFx'] == 0.70 for x in p['holdings']) and abs(h['qty'] - 1000 / (h['buyPrice'] * 0.70)) < 1e-9 and h['costUsd'] == 1000 and p['cash'] == 97000, [(x['symbol'], x['currency'], x['buyFx']) for x in p['holdings']])
check('each market keeps its own last check', rec['state']['lastRunBy'] == {'au': m.iso(mon(1))} and m.due_markets(rec, mon(2)) == [] and m.due_markets(rec, mon(9)) == ['uk'] and m.due_markets(rec, mon(1, day=13)) == ['au'])
s, rec = run2(mon(9), markets=['uk']); p = portfolio(); uk = [x for x in p['holdings'] if x['symbol'].endswith('.L')]
check('London check-in: pence handled, the budget cap holds', s['bought'] == 1 and uk[0]['currency'] == 'GBp' and abs(uk[0]['buyFx'] - 0.013) < 1e-12 and abs(uk[0]['qty'] * uk[0]['buyPrice'] * 0.013 - 1000) < 1e-6 and len(p['holdings']) == 4, [(x['symbol'], x['buyFx']) for x in p['holdings']])
PRICES['S00.AX'] = 100.0 * 0.75; FX['AUDUSD=X'] = 0.77            # share down 25% in its own currency, currency up 10%: down 17.5% in dollars
s, rec = run2(mon(15), markets=['us']); check('New York check-in leaves the Sydney holding alone while Sydney is shut', s['sold'] == 0 and any(x['symbol'] == 'S00.AX' for x in portfolio()['holdings']))
s, rec = run2(mon(1, day=13), markets=['au']); sold = [c for c in portfolio()['closed'] if c['symbol'] == 'S00.AX']
check('sold in dollars: the currency move counts (not at -20% yet, so it is kept)', s['sold'] == 0 and not sold, sold)
PRICES['S00.AX'] = 100.0 * 0.70; s, rec = run2(mon(1, day=14), markets=['au']); sold = [c for c in portfolio()['closed'] if c['symbol'] == 'S00.AX']
check('past the limit in dollars: sold, proceeds at the new rate', s['sold'] == 1 and abs(sold[0]['proceedsUsd'] - 1000 * 0.70 * 0.77 / 0.70) < 0.01 and sold[0]['sellFx'] == 0.77 and 'Down 23.0%' in [e['text'] for e in rec['log'] if e['type'] == 'sell'][-1], sold)
FX.pop('GBPUSD=X'); D.t.clear(); rec = m.load_item(U); rec['settings'].update(enabled=True, risk=5, budgetUsd=4000.0, periodDays=1, screeners=['5-ftse100']); rec['state']['startedAt'] = m.iso(mon(8)); m.save_item(U, rec)
s, rec = run2(mon(9)); check('no exchange rate: skipped, nothing bought at a wrong value', s['bought'] == 0 and not (portfolio() or {'holdings': []})['holdings'] and any('no matching live price' in e['text'] for e in rec['log'])); FX['GBPUSD=X'] = 1.30; FX['AUDUSD=X'] = 0.70

check('exchange rates: yen from the per-dollar quote, pence and Australian dollars direct', m.fx_pair('JPY') == ('USDJPY=X', 1, True) and m.fx_pair('GBp') == ('GBPUSD=X', 100, False) and m.fx_pair('AUD') == ('AUDUSD=X', 1, False) and m.fx_pair('USD') == (None, 1, False)
      and abs(m.usd_rate('JPY', lambda s: {'price': 158.246}, {}) - 0.0063193) < 1e-7 and m.usd_rate('JPY', lambda s: None, {}) is None and m.usd_rate('USD', None, {}) == 1.0)
# --- stored screener results
calls = []; m.fetch_snapshot = lambda k: (calls.append(k), rows(key=k, n=200))[1]; D.t.clear(); now0 = dt.datetime(2026, 10, 12, 15, 0)
a = m.get_snapshot('3-100', now0); b2 = m.get_snapshot('3-100', now0 + dt.timedelta(minutes=30)); c = m.get_snapshot('3-100', now0 + dt.timedelta(minutes=50))
check('a screener is run once and reused for 45 minutes', calls == ['3-100', '3-100'] and len(b2) == 200 and b2[:150] == a[:150] and (b2[180]['symbol'], b2[180]['score'], b2[180]['signal'], b2[180]['rank']) == (a[180]['symbol'], a[180]['score'], a[180]['signal'], a[180]['rank']), calls)
check('the stored copy is small enough for the table', len(D.Table(m.SETTINGS_TABLE).rows['_snapshot#3-100']['data']) < 100000)

# --- learning from its own results
D.t.clear(); PRICES.clear(); SNAP['3-100'] = rows(); MODEL['answer'] = None; MODEL['prompts'].clear()
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=5, budgetUsd=4000.0, periodDays=1, everyHours=24, maxHoldDays=5, screeners=['3-100']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
s, rec = run(t0); s, rec = run(t0 + dt.timedelta(days=1)); ids = {h['symbol']: h['id'] for h in portfolio()['holdings']}
check('remembers what each buy was based on', len(rec['state']['open']) == 4 and rec['state']['open'][ids['S00']] == {'symbol': 'S00', 'label': 'S00', 'screener': '3-100', 'risk': 5, 'chosen': 'rules', 'rank': 1, 'score': 4.0, 'rsi': 50.0, 'd7': 3.0, 'd30': 5.0, 'volume': 1.2, 't': m.iso(t0)}, rec['state']['open'].get(ids['S00']))
PRICES.update(S00=79.0, S01=150.0)
s, rec = run(t0 + dt.timedelta(days=2)); hist = {x['symbol']: x for x in rec['history']}
check('sold holdings go into the history with their result', s['sold'] == 2 and set(hist) == {'S00', 'S01'} and hist['S00']['pct'] == -21.0 and hist['S00']['exit'] == 'stop' and hist['S00']['market'] == 0.0 and hist['S00']['vs'] == -21.0 and hist['S00']['days'] == 2.0
      and abs(hist['S01']['pct'] - 48.51) < 0.02 and hist['S01']['exit'] == 'take' and hist['S01']['rank'] == 2, hist)
pf = D.Table(m.PORTFOLIO_TABLE).rows[U]; data = json.loads(pf['data']); hand = next(h for h in data['holdings'] if h['symbol'] == 'S02')
data['holdings'] = [h for h in data['holdings'] if h['id'] != hand['id']]; data['closed'].append(dict(hand, sellPrice=110.0, sellFx=1, proceedsUsd=round(hand['qty'] * 110, 2), soldAt=m.iso(t0 + dt.timedelta(days=2, hours=1)), spyAtSell=721.0)); pf['data'] = json.dumps(data); pf['version'] += 1
gone = next(h for h in data['holdings'] if h['symbol'] == 'S03'); data['holdings'] = [h for h in data['holdings'] if h['id'] != gone['id']]; pf['data'] = json.dumps(data)
s, rec = run(t0 + dt.timedelta(days=3)); hist = {x['symbol']: x for x in rec['history']}
check('a sale by hand is learned from too; a vanished holding is not guessed at', hist['S02']['exit'] == 'hand' and abs(hist['S02']['market'] - 3.0) < 0.01 and abs(hist['S02']['vs'] - (hist['S02']['pct'] - 3.0)) < 0.011 and 'S03' not in hist and gone['id'] not in rec['state']['open'], hist.get('S02'))
card = m.scorecard(rec['history'])
check('scorecard adds up', card['n'] == 3 and card['up'] == 2 and card['judged'] == 3 and [g['label'] for g in card['groups']['exit']] == ['sold at the loss limit', 'sold at the gain mark', 'sold by you'] and card['groups']['screener'][0] == dict(label='S&P 100', n=3, avg=card['avg'], vs=card['vs'], beat=card['beat'], judged=3, up=2) and card['groups']['rank'][0]['label'] == 'rank 1 to 3', card)
check('an empty history gives an empty scorecard', m.scorecard([]) == {'n': 0, 'groups': {}} and m.memory_text(m.scorecard([]), None) == '')
def trade(i, vs, key='3-100', sold=None): return {'symbol': f'T{i}', 'label': f'T{i}', 'screener': key, 'risk': 3, 'chosen': 'ai', 'rank': 1 + i % 12, 'score': 3.0, 'rsi': 40 + i * 2, 'd7': 1.0, 'd30': 5.0, 'volume': 1.0, 't': 'x', 'pct': vs + 1.0, 'market': 1.0, 'vs': vs, 'days': 3.0, 'exit': 'time', 'sold': sold or m.iso(t0 + dt.timedelta(days=i))}
rec = m.load_item(U); rec['history'] = [trade(i, -3.0) for i in range(7)]
check('seven poor trades are too few to act on', m.review_resting(rec, t0 + dt.timedelta(days=20)) == [] and not rec['state'].get('rest'))
rec['history'].append(trade(7, -3.0)); notes = m.review_resting(rec, t0 + dt.timedelta(days=20))
check('eight trades lagging the market: the screener is rested, and says so', list(rec['state']['rest']) == ['3-100'] and 'Resting the S&P 100 screener for 14 days: its last 8 trades averaged -3.0% against the market' in notes[0]['text'], notes)
rec['settings']['screeners'] = ['3-100', '7-1']; rec['settings']['risk'] = 4; m.save_item(U, rec); s, rec = run(t0 + dt.timedelta(days=21))
check('a resting screener is not bought from; the others still are', s['bought'] >= 1 and all(h['symbol'].endswith('-USD') for h in portfolio()['holdings'] if h['boughtAt'] == m.iso(t0 + dt.timedelta(days=21))), [h['symbol'] for h in portfolio()['holdings']])
rec['settings']['screeners'] = ['3-100']; m.save_item(U, rec); s, rec = run(t0 + dt.timedelta(days=22, hours=1))
check('all chosen screeners resting: says so', s['bought'] == 0 and 'resting after lagging the market' in rec['log'][-1]['text'], rec['log'][-1])
notes = m.review_resting(rec, t0 + dt.timedelta(days=35)); check('the rest ends after 14 days and old trades are not held against it again', not rec['state']['rest'] and 'again after its rest' in notes[0]['text'] and m.review_resting(rec, t0 + dt.timedelta(days=36)) == [], notes)
good = m.load_item(U); good['state'] = {}; good['history'] = [trade(i, +2.0) for i in range(12)]; check('a screener doing well is never rested', m.review_resting(good, t0) == [] and not good['state'].get('rest'))
rec = m.load_item(U); rec['history'] = [trade(i, 1.5 if i % 2 else -2.5) for i in range(9)]; rec['state'].pop('lessons', None)
MODEL['answer'] = {'lessons': ['Trades bought with RSI under 45 did better than those over 60 (4 against 3 trades).', '   ', 'x' * 400]}; MODEL['prompts'].clear()
wrote = m.write_lessons(rec, t0, model)
check('after enough closed trades the AI model writes notes from the record', wrote and rec['state']['lessons']['n'] == 9 and len(rec['state']['lessons']['items']) == 2 and len(rec['state']['lessons']['items'][1]) == 200 and 'All 9 closed trades' in MODEL['prompts'][0]['user'] and 'result -1.5%' in MODEL['prompts'][0]['user'] and 'No predictions, no advice' in MODEL['prompts'][0]['system'], rec['state'].get('lessons'))
check('not again until five more trades have closed', not m.write_lessons(rec, t0, model) and len(MODEL['prompts']) == 1)
MODEL['answer'] = None; rec['history'] += [trade(20 + i, 1.0) for i in range(5)]; kept = dict(rec['state']['lessons'])
check('if the model gives nothing, the old notes stay', not m.write_lessons(rec, t0, model) and rec['state']['lessons'] == kept)
text = m.memory_text(m.scorecard(rec['history']), rec['state']['lessons'])
check('the record and notes are put in front of the model when it chooses', 'All 14 closed trades' in text and '- S&P 100: 14 trades' in text and 'Note from the last review: Trades bought with RSI under 45' in text and 'own record so far' in m.build_prompt(rec['settings'], SNAP['3-100'][:3], '', 1, text)['user'] and 'own record' not in m.build_prompt(rec['settings'], SNAP['3-100'][:3], '', 1)['user'])
m.save_item(U, rec); s, b = call(action='get', userId=U)
check('the dashboard gets the scorecard, notes and resting list, not the bulk', b['scorecard']['n'] == 14 and b['lessons']['items'] and isinstance(b['resting'], dict) and len(b['recent']) == 10 and 'history' not in b and 'open' not in b['state'] and b['minSample'] == 8, list(b))
# --- nothing is chosen for the user, and each change can be saved on its own
D.t.clear(); s, b = call(action='get', userId=U)
check('a new user has no screener ticked', b['settings']['screeners'] == [] and b['settings']['enabled'] is False)
base = dict(b['settings'])
s, b = call(action='save', userId=U, settings=dict(base, enabled=True)); check('it can be switched on before a screener is chosen, and just waits', s == 200 and b['settings']['enabled'] is True and b['settings']['screeners'] == [] and b['nextCheck'] is None and m.due_markets(m.load_item(U), t0) == [])
check('check in now with no screener says what is missing', call(action='run', userId=U) == (400, {'error': 'Choose at least one screener for it to buy from first'}))
for budget in (2000, 20000, 20500): s, b = call(action='save', userId=U, settings=dict(base, enabled=True, budgetUsd=budget))
s, b = call(action='save', userId=U, settings=dict(base, enabled=True, budgetUsd=20500, screeners=['3-8', '7-1'])); s, b = call(action='save', userId=U, settings=dict(base, enabled=True, budgetUsd=20500, screeners=['3-8', '7-1'], maxHoldDays=5))
check('a burst of saves leaves one line in the activity list, with the final values', [e['text'] for e in b['log']] == ['Autopilot on: Balanced level, $20,500 over 10 days, checking every 24 hours.'], [e['text'] for e in b['log']])
s, b = call(action='get', userId=U); check('every setting is remembered', b['settings'] == dict(base, enabled=True, budgetUsd=20500.0, screeners=['3-8', '7-1'], maxHoldDays=5), b['settings'])
s, b = call(action='save', userId=U, settings=dict(b['settings'], screeners=[])); check('unticking everything is remembered too', b['settings']['screeners'] == [] and b['settings']['enabled'] is True)

# --- what the panel is told: when it will next check in, and what it holds
D.t.clear(); rec = m.load_item(U); rec['settings'].update(enabled=True, screeners=['3-100']); sat = dt.datetime(2026, 10, 17, 10, 25)
check('next check-in: a US list on a Saturday waits for Monday\'s session', m.next_check(rec, sat) == {'at': '2026-10-19T14:40:00Z', 'markets': ['US']}, m.next_check(rec, sat))
rec['settings']['screeners'] = ['3-100', '4-200']; check('with an Australian list too, Sydney opens first', m.next_check(rec, sat) == {'at': '2026-10-19T00:40:00Z', 'markets': ['Australian']}, m.next_check(rec, sat))
rec['settings']['screeners'] = ['7-1']; check('coins: the next hourly slot', m.next_check(rec, sat) == {'at': '2026-10-17T10:40:00Z', 'markets': ['coin']} and m.next_check(rec, sat.replace(minute=45))['at'] == '2026-10-17T11:40:00Z')
rec['state']['lastRunBy'] = {'crypto': m.iso(sat)}; rec['settings']['everyHours'] = 6; check('after a check-in it waits the chosen gap', m.next_check(rec, sat)['at'] == '2026-10-17T16:40:00Z', m.next_check(rec, sat))
rec['settings']['enabled'] = False; check('off: no next check-in', m.next_check(rec, sat) is None)
D.t.clear(); PRICES.clear(); SNAP['3-100'] = rows(); MODEL['answer'] = None; rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, screeners=['3-100']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec); run(t0)
s, b = call(action='get', userId=U); check('the panel is told what the autopilot holds and when it checks next', b['holding'] == {'count': 3, 'investedUsd': 3000.0} and b['nextCheck'] and b['nextCheck']['markets'] == ['US'] and b['practiceCash'] == 100000, (b.get('holding'), b.get('nextCheck')))
D.t.clear(); PRICES.clear(); rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, screeners=['3-100']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
D.Table(m.PORTFOLIO_TABLE).fail_next = True; s, rec = run(t0)
check('a clash with the user: the unsaved buys are not remembered', s.get('conflict') and not rec['state'].get('open'), rec['state'].get('open'))

# scheduled event end to end (with the stand-ins patched in)
m.fetch_snapshot, m.fetch_quote, m.ask_model = snapshot, quote, model
D.t.clear(); rec = m.load_item(U); rec['settings'].update(enabled=True, screeners=['7-1'], risk=4); rec['state']['startedAt'] = m.iso(dt.datetime.utcnow()); m.save_item(U, rec)
rec2 = m.load_item('stranger@y.com'); rec2['settings']['enabled'] = True; D.Table(m.SETTINGS_TABLE).put_item(Item={'userId': 'stranger@y.com', 'data': json.dumps(rec2), 'enabled': True})
r = json.loads(m.lambda_handler({'source': 'aws.events'}, None)['body'])
check('the schedule runs the due user and skips one not on the list', len(r['ran']) == 1 and r['ran'][0]['bought'] >= 1 and 'stranger@y.com' not in D.Table(m.PORTFOLIO_TABLE).rows, r)
check('"check in now" has a 10-minute gap', call(action='run', userId=U)[0] == 429)
print('ALL PASS' if ok else 'SOME FAILED')
