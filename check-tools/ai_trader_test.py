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
    s = m.run_user(U, rec, now, snapshot=snapshot, quote=quote, model=model, mail=lambda subject, lines: MAILS.append((subject, lines)), headlines=lambda h, now: NEWS.get(h['symbol'], [])); m.save_item(U, rec); return s, rec
MAILS = []; NEWS = {}
buy_prompts = lambda: [p for p in MODEL['prompts'] if 'Pick exactly' in p['user']]
t0 = dt.datetime(2026, 10, 12, 15, 0, 0)          # a Monday, US market open

# --- access and settings
check('someone not on the list is refused', call(action='get', userId='stranger@y.com')[1] == {'success': True, 'allowed': False})
check('not on the list cannot switch it on', m.clean_settings({'enabled': True}, 'stranger@y.com')['enabled'] is False)
s, b = call(action='get', userId=U); check('defaults', b['allowed'] and b['settings'] == dict(m.DEFAULTS) and '3-100' in b['options']['screeners'], b)
s, b = call(action='save', userId=U, settings={'enabled': True, 'risk': 9, 'budgetUsd': 'lots', 'periodDays': 0.2, 'everyHours': 7, 'maxHoldDays': 5, 'screeners': ['3-100', 'nope'], 'x': 1})
check('settings are cleaned', b['settings'] == {'enabled': True, 'risk': 5, 'budgetUsd': 10000.0, 'periodDays': 1, 'everyHours': 24, 'maxHoldDays': 5, 'screeners': ['3-100'], 'aiSell': True, 'selfTune': True, 'emails': True, 'stopPct': None, 'takePct': None} and b['state'].get('startedAt') and b['log'][-1]['text'].startswith('Autopilot on'), b['settings'])
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
s, rec = run(t0 + dt.timedelta(hours=1)); check('an hour later: nothing more yet', s['bought'] == 0 and 'released in steps over the 4 days set under "Build up to it over"; the next $1,000 in about 23 hours.' in rec['log'][-1]['text'], rec['log'][-1])
MODEL['answer'] = None
s, rec = run(t0 + dt.timedelta(days=1)); p = portfolio()
check('day 2: 2 more, chosen by score because the model gave nothing', s['bought'] == 2 and s['decidedBy'] == 'rules' and [h['symbol'] for h in p['holdings']][2:] == ['S00', 'S02'] and 'chosen by rank' in rec['log'][-1]['text'], [h['symbol'] for h in p['holdings']])
s, rec = run(t0 + dt.timedelta(days=5)); p = portfolio()
check('never more than 3 buys in one check-in', s['bought'] == 3 and len(p['holdings']) == 7)
s, rec = run(t0 + dt.timedelta(days=6)); s2, rec = run(t0 + dt.timedelta(days=7)); p = portfolio()
check('stops at the budget: 8 holdings, $8,000', len(p['holdings']) == 8 and p['cash'] == 92000 and s2['bought'] == 0 and 'fully invested' in rec['log'][-1]['text'], (len(p['holdings']), p['cash'], rec['log'][-1]['text']))

# --- cents: a budget that does not divide evenly (Bold, 6 holdings of $1,666.67) is still used in full, never a cent over
D.t.clear()
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=4, budgetUsd=10000.0, periodDays=1, everyHours=24, maxHoldDays=20, screeners=['3-100']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
s, rec = run(t0); s2, rec = run(t0 + dt.timedelta(days=1)); p = portfolio(); spent = round(sum(h['costUsd'] for h in p['holdings']), 2)
check('the last holding is not lost to a cent of rounding: 6 of 6, exactly $10,000', s['bought'] == 3 and s2['bought'] == 3 and len(p['holdings']) == 6 and spent == 10000.0 and p['cash'] == 90000.0 and p['holdings'][-1]['costUsd'] == 1666.65, (s['bought'], s2['bought'], spent, [h['costUsd'] for h in p['holdings']]))
s3, rec = run(t0 + dt.timedelta(days=2)); check('and then it says the budget is fully invested', s3['bought'] == 0 and 'fully invested in 6 holdings' in rec['log'][-1]['text'], rec['log'][-1]['text'])

# --- risk filters
view = lambda risk, scr=('3-100',): [c['symbol'] for c in m.shortlist(m.new_portfolio(t0), dict(m.DEFAULTS, risk=risk, screeners=list(scr)), SNAP, t0)]
check('Cautious: top 5 only, and nothing that has run 20%+ in a month', view(1) == ['S00', 'S01', 'S02', 'S03', 'S04'], view(1))
check('Adventurous looks further down, but only at positive signals', view(5) == [f'S{i:02d}' for i in range(15)], view(5))
check('coins need Balanced or above', view(2, ('3-100', '7-1')) == view(2) and any(x.startswith('C') for x in view(3, ('3-100', '7-1'))))
SNAP['3-100'][0]['rsi'] = 80; check('an overbought leader is left out at Balanced', 'S00' not in view(3) and 'S00' in view(5)); SNAP['3-100'][0]['rsi'] = 50

