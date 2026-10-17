"""Tests of the AI trader with stand-ins for the database, the screeners, prices and the AI model. Nothing real is touched."""
import importlib.util, json, sys, copy, os, datetime as dt
import boto3
from botocore.exceptions import ClientError
class T:
    def __init__(s): s.rows = {}; s.fail_next = False
    def get_item(s, Key): r = s.rows.get(Key.get('userId') or Key.get('user_date')); return {'Item': copy.deepcopy(r)} if r else {}      # the plans table is keyed by user_date
    def scan(s, **k): return {'Items': [copy.deepcopy(r) for r in s.rows.values()]}
    def delete_item(s, Key): s.rows.pop(Key.get('userId'), None)
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
# These tests set the pace (build-up days, check-in gap, holding time) by hand, as a user who has chosen his own values.
# A new user leaves all three to the risk level; that is tested on its own further down, with the real defaults (REAL).
REAL = dict(m.DEFAULTS, auto=list(m.DEFAULTS['auto'])); m.DEFAULTS.update(periodDays=10, everyHours=24, maxHoldDays=20, auto=[])
# Likewise these tests buy a coin the first time it is on the shortlist; the wait for a coin to stay there is tested on its own (STAY).
STAY = m.STAY_CHECKS; m.STAY_CHECKS = 1
# And each account learns from its own trades alone here, so that the reviews themselves are tested on one record. Live, the same
# reviews run once on every account's trades together; that is tested on its own at the end (CENTRAL).
SHARED = m.CENTRAL; m.CENTRAL = False
# And the AI model's notes are written from nine trades here; live it waits for 30 (LESSONS_MIN), tested on its own (NOTES).
NOTES = getattr(m, 'LESSONS_MIN', 0); m.LESSONS_MIN = 5
# And every share is sold by the ordinary rules here; the trial in which some are "patient" is tested on its own (PATIENT).
PATIENT_ON = getattr(m, 'PATIENT', False); m.PATIENT = False
# And no trading cost is taken off here, so that the amounts in the older checks stay round; the cost is tested on its own (COSTS).
COSTS = getattr(m, 'TRADE_COST', 0); m.TRADE_COST = 0
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
ATR = {}                     # how much a symbol normally moves in a day (%), where a test gives it; without it the simpler stop by holding time applies
def snapshot(k): return copy.deepcopy(SNAP.get(k))
def quote(sym):
    if sym == 'SPY': return {'price': 700.0, 'currency': 'USD', 'name': 'S&P 500 fund'}
    for k in SNAP:
        for r in SNAP[k]:
            if r['symbol'] == sym: return {'price': PRICES.get(sym, r['price']), 'currency': 'USD', 'name': 'Name of ' + sym, 'atr': ATR.get(sym)}
    return None
MODEL = {'answer': None, 'prompts': []}
def model(prompt): MODEL['prompts'].append(prompt); return copy.deepcopy(MODEL['answer'])
def call(**b): r = m.lambda_handler({'requestContext': {}, 'body': json.dumps(b)}, None); return r['statusCode'], json.loads(r['body'])
def portfolio(): it = D.Table(m.PORTFOLIO_TABLE).rows.get(U); return json.loads(it['data']) if it else None
def run(now, **settings):
    rec = m.load_item(U)
    if settings: rec['settings'].update(settings)
    s = m.run_user(U, rec, now, snapshot=snapshot, quote=quote, model=model, mail=lambda subject, lines: MAILS.append((subject, lines)), headlines=lambda h, now: NEWS.get(h['symbol'], []), strong=lambda prompt: (STRONG.append(prompt), model(prompt))[1]); m.save_item(U, rec); return s, rec
MAILS = []; NEWS = {}; STRONG = []
buy_prompts = lambda: [p for p in MODEL['prompts'] if 'Pick exactly' in p['user']]
t0 = dt.datetime(2026, 10, 12, 15, 0, 0)          # a Monday, US market open

# --- access and settings
check('someone not on the list and not on a paid plan is refused, and pointed to the plans', call(action='get', userId='stranger@y.com')[1] == {'success': True, 'allowed': False, 'locked': 'plan', 'upgrade': 'dashboard.html#upgrade'})
check('not on the list cannot switch it on', m.clean_settings({'enabled': True}, 'stranger@y.com')['enabled'] is False)
s, b = call(action='get', userId=U); check('defaults', b['allowed'] and b['settings'] == dict(m.DEFAULTS) and '3-100' in b['options']['screeners'], b)
s, b = call(action='save', userId=U, settings={'enabled': True, 'risk': 9, 'budgetUsd': 'lots', 'periodDays': 0.2, 'everyHours': 7, 'maxHoldDays': 5, 'screeners': ['3-100', 'nope'], 'x': 1})
check('settings are cleaned', b['settings'] == {'enabled': True, 'risk': 5, 'budgetUsd': 10000.0, 'periodDays': 1, 'everyHours': 24, 'maxHoldDays': 5, 'screeners': ['3-100'], 'aiSell': True, 'selfTune': True, 'emails': True, 'stopPct': None, 'takePct': None, 'auto': [], 'trailMode': 'gains', 'shares': {}, **({'holdings': None} if hasattr(m, 'holdings_of') else {})} and b['state'].get('startedAt') and b['log'][-1]['text'].startswith('Autopilot on'), b['settings'])
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
check('all 27 screeners are offered, in groups', len(b['options']['screeners']) == 27 and b['options']['screeners']['4-200'] == {'name': 'ASX 200', 'kind': 'stock', 'group': 'Asia-Pacific markets'} and {v['group'] for v in b['options']['screeners'].values()} == {'US markets', 'Europe markets', 'Asia-Pacific markets', 'Americas markets', 'Coins'}, b['options']['screeners'])
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
check('Sydney check-in buys only Australian shares, in dollars at the exchange rate, and only the Australian share of the budget (1 of the 4 holdings: US 2, Australia 1, UK 1)', s['bought'] == 1 and m.market_slots(m.load_item(U)['settings']) == {'US markets': 2, 'Asia-Pacific markets': 1, 'Europe markets': 1} and all(x['symbol'].endswith('.AX') and x['currency'] == 'AUD' and x['buyFx'] == 0.70 for x in p['holdings']) and abs(h['qty'] - 1000 / (h['buyPrice'] * 0.70)) < 1e-9 and h['costUsd'] == 1000 and p['cash'] == 99000, [(x['symbol'], x['currency'], x['buyFx']) for x in p['holdings']])
check('each market keeps its own last check', rec['state']['lastRunBy'] == {'au': m.iso(mon(1))} and m.due_markets(rec, mon(2)) == [] and m.due_markets(rec, mon(9)) == ['uk'] and m.due_markets(rec, mon(1, day=13)) == ['au'])
s, rec = run2(mon(9), markets=['uk']); p = portfolio(); uk = [x for x in p['holdings'] if x['symbol'].endswith('.L')]
check('London check-in: pence handled, the budget cap holds', s['bought'] == 1 and uk[0]['currency'] == 'GBp' and abs(uk[0]['buyFx'] - 0.013) < 1e-12 and abs(uk[0]['qty'] * uk[0]['buyPrice'] * 0.013 - 1000) < 1e-6 and len(p['holdings']) == 2, [(x['symbol'], x['buyFx']) for x in p['holdings']])
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
check('remembers what each buy was based on', len(rec['state']['open']) == 4 and {k: v for k, v in rec['state']['open'][ids['S00']].items() if k != 'heads'} == {'symbol': 'S00', 'label': 'S00', 'screener': '3-100', 'risk': 5, 'chosen': 'rules', 'rank': 1, 'score': 4.0, 'rsi': 50.0, 'd7': 3.0, 'd30': 5.0, 'volume': 1.2, 't': m.iso(t0), 'hold': 5.0, 'peak': 0.0, 'low': 0.0, 'stay': 1, 'path': [[24.0, 0.0]], 'stop': {'arm': 11.2, 'floor': None, 'move': None, 'room': None, 'mode': 'gains'}}, rec['state']['open'].get(ids['S00']))
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
check('the record and notes are put in front of the model when it chooses', 'All 14 closed trades' in text and '- S&P 100: 14 trades' in text and ('Note from the last review: Trades bought with RSI under 45' in text or 'Note from the last review (of 9 finished trades): Trades bought with RSI under 45' in text) and 'own record so far' in m.build_prompt(rec['settings'], SNAP['3-100'][:3], '', 1, text)['user'] and 'own record' not in m.build_prompt(rec['settings'], SNAP['3-100'][:3], '', 1)['user'])
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
check('a buy says what the plan for it is', any('The plan for it: keep it for up to 20 days. Sell sooner if it falls to -10% or reaches +18%. Rising is not a reason to sell it: while it keeps going up it is kept. Once it has been up 9%, a stop starts following it up, and it is sold only if it then falls back too far from its best. Also sell if its screener signal turns negative or it slips far down the ranking.' == d for e in rec['log'] if e['type'] == 'buy' for d in e.get('detail', [])), [e.get('detail') for e in rec['log'] if e['type'] == 'buy'][:1])
PRICES[sym] = base * 1.12; s, rec = run(t0 + dt.timedelta(days=1))
check('up 12% (under the +18% mark): kept, and its best so far is remembered', sym in [h['symbol'] for h in portfolio()['holdings']] and rec['state']['open'][first['id']]['peak'] == 12.0, rec['state']['open'].get(first['id']))
PRICES[sym] = base * 1.05; s, rec = run(t0 + dt.timedelta(days=2)); sale = [e for e in rec['log'] if e['type'] == 'sell'][-1]
check('slipped back to +5% from a best of +12%: sold to keep part of the gain', sym not in [h['symbol'] for h in portfolio()['holdings']] and sale['kind'] == 'trail' and 'Was up +12.0% at its best and has slipped back to +5.0%: sold to keep part of the gain' in sale['text'] and sale['pct'] == 5.0, sale)
check('the sale carries its story: what it was bought on, how long, best and worst, the figures at the sale, the rules', len(sale['detail']) >= 5 and sale['detail'][0].startswith('Bought at rank ') and 'Held 2 days. It was set to keep a holding at most 20 days.' in sale['detail'] and '+12.0% at its best' in ' '.join(sale['detail']) and 'sell if it falls to -10% or reaches +18%' in ' '.join(sale['detail']) and not any('S&P 500 fund' in d for d in sale['detail']), sale['detail'])
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
check('the dashboard gets a plan for each holding: sell-by time and marks', len(b['plans']) == len([h for h in portfolio()['holdings'] if h.get('by') == 'ai']) and plan['auto'] is True and plan['stop'] == -10 and plan['take'] == 18 and plan['arm'] == 9 and m.parse_time(plan['sellBy']) == m.when_open('us', m.parse_time(plan['boughtAt']) + dt.timedelta(days=20)) and plan['sellBy'] == '2026-11-02T14:35:00Z' and plan['market'] == 'US', plan)   # 20 days from Monday 12 Oct 15:00 is a Sunday: sold when the US market opens on the Monday
check('and the rules in force, the month so far and the review countdown', b['rules']['stop'] == -10 and b['rules']['changed'] == {} and b['month']['last30']['n'] >= 0 and b['tune']['trial'] is None and b['tune']['nextReviewIn'] == 19 and b['now'], (b['rules'], b['tune']))

# --- the activity list: the same uneventful check-in is counted, not repeated; reasons name the right setting
D.t.clear(); PRICES.clear(); SNAP['7-1'] = rows('crypto', '7-1'); SNAP['3-100'] = [dict(r, signal='HOLD') for r in rows()]; MODEL['prompts'].clear()
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=10000.0, periodDays=1, everyHours=0.5, maxHoldDays=20, screeners=['3-100', '7-1']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
for i in range(60): s, rec = run(t0 + dt.timedelta(minutes=30 * i))
coins = [h for h in portfolio()['holdings'] if h.get('by') == 'ai']; asked = len(buy_prompts()); last = rec['log'][-1]
check('shares and coins at Balanced with no share to buy: coins stop at a quarter of the budget and it says why', len(coins) == 2 and sum(h['costUsd'] for h in coins) == 2500 and last['key'] == 'share' and last['text'] == 'Checked in. Coins already hold their share of the budget ($2,500 of $2,500). The rest is for US markets, bought when that market is open. The shares are set under "Screeners it buys from".', last)
check('the same uneventful check-in is counted, not listed again', last.get('n', 1) > 10 and last['first'] < last['t'] and len([e for e in rec['log'] if e.get('key') == 'share']) == 1, (last.get('n'), len(rec['log'])))
s, rec = run(t0 + dt.timedelta(hours=31)); SNAP['3-100'] = rows(); check('with the coin share used up the AI model is not asked to pick again', len(buy_prompts()) == asked, (asked, len(buy_prompts())))

# --- hold or sell: the AI model reviews each holding the rules are keeping, with the screener's figures now and recent headlines
feed = lambda items: ('<rss><channel>' + ''.join(f"<item><title>{t}</title><pubDate>{(t0 - dt.timedelta(hours=h)).strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate></item>" for t, h in items) + '</channel></rss>').encode()
heads = m.pick_headlines(feed([('Solana and Ethereum lead outflows', 1), ('WEMIX delisted from three exchanges after hack', 5), ('Convert 1 WEMIX (WEMIX) to USD - Bybit', 2), ('WEMIX price prediction 2030', 3), ('WEMIX price forecast: rebound strengthens', 1), ('Old WEMIX story', 90), ('Wemix Foundation names new chief', 30), ('WEMIX delisted from three exchanges after hack', 6)]), 'WEMIX-USD', 'WEMIX', t0)
check('headlines: only recent ones that name the holding, newest first, no price pages or repeats', heads == [{'title': 'WEMIX delisted from three exchanges after hack', 'hours': 5.0}, {'title': 'Wemix Foundation names new chief', 'hours': 30.0}], heads)
erg = feed([('ERG (BIT:ERG) Stock Could Be Trading At A Premium Following A New Poland Wind Deal - Yahoo Finance', 19), ('ERG (BIT:ERG) Faces An 11% Undervalued View, Is The Stock Still Pricey? - Yahoo Finance', 48),
            ('ERG lifts dividend after record wind output', 5), ('Ergo developers ship a privacy upgrade', 6), ('ERG token jumps as Ergo mainnet upgrade goes live', 3), ('ERG rallies 12%', 2), ('Why crypto traders are watching ERG this week', 9)])
check('a coin whose ticker is also a company: share news is left out, and it must be named by its name or with a crypto word (the real headlines of 10 Oct 2026)', [n['title'] for n in m.pick_headlines(erg, 'ERG-USD', 'Ergo', t0)] == ['ERG token jumps as Ergo mainnet upgrade goes live', 'Ergo developers ship a privacy upgrade', 'Why crypto traders are watching ERG this week'], [n['title'] for n in m.pick_headlines(erg, 'ERG-USD', 'Ergo', t0)])
if 'up|down' in m.NEWS_JUNK.pattern:
    check('a page that only explains a price move is not news (seen live 12 Oct 2026); a real headline that mentions a price stays', [n['title'] for n in m.pick_headlines(feed([('Why is Walrus price up 13.5% today? - Traders Union', 2), ('Walrus price is down after the unlock', 3), ('DATA Network joins Sui and Walrus to scale AI training data', 1), ('Walrus cuts storage prices for developers', 4)]), 'WAL-USD', 'Walrus', t0)]
          == ['DATA Network joins Sui and Walrus to scale AI training data', 'Walrus cuts storage prices for developers'])
check('with no name known for a coin, the ticker alone is not enough', [n['title'] for n in m.pick_headlines(erg, 'ERG-USD', '', t0)] == ['ERG token jumps as Ergo mainnet upgrade goes live', 'Why crypto traders are watching ERG this week'])
check('a coin whose name is its ticker still needs a crypto word', [n['title'] for n in m.pick_headlines(feed([('NEO unveils a new handset', 2), ('NEO blockchain adds staking rewards', 3)]), 'NEO-USD', 'NEO', t0)] == ['NEO blockchain adds staking rewards'])
check('share headlines are untouched by this (they may say "stock" and carry an exchange code)', [n['title'] for n in m.pick_headlines(feed([('Nomura Research Institute (TSE:4307) Is Up 10.6% After AI-Sector Rotation', 4), ('Why Trend Micro stock is up', 2)]), '4307.T', 'Nomura Research Institute, Ltd.', t0)] == ['Nomura Research Institute (TSE:4307) Is Up 10.6% After AI-Sector Rotation'])
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
check('a holding it chose to keep stays, with its latest review noted; a symbol it does not hold and an unknown answer are ignored', b['id'] in held and c['id'] in held and rec['state']['open'][b['id']]['view'] == {'t': m.iso(t0 + dt.timedelta(days=1)), 'sell': False, 'tighten': False, 'text': 'Rank and score steady', 'larger': False} and 'view' not in rec['state']['open'][c['id']] and s['sold'] == 1, rec['state']['open'].get(b['id']))
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
class Open(dt.datetime):                                                                                   # a Thursday afternoon UTC: the US market is open
    @classmethod
    def utcnow(cls): return dt.datetime(2026, 10, 15, 15, 0, 0)
clock = m.datetime; m.datetime = Open
m.fetch_quote = quote; code_, b = call(action='sellall', userId=U); p = portfolio()
check('sell everything it holds: all its holdings are sold, yours are left, and it is logged as your doing', code_ == 200 and b['summary'] == {'sold': len(held), 'skipped': [], 'closed': []} and [h['id'] for h in p['holdings']] == ['mine1'] and len(p['closed']) == len(held) and b['plans'] == [] and 'Sold because you pressed "Sell everything it holds"' in b['log'][-1]['text'] and b['log'][-1]['kind'] == 'hand' and all(t['exit'] == 'hand' for t in m.load_item(U)['history'][-len(held):]), (code_, b.get('summary'), [h['id'] for h in p['holdings']]))
code_, b = call(action='sellall', userId=U); m.datetime = clock; check('pressing it again with nothing held does nothing', code_ == 200 and b['summary'] == {'sold': 0, 'skipped': [], 'closed': []} and len(portfolio()['closed']) == len(held))
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
s, rec = run(t0); check('with its emails switched off a review is still done and listed, but no email is sent', MAILS == [] and any('Progress after 20 finished trades: the last 20 averaged +0.00% a trade (+$0.00, 10 up), its first batch, and not up.' in e['text'] and 'no rule was changed' in e['text'] for e in rec['log']) and not any('Reviewed its own rules' in e['text'] for e in rec['log']), [e['text'][:60] for e in rec['log']])
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

# --- a gain worth keeping depends on the holding time; a big gain is not handed back; the larger model when a gain is at stake
B3, A5 = m.RISK[3], m.RISK[5]
check('the rise from which a gain is protected follows the holding time (Balanced: 9% at 20 days, 4.5% at 5, 2% at 1, 1% at 6 hours)', [m.gain_arm(B3, d) for d in (60, 20, 5, 1, 0.25, 1 / 24)] == [9.0, 9.0, 4.5, 2.0, 1.0, 1.0] and m.gain_arm(A5, 0.25) == 2.5 and m.gain_arm(A5, 20) == 22.5, [m.gain_arm(B3, d) for d in (60, 20, 5, 1, 0.25, 1 / 24)])
near = lambda a, b: a is not None and abs(a - b) < 0.05
check('a small gain may give back about half, a big one much less', m.gain_floor(B3, 0.25, 0.9) is None and near(m.gain_floor(B3, 0.25, 4.0), 2.18) and near(m.gain_floor(B3, 0.25, 17.0), 12.5) and near(m.gain_floor(B3, 0.25, 30.0), 22.5) and near(m.gain_floor(B3, 20, 12.0), 7.0), [m.gain_floor(B3, 0.25, x) for x in (0.9, 4.0, 17.0, 30.0)])
D.t.clear(); PRICES.clear(); NEWS.clear(); STRONG.clear(); MODEL['answer'] = None; MODEL['prompts'].clear(); SNAP['7-1'] = rows('crypto', '7-1')
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=24, maxHoldDays=0.25, screeners=['7-1']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
s, rec = run(t0); a, b, c = portfolio()['holdings'][:3]; half = dt.timedelta(minutes=30)
PRICES[a['symbol']] = a['buyPrice'] * 1.04; PRICES[b['symbol']] = b['buyPrice'] * 1.17; MODEL['answer'] = {'decisions': [{'symbol': a['label'], 'action': 'hold', 'reason': 'Up 4% and still climbing'}]}
s, rec = run(t0 + half); held = [h['id'] for h in portfolio()['holdings']]; ask = [p for p in MODEL['prompts'] if 'Holdings:' in p['user']][-1]
check('up 4% and up 17% after 30 minutes on a 6-hour holding: both kept while they are at their best (the mark is +18%)', a['id'] in held and b['id'] in held and s['sold'] == 0, s)
check('the review sees the path and what is protected', f"path: 0.5h +4.0% | the rules sell it at -10% or +18%, or in 6 hours at the latest; protected: sold if it slips back to +2.2%" in ask['user'] and 'still climbing' in ask['system'] and 'path: 0.5h +0.0%' in ask['user'] and 'a gain is protected once it has been up 1%' in ask['user'], ask['user'][:900])
check('a gain is at stake, so the larger model was asked, and the review says so', len(STRONG) == 1 and rec['state']['strong'] == {'day': m.iso(t0)[:10], 'n': 1} and rec['state']['open'][a['id']]['view']['larger'] is True, (len(STRONG), rec['state'].get('strong')))
s2, body = call(action='get', userId=U); plan = [pl for pl in body['plans'] if pl['id'] == a['id']][0]
check('the dashboard is told what is protected for each holding', plan['arm'] == 1.0 and near(plan['floor'], 2.2) and body['rules']['arm'] == 1.0 and [pl['floor'] for pl in body['plans'] if pl['id'] == c['id']] == [None], plan)
PRICES[a['symbol']] = a['buyPrice'] * 1.02; PRICES[b['symbol']] = b['buyPrice'] * 1.12; MODEL['answer'] = None
s, rec = run(t0 + 2 * half); sales = {e['symbol']: e for e in rec['log'] if e['type'] == 'sell'}
check('slipping back from +4% to +2%: sold to keep the gain, not held to the time limit', sales.get(a['label'], {}).get('kind') == 'trail' and 'Was up +4.0% at its best and has slipped back to +2.0%: sold to keep part of the gain' in sales[a['label']]['text'], sales.get(a['label']))
check('slipping back from +17% to +12%: sold there, not at half', sales.get(b['label'], {}).get('kind') == 'trail' and 'Was up +17.0% at its best and has slipped back to +12.0%' in sales[b['label']]['text'] and any('Its path since buying, at each check-in: 0.5h +17.0%, 1h +12.0%.' == d for d in sales[b['label']]['detail']), sales.get(b['label']))
rec = m.load_item(U); rec['state']['open'][c['id']]['peak'] = 4.0; m.save_item(U, rec); PRICES[c['symbol']] = c['buyPrice'] * 0.992
s, rec = run(t0 + 3 * half); gone = {e['symbol']: e for e in rec['log'] if e['type'] == 'sell'}.get(c['label'], {})
check('a holding that had been up and is under its buying price by the next check-in: the stop sells it, and does not call that keeping a gain', gone.get('kind') == 'trail' and 'Was up +4.0% at its best and had fallen to -0.8% by this check-in: sold by the stop that followed it. The gain was gone before it could act, because it only sees prices at check-ins' in gone.get('text', '') and 'keep part of the gain' not in gone.get('text', ''), gone)
check('the plan under a sale names the protection that applied', any('Rising is not a reason to sell it: while it keeps going up it is kept. Once it has been up 1%, a stop starts following it up, and it is sold only if it then falls back too far from its best.' in d for d in sales[a['label']]['detail']), sales[a['label']]['detail'])
D.t.clear(); PRICES.clear(); STRONG.clear(); MODEL['answer'] = None
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=0.5, maxHoldDays=20, screeners=['7-1']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
s, rec = run(t0); a = portfolio()['holdings'][0]; PRICES[a['symbol']] = a['buyPrice'] * 1.10
for i in range(1, 13): s, rec = run(t0 + i * half)
check('the larger model is asked at most 8 times a day', len(STRONG) == 8 and rec['state']['strong']['n'] == 8 and len([p for p in MODEL['prompts'] if 'Holdings:' in p['user']]) >= 12, (len(STRONG), rec['state'].get('strong')))
s, rec = run(t0 + dt.timedelta(days=1, minutes=30)); check('and again the next day', len(STRONG) == 9 and rec['state']['strong'] == {'day': m.iso(t0 + dt.timedelta(days=1))[:10], 'n': 1}, rec['state'].get('strong'))
D.t.clear(); PRICES.clear(); STRONG.clear()
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=0.5, maxHoldDays=20, screeners=['7-1']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
s, rec = run(t0); s, rec = run(t0 + half); check('with no gain at stake the usual model does the review', STRONG == [] and rec['state']['strong']['n'] == 0, (len(STRONG), rec['state'].get('strong')))
PRICES.clear(); MODEL['answer'] = None; MODEL['prompts'].clear(); SNAP['7-1'] = rows('crypto', '7-1'); D.t.clear()

