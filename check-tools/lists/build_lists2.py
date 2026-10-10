import urllib.request, urllib.parse, re, json, time, glob, importlib.util, io, contextlib
from bs4 import BeautifulSoup
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36'}
def page(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read().decode('utf-8', 'ignore')
def col(html, want, minrows=20, extra=None):
    soup = BeautifulSoup(html, 'html.parser'); best = []
    for t in soup.find_all('table'):
        rows = t.find_all('tr')
        if len(rows) < minrows: continue
        heads = [re.sub(r'\[.*?\]', '', th.get_text(' ', strip=True)).strip().lower() for th in rows[0].find_all(['th', 'td'])]
        idx = next((i for i, h in enumerate(heads) if re.match(want, h)), None)
        if idx is None: continue
        xi = next((i for i, h in enumerate(heads) if extra and re.match(extra, h)), None)
        out = []
        for r in rows[1:]:
            c = r.find_all(['td', 'th'])
            if len(c) <= idx: continue
            s = re.sub(r'\[.*?\]', '', c[idx].get_text(' ', strip=True)).strip(); s = s.split()[-1] if s else s
            if not re.fullmatch(r'[A-Za-z0-9.\-]{1,8}', s): continue
            x = None
            if xi is not None and len(c) > xi:
                try: x = float(re.sub(r'[^0-9.]', '', c[xi].get_text(' ', strip=True)) or 0)
                except Exception: x = 0
            out.append((s.upper(), x))
        if len(out) > len(best): best = out
    seen = set(); res = []
    for s, x in best:
        if s not in seen: seen.add(s); res.append((s, x))
    return res
raw = json.load(open('raw_lists.json')); src = {}
src['dow30'] = [s for s, _ in col(page('https://www.slickcharts.com/dowjones'), r'^symbol$')]; time.sleep(1)
src['nasdaq100'] = [s for s, _ in col(page('https://www.slickcharts.com/nasdaq100'), r'^symbol$')]; time.sleep(1)
for k in ('sp100', 'sp500', 'sp400', 'sp600', 'ftse100', 'nikkei225'): src[k] = raw[k]
asx200 = col(page('https://en.wikipedia.org/wiki/S%26P/ASX_200'), r'^code$', extra=r'^market cap'); time.sleep(1)
asx50 = [s for s, _ in col(page('https://en.wikipedia.org/wiki/S%26P/ASX_50'), r'^(code|symbol|ticker|asx code)$', minrows=30)]
by_cap = [s for s, _ in sorted(asx200, key=lambda t: -(t[1] or 0))]
print('asx200', len(asx200), 'with caps', sum(1 for _, x in asx200 if x), '| asx50 page', len(asx50), '| top5 by cap', by_cap[:5])
spec = importlib.util.spec_from_file_location('coord', '/Users/dave/VSCODE/stockiq/lambda-sync/stockiq-screener-coordinator/lambda_function.py')
m = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(m)
old = m.STOCK_UNIVERSES
us = lambda s: s.replace('.', '-')
def ftse(s): s = s.rstrip('.'); return s.replace('.', '-') + '.L'
a200 = [s + '.AX' for s, _ in asx200]
lists = {
    '3-8': [us(s) for s in src['dow30']], '3-100': [us(s) for s in src['sp100']], '3-7': [us(s) for s in src['nasdaq100']],
    '3-3': [us(s) for s in src['sp500']], '3-2': [us(s) for s in src['sp400'] + src['sp600']], '3-4': [us(s) for s in src['sp500'] + src['sp400'] + src['sp600']],
    '5-ftse100': [ftse(s) for s in src['ftse100']], '5-nikkei225': [s + '.T' for s in src['nikkei225']],
    '4-50': [s + '.AX' for s in (asx50 if len(asx50) >= 45 else by_cap[:50])], '4-100': [s + '.AX' for s in by_cap[:100]], '4-200': a200,
    '4-300': a200 + [s for s in old['4-300'] if s not in set(a200)],
}
for k in lists: lists[k] = list(dict.fromkeys(lists[k]))
known = set()
for f in glob.glob('../full/res_*.json'):
    try: known |= {r['symbol'] for r in json.load(open(f))['results']}
    except Exception: pass
allsyms = {s for v in lists.values() for s in v}; todo = sorted(allsyms - known)
print('unique symbols', len(allsyms), '| already known live', len(allsyms & known), '| to probe', len(todo), flush=True)
PROXY = 'https://dohdeb4vpu67fa2tq3ax56ls4i0rshvm.lambda-url.us-east-1.on.aws/?symbol='
def probe(sym):
    """Ask the site's own price proxy (runs in AWS) whether the price source has data for this symbol."""
    for attempt in range(3):
        try:
            d = json.loads(urllib.request.urlopen(urllib.request.Request(PROXY + urllib.parse.quote(sym), headers=UA), timeout=20).read())
            res = (d.get('chart') or {}).get('result')
            if not res:
                err = str((d.get('chart') or {}).get('error') or d)[:60]
                return -404 if 'Not Found' in err or 'No data' in err or 'delisted' in err else -1
            return len([c for c in res[0]['indicators']['quote'][0].get('close', []) if c])
        except urllib.error.HTTPError as e:
            if e.code in (404, 400): return -404
            if e.code == 500 and attempt >= 1: return -404   # the proxy answers 500 when the price source has no such symbol
            time.sleep(2)
        except Exception: time.sleep(3)
    return -1
pr = {}
for i, s in enumerate(todo):
    pr[s] = probe(s); time.sleep(0.15)
    if i % 50 == 0: print('probed', i, 'errors so far', sum(1 for v in pr.values() if v == -1), flush=True)
final = {}; dropped = {}
for k, v in lists.items():
    final[k] = [s for s in v if s in known or pr.get(s, 0) >= 10]
    dropped[k] = [(s, pr.get(s)) for s in v if not (s in known or pr.get(s, 0) >= 10)]
    added = [s for s in final[k] if s not in set(old.get(k, []))]; removed = [s for s in old.get(k, []) if s not in set(final[k])]
    print(f'final {k:12} {len(final[k]):5} of {len(v):5} from source | was {len(old.get(k, [])):5} | new members {len(added):4} | no longer members {len(removed):4} | not on price source {len(dropped[k]):3} {dropped[k][:6]}', flush=True)
json.dump({'final': final, 'dropped': dropped, 'probe': pr}, open('final_lists.json', 'w'))
print('could not be checked:', sum(1 for v in pr.values() if v == -1)); print('LISTS_DONE', flush=True)