# --- crypto share: with shares ticked too, Balanced = 25% of the budget; with only coins ticked, the whole budget at any level
quiet = [dict(r, signal='HOLD') for r in rows()]            # no share passes the filters, so only the coin share is in play
D.t.clear(); SNAP['3-100'] = quiet; rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=24, screeners=['3-100', '7-1']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
for d in range(4): s, rec = run(t0 + dt.timedelta(days=d))
p = portfolio(); check('with shares ticked too, coins never exceed the level\'s share of the budget', abs(sum(h['costUsd'] for h in p['holdings']) - 2000) < 0.01 and all(h['symbol'].endswith('-USD') for h in p['holdings']) and m.coin_share(rec['settings']) == 0.25, sum(h['costUsd'] for h in p['holdings']))
D.t.clear(); rec = m.load_item(U); rec['settings'].update(enabled=True, risk=1, budgetUsd=6000.0, periodDays=1, everyHours=24, screeners=['7-1']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
for d in range(5): s, rec = run(t0 + dt.timedelta(days=d))
p = portfolio(); check('with only coin screeners ticked coins are bought at any level, past the level\'s share (Cautious: every coin that passes its filters)', len(p['holdings']) == 5 and all(h['symbol'].endswith('-USD') for h in p['holdings']) and abs(sum(h['costUsd'] for h in p['holdings']) - 2500) < 0.01 and m.coin_share(rec['settings']) == 1.0 and 'Nothing on the shortlist passed the Cautious filters' in rec['log'][-1]['text'] and m.public(rec, t0)['coinShare'] == 1.0, (len(p['holdings']), rec['log'][-1]['text']))
SNAP['3-100'] = rows()

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
check('remembers what each buy was based on', len(rec['state']['open']) == 4 and rec['state']['open'][ids['S00']] == {'symbol': 'S00', 'label': 'S00', 'screener': '3-100', 'risk': 5, 'chosen': 'rules', 'rank': 1, 'score': 4.0, 'rsi': 50.0, 'd7': 3.0, 'd30': 5.0, 'volume': 1.2, 't': m.iso(t0), 'hold': 5.0, 'peak': 0.0, 'low': 0.0}, rec['state']['open'].get(ids['S00']))
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

# --- quick trading: check-ins every 30 minutes or hour, holdings kept for as little as 30 minutes
s, b = call(action='get', userId=U)
check('quick options are offered', b['options']['everyHours'] == [0.5, 1, 3, 6, 12, 24] and b['options']['holdDays'][:3] == [0.5 / 24, 1 / 24, 3 / 24] and b['options']['holdDays'][-1] == 60 and 20 in b['options']['holdDays'])
check('settings keep a half-hour check-in and a one-hour hold exactly', m.clean_settings({'everyHours': 0.5, 'maxHoldDays': 1 / 24}, U)['everyHours'] == 0.5 and m.clean_settings(json.loads(json.dumps({'maxHoldDays': 1 / 24})), U)['maxHoldDays'] == 1 / 24
      and m.clean_settings({'everyHours': 2, 'maxHoldDays': 7}, U)['everyHours'] == 24 and m.clean_settings({'everyHours': 'x', 'maxHoldDays': None}, U)['maxHoldDays'] == 20)
check('time in plain words', [m.span_text(d) for d in (0.5 / 24, 1 / 24, 3 / 24, 1, 5, 20)] == ['30 minutes', '1 hour', '3 hours', '1 day', '5 days', '20 days'] and [m.every_text(h) for h in (0.5, 1, 3, 24)] == ['every 30 minutes', 'every hour', 'every 3 hours', 'every 24 hours'])
D.t.clear(); PRICES.clear(); SNAP['7-1'] = rows('crypto', '7-1'); MODEL['answer'] = None; q0 = dt.datetime(2026, 10, 17, 10, 40, 6)       # a Saturday: coins only
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=5, budgetUsd=4000.0, periodDays=1, everyHours=0.5, maxHoldDays=1 / 24, screeners=['7-1']); rec['state']['startedAt'] = m.iso(q0); m.save_item(U, rec)
s, rec = run(q0); first = [h['symbol'] for h in portfolio()['holdings']]
check('half-hourly: due again at the next slot, not before', m.due_markets(rec, q0 + dt.timedelta(minutes=10)) == [] and m.due_markets(rec, dt.datetime(2026, 10, 17, 11, 10, 2)) == ['crypto'] and m.next_check(rec, q0)['at'] == '2026-10-17T11:10:00Z', m.next_check(rec, q0))
s, rec = run(dt.datetime(2026, 10, 17, 11, 10, 2)); check('30 minutes on, a one-hour holding is kept', s['sold'] == 0 and all(x in [h['symbol'] for h in portfolio()['holdings']] for x in first))
s, rec = run(dt.datetime(2026, 10, 17, 11, 40, 3)); texts = [e['text'] for e in rec['log'] if e['type'] == 'sell']
check('at the hour (even three seconds early) it is sold, and says so in hours', s['sold'] == len(first) and all('Held 1 hour, the longest this autopilot keeps a holding' in x for x in texts) and rec['history'][0]['days'] == 0.042 and rec['history'][0]['exit'] == 'time', (s, texts[:1], rec['history'][:1]))
now3 = dt.datetime(2026, 10, 17, 11, 40, 3); again = lambda at: {c['symbol'] for c in m.shortlist(portfolio(), rec['settings'], SNAP, at)}
check('it waits two holding times (2 hours), not two days, before buying the same coin again', not (set(first) & again(now3 + dt.timedelta(hours=1))) and set(first) <= again(now3 + dt.timedelta(hours=2, minutes=1)), sorted(again(now3 + dt.timedelta(hours=2, minutes=1)))[:5])
rec['settings'].update(maxHoldDays=20); check('with a long holding time the wait is still two days', not (set(first) & {c['symbol'] for c in m.shortlist(portfolio(), rec['settings'], SNAP, now3 + dt.timedelta(hours=30))}))
s, b = call(action='save', userId=U, settings=dict(rec['settings'], everyHours=0.5, budgetUsd=5000.0)); check('the activity line says the pace in words', b['log'][-1]['text'].endswith('checking every 30 minutes.'), b['log'][-1])

# --- what the panel is told: when it will next check in, and what it holds
D.t.clear(); rec = m.load_item(U); rec['settings'].update(enabled=True, screeners=['3-100']); sat = dt.datetime(2026, 10, 17, 10, 25)
check('next check-in: a US list on a Saturday waits for Monday\'s session', m.next_check(rec, sat) == {'at': '2026-10-19T14:40:00Z', 'markets': ['US']}, m.next_check(rec, sat))
rec['settings']['screeners'] = ['3-100', '4-200']; check('with an Australian list too, Sydney opens first', m.next_check(rec, sat) == {'at': '2026-10-19T00:10:00Z', 'markets': ['Australian']}, m.next_check(rec, sat))
rec['settings']['screeners'] = ['7-1']; check('coins: the next half-hourly slot', m.next_check(rec, sat) == {'at': '2026-10-17T10:40:00Z', 'markets': ['coin']} and m.next_check(rec, sat.replace(minute=45))['at'] == '2026-10-17T11:10:00Z')
rec['state']['lastRunBy'] = {'crypto': m.iso(sat)}; rec['settings']['everyHours'] = 6; check('after a check-in it waits the chosen gap', m.next_check(rec, sat)['at'] == '2026-10-17T16:40:00Z', m.next_check(rec, sat))
rec['settings']['enabled'] = False; check('off: no next check-in', m.next_check(rec, sat) is None)
D.t.clear(); PRICES.clear(); SNAP['3-100'] = rows(); MODEL['answer'] = None; rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, screeners=['3-100']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec); run(t0)
s, b = call(action='get', userId=U); check('the panel is told what the autopilot holds and when it checks next', b['holding'] == {'count': 3, 'investedUsd': 3000.0} and b['nextCheck'] and b['nextCheck']['markets'] == ['US'] and b['practiceCash'] == 100000, (b.get('holding'), b.get('nextCheck')))
D.t.clear(); PRICES.clear(); rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, screeners=['3-100']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
D.Table(m.PORTFOLIO_TABLE).fail_next = True; s, rec = run(t0)
check('a clash with the user: the unsaved buys are not remembered', s.get('conflict') and not rec['state'].get('open'), rec['state'].get('open'))

