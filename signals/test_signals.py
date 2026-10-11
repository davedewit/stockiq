"""The trading-signals functions on saved prices, beside the two files they replaced. Nothing live is called.
    python3 signals/test_signals.py [--show]
Prices: workers/data/sample.json (Yahoo's own answers for ASX, London, Tokyo and NASDAQ shares) and
check-tools/paper-test/data/prices.json (the S&P 100). The old files: unzip
~/VSCODE/backup/stockiq-option-2-trading-signals_before_onefile_20261011.zip (kept by the deploy of 11 Oct 2026)."""
import sys, os, io, json, glob, contextlib, importlib.util, urllib.request, urllib.parse, urllib.error, time, re, zipfile, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SAMPLE = json.load(open(os.path.join(ROOT, 'workers', 'data', 'sample.json')))
US = json.load(open(os.path.join(ROOT, 'check-tools', 'paper-test', 'data', 'prices.json')))
passed = failed = 0
def check(name, ok, detail=''):
    global passed, failed
    if ok: passed += 1; print('PASS', name)
    else: failed += 1; print('FAIL', name, '|', str(detail)[:300])

state = {'refuse': set(), 'refuse_once': set(), 'calls': []}
def chart_for(symbol):
    if symbol in SAMPLE:
        c = SAMPLE[symbol]; ts = c['timestamp']; q = c['indicators']['quote'][0]; keep = [i for i, t in enumerate(ts) if t >= ts[-1] - 365 * 86400]
        return {'meta': dict(c['meta']), 'timestamp': [ts[i] for i in keep], 'indicators': {'quote': [{k: [q[k][i] for i in keep] for k in ('open', 'high', 'low', 'close', 'volume')}]}}
    if symbol in US:
        rows = US[symbol][-252:]
        return {'meta': {'currency': 'USD', 'gmtoffset': -14400, 'shortName': symbol + ' Inc.'}, 'timestamp': [r[0] for r in rows],
                'indicators': {'quote': [{k: [r[i + 1] for r in rows] for i, k in enumerate(['open', 'high', 'low', 'close', 'volume'])}]}}
    return None
class Answer:
    def __init__(self, body): self.body = json.dumps(body).encode()
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return self.body
def fake_urlopen(req, timeout=None):
    url = req.full_url if hasattr(req, 'full_url') else req
    symbol = urllib.parse.unquote(url.split('/chart/')[1].split('?')[0]); state['calls'].append(symbol)
    if symbol in state['refuse']: raise urllib.error.HTTPError(url, 429, 'Too Many Requests', None, None)
    if symbol in state['refuse_once']: state['refuse_once'].discard(symbol); raise urllib.error.HTTPError(url, 429, 'Too Many Requests', None, None)
    c = chart_for(symbol)
    if not c: raise urllib.error.HTTPError(url, 404, 'Not Found', None, None)
    return Answer({'chart': {'result': [c]}})
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); mod = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(mod)
    return mod
real = urllib.request.urlopen, time.sleep
urllib.request.urlopen = fake_urlopen; time.sleep = lambda s: None
new = load('signals_new', os.path.join(HERE, 'lambda_function.py'))
class Ctx:
    def __init__(self, name): self.function_name = name
def call(mod, name, body):
    with contextlib.redirect_stdout(io.StringIO()):
        r = mod.lambda_handler({'body': json.dumps(body)}, Ctx(name))
    return r['statusCode'], json.loads(r['body'])

