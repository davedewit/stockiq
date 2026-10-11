"""The single-stock report: the code from before 11 Oct 2026 and the code now, on the same saved prices. Nothing live is called.
    python3 report_test.py <old lambda_function2.py> <new lambda_function2.py> [--show SYMBOL]
old: unzip ~/VSCODE/backup/stockiq-option-1-1-custom-analysis_before_report_20261011.zip somewhere and give that file;
new: lambda-sync/stockiq-option-1-1-custom-analysis/lambda_function2.py, or a copy being worked on.
Prices: workers/data/sample.json (Yahoo's own answers, saved 11 Oct 2026). Stand-ins for Finnhub, the file of company
figures the site publishes (publish_company_figures.py), the news page, the VIX and the chart function."""
import sys, os, io, json, re, copy, contextlib, importlib.util, urllib.request, urllib.parse, urllib.error, time
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
ROOT = '/Users/dave/VSCODE/stockiq'
SAMPLE = json.load(open(os.path.join(ROOT, 'workers', 'data', 'sample.json')))
SHOW = sys.argv[sys.argv.index('--show') + 1] if '--show' in sys.argv else None
passed = failed = 0
def check(name, ok, detail=''):
    global passed, failed
    if ok: passed += 1; print('PASS', name)
    else: failed += 1; print('FAIL', name, '|', str(detail)[:300])

FINNHUB = {'CRWD': {'peBasicExclExtraTTM': None, 'beta': 1.1, 'marketCapitalization': 90000, 'revenueGrowthTTMYoy': 29.4, 'netProfitMarginTTM': -2.1,
                    'totalDebt2TotalEquityQuarterly': 0.24, 'roeTTM': -3.2, 'currentRatioQuarterly': 1.8, 'pbQuarterly': 24.0},
           'KHC': {'peBasicExclExtraTTM': 13.2, 'beta': 0.5, 'marketCapitalization': 40000, 'revenueGrowthTTMYoy': None, 'netProfitMarginTTM': 11.0,
                   'totalDebt2TotalEquityQuarterly': 0.41, 'roeTTM': 5.6, 'currentRatioQuarterly': 1.1, 'pbQuarterly': 0.8},
           'CSX': {'peBasicExclExtraTTM': 17.9, 'beta': 1.2, 'marketCapitalization': 60000, 'revenueGrowthTTMYoy': 2.0, 'netProfitMarginTTM': 24.0,
                   'totalDebt2TotalEquityQuarterly': 1.52, 'roeTTM': 28.0, 'currentRatioQuarterly': 0.9, 'pbQuarterly': 5.4}}
# What the daily job's cache holds (Yahoo's own units: fractions, debt to equity in percent), turned into the published
# file by the real converter
sys.path.insert(0, ROOT)
import publish_company_figures as publisher
CACHE = {'BHP.AX': {'pe_ratio': 12.4, 'revenue_growth': -0.02, 'profit_margin': 0.21, 'debt_to_equity': 44.0, 'current_ratio': 1.6, 'return_on_equity': 0.24, 'price_to_book': 3.1},
         'IMB.L': {'pe_ratio': 9.1, 'revenue_growth': 0.01, 'profit_margin': 0.08, 'debt_to_equity': 190.0, 'current_ratio': 0.7, 'return_on_equity': 0.44, 'price_to_book': 5.14},
         'KHC': {'pe_ratio': 13.0, 'revenue_growth': -0.03, 'profit_margin': 0.11, 'debt_to_equity': 41.0, 'current_ratio': 1.1, 'return_on_equity': 0.056, 'price_to_book': 0.8},
         'ETFX': {'pe_ratio': 27.0, 'price_to_book': 4.0}}
PUBLISHED = {'made': '2026-10-11', 'figures': {s: dict(publisher.to_score_units(e), as_of='2026-10-05') for s, e in CACHE.items()}}
state = {'figures': 'ok', 'figure_reads': 0, 'chart_payloads': [], 'emptied': set(), 'charts': {}}

