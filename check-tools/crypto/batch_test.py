"""The crypto job, one coin a call (the code that was live) against ten coins a call (the new code). Nothing live is called.
    python3 batch_test.py <old orchestrator.py> <new orchestrator.py> <old worker lambda_function.py> <new worker lambda_function.py> <a real coin analysis.json>
A stand-in plays the 54 worker functions: every coin gets the same made-up analysis under either way of asking, some
coins cannot be analysed, one worker function is down. The two orchestrators must then rank exactly the same."""
import sys, os, io, json, re, copy, hashlib, contextlib, importlib.util, urllib.request, urllib.error
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
passed = failed = 0
def check(name, ok, detail=''):
    global passed, failed
    if ok: passed += 1; print('PASS', name)
    else: failed += 1; print('FAIL', name, '|', str(detail)[:300])
TEMPLATE = json.load(open(sys.argv[5]))['coins'][0]
state = {'calls': [], 'dead': set(), 'unknown': {'ZEC', 'ONDO', 'KAS'}, 'flaky': {}}

def analysis(ticker):
    """A made-up analysis that depends only on the ticker"""
    n = int(hashlib.sha256(ticker.encode()).hexdigest(), 16)
    c = copy.deepcopy(TEMPLATE)
    c.update(symbol=ticker, price=round(0.5 + (n % 100000) / 37.0, 4), score=(n % 15) - 6, change_24h=((n >> 8) % 400) / 10 - 20, change_7d=((n >> 16) % 600) / 10 - 30,
             change_30d=((n >> 24) % 900) / 10 - 45, rsi=20 + (n >> 4) % 60, atr=1 + (n % 7))
    return c

class Answer:
    def __init__(self, body): self.body = json.dumps(body).encode()
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return self.body
def worker(req, timeout=None):
    url = req.full_url; body = json.loads(req.data.decode()); state['calls'].append((url, body))
    if url in state['dead']: raise urllib.error.HTTPError(url, 403, 'Forbidden', None, None)
    def one(ticker):
        if ticker in state['unknown']: return None
        if state['flaky'].get(ticker, 0) > 0: state['flaky'][ticker] -= 1; return None
        return analysis(ticker)
    if 'coin_list' in body:
        return Answer({'results': [{'ticker': t.upper(), 'coin': one(t.upper())} for t in body['coin_list']], 'status': 'success', 'analysis_type': 'coin_list'})
    coin = one(body['single_coin'].upper())
    if not coin: raise urllib.error.HTTPError(url, 500, 'Failed to analyze', None, None)
    return Answer({'coins': [coin], 'status': 'success', 'analysis_type': 'single_coin'})

class Table:
    def get_item(self, **k): return {}
    def scan(self, **k): return {'Items': []}
    def query(self, **k): return {'Items': []}
    def put_item(self, **k): raise RuntimeError('a user run must not write')
    def update_item(self, **k): raise RuntimeError('a user run must not write')
    def batch_get_item(self, **k): return {'Responses': {}}
class Dynamo:
    def Table(self, name): return Table()
    def batch_get_item(self, **k): return {'Responses': {}}
class Boto:
    def resource(self, *a, **k): return Dynamo()
    def client(self, *a, **k): return Dynamo()

def load(name, path):
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    spec = importlib.util.spec_from_file_location(name, path); mod = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(mod)
    sys.path.pop(0); return mod
def run(mod):
    state['calls'].clear(); mod.boto3 = Boto()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        r = mod.lambda_handler({'requestContext': {}, 'body': '{}'}, None)
    return json.loads(r['body']), out.getvalue()
real = urllib.request.urlopen; urllib.request.urlopen = worker
old = load('orch_old', sys.argv[1]); new = load('orch_new', sys.argv[2])
picture = lambda d: [(c['symbol'], c.get('yahoo_ticker'), c['score'], c['price']) for c in d['coins']]
strip = lambda text: re.sub(r'\d{1,2}:\d\d(:\d\d)?( UTC)?|\d+\.\d+ ?s\b|\d{4}-\d\d-\d\d|\d{1,2} [A-Z][a-z]{2}', '', text)