print('== "Enter Symbols for Live Signals"')
code, d = call(new, 'stockiq-option-2-trading-signals', {'symbols': ['crwd', 'BHP.AX', 'IMB.L', '7203.T', 'NOSUCH', 'CRWD']})
sig = {s['symbol']: s for s in d['signals']}
check('answers, one reading per symbol found, a repeated symbol once', code == 200 and d['symbols_analyzed'] == 4 and list(sig) == ['CRWD', 'BHP.AX', 'IMB.L', '7203.T'], (code, list(sig)))
check('a symbol with no prices is named, not silently dropped', d['not_found'] == ['NOSUCH'], d.get('not_found'))
check('each reading says what currency its prices are in', [sig[s]['currency'] for s in sig] == ['USD', 'AUD', 'GBp', 'JPY'], [sig[s]['currency'] for s in sig])
check('and carries the company\'s name', sig['BHP.AX']['name'].startswith('BHP') and sig['IMB.L']['name'].startswith('Imperial'), (sig['BHP.AX']['name'], sig['IMB.L']['name']))
check('the time is marked as UTC, so a browser shows it in the visitor\'s own time', re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', d['timestamp']) is not None, d['timestamp'])
check('every field the page already reads is still there', all(k in sig['CRWD'] for k in ('symbol', 'current_price', 'action', 'confidence', 'entry_price', 'stop_loss', 'take_profit', 'stop_loss_pct', 'take_profit_pct', 'rsi', 'support', 'resistance', 'signals', 'signal_strength')))
check('the codes are the ones the page has labels for', all(s['action'] in ('BUY', 'SELL', 'HOLD') and s['confidence'] in ('HIGH', 'MEDIUM', 'LOW') for s in sig.values()))
for s in sig.values():
    pts = [int(m.group(1)) for r in s['reasons'] for m in [re.search(r': ([+-]\d+)$', r)] if m]
    check(f"{s['symbol']}: the reasons add up to the reading", sum(pts) == s['signal_strength'] and len(s['reasons']) >= 2, (s['reasons'], s['signal_strength']))
    want = 'BUY' if s['signal_strength'] >= 2 else 'SELL' if s['signal_strength'] <= -2 else 'HOLD'
    check(f"{s['symbol']}: the code follows the reading", s['action'] == want and s['confidence'] == ('LOW' if want == 'HOLD' else 'HIGH' if abs(s['signal_strength']) >= 3 else 'MEDIUM'), (s['action'], s['confidence'], s['signal_strength']))
    hi, lo = max(s['take_profit'], s['stop_loss']), min(s['take_profit'], s['stop_loss'])
    check(f"{s['symbol']}: the levels are the last 20 sessions' high and low, either side of the price", abs(hi - s['resistance']) < 1e-9 and abs(lo - s['support']) < 1e-9 and lo <= s['current_price'] <= hi and (s['take_profit'] < s['stop_loss']) == (s['action'] == 'SELL'), (lo, s['current_price'], hi))
    bad = [r for r in s['reasons'] + [s['trend']] if re.search(r'\b(buy|sell|target|stop loss|take profit|recommend|opportunit|picks?)\b', r, re.I)]
    check(f"{s['symbol']}: describes, does not advise", not bad, bad)
check('ASX: one bar a day (the day\'s change is real, not 0)', abs(sig['BHP.AX']['change_pct'] - (-0.41)) < 0.02, sig['BHP.AX']['change_pct'])
check('London: the price in pence, as the source gives it', abs(sig['IMB.L']['current_price'] - 2662.0) < 0.01)
code, d0 = call(new, 'stockiq-option-2-trading-signals', {})
check('no symbols sent: the five defaults', code == 200 and [s['symbol'] for s in d0['signals']] == ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'TSLA'], [s['symbol'] for s in d0['signals']])
code, d10 = call(new, 'stockiq-option-2-trading-signals', {'symbols': sorted(US)[:14]})
check('at most ten symbols a call', d10['symbols_analyzed'] == 10)
state['refuse_once'] = {'CRWD'}; code, dr = call(new, 'stockiq-option-2-trading-signals', {'symbols': ['CRWD']})
check('a refusal from the price source is tried once more', dr['symbols_analyzed'] == 1)

print('== the same RSI and the same trend words as the rest of the site')
worker = load('worker', os.path.join(ROOT, 'workers', 'stock_worker.py'))
report_path = os.path.join(ROOT, 'lambda-sync', 'stockiq-option-1-1-custom-analysis', 'lambda_function2.py')
for symbol in ('CRWD', 'BHP.AX', 'IMB.L'):
    closes = [b['close'] for b in new.bars_from_chart(chart_for(symbol))[0]]
    check(f'{symbol}: RSI is the screeners\' RSI', abs(new.calculate_rsi(closes) - worker.calculate_rsi(closes)) < 1e-9 and abs(sig[symbol]['rsi'] - worker.calculate_rsi(closes)) < 1e-9)
if os.path.exists(report_path):
    os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
    with contextlib.redirect_stderr(io.StringIO()): report = load('report', report_path)
    cases = [(100.4, 100, 96), (99.97, 100, 103), (95, 100, 104), (100, 100, 100)]
    check('the trend line is the single-stock report\'s, word for word', all(new.trend_words(*c) == report.trend_points(*c)[2] for c in cases), [(new.trend_words(*c), report.trend_points(*c)[2]) for c in cases])