def chart_for(symbol):
    c = state['charts'].get(symbol) or SAMPLE.get(symbol)
    if not c: return None
    ts = c['timestamp']; q = c['indicators']['quote'][0]; keep = [i for i, t in enumerate(ts) if t >= ts[-1] - 365 * 86400]
    out = {'meta': dict(c['meta']), 'timestamp': [ts[i] for i in keep], 'indicators': {'quote': [{k: [q[k][i] for i in keep] for k in ('open', 'high', 'low', 'close', 'volume')}]}}
    if symbol in state['emptied']:
        for k in out['indicators']['quote'][0]: out['indicators']['quote'][0][k][-1] = None
    return out

class Answer:
    def __init__(self, body): self.body = body if isinstance(body, bytes) else json.dumps(body).encode()
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def getcode(self): return 200
    def read(self): return self.body

def fake_urlopen(req, timeout=None):
    url = req.full_url if hasattr(req, 'full_url') else req
    if '/v8/finance/chart/' in url:
        symbol = urllib.parse.unquote(url.split('/chart/')[1].split('?')[0])
        if 'VIX' in symbol: return Answer({'chart': {'result': [{'meta': {'regularMarketPrice': 14.84}, 'timestamp': [1], 'indicators': {'quote': [{'close': [14.84]}]}}]}})
        c = chart_for(symbol)
        if c and 'events=div' in url:
            t = c['timestamp']; c['events'] = {'dividends': {str(t[-40]): {'amount': 0.5, 'date': t[-40]}, str(t[-130]): {'amount': 0.5, 'date': t[-130]}}}
        return Answer({'chart': {'result': [c] if c else None}})
    if 'finnhub.io' in url:
        symbol = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get('symbol', [''])[0]
        return Answer({'metric': FINNHUB[symbol]} if symbol in FINNHUB else {})
    raise urllib.error.HTTPError(url, 404, 'not found', None, None)

class FakeS3:
    """Stands in for the S3 client: the file of company figures; no stocks.txt (names then come from Yahoo's answer)"""
    def get_object(self, Bucket=None, Key=None):
        if Key != 'site-data/company_figures.json' or Bucket != 'stockiq-dynamic-stock-lists' or state['figures'] == 'fail': raise RuntimeError('NoSuchKey')
        state['figure_reads'] += 1
        return {'Body': io.BytesIO(json.dumps(PUBLISHED).encode())}

class FakeLambda:
    def invoke(self, FunctionName=None, InvocationType=None, Payload=None):
        state['chart_payloads'].append(json.loads(Payload))
        return {'StatusCode': 200, 'Payload': io.BytesIO(json.dumps({'statusCode': 200, 'body': json.dumps({'price_chart_url': 'data:image/svg+xml;base64,QUJD', 'volume_chart_url': 'data:image/svg+xml;base64,QUJD'})}).encode())}
class FakeBoto:
    def client(self, name, **kw): return FakeLambda()
    def resource(self, name, **kw): raise RuntimeError('no database in a test')

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); mod = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()): spec.loader.exec_module(mod)
    mod.boto3 = FakeBoto(); mod.s3_client = FakeS3(); mod.history_table = None; mod.finnhub_rate_limit = lambda: None
    return mod

real_open, real_sleep = urllib.request.urlopen, time.sleep
urllib.request.urlopen = fake_urlopen; time.sleep = lambda s: None
old = load('old_report', sys.argv[1]); new = load('new_report', sys.argv[2])

def run(mod, symbol):
    mod._api_cache.clear()
    if hasattr(mod, '_site_figures') and not state.get('keep_file'): mod._site_figures.update(figures=None, at=0)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return mod.analyze_stock_comprehensive_enhanced(symbol)
text = lambda r: r['comprehensive_analysis']
points = lambda r: [int(m.group(1)) for b in r['score_breakdown'] for m in [re.search(r': ([+-]\d+)', b)] if m]

worker_spec = importlib.util.spec_from_file_location('worker', os.path.join(ROOT, 'workers', 'stock_worker.py')); worker = importlib.util.module_from_spec(worker_spec)
with contextlib.redirect_stdout(io.StringIO()): worker_spec.loader.exec_module(worker)