print('== the same ranking, in a tenth of the calls')
a, _ = run(old); calls_old = len(state['calls'])
b, log = run(new); calls_new = len(state['calls']); sent = [c for c in state['calls']]
check('the old way: one call a coin (with a second try for the three that cannot be analysed)', calls_old == 543, calls_old)
check('the new way: one call for every ten coins (and one more for the three)', calls_new == 55, calls_new)
check('every call carries at most ten coins, and no coin is asked for twice in the first round', all(len(body['coin_list']) <= 10 for _, body in sent) and len({t for _, body in sent[:54] for t in body['coin_list']}) == 540)
check('the 54 batches go to 54 different worker functions', len({url for url, _ in sent[:54]}) == 54)
check('the same coins come back, in the same order, with the same scores', picture(a) == picture(b) and len(b['coins']) > 500, (len(a['coins']), len(b['coins'])))
check('the report text is the same', strip(a['report']) == strip(b['report']), [x for x, y in zip(strip(a['report']).split('\n'), strip(b['report']).split('\n')) if x != y][:2])
check('each coin carries the symbol shown and the ticker it was priced by', all(c.get('yahoo_ticker') for c in b['coins']) and any(c['symbol'] != c['yahoo_ticker'] for c in b['coins']))
check('the three that cannot be analysed are simply not in the list', not {'ZEC', 'ONDO', 'KAS'} & {c['symbol'] for c in b['coins']})

print('== when things go wrong')
first_url = sent[0][0]; state['dead'] = {first_url}
c, _ = run(new); state['dead'] = set()
check('a worker function that is down: its batch goes to the next one, nothing is lost', picture(c) == picture(b), (len(c['coins']), len(b['coins'])))
state['flaky'] = {'ETH': 1, 'SOL': 1}
d, log2 = run(new)
check('a coin that fails once is asked for again and comes back', picture(d) == picture(b) and 'asked for a second time' in log2, len(d['coins']))
state['unknown'] = set(); e, _ = run(new); state['unknown'] = {'ZEC', 'ONDO', 'KAS'}
check('with every coin answering there is no second round: 54 calls', len(state['calls']) == 54 and len(e['coins']) >= len(b['coins']), len(state['calls']))

print('== the worker')
wold = load('worker_old', sys.argv[3]); wnew = load('worker_new', sys.argv[4])
for m in (wold, wnew):
    m.CryptoAnalytics.__init__ = lambda self: None
    def fake(self, symbol, price_data):
        if symbol == 'BOOM': raise RuntimeError('boom')
        return None if symbol == 'NONE' else analysis(symbol)
    m.CryptoAnalytics.analyze_coin = fake
def ask(m, body):
    with contextlib.redirect_stdout(io.StringIO()):
        r = m.lambda_handler({'body': json.dumps(body)}, None)
    return r['statusCode'], json.loads(r['body'])
code, out = ask(wnew, {'coin_list': ['btc', 'NONE', 'BOOM', 'SUI20947']})
check('a list of coins: one answer for each, in order, None for one that cannot be analysed or fails', code == 200 and [r['ticker'] for r in out['results']] == ['BTC', 'NONE', 'BOOM', 'SUI20947'] and [bool(r['coin']) for r in out['results']] == [True, False, False, True], out.get('results') and [(r['ticker'], bool(r['coin'])) for r in out['results']])
check('each coin\'s analysis is the one the single-coin mode gives', out['results'][0]['coin'] == ask(wnew, {'single_coin': 'BTC'})[1]['coins'][0] == ask(wold, {'single_coin': 'BTC'})[1]['coins'][0])
check('single-coin mode answers as before (the page\'s single-coin analysis and older callers)', ask(wnew, {'single_coin': 'eth'}) [1]['coins'][0] == ask(wold, {'single_coin': 'eth'})[1]['coins'][0] and ask(wnew, {'single_coin': 'NONE'})[0] == 500)
check('at most 25 coins a call', len(ask(wnew, {'coin_list': ['C%d' % i for i in range(40)]})[1]['results']) == 25)
try:
    knows = 'results' in ask(wold, {'coin_list': ['BTC']})[1]
except Exception:
    knows = False          # it falls through to its own built-in list, which this stand-in does not have
check('the old worker does not know the new mode (so the workers are deployed before the orchestrator)', not knows)
urllib.request.urlopen = real
print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