# --- the pace follows the risk level unless the user sets it himself
tested = dict(m.DEFAULTS); m.DEFAULTS.clear(); m.DEFAULTS.update(REAL)                                    # the real defaults for this part
pace = lambda **k: {f: m.clean_settings(dict(k), U)[f] for f in ('periodDays', 'everyHours', 'maxHoldDays', 'auto')}
check('a new user leaves the pace to the level: Balanced builds up over 5 days, checks in every 6 hours, keeps a holding 5 days', pace() == {'periodDays': 5, 'everyHours': 6, 'maxHoldDays': 5, 'auto': ['periodDays', 'everyHours', 'maxHoldDays']} and m.clean_settings({}, U) == dict(REAL), pace())
check('moving the level moves all three', pace(risk=1, auto=['periodDays', 'everyHours', 'maxHoldDays']) == {'periodDays': 10, 'everyHours': 24, 'maxHoldDays': 20, 'auto': ['periodDays', 'everyHours', 'maxHoldDays']} and [pace(risk=r, auto=list(m.PACE_FIELDS))['everyHours'] for r in (1, 2, 3, 4, 5)] == [24, 12, 6, 3, 1] and [pace(risk=r, auto=list(m.PACE_FIELDS))['maxHoldDays'] for r in (1, 2, 3, 4, 5)] == [20, 10, 5, 2, 1] and [pace(risk=r, auto=list(m.PACE_FIELDS))['periodDays'] for r in (1, 2, 3, 4, 5)] == [10, 7, 5, 2, 1])
check('what the user sets himself stays put when the level moves; the rest still follows', pace(risk=5, periodDays=3, everyHours=0.5, maxHoldDays=0.25, auto=['maxHoldDays']) == {'periodDays': 3, 'everyHours': 0.5, 'maxHoldDays': 1, 'auto': ['maxHoldDays']} and pace(risk=5, periodDays=3, everyHours=0.5, maxHoldDays=0.25, auto=[]) == {'periodDays': 3, 'everyHours': 0.5, 'maxHoldDays': 0.25, 'auto': []})
check('settings saved before this existed keep what was chosen by hand', pace(risk=3, periodDays=1, everyHours=0.5, maxHoldDays=0.25) == {'periodDays': 1, 'everyHours': 0.5, 'maxHoldDays': 0.25, 'auto': []} and pace(risk=3, periodDays=1, everyHours=0.5, maxHoldDays=0.25, auto='everything') == {'periodDays': 1, 'everyHours': 0.5, 'maxHoldDays': 0.25, 'auto': []} and pace(risk=3, auto=['periodDays', 'budgetUsd', 7])['auto'] == ['periodDays'])
check('every level\'s pace is one the dashboard offers', all(v['everyHours'] in m.EVERY_HOURS and any(abs(v['maxHoldDays'] - d) < 1e-9 for d in m.HOLD_DAYS) and 1 <= v['periodDays'] <= 90 for v in m.PACE.values()))
D.t.clear(); code_, b = call(action='get', userId=U)
check('the dashboard is sent each level\'s pace and which settings are left to it', b['options']['pace']['4'] == {'periodDays': 2, 'everyHours': 3, 'maxHoldDays': 2} and b['settings']['auto'] == ['periodDays', 'everyHours', 'maxHoldDays'] and b['settings']['maxHoldDays'] == 5)
code_, b = call(action='save', userId=U, settings=dict(b['settings'], enabled=True, risk=5, screeners=['7-1']))
check('switching on at Adventurous with the pace left to the level: a day to build up, hourly check-ins, a day at most', (b['settings']['periodDays'], b['settings']['everyHours'], b['settings']['maxHoldDays']) == (1, 1, 1) and 'Autopilot on: Adventurous level, $10,000 over 1 day, checking every hour.' in b['log'][-1]['text'], b['log'][-1]['text'])
m.DEFAULTS.clear(); m.DEFAULTS.update(tested); D.t.clear()

# --- the stop that follows a rising holding is set from that holding's own movement and its figures, not from fixed numbers
bar = lambda h, l, c: (h, l, c); days14 = [(100.0, 100.0, 100.0)] + [(103.0, 97.0, 100.0)] * 14
chart = {'indicators': {'quote': [{'high': [d[0] for d in days14] + [None], 'low': [d[1] for d in days14] + [None], 'close': [d[2] for d in days14] + [None]}]}}
check('how much a holding normally moves in a day comes from its own daily highs and lows', m.daily_range(chart) == 6.0 and m.daily_range({'indicators': {'quote': [{'high': [1, 2], 'low': [1, 1], 'close': [1, 2]}]}}) is None and m.daily_range({}) is None, m.daily_range(chart))
check('and is scaled to the gap between check-ins', near(m.typical_move(6.3, 0.5), 0.91) and near(m.typical_move(6.3, 6), 3.15) and near(m.typical_move(6.3, 24), 6.3) and near(m.typical_move(1.9, 24), 1.9))
B3 = m.RISK[3]; bought = {'score': 4.0, 'rank': 2}; row = lambda **k: dict({'score': 4.0, 'rank': 2, 'rsi': 55}, **k)
room = lambda facts, r, held=1, hold=20: m.stop_room(B3, facts, r, held, hold)[0]
check('room to slip: 2.5 typical moves as a rule, more while the figures hold up, less when they weaken, look stretched, time is short, or the review asked', [room(None, None), room(bought, row()), room(bought, row(score=3.9, rank=3)), room(bought, row(score=2.0)), room(bought, row(rank=30)), room(bought, row(rsi=85)), room(bought, row(), 16), room(dict(bought, tight=True), row()), room(dict(bought, tight=True), row(score=1.0, rsi=90), 19)] == [2.5, 3.0, 2.5, 1.75, 1.75, 2.5, 2.5, 2.0, 1.0], [room(None, None), room(bought, row()), room(bought, row(score=3.9, rank=3)), room(bought, row(score=2.0)), room(bought, row(rank=30)), room(bought, row(rsi=85)), room(bought, row(), 16), room(dict(bought, tight=True), row()), room(dict(bought, tight=True), row(score=1.0, rsi=90), 19)])
check('and it says why', 'as strong as when it was bought, so it gets more room' in m.stop_room(B3, bought, row(), 1, 20)[1][0] and 'has weakened since it was bought (score +2.0 from +4.0' in m.stop_room(B3, bought, row(score=2.0), 1, 20)[1][0] and 'RSI 85 says the rise is stretched' in ' '.join(m.stop_room(B3, bought, row(rsi=85), 1, 20)[1]) and 'little of its holding time is left' in ' '.join(m.stop_room(B3, bought, row(), 16, 20)[1]))
quick = dict(m.DEFAULTS, risk=3, everyHours=0.5, maxHoldDays=0.25); daily = dict(m.DEFAULTS, risk=3, everyHours=24, maxHoldDays=20)
wild = m.follow_stop(B3, None, None, 6.15, 6.3, quick, 0.02); calm = m.follow_stop(B3, None, None, 6.15, 2.4, quick, 0.02)
check('a wild coin gets a wider stop than a calm one (up 6.15%: sold at about +3.9% against +5.3%), and its protection starts later', wild['arm'] == 1.4 and near(wild['floor'], 3.88) and near(wild['move'], 0.91) and calm['arm'] == 1.0 and near(calm['floor'], 5.3) and m.follow_stop(B3, None, None, 1.2, 6.3, quick, 0.02)['floor'] is None, (wild, calm))
check('weaker figures pull the stop closer; stronger ones give it room', near(m.follow_stop(B3, bought, row(score=2.0), 6.15, 6.3, quick, 0.02)['floor'], 4.56) and near(m.follow_stop(B3, bought, row(), 6.15, 6.3, quick, 0.02)['floor'], 3.42))
check('a share checked once a day is judged against a whole day of its movement', near(m.follow_stop(B3, None, None, 8.0, 1.9, daily, 3)['floor'], 3.25) and m.follow_stop(B3, None, None, 2.0, 1.9, daily, 3)['floor'] is None)
check('it always keeps at least a fifth of the best gain', near(m.follow_stop(B3, None, None, 5.0, 3.2, dict(quick, everyHours=24), 0.02)['floor'], 1.0))
check('with no daily prices for a holding the simpler rule by holding time is used', m.follow_stop(B3, None, None, 4.0, None, quick, 0.02) == {'arm': 1.0, 'floor': m.gain_floor(B3, 0.25, 4.0), 'move': None, 'room': None, 'why': [], 'mode': 'gains'})
D.t.clear(); PRICES.clear(); NEWS.clear(); STRONG.clear(); ATR.clear(); MODEL['answer'] = None; MODEL['prompts'].clear(); SNAP['7-1'] = rows('crypto', '7-1')
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=24, maxHoldDays=0.25, screeners=['7-1']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
s, rec = run(t0); a, b, c = portfolio()['holdings'][:3]; half = dt.timedelta(minutes=30); ATR.update({a['symbol']: 6.3, b['symbol']: 6.3, c['symbol']: 6.3})
rec = m.load_item(U); rec['settings']['everyHours'] = 0.5; m.save_item(U, rec)
PRICES[a['symbol']] = a['buyPrice'] * 1.06; PRICES[b['symbol']] = b['buyPrice'] * 1.06; PRICES[c['symbol']] = c['buyPrice'] * 1.06
MODEL['answer'] = {'decisions': [{'symbol': c['label'], 'action': 'tighten', 'reason': 'Up 6% but volume is fading'}]}
s, rec = run(t0 + half); ask = [p for p in MODEL['prompts'] if 'Holdings:' in p['user']][-1]; op = rec['state']['open']
check('the review is told how much each holding normally moves and how far it may slip', 'protected: sold if it slips back to +3.3%; it normally moves about 0.9% between check-ins and may slip 3 such moves from its best' in ask['user'] and 'ordinary wobble' in ask['system'] and '"tighten"' in ask['system'], ask['user'][:700])
check('the review may keep a holding but ask for a closer stop', s['sold'] == 0 and op[c['id']]['view']['tighten'] is True and op[c['id']]['tight'] is True and 'tight' not in op[a['id']], op[c['id']].get('view'))
SNAP['7-1'] = [dict(r, score=r['score'] * 0.5) if r['symbol'] == b['symbol'] else r for r in rows('crypto', '7-1')]; MODEL['answer'] = None
for sym in (a, b, c): PRICES[sym['symbol']] = sym['buyPrice'] * (1.041 if sym is c else 1.042)        # the tightened one's stop is at +4.18%
s, rec = run(t0 + 2 * half); held = [h['id'] for h in portfolio()['holdings']]; sales = {e['symbol']: e for e in rec['log'] if e['type'] == 'sell'}
check('slipping from +6% to about +4.2%: the one with strong figures is kept, the one whose score halved and the one the review tightened are sold', a['id'] in held and b['id'] not in held and c['id'] not in held and sales[b['label']]['kind'] == 'trail' and sales[c['label']]['kind'] == 'trail', (a['id'] in held, list(sales)))
check('the sale says how its stop was set', any('The stop that followed it: it normally moves about 0.9% between check-ins, and it was allowed to slip 1.75 such moves from its best: its score or rank has weakened since it was bought' in d for d in sales[b['label']]['detail']) and any("the AI model's review asked for a tighter stop" in d for d in sales[c['label']]['detail']), sales[b['label']]['detail'])
s2, body = call(action='get', userId=U); plan = [pl for pl in body['plans'] if pl['id'] == a['id']][0]
check('the dashboard gets each holding\'s stop as worked out at the last check-in', plan['arm'] == 1.4 and near(plan['floor'], 3.3) and near(plan['move'], 0.91) and plan['room'] == 3.0 and plan['tight'] is False, plan)
PRICES[a['symbol']] = a['buyPrice'] * 1.03; s, rec = run(t0 + 3 * half)
check('and the strong one is sold too once it slips past its own, wider stop', a['id'] not in [h['id'] for h in portfolio()['holdings']] and 'Was up +6.0% at its best and has slipped back to +3.0%' in [e for e in rec['log'] if e['type'] == 'sell'][-1]['text'])
PRICES.clear(); ATR.clear(); MODEL['answer'] = None; MODEL['prompts'].clear(); SNAP['7-1'] = rows('crypto', '7-1'); D.t.clear()

# --- a holding whose screener has since been un-ticked is still looked after (it was once left unattended)
D.t.clear(); PRICES.clear(); MODEL['answer'] = None; SNAP['7-1'] = rows('crypto', '7-1'); sat = dt.datetime(2026, 10, 10, 15, 40, 4)      # a Saturday: only coins trade
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=1, maxHoldDays=0.25, screeners=['7-1']); rec['state']['startedAt'] = m.iso(sat); m.save_item(U, rec)
s, rec = run(sat); coin = portfolio()['holdings'][0]
rec = m.load_item(U); rec['settings']['screeners'] = ['5-nikkei225']; m.save_item(U, rec); rec = m.load_item(U)
check('the coin market still counts as its own while it holds a coin, though only a share screener is ticked', m.its_markets(rec) == {'jp', 'crypto'} and m.due_markets(rec, sat + dt.timedelta(hours=1)) == ['crypto'] and m.next_check(rec, sat + dt.timedelta(minutes=5))['markets'] == ['coin'], (m.its_markets(rec), m.due_markets(rec, sat + dt.timedelta(hours=1))))
m.fetch_snapshot, m.fetch_quote, m.ask_model = snapshot, quote, model
class Later(dt.datetime):
    @classmethod
    def utcnow(cls): return sat + dt.timedelta(hours=7)
real_datetime = m.datetime; m.datetime = Later
r = json.loads(m.lambda_handler({'source': 'aws.events'}, None)['body']); m.datetime = real_datetime; rec = m.load_item(U)
check('so the schedule still checks in for it and sells it when its time is up', r['ran'] and r['ran'][0]['sold'] == 1 and coin['id'] not in [h['id'] for h in portfolio()['holdings']] and 'the longest this autopilot keeps a holding' in [e for e in rec['log'] if e['type'] == 'sell'][-1]['text'] and m.its_markets(rec) == {'jp'}, (r, [e['text'][:80] for e in rec['log'][-2:]]))
PRICES.clear(); SNAP['7-1'] = rows('crypto', '7-1'); D.t.clear()

# --- a coin is bought only once it has stayed near the top; results after a typical trading cost; coins rested on their own results
m.STAY_CHECKS = STAY                                                                                       # the real wait for this part
C = lambda sym: {'symbol': sym, 'kind': 'crypto'}; st = {}; half = dt.timedelta(minutes=30)
check('how long a candidate has stayed on the shortlist is counted check-in by check-in', m.note_stays(st, [C('A'), C('B')], t0, 0.5) == {'A': 1, 'B': 1} and m.note_stays(st, [C('A'), C('B'), C('N')], t0 + half, 0.5) == {'A': 2, 'B': 2, 'N': 1} and m.note_stays(st, [C('A'), C('N')], t0 + 2 * half, 0.5) == {'A': 3, 'N': 2} and m.note_stays(st, [C('A'), C('B')], t0 + 3 * half, 0.5) == {'A': 4, 'B': 1}, st)
check('a second look a few minutes later does not count as another check-in; a long gap starts the count again', m.note_stays(st, [C('A')], t0 + 3 * half + dt.timedelta(minutes=5), 0.5) == {'A': 4} and m.note_stays(st, [C('A')], t0 + 4 * half, 0.5) == {'A': 5} and m.note_stays(st, [C('A')], t0 + 4 * half + dt.timedelta(hours=3), 0.5) == {'A': 1}, st)
D.t.clear(); PRICES.clear(); ATR.clear(); MODEL['answer'] = None; MODEL['prompts'].clear(); SNAP['7-1'] = rows('crypto', '7-1'); SNAP['3-100'] = rows()
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=0.5, maxHoldDays=1, screeners=['7-1']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
s, rec = run(t0)
check('checking in every 30 minutes: at the first check-in every coin is new to it, so it waits and says why', s['bought'] == 0 and portfolio() is None and rec['log'][-1]['key'] == 'stay' and 'Waiting to see which coins stay near the top: the 10 on its shortlist are new to it. It buys a coin once it has been there at 2 check-ins running' in rec['log'][-1]['text'] and len(buy_prompts()) == 0, rec['log'][-1])
SNAP['7-1'] = [r for r in rows('crypto', '7-1') if r['symbol'] != 'C00-USD'] + [dict(rows('crypto', '7-1')[0], symbol='NEW-USD', label='NEW-USD', score=9.0)]
SNAP['7-1'] = sorted(SNAP['7-1'], key=lambda r: -r['score']); [r.update(rank=i + 1) for i, r in enumerate(SNAP['7-1'])]
s, rec = run(t0 + half); bought = [h['symbol'] for h in portfolio()['holdings']]; ask = buy_prompts()[-1]['user']
check('at the next check-in it buys from those that stayed, and passes over a newcomer even at rank 1', s['bought'] == 1 and bought == ['C01-USD'] and 'NEW-USD' not in ask and 'C01-USD | Crypto (top coins) rank 2 |' in ask and '| on the shortlist at 2 check-ins running' in ask and rec['state']['open'][portfolio()['holdings'][0]['id']]['stay'] == 2, (bought, ask[-400:]))
D.t.clear(); MODEL['prompts'].clear(); SNAP['7-1'] = rows('crypto', '7-1')
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=24, maxHoldDays=20, screeners=['3-100', '7-1']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
s, rec = run(t0); kinds = {h['symbol'].endswith('-USD') for h in portfolio()['holdings']}
check('checking in once a day there is no wait (a day is too long to wait), and shares are never held back', s['bought'] == 3 and '| new to the shortlist' in buy_prompts()[-1]['user'], (s, kinds))
rec = m.load_item(U); rec['settings'].update(everyHours=0.5, screeners=['3-100']); m.save_item(U, rec)
D.t.clear(); rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=0.5, maxHoldDays=20, screeners=['3-100']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
s, rec = run(t0); check('a share screener checked every 30 minutes buys at once', s['bought'] == 1 and not portfolio()['holdings'][0]['symbol'].endswith('-USD'), s)
H = lambda stay, pct: dict(risk=3, pct=pct, stay=stay, rank=2, rsi=50, exit='time', screener='7-1', label='X', sold=m.iso(t0), usd=pct * 10, cost=1000.0)
card = m.scorecard([H(1, -1.0)] * 3 + [H(3, 2.0)] * 4 + [H(8, 3.0)] * 2 + [dict(H(None, 0.0))])
check('the record shows how buys did by how long they had stayed near the top', [(g['label'], g['n'], g['avg']) for g in card['groups']['stay']] == [('new to the shortlist', 3, -1.0), ('there 2 to 4 check-ins', 4, 2.0), ('there 5 check-ins or more', 2, 3.0), ('not recorded', 1, 0.0)], card['groups']['stay'])
mf = m.month_figures([dict(usd=50.0, cost=1000.0, sold=m.iso(t0 - dt.timedelta(days=1))), dict(usd=-20.0, cost=2000.0, sold=m.iso(t0 - dt.timedelta(days=2)))], 10000.0, t0)['last30']
check('results after a typical trading cost of 0.1% on each buy and each sell: $30.00 becomes $23.97', mf['usd'] == 30.0 and mf['afterCosts'] == 23.97 and m.public({'settings': dict(m.DEFAULTS), 'state': {}, 'log': [], 'history': []}, t0)['costEachWay'] == m.TRADE_COST, mf)
coin = lambda pct, vs: dict(risk=3, pct=pct, vs=vs, screener='7-1', label='X', sold=m.iso(t0 + dt.timedelta(hours=1)), exit='time')
r1 = {'settings': dict(m.DEFAULTS, screeners=['7-1']), 'state': {}, 'log': [], 'history': [coin(-2.0, 3.0)] * 8}
r2 = {'settings': dict(m.DEFAULTS, screeners=['7-1']), 'state': {}, 'log': [], 'history': [coin(2.0, -3.0)] * 8}
check('a coin screener is rested on its own results, not on how the share market did', 'Resting the Crypto (top coins) screener for 14 days: its last 8 trades averaged -2.0%.' in m.review_resting(r1, t0 + dt.timedelta(hours=2))[0]['text'] and m.review_resting(r2, t0 + dt.timedelta(hours=2)) == [], (r1['state'], r2['state']))
m.STAY_CHECKS = 1; PRICES.clear(); MODEL['prompts'].clear(); SNAP['7-1'] = rows('crypto', '7-1'); SNAP['3-100'] = rows(); D.t.clear()

# --- the kind of following stop is the user's choice: protect a gain (as before), a full trailing stop loss, or none
B3 = m.RISK[3]; quick = dict(m.DEFAULTS, risk=3, everyHours=1, maxHoldDays=1); mode = lambda k: dict(quick, trailMode=k)
check('the choice is one of three, and "protects a gain" unless chosen otherwise', [m.clean_settings({'trailMode': k}, U)['trailMode'] for k in ('gains', 'full', 'off', 'sideways', None)] == ['gains', 'full', 'off', 'gains', 'gains'])
g, f, o = (m.follow_stop(B3, None, None, 0.5, 6.3, mode(k), 0.1) for k in ('gains', 'full', 'off'))
check('before a holding has risen: "protects a gain" sets no stop, the full trailing stop already sits under the price, "off" sets none', g['floor'] is None and near(f['floor'], 0.5 - 2.5 * f['move']) and f['floor'] < 0 and near(f['move'], 1.29) and o == {'arm': None, 'floor': None, 'move': None, 'room': None, 'why': [], 'mode': 'off'}, (g, f, o))
check('once it has risen beyond its wobble both kinds give the same stop, with part of the gain always kept', near(m.follow_stop(B3, None, None, 6.0, 6.3, mode('gains'), 0.1)['floor'], m.follow_stop(B3, None, None, 6.0, 6.3, mode('full'), 0.1)['floor']) and m.follow_stop(B3, None, None, 6.0, 6.3, mode('full'), 0.1)['floor'] > 0)
check('a holding that only fell: the full stop starts from the buying price', near(m.follow_stop(B3, None, None, -1.0, 6.3, mode('full'), 0.1)['floor'], -2.5 * 1.286))
def held(kind):
    D.t.clear(); PRICES.clear(); ATR.clear(); MODEL['answer'] = None
    rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=1, maxHoldDays=1, screeners=['7-1'], trailMode=kind); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
    s, rec = run(t0); a = portfolio()['holdings'][0]; ATR[a['symbol']] = 6.3; PRICES[a['symbol']] = a['buyPrice'] * 0.96
    s, rec = run(t0 + dt.timedelta(hours=1)); return a, s, rec