# --- selling: keeping part of a gain, slipping down the ranking, and the story of a sale
D.t.clear(); PRICES.clear(); MODEL['answer'] = None; SNAP['3-100'] = rows()
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=24, maxHoldDays=20, screeners=['3-100']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
s, rec = run(t0); p = portfolio(); first = p['holdings'][0]; sym = first['symbol']; base = first['buyPrice']
check('a buy says what the plan for it is', any('sell 20 days after buying at the latest; sooner at -10% or +18%; once it has been up 9%, sell if it gives back 50% of its best gain' in d for e in rec['log'] if e['type'] == 'buy' for d in e.get('detail', [])), [e.get('detail') for e in rec['log'] if e['type'] == 'buy'][:1])
PRICES[sym] = base * 1.12; s, rec = run(t0 + dt.timedelta(days=1))
check('up 12% (under the +18% mark): kept, and its best so far is remembered', sym in [h['symbol'] for h in portfolio()['holdings']] and rec['state']['open'][first['id']]['peak'] == 12.0, rec['state']['open'].get(first['id']))
PRICES[sym] = base * 1.05; s, rec = run(t0 + dt.timedelta(days=2)); sale = [e for e in rec['log'] if e['type'] == 'sell'][-1]
check('slipped back to +5% from a best of +12%: sold to keep part of the gain', sym not in [h['symbol'] for h in portfolio()['holdings']] and sale['kind'] == 'trail' and 'Was up +12.0% at its best and has slipped back to +5.0%: sold to keep part of the gain' in sale['text'] and sale['pct'] == 5.0, sale)
check('the sale carries its story: what it was bought on, how long, best and worst, the figures at the sale, the rules', len(sale['detail']) >= 5 and sale['detail'][0].startswith('Bought at rank ') and 'Held 2 days. It was set to keep a holding at most 20 days.' in sale['detail'] and '+12.0% at its best' in ' '.join(sale['detail']) and 'sell at -10% or +18%' in ' '.join(sale['detail']) and not any('S&P 500 fund' in d for d in sale['detail']), sale['detail'])
done = rec['history'][-1]
check('the finished trade keeps the dollars, the best and worst, and how it was sold', done['exit'] == 'trail' and done['usd'] == 50.0 and done['cost'] == 1000.0 and done['peak'] == 12.0 and done['low'] == 0.0 and done['id'] == first['id'] and rec['state']['closedCount'] == 1 and m.scorecard(rec['history'])['groups']['exit'][0]['label'] == 'sold to keep part of a gain', done)
check('its price is looked at again later', rec['state']['watch'][-1]['symbol'] == sym and rec['state']['watch'][-1]['due'] == m.iso(t0 + dt.timedelta(days=2) + dt.timedelta(days=5)), rec['state'].get('watch'))
PRICES[sym] = base * 1.05 * 1.10; s, rec = run(t0 + dt.timedelta(days=7, hours=1))
check('later: what it did after it was sold is added to the record', rec['history'][0].get('after') == 10.0 and not rec['state']['watch'], (rec['history'][0], rec['state'].get('watch')))
other = portfolio()['holdings'][0]; far = [dict(r, rank=r['rank'] + 60, score=1.0) if r['symbol'] == other['symbol'] else r for r in rows()]
info = {}; sells = m.review_sells(portfolio(), rec['settings'], {'3-100': far}, {other['symbol']: {'price': other['buyPrice']}}, t0 + dt.timedelta(days=8), opened=rec['state']['open'], info=info)
check('far down the ranking with under half its score: sold', len(sells) == 1 and info[other['id']]['kind'] == 'fade' and 'Slipped to rank' in sells[0][2] and 'less than half the score it was bought on' in sells[0][2], sells and sells[0][2])
near = [dict(r, rank=r['rank'] + 60) if r['symbol'] == other['symbol'] else r for r in rows()]
below = [dict(r, score=-1.0, signal='HOLD', rank=149) if r['symbol'] == other['symbol'] else r for r in rows()]
said = m.review_sells(portfolio(), rec['settings'], {'3-100': below}, {other['symbol']: {'price': other['buyPrice']}}, t0 + dt.timedelta(days=8), opened=rec['state']['open'])
check('a score below zero with a signal that is only mixed: the reason says the score, not the signal', len(said) == 1 and 'Its screener score fell below zero (score -1.0, rank 149)' in said[0][2] and 'signal turned negative' not in said[0][2], said and said[0][2])
check('far down the ranking but the score has held: kept', m.review_sells(portfolio(), rec['settings'], {'3-100': near}, {other['symbol']: {'price': other['buyPrice']}}, t0 + dt.timedelta(days=8), opened=rec['state']['open']) == [])
s, b = call(action='get', userId=U); plan = b['plans'][0]
check('the dashboard gets a plan for each holding: sell-by time and marks', len(b['plans']) == len([h for h in portfolio()['holdings'] if h.get('by') == 'ai']) and plan['auto'] is True and plan['stop'] == -10 and plan['take'] == 18 and plan['arm'] == 9 and m.parse_time(plan['sellBy']) - m.parse_time(plan['boughtAt']) == dt.timedelta(days=20), plan)
check('and the rules in force, the month so far and the review countdown', b['rules']['stop'] == -10 and b['rules']['changed'] == {} and b['month']['last30']['n'] >= 0 and b['tune']['trial'] is None and b['tune']['nextReviewIn'] == 19 and b['now'], (b['rules'], b['tune']))

# --- the activity list: the same uneventful check-in is counted, not repeated; reasons name the right setting
D.t.clear(); PRICES.clear(); SNAP['7-1'] = rows('crypto', '7-1'); SNAP['3-100'] = [dict(r, signal='HOLD') for r in rows()]; MODEL['prompts'].clear()
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=10000.0, periodDays=1, everyHours=0.5, maxHoldDays=20, screeners=['3-100', '7-1']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
for i in range(60): s, rec = run(t0 + dt.timedelta(minutes=30 * i))
coins = [h for h in portfolio()['holdings'] if h.get('by') == 'ai']; asked = len(buy_prompts()); last = rec['log'][-1]
check('shares and coins at Balanced with no share to buy: coins stop at a quarter of the budget and it says why', len(coins) == 2 and sum(h['costUsd'] for h in coins) == 2500 and last['key'] == 'coins' and '$2,500 is in coins, and the Balanced level puts at most 25% of the budget ($2,500) in coins. Tick a share screener as well, or move the level up' in last['text'], last)
check('the same uneventful check-in is counted, not listed again', last.get('n', 1) > 10 and last['first'] < last['t'] and len([e for e in rec['log'] if e.get('key') == 'coins']) == 1, (last.get('n'), len(rec['log'])))
s, rec = run(t0 + dt.timedelta(hours=31)); SNAP['3-100'] = rows(); check('with the coin share used up the AI model is not asked to pick again', len(buy_prompts()) == asked, (asked, len(buy_prompts())))