print('== old and new on the same prices')
rows = []
for symbol in ['BHP.AX', 'CBA.AX', 'IMB.L', 'AZN.L', '7203.T', 'CRWD', 'KHC', 'CSX', 'MSTR', 'ASML']:
    a = run(old, symbol); b = run(new, symbol)
    check(f'{symbol}: both give a report', bool(a and b))
    if not (a and b): continue
    rows.append((symbol, a, b))
    closes = [x for x in chart_for(symbol)['indicators']['quote'][0]['close'] if x is not None]
    check(f'{symbol}: the score is 50 plus its breakdown', b['investment_score'] == max(0, min(100, 50 + sum(points(b)))), (b['investment_score'], points(b)))
    check(f'{symbol}: every breakdown line carries its points', len(points(b)) == len(b['score_breakdown']), b['score_breakdown'])
    t = text(b)
    for bad in ('YTD', 'Buy signal', 'Sell signal', 'BREAKING', 'DETAILED SCORING', '40% weight', 'Liquidity Crisis', 'Overall Financial Health', 'Chart shows'):
        if bad in t: check(f'{symbol}: no "{bad}" in the report', False, [l for l in t.split('\n') if bad in l][:2])
    m = re.search(r'50 \+ (\d+) - (\d+) = (-?\d+)', t)
    check(f'{symbol}: the explanation adds up to the score', bool(m) and 50 + int(m.group(1)) - int(m.group(2)) == int(m.group(3)) and max(0, min(100, int(m.group(3)))) == b['investment_score'], m and m.group(0))
for symbol, a, b in rows:
    print(f"   {symbol:<7} score {a['investment_score']:>3} -> {b['investment_score']:>3} | RSI {a['rsi']:.1f} -> {b['rsi']:.1f} | today {a['daily_change_pct']:+.2f}% -> {b['daily_change_pct']:+.2f}% | {[l for l in b['score_breakdown'] if 'rend' in l and 'Long-term' not in l and 'MA200' not in l][:1]}")

print('== prices and currency')
got = {s: (a, b) for s, a, b in rows}
a, b = got['BHP.AX']
check('ASX: the live code says 0.00% today on the saved answer', abs(a['daily_change_pct']) < 1e-9, a['daily_change_pct'])
check('ASX: the new code gives the real change', abs(b['daily_change_pct'] - (-0.41)) < 0.02, b['daily_change_pct'])
check('ASX: prices in A$', 'Current Price: A$60.94' in text(b) and 'Prices for this share are in AUD' in text(b), [l for l in text(b).split('\n') if 'Current Price' in l])
a, b = got['IMB.L']
check('London: prices in pence with the pounds beside', 'Current Price: 2,662.00p' in text(b) and '2,662.00p is £26.62' in text(b), [l for l in text(b).split('\n')[:12]])
check('London: no dollar sign anywhere in the report', '$' not in text(b), [l for l in text(b).split('\n') if '$' in l][:3])
check('London: dividends in pence', 'Latest Dividend: 0.500p' in text(b), [l for l in text(b).split('\n') if 'Dividend' in l][:3])
check('Tokyo: prices in yen', 'Current Price: ¥2,910.50' in text(got['7203.T'][1]), [l for l in text(got['7203.T'][1]).split('\n') if 'Current Price' in l])
check('US: prices in dollars as before, no currency note', 'Current Price: $' in text(got['CRWD'][1]) and 'Prices for this share' not in text(got['CRWD'][1]))
state['emptied'] = {'IMB.L'}
a2 = run(old, 'IMB.L'); b2 = run(new, 'IMB.L'); state['emptied'] = set()
check('London, latest session sent empty: the live code shows the day before', abs(a2['current_price'] - 2614.0) < 0.01, a2['current_price'])
check('London, latest session sent empty: the new code shows the latest price', abs(b2['current_price'] - 2662.0) < 0.01, b2['current_price'])