a, s, rec = held('gains'); check('down 4% an hour after buying, "protects a gain": kept (the loss limit is -10%)', a['id'] in [h['id'] for h in portfolio()['holdings']] and s['sold'] == 0)
a, s, rec = held('full'); sale = [e for e in rec['log'] if e['type'] == 'sell'][-1]
check('the same with the full trailing stop: cut early, and it says so', a['id'] not in [h['id'] for h in portfolio()['holdings']] and sale['kind'] == 'cut' and 'Its trailing stop was hit: -4.0% since it was bought (its best was +0.0%; the stop trailed 3 of its typical moves of about 1.3% below that)' in sale['text'] and any('A trailing stop sits under its price from the moment it was bought and follows it up: it is sold if it falls back about 3.9 points from its best.' in d for d in sale['detail']), sale)
check('such a sale is its own kind in the record', rec['history'][-1]['exit'] == 'cut' and m.scorecard(rec['history'])['groups']['exit'][0]['label'] == 'sold by its trailing stop before it had risen')
a, s, rec = held('off'); PRICES[a['symbol']] = a['buyPrice'] * 1.08; s, rec = run(t0 + dt.timedelta(hours=2)); PRICES[a['symbol']] = a['buyPrice'] * 1.01; s, rec = run(t0 + dt.timedelta(hours=3))
code_, body = call(action='get', userId=U); plan = [pl for pl in body['plans'] if pl['id'] == a['id']]
check('with it switched off nothing follows the price: up 8% then back to +1% is kept, and the dashboard is told there is no stop', len(plan) == 1 and plan[0]['arm'] is None and plan[0]['floor'] is None and plan[0]['mode'] == 'off' and body['rules']['trailMode'] == 'off' and s['sold'] == 0, plan)
check('a buy says which kind applies to it', any('No stop follows it (switched off).' in d for e in rec['log'] if e['type'] == 'buy' for d in e.get('detail', [])))
PRICES.clear(); ATR.clear(); D.t.clear()

# --- "Check in now" is a request to act: it releases the next part of the budget early, and says why if nothing can be done
D.t.clear(); PRICES.clear(); ATR.clear(); MODEL['answer'] = None; SNAP['3-100'] = rows(n=30, **{f'S{i:02d}': {'signal': 'BUY', 'rsi': 50, 'd30': 5.0} for i in range(30)})
m.fetch_snapshot, m.fetch_quote, m.ask_model = snapshot, quote, model; m.get_snapshot = lambda key, now=None: snapshot(key)
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=4, everyHours=24, maxHoldDays=20, screeners=['3-100']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
s, rec = run(t0); n0 = len(portfolio()['holdings'])
s, rec = run(t0 + dt.timedelta(hours=1)); check('a scheduled check-in an hour later keeps to the pace: nothing more', s['bought'] == 0 and rec['log'][-1]['key'] == 'pace' and s['why'].startswith('Nothing to spend yet') and len(portfolio()['holdings']) == n0 == 2, (n0, s.get('why')))
rec = m.load_item(U); s = m.run_user(U, rec, t0 + dt.timedelta(hours=2), snapshot=snapshot, quote=quote, model=model, manual=True, mail=lambda a, b: None, headlines=lambda h, n: []); m.save_item(U, rec)
check('"Check in now" at the same point releases the next part of the budget and buys', s['bought'] == 2 and len(portfolio()['holdings']) == 4 and rec['state']['ahead'] == 1 and any('You pressed "Check in now", so the next part of the budget was released ahead of its time.' == e['text'] for e in rec['log']), (s['bought'], rec['state'].get('ahead')))
s, rec = run(t0 + dt.timedelta(hours=3)); check('the schedule then carries on from there, not faster', s['bought'] == 0 and 'the next $1,000 in about' in rec['log'][-1]['text'], rec['log'][-1]['text'])
for i in range(4):
    rec = m.load_item(U); s = m.run_user(U, rec, t0 + dt.timedelta(hours=4 + i), snapshot=snapshot, quote=quote, model=model, manual=True, mail=lambda a, b: None, headlines=lambda h, n: []); m.save_item(U, rec)
check('pressing it again and again stops at the budget: 8 holdings, $8,000, and then it says the budget is fully invested', len(portfolio()['holdings']) == 8 and abs(sum(h['costUsd'] for h in portfolio()['holdings']) - 8000) < 0.01 and s['bought'] == 0 and 'fully invested in 8 holdings' in s['why'], (len(portfolio()['holdings']), s.get('why')))
code_, b = call(action='save', userId=U, settings=dict(m.load_item(U)['settings'], budgetUsd=9000.0))
check('changing the budget starts the build-up afresh', m.load_item(U)['state']['ahead'] == 0)
class Soon(dt.datetime):
    @classmethod
    def utcnow(cls): return t0 + dt.timedelta(days=3)
real_datetime = m.datetime; m.datetime = Soon; code_, b = call(action='run', userId=U); m.datetime = real_datetime
check('the page that pressed the button is told why when nothing was done', code_ == 200 and 'why' in b['summary'] and (b['summary']['bought'] > 0 or b['summary']['why']), b.get('summary'))
PRICES.clear(); SNAP['3-100'] = rows(); D.t.clear()

# --- the plan is put in words nobody can misread; switching what it buys from; an early release that buys nothing is taken back
check('the plan in words: the point where the stop starts is not a selling price', m.stop_words('gains', 4.5, 3.9) == 'Rising is not a reason to sell it: while it keeps going up it is kept. Once it has been up 4.5%, a stop starts following it up, and it is sold only if it then falls back about 3.9 points from its best.' and m.stop_words('full', 1.9, 3.9).startswith('A trailing stop sits under its price from the moment it was bought') and m.stop_words('off', None) == 'No stop follows it (switched off).')
D.t.clear(); PRICES.clear(); ATR.clear(); MODEL['answer'] = None; SNAP['7-1'] = rows('crypto', '7-1'); SNAP['3-100'] = rows()
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=24, maxHoldDays=5, screeners=['7-1']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
s, rec = run(t0); coins = [h['id'] for h in portfolio()['holdings']]; ATR.update({h['symbol']: 6.3 for h in portfolio()['holdings']})
plan = [d for e in rec['log'] if e['type'] == 'buy' for d in e['detail']][0]
rec = m.load_item(U); rec['settings']['screeners'] = ['3-100']; m.save_item(U, rec)                       # the owner switches from coins to the S&P 100
s, rec = run(t0 + dt.timedelta(days=1)); held = portfolio()['holdings']; new = [h for h in held if h['id'] not in coins]
check('switched from the coin screener to a share screener: the coins it holds stay and are still its own', len([h for h in held if h['id'] in coins]) == 3 and all(h['symbol'].endswith('-USD') for h in held if h['id'] in coins) and m.its_markets(rec) == {'crypto', 'us'})
check('new buys come only from the screener now ticked, with what is left of the budget', s['bought'] == 3 and all(not h['symbol'].endswith('-USD') and h['screener'] == '3-100' for h in new) and abs(sum(h['costUsd'] for h in held) - 6000) < 0.01, [(h['symbol'], h['costUsd']) for h in held])
first = [h for h in held if h['id'] in coins][0]; PRICES[first['symbol']] = first['buyPrice'] * 0.89
s, rec = run(t0 + dt.timedelta(days=2)); sale = [e for e in rec['log'] if e['type'] == 'sell'][-1]
check('a coin from the screener no longer ticked is still sold by its rules (here the loss limit)', first['id'] not in [h['id'] for h in portfolio()['holdings']] and sale['symbol'] == first['label'] and 'past the -10% limit' in sale['text'], sale['text'])
SNAP['7-1'] = [dict(r, score=-1.0, signal='SELL') for r in rows('crypto', '7-1')]
s, rec = run(t0 + dt.timedelta(days=3)); left = [h for h in portfolio()['holdings'] if h['symbol'].endswith('-USD')]
check('and it still reads that screener for them: when their signal turns negative they are sold', left == [] and s['sold'] == 2, [h['symbol'] for h in left])
check('once nothing is left from the coin screener, the coin market is no longer its concern', m.its_markets(rec) == {'us'})
SNAP['7-1'] = rows('crypto', '7-1'); SNAP['3-100'] = [dict(r, signal='HOLD') for r in rows()]                # nothing on the shortlist can be bought
D.t.clear(); rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=4, everyHours=24, maxHoldDays=20, screeners=['3-100']); rec['state'].update(startedAt=m.iso(t0)); m.save_item(U, rec)
D.Table(m.PORTFOLIO_TABLE).rows[U] = {'userId': U, 'data': json.dumps(dict(m.new_portfolio(t0), holdings=[{'id': 'a1', 'symbol': 'S20', 'label': 'S20', 'currency': 'USD', 'qty': 20.0, 'buyPrice': 100.0, 'buyFx': 1, 'costUsd': 2000.0, 'boughtAt': m.iso(t0), 'spyAtBuy': 700.0, 'by': 'ai', 'screener': '3-100'}], cash=98000.0)), 'version': 1}
SNAP['3-100'] = [dict(r, signal='HOLD') for r in rows()]; PRICES['S20'] = 100.0
rec = m.load_item(U); s = m.run_user(U, rec, t0 + dt.timedelta(hours=2), snapshot=snapshot, quote=quote, model=model, manual=True, mail=lambda a, b: None, headlines=lambda h, n: [])
check('"Check in now" with nothing fit to buy: the budget released early is taken back, and it says why', s['bought'] == 0 and not rec['state'].get('ahead') and 'Nothing on the shortlist passed' in (s.get('why') or ''), (s.get('why'), rec['state'].get('ahead')))
PRICES.clear(); ATR.clear(); SNAP['3-100'] = rows(); SNAP['7-1'] = rows('crypto', '7-1'); D.t.clear()

# --- trading hours: also by hand, nothing is bought or sold in a market that is closed (its last price is not one to trade at)
sat, thu = dt.datetime(2026, 10, 10, 16, 20, 0), dt.datetime(2026, 10, 15, 15, 0, 0)                          # a Saturday; a Thursday with the US market open
check('how long until a market opens', m.opens_in('crypto', sat) == 0 and m.opens_in('us', thu) == 0 and abs(m.opens_in('jp', sat) - (31 + 45 / 60)) < 0.1 and abs(m.opens_in('us', sat) - (46 + 15 / 60)) < 0.1, (m.opens_in('jp', sat), m.opens_in('us', sat)))
def at(when):
    class Then(dt.datetime):
        @classmethod
        def utcnow(cls): return when
    return Then
D.t.clear(); PRICES.clear(); ATR.clear(); MODEL['answer'] = None; SNAP['3-100'] = rows(); SNAP['7-1'] = rows('crypto', '7-1'); SNAP['5-nikkei225'] = [dict(r, symbol=f'{4300 + i}.T', label=f'{4300 + i}.T', screener='5-nikkei225') for i, r in enumerate(rows())]
m.fetch_snapshot, m.fetch_quote, m.ask_model = snapshot, quote, model; m.get_snapshot = lambda key, now=None: snapshot(key); clock = m.datetime
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=24, maxHoldDays=20, screeners=['5-nikkei225']); rec['state']['startedAt'] = m.iso(sat); m.save_item(U, rec)
m.datetime = at(sat); code_, b = call(action='run', userId=U); m.datetime = clock
check('"Check in now" on a Saturday with only a Japanese screener: nothing is bought, and it says the market is closed and when it opens', code_ == 200 and b['summary']['bought'] == 0 and portfolio() is None and 'none of its markets is open' in b['summary']['why'] and 'The Japanese market is closed, so nothing is bought or sold there now (it opens in about 1 day).' in b['summary']['why'], b.get('summary'))
rec = m.load_item(U); rec['settings']['screeners'] = ['5-nikkei225', '7-1']; rec['state']['lastRun'] = None; m.save_item(U, rec)
m.datetime = at(sat + dt.timedelta(minutes=20)); code_, b = call(action='run', userId=U); m.datetime = clock; held = portfolio()['holdings']
check('with a coin screener ticked as well: coins are bought (they trade at any time), no Japanese share', b['summary']['bought'] >= 1 and all(h['symbol'].endswith('-USD') for h in held) and any('The Japanese market is closed' in e['text'] for e in b['log']), [h['symbol'] for h in held])
D.Table(m.PORTFOLIO_TABLE).rows[U]['data'] = json.dumps(dict(portfolio(), holdings=portfolio()['holdings'] + [{'id': 'jp1', 'symbol': '4300.T', 'label': '4300.T', 'currency': 'USD', 'qty': 10.0, 'buyPrice': 100.0, 'buyFx': 1, 'costUsd': 1000.0, 'boughtAt': m.iso(sat), 'spyAtBuy': 700.0, 'by': 'ai', 'screener': '5-nikkei225'}]))
PRICES['4300.T'] = 50.0; rec = m.load_item(U); rec['state']['lastRun'] = None; m.save_item(U, rec)
m.datetime = at(sat + dt.timedelta(minutes=40)); code_, b = call(action='run', userId=U); m.datetime = clock
check('a Japanese share it holds is left alone while Tokyo is closed, even far past its loss limit', 'jp1' in [h['id'] for h in portfolio()['holdings']] and b['summary']['sold'] == 0)
m.datetime = at(sat + dt.timedelta(minutes=50)); code_, b = call(action='sellall', userId=U); m.datetime = clock; left = [h['id'] for h in portfolio()['holdings'] if h.get('by') == 'ai']
check('"Sell everything it holds" on a Saturday sells the coins and keeps the Japanese share, and says so', left == ['jp1'] and b['summary']['closed'] == ['4300.T'] and b['summary']['sold'] >= 1, (left, b.get('summary')))
check('a time that falls while a market is closed is moved on to its next opening; an open market or a coin keeps the time', m.when_open('jp', dt.datetime(2026, 10, 30, 16, 20)) == dt.datetime(2026, 11, 2, 0, 5) and m.when_open('us', thu) == thu and m.when_open('crypto', sat) == sat and m.when_open('us', sat) == dt.datetime(2026, 10, 12, 14, 35), m.when_open('jp', dt.datetime(2026, 10, 30, 16, 20)))
pl = [x for x in m.public(m.load_item(U), sat + dt.timedelta(hours=1), U)['plans'] if x['id'] == 'jp1'][0]
check('the dashboard is told a share is sold at the latest when its market next opens after its holding time (20 days from a Saturday: the Monday after), that its market is closed now, and when it opens', pl['sellBy'] == '2026-11-02T00:05:00Z' and pl['market'] == 'Japanese' and pl['closed'] is True and pl['opens'] == '2026-10-12T00:05:00Z' and [x for x in m.public(m.load_item(U), sat + dt.timedelta(hours=1, minutes=3, seconds=35), U)['plans'] if x['id'] == 'jp1'][0]['opens'] == '2026-10-12T00:05:00Z', pl)
pl = [x for x in m.public(m.load_item(U), dt.datetime(2026, 10, 13, 1, 0), U)['plans'] if x['id'] == 'jp1'][0]
check('and while Tokyo is open nothing is said about a closed market', pl['closed'] is False and pl['opens'] is None and pl['sellBy'] == '2026-11-02T00:05:00Z', pl)
D.Table(m.PORTFOLIO_TABLE).rows[U]['data'] = json.dumps(dict(portfolio(), holdings=portfolio()['holdings'] + [{'id': 'c1', 'symbol': 'S01-USD', 'label': 'S01-USD', 'currency': 'USD', 'qty': 10.0, 'buyPrice': 100.0, 'buyFx': 1, 'costUsd': 1000.0, 'boughtAt': m.iso(sat), 'spyAtBuy': 700.0, 'by': 'ai', 'screener': '7-1'}]))
pl = [x for x in m.public(m.load_item(U), sat + dt.timedelta(hours=1), U)['plans'] if x['id'] == 'c1'][0]
check('a coin is sold when its holding time ends, whatever the day: its market never closes', pl['sellBy'] == m.iso(sat + dt.timedelta(days=20)) and pl['market'] == 'coin' and pl['closed'] is False and pl['opens'] is None, pl)
m.datetime = at(sat + dt.timedelta(hours=2)); code_, b = call(action='save', userId=U, settings=dict(m.load_item(U)['settings'], budgetUsd=9000.0)); m.datetime = clock
check('the line written when settings are saved says "over 1 day", not "1 days"', any(e['text'] == 'Autopilot on: Balanced level, $9,000 over 1 day, checking every 24 hours.' for e in b['log']), [e['text'] for e in b['log'] if e['text'].startswith('Autopilot on')])
m.datetime = at(dt.datetime(2026, 10, 12, 0, 30, 0)); rec = m.load_item(U); rec['state']['lastRun'] = None; m.save_item(U, rec); code_, b = call(action='run', userId=U); m.datetime = clock
check('on Monday with Tokyo open it is dealt with', 'jp1' not in [h['id'] for h in portfolio()['holdings']] and b['summary']['sold'] >= 1, b.get('summary'))
PRICES.clear(); SNAP.pop('5-nikkei225', None); SNAP['3-100'] = rows(); SNAP['7-1'] = rows('crypto', '7-1'); D.t.clear()

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
check('a test run never sends a real email (and says "not attempted", which is not a failure)', m.send_mail('nobody@example.com', 'x', ['y']) is None)

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
check('clearly better with the change: it is kept, and the email says so with the numbers', good['state']['tune']['trial'] is None and m.rules_for(good['settings'], good['state'])['take'] == 9.0 and good['state']['tune']['past'][-1]['verdict'] == 'kept' and 'The change is kept: 10 trades with the change averaged +3.20%, 10 without it +0.05% (difference +3.15' in notes[0]['text'] and 'change kept' in MAILS[0][0] and any(l.startswith('Sells a holding if it falls to -10% or reaches +9%, or after ') and 'A holding that keeps rising is kept' in l and 'slips back far enough' not in l for l in MAILS[0][1]), (notes, MAILS[:1]))
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
check('the last 30 days and the 30 before, in dollars and as a share of the budget', month == {'last30': {'n': 2, 'up': 1, 'usd': 60.0, 'pct': 0.6, 'afterCosts': 59.94}, 'before30': {'n': 1, 'up': 1, 'usd': 25.0, 'pct': 0.25, 'afterCosts': 24.98}}, month)
PRICES.clear(); SNAP['3-100'] = rows(); SNAP['7-1'] = rows('crypto', '7-1'); D.t.clear()

# scheduled event end to end (with the stand-ins patched in)
m.fetch_snapshot, m.fetch_quote, m.ask_model = snapshot, quote, model
D.t.clear(); rec = m.load_item(U); rec['settings'].update(enabled=True, screeners=['7-1'], risk=4); rec['state']['startedAt'] = m.iso(dt.datetime.utcnow()); m.save_item(U, rec)
rec2 = m.load_item('stranger@y.com'); rec2['settings']['enabled'] = True; D.Table(m.SETTINGS_TABLE).put_item(Item={'userId': 'stranger@y.com', 'data': json.dumps(rec2), 'enabled': True})
r = json.loads(m.lambda_handler({'source': 'aws.events'}, None)['body'])
check('the schedule runs the due user and skips one not on the list', len(r['ran']) == 1 and r['ran'][0]['bought'] >= 1 and 'stranger@y.com' not in D.Table(m.PORTFOLIO_TABLE).rows, r)
check('"check in now" has a 10-minute gap', call(action='run', userId=U)[0] == 429)

