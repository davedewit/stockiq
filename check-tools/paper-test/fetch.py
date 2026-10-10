"""Fetch 5 years of daily prices for the Dow 30 and S&P 100 screener lists (one slow call per symbol) into data/.
The lists are frozen in frozen_lists.txt the first time this runs, so later runs test the same stocks
(a list chosen today and tested on later prices has no hindsight in it). Delete that file to re-freeze.
Yahoo blocks this machine after a few hundred calls: this makes 106, so do not loop it."""
import importlib.util, io, contextlib, json, time, urllib.request, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); os.makedirs(os.path.join(HERE, 'data'), exist_ok=True)
FROZEN = os.path.join(HERE, 'frozen_lists.txt'); os.chdir(os.path.join(HERE, 'data'))
if os.path.exists(FROZEN):
    lists = {l.split(':')[0]: l.split(':')[1].split() for l in open(FROZEN) if ':' in l and not l.startswith('#')}
else:
    spec = importlib.util.spec_from_file_location('coord', '/Users/dave/VSCODE/stockiq/lambda-sync/stockiq-screener-coordinator/lambda_function.py')
    m = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(m)
    lists = {'dow30': m.STOCK_UNIVERSES['3-8'], 'sp100': m.STOCK_UNIVERSES['3-100']}
    open(FROZEN, 'w').write('# Screener lists as frozen on ' + time.strftime('%Y-%m-%d') + ' (from the coordinator). One list per line.\n'
                            + ''.join(f'{k}: {" ".join(v)}\n' for k, v in lists.items()))
syms = ['SPY'] + sorted(set(lists['dow30']) | set(lists['sp100']))
cache = {}                                           # always refetch: a re-run is for newer prices
print(len(syms), 'symbols,', len(cache), 'cached', flush=True)
fails = 0
for s in syms:
    if s in cache: continue
    try:
        req = urllib.request.Request(f'https://query1.finance.yahoo.com/v8/finance/chart/{s}?range=5y&interval=1d&includePrePost=false', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        r = json.loads(urllib.request.urlopen(req, timeout=20).read())['chart']['result'][0]
        q = r['indicators']['quote'][0]
        bars = [[t, q['open'][i], q['high'][i], q['low'][i], q['close'][i], q['volume'][i]] for i, t in enumerate(r['timestamp'])
                if all(q[k][i] is not None for k in ('open', 'high', 'low', 'close', 'volume'))]
        cache[s] = bars; fails = 0
    except Exception as e:
        fails += 1; print('FAIL', s, str(e)[:80], flush=True)
        if '429' in str(e) or fails >= 3: print('stopping: rate limited or repeated failures'); break
    time.sleep(0.6)
json.dump(cache, open('prices.json', 'w'))
print('have', len(cache), 'of', len(syms), '| bars for SPY:', len(cache.get('SPY', [])), '| missing:', [s for s in syms if s not in cache])