print('== RSI')
for symbol in ['BHP.AX', 'CRWD', 'IMB.L']:
    closes = [bar['close'] for bar in new.bars_from_chart(chart_for(symbol))[0]]
    check(f'{symbol}: the report\'s RSI is the screeners\' RSI', abs(new.calculate_rsi(closes) - worker.calculate_rsi(closes)) < 1e-9, (new.calculate_rsi(closes), worker.calculate_rsi(closes)))
check('RSI: too little history gives none', new.calculate_rsi([1, 2, 3]) is None)

print('== the trend factor')
tp = new.trend_points
check('trend: price a hair under its average, averages level: nothing', tp(99.97, 100, 100)[0] == 0 and tp(99.97, 100, 100)[1] == 'Flat Trend', tp(99.97, 100, 100))
check('trend: far above both: the full 12', tp(105, 100, 96)[:2] == (12, 'Strong Uptrend'), tp(105, 100, 96))
check('trend: far below both: the full -12', tp(95, 100, 104)[:2] == (-12, 'Strong Downtrend'), tp(95, 100, 104))
check('trend: 1% above, averages 1% apart: half', tp(101, 100, 100 / 1.01)[0] == 6, tp(101, 100, 100 / 1.01))
check('trend: above its average but the averages the other way: about nothing, and called mixed', tp(103, 100, 103)[:2] == (0, 'Mixed Trend'), tp(103, 100, 103))
check('trend: a tiny move changes the points by at most one', all(abs(tp(100 + d / 100, 100, 99)[0] - tp(100 + (d + 1) / 100, 100, 99)[0]) <= 1 for d in range(-400, 400)))
check('trend: no averages, no points', tp(100, None, None)[0] == 0)
check('trend: the words say where the price is', 'price 0.4% above its 20-day average; 20-day average 4.0% above the 50-day' == tp(100.4, 100, 100 / 1.04)[2], tp(100.4, 100, 100 / 1.04)[2])
check('trend: a hair from the average is "level with" it', tp(99.97, 100, 97)[2] == 'price level with its 20-day average; 20-day average 3.1% above the 50-day', tp(99.97, 100, 97)[2])

print('== company figures')
a, b = got['BHP.AX']
check('non-US share: the old code had no company figure at all', a['pe_ratio'] is None and a['profit_margin'] is None)
check('non-US share: figures from the site\'s file, in the score\'s units', b['pe_ratio'] == 12.4 and abs(b['profit_margin'] - 21.0) < 1e-9 and abs(b['debt_to_equity'] - 0.44) < 1e-9 and abs(b['return_on_equity'] - 24.0) < 1e-9, (b['pe_ratio'], b['profit_margin'], b['debt_to_equity'], b['return_on_equity']))
check('non-US share: they count in the score and the report says where they came from and from when', any('P/E' in l for l in b['score_breakdown']) and 'Company figures from Yahoo Finance (as of 5 Oct 2026)' in text(b), [l for l in text(b).split('\n') if 'Company figures from' in l])
check('London: price-to-book counts (the source gives it right for a share priced in pence)', any('High P/B (5.14)' in l for l in got['IMB.L'][1]['score_breakdown']) and 'Price/Book: 5.14' in text(got['IMB.L'][1]), got['IMB.L'][1]['score_breakdown'])
check('US share with every figure from the first source: nothing is taken from the file', 'Company figures from Finnhub\n' in text(got['CSX'][1]) + '\n' and got['CSX'][1]['pe_ratio'] == 17.9, [l for l in text(got['CSX'][1]).split('\n') if 'Company figures from' in l])
k = got['KHC'][1]
check('US share missing one figure: only that one is filled', abs(k['revenue_growth'] - (-3.0)) < 1e-9 and k['pe_ratio'] == 13.2 and 'Company figures from Finnhub and Yahoo Finance (as of 5 Oct 2026)' in text(k), (k['revenue_growth'], k['pe_ratio'], [l for l in text(k).split('\n') if 'Company figures from' in l]))
check('a share that is not in the file: a report that says the score is price and volume only', 'were not available for this share' in text(got['7203.T'][1]) and 'from price and volume only' in text(got['7203.T'][1]) and got['7203.T'][1]['pe_ratio'] is None)
state['figures'] = 'fail'; f = run(new, 'BHP.AX'); state['figures'] = 'ok'
check('the file cannot be read: still a report, and it says the score is price and volume only', bool(f) and 'were not available for this share' in text(f) and 'from price and volume only' in text(f) and f['pe_ratio'] is None, f and [l for l in text(f).split('\n') if 'available' in l])
state['keep_file'] = True; new._site_figures.update(figures=None, at=0); state['figure_reads'] = 0; run(new, 'BHP.AX'); run(new, 'IMB.L'); run(new, 'KHC'); state['keep_file'] = False
check('the file is read once and kept, not once a report', state['figure_reads'] == 1, state['figure_reads'])
for symbol, a, b in rows:
    lines = new.company_figure_lines({k: b.get(k) for k in ('pe_ratio', 'revenue_growth', 'profit_margin', 'debt_to_equity', 'return_on_equity')})
    bad = [l for l in lines if ('❌' in l) and not any(w in ' '.join(b['score_breakdown']) for w in ('High P/E', 'Declining', 'Unprofitable', 'Weak Profit', 'High Debt', 'Elevated Debt', 'Negative ROE', 'Weak ROE'))]
    if bad: check(f'{symbol}: a figure marked bad is also taken off the score', False, (bad, b['score_breakdown']))