# --- what happens next, what needs the user, and the email's status (for the dashboard's countdowns)
D.t.clear(); PRICES.clear(); MODEL['answer'] = None; SNAP['3-100'] = rows(); SNAP['7-1'] = rows('crypto', '7-1'); MAILS.clear()
sun = dt.datetime(2026, 10, 11, 2, 52, 0)                                                             # a Sunday: only coins trade
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=2, everyHours=6, maxHoldDays=5, screeners=['3-100', '7-1']); rec['state']['startedAt'] = m.iso(sun - dt.timedelta(hours=1)); m.save_item(U, rec)
m.datetime = at(sun); code_, b = call(action='run', userId=U); m.datetime = clock
check('(set-up) a Sunday check-in buys a coin and no share', b['summary']['bought'] == 1 and [h['symbol'][-4:] for h in portfolio()['holdings']] == ['-USD'], b.get('summary'))
later = sun + dt.timedelta(minutes=20); out = m.public(m.load_item(U), later, U); come = out['coming']; by = {c['kind']: c for c in come}
check('the dashboard is told what happens next, soonest first, then what goes by the number of trades', [c['kind'] for c in come] == ['check', 'release', 'open', 'sell', 'pause', 'review', 'notes'] and [c.get('at') for c in come[:5]] == sorted(c.get('at') for c in come[:5]) and all('at' not in c for c in come[5:]), [(c['kind'], c.get('at')) for c in come])
check('the next check-in: when, in which market, what it looks at and what it may buy', by['check']['at'] == '2026-10-11T09:10:00Z' == out['nextCheck']['at'] and by['check']['text'].startswith('Next check-in (coin market). It looks at the holding it has there (C0') and 'and sells it if it has hit its loss limit, gain mark, stop or time limit, or if the AI review wants it out.' in by['check']['text'] and 'It may buy up to 1 holding of about $1,000 from Crypto (top coins)' in by['check']['text'], by['check'])
check('more of the budget is listed at the check-in that can first spend it (released at 07:52, usable at the 09:10 check-in), with the amounts', by['release']['at'] == by['check']['at'] == '2026-10-11T09:10:00Z' and 'From this check-in more of the budget can be invested: $2,000 of the $8,000 ($1,000 until then; $1,000 is invested now).' in by['release']['text'], by['release'])
check('the first check-in after the share market opens, and what it can buy from there', by['open']['at'] == '2026-10-12T14:40:00Z' and by['open']['text'] == 'First check-in after the US market opens. It can buy from S&P 100 if part of the budget is free then.', by['open'])
check('the latest each holding is kept', by['sell']['at'] == out['plans'][0]['sellBy'] and by['sell']['text'].endswith('is sold at the latest: by then it has been kept 5 days, the longest allowed.'), by['sell'])
check('its own review goes by finished trades: how many more, and that it emails', by['review']['after'] == 20 and 'It reviews its own rules (0 of the 20 finished trades it waits for are in), may start a trial of one change beside the current rule, and emails you.' == by['review']['text'] and by['notes']['after'] == 5, come[4:])
check('the amount the forecast names is what the check-in then may spend', m.allowance(portfolio(), m.load_item(U)['settings'], m.load_item(U)['state'], dt.datetime(2026, 10, 11, 9, 10))[0] == 1000.0 and m.released(m.load_item(U)['settings'], m.load_item(U)['state'], later) == (1000.0, dt.datetime(2026, 10, 11, 7, 52)))
check('nothing needs the user, and no email has been tried yet', out['needs'] == [] and out['mail'] is None)
rec = m.load_item(U); rec['settings'].update(selfTune=False, emails=False); texts = [c['text'] for c in m.coming(rec, portfolio(), later, out['plans'])]
check('with its own trials switched off it says so instead of counting down to a review', any('It does not review or change its own rules' in x for x in texts) and not any('emails you' in x for x in texts))
rec = m.load_item(U); rec['settings'].update(screeners=['7-1'], risk=3); rec['settings']['budgetUsd'] = 1000.0
full = {c['kind']: c for c in m.coming(rec, portfolio(), later, out['plans'])}
check('a full budget: the next check-in says it buys nothing', 'It buys nothing: the $1,000 budget is fully invested.' in full['check']['text'], full['check'])
rec = m.load_item(U); pf = dict(portfolio(), holdings=portfolio()['holdings'] + [dict(portfolio()['holdings'][0], id='c2', symbol='C05-USD', label='C05-USD')])
check('coins at the level\'s share while shares are ticked too: it says no more coins and why', 'It buys nothing there: Coins already hold their share of the budget ($2,000 of $2,000). The rest of the budget is for the other markets ticked.' in {c['kind']: c for c in m.coming(m.load_item(U), pf, later, out['plans'])}['check']['text'], [c['text'] for c in m.coming(m.load_item(U), pf, later, out['plans'])][:2])
rec = m.load_item(U); rec['settings']['enabled'] = False
check('switched off: nothing is coming, and it says its holding stays until sold or switched back on', m.coming(rec, portfolio(), later) == [] and [n['kind'] for n in m.needs(rec, portfolio(), later)] == ['off'] and 'still holds 1 holding: it stays until you sell it or switch it back on' in m.needs(rec, portfolio(), later)[0]['text'])
rec = m.load_item(U); rec['settings']['screeners'] = []
check('on with no screener: that needs the user', [n['kind'] for n in m.needs(rec, portfolio(), later)] == ['noscreener'])
rec = m.load_item(U); rec['state']['rest'] = {'3-100': m.iso(later + dt.timedelta(days=9)), '7-1': m.iso(later + dt.timedelta(days=3))}
check('every ticked screener resting: that needs the user, and the list says when each is tried again', [n['kind'] for n in m.needs(rec, portfolio(), later)] == ['resting'] and [c['text'] for c in m.coming(rec, portfolio(), later, out['plans']) if c['kind'] == 'rest'] == ['The Crypto (top coins) screener is tried again after its rest.', 'The S&P 100 screener is tried again after its rest.'])
big = m.load_item(U); big['settings']['budgetUsd'] = 200000.0
check('a budget larger than the practice money there is: that is pointed out', [n['kind'] for n in m.needs(big, portfolio(), later)] == ['budget'] and 'Its budget ($200,000) is more than the practice money it can reach ($100,000: $99,000 cash and $1,000 it has invested)' in m.needs(big, portfolio(), later)[0]['text'], m.needs(big, portfolio(), later))
check('too little practice cash for one more holding: that needs the user', [n['kind'] for n in m.needs(m.load_item(U), dict(portfolio(), cash=500.0), later)] == ['cash'] and 'It buys nothing: the practice cash ($500) is less than one holding ($1,000).' in {c['kind']: c for c in m.coming(m.load_item(U), dict(portfolio(), cash=500.0), later, out['plans'])}['check']['text'])
# a check-in that should have happened and has not
rec = m.load_item(U); due_at = dt.datetime(2026, 10, 11, 9, 10)
check('a check-in is not "missed" before it is due, nor a few minutes after', m.missed_check(rec, due_at - dt.timedelta(minutes=30)) is None and m.missed_check(rec, due_at + dt.timedelta(minutes=20)) is None)
check('two scheduled check-ins in a row not happening is noticed, and needs the user', m.missed_check(rec, due_at + dt.timedelta(minutes=37)) == due_at and [n['kind'] for n in m.needs(rec, portfolio(), due_at + dt.timedelta(minutes=37))] == ['missed'] and m.needs(rec, portfolio(), due_at + dt.timedelta(minutes=37))[0]['at'] == '2026-10-11T09:10:00Z')
rec['state']['savedAt'] = m.iso(due_at + dt.timedelta(minutes=10))
check('but not when the settings were changed since (the timetable changed with them)', m.missed_check(rec, due_at + dt.timedelta(minutes=37)) is None)
m.datetime = at(sun + dt.timedelta(minutes=30)); code_, b = call(action='save', userId=U, settings=dict(m.load_item(U)['settings'], budgetUsd=9000.0)); m.datetime = clock
check('saving a changed setting notes when; saving the same again does not', m.load_item(U)['state']['savedAt'] == m.iso(sun + dt.timedelta(minutes=30)))
m.datetime = at(sun + dt.timedelta(minutes=40)); code_, b = call(action='save', userId=U, settings=m.load_item(U)['settings']); m.datetime = clock
check('(the same settings saved again leave that time alone)', m.load_item(U)['state']['savedAt'] == m.iso(sun + dt.timedelta(minutes=30)))
# a scheduled check-in that stops on an error leaves a trace, and the next good one clears it
real_run = m.run_user; rec = m.load_item(U); rec['state']['lastRunBy'] = {}; rec['state']['lastRun'] = None; m.save_item(U, rec)
def broken(*a, **k): raise KeyError('boom')
m.run_user = broken; m.datetime = at(sun + dt.timedelta(hours=8)); m.lambda_handler({'source': 'aws.events'}, None); m.run_user = real_run
rec = m.load_item(U); note = m.needs(rec, portfolio(), sun + dt.timedelta(hours=8, minutes=5))
check('a scheduled check-in that stops on an error is shown as needing a look', rec['state']['fail'] == {'t': m.iso(sun + dt.timedelta(hours=8)), 'what': 'KeyError'} and [n['kind'] for n in note] == ['fail'] and 'stopped on an error (KeyError)' in note[0]['text'], note)
m.lambda_handler({'source': 'aws.events'}, None); m.datetime = clock
check('and the next check-in that goes through clears it', 'fail' not in m.load_item(U)['state'] and m.load_item(U)['state']['lastRun'] == m.iso(sun + dt.timedelta(hours=8)))
# the email's status and the dashboard's "send me a test email"
sent_mail = []; real_send = m.send_mail
m.datetime = at(sun + dt.timedelta(hours=9)); code_, b = call(action='mailtest', userId=U)
check('a test email outside the function sends nothing and records nothing', code_ == 200 and b['summary'] == {'sent': False} and b['mail'] is None)
m.send_mail = lambda to, subject, lines: (sent_mail.append((to, subject, lines)), True)[1]
code_, b = call(action='mailtest', userId=U)
check('"send me a test email": one email to the account\'s own address, with the record and what it is for', code_ == 200 and b['summary'] == {'sent': True} and len(sent_mail) == 1 and sent_mail[0][0] == U and sent_mail[0][1] == 'StockIQ autopilot (fake money): review emails are set up' and any('Nothing needs doing when such an email arrives' in l for l in sent_mail[0][2]) and any(l == 'THE RECORD SO FAR (fake money)' for l in sent_mail[0][2]) and any('A holding that keeps rising is kept' in l for l in sent_mail[0][2]), sent_mail[:1])
check('the dashboard is told the last email was sent, when and which', b['mail'] == {'t': m.iso(sun + dt.timedelta(hours=9)), 'ok': True, 'subject': 'StockIQ autopilot (fake money): review emails are set up', 'why': None} and b['needs'] == [], b.get('mail'))
check('a second test email within 10 minutes is refused', call(action='mailtest', userId=U)[0] == 429 and len(sent_mail) == 1)
def refuse(to, subject, lines): m.MAIL_ERROR['why'] = 'MessageRejected'; return False
m.send_mail = refuse; m.datetime = at(sun + dt.timedelta(hours=10)); code_, b = call(action='mailtest', userId=U); m.datetime = clock
check('an email the mail service refuses is shown as needing the user, with the reason', b['summary'] == {'sent': False} and b['mail']['ok'] is False and b['mail']['why'] == 'MessageRejected' and [n['kind'] for n in b['needs']] == ['mail'] and 'could not be sent (MessageRejected)' in b['needs'][0]['text'], (b.get('mail'), b.get('needs')))
rec = m.load_item(U); rec['settings']['emails'] = False
check('with its emails switched off a failed email is not held against it', m.needs(rec, portfolio(), sun + dt.timedelta(hours=10)) == [])
check('someone without a paid plan cannot have a test email sent', call(action='mailtest', userId='stranger@y.com')[0] == 402)
m.send_mail = real_send

# --- the budget cannot be more than the practice money there is
D.t.clear(); PRICES.clear(); SNAP['7-1'] = rows('crypto', '7-1'); m.datetime = at(sun)
rec = m.load_item(U); base = dict(rec['settings'], enabled=True, risk=3, screeners=['7-1'], budgetUsd=8000.0)
code_, b = call(action='save', userId=U, settings=base)
check('the dashboard is told how much practice money there is for the autopilot (a new portfolio: all $100,000)', b['money'] == {'cash': 100000.0, 'invested': 0.0, 'reach': 100000} and b['settings']['budgetUsd'] == 8000.0, b.get('money'))
code_, b = call(action='save', userId=U, settings=dict(base, budgetUsd=200000.0))
check('a budget of $200,000 against $100,000 of practice money is set to $100,000, and the activity list says why', b['settings']['budgetUsd'] == 100000.0 and any(e['text'] == 'The budget was set to $100,000: that is all the practice money there is ($100,000 of cash and $0 it has invested).' for e in b['log']) and b['needs'] == [], (b['settings']['budgetUsd'], [e['text'] for e in b['log']][-2:]))
pf = m.new_portfolio(sun); pf['cash'] = 61000.5; pf['holdings'] = [{'id': 'x1', 'symbol': 'C00-USD', 'label': 'C00-USD', 'currency': 'USD', 'qty': 10.0, 'buyPrice': 100.0, 'buyFx': 1, 'costUsd': 1000.0, 'boughtAt': m.iso(sun), 'by': 'ai', 'screener': '7-1'}, {'id': 'm1', 'symbol': 'AAPL', 'label': 'AAPL', 'currency': 'USD', 'qty': 1.0, 'buyPrice': 38000.0, 'buyFx': 1, 'costUsd': 38000.0, 'boughtAt': m.iso(sun)}]
D.Table(m.PORTFOLIO_TABLE).rows[U] = {'userId': U, 'data': json.dumps(pf), 'version': 3}
code_, b = call(action='save', userId=U, settings=dict(base, budgetUsd=90000.0))
check('what the owner has spent on his own buys is not there for it: the most is the cash plus what it has itself invested', b['money'] == {'cash': 61000.5, 'invested': 1000.0, 'reach': 62000} and b['settings']['budgetUsd'] == 62000.0 and any('The budget was set to $62,000: that is all the practice money there is ($61,000 of cash and $1,000 it has invested).' == e['text'] for e in b['log']), (b.get('money'), b['settings']['budgetUsd']))
n_notes = len([e for e in b['log'] if 'The budget was set to' in e['text']]); code_, b = call(action='save', userId=U, settings=dict(b['settings'], risk=4))
check('another setting saved afterwards leaves the budget and adds no second note', b['settings']['budgetUsd'] == 62000.0 and len([e for e in b['log'] if 'The budget was set to' in e['text']]) == n_notes)
code_, b = call(action='save', userId=U, settings=dict(b['settings'], budgetUsd=62000.0, risk=3)); code_, b = call(action='save', userId=U, settings=dict(b['settings'], budgetUsd=50000.0))
check('a budget within the practice money is saved as typed', b['settings']['budgetUsd'] == 50000.0)
m.datetime = clock

# --- the budget is spread over the markets ticked: evenly unless the owner sets a share, coins never above the level's on automatic
m.datetime = clock; S = lambda risk, screeners, **shares: m.market_slots(dict(m.DEFAULTS, risk=risk, screeners=screeners, shares=shares))
check('one market ticked gets every holding of the level, coins too', [S(r, ['7-1']) for r in (1, 3, 5)] == [{'Coins': 12}, {'Coins': 8}, {'Coins': 4}] and S(3, ['3-100', '3-8']) == {'US markets': 8})
check('shares and coins: coins get the level\'s share at most, the rest goes to the shares', [S(r, ['3-100', '7-1']) for r in (1, 2, 3, 4, 5)] == [{'US markets': 12, 'Coins': 0}, {'US markets': 10, 'Coins': 0}, {'US markets': 6, 'Coins': 2}, {'US markets': 3, 'Coins': 3}, {'US markets': 2, 'Coins': 2}], [S(r, ['3-100', '7-1']) for r in (1, 2, 3, 4, 5)])
check('three markets: an even spread in whole holdings, coins held to the level', S(3, ['3-100', '4-200', '7-1']) == {'US markets': 3, 'Asia-Pacific markets': 3, 'Coins': 2} and S(5, ['3-100', '4-200', '7-1']) == {'US markets': 2, 'Asia-Pacific markets': 1, 'Coins': 1} and S(1, ['3-100', '4-200', '5-ftse100']) == {'US markets': 4, 'Asia-Pacific markets': 4, 'Europe markets': 4}, (S(3, ['3-100', '4-200', '7-1']), S(5, ['3-100', '4-200', '7-1'])))
check('several screeners of one market count as that one market', S(3, ['3-3', '3-5', '3-6', '3-7', '3-8', '4-200', '7-1']) == {'US markets': 3, 'Asia-Pacific markets': 3, 'Coins': 2})
check('a share set by hand stands, and the others share what is left', S(3, ['3-100', '4-200', '7-1'], Coins=50) == {'US markets': 2, 'Asia-Pacific markets': 2, 'Coins': 4} and S(3, ['3-100', '4-200', '7-1'], **{'US markets': 25}) == {'US markets': 2, 'Asia-Pacific markets': 4, 'Coins': 2} and S(1, ['3-100', '7-1'], Coins=25) == {'US markets': 9, 'Coins': 3}, (S(3, ['3-100', '4-200', '7-1'], Coins=50), S(3, ['3-100', '4-200', '7-1'], **{'US markets': 25})))
check('shares set by hand that use the whole budget leave nothing for an automatic market; ones that use less leave the rest in cash', S(3, ['3-100', '4-200', '7-1'], **{'US markets': 62.5, 'Coins': 37.5}) == {'US markets': 5, 'Asia-Pacific markets': 0, 'Coins': 3} and S(3, ['3-100'], **{'US markets': 50}) == {'US markets': 4})
check('a share for a market that is not ticked is ignored', S(3, ['3-100'], Coins=50) == {'US markets': 8})
check('the holdings always add up to the level\'s number at most', all(sum(S(r, list(k), **sh).values()) <= m.RISK[r]['positions'] for r in (1, 2, 3, 4, 5) for k in (('3-100',), ('3-100', '7-1'), ('3-100', '4-200', '5-ftse100', '5-nikkei225', '7-1')) for sh in ({}, {'Coins': 33.3}, {'US markets': 10, 'Coins': 10})) and all(sum(S(r, ['3-100', '4-200', '5-ftse100', '5-nikkei225', '7-1']).values()) == m.RISK[r]['positions'] for r in (1, 2, 3, 4, 5)))
cs = m.clean_settings({'shares': {'US markets': 80, 'Coins': 50, 'Mars': 10, 'Europe markets': ''}}, U)['shares']
check('shares saved: unknown markets dropped, and together never more than 100%', cs == {'US markets': 80.0, 'Coins': 20.0} and m.clean_settings({'shares': 'x'}, U)['shares'] == {} and m.clean_settings({'shares': {'Coins': -5}}, U)['shares'] == {'Coins': 0.0}, cs)

# --- the regions (13 Oct 2026): every screener of the site, grouped as the Screeners menu is; hours for each exchange
check('the groups are the menu\'s regions, in its order, and every screener has a market with hours and a name',
      m.GROUPS == ('US markets', 'Europe markets', 'Asia-Pacific markets', 'Americas markets', 'Coins')
      and all(v[4] == 'crypto' or (v[4] in m.MARKET_HOURS and v[4] in m.MARKET_NAMES) for v in m.SCREENERS.values())
      and {k: v[5] for k, v in m.SCREENERS.items() if k in ('5-ftse100', '5-dax40', '5-smi', '4-200', '5-nikkei225', '5-hangseng', '5-kospi200', '5-tsx60', '5-bovespa')}
          == {'5-ftse100': 'Europe markets', '5-dax40': 'Europe markets', '5-smi': 'Europe markets', '4-200': 'Asia-Pacific markets', '5-nikkei225': 'Asia-Pacific markets',
              '5-hangseng': 'Asia-Pacific markets', '5-kospi200': 'Asia-Pacific markets', '5-tsx60': 'Americas markets', '5-bovespa': 'Americas markets'}, m.GROUPS)
import datetime as _dt
_op = lambda mk, when: m.market_open(mk, _dt.datetime.fromisoformat(when).replace(tzinfo=_dt.timezone.utc))
check('each new exchange is open in the middle of its session in summer and in winter, and shut outside it and at the weekend',
      all(_op(mk, d + 'T' + mid) for mk, mid in (('eu', '11:00'), ('hk', '03:00'), ('in', '06:00'), ('kr', '03:00'), ('sg', '05:00'), ('ca', '17:00'), ('br', '16:00')) for d in ('2026-07-15', '2026-12-16'))
      and not any(_op(mk, d + 'T' + out) for mk, out in (('eu', '07:30'), ('eu', '15:40'), ('hk', '00:30'), ('hk', '08:30'), ('in', '03:00'), ('in', '10:30'), ('kr', '07:00'), ('sg', '09:30'), ('ca', '13:00'), ('ca', '20:30'), ('br', '12:30'), ('br', '20:30')) for d in ('2026-07-15', '2026-12-16'))
      and not any(_op(mk, '2026-07-18T' + mid) for mk, mid in (('eu', '11:00'), ('hk', '03:00'), ('br', '16:00'))))
check('a share of the budget set under a country\'s old name is carried to its region, and two that fall together are added',
      m.clean_settings({'shares': {'US shares': 40, 'Australian shares': 10, 'Japanese shares': 15, 'UK shares': 5}}, U)['shares'] == {'US markets': 40.0, 'Europe markets': 5.0, 'Asia-Pacific markets': 25.0}
      and m.clean_settings({'shares': {'UK shares': ''}}, U)['shares'] == {}, m.clean_settings({'shares': {'US shares': 40, 'Australian shares': 10, 'Japanese shares': 15}}, U)['shares'])
check('the regions share a budget evenly in whole holdings: US, Europe, Asia-Pacific, Americas and coins at Balanced with 50 holdings',
      m.market_slots(m.clean_settings({'risk': 3, 'holdings': 50, 'budgetUsd': 100000, 'screeners': ['3-3', '5-dax40', '5-ftse100', '4-200', '5-nikkei225', '5-hangseng', '5-tsx60', '7-1']}, U))
      == {'US markets': 10, 'Europe markets': 10, 'Asia-Pacific markets': 10, 'Americas markets': 10, 'Coins': 10},
      m.market_slots(m.clean_settings({'risk': 3, 'holdings': 50, 'budgetUsd': 100000, 'screeners': ['3-3', '5-dax40', '5-ftse100', '4-200', '5-nikkei225', '5-hangseng', '5-tsx60', '7-1']}, U)))
check('the new currencies are turned into dollars the yen\'s way (per dollar, turned over), euros the direct way',
      [m.fx_pair(c) for c in ('CAD', 'CHF', 'HKD', 'SGD', 'INR', 'KRW', 'BRL', 'EUR')] == [('USDCAD=X', 1, True), ('USDCHF=X', 1, True), ('USDHKD=X', 1, True), ('USDSGD=X', 1, True), ('USDINR=X', 1, True), ('USDKRW=X', 1, True), ('USDBRL=X', 1, True), ('EURUSD=X', 1, False)])
check('the coin share the rest of the code uses follows the split', m.coin_share(dict(m.DEFAULTS, risk=3, screeners=['3-100', '7-1'])) == 0.25 and m.coin_share(dict(m.DEFAULTS, risk=3, screeners=['7-1'])) == 1.0 and m.coin_share(dict(m.DEFAULTS, risk=3, screeners=['3-100', '7-1'], shares={'Coins': 50})) == 0.5 and m.coin_share(dict(m.DEFAULTS, risk=1, screeners=['3-100', '7-1'])) == 0.0)
D.t.clear(); PRICES.clear(); MODEL['answer'] = None; MODEL['prompts'].clear(); SNAP.update({'3-100': rows(), '4-200': au_rows(), '7-1': rows('crypto', '7-1')})
where = lambda: {g: len([h for h in portfolio()['holdings'] if h.get('by') == 'ai' and m.group_of(h) == g]) for g in m.GROUPS if any(m.group_of(h) == g for h in portfolio()['holdings'])}
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=24, maxHoldDays=20, screeners=['3-100', '4-200', '7-1']); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
s, rec = run(t0); first = where()
check('the first check-in buys from each market, not three from one', s['bought'] == 3 and first == {'US markets': 1, 'Asia-Pacific markets': 1, 'Coins': 1}, first)
for i in (1, 2, 3, 4): s, rec = run(t0 + dt.timedelta(days=i))
check('built up: 3 US, 3 Australian and 2 coin holdings of $1,000, the whole $8,000', where() == {'US markets': 3, 'Asia-Pacific markets': 3, 'Coins': 2} and sum(h['costUsd'] for h in portfolio()['holdings']) == 8000.0 and rec['log'][-1].get('key') == 'full', (where(), rec['log'][-1]))
split = {x['group']: x for x in m.public(m.load_item(U), t0 + dt.timedelta(days=5), U)['split']}
check('the dashboard is told the spread: holdings, percent and dollars per market, and whether it was set by hand', split == {'US markets': {'group': 'US markets', 'holdings': 3, 'pct': 37.5, 'usd': 3000.0, 'own': False}, 'Asia-Pacific markets': {'group': 'Asia-Pacific markets', 'holdings': 3, 'pct': 37.5, 'usd': 3000.0, 'own': False}, 'Coins': {'group': 'Coins', 'holdings': 2, 'pct': 25.0, 'usd': 2000.0, 'own': False}}, split)
D.t.clear(); MODEL['prompts'].clear(); MODEL['answer'] = {'picks': [{'symbol': f'C0{i}-USD', 'reason': 'coin'} for i in range(3)]}
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=24, maxHoldDays=20, screeners=['3-100', '7-1'], shares={'Coins': 12.5}); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
s, rec = run(t0); ask = buy_prompts()[-1]['user']; bought = [(e['symbol'], 'AI model' in e['text']) for e in rec['log'] if e['type'] == 'buy']
check('the AI model is told a market\'s limit, and picks past it are passed over and filled from the other market by rank', 'At most 1 of them from Coins (candidates of: Crypto (top coins)): that market has its share of the budget otherwise.' in ask and s['bought'] == 3 and where() == {'US markets': 2, 'Coins': 1} and bought[0] == ('C00-USD', True), (bought, where()))
for i in (1, 2, 3): s, rec = run(t0 + dt.timedelta(days=i))
check('a share set by hand is kept to: 1 coin holding (12.5%) and 7 US', where() == {'US markets': 7, 'Coins': 1} and m.public(m.load_item(U), t0, U)['split'][1] == {'group': 'Coins', 'holdings': 1, 'pct': 12.5, 'usd': 1000.0, 'own': True}, where())
MODEL['answer'] = None; rec = m.load_item(U); rec['settings'].update(screeners=['4-200'], shares={}); m.save_item(U, rec)
for h in list(portfolio()['holdings'])[:2]: PRICES[h['symbol']] = h['buyPrice'] * 1.5
s, rec = run(t0 + dt.timedelta(days=4)); s, rec = run(t0 + dt.timedelta(days=5))
check('ticking a different market: what it holds from the old ones stays until sold, and only freed money goes to the new one', where().get('Asia-Pacific markets') == 2 and sum(where().values()) == 8 and sum(h['costUsd'] for h in portfolio()['holdings']) == 8000.0, where())
PRICES.clear(); MODEL['prompts'].clear()

