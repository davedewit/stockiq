"""The crypto worker before and after the clean-up, on recorded answers of the price source. Nothing live is called.
    python3 worker_test.py <old lambda_function.py> <new lambda_function.py> <recorded.txt>
recorded.txt: Yahoo's own answers for ten coins on 11 Oct 2026, both the 30-day and the 90-day request the old code made."""
import sys, os, io, json, copy, contextlib, importlib.util, time
passed = failed = 0
def check(name, ok, detail=''):
    global passed, failed
    if ok: passed += 1; print('PASS', name)
    else: failed += 1; print('FAIL', name, '|', str(detail)[:300])
REC = json.load(open(sys.argv[3])); END = REC['end']
COINS = sorted({k.split(':')[0] for k, v in REC['answers'].items() if 'chart' in v})
state = {'calls': [], 'answers': REC['answers']}
class Resp:
    def __init__(self, body): self.body = body; self.status_code = 200 if body and 'chart' in body else 404
    def json(self): return copy.deepcopy(self.body)
def fake_get(url, params=None, headers=None, timeout=None):
    sym = url.split('/chart/')[1].replace('-USD', ''); days = round((params['period2'] - params['period1']) / 86400)
    state['calls'].append((sym, days)); return Resp(state['answers'].get(f'{sym}:{days}'))
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); mod = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(mod)
    mod.requests.get = fake_get; return mod
real_time = time.time; time.time = lambda: END
old = load('worker_old', sys.argv[1]); new = load('worker_new', sys.argv[2])
old.requests.get = fake_get
def one(mod, sym):
    state['calls'].clear()
    with contextlib.redirect_stdout(io.StringIO()):
        return mod.CryptoAnalytics().analyze_coin(sym, {}), list(state['calls'])
def ask(mod, body):
    with contextlib.redirect_stdout(io.StringIO()):
        r = mod.lambda_handler({'body': json.dumps(body)} if body is not None else {}, None)
    return r['statusCode'], json.loads(r['body'])

print('== the same answer for every recorded coin, from one request where there were two')
for sym in COINS:
    a, ca = one(old, sym); b, cb = one(new, sym)
    diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    check(f'{sym}: every figure the same ({len(a)} fields, score {a["score"]:+d})', not diff, [(k, a.get(k), b.get(k)) for k in diff][:3])
    check(f'{sym}: one request, not two', len(ca) == 2 and len(cb) == 1 and cb[0][1] == 90, (ca, cb))
a, _ = one(old, 'NOSUCH'); b, _ = one(new, 'NOSUCH')
check('a coin the price source does not know: the same "no data" answer', a == b and b['price'] == 0 and b['score'] == 0, (a.get('score_breakdown'), b.get('score_breakdown')))

print('== a day\'s figures stay together')
gap = copy.deepcopy(REC['answers']['BTC:90']); q = gap['chart']['result'][0]['indicators']['quote'][0]
q['volume'][-5] = None; q['high'][-9] = None
state['answers'] = dict(REC['answers'], **{'GAP:90': gap, 'GAP:30': REC['answers']['BTC:30']})
bars = new.CryptoAnalytics().fetch_bars('GAP'); full = new.CryptoAnalytics().fetch_bars('BTC')
check('a missing volume or high does not shift the other days', len(bars) == len(full) and [x['close'] for x in bars] == [x['close'] for x in full] and bars[-5]['volume'] == 0 and bars[-9]['high'] == bars[-9]['close'] and bars[-1] == full[-1])
closed = copy.deepcopy(REC['answers']['BTC:90']); closed['chart']['result'][0]['indicators']['quote'][0]['close'][-3] = None
state['answers'] = dict(REC['answers'], **{'GAP2:90': closed})
bars2 = new.CryptoAnalytics().fetch_bars('GAP2')
check('a day without a closing price is left out whole', len(bars2) == len(full) - 1 and all(x['close'] is not None for x in bars2) and [x['timestamp'] for x in bars2] == [x['timestamp'] for x in full if x['timestamp'] != full[-3]['timestamp']])
state['answers'] = REC['answers']

print('== the three ways of calling it')
code, out = ask(new, {'coin_list': ['btc', 'NOSUCH', 'ETH']}); code_old, out_old = ask(old, {'coin_list': ['btc', 'NOSUCH', 'ETH']})
check('a list of coins: answered as before the clean-up', code == 200 and out['results'] == out_old['results'] and [r['ticker'] for r in out['results']] == ['BTC', 'NOSUCH', 'ETH'])
code, out = ask(new, {'single_coin': 'eth'}); code_old, out_old = ask(old, {'single_coin': 'eth'})
check('a single coin: answered as before the clean-up', code == 200 and out['coins'] == out_old['coins'])
state['calls'].clear(); code, out = ask(new, {}); code2, out2 = ask(new, None)
check('no coin at all: says so, and asks the price source nothing', code == 400 and code2 == 400 and out['coins'] == [] and state['calls'] == [], (code, code2, state['calls']))
src = open(sys.argv[2]).read()
check('the old list, the report writer and the database are gone', all(word not in src for word in ('target_coins', 'generate_report', 'check_prediction_status', 'boto3', 'coinspot.com')))
time.time = real_time
print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