# --- hold or sell: the AI model reviews each holding the rules are keeping, with the screener's figures now and recent headlines
feed = lambda items: ('<rss><channel>' + ''.join(f"<item><title>{t}</title><pubDate>{(t0 - dt.timedelta(hours=h)).strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate></item>" for t, h in items) + '</channel></rss>').encode()
heads = m.pick_headlines(feed([('Solana and Ethereum lead outflows', 1), ('WEMIX delisted from three exchanges after hack', 5), ('Convert 1 WEMIX (WEMIX) to USD - Bybit', 2), ('WEMIX price prediction 2030', 3), ('Old WEMIX story', 90), ('Wemix Foundation names new chief', 30), ('WEMIX delisted from three exchanges after hack', 6)]), 'WEMIX-USD', 'WEMIX', t0)
check('headlines: only recent ones that name the holding, newest first, no price pages or repeats', heads == [{'title': 'WEMIX delisted from three exchanges after hack', 'hours': 5.0}, {'title': 'Wemix Foundation names new chief', 'hours': 30.0}], heads)
check('a share is matched by its code or its company name', [n['title'] for n in m.pick_headlines(feed([('Apple supplier warns on demand', 2), ('Solana addresses surge', 3), ('Why AAPL slid today', 4), ('Pineapple prices rise', 1)]), 'AAPL', 'Apple Inc.', t0)] == ['Apple supplier warns on demand', 'Why AAPL slid today'])
check('a test run never fetches real headlines', m.fetch_news({'symbol': 'AAPL', 'label': 'AAPL', 'name': 'Apple Inc.'}, t0) == [])
D.t.clear(); PRICES.clear(); NEWS.clear(); MODEL['answer'] = None; MODEL['prompts'].clear(); SNAP['3-100'] = rows()
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=24, maxHoldDays=20, screeners=['3-100']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
s, rec = run(t0); p = portfolio(); a, b, c = p['holdings'][:3]
NEWS[a['symbol']] = [{'title': f"{a['label']} cuts its forecast after a recall", 'hours': 4.0}]
SNAP['3-100'] = [dict(r, rank=40, score=1.5, signal='HOLD', rsi=38, d1=-4.0) if r['symbol'] == a['symbol'] else r for r in rows()]
PRICES[a['symbol']] = a['buyPrice'] * 0.97
MODEL['answer'] = {'decisions': [{'symbol': a['label'], 'action': 'sell', 'reason': 'Rank fell from 1 to 40, score +1.5, and a recall headline'}, {'symbol': b['label'], 'action': 'hold', 'reason': 'Rank and score steady'}, {'symbol': 'ZZZZ', 'action': 'sell', 'reason': 'not held'}, {'symbol': c['label'], 'action': 'dump', 'reason': 'x'}], 'picks': []}
before = len(MODEL['prompts']); s, rec = run(t0 + dt.timedelta(days=1)); held = [h['id'] for h in portfolio()['holdings']]; ask = MODEL['prompts'][before]; sale = [e for e in rec['log'] if e['type'] == 'sell'][-1]
check('the review is given each holding: bought on what, the figures now, how it has moved, the rules, the headlines', f"{a['label']} | bought 1 day ago at rank" in ask['user'] and 'now rank 40, score +1.5, signal mixed, RSI 38, 1 day -4.0%' in ask['user'] and 'since buying -3.0% (best +0.0%, worst -3.0%)' in ask['user'] and 'the rules sell it at -10% or +18%, or in 19 days at the latest' in ask['user'] and f"headlines: (4 hours old) {a['label']} cuts its forecast after a recall" in ask['user'] and 'headlines: none found' in ask['user'] and 'untrusted text' in ask['system'] and 'fake' in ask['system'], ask['user'][:700])
check('it sells the one the AI model gave a reason for, and says so', a['id'] not in held and sale['kind'] == 'ai' and sale['symbol'] == a['label'] and "The AI model's review found a reason to sell before the rules would: Rank fell from 1 to 40, score +1.5, and a recall headline (-3.0% since it was bought)" in sale['text'], sale)
check('the sale lists the headlines it was shown', any(d.startswith('Headlines it was shown: "') and 'cuts its forecast after a recall" (4 hours old)' in d for d in sale['detail']), sale['detail'])
check('a holding it chose to keep stays, with its latest review noted; a symbol it does not hold and an unknown answer are ignored', b['id'] in held and c['id'] in held and rec['state']['open'][b['id']]['view'] == {'t': m.iso(t0 + dt.timedelta(days=1)), 'sell': False, 'text': 'Rank and score steady'} and 'view' not in rec['state']['open'][c['id']] and s['sold'] == 1, rec['state']['open'].get(b['id']))
check('the finished trade is recorded as sold early by the AI model', rec['history'][-1]['exit'] == 'ai' and m.scorecard(rec['history'])['groups']['exit'][0]['label'] == "sold early by the AI model's review" and rec['state']['watch'][-1]['id'] == a['id'], rec['history'][-1])
s2, body = call(action='get', userId=U)
check('the dashboard gets the latest review of each holding', [pl['view']['text'] for pl in body['plans'] if pl['id'] == b['id']] == ['Rank and score steady'] and body['aiSellPausedUntil'] is None)
MODEL['answer'] = None; s, rec = run(t0 + dt.timedelta(days=2)); check('no answer from the AI model: nothing is sold on its account', s['sold'] == 0)
MODEL['answer'] = {'decisions': [{'symbol': b['label'], 'action': 'hold', 'reason': 'keep it for ever'}]}; PRICES[b['symbol']] = b['buyPrice'] * 0.85
s, rec = run(t0 + dt.timedelta(days=3)); check('it cannot keep a holding past a rule: the loss limit still sells', b['id'] not in [h['id'] for h in portfolio()['holdings']] and [e for e in rec['log'] if e['type'] == 'sell'][-1]['kind'] == 'stop')
early = lambda after: dict(risk=3, pct=-1.0, exit='ai', after=after, sold=m.iso(t0), screener='3-100', label='X', rank=2, rsi=50)
rec = m.load_item(U); rec['history'] = [early(2.0)] * 8; notes = m.review_ai_sells(rec, t0 + dt.timedelta(days=4))
check('if what it sold early went on rising, its early sells are paused', rec['state']['aiSell']['rest'] == m.iso(t0 + dt.timedelta(days=18)) and "Pausing the AI model's early sells for 14 days: the last 8 holdings it sold early went on to +2.0% on average afterwards" in notes[0]['text'], notes)
m.save_item(U, rec); MODEL['answer'] = {'decisions': [{'symbol': c['label'], 'action': 'sell', 'reason': 'x'}]}; before = len(MODEL['prompts']); s, rec = run(t0 + dt.timedelta(days=5))
check('while paused the review is not asked and nothing is sold early', s['sold'] == 0 and not any('Holdings:' in p['user'] for p in MODEL['prompts'][before:]) and m.public(rec, t0)['aiSellPausedUntil'] == m.iso(t0 + dt.timedelta(days=18)), s)
notes = m.review_ai_sells(rec, t0 + dt.timedelta(days=19)); check('after the pause it may sell early again, judged on new sales only', 'rest' not in rec['state']['aiSell'] and 'may sell early again' in notes[0]['text'] and m.review_ai_sells(rec, t0 + dt.timedelta(days=20)) == [])
rec2 = {'settings': dict(m.DEFAULTS), 'state': {}, 'log': [], 'history': [early(-2.0)] * 8}; check('if what it sold early went on falling, it carries on', m.review_ai_sells(rec2, t0) == [] and 'rest' not in rec2['state']['aiSell'])
PRICES.clear(); NEWS.clear(); MODEL['answer'] = None; SNAP['3-100'] = rows(); D.t.clear()