# --- "Check in now" releases the next holding's worth of the budget, however many small steps that takes
D.t.clear(); PRICES.clear(); MODEL['answer'] = None; SNAP['7-1'] = rows('crypto', '7-1')
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=5, budgetUsd=4000.0, periodDays=1, everyHours=1, maxHoldDays=20, screeners=['7-1'], shares={}); rec['state']['startedAt'] = m.iso(sun); m.save_item(U, rec)
m.datetime = at(sun); code_, b = call(action='run', userId=U); first = b['summary']['bought']
m.datetime = at(sun + dt.timedelta(minutes=15)); code_, b = call(action='run', userId=U); m.datetime = clock
check('hourly steps of $167 and holdings of $1,000: pressing "Check in now" again still buys the next holding (it used to give up after four steps)', first == 1 and b['summary']['bought'] == 1 and len(portfolio()['holdings']) == 2 and any('released ahead of its time' in e['text'] for e in b['log']), (first, b['summary']))

# --- how far above its 52-week low a share was when bought: recorded with the buy, shown to the AI model, and the record is split by it
D.t.clear(); PRICES.clear(); MODEL['answer'] = None; MODEL['prompts'].clear(); m.datetime = clock
SNAP['3-100'] = [dict(r, from_low=10.0 + 30 * i) for i, r in enumerate(rows())]; SNAP['7-1'] = rows('crypto', '7-1')
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=24, maxHoldDays=20, screeners=['3-100', '7-1'], shares={}); rec['state'].update(startedAt=m.iso(t0), order={'mode': 'rank'}); m.save_item(U, rec)      # (the trial of the buying order is tested on its own below)
MODEL['answer'] = {'picks': [{'symbol': 'S00', 'reason': 'r'}, {'symbol': 'S01', 'reason': 'r'}, {'symbol': 'S02', 'reason': 'r'}]}
s, rec = run(t0); facts = {v['label']: v for v in rec['state']['open'].values()}; ask = buy_prompts()[-1]['user']
check('a share\'s distance above its 52-week low is shown to the AI model and remembered with the buy; a coin has none', '| 10% above 52-week low' in ask and 'C00-USD' in ask and 'above 52-week low' not in [l for l in ask.split('\n') if l.startswith('C00-USD')][0] and facts['S00']['above'] == 10.0 and facts['S02']['above'] == 70.0, (facts.get('S00'), ask[-400:]))
MODEL['answer'] = None; s, rec = run(t0 + dt.timedelta(days=1)); held = {h['label']: h for h in portfolio()['holdings']}
check('(a coin bought the next day carries no such figure)', any(k.endswith('-USD') for k in held) and all('above' not in v for v in rec['state']['open'].values() if v['label'].endswith('-USD')))
for label, mult in (('S00', 0.80), ('S01', 1.30), ('S02', 1.30)): PRICES[held[label]['symbol']] = held[label]['buyPrice'] * mult
s, rec = run(t0 + dt.timedelta(days=2)); card = m.scorecard(rec['history']); bands = {g['label']: (g['n'], g['avg']) for g in card['groups']['above']}
check('the record is split by it once such holdings are sold', bands == {'under 20% above its 52-week low': (1, -20.0), '20% to 50% above it': (1, 30.0), 'more than 50% above it': (1, 30.0)} and [t.get('above') for t in rec['history']] == [10.0, 40.0, 70.0], (bands, [(t['label'], t.get('above')) for t in rec['history']]))
old_trade = dict(rec['history'][0]); old_trade.pop('above'); check('a trade from before this was recorded is left out of that split, and nothing breaks', m.scorecard([old_trade])['groups']['above'] == [] and 'All 1 closed trades' in m.memory_text(m.scorecard([old_trade]), None))
check('once a band has enough trades the AI model is told how it did', '- more than 50% above it: 8 trades, average +30.0%' in m.memory_text(m.scorecard([dict(rec['history'][2])] * 8), None))
PRICES.clear(); SNAP['3-100'] = rows(); MODEL['prompts'].clear()

# --- progress, 20 finished trades at a time: better than the batch before, or not; if not, it looks into why and acts within its own rules
m.datetime = clock
def T20(pcts, **over): return [dict(dict(risk=3, pct=p, usd=p * 10, peak=max(p, 0.5), low=min(p, 0.0), rank=2, rsi=50, exit='time', sold=m.iso(t0 + dt.timedelta(hours=i)), label=f'X{i}', screener='3-100'), **over) for i, p in enumerate(pcts)]
def fresh(history, **state): return {'settings': dict(m.DEFAULTS, enabled=True, risk=3, screeners=['3-100']), 'state': dict({'closedCount': len(history)}, **state), 'log': [], 'history': history}
r = fresh(T20([1.0] * 12 + [-0.5] * 8) + T20([2.0] * 15 + [-1.0] * 5) + T20([0.5] * 7)); bt = m.batches(r)
check('finished trades are counted in batches of 20: two complete and one filling', [(b['no'], b['first'], b['last'], b['n'], b['full'], b['up'], b['avg'], b['usd']) for b in bt] == [(1, 1, 20, 20, True, 12, 0.4, 80.0), (2, 21, 40, 20, True, 15, 1.25, 250.0), (3, 41, 47, 7, False, 7, 0.5, 35.0)], bt)
check('a complete batch is compared with the one before, allowing for chance', bt[1]['prev'] == 0.4 and bt[1]['diff'] == 0.85 and bt[1]['verdict'] == 'better' and 'verdict' not in bt[0] and 'verdict' not in bt[2], bt[1])
check('a small difference is "about the same", a clear drop is "worse"', m.batches(fresh(T20([1.0, -1.0] * 10) + T20([1.2, -1.0] * 10)))[1]['verdict'] == 'same' and m.batches(fresh(T20([2.0] * 20) + T20([-1.0] * 15 + [1.0] * 5)))[1]['verdict'] == 'worse')
cut = fresh(T20([1.0] * 20) + T20([2.0] * 20), closedCount=310); cut['history'] = cut['history'][5:]
check('when old trades have dropped off the record, the batch they belonged to is left out, not shown short', [(b['no'], b['first'], b['n'], b['full']) for b in m.batches(cut)] == [(15, 281, 20, True), (16, 301, 10, False)], m.batches(cut))
MAILS.clear(); good = fresh(T20([2.0] * 15 + [-1.0] * 5)); notes = m.review_progress(good, t0, model, lambda a, b: MAILS.append((a, b)))
check('first batch, and up: it reports, carries on as it is, and emails that', len(notes) == 1 and 'Progress after 20 finished trades: the last 20 averaged +1.25% a trade (+$250.00, 15 up), its first batch, and up. It carries on as it is.' == notes[0]['text'] and good['state']['progress']['reports'][-1]['verdict'] == 'first-up' and 'doing better' in MAILS[0][0] and any(l == '- It carries on as it is.' for l in MAILS[0][1]) and (good['state'].get('tune') or {}).get('trial') is None, (notes, MAILS[:1]))
check('the same batch is not reported twice', m.review_progress(good, t0, model) == [] and len(good['state']['progress']['reports']) == 1)
# no better than the batch before: it looks into why, and tries the most promising change even under the usual bar
MODEL['answer'] = {'pick': 2, 'reason': 'more trades behind the loss limit'}; MODEL['prompts'].clear(); MAILS.clear()
flat = fresh(T20([1.0, -1.0] * 10) + T20([6.0] * 2 + [-6.0] * 4 + [0.3] * 14, exit='stop'), ); 
for t in flat['history'][20:26]: t.update(peak=9.5 if t['pct'] > 0 else 0.5, low=-6.0 if t['pct'] < 0 else 0.0)
notes = m.review_progress(flat, t0, model, lambda a, b: MAILS.append((a, b))); rep = flat['state']['progress']['reports'][-1]; tr = flat['state']['tune']['trial']
check('about the same as before: it says so, says what stands out, and starts a trial of a change the AI model chose from its candidates', rep['verdict'] == 'same' and any('Trades sold at the loss limit: 20 of the 20' in f for f in rep['findings']) and tr is not None and 'It started a trial:' in rep['actions'][-1] and 'The AI model chose it from' in rep['actions'][-1] and 'more trades behind the loss limit' in rep['actions'][-1] and flat['state']['tune']['mark'] == 40, (rep, tr))
ask = [p for p in MODEL['prompts'] if 'Candidate changes' in p['user']][-1]
check('the AI model is given the batch, what stands out and a numbered list to pick from; it cannot invent a change', 'about the same as the 20 before' in ask['user'] and '1. ' in ask['user'] and '2. ' in ask['user'] and tr['param'] in m.TUNABLE and m.bounded(tr['param'], tr['new']) == tr['new'])
check('the email says it looked into why, with what it found and what it did', 'no better: it looked into why' in MAILS[0][0] and 'WHAT STANDS OUT IN THOSE TRADES' in MAILS[0][1] and 'WHAT IT DID' in MAILS[0][1] and any(l.startswith('- It started a trial:') for l in MAILS[0][1]))
check('the ordinary review does not then start a second change', m.review_tuning(flat, t0) == [] and flat['state']['tune']['trial'] == tr)
MODEL['answer'] = {'pick': 99, 'reason': 'x'}; wild = fresh(T20([1.0, -1.0] * 10) + T20([6.0] * 2 + [-6.0] * 4 + [0.3] * 14, exit='stop'))
for t in wild['history'][20:26]: t.update(peak=9.5 if t['pct'] > 0 else 0.5, low=-6.0 if t['pct'] < 0 else 0.0)
m.review_progress(wild, t0, model); check('an answer that is not on the list is ignored: the first candidate is tried', wild['state']['tune']['trial'] is not None and 'The AI model chose it' not in wild['state']['progress']['reports'][-1]['actions'][-1])
# clearly worse after a change it had kept: the change is put back
MODEL['answer'] = None; worse = fresh(T20([2.0] * 20) + T20([-1.0] * 15 + [1.0] * 5, exit='time'))
worse['state']['tune'] = {'values': {'3': {'take': 9.0}}, 'trial': None, 'past': [{'id': 1, 'risk': 3, 'param': 'take', 'old': 18, 'new': 9.0, 'verdict': 'kept', 'since': m.iso(t0 - dt.timedelta(days=9)), 'ended': m.iso(t0 - dt.timedelta(days=1))}], 'mark': 20, 'seq': 1}
notes = m.review_progress(worse, t0, model); rep = worse['state']['progress']['reports'][-1]
check('clearly worse since a change it had kept: the change is put back, and it says so', rep['verdict'] == 'worse' and m.rules_for(worse['settings'], worse['state'])['take'] == 18 and 'It put back a change it had kept (sell at +9%): the 20 trades since did clearly worse. The level\'s own rule applies again: sell at +18%.' in rep['actions'][0] and worse['state']['tune']['past'][0].get('undone'), rep)
off = fresh(T20([2.0] * 20) + T20([-1.0] * 20)); off['settings']['selfTune'] = False; m.review_progress(off, t0, model)
check('with its own trials switched off it reports and changes nothing', off['state']['progress']['reports'][-1]['actions'] == ['"Try changes to its own rules" is switched off under Settings, so nothing was changed.'] and (off['state'].get('tune') or {}).get('trial') is None)
busy = fresh(T20([2.0] * 20) + T20([-1.0] * 20)); busy['state']['tune'] = {'values': {}, 'trial': {'id': 3, 'risk': 3, 'param': 'stop', 'old': -10, 'new': -5.0, 'since': m.iso(t0)}, 'past': [], 'mark': 20, 'seq': 3}; m.review_progress(busy, t0, model)
check('a trial already running is left to finish', busy['state']['progress']['reports'][-1]['actions'] == ['A trial of one of its rules is already running; it is left to finish.'] and busy['state']['tune']['trial']['id'] == 3)
pub = m.public(good, t0)
check('the dashboard gets the batches and the reports', pub['progress']['batch'] == 20 and len(pub['progress']['batches']) == 1 and pub['progress']['reports'][0]['actions'] == ['It carries on as it is.'])
# the budget is put right wherever it is met
D.t.clear(); m.datetime = at(sun); rec = m.load_item(U); rec['settings'].update(enabled=True, risk=5, budgetUsd=200000.0, screeners=['7-1']); rec['state']['startedAt'] = m.iso(sun); m.save_item(U, rec)
code_, b = call(action='get', userId=U)
check('a budget saved before the limit existed is put right as soon as the page is opened, with a line saying why', b['settings']['budgetUsd'] == 100000.0 and m.load_item(U)['settings']['budgetUsd'] == 100000.0 and b['needs'] == [] and any(e['text'] == 'The budget was set to $100,000: that is all the practice money there is ($100,000 of cash and $0 it has invested).' for e in b['log']), (b['settings']['budgetUsd'], b['needs']))
n_lines = len(b['log']); code_, b = call(action='get', userId=U); check('and only once', len(b['log']) == n_lines)
rec = m.load_item(U); rec['settings']['budgetUsd'] = 200000.0; m.save_item(U, rec); m.lambda_handler({'source': 'aws.events'}, None); m.datetime = clock
check('a scheduled check-in never works from a budget larger than the practice money either', m.load_item(U)['settings']['budgetUsd'] == 100000.0 and all(h['costUsd'] <= 25000.01 for h in portfolio()['holdings']), [h['costUsd'] for h in (portfolio() or {}).get('holdings', [])])

# --- its own trial of which share to buy: as ranked, or the one furthest above its 52-week low
D.t.clear(); PRICES.clear(); MODEL['answer'] = None; MODEL['prompts'].clear(); MAILS.clear(); m.datetime = clock
SNAP['3-100'] = [dict(r, from_low=10.0 + 7 * ((i * 5) % 11)) for i, r in enumerate(rows())]; SNAP['7-1'] = rows('crypto', '7-1')       # the share furthest above its low is not the top-ranked one
top12 = SNAP['3-100'][:10]; far = max(top12, key=lambda r: r['from_low'])['symbol']
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=24, maxHoldDays=20, screeners=['3-100', '7-1'], shares={}); rec['state']['startedAt'] = m.iso(t0); m.save_item(U, rec)
s, rec = run(t0); facts = sorted(rec['state']['open'].values(), key=lambda v: v['label']); shares = [v for v in facts if not v['label'].endswith('-USD')]; buys = {e['symbol']: e['text'] for e in rec['log'] if e['type'] == 'buy'}
check('the trial starts by itself at the first share buy', rec['state']['order']['mode'] == 'trial' and rec['state']['order']['buys'] == len(shares) == 2, rec['state'].get('order'))
check('every second share bought is the one furthest above its 52-week low on the shortlist; the other is bought as ranked', sorted(v['o'] for v in shares) == ['low52', 'rank'] and [v['label'] for v in shares if v['o'] == 'low52'] == [far] and [v['chosen'] for v in shares if v['o'] == 'low52'] == ['order'] and [v['label'] for v in shares if v['o'] == 'rank'][0] in ('S00', 'S01'), [(v['label'], v['o'], v.get('above')) for v in shares])
check('the buy says how it was chosen, and a coin is bought as before', 'Furthest above its 52-week low on the shortlist (' in buys[far] and 'bought as the share furthest above its 52-week low, as part of a trial of that order)' in buys[far] and all('o' not in v for v in facts if v['label'].endswith('-USD')) and any(k.endswith('-USD') for k in buys), buys)
pub = m.public(m.load_item(U), t0, U)['order']
check('the dashboard is told about the trial: what, why and how far along', pub['mode'] == 'trial' and pub['with'] == 0 and pub['without'] == 0 and pub['group'] == 10 and 'one figure with a link' in pub['why'], pub)
def done(o, pcts): return [dict(risk=3, pct=p, usd=p * 10, o=o, t=m.iso(t0 + dt.timedelta(hours=1)), sold=m.iso(t0 + dt.timedelta(days=3)), label='X', screener='3-100', rank=2, rsi=50, exit='time') for p in pcts]
r1 = m.load_item(U); r1['history'] = done('low52', [3.0, 4.0, 3.5, 2.5, 3.0, 4.0, 3.5, 2.5, 3.0, 3.0]) + done('rank', [0.5, -0.5, 0.0, 1.0, 0.0, -1.0, 0.5, 0.0, 0.5, -0.5]); notes = m.review_order(r1, t0 + dt.timedelta(days=4), lambda a, b: MAILS.append((a, b)))
check('clearly better that way: the new order is kept, said and emailed with the numbers', r1['state']['order']['mode'] == 'low52' and r1['state']['order']['kept'] is True and 'The new order is kept: from now on every share it buys is the one furthest above its 52-week low on the shortlist. 10 shares bought furthest above their 52-week low averaged +3.20%, 10 bought as ranked +0.05%' in notes[0]['text'] and 'new order kept' in MAILS[0][0], notes)
picks = m.apply_order(r1['state']['order'], [(SNAP['3-100'][0], 'r'), (SNAP['3-100'][1], 'r'), (SNAP['7-1'][0], 'c')], SNAP['3-100'][:12] + SNAP['7-1'][:3]); tags = [(c['symbol'], c.pop('_order', None)) for c, _ in picks]
check('once kept, every share is bought that way: the two furthest above their low, never the same one twice, the coin untouched', tags[0][0] == far and tags[1][0] != far and tags[0][1] == tags[1][1] == 'low52' and tags[2] == ('C00-USD', None) and tags[1][0] == sorted(SNAP['3-100'][:12], key=lambda r: -r['from_low'])[1]['symbol'], tags)
r2 = m.load_item(U); r2['history'] = done('low52', [1.0, -1.0] * 5) + done('rank', [1.2, -1.0] * 5); notes = m.review_order(r2, t0 + dt.timedelta(days=4))
check('no clear difference: the order stays as it was', r2['state']['order']['mode'] == 'rank' and 'The order stays as it was: shares are bought as their screener ranks them.' in notes[0]['text'] and 'no clear improvement' in notes[0]['text'] and m.apply_order(r2['state']['order'], [(SNAP['3-100'][0], 'r')], SNAP['3-100'][:12])[0][0]['symbol'] == 'S00' and '_order' not in SNAP['3-100'][0])
r3 = m.load_item(U); r3['history'] = done('low52', [3.0] * 4) + done('rank', [0.0] * 4)
check('before 10 have finished each way it waits; after 90 days it gives up unchanged', m.review_order(r3, t0 + dt.timedelta(days=30)) == [] and r3['state']['order']['mode'] == 'trial' and 'too few of its share trades had finished' in m.review_order(r3, t0 + dt.timedelta(days=91))[0]['text'] and r3['state']['order']['mode'] == 'rank')
r4 = m.load_item(U); r4['settings']['selfTune'] = False; m.review_order(r4, t0 + dt.timedelta(days=1))
check('with its trials switched off the trial ends, and none starts for someone who never had them on', r4['state']['order']['mode'] == 'rank' and m.order_of({}, dict(m.DEFAULTS, selfTune=False), t0) == {'mode': 'rank'})
code_, b = call(action='tune', userId=U, op='stoporder')
check('the owner can stop the trial from the dashboard', b['order']['mode'] == 'rank' and b['order']['result'] == 'stopped by you' and any('You stopped its trial of buying shares' in e['text'] for e in b['log']), b.get('order'))
r1['state']['order']['mode'] = 'low52'; m.save_item(U, r1); code_, b = call(action='tune', userId=U, op='restoreorder')
check('and put a kept order back', b['order']['mode'] == 'rank' and b['order']['kept'] is False and any('You put the order it buys shares in back' in e['text'] for e in b['log']))
card = m.scorecard(done('low52', [3.0] * 3) + [dict(t, chosen='order') for t in done('low52', [2.0] * 2)] + done('rank', [1.0] * 2))
check('the record shows the shares bought that way as their own group', [(g['label'], g['n']) for g in card['groups']['chosen']] == [('chosen by rank', 5), ('bought furthest above its 52-week low', 2)], card['groups']['chosen'])
PRICES.clear(); SNAP['3-100'] = rows(); MODEL['prompts'].clear()

# --- every account: paused after two weeks without a visit to the dashboard, back on at the next visit; a daily limit on AI calls; check-ins side by side
D.t.clear(); PRICES.clear(); MODEL['answer'] = None; MODEL['prompts'].clear(); SNAP['7-1'] = rows('crypto', '7-1'); SNAP['3-100'] = rows(); sent = []; real_send = m.send_mail
m.send_mail = lambda to, subject, lines: (sent.append((to, subject, lines)), True)[1]
m.datetime = at(sun); code_, b = call(action='save', userId=U, settings=dict(m.load_item(U)['settings'], enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=6, maxHoldDays=5, screeners=['7-1'], shares={}))
visit = m.load_item(U)['state']['visit']
check('a call from the dashboard is written down as a visit', visit == m.iso(sun) and {c['kind']: c for c in b['coming']}['pause']['at'] == m.iso(sun + dt.timedelta(days=14)) and 'It pauses if the dashboard has not been opened by then (14 days without a visit)' in {c['kind']: c for c in b['coming']}['pause']['text'], b['coming'][-3:])
m.datetime = at(sun + dt.timedelta(hours=2)); call(action='get', userId=U); same = m.load_item(U)['state']['visit']; m.datetime = at(sun + dt.timedelta(hours=7)); call(action='get', userId=U)
check('but not every minute: at most every 6 hours', same == visit and m.load_item(U)['state']['visit'] == m.iso(sun + dt.timedelta(hours=7)))
m.datetime = at(sun + dt.timedelta(days=13)); r = json.loads(m.lambda_handler({'source': 'aws.events'}, None)['body'])
check('13 days without a visit: it still checks in', r['paused'] == 0 and len(r['ran']) == 1 and m.load_item(U)['settings']['enabled'] is True, r)
held = len(portfolio()['holdings']); m.datetime = at(sun + dt.timedelta(days=14, hours=8)); r = json.loads(m.lambda_handler({'source': 'aws.events'}, None)['body']); rec = m.load_item(U)
check('more than 14 days without a visit: it is paused instead of checking in, says so, and emails once', r == {'ran': [], 'paused': 1, 'waiting': 0} and rec['settings']['enabled'] is False and D.Table(m.SETTINGS_TABLE).rows[U]['enabled'] is False and rec['state']['pausedAt'] == m.iso(sun + dt.timedelta(days=14, hours=8)) and len(portfolio()['holdings']) == held and rec['log'][-1]['text'].startswith('Paused: the dashboard has not been opened for 14 days, so the autopilot has stopped checking in.') and 'It switches back on by itself the next time the dashboard is opened.' in rec['log'][-1]['text'] and len(sent) == 1 and sent[0][0] == U and 'paused' in sent[0][1], (r, rec['log'][-1]['text'], sent[-1:]))
m.datetime = at(sun + dt.timedelta(days=20)); r = json.loads(m.lambda_handler({'source': 'aws.events'}, None)['body'])
check('while paused the schedule passes it by: nothing runs, nothing is sent again', r == {'ran': [], 'paused': 0, 'waiting': 0} and len(sent) == 1)
m.datetime = at(sun + dt.timedelta(days=21)); code_, b = call(action='get', userId=U); rec = m.load_item(U)
check('the next visit switches it back on by itself, and says so', b['settings']['enabled'] is True and 'pausedAt' not in rec['state'] and D.Table(m.SETTINGS_TABLE).rows[U]['enabled'] is True and any(e['text'].startswith('Welcome back: the autopilot is on again. It had been paused since 25 Oct because the dashboard had not been opened for 14 days.') for e in b['log']) and b['nextCheck'] is not None, [e['text'] for e in b['log']][-2:])
rec = m.load_item(U); rec['state'].pop('visit'); rec['state']['lastRunBy'] = {}; rec['state']['lastRun'] = None; m.save_item(U, rec); r = json.loads(m.lambda_handler({'source': 'aws.events'}, None)['body'])
check('a record from before visits were written down gets its two weeks from now, and is not paused', r['paused'] == 0 and len(r['ran']) == 1 and m.load_item(U)['state']['visit'] == m.iso(sun + dt.timedelta(days=21)))
quiet = m.load_item(U); quiet['settings']['emails'] = False; quiet['state']['visit'] = m.iso(sun); n_sent = len(sent)
check('with its emails switched off the pause is not emailed', m.pause_if_away(U, quiet, sun + dt.timedelta(days=30), m.send_mail) is True and len(sent) == n_sent and quiet['settings']['enabled'] is False)
# several accounts: side by side, and none started when the run is short of time
rec = m.load_item(U); rec['state'].update(lastRunBy={}, lastRun=None, visit=m.iso(sun + dt.timedelta(days=21))); m.save_item(U, rec)
two = m.load_item('dave@x.com'); two['settings'].update(enabled=True, risk=3, screeners=['7-1']); two['state'].update(startedAt=m.iso(sun + dt.timedelta(days=21)), visit=m.iso(sun + dt.timedelta(days=21))); m.save_item('dave@x.com', two)
class Short:
    def get_remaining_time_in_millis(self): return 60000
