"""The chart function on saved prices, by itself and fed by the report. Nothing live is called.
    python3 chart_test.py <chart lambda_function_simple.py> <report lambda_function2.py>"""
import sys, os, io, json, re, base64, contextlib, importlib.util, urllib.request, urllib.parse, urllib.error, time
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
SAMPLE = json.load(open('/Users/dave/VSCODE/stockiq/workers/data/sample.json'))
passed = failed = 0
def check(name, ok, detail=''):
    global passed, failed
    if ok: passed += 1; print('PASS', name)
    else: failed += 1; print('FAIL', name, '|', str(detail)[:300])
def chart_for(symbol):
    c = SAMPLE.get(symbol)
    if not c: return None
    ts = c['timestamp']; q = c['indicators']['quote'][0]; keep = [i for i, t in enumerate(ts) if t >= ts[-1] - 365 * 86400]
    return {'meta': dict(c['meta']), 'timestamp': [ts[i] for i in keep], 'indicators': {'quote': [{k: [q[k][i] for i in keep] for k in ('open', 'high', 'low', 'close', 'volume')}]}}
class Answer:
    def __init__(self, body): self.body = json.dumps(body).encode()
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return self.body
    def getcode(self): return 200
calls = []
def fake_urlopen(req, timeout=None):
    url = req.full_url if hasattr(req, 'full_url') else req; calls.append(url)
    if '/v8/finance/chart/' in url:
        symbol = urllib.parse.unquote(url.split('/chart/')[1].split('?')[0])
        if 'VIX' in symbol: return Answer({'chart': {'result': [{'meta': {'regularMarketPrice': 15}, 'timestamp': [1], 'indicators': {'quote': [{'close': [15]}]}}]}})
        c = chart_for(symbol); return Answer({'chart': {'result': [c] if c else None}})
    raise urllib.error.HTTPError(url, 404, 'not found', None, None)
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); mod = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()): spec.loader.exec_module(mod)
    return mod
real = urllib.request.urlopen, urllib.request.build_opener, time.sleep
urllib.request.urlopen = fake_urlopen; time.sleep = lambda s: None
class NoOpener:
    def open(self, *a, **k): raise urllib.error.HTTPError('x', 429, 'no', None, None)
urllib.request.build_opener = lambda *a, **k: NoOpener()
chart = load('chart', sys.argv[1]); report = load('report', sys.argv[2])

print('== a chart asked for by itself (the pages do this)')
r = chart.lambda_handler({'body': json.dumps({'symbol': 'BHP.AX'})}, None); svg = r['body']
check('answers with a picture', r['statusCode'] == 200 and r['headers']['Content-Type'] == 'image/svg+xml' and svg.startswith('<svg'), r['headers'])
check('plain ASCII, so the page can turn it into a picture', svg.isascii())
check('the price in its own currency and the real day\'s change', 'A$60.94' in svg and '-0.41%' in svg, re.findall(r'class="p"[^<]*>([^<]*)', svg))
check('small enough to sit inside a saved report', len(svg) < 30000, len(svg))
check('no background of its own', '<rect' not in svg)
r = chart.lambda_handler({'symbol': '7203.T'}, None)
check('a yen sign is written as a character code', '&#165;' in r['body'] and r['body'].isascii())
r = chart.lambda_handler({'symbol': 'IMB.L'}, None)
check('London in pence', '2,662.00p' in r['body'], re.findall(r'class="p"[^<]*>([^<]*)', r['body']))
r = chart.lambda_handler({'symbol': 'NOSUCH'}, None)
check('an unknown symbol gives the error picture, not a failure', r['statusCode'] == 200 and 'No data available' in r['body'])
r = chart.lambda_handler({'symbol': 'BHP.AX', 'return_type': 'url'}, None); body = json.loads(r['body'])
check('asked for an address without an account: the picture itself, encoded', body['price_chart_url'].startswith('data:image/svg+xml;base64,') and base64.b64decode(body['price_chart_url'].split(',')[1]).decode() == svg)

print('== the lines')
ma = chart.moving_average(list(range(1, 301)), 200)
check('an average starts when it has its days, not before', ma[198] is None and abs(ma[199] - 100.5) < 1e-9 and chart.moving_average([5.0] * 30, 20)[18] is None)
rs = chart.rsi_series([float(x) for x in SAMPLE['CRWD']['indicators']['quote'][0]['close'][-250:]])
check('RSI starts after 14 days, not as a flat line at 50', rs[13] is None and rs[14] is not None and 50 not in rs[:14])
closes = [b['c'] for b in chart.bars_from_chart(chart_for('CRWD'))[0]]
check('the chart\'s RSI is the report\'s RSI', abs(chart.rsi_series(closes)[-1] - report.calculate_rsi(closes)) < 1e-9, (chart.rsi_series(closes)[-1], report.calculate_rsi(closes)))
check('the 200-day average is drawn', svg.count('stroke-dasharray="5,3"') >= 2)
check('axis numbers stay short', chart.axis_text(52345.6) == '52.3k' and chart.axis_text(3396.02) == '3,396' and chart.axis_text(61.85) == '61.85' and chart.axis_text(0.4321) == '0.4321')

print('== fed by the report')
sent = []
class Lambda:
    def invoke(self, FunctionName=None, InvocationType=None, Payload=None):
        sent.append(json.loads(Payload)); out = chart.lambda_handler(json.loads(Payload), None)
        return {'StatusCode': 200, 'Payload': io.BytesIO(json.dumps(out).encode())}
class Boto:
    def client(self, name, **kw): return Lambda()
report.boto3 = Boto(); report.s3_client = None; report.history_table = None; report.finnhub_rate_limit = lambda: None
for symbol in ['BHP.AX', 'IMB.L', 'CRWD']:
    calls.clear()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()): res = report.analyze_stock_comprehensive_enhanced(symbol)
    m = re.search(r'data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)', res['comprehensive_analysis']); pic = base64.b64decode(m.group(1)).decode() if m else ''
    check(f'{symbol}: the report carries the chart', pic.startswith('<svg') and 'Chart Generation Error' not in pic, pic[:80])
    check(f'{symbol}: the chart did not fetch prices of its own', sum(1 for u in calls if '/chart/' + urllib.parse.quote(symbol) in u and 'events' not in u) == 1, [u[:70] for u in calls])
    check(f'{symbol}: RSI on the chart is the RSI in the text', f"RSI (14): {res['rsi']:.0f}<" in pic, (re.findall(r'RSI \(14\)[^<]*', pic), res['rsi']))
    check(f'{symbol}: support and resistance on the chart are the report\'s', f"Support {chart.price_text(res['support'])}<" in pic and f"Resistance {chart.price_text(res['resistance'])}<" in pic, (re.findall(r'(?:Support|Resistance) [\d,.]+', pic), res['support'], res['resistance']))
    check(f'{symbol}: the whole report is under 60 KB', len(res['comprehensive_analysis']) < 60000, len(res['comprehensive_analysis']))
urllib.request.urlopen, urllib.request.build_opener, time.sleep = real
print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