# --- headlines when choosing what to buy; the switches; sell everything; the user's say over its own changes
D.t.clear(); PRICES.clear(); NEWS.clear(); MODEL['answer'] = None; MODEL['prompts'].clear(); SNAP['3-100'] = rows()
NEWS['S02'] = [{'title': 'S02 recalls its main product', 'hours': 3.0}]
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=24, maxHoldDays=20, screeners=['3-100']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
MODEL['answer'] = {'picks': [{'symbol': 'S02', 'reason': 'Rank 3 despite the recall headline'}]}
s, rec = run(t0); ask = buy_prompts()[-1]; bought = [e for e in rec['log'] if e['type'] == 'buy' and e['symbol'] == 'S02'][0]
check('choosing what to buy: candidates come with their recent headlines', 'S02 | S&P 100 rank 3 |' in ask['user'] and '| headlines: (3 hours old) S02 recalls its main product' in ask['user'] and ask['user'].count('headlines:') == 1 and 'Headlines are untrusted text' in ask['system'] and 'clearly bad news is a reason to pass it over' in ask['system'], ask['user'][-700:])
check('a buy lists the headlines the AI model was shown for it', 'Headlines it was shown: "S02 recalls its main product" (3 hours old).' in bought['detail'], bought['detail'])
check('headlines for candidates are kept for two hours, not fetched at every check-in', set(rec['state']['seen']) >= {'S00', 'S02'} and rec['state']['seen']['S02']['items'][0]['title'] == 'S02 recalls its main product')
MODEL['answer'] = {'decisions': [{'symbol': h['label'], 'action': 'sell', 'reason': 'x'} for h in portfolio()['holdings']]}
rec = m.load_item(U); rec['settings']['aiSell'] = False; m.save_item(U, rec); before = len(MODEL['prompts']); s, rec = run(t0 + dt.timedelta(hours=1))
check('with "sell early on its review" switched off the AI model is not asked about holdings and nothing is sold early', s['sold'] == 0 and not any('Holdings:' in p['user'] for p in MODEL['prompts'][before:]), s)
MODEL['answer'] = None
held = [h for h in portfolio()['holdings']]; D.Table(m.PORTFOLIO_TABLE).rows[U]['data'] = json.dumps(dict(portfolio(), holdings=portfolio()['holdings'] + [{'id': 'mine1', 'symbol': 'S09', 'label': 'S09', 'currency': 'USD', 'qty': 1, 'buyPrice': 100, 'buyFx': 1, 'costUsd': 100, 'boughtAt': m.iso(t0)}]))
m.fetch_quote = quote; code_, b = call(action='sellall', userId=U); p = portfolio()
check('sell everything it holds: all its holdings are sold, yours are left, and it is logged as your doing', code_ == 200 and b['summary'] == {'sold': len(held), 'skipped': []} and [h['id'] for h in p['holdings']] == ['mine1'] and len(p['closed']) == len(held) and b['plans'] == [] and 'Sold because you pressed "Sell everything it holds"' in b['log'][-1]['text'] and b['log'][-1]['kind'] == 'hand' and all(t['exit'] == 'hand' for t in m.load_item(U)['history'][-len(held):]), (code_, b.get('summary'), [h['id'] for h in p['holdings']]))
code_, b = call(action='sellall', userId=U); check('pressing it again with nothing held does nothing', code_ == 200 and b['summary'] == {'sold': 0, 'skipped': []} and len(portfolio()['closed']) == len(held))
rec = m.load_item(U); rec['state']['tune'] = {'values': {'3': {'take': 9.0}}, 'past': [], 'mark': 0, 'trial': {'id': 4, 'risk': 3, 'param': 'stop', 'old': -10, 'new': -5.0, 'direction': 'up', 'since': m.iso(t0), 'why': 'w', 'gain': 0.5, 'buys': 0}}; m.save_item(U, rec)
code_, b = call(action='tune', userId=U, op='stop')
check('you can stop its running trial', b['tune']['trial'] is None and b['tune']['past'][-1]['verdict'] == 'stopped' and b['tune']['past'][-1]['result'] == 'stopped by you' and 'You stopped its trial (sell at -5% instead of "sell at -10%"). The rule stays as it was.' in b['log'][-1]['text'], b['tune'])
code_, b = call(action='tune', userId=U, op='restore', param='take')
check('and put back a rule it changed by itself', b['rules']['take'] == 18 and b['rules']['changed'] == {} and "You put a rule back to the Balanced level's own: sell at +18%." in b['log'][-1]['text'], b['rules'])
code_, b2 = call(action='tune', userId=U, op='restore', param='positions'); check('nothing else can be changed through that door', b2['rules'] == b['rules'] and len(b2['log']) == len(b['log']))
off = {'settings': dict(m.DEFAULTS, risk=3, selfTune=False), 'state': {'closedCount': 20}, 'log': [], 'history': [dict(risk=3, pct=1.0, peak=10.0, low=0.0, rank=2, rsi=50, exit='time', sold=m.iso(t0))] * 10 + [dict(risk=3, pct=-2.0, peak=0.5, low=-2.0, rank=2, rsi=50, exit='time', sold=m.iso(t0))] * 10}
check('with its trials switched off it starts none', m.review_tuning(off, t0) == [] and off['state']['tune']['trial'] is None)
off['state']['tune']['trial'] = {'id': 1, 'risk': 3, 'param': 'take', 'old': 18, 'new': 9.0, 'since': m.iso(t0)}
check('and a trial already running is ended, unchanged', 'its trials were switched off' in m.review_tuning(off, t0)[0]['text'] and off['state']['tune']['trial'] is None and m.rules_for(off['settings'], off['state'])['take'] == 18)
D.t.clear(); MAILS.clear(); rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, emails=False, screeners=['3-100']); rec['state'].update(startedAt=m.iso(t0), closedCount=20); rec['history'] = [dict(risk=3, pct=1.0, rank=2, rsi=50, exit='time', sold=m.iso(t0), label='X', screener='3-100'), dict(risk=3, pct=-1.0, rank=2, rsi=50, exit='time', sold=m.iso(t0), label='X', screener='3-100')] * 10; m.save_item(U, rec)
s, rec = run(t0); check('with its emails switched off a review is still done and listed, but no email is sent', MAILS == [] and any('Reviewed its own rules after 20 finished trades' in e['text'] for e in rec['log']), [e['text'][:60] for e in rec['log']])
PRICES.clear(); NEWS.clear(); MODEL['answer'] = None; SNAP['3-100'] = rows(); D.t.clear()