try:
    import update_stock_analysis as pages
    entry = {'pe_ratio': 21.49, 'revenue_growth': 0.183, 'profit_margin': 0.167, 'debt_to_equity': 50.473, 'current_ratio': 1.885, 'return_on_equity': 0.24, 'price_to_book': 4.283}
    theirs = pages.to_model_fundamentals(entry); ours = publisher.to_score_units(entry)
    check('the published file uses the same units as the stock pages', all(abs(theirs[k] - ours[k]) < 1e-3 for k in theirs), (theirs, ours))
except Exception as e:
    print('(the stock pages\' script could not be loaded here, so its units were not compared:', str(e)[:80] + ')')
sample_etf = copy.deepcopy(SAMPLE['CSX']); sample_etf['meta']['instrumentType'] = 'ETF'; state['charts']['ETFX'] = sample_etf
e = run(new, 'ETFX')
check('a fund: no company figures are taken for it, although the file has some', bool(e) and e['pe_ratio'] is None and 'were not available for this share' in text(e), e and e['pe_ratio'])

print('== a session that is still open')
c = chart_for('CRWD'); last = c['timestamp'][-1]
c['meta']['currentTradingPeriod'] = {'regular': {'start': last, 'end': last + 23400}}
bars, facts = new.bars_from_chart(c, now=last + 3600); bars2, facts2 = new.bars_from_chart(c, now=last + 30000)
check('open session: seen as a part of a day', facts['partial_day'] is True and facts2['partial_day'] is False, (facts, facts2))
check('one bar a day on the ASX answer', len(new.bars_from_chart(chart_for('BHP.AX'))[0]) == len(chart_for('BHP.AX')['timestamp']) - 1)

print('== what the chart function is sent')
p = state['chart_payloads'][-1]
check('the chart function is sent the report\'s own bars, currency and levels', p.get('symbol') == 'ETFX' and len(p.get('series', {}).get('c', [])) == len(e and new.bars_from_chart(chart_for('ETFX'))[0]) and p.get('currency') == 'USD' and abs(p.get('support') - e['support']) < 1e-9 and abs(p.get('resistance') - e['resistance']) < 1e-9, {k: (v if k != 'series' else len(v['c'])) for k, v in p.items()})
state['chart_payloads'].clear(); run(old, 'CRWD')
check('(the live code sends the chart function the symbol only)', set(state['chart_payloads'][-1]) == {'symbol', 'return_type'}, state['chart_payloads'][-1:])

if SHOW:
    r = run(new, SHOW); print('\n' + re.sub(r'data:image/svg\+xml;base64,[A-Za-z0-9+/=]+', '<CHART>', text(r)))
urllib.request.urlopen, time.sleep = real_open, real_sleep
print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
