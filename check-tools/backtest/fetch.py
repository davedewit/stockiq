"""Download 3 years of daily prices for the S&P 500 list, slowly (the price source blocks fast callers). Resumable."""
import importlib.util, io, contextlib, json, os, sys, time, urllib.request, urllib.error
spec = importlib.util.spec_from_file_location('coord', '/Users/dave/VSCODE/stockiq/lambda-sync/stockiq-screener-coordinator/lambda_function.py')
m = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(m)
syms = ['SPY'] + list(m.STOCK_UNIVERSES['3-3'])
json.dump(syms[1:], open('universe.json', 'w'))
done = fail = 0
for n, s in enumerate(syms):
    fn = f'data/{s}.json'
    if os.path.exists(fn): done += 1; continue
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{s}?range=3y&interval=1d&includePrePost=false'
    for attempt in range(6):
        try:
            d = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}), timeout=20).read()
            json.loads(d)['chart']['result'][0]['timestamp']
            open(fn, 'wb').write(d); done += 1; break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f'429 at {s} (#{n}), waiting {90 * (attempt + 1)}s', flush=True); time.sleep(90 * (attempt + 1)); continue
            print('HTTP', e.code, s, flush=True); fail += 1; break
        except Exception as e:
            print('ERR', s, repr(e)[:80], flush=True); fail += 1; break
    else:
        print('GAVE UP (still blocked) at', s, flush=True); break
    if n % 50 == 0: print(f'{n}/{len(syms)} done={done} fail={fail}', flush=True)
    time.sleep(1.1)
print(f'FETCH_DONE done={done} fail={fail} of {len(syms)}', flush=True)