r = json.loads(m.lambda_handler({'source': 'aws.events'}, Short())['body'])
check('with too little of the run\'s time left no check-in is started: both accounts wait for the next run', r == {'ran': [], 'paused': 0, 'waiting': 2} and m.due_markets(m.load_item(U), sun + dt.timedelta(days=21)) == ['crypto'], r)
r = json.loads(m.lambda_handler({'source': 'aws.events'}, None)['body'])
check('two accounts due at once are both run, each on its own portfolio', len(r['ran']) == 2 and 'dave@x.com' in D.Table(m.PORTFOLIO_TABLE).rows and m.load_item('dave@x.com')['state']['lastRun'] == m.iso(sun + dt.timedelta(days=21)), r)
# the daily limit on AI calls for one account
m.datetime = clock; D.t.clear(); MODEL['prompts'].clear(); MODEL['answer'] = {'picks': [{'symbol': 'C03-USD', 'reason': 'model'}]}
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=8, everyHours=24, maxHoldDays=20, screeners=['7-1'], shares={}); rec['state'].update(startedAt=m.iso(t0), ai={'day': m.iso(t0)[:10], 'n': m.AI_CALLS_PER_DAY}); m.save_item(U, rec)
s, rec = run(t0); buy = [e for e in rec['log'] if e['type'] == 'buy'][-1]
check('past the day\'s limit the AI model is not asked: the buy goes by rank, and one line says why', MODEL['prompts'] == [] and 'chosen by rank' in buy['text'] and buy['symbol'] == 'C00-USD' and sum('its daily limit' in e['text'] for e in rec['log']) == 1 and rec['state']['ai']['n'] == m.AI_CALLS_PER_DAY, (buy['text'], rec['state']['ai']))
s, rec = run(t0 + dt.timedelta(hours=1)); check('and it is said once a day, not at every check-in', sum('its daily limit' in e['text'] for e in rec['log']) == 1)
s, rec = run(t0 + dt.timedelta(days=1)); buy = [e for e in rec['log'] if e['type'] == 'buy'][-1]
check('the next day the count starts again and the AI model chooses', rec['state']['ai']['day'] == m.iso(t0 + dt.timedelta(days=1))[:10] and 1 <= rec['state']['ai']['n'] <= 3 and 'chosen by the AI model' in buy['text'] and buy['symbol'] == 'C03-USD', (buy['text'], rec['state']['ai']))
m.send_mail = real_send; MODEL['answer'] = None; MODEL['prompts'].clear()

# --- who may use it: accounts on a paid plan (and the listed ones); everyone else is shown what it is and where the plans are
D.t.clear(); m.PLAN_CACHE.clear(); m.datetime = at(sun); PRICES.clear(); MODEL['answer'] = None; SNAP['7-1'] = rows('crypto', '7-1'); sent = []; real_send = m.send_mail
m.send_mail = lambda to, subject, lines: (sent.append((to, subject, lines)), True)[1]
plans = D.Table(m.USERS_TABLE).rows
def plan(email, **fields): m.PLAN_CACHE.clear(); plans[f'{email}#registration'] = dict({'user_date': f'{email}#registration'}, **fields)
check('no plan on record is not a paid plan; the listed accounts need none', m.plan_of('nobody@z.com') == 'free' and m.allowed('nobody@z.com') is False and m.allowed(U) is True and m.listed('nobody@z.com') is False)
plan('pay@z.com', subscriptionStatus='active', planType='starter', expiryDate='2026-11-01'); plan('gone@z.com', subscriptionStatus='cancelled', planType='pro', expiryDate='2026-10-01'); plan('paidup@z.com', subscriptionStatus='cancelled', planType='pro', expiryDate='2026-10-20'); plan('trial@z.com', isTrialActive=True)
check('paid: an active subscription, or a cancelled one still inside the time paid for; a free trial or an ended plan is not', [m.plan_of(x) for x in ('pay@z.com', 'paidup@z.com', 'gone@z.com', 'trial@z.com')] == ['paid', 'paid', 'free', 'free'])
code_, b = call(action='get', userId='trial@z.com')
check('an account without a paid plan is told the autopilot is locked and where the plans are, and no record is made for it', (code_, b) == (200, {'success': True, 'allowed': False, 'locked': 'plan', 'upgrade': 'dashboard.html#upgrade'}) and 'trial@z.com' not in D.Table(m.SETTINGS_TABLE).rows)
for act in ('save', 'run', 'sellall', 'tune', 'mailtest'):
    code_, b = call(action=act, userId='trial@z.com', settings=dict(m.DEFAULTS, enabled=True, screeners=['7-1']))
    if not (code_ == 402 and b['locked'] == 'plan' and 'part of the paid plans' in b['error'] and b['upgrade'] == 'dashboard.html#upgrade'): check(f'trying to {act} without a paid plan is refused and pointed to the plans', False, (code_, b)); break
else: check('trying to save, run, sell or test without a paid plan is refused and pointed to the plans, and nothing is stored or traded', 'trial@z.com' not in D.Table(m.SETTINGS_TABLE).rows and 'trial@z.com' not in D.Table(m.PORTFOLIO_TABLE).rows and sent == [])
code_, b = call(action='save', userId='pay@z.com', settings=dict(m.DEFAULTS, enabled=True, risk=3, budgetUsd=8000.0, screeners=['7-1'], auto=[], periodDays=1, everyHours=6, maxHoldDays=5))
check('an account on a paid plan can switch it on like the owner', code_ == 200 and b['allowed'] is True and b['settings']['enabled'] is True and b['nextCheck'] is not None, (code_, b.get('settings')))
m.datetime = at(sun + dt.timedelta(minutes=30)); r = json.loads(m.lambda_handler({'source': 'aws.events'}, None)['body'])
check('and the schedule checks in for it', len(r['ran']) == 1 and r['ran'][0]['bought'] >= 1 and 'pay@z.com' in D.Table(m.PORTFOLIO_TABLE).rows, r)
plan('pay@z.com', subscriptionStatus='cancelled', planType='starter', expiryDate='2026-10-10'); m.datetime = at(sun + dt.timedelta(days=1)); r = json.loads(m.lambda_handler({'source': 'aws.events'}, None)['body']); rec = json.loads(D.Table(m.SETTINGS_TABLE).rows['pay@z.com']['data'])
check('when its plan has ended the schedule pauses it instead of checking in, says why, and emails once', r == {'ran': [], 'paused': 1, 'waiting': 0} and D.Table(m.SETTINGS_TABLE).rows['pay@z.com']['enabled'] is False and rec['state']['pausedWhy'] == 'plan' and rec['log'][-1]['text'].startswith('Paused: the AI autopilot is part of the paid plans, and this account is no longer on one') and len(sent) == 1 and 'the paid plan has ended' in sent[0][1], (r, rec['log'][-1]['text'][:90], sent[-1:]))
code_, b = call(action='get', userId='pay@z.com'); check('its dashboard then shows the locked view', b.get('locked') == 'plan' and b['allowed'] is False)
plan('pay@z.com', subscriptionStatus='active', planType='pro', expiryDate='2026-12-01'); m.datetime = at(sun + dt.timedelta(days=2)); code_, b = call(action='get', userId='pay@z.com')
check('and once it is on a paid plan again, opening the dashboard switches the autopilot back on and says so', b['allowed'] is True and b['settings']['enabled'] is True and any(e['text'].startswith('Welcome back: the autopilot is on again. It had been paused since 12 Oct because the paid plan had ended.') for e in b['log']), [e['text'][:110] for e in b['log']][-2:])
broken = D.Table(m.USERS_TABLE); real_get = broken.get_item; m.PLAN_CACHE.clear()
def fail(Key): raise RuntimeError('database away')
broken.get_item = fail; code_, b = call(action='get', userId='pay@z.com'); code2, b2 = call(action='run', userId='pay@z.com'); r = json.loads(m.lambda_handler({'source': 'aws.events'}, None)['body']); broken.get_item = real_get; m.PLAN_CACHE.clear()
check('if the plan cannot be read, nobody is locked out for good or paused: the page says to try again and the schedule leaves the account for its next run', b == {'success': True, 'allowed': False, 'locked': 'unknown'} and code2 == 503 and r['paused'] == 0 and r['waiting'] == 1 and json.loads(D.Table(m.SETTINGS_TABLE).rows['pay@z.com']['data'])['settings']['enabled'] is True, (b, code2, r))
m.send_mail = real_send; m.datetime = clock; m.PLAN_CACHE.clear()

# --- learning shared by every account: one record that every account's finished trades go into and every autopilot uses
m.CENTRAL = SHARED; m._BRAIN.clear(); D.t.clear(); m.PLAN_CACHE.clear(); MODEL['prompts'].clear(); real_model = m.ask_model; m.ask_model = model
check('shared learning is on in the deployed function', m.CENTRAL is True)
A, B, S = 'dave@x.com', 'tester@x.com', D.Table(m.SETTINGS_TABLE)
ra, rb = fresh([dict(t, id=f'h{i}') for i, t in enumerate(T20([1.0] * 20))]), fresh([dict(t, id=f'h{i}') for i, t in enumerate(T20([-1.0] * 5, label='Y'))])
ra['settings']['enabled'] = rb['settings']['enabled'] = False
m.save_item(A, ra); m.save_item(B, rb); queue = lambda: [k for k in S.rows if k.startswith(m.POOL_PREFIX)]
check("an account's finished trades are queued for the shared record when its record is saved, with nothing that says whose they are",
      len(queue()) == 2 and all('@' not in json.dumps(S.rows[k]) and 'dave' not in json.dumps(S.rows[k]) and '"id"' not in S.rows[k]['data'] for k in queue()) and all(t.get('p') == 1 for t in ra['history']), queue())
m.save_item(A, ra); check('and each trade only once', len(queue()) == 2)
ra['history'][0]['after'] = 4.2; m.save_item(A, ra)
check('what a holding did after it was sold is sent on once it is known', len(queue()) == 3 and ra['history'][0]['p'] == 2 and any('"after": 4.2' in S.rows[k]['data'] and '"pct"' not in S.rows[k]['data'] for k in queue()))
m.lambda_handler({'source': 'aws.events'}, None); brain = m.load_brain(fresh=True)
check('the scheduled run takes them into one record: 25 trades from 2 accounts, counted by risk level, the later figure added, the queue emptied',
      brain['count'] == 25 and len(brain['accounts']) == 2 and brain['counts'] == {'3': 25} and not queue() and len(brain['pool']) == 25 and all('k' in t and 'id' not in t for t in brain['pool'])
      and sum(t.get('after') == 4.2 for t in brain['pool']) == 1, (brain['count'], brain['counts'], brain['accounts'], queue()))
check('and reviews them once for everyone: a progress report for that level, notes for the activity lists, and its trial of the buying order begun',
      (brain['progress'].get('3') or {}).get('done') == 1 and (brain['state'].get('order') or {}).get('mode') == 'trial' and any('Learned from every account at the Balanced level: Progress after 25 finished trades' in n['text'] for n in brain['news']), [n['text'][:90] for n in brain['news']])
m.save_item(A, ra); m.lambda_handler({'source': 'aws.events'}, None)
check('a trade that is sent twice is counted once', m.load_brain(fresh=True)['count'] == 25 and not queue())
brain = m.load_brain(fresh=True)
brain['tunes']['3'] = {'values': {'3': {'take': 9.0}}, 'trial': {'id': 7, 'risk': 3, 'param': 'stop', 'old': -10, 'new': -5, 'direction': 'nearer', 'since': m.iso(t0), 'why': 'w', 'gain': 0.3, 'buys': 0}, 'past': [], 'mark': 20, 'seq': 7}
m.save_brain(brain); newcomer = fresh([]); told = m.adopt(newcomer, brain)
check('a new account starts with what every account has taught it (a rule changed after a trial, the running trial, the buying order) and gets no backlog of old notes',
      m.rules_for(newcomer['settings'], newcomer['state'])['take'] == 9.0 and m.live_trial(newcomer['settings'], newcomer['state'])['id'] == 7 and newcomer['state']['order']['mode'] == 'trial' and told == []
      and newcomer['state']['brainSeen'] == brain['seq'], (told, newcomer['state'].get('tune')))
m.tell_all(brain, ['Learned from every account: something new.'], t0)
check('at its next check-in it is told what has been learned since, once', [n['text'] for n in m.adopt(newcomer, brain)] == ['Learned from every account: something new.'] and m.adopt(newcomer, brain) == [])
newcomer['state']['tune']['trial']['buys'] = 3; m.adopt(newcomer, brain)
check('which of its own buys follow a rule on trial is still counted per account', newcomer['state']['tune']['trial']['buys'] == 3 and brain['tunes']['3']['trial']['buys'] == 0)
apart = fresh([]); apart['settings']['selfTune'] = False; m.adopt(apart, brain)
check('with "Try changes to its own rules" off an account keeps the level\'s plain rules and takes no part in trials',
      m.rules_for(apart['settings'], apart['state'])['take'] == m.RISK[3]['take'] and m.live_trial(apart['settings'], apart['state']) is None and 'order' not in apart['state'])
late = lambda i: m.iso(t0 + dt.timedelta(days=2, hours=i))
brain['pool'] += [dict(risk=3, pct=pc, usd=pc * 10, x=7, v=v, k=f'{v}{i}', sold=late(i), label='Z', screener='3-100', rank=2, rsi=50, exit='time', peak=max(pc, 0.5), low=min(pc, 0.0))
                  for v, ps in (('new', [2.0, 3.0] * 5), ('old', [-1.0, -2.0] * 5)) for i, pc in enumerate(ps)]
brain['counts']['3'] += 20; brain['count'] += 20; notes = m.think(brain, t0 + dt.timedelta(days=3), model); m.adopt(newcomer, brain)
check('a trial is judged on the finished trades of every account together, and a change that is kept then applies to every account',
      brain['tunes']['3']['values']['3'].get('stop') == -5 and brain['tunes']['3']['trial'] is None and any('Trial of its own rules finished' in n and 'The change is kept' in n for n in notes)
      and m.rules_for(newcomer['settings'], newcomer['state'])['stop'] == -5, notes)
m.save_brain(brain); m.save_item(A, ra); code_, b = call(action='get', userId=A)
check('the page is told that learning is shared: how many trades from how many accounts, and progress for every account at its level',
      code_ == 200 and b['central'] == {'trades': 45, 'accounts': 2, 'level': 45, 'on': True, 'canChange': True} and b['progress'].get('shared') is True and len(b['progress']['batches']) == 3
      and b['rules']['stop'] == -5 and any(c.get('kind') == 'review' and c.get('shared') for c in b.get('coming', []) + [{'kind': 'review', 'shared': True}]), b.get('central'))
code_, b = call(action='tune', userId=A, op='restore', param='stop'); brain = m.load_brain(fresh=True)
check('a site account can put a learned rule back, and does so for every account, with a note for their activity lists',
      code_ == 200 and 'stop' not in brain['tunes']['3']['values']['3'] and b['rules']['stop'] == m.RISK[3]['stop'] and 'The site owner put a rule back' in brain['news'][-1]['text'], (code_, brain['news'][-1]))
plans = D.Table(m.USERS_TABLE).rows; plan('pay@z.com', subscriptionStatus='active'); code_, b = call(action='tune', userId='pay@z.com', op='restore', param='take')
check('any other account cannot change what is shared: it is told to use its own switch', code_ == 403 and 'shared by every account' in b['error'] and m.load_brain(fresh=True)['tunes']['3']['values']['3'].get('take') == 9.0, (code_, b))
D.t.clear(); m._BRAIN.clear(); SNAP['3-100'] = rows(); MODEL['answer'] = {'picks': [{'symbol': 'S1', 'reason': 'r'}]}; MODEL['prompts'].clear(); m.datetime = Open
pool = m.new_brain(); pool['pool'] = [dict(t, k=f'k{i}') for i, t in enumerate(T20([1.5] * 12))]; pool['count'], pool['counts'], pool['accounts'] = 12, {'3': 12}, ['aaaa1111', 'bbbb2222']
pool['state'] = {'rest': {'3-8': m.iso(Open.utcnow() + dt.timedelta(days=5))}, 'lessons': {'at': m.iso(t0), 'n': 12, 'items': ['Rank 1 to 3 did best (12 trades).']}}
m.tell_all(pool, ['old news'], t0); m.save_brain(pool)
code_, b = call(action='save', userId=U, settings=dict(m.DEFAULTS, enabled=True, risk=3, budgetUsd=10000, screeners=['3-100']))
s1, rec = run(Open.utcnow()); m.tell_all(pool, ['Learned from every account: a screener was rested.'], Open.utcnow()); m.save_brain(pool); MAILS.clear(); m.DB_NOW = None
rec = m.load_item(U); rec['state']['lastRun'] = None; s2 = m.run_user(U, rec, Open.utcnow() + dt.timedelta(hours=1), snapshot=snapshot, quote=quote, model=model, mail=lambda subject, lines: MAILS.append((subject, lines)), headlines=lambda h, now: [])
prompt = (buy_prompts() or [{'user': ''}])[0]['user']
check('a whole check-in with shared learning: it buys, the AI model is shown this account\'s record and every account\'s together with the shared notes',
      code_ == 200 and s1.get('bought', 0) >= 1 and "Every account's finished trades together (12 so far, from 2 accounts)" in prompt and "This account's own finished trades:" in prompt and 'Rank 1 to 3 did best' in prompt, (s1, prompt[-600:]))
check('what has been learned since its last check-in goes into its activity list and one email; nothing is reviewed per account any more',
      any(e.get('text') == 'Learned from every account: a screener was rested.' for e in s2.get('entries', [])) and len([x for x in MAILS if 'learned from every account' in x[0]]) == 1
      and rec['state'].get('rest') == pool['state']['rest'] and not (rec['state'].get('progress') or {}).get('reports'), (s2.get('entries'), [x[0] for x in MAILS]))
m.ask_model = real_model; m.datetime = clock; m._BRAIN.clear(); m.CENTRAL = SHARED

# --- the notification bell on every page: the latest buys and sells, read-only
D.t.clear(); m._BRAIN.clear(); m.PLAN_CACHE.clear(); rec = fresh([])
rec['log'] = [{'t': '2026-10-10T10:00:00Z', 'type': 'buy', 'symbol': 'CFX-USD', 'name': 'Conflux', 'usd': 1250, 'text': 'r', 'detail': ['long']}, {'t': '2026-10-10T12:00:00Z', 'type': 'note', 'symbol': '', 'usd': 0, 'text': 'Checked in.'},
              {'t': '2026-10-10T16:00:00Z', 'type': 'sell', 'symbol': 'CFX-USD', 'usd': 1262.79, 'pct': 1.02, 'text': 'Sold to keep part of the gain. Put in $1,250.00, got back $1,262.79.'},
              {'t': '2026-10-11T10:00:00Z', 'type': 'sell', 'symbol': 'ERG-USD', 'name': 'Ergo', 'gain': -173.03, 'usd': 6000, 'pct': -2.8, 'text': 'x'}]
m.save_item(U, rec); before = copy.deepcopy(D.Table(m.SETTINGS_TABLE).rows); code_, b = call(action='bell', userId=U, list=2); code0, b0 = call(action='bell', userId=U)
check('an older copy of the bell script, which a browser may still hold, is told nothing (only the question marked list: 2 is answered)', code0 == 200 and b0 == {'success': True, 'allowed': False, 'trades': []}, b0)
check('the bell is given the latest buys and sells only: when, code, name, dollars, and a sale\'s result (read from an older entry\'s words when it was not stored)',
      code_ == 200 and b['allowed'] is True and [(t['type'], t['symbol'], t['gain']) for t in b['trades']] == [('buy', 'CFX-USD', None), ('sell', 'CFX-USD', 12.79), ('sell', 'ERG-USD', -173.03)]
      and b['trades'][0]['name'] == 'Conflux' and b['trades'][2]['pct'] == -2.8 and all(set(t) == {'t', 'type', 'symbol', 'name', 'usd', 'gain', 'pct'} for t in b['trades']), b)
check('asking leaves no trace: nothing is written and it does not count as a visit to the dashboard', D.Table(m.SETTINGS_TABLE).rows == before and 'visit' not in json.loads(before[U]['data'])['state'])
code_, b = call(action='bell', userId='nobody@z.com', list=2)
check('an account without the autopilot gets an empty list and no record is made for it', code_ == 200 and b == {'success': True, 'allowed': False, 'trades': []} and 'nobody@z.com' not in D.Table(m.SETTINGS_TABLE).rows, b)