# --- your own loss limit and gain mark; what its finished trades have made in all
own = lambda **k: {f: m.clean_settings(dict(k), U)[f] for f in ('stopPct', 'takePct')}
check('your own limits are optional sizes in percent, kept inside the same bounds as its own', own() == {'stopPct': None, 'takePct': None} and own(stopPct=-6, takePct='10') == {'stopPct': 6.0, 'takePct': 10.0} and own(stopPct=100, takePct=1) == {'stopPct': 30.0, 'takePct': 2.0} and own(stopPct='', takePct=0) == {'stopPct': None, 'takePct': None} and own(stopPct=0.2) == {'stopPct': 1.5, 'takePct': None})
yours = dict(m.DEFAULTS, risk=3, stopPct=6.0, takePct=10.0)
check('they come before the level and before its own changes', m.rules_for(yours, {'tune': {'values': {'3': {'stop': -4.0, 'take': 25.0, 'top': 5}}}}) == dict(m.RISK[3], stop=-6.0, take=10.0, top=5) and m.set_by_user(yours) == {'stop', 'take'} and m.set_by_user(dict(m.DEFAULTS)) == set())
D.t.clear(); PRICES.clear(); NEWS.clear(); MODEL['answer'] = None; SNAP['3-100'] = rows()
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=24, maxHoldDays=20, screeners=['3-100'], stopPct=6.0, takePct=10.0); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
s, rec = run(t0); a, b, c = portfolio()['holdings'][:3]; PRICES[a['symbol']] = a['buyPrice'] * 0.93; PRICES[b['symbol']] = b['buyPrice'] * 1.11
s, rec = run(t0 + dt.timedelta(days=1)); texts = [e['text'] for e in rec['log'] if e['type'] == 'sell']
check('it sells at your limits, not the level\'s', s['sold'] == 2 and any('past the -6% limit' in t for t in texts) and any('reached the +10% mark' in t for t in texts), texts)
check('what its finished trades have made in all is kept, apart from the sold list', rec['state']['realizedUsd'] == round(sum(t['usd'] for t in rec['history']), 2) == 40.0 and m.public(rec, t0)['realizedUsd'] == 40.0, (rec['state'].get('realizedUsd'), [t['usd'] for t in rec['history']]))
pub = m.public(rec, t0, U)
check('the dashboard is told which rules are yours and what an empty field would fall back to', pub['rules']['yours'] == ['stop', 'take'] and pub['rules']['stop'] == -6.0 and pub['rules']['take'] == 10.0 and pub['rules']['level'] == {'stop': -10, 'take': 18} and pub['rules']['changed'] == {} and all(pl['stop'] == -6.0 and pl['take'] == 10.0 for pl in pub['plans']), pub['rules'])
fixed = {'settings': dict(m.DEFAULTS, risk=3, takePct=10.0), 'state': {'closedCount': 20}, 'log': [], 'history': [dict(risk=3, pct=1.0, peak=9.0, low=0.0, rank=2, rsi=50, exit='time', sold=m.iso(t0), label='X', screener='3-100')] * 10 + [dict(risk=3, pct=-2.0, peak=0.5, low=-2.0, rank=2, rsi=50, exit='time', sold=m.iso(t0), label='X', screener='3-100')] * 10}
notes = m.review_tuning(fixed, t0); trial = fixed['state']['tune']['trial']
check('its trials leave a rule you set alone', trial is None or trial['param'] != 'take', (trial, notes))
taken = {'settings': dict(m.DEFAULTS, risk=3, takePct=10.0), 'state': {'tune': {'values': {}, 'past': [], 'mark': 0, 'trial': {'id': 1, 'risk': 3, 'param': 'take', 'old': 18, 'new': 9.0, 'since': m.iso(t0)}}}, 'log': [], 'history': []}
check('and a trial of a rule you then set yourself is ended', 'you set that rule yourself' in m.review_tuning(taken, t0)[0]['text'] and taken['state']['tune']['trial'] is None)
PRICES.clear(); SNAP['3-100'] = rows(); D.t.clear()