print('== "Auto-detect Top 5 Signals"')
state['calls'].clear(); code, a = call(new, 'stockiq-option-2-2-auto-signals', {})
listed = open(os.path.join(HERE, 'sp100.txt')).read().split()
check('scans the whole S&P 100 list, each share once', code == 200 and sorted(state['calls']) == sorted(listed) and a['scanned'] == len(listed) == a['universe_size'] and a['universe'] == 'S&P 100', (len(state['calls']), a.get('scanned')))
check('gives five readings, and names them where the page looks', a['symbols_analyzed'] == 5 and a['top_performers'] == [s['symbol'] for s in a['signals']], a['top_performers'])
with contextlib.redirect_stdout(io.StringIO()): everything = [new.read_signal(s) for s in listed]
strongest = sorted((abs(s['signal_strength']) for s in everything if s), reverse=True)[:5]
check('they are the five strongest readings of the list, strongest first, either direction', [abs(s['signal_strength']) for s in a['signals']] == strongest, ([s['signal_strength'] for s in a['signals']], strongest))
check('the count of readings covers every share scanned', sum(a['readings'].values()) == a['scanned'], a['readings'])
check('the description says what was done, and does not call them top performers', 'Scanned 101 of the 101 S&P 100 shares' in a['methodology'] and 'strongest readings, in either direction' in a['methodology'] and 'perform' not in a['methodology'].lower(), a['methodology'])
state['refuse'] = set(listed[:40]); code, part = call(new, 'stockiq-option-2-2-auto-signals', {}); state['refuse'] = set()
check('when the price source refuses part of the list, it says how many it scanned', part['scanned'] == 61 and 'Scanned 61 of the 101' in part['methodology'] and part['symbols_analyzed'] == 5, (part['scanned'], part['methodology'][:60]))
state['refuse'] = set(listed); code, none = call(new, 'stockiq-option-2-2-auto-signals', {}); state['refuse'] = set()
check('when it refuses everything: an answer with no readings, not a failure', code == 200 and none['signals'] == [] and none['top_performers'] == [] and none['scanned'] == 0, (code, none.get('scanned')))
code, same = call(new, 'stockiq-option-2-2-auto-signals', {})
check('the same prices give the same five', same['top_performers'] == a['top_performers'])

print('== beside the files it replaces (when they are at hand)')
olds = {}
for name in ('stockiq-option-2-trading-signals', 'stockiq-option-2-2-auto-signals'):
    path = os.path.join(os.path.expanduser('~/VSCODE/backup'), name + '_before_onefile_20261011.zip')
    live = os.path.join(ROOT, 'lambda-sync', name, 'lambda_function.py')
    if os.path.exists(path):
        d = tempfile.mkdtemp(); zipfile.ZipFile(path).extractall(d); olds[name] = load('old_' + name[-12:].replace('-', '_'), os.path.join(d, 'lambda_function.py'))
    elif os.path.exists(live) and 'ONE file for both buttons' not in open(live).read():
        olds[name] = load('old_' + name[-12:].replace('-', '_'), live)
if len(olds) == 2:
    code, o = call(olds['stockiq-option-2-trading-signals'], 'stockiq-option-2-trading-signals', {'symbols': ['CRWD', 'BHP.AX', 'IMB.L', '7203.T']})
    osig = {s['symbol']: s for s in o['signals']}
    check('(the old code: no currency, no reasons the page could print, a time with no zone)', 'currency' not in osig['CRWD'] and 'reasons' not in osig['CRWD'] and not o['timestamp'].endswith('Z'))
    moved = [(s, osig[s]['action'], sig[s]['action'], round(osig[s]['rsi'], 1), round(sig[s]['rsi'], 1)) for s in sig]
    print('   symbol, old code -> new code, old RSI -> new RSI:', moved)
    state['calls'].clear(); code, oa = call(olds['stockiq-option-2-2-auto-signals'], 'stockiq-option-2-2-auto-signals', {})
    looked = sorted(set(state['calls']))
    check('(the old auto-detect looked at 15 names and called its five "top performers")', len(looked) == 15 and 'Top 5 performers' in oa['methodology'], (len(looked), oa['methodology']))
    print('   old five:', oa['top_performers'], [s['signal_strength'] for s in oa['signals']], '| new five:', a['top_performers'], [s['signal_strength'] for s in a['signals']])
else:
    print('   (the old files are not at hand: comparison skipped)')
if '--show' in sys.argv:
    for s in d['signals'] + a['signals']: print(f"   {s['symbol']:<8} {s['current_price']:>10.2f} {s['currency']:<4} {s['action']:<4} {s['confidence']:<6} {s['signal_strength']:+d} | {'; '.join(s['reasons'])} | {s['trend']}")
urllib.request.urlopen, time.sleep = real
print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