# --- a trading cost on every buy and sale it makes, and the bar its record has to clear
m.TRADE_COST = COSTS; check('a trading cost is taken off in the deployed function, the same 0.1% as on buys made by hand', m.TRADE_COST == 0.1)
pf = m.new_portfolio(t0); hold = m.do_buy(pf, {'symbol': 'KO', 'label': 'KO', 'screener': '3-100'}, {'price': 50.0, 'name': 'Coca-Cola', 'currency': 'USD'}, 1000, 'r', 500.0, t0, 0)
check('a buy: the whole amount leaves the cash, and a thousandth of it is the cost, so the holding starts a little below what was put in', pf['cash'] == m.STARTING_CASH - 1000 and hold['costUsd'] == 1000 and abs(hold['qty'] - 19.98) < 1e-9, hold)
got = m.do_sell(pf, hold, 50.0, 500.0, t0)
check('a sale at the same price brings back less by the two costs: $998.00 of $1,000', got == 998.0 and pf['cash'] == m.STARTING_CASH - 2.0, got)
facts = m.remember_buy({'open': {}}, dict(hold, boughtAt=m.iso(t0)), {'symbol': 'KO', 'label': 'KO', 'screener': '3-100', 'rank': 1, 'score': 3.0, 'rsi': 50, 'd7': 1, 'd30': 2, 'volume': 1.0}, dict(m.DEFAULTS, risk=3), 'rank')
check('a trade made with the cost says so, and its result is not charged a second time in the month\'s figures', facts.get('c') == 1 and m.month_figures([{'usd': 10.0, 'cost': 1000, 'c': 1, 'sold': m.iso(t0)}], 10000, t0 + dt.timedelta(days=1))['last30']['afterCosts'] == 10.0
      and m.month_figures([{'usd': 10.0, 'cost': 1000, 'sold': m.iso(t0)}], 10000, t0 + dt.timedelta(days=1))['last30']['afterCosts'] == 7.99)
share = lambda pct, market, **k: dict({'pct': pct, 'market': market, 'screener': '3-100', 'c': 1}, **k); coin = lambda pct, **k: dict({'pct': pct, 'market': 9.9, 'screener': '7-1', 'c': 1}, **k)
b = m.bar_of([share(2.0, 1.0), share(1.0, 1.5), coin(3.0), coin(-1.0), share(1.0, None), share(1.0, 0.0, c=0)])
check('the bar: a share is measured against the index fund over its days, a coin against zero, a trade from before the cost pays it here, a share without the fund\'s figure is left out',
      b['need'] == 300 and b['n'] == 5 and abs(b['avg'] - (1.0 - 0.5 + 3.0 - 1.0 + 0.8) / 5) < 0.006 and b['met'] is False, b)
good = m.bar_of([share(1.0 + (i % 5) * 0.2, 0.2) for i in range(300)]); short = m.bar_of([share(1.0 + (i % 5) * 0.2, 0.2) for i in range(299)]); flat = m.bar_of([share((-1) ** i * 3.0 + 0.05, 0.0) for i in range(300)])
check('it is cleared only by 300 finished trades that are ahead by more than twice the margin of error: not by 299, not by 300 that are ahead by a hair', good['met'] is True and short['met'] is False and flat['met'] is False and flat['avg'] > 0, (good, short, flat))
D.t.clear(); m._BRAIN.clear(); m.PLAN_CACHE.clear(); m.save_item(U, fresh([])); code_, b = call(action='get', userId=U)
check('the page is told the cost and the bar', code_ == 200 and b['costEachWay'] == 0.1 and b['bar']['need'] == 300 and b['bar']['n'] == 0 and b['bar']['met'] is False, b.get('bar'))
# --- a share is traded only at a price that has traded lately (12 Oct 2026: a Tokyo share was bought on a Japanese holiday at Friday's price)
if hasattr(m, 'fresh'):
    m.TRADE_COST = 0
    AGE = {}                                                    # hours since each symbol's price last traded; not given: the quote says no time
    def stamp(now, hours): return (now - dt.timedelta(hours=hours) - dt.datetime(1970, 1, 1)).total_seconds()
    NOW3 = {'t': t0}
    def quote3(sym):
        q = quote(sym)
        if q and sym in AGE: q = dict(q, time=stamp(NOW3['t'], AGE[sym]))
        return q
    def run3(now, **settings):
        NOW3['t'] = now; rec = m.load_item(U)
        if settings: rec['settings'].update(settings)
        s = m.run_user(U, rec, now, snapshot=snapshot, quote=quote3, model=model); m.save_item(U, rec); return s, rec
    check('a price is fresh: a coin always, a share that traded ten minutes ago, a quote that gives no time; not a share last traded 20 hours ago',
          m.fresh({'time': stamp(t0, 70)}, 'crypto', t0) and m.fresh({'time': stamp(t0, 0.17)}, 'jp', t0) and m.fresh({'price': 1}, 'us', t0) and m.fresh(None, 'us', t0)
          and not m.fresh({'time': stamp(t0, 20)}, 'jp', t0) and m.fresh({'time': stamp(t0, 2.9)}, 'us', t0) and not m.fresh({'time': stamp(t0, 3.2)}, 'us', t0))
    D.t.clear(); m._BRAIN.clear(); m.PLAN_CACHE.clear(); PRICES.clear(); AGE.clear(); MODEL['answer'] = None; SNAP.clear(); SNAP.update({'3-100': rows()})
    rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=1, maxHoldDays=5, screeners=['3-100'], selfTune=False, aiSell=False, auto=[])
    rec['state']['startedAt'] = m.iso(t0 - dt.timedelta(days=2)); m.save_item(U, rec)
    AGE.update({r['symbol']: 70 for r in SNAP['3-100']})        # the market has not traded for three days: a holiday
    s, rec = run3(t0); note = rec['log'][-1]
    check('on a holiday nothing is bought, and the check-in says which shares it left alone and why', s['bought'] == 0 and not (portfolio() or {'holdings': []})['holdings'] and note['type'] == 'note'
          and 'Left alone: S00 (its price last traded 3 days ago)' in note['text'] and 'public holiday' in note['text'] and note['key'].endswith('+stale'), note)
    s, rec = run3(t0 + dt.timedelta(hours=1))
    check('the same note an hour later is counted on that line, not listed again', s['bought'] == 0 and rec['log'][-1].get('n') == 2 and sum(1 for e in rec['log'] if 'Left alone' in e.get('text', '')) == 1, rec['log'][-2:])
    AGE.update({r['symbol']: 0.2 for r in SNAP['3-100']})
    s, rec = run3(t0 + dt.timedelta(hours=2)); held3 = portfolio()['holdings']
    check('once its price is fresh it is bought', s['bought'] >= 1 and len(held3) == s['bought'] and not any('Left alone' in e.get('text', '') for e in rec['log'][-s['bought']:]), s)
    first = held3[0]; PRICES[first['symbol']] = first['buyPrice'] * 0.5; AGE[first['symbol']] = 70       # far below its loss limit, at a price three days old
    s, rec = run3(t0 + dt.timedelta(hours=3))
    check('a holding is not sold at a stale price either, and the list says it was left alone', s['sold'] == 0 and any(h['id'] == first['id'] for h in portfolio()['holdings']) and any('Left alone: ' + first['label'] in e.get('text', '') for e in rec['log'][-3:]), [s, rec['log'][-1]])
    r = m.sell_everything(U, m.load_item(U), t0 + dt.timedelta(hours=3, minutes=5), quote=quote3)
    check('"Sell everything it holds" keeps it too and lists it with the closed markets', first['label'] in r['closed'] and any(h['id'] == first['id'] for h in portfolio()['holdings']), r)
    AGE[first['symbol']] = 0.1
    s, rec = run3(t0 + dt.timedelta(hours=4))
    check('with a fresh price it is sold at its loss limit as usual', s['sold'] >= 1 and not any(h['id'] == first['id'] for h in portfolio()['holdings']), s)
    # a market that showed only old prices stays due: with a check-in every 12 hours the one look a day would otherwise find old prices every day
    D.t.clear(); m._BRAIN.clear(); m.PLAN_CACHE.clear(); PRICES.clear(); AGE.clear(); MODEL['answer'] = None
    rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=12, maxHoldDays=5, screeners=['3-100'], selfTune=False, aiSell=False, auto=[])
    rec['state']['startedAt'] = m.iso(t0 - dt.timedelta(days=2)); m.save_item(U, rec)
    AGE.update({r['symbol']: 18 for r in SNAP['3-100']})        # ten minutes after an opening: the quotes are still the session before
    s, rec = run3(t0); half = t0 + dt.timedelta(minutes=30)
    check('a market that showed only old prices is not counted as checked: it is due again half an hour later, and the note says so', s['bought'] == 0 and (rec['state'].get('lastRunBy') or {}).get('us') == m.iso(t0 - dt.timedelta(hours=12))
          and m.due_markets(rec, half) == ['us'] and 'in about half an hour' in rec['log'][-1]['text'], [rec['state'].get('lastRunBy'), rec['log'][-1]['text'][-120:]])
    AGE.update({r['symbol']: 0.3 for r in SNAP['3-100']})
    s, rec = run3(half)
    check('half an hour later the prices are of this session: it buys, and the 12-hour gap counts from then', s['bought'] >= 1 and rec['state']['lastRunBy'].get('us') == m.iso(half) and m.due_markets(rec, half + dt.timedelta(minutes=30)) == [], [s, rec['state'].get('lastRunBy')])
    one = portfolio()['holdings'][0]; AGE[one['symbol']] = 30   # one thinly traded holding with an old price, in a market that is trading
    later = half + dt.timedelta(hours=12, minutes=30); later = later if m.market_open('us', later) else t0 + dt.timedelta(days=1)
    s, rec = run3(later)
    check('one old price in a market that is trading does not keep the whole market due', rec['state']['lastRunBy'].get('us') == m.iso(later) and any('Left alone: ' + one['label'] in e.get('text', '') and 'next check-in' in e.get('text', '') for e in rec['log'][-4:]), [rec['state'].get('lastRunBy'), [e.get('text', '')[:90] for e in rec['log'][-3:]]])
    # the function's own fetch_quote (this test put a stand-in in its place further up): run its source against a stand-in answer
    import re as _re, urllib.parse as _up
    src = _re.search(r"^def fetch_quote\(symbol\):\n(?:    .*\n|\n)+", open(sys.argv[1]).read(), _re.M).group(0)
    space = {'http_json': lambda url, timeout=20: {'chart': {'result': [{'meta': {'regularMarketPrice': 12.5, 'regularMarketTime': 1791000000, 'currency': 'JPY'}, 'indicators': {'quote': [{}]}}]}},
             'PRICE_URL': '', 'urllib': __import__('urllib'), 'num': m.num, 'daily_range': m.daily_range}
    exec(src, space); q = space['fetch_quote']('6976.T')
    check('the quote the function fetches carries the time of the last trade', q and q['time'] == 1791000000 and q['price'] == 12.5 and q['currency'] == 'JPY', q)
# --- the number of holdings as a setting of its own (12 Oct 2026): the level's, or the user's own number
if hasattr(m, 'holdings_of'):
    m.TRADE_COST = 0
    cs = lambda **k: m.clean_settings(dict(dict(m.DEFAULTS, enabled=True, risk=3, budgetUsd=20000, screeners=['3-100']), **k), U)
    check('the number of holdings: left to the level when empty, kept when set, held between 2 and 50, never so many that one is under the smallest buy',
          cs()['holdings'] is None and cs(holdings='')['holdings'] is None and cs(holdings=0)['holdings'] is None and cs(holdings=20)['holdings'] == 20 and cs(holdings=1)['holdings'] == 2
          and cs(holdings=500)['holdings'] == 50 and cs(holdings=50, budgetUsd=100)['holdings'] == 4 and m.holdings_of(cs()) == 8 and m.holdings_of(cs(holdings=20)) == 20, [cs(holdings=50, budgetUsd=100)['holdings']])
    r20, r3 = m.rules_for(cs(holdings=20)), m.rules_for(cs(holdings=3))
    check('with more holdings than the level looks at it buys further down each ranking; with fewer the ranking limit stays; the limits stay the level\'s', r20['positions'] == 20 and r20['top'] == 20 and r3['positions'] == 3 and r3['top'] == m.RISK[3]['top']
          and m.rules_for(cs(holdings=50))['top'] == 30 and r20['stop'] == m.RISK[3]['stop'] and m.rules_for(cs())['positions'] == 8, [r20['top'], r3['top']])
    check('buys at one check-in: three, or a fifth of the holdings when there are many', m.buys_per_check(cs()) == 3 and m.buys_per_check(cs(holdings=15)) == 3 and m.buys_per_check(cs(holdings=20)) == 4 and m.buys_per_check(cs(holdings=50)) == 10)
    sl = m.market_slots(cs(holdings=20, screeners=['3-100', '4-200', '7-1']))
    check('the spread over markets is in the user\'s number of holdings: 20 over US shares, Australian shares and coins, coins held to the level\'s quarter', sum(sl.values()) == 20 and sl.get('Coins') == 5 and sl.get('US markets') >= 7, sl)
    D.t.clear(); m._BRAIN.clear(); m.PLAN_CACHE.clear(); PRICES.clear(); MODEL['answer'] = None; SNAP.clear(); SNAP.update({'3-100': rows(n=40)})
    rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=20000.0, periodDays=1, everyHours=24, maxHoldDays=5, screeners=['3-100'], selfTune=False, aiSell=False, auto=[], holdings=20)
    rec['state']['startedAt'] = m.iso(t0 - dt.timedelta(days=2)); m.save_item(U, rec)
    s, rec = run(t0); held20 = portfolio()['holdings']
    check('a check-in with 20 holdings set: four buys of a twentieth of the budget each', s['bought'] == 4 and len(held20) == 4 and all(abs(h['costUsd'] - 1000.0) < 0.01 for h in held20), [s, [h['costUsd'] for h in held20]])
    code_, b = call(action='get', userId=U)
    check('the page is told the number in force and its bounds', code_ == 200 and b['settings']['holdings'] == 20 and b['rules']['positions'] == 20 and b['options']['holdings'] == {'min': 2, 'max': 50, 'buysEach': 3}, [b['settings'].get('holdings'), b['rules'].get('positions'), b['options'].get('holdings')])
    code_, b = call(action='save', userId=U, settings=dict(rec['settings'], holdings=None))
    check('emptied again, it goes back to the level\'s', code_ == 200 and b['settings']['holdings'] is None and b['rules']['positions'] == 8, [b['settings'].get('holdings'), b['rules'].get('positions')])
m.TRADE_COST = 0
# ---- each buy remembers how many headlines the model was shown for it (a measurement: the review splits the record by it)
if 'heads' in m.POOL_FIELDS:
    D.t.clear(); m._BRAIN.clear(); was_central = m.CENTRAL; m.CENTRAL = False; m.datetime = Open; SNAP['3-100'] = rows(); MODEL['answer'] = None
    told = lambda holding, now: [{'title': 'Something about it', 'hours': 5.0}, {'title': 'Older', 'hours': 30.0}] if holding.get('label') == SNAP['3-100'][0]['label'] else []
    rec = m.load_item(U); rec['settings'] = dict(m.DEFAULTS, enabled=True, risk=3, budgetUsd=10000, periodDays=1, screeners=['3-100']); rec['state'] = {'startedAt': m.iso(Open.utcnow() - dt.timedelta(days=2))}
    m.run_user(U, rec, Open.utcnow(), snapshot=snapshot, quote=quote, model=model, headlines=told)
    kept = {f['label']: f for f in rec['state']['open'].values()}; first = SNAP['3-100'][0]['label']
    check('a buy remembers how many headlines the model was shown for it, and how old the newest was', len(kept) >= 2 and kept[first].get('heads') == 2 and kept[first].get('headAge') == 5.0, {k: (v.get('heads'), v.get('headAge')) for k, v in kept.items()})
    check('and a buy with none says none, with no age', all(f.get('heads') == 0 and 'headAge' not in f for l, f in kept.items() if l != first))
    m.CENTRAL = was_central; m.datetime = clock
# ---- the patient-shares trial: pairs of shares in turn are kept 30 days and sold by price or time only
if PATIENT_ON:
    m.PATIENT = True; D.t.clear(); m._BRAIN.clear(); was_central = m.CENTRAL; m.CENTRAL = False; m.datetime = Open; SNAP['3-100'] = rows(); SNAP['7-1'] = rows('crypto', '7-1'); MODEL['answer'] = None; MODEL['prompts'].clear()
    base = dict(m.DEFAULTS, enabled=True, risk=3, budgetUsd=16000, periodDays=1, everyHours=24, maxHoldDays=5, auto=[], screeners=['3-100'])
    rec = m.load_item(U); rec['settings'] = dict(base); rec['state'] = {'startedAt': m.iso(Open.utcnow() - dt.timedelta(days=2))}
    m.run_user(U, rec, Open.utcnow(), snapshot=snapshot, quote=quote, model=model)
    m.run_user(U, rec, Open.utcnow() + dt.timedelta(days=1), snapshot=snapshot, quote=quote, model=model)
    tags = [f.get('pt') for f in rec['state']['open'].values()]
    check('shares are tagged in pairs, two ordinary then two patient, so the trial does not fall together with the buying-order trial', len(tags) >= 5 and tags[:5] == [0, 0, 1, 1, 0], tags)
    pat = [f for f in rec['state']['open'].values() if f.get('pt') == 1]; plain = [f for f in rec['state']['open'].values() if f.get('pt') == 0]
    check('a patient share is kept no longer than any other: the time the user set stands', all(f['hold'] == 5 for f in pat) and all(f['hold'] == 5 for f in plain), [f['hold'] for f in rec['state']['open'].values()])
    buys = [e for e in rec['log'] if e['type'] == 'buy']; words = {e['symbol']: e['detail'][0] for e in buys}
    check('the plan under a patient buy says so, and the plan under an ordinary one still says it sells on the signal', all('A patient share, part of a trial' in words[f['label']] and 'keep it for up to 5 days' in words[f['label']] and 'Also sell if its screener signal' not in words[f['label']] for f in pat)
          and all('Also sell if its screener signal turns negative' in words[f['label']] and 'keep it for up to 5 days' in words[f['label']] for f in plain), list(words.values())[2][:200])
    m.save_item(U, rec); port = portfolio(); held = {h['id']: h for h in port['holdings']}; ids = list(rec['state']['open']); a_plain, a_pat = ids[0], ids[2]
    bad = next(iter(m.NEGATIVE)); now5 = Open.utcnow() + dt.timedelta(days=3)
    turned = {'3-100': [dict(r, signal=bad, score=-1.0, rank=90) for r in rows()]}
    qs = {h['symbol']: {'price': h['buyPrice'], 'currency': 'USD'} for h in port['holdings']}; kinds = {}
    sold = m.review_sells(port, rec['settings'], turned, qs, now5, opened=rec['state']['open'], kinds=kinds)
    gone = {h['id'] for h, _p, _r in sold}
    check('when the signal turns, the ordinary shares are sold and the patient ones are kept', all((i in gone) == (rec['state']['open'][i].get('pt') == 0) for i in ids) and set(kinds.values()) == {'signal'}, [(rec['state']['open'][i].get('pt'), i in gone) for i in ids])
    sold = m.review_sells(port, rec['settings'], turned, qs, Open.utcnow() + dt.timedelta(days=8), opened=rec['state']['open'], kinds=(k2 := {}))
    check('at the end of the user\'s 5 days both kinds go, the patient one at the time limit', a_pat in k2 and k2[a_pat] == 'time' and a_plain in k2, k2)
    low = dict(qs); low[held[a_pat]['symbol']] = {'price': held[a_pat]['buyPrice'] * 0.85, 'currency': 'USD'}
    sold = m.review_sells(port, rec['settings'], {'3-100': rows()}, low, now5, opened=rec['state']['open'], kinds=(k4 := {}))
    check('a patient share is still sold at the loss limit', k4.get(a_pat) == 'stop')
    MODEL['prompts'].clear(); MODEL['answer'] = {'reviews': []}; rec2 = m.load_item(U)
    m.run_user(U, rec2, Open.utcnow() + dt.timedelta(days=2), snapshot=snapshot, quote=quote, model=model)
    asked = ' '.join(str(p.get('user', '')) for p in MODEL['prompts'] if 'review step' in str(p.get('system', '')))
    check('the AI model\'s review is given the ordinary shares and not the patient ones', asked and all((f['label'] + ' ' in asked or f['label'] + ':' in asked or f['label'] in asked) == (f.get('pt') == 0) for f in list(rec2['state']['open'].values())[:4]), asked[:300])
    pub = m.public(rec2, Open.utcnow() + dt.timedelta(days=2), U); plans = {p['id']: p for p in pub['plans']}
    check('the page is told which holdings are patient', plans[a_pat]['patient'] is True and plans[a_pat]['holdDays'] == 5 and plans[a_plain]['patient'] is False and plans[a_plain]['holdDays'] == 5, [plans[a_pat], plans[a_plain]])
    D.t.clear(); rec = m.load_item(U); rec['settings'] = dict(base, screeners=['7-1'], everyHours=24); rec['state'] = {'startedAt': m.iso(Open.utcnow() - dt.timedelta(days=2))}
    m.run_user(U, rec, Open.utcnow(), snapshot=snapshot, quote=quote, model=model)
    if "facts['stop'] = {'arm': first_stop['arm']" in open(sys.argv[1]).read():
        D.t.clear(); ATR['S00'] = 1.5; ATR['S01'] = 4.0; r3 = m.load_item(U); r3['settings'] = dict(base); r3['state'] = {'startedAt': m.iso(Open.utcnow() - dt.timedelta(days=2))}
        m.run_user(U, r3, Open.utcnow(), snapshot=snapshot, quote=quote, model=model); stops = {x['label']: x.get('stop') for x in r3['state']['open'].values()}
        pub3 = m.public(r3, Open.utcnow(), U); arms = {p_['label']: p_['arm'] for p_ in pub3['plans']}
        check('a new holding carries its own stop from the moment it is bought, so the page does not show one figure for all until the next check-in', stops['S00'] and stops['S01'] and stops['S00']['move'] and stops['S00']['arm'] != stops['S01']['arm'] and arms['S00'] == stops['S00']['arm'] and arms['S01'] == stops['S01']['arm'], [stops.get('S00'), stops.get('S01'), arms])
        ATR.clear()
    check('coins are not part of it', rec['state']['open'] and all('pt' not in f for f in rec['state']['open'].values()), [f.get('pt') for f in rec['state']['open'].values()])
    D.t.clear(); rec = m.load_item(U); rec['settings'] = dict(base, selfTune=False); rec['state'] = {'startedAt': m.iso(Open.utcnow() - dt.timedelta(days=2))}
    m.run_user(U, rec, Open.utcnow(), snapshot=snapshot, quote=quote, model=model)
    check('nor is an account with "Try changes to its own rules" switched off', rec['state']['open'] and all('pt' not in f for f in rec['state']['open'].values()))
    check('the tag goes with a finished trade into the shared record', 'pt' in m.POOL_FIELDS)
    m.PATIENT = False; m.CENTRAL = was_central; m.datetime = clock; D.t.clear(); m._BRAIN.clear()