# --- improving its own rules: what the record suggests, a trial beside the current rule, keep or drop, an email each time
TR = lambda pct, peak=None, low=None, rank=2, rsi=50, exit='time', **k: dict(risk=3, pct=pct, peak=pct if peak is None else peak, low=min(pct, 0) if low is None else low, rank=rank, rsi=rsi, exit=exit, screener='3-100', label='X', **k)
base_rules = m.rules_for({'risk': 3})
check('too few trades: nothing is suggested', m.propose([TR(1.0)] * 19, base_rules) == [])
ideas = m.propose([TR(1.0, peak=10.0)] * 12 + [TR(-2.0, peak=0.5)] * 12, base_rules)
check('holdings that were well up and ended low: a nearer gain mark is suggested, with the reason', ideas and ideas[0]['param'] == 'take' and ideas[0]['new'] == 9.0 and ideas[0]['old'] == 18 and ideas[0]['gain'] == 4.0 and '12 of the last 24 finished trades were up 9% or more at some point while held, and ended at +1.0% on average' in ideas[0]['why'], ideas[:1])
ideas = m.propose([TR(-9.0, low=-9.5)] * 10 + [TR(2.0)] * 14, base_rules)
check('holdings that were well down and stayed down: a nearer loss limit', ideas and ideas[0]['param'] == 'stop' and ideas[0]['new'] == -5.0 and 'were down 5% or more' in ideas[0]['why'], ideas[:1])
ideas = m.propose([TR(18.5, exit='take', after=6.0)] * 6 + [TR(0.0)] * 18, base_rules)
check('sold at the gain mark and then went on rising: a further gain mark', [i for i in ideas if i['param'] == 'take' and i['new'] == 27.0 and 'went on to +6.0% on average afterwards' in i['why']], ideas)
ideas = m.propose([TR(3.0, rank=2)] * 12 + [TR(-1.0, rank=8)] * 12, base_rules)
check('buys near the top did better: buy nearer the top', ideas and ideas[0]['param'] == 'top' and ideas[0]['new'] == 5 and 'buys ranked 1 to 5 averaged +3.0% over 12 trades; those ranked lower -1.0% over 12' in ideas[0]['why'], ideas[:1])
ideas = m.propose([TR(2.0, rsi=50)] * 12 + [TR(-1.0, rsi=72)] * 12, base_rules)
check('calmer buys did better: a lower RSI limit', [i for i in ideas if i['param'] == 'max_rsi' and i['new'] == 68], ideas)
check('an even record: nothing is suggested', m.propose([TR(1.0), TR(-1.0)] * 12, base_rules) == [])
check('a change that was dropped lately is not tried again straight away', m.propose([TR(1.0, peak=10.0)] * 12 + [TR(-2.0, peak=0.5)] * 12, base_rules, [{'param': 'take', 'direction': 'down', 'verdict': 'dropped'}]) == [] or m.propose([TR(1.0, peak=10.0)] * 12 + [TR(-2.0, peak=0.5)] * 12, base_rules, [{'param': 'take', 'direction': 'down', 'verdict': 'dropped'}])[0]['param'] != 'take')
check('its own changes stay inside fixed bounds', m.rules_for({'risk': 3}, {'tune': {'values': {'3': {'stop': -99, 'take': 500, 'top': 1, 'trail': 0.01, 'positions': 1, 'crypto': 1}}}}) == dict(m.RISK[3], stop=-30.0, take=80.0, top=3, trail=0.2))
check('a test run never sends a real email', m.send_mail('nobody@example.com', 'x', ['y']) is False)

D.t.clear(); PRICES.clear(); MAILS.clear(); SNAP['3-100'] = rows(n=200)
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=24, maxHoldDays=1, screeners=['3-100']); rec['state'].update(startedAt=m.iso(t0), closedCount=20)
rec['history'] = [dict(TR(1.0, peak=10.0), sold=m.iso(t0), usd=10.0, cost=1000.0)] * 10 + [dict(TR(-2.0, peak=0.5), sold=m.iso(t0), usd=-20.0, cost=1000.0)] * 10
notes = m.review_tuning(rec, t0, lambda subject, lines: MAILS.append((subject, lines))); trial = rec['state']['tune']['trial']
check('after 20 finished trades it starts a trial of the most promising change', trial and trial['param'] == 'take' and trial['new'] == 9.0 and trial['old'] == 18 and trial['id'] == 1 and rec['state']['tune']['mark'] == 20 and 'started a trial: sell at +9% instead of the current "sell at +18%"' in notes[0]['text'] and 'Every second buy follows the changed rule' in notes[0]['text'], (trial, notes))
check('and emails what it is trying, why, and the record', len(MAILS) == 1 and 'trying a change to one of its rules' in MAILS[0][0] and any('What it is trying: sell at +9% instead of the current "sell at +18%" (Balanced level).' == l for l in MAILS[0][1]) and any(l.startswith('Why: 10 of the last 20 finished trades were up 9% or more') for l in MAILS[0][1]) and any('Last 30 days: 20 finished trades, 10 of them up, -$100.00 in all, which is -1.25% of the $8,000 budget.' == l for l in MAILS[0][1]) and any('fake-money experiment' in l for l in MAILS[0][1]) and not any('@' in l for l in MAILS[0][1]), MAILS[0])
check('the rule in force is unchanged while it is only on trial', m.rules_for(rec['settings'], rec['state'])['take'] == 18)
m.save_item(U, rec); s, rec = run(t0); p = portfolio(); tags = [rec['state']['open'][h['id']].get('v') for h in p['holdings']]
check('every second buy follows the changed rule', tags == ['new', 'old', 'new'] and all(rec['state']['open'][h['id']]['x'] == 1 for h in p['holdings']), tags)
for h in p['holdings']: PRICES[h['symbol']] = h['buyPrice'] * 1.10
s, rec = run(t0 + dt.timedelta(hours=2)); sold_now = [e for e in rec['log'] if e['type'] == 'sell']
check('at +10% the trial buys are sold (their mark is +9%) and the other is kept (its mark is +18%)', len(sold_now) == 2 and all('reached the +9% mark' in e['text'] for e in sold_now) and len([h for h in portfolio()['holdings'] if h['id'] == p['holdings'][1]['id']]) == 1 and all('This buy was part of a trial of a changed rule.' in ' '.join(e['detail']) for e in sold_now), [e['text'] for e in sold_now])
s, b = call(action='get', userId=U)
check('the dashboard shows the trial and how the two groups are doing', b['tune']['trial']['text'] == 'sell at +9% instead of "sell at +18%"' and b['tune']['trial']['with'] == 2 and b['tune']['trial']['without'] == 0 and b['tune']['trial']['avgWith'] == 10.0 and b['tune']['nextReviewIn'] is None and [pl['take'] for pl in b['plans'] if pl['id'] == p['holdings'][1]['id']] == [18], b['tune'])
def finish(rec, with_pcts, without_pcts):
    rec['history'] += [dict(TR(x), x=1, v='new', sold=m.iso(t0)) for x in with_pcts] + [dict(TR(x), x=1, v='old', sold=m.iso(t0)) for x in without_pcts]