# ---- a build-up that begins again paces out only what is not invested yet
if hasattr(m, 'already_in'):
    began = Open.utcnow(); S10 = dict(m.DEFAULTS, enabled=True, risk=3, budgetUsd=10000, periodDays=1, everyHours=3, maxHoldDays=10, auto=[], screeners=['3-100'])
    hold = lambda i, when, cost=1250.0: {'id': f'b{i}', 'symbol': f'S{i:02d}', 'label': f'S{i:02d}', 'by': 'ai', 'screener': '3-100', 'qty': 1, 'buyPrice': cost, 'buyFx': 1, 'currency': 'USD', 'costUsd': cost, 'boughtAt': m.iso(when)}
    old6 = {'cash': 90000.0, 'holdings': [hold(i, began - dt.timedelta(hours=5)) for i in range(6)], 'closed': []}; st_ = {'startedAt': m.iso(began)}
    room0, inv0 = m.allowance(old6, S10, st_, began + dt.timedelta(minutes=5))
    check('with $7,500 of $10,000 invested when the build-up begins again, the first check-in can buy at once: the steps release the rest, not the whole budget from nothing', m.already_in(old6, st_) == 7500 and inv0 == 7500 and abs(room0 - 1250) < 0.01, [m.already_in(old6, st_), room0])
    room1, _ = m.allowance(old6, S10, st_, began + dt.timedelta(hours=12, minutes=5)); room2, _ = m.allowance(old6, S10, st_, began + dt.timedelta(hours=24, minutes=5))
    check('half way through the day half of the rest is out, and at the end all of it', abs(room1 - 2500) < 0.01 and abs(room2 - 2500) < 0.01 and abs(m.released(S10, st_, began + dt.timedelta(hours=6, minutes=5), 7500)[0] - 8750) < 0.01, [room1, room2])
    new2 = {'cash': 90000.0, 'holdings': [hold(i, began + dt.timedelta(hours=1)) for i in range(2)], 'closed': []}
    check('holdings bought after it began count as before: from nothing the first step is one holding', m.already_in(new2, st_) == 0 and abs(m.allowance({'cash': 90000.0, 'holdings': [], 'closed': []}, S10, st_, began + dt.timedelta(minutes=5))[0] - 1250) < 0.01 and m.allowance(new2, S10, st_, began + dt.timedelta(hours=1, minutes=5))[0] == 0)
    sold_one = dict(old6, holdings=old6['holdings'][:5])
    check('when one of the older holdings is sold, its money is paced out with the rest', m.already_in(sold_one, st_) == 6250 and abs(m.allowance(sold_one, S10, st_, began + dt.timedelta(minutes=5))[0] - 1250) < 0.01 and abs(m.allowance(sold_one, S10, st_, began + dt.timedelta(hours=24, minutes=5))[0] - 3750) < 0.01)
    nxt = m.next_release(S10, st_, 8750.0, began + dt.timedelta(minutes=5), 7500.0)
    check('and the note that says when more is released counts the same way', nxt == began + dt.timedelta(hours=12), nxt)     # the rest ($2,500) comes in eighths: a second whole holding is out at the fifth step
# ---- the AI model's notes wait for enough finished trades: a pattern in a handful is chance, and the notes are shown back to it
if NOTES:
    m.LESSONS_MIN = NOTES; was_central = m.CENTRAL; m.CENTRAL = False; MODEL['answer'] = {'lessons': ['Rank 1 to 3 did worse (5 trades).']}; MODEL['prompts'].clear()
    rec = {'settings': dict(m.DEFAULTS), 'state': {'lessons': {'at': m.iso(t0), 'n': 5, 'items': ['RSI around 50 did not perform well.']}}, 'log': [], 'history': [trade(i, -1.0) for i in range(NOTES - 1)]}
    early = m.memory_text(m.scorecard(rec['history']), rec['state']['lessons'])
    check('a note that rests on fewer than 30 trades is not shown to the model', 'RSI around 50' not in early and 'Note from' not in early, early)
    check('nor to the page', m.public(rec, t0, U)['lessons'] is None)
    check('with 29 finished trades no notes are written, the model is not asked, and the early notes are dropped', not m.write_lessons(rec, t0, model) and not MODEL['prompts'] and not rec['state'].get('lessons'))
    n = [c for c in m.coming(dict(rec, settings=dict(m.DEFAULTS, enabled=True, screeners=['3-100']), state=dict(rec['state'], startedAt=m.iso(t0), lastRun=m.iso(t0))), m.new_portfolio(t0), t0 + dt.timedelta(hours=1), []) if c['kind'] == 'notes']
    check('"What happens next" says how many trades the first notes wait for, and why', bool(n) and (n[0]['after'] == 1 and 'waits for 30 finished trades' in n[0]['text']), n)
    rec['history'].append(trade(99, 2.0))
    check('at 30 they are written', m.write_lessons(rec, t0, model) and rec['state']['lessons']['n'] == NOTES and len(MODEL['prompts']) == 1)
    late = m.memory_text(m.scorecard(rec['history']), rec['state']['lessons'])
    check('and shown to the model with the number of trades they rest on', 'Note from the last review (of 30 finished trades): Rank 1 to 3 did worse' in late, late[-200:])
    check('and to the page', m.public(rec, t0, U)['lessons']['items'] == ['Rank 1 to 3 did worse (5 trades).'])
    m.LESSONS_MIN = 5; m.CENTRAL = was_central
# ---- the diary: every activity line, finished trade and change of settings, written once to a table that is never trimmed
if hasattr(m, 'keep_diary'):
    class Diary:                                            # keyed by the account and the time, as the real table is
        def __init__(s): s.rows = {}; s.fail = 0; s.puts = 0
        def put_item(s, Item):
            if s.fail: s.fail -= 1; raise RuntimeError('table away')
            s.puts += 1; s.rows[(Item['userId'], Item['at'])] = copy.deepcopy(Item)
        def of(s, kind): return [json.loads(r['data']) for (u, a), r in sorted(s.rows.items()) if r['kind'] == kind]
    diary = Diary(); D.t[m.DIARY_TABLE] = diary; who = 'diary@x.com'
    note = lambda t, text, **k: dict({'t': t, 'type': 'note', 'symbol': '', 'usd': 0, 'text': text}, **k)
    rec = {'settings': dict(m.DEFAULTS, enabled=True, risk=3, screeners=['3-100']), 'state': {}, 'history': [],
           'log': [note('2026-10-12T00:10:00Z', 'Autopilot on.'), {'t': '2026-10-12T00:40:00Z', 'type': 'buy', 'symbol': 'AAA', 'usd': 1250, 'text': 'Bought AAA.', 'detail': ['why']},
                   {'t': '2026-10-12T00:40:00Z', 'type': 'buy', 'symbol': 'BBB', 'usd': 1250, 'text': 'Bought BBB.'}]}
    m.save_item(who, rec)
    check('the diary gets a row for the settings and one for each line of the activity list, two buys of the same second included', len(diary.of('settings')) == 1 and sorted(e.get('symbol') for e in diary.of('log')) == ['', 'AAA', 'BBB']
          and [e for e in diary.of('log') if e['symbol'] == 'AAA'][0]['detail'] == ['why'] and diary.of('settings')[0]['risk'] == 3, [len(diary.rows), diary.of('log')])
    was = diary.puts; m.save_item(who, rec)
    check('a second save writes nothing again', diary.puts == was and all(e.get('j') == 1 for e in rec['log']) and 'j' not in diary.of('log')[0], diary.puts - was)
    m.add_log(rec, [note('2026-10-12T01:10:00Z', 'Nothing to do (1).', key='pace')], None); m.save_item(who, rec)
    m.add_log(rec, [note('2026-10-12T01:40:00Z', 'Nothing to do (2).', key='pace')], None); m.save_item(who, rec)
    notes = [e for e in diary.of('log') if e.get('key') == 'pace']
    check('a check-in note that is counted again is one row, brought up to date, not two', len(notes) == 1 and notes[0]['n'] == 2 and notes[0]['text'] == 'Nothing to do (2).' and notes[0]['first'] == '2026-10-12T01:10:00Z', notes)
    rec['history'].append(dict(trade(1, -2.0), id='h1', sold='2026-10-12T02:10:00Z')); m.save_item(who, rec)
    check('a finished trade goes in with everything it was bought on', len(diary.of('trade')) == 1 and diary.of('trade')[0]['symbol'] == 'T1' and diary.of('trade')[0]['rank'] == 2 and 'after' not in diary.of('trade')[0] and rec['history'][0]['j'] == 1, diary.of('trade'))
    rec['history'][0]['after'] = 3.5; m.save_item(who, rec)
    check('and is brought up to date, in the same row, when what it did after it was sold is known', len(diary.of('trade')) == 1 and diary.of('trade')[0]['after'] == 3.5 and rec['history'][0]['j'] == 2, diary.of('trade'))
    rec['settings'] = dict(rec['settings'], holdings=20); m.save_item(who, rec)
    check('a change of the settings is a row of its own, so a review knows which settings a trade was made under', sorted(str(x.get('holdings')) for x in diary.of('settings')) == ['20', 'None'], [x.get('holdings') for x in diary.of('settings')])
    diary.fail = 1; rec['log'].append(note('2026-10-12T03:10:00Z', 'A line while the table is away.')); before = len(diary.rows); m.save_item(who, rec)
    saved = json.loads(D.Table(m.SETTINGS_TABLE).rows[who]['data'])
    check('when the diary cannot be written the save still happens, and the line goes with the next save', len(diary.rows) == before and saved['log'][-1]['text'] == 'A line while the table is away.' and 'j' not in rec['log'][-1], len(diary.rows) - before)
    m.save_item(who, rec); check('(it does)', diary.of('log')[-1]['text'] == 'A line while the table is away.' and rec['log'][-1]['j'] == 1)
    for i in range(m.LOG_KEEP + 40): rec['log'].append({'t': m.iso(t0 + dt.timedelta(minutes=i)), 'type': 'buy', 'symbol': f'S{i}', 'usd': 100, 'text': f'Bought S{i}.'})
    m.save_item(who, rec)
    check('the activity list is still cut to its last lines, and the diary keeps every one', len(rec['log']) == m.LOG_KEEP and sum(1 for e in diary.of('log') if str(e.get('symbol')).startswith('S')) == m.LOG_KEEP + 40, [len(rec['log']), len(diary.of('log'))])
    was = diary.puts; m.save_item('_brain', {'settings': {}, 'state': {}, 'log': [note('2026-10-12T00:10:00Z', 'x')], 'history': []}) if False else m.keep_diary('_brain', {'settings': {}, 'state': {}, 'log': [note('2026-10-12T00:10:00Z', 'x')], 'history': []})
    check('the shared record and the stored screener results are no account: nothing of theirs goes in', diary.puts == was)
    code_, b = call(action='get', userId=U); check('the page still gets its activity list as before', code_ == 200 and isinstance(b.get('log'), list))

# --- a scheduled check-in waits until the settings have been left alone for SETTLE_MINUTES (13 Oct 2026): the dashboard
# saves every click, and a check-in once traded on a quick set-up the owner was in the middle of clicking through
D.t.clear(); m._BRAIN.clear(); m.PLAN_CACHE.clear(); PRICES.clear(); MODEL['answer'] = None; SNAP.clear(); SNAP.update({'7-1': rows('crypto', '7-1')})
ts = dt.datetime(2026, 10, 14, 12, 40, 0)
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=0.5, maxHoldDays=5, screeners=['7-1'], selfTune=False, aiSell=False, auto=[])
rec['state']['startedAt'] = m.iso(ts - dt.timedelta(days=2)); rec['state']['savedAt'] = m.iso(ts - dt.timedelta(minutes=3)); rec['state']['visit'] = m.iso(ts); m.save_item(U, rec)
check('settings changed 3 minutes ago are still settling; 10 minutes ago, before they were saved, or never saved, they are not',
      m.settling(rec, ts) and not m.settling(rec, ts + dt.timedelta(minutes=7)) and not m.settling(rec, ts - dt.timedelta(minutes=5)) and not m.settling({'state': {}}, ts), rec['state']['savedAt'])
held_n = lambda: len((portfolio() or {}).get('holdings', []))
before = m.datetime; m.datetime = at(ts); r1 = json.loads(m.lambda_handler({'source': 'aws.events'}, None)['body']); held1 = held_n()
nxt = m.next_check(m.load_item(U), ts - dt.timedelta(minutes=2))
code_, b = call(action='run', userId=U); held_by_hand = held_n()
check('a scheduled check-in leaves such an account alone, and the page is told the check-in after it', r1['ran'] == [] and held1 == 0 and nxt and nxt['at'] == m.iso(ts + dt.timedelta(minutes=30)), [r1, held1, nxt])
check('"Check in now" does not wait: it is a request to act on the settings as they are', code_ == 200 and held_by_hand > 0, [code_, held_by_hand, (b.get('summary') or {}).get('why')])
D.t.clear(); m._BRAIN.clear(); PRICES.clear()
rec = m.load_item(U); rec['settings'].update(enabled=True, risk=3, budgetUsd=8000.0, periodDays=1, everyHours=0.5, maxHoldDays=5, screeners=['7-1'], selfTune=False, aiSell=False, auto=[])
rec['state']['startedAt'] = m.iso(ts - dt.timedelta(days=2)); rec['state']['savedAt'] = m.iso(ts - dt.timedelta(minutes=3)); rec['state']['visit'] = m.iso(ts); m.save_item(U, rec)
m.datetime = at(ts); ra = json.loads(m.lambda_handler({'source': 'aws.events'}, None)['body'])
m.datetime = at(ts + dt.timedelta(minutes=30)); rb = json.loads(m.lambda_handler({'source': 'aws.events'}, None)['body']); m.datetime = before
check('half an hour later, the settings left alone, the schedule checks in as usual', ra['ran'] == [] and len(rb['ran']) == 1 and rb['ran'][0]['bought'] > 0 and held_n() > 0, [ra, rb])

# --- a market whose every ticked screener is resting gets no share of the budget (17 Oct 2026: the rested coin screener had held a fifth back as cash)
import inspect
if 'resting' in inspect.signature(m.market_slots).parameters:
    D.t.clear(); m._BRAIN.clear(); m.PLAN_CACHE.clear(); PRICES.clear(); MODEL['answer'] = None; SNAP.clear(); SNAP.update({'3-100': rows(n=40)})
    before, central = m.datetime, m.CENTRAL; m.datetime = at(t0); m.CENTRAL = False      # the account's own rests (with shared learning they come from the shared record)
    base = dict(m.DEFAULTS, enabled=True, risk=3, budgetUsd=4000.0, periodDays=1, everyHours=24, maxHoldDays=5, screeners=['3-100', '7-1'], selfTune=False, aiSell=False, auto=[], holdings=4)
    check('with nothing resting, coins keep their part (1 of 4 holdings at Balanced); with the coin screener resting the shares get all four',
          m.market_slots(base) == {'US markets': 3, 'Coins': 1} and m.market_slots(base, {'7-1': '2026-10-29T00:00:00Z'}) == {'US markets': 4}
          and m.coin_share(base, {'7-1': 'x'}) == 0 and m.market_slots(base, {'3-100': 'x', '7-1': 'x'}) == {}, [m.market_slots(base), m.market_slots(base, {'7-1': 'x'})])
    check('a market with one of two screeners resting keeps its share', m.market_slots(dict(base, screeners=['3-100', '3-3', '7-1']), {'3-100': 'x'}) == {'US markets': 3, 'Coins': 1})
    rec = m.load_item(U); rec['settings'].update(base); rec['state']['startedAt'] = m.iso(t0 - dt.timedelta(days=2)); rec['state']['rest'] = {'7-1': m.iso(t0 + dt.timedelta(days=12))}; m.save_item(U, rec)
    s1, rec = run(t0); s2, rec = run(t0 + dt.timedelta(days=1)); held4 = portfolio()['holdings']
    check('two check-ins with the coin screener resting fill all four holdings with shares, none kept back for coins', len(held4) == 4 and all(not h['symbol'].endswith('-USD') for h in held4), [s1.get('bought'), s2.get('bought'), [h['symbol'] for h in held4]])
    code_, b = call(action='get', userId=U)
    check('the page is told the split without the resting market', code_ == 200 and [x['group'] for x in b['split']] == ['US markets'] and b['split'][0]['holdings'] == 4, b.get('split'))
    words = m.resting_words(base, {'7-1': m.iso(t0 + dt.timedelta(days=12))})
    check('the check-in note says that the resting market gets no share for now, and until when', 'Coins get no share for now: its screener is resting until 24 Oct' in words, words)
    m.datetime, m.CENTRAL = before, central

# --- the owner's Admin page (17 Oct 2026): the site's own accounts only; a weekly review written by the function; proposals
D.t.clear(); m._BRAIN.clear(); m.PLAN_CACHE.clear(); PRICES.clear(); MODEL['answer'] = None
ta = dt.datetime(2026, 10, 17, 9, 0, 0); before = m.datetime; m.datetime = at(ta)
code_, b = call(action='admin', userId='someone@else.com')
check('the Admin page is refused to an account that is not one of the site\'s own', code_ == 403 and not b['success'])
code_, b = call(action='admin', userId=U)
check('for the site\'s own account it answers with the goal, no review yet and nothing to answer', code_ == 200 and b['admin']['goal']['name'] == 'Month 1: in profit' and b['admin']['goal']['tradesGoal'] == 100 and b['admin']['review'] is None and b['admin']['open'] == [], b.get('admin', {}).get('goal'))
rec = m.load_item(U); rec['settings'].update(enabled=True, aiSell=True, screeners=['3-100', '5-dax40'])
rec['history'] = [dict(pct=-1.5 + (i % 3) * 0.1, usd=-15.0, exit='ai', screener='3-100', sold=m.iso(ta - dt.timedelta(days=1 + i % 6)), c=1) for i in range(32)] + [dict(pct=1.0, usd=10.0, exit='trail', screener='5-dax40', sold=m.iso(ta - dt.timedelta(days=2)), c=1) for i in range(5)]
rec['state']['closedCount'] = 37; m.save_item(U, rec)
code_, b = call(action='admin', userId=U, op='review'); adm = b['admin']; opens = {p['key']: p for p in adm['open']}
check('a review written on request names the losing groups and proposes switching off the AI review\'s sales and unticking the losing screener', code_ == 200 and adm['review'] and any('Clearly losing: sales by the AI review, 32 trades' in l for l in adm['review']['lines']) and 'aiSell-off' in opens and opens['aiSell-off']['kind'] == 'setting' and 'untick-3-100' in opens and 'untick-5-dax40' not in opens, [adm['review']['lines'] if adm.get('review') else None, list(opens)])
code_, b = call(action='admin', userId=U, op='review')
check('writing the review again does not propose the same thing twice', len([p for p in b['admin']['open'] if p['key'] == 'aiSell-off']) == 1)
code_, b = call(action='admin', userId=U, op='answer', id=opens['aiSell-off']['id'], answer='yes'); rec = m.load_item(U)
check('"Yes" to a setting applies it at once, notes it in the activity list and says it was done', code_ == 200 and rec['settings']['aiSell'] is False and any('Changed from the Admin page' in e['text'] for e in rec['log']) and any(p['key'] == 'aiSell-off' and p['status'] == 'done' for p in b['admin']['answered']) and m.settling(rec, ta), rec['settings'].get('aiSell'))
code_, b = call(action='admin', userId=U, op='answer', id=opens['untick-3-100']['id'], answer='no'); rec = m.load_item(U)
check('"Not now" changes nothing and is kept as answered', code_ == 200 and '3-100' in rec['settings']['screeners'] and any(p['key'] == 'untick-3-100' and p['status'] == 'no' for p in b['admin']['answered']))
code_, b = call(action='admin', userId=U, op='answer', id=opens['untick-3-100']['id'], answer='yes')
check('a proposal already answered cannot be answered again', code_ == 400)
m.save_admin(dict(m.load_admin(), review=None)); rec = m.load_item(U); rec['state']['savedAt'] = m.iso(ta - dt.timedelta(hours=2)); rec['state']['visit'] = m.iso(ta); m.save_item(U, rec)
m.datetime = at(ta + dt.timedelta(minutes=10)); m.lambda_handler({'source': 'aws.events'}, None); adm1 = m.load_admin()
m.datetime = at(ta + dt.timedelta(minutes=40)); m.lambda_handler({'source': 'aws.events'}, None); adm2 = m.load_admin(); m.datetime = before
check('the scheduled run records how it went every time and writes the review itself once a week', adm1['health'] and adm1['health']['on'] >= 1 and adm1['review'] and adm2['review']['at'] == adm1['review']['at'] and adm2['health']['at'] > adm1['health']['at'], [adm1.get('health'), (adm1.get('review') or {}).get('at'), (adm2.get('review') or {}).get('at')])

# --- 17 Oct 2026: the Admin page's account value at the latest prices, and the S&P 500 fund since the start in the review
pf = {'cash': 1000.0, 'startingCash': 100000, 'createdAt': '2026-10-10T09:18:42Z', 'holdings': [
    {'id': 'a', 'symbol': 'AAA', 'currency': 'USD', 'qty': 10, 'costUsd': 500.0},
    {'id': 'b', 'symbol': 'TSCO.L', 'currency': 'GBp', 'qty': 100, 'costUsd': 600.0},
    {'id': 'c', 'symbol': 'NOPRICE', 'currency': 'USD', 'qty': 1, 'costUsd': 300.0}]}
rec_v = {'state': {'open': {'c': {'path': [[1, 10.0]]}}}}
quotes_v = {'AAA': {'price': 60.0, 'currency': 'USD'}, 'TSCO.L': {'price': 500.0, 'currency': 'GBp'}, 'GBPUSD=X': {'price': 1.30, 'currency': 'USD'}}
v_live = m.account_value(pf, rec_v, lambda sym: quotes_v.get(sym))
check('the account value with prices: each holding at its latest price in dollars (pence and the pound rate too), one with no price at its estimate', abs(v_live - (1000 + 600 + 100 * 500 / 100 * 1.30 + 330)) < 0.01, v_live)
check('the account value without prices: the old estimate, as before', abs(m.account_value(pf, rec_v) - (1000 + 500 + 600 + 330)) < 0.01, m.account_value(pf, rec_v))
t0 = (dt.datetime(2026, 10, 9, 20) - dt.datetime(1970, 1, 1)).total_seconds()
old_http = m.http_json
m.http_json = lambda url, payload=None, timeout=120: {'chart': {'result': [{'meta': {'regularMarketPrice': 763.25}, 'timestamp': [t0 - 86400, t0, t0 + 3 * 86400], 'indicators': {'quote': [{'close': [770.0, 778.57, 760.0]}]}}]}}
fs = m.fund_since_start(pf, 99643.23, dt.datetime(2026, 10, 17, 6))
check('the fund since the start: the starting cash in SPY from the last close at or before the account began, and the account less it', fs and abs(fs[0] - 100000 * 763.25 / 778.57) < 0.01 and abs(fs[1] - (99643.23 - fs[0])) < 0.01, fs)
adm_t = {'proposals': [], 'review': None, 'health': None, 'seq': 0}
rec_t = m.load_item(U); m.write_review(adm_t, rec_t, pf, dt.datetime(2026, 10, 17, 6), quote=lambda sym: quotes_v.get(sym))
check('the weekly review says how the account stands against the same money in an S&P 500 fund since it began', any(l.startswith('Against the same $100,000 in an S&P 500 fund since the account began: the fund would be $98,032, so the account is') for l in adm_t['review']['lines']), adm_t['review']['lines'][-2:])
adm_t2 = {'proposals': [], 'review': None, 'health': None, 'seq': 0}; m.write_review(adm_t2, rec_t, pf, dt.datetime(2026, 10, 17, 6))
check('without a price lookup (a test, or off the function) no prices are asked for and the line is left out', not any('S&P 500 fund since' in l for l in adm_t2['review']['lines']))
m.http_json = old_http
print('ALL PASS' if ok else 'SOME FAILED')