import copy as _c
good = _c.deepcopy(rec); good['history'] = [t for t in good['history'] if not t.get('x')]; finish(good, [3.0, 4.0, 3.5, 2.5, 3.0, 4.0, 3.5, 2.5, 3.0, 3.0], [0.5, -0.5, 0.0, 1.0, 0.0, -1.0, 0.5, 0.0, 0.5, -0.5]); MAILS.clear()
notes = m.review_tuning(good, t0 + dt.timedelta(days=9), lambda subject, lines: MAILS.append((subject, lines)))
check('clearly better with the change: it is kept, and the email says so with the numbers', good['state']['tune']['trial'] is None and m.rules_for(good['settings'], good['state'])['take'] == 9.0 and good['state']['tune']['past'][-1]['verdict'] == 'kept' and 'The change is kept: 10 trades with the change averaged +3.20%, 10 without it +0.05% (difference +3.15' in notes[0]['text'] and 'change kept' in MAILS[0][0] and any(l.startswith('Sells at -10% or +9%') for l in MAILS[0][1]), (notes, MAILS[:1]))
check('the dashboard marks the rule as changed by itself', m.public(good, t0)['rules']['changed'] == {'take': 18} and m.public(good, t0)['tune']['past'][-1]['text'] == 'sell at +9% instead of "sell at +18%"')
flat = _c.deepcopy(rec); flat['history'] = [t for t in flat['history'] if not t.get('x')]; finish(flat, [3.0, -4.0, 3.5, -2.5, 3.0, -4.0, 3.5, -2.5, 1.0, 0.0], [0.5, -0.5, 0.0, 1.0, 0.0, -1.0, 0.5, 0.0, 0.5, -0.5]); MAILS.clear()
notes = m.review_tuning(flat, t0 + dt.timedelta(days=9), lambda subject, lines: MAILS.append((subject, lines)))
check('no clear difference: the rule stays as it was', flat['state']['tune']['trial'] is None and m.rules_for(flat['settings'], flat['state'])['take'] == 18 and flat['state']['tune']['past'][-1]['verdict'] == 'dropped' and 'The rule stays as it was' in notes[0]['text'] and 'no clear improvement' in notes[0]['text'] and 'rule left as it was' in MAILS[0][0], notes)
few = _c.deepcopy(rec); few['history'] = [t for t in few['history'] if not t.get('x')]; finish(few, [3.0] * 5, [0.0] * 5)
check('before both groups are full it waits', m.review_tuning(few, t0 + dt.timedelta(days=9)) == [] and few['state']['tune']['trial'] is not None)
check('a trial that cannot fill its groups ends after 30 days, unchanged', 'too few trades had finished' in m.review_tuning(few, t0 + dt.timedelta(days=31))[0]['text'] and few['state']['tune']['trial'] is None and m.rules_for(few['settings'], few['state'])['take'] == 18)
moved = _c.deepcopy(rec); moved['settings']['risk'] = 4
check('changing the risk level ends the trial', 'The trial was stopped' in m.review_tuning(moved, t0 + dt.timedelta(days=1))[0]['text'] and moved['state']['tune']['trial'] is None)
quiet = m.load_item('tester@x.com'); quiet['settings'].update(risk=3); quiet['state'] = {'closedCount': 20}; quiet['history'] = [dict(TR(1.0), sold=m.iso(t0)), dict(TR(-1.0), sold=m.iso(t0))] * 10; MAILS.clear()
notes = m.review_tuning(quiet, t0, lambda subject, lines: MAILS.append((subject, lines)))
check('a review that finds nothing says so, and emails that too', 'nothing in the record suggests a change worth trying' in notes[0]['text'] and quiet['state']['tune']['trial'] is None and 'no change' in MAILS[0][0] and m.review_tuning(quiet, t0) == [])
wide = {'id': 7, 'risk': 3, 'param': 'top', 'old': 10, 'new': 15}; st = {'tune': {'trial': wide}}
picks = [c['rank'] for c in m.shortlist(m.new_portfolio(t0), dict(m.DEFAULTS, risk=3, screeners=['3-100']), {'3-100': rows(n=30, **{f'S{i:02d}': {'signal': 'BUY', 'rsi': 50, 'd30': 5.0} for i in range(30)})}, t0, None, wide)]
check('a wider buying rule on trial: it buys from the wider range', max(picks) == 15, picks)
f_in = m.remember_buy(st, {'id': 'h1', 'boughtAt': m.iso(t0)}, {'symbol': 'A', 'label': 'A', 'screener': '3-100', 'rank': 4, 'score': 3.0, 'rsi': 50, 'd7': 1, 'd30': 1, 'volume': 1}, dict(m.DEFAULTS, risk=3), 'rules')
f_out = m.remember_buy(st, {'id': 'h2', 'boughtAt': m.iso(t0)}, {'symbol': 'B', 'label': 'B', 'screener': '3-100', 'rank': 13, 'score': 3.0, 'rsi': 50, 'd7': 1, 'd30': 1, 'volume': 1}, dict(m.DEFAULTS, risk=3), 'rules')
check('and the extra buys are the group that is compared with the usual ones', f_in['v'] == 'old' and f_out['v'] == 'new' and f_out['x'] == 7, (f_in, f_out))
month = m.month_figures([{'usd': 100.0, 'sold': m.iso(t0 - dt.timedelta(days=3))}, {'usd': -40.0, 'sold': m.iso(t0 - dt.timedelta(days=10))}, {'usd': 25.0, 'sold': m.iso(t0 - dt.timedelta(days=45))}, {'sold': m.iso(t0)}], 10000.0, t0)
check('the last 30 days and the 30 before, in dollars and as a share of the budget', month == {'last30': {'n': 2, 'up': 1, 'usd': 60.0, 'pct': 0.6}, 'before30': {'n': 1, 'up': 1, 'usd': 25.0, 'pct': 0.25}}, month)
PRICES.clear(); SNAP['3-100'] = rows(); SNAP['7-1'] = rows('crypto', '7-1'); D.t.clear()

# scheduled event end to end (with the stand-ins patched in)
m.fetch_snapshot, m.fetch_quote, m.ask_model = snapshot, quote, model
D.t.clear(); rec = m.load_item(U); rec['settings'].update(enabled=True, screeners=['7-1'], risk=4); rec['state']['startedAt'] = m.iso(dt.datetime.utcnow()); m.save_item(U, rec)
rec2 = m.load_item('stranger@y.com'); rec2['settings']['enabled'] = True; D.Table(m.SETTINGS_TABLE).put_item(Item={'userId': 'stranger@y.com', 'data': json.dumps(rec2), 'enabled': True})
r = json.loads(m.lambda_handler({'source': 'aws.events'}, None)['body'])
check('the schedule runs the due user and skips one not on the list', len(r['ran']) == 1 and r['ran'][0]['bought'] >= 1 and 'stranger@y.com' not in D.Table(m.PORTFOLIO_TABLE).rows, r)
check('"check in now" has a 10-minute gap', call(action='run', userId=U)[0] == 429)
print('ALL PASS' if ok else 'SOME FAILED')
