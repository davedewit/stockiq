import urllib.request, re, json, time
from bs4 import BeautifulSoup
UA = {'User-Agent': 'Mozilla/5.0 (stockiq list refresh; contact support@stockiq.tech)'}
def page(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read().decode('utf-8', 'ignore')
def table_symbols(html, want=r'^(symbol|ticker|code|ticker symbol|asx code|epic)$'):
    soup = BeautifulSoup(html, 'html.parser'); best = []
    for t in soup.find_all('table', class_=re.compile('wikitable')):
        rows = t.find_all('tr')
        if not rows: continue
        heads = [re.sub(r'\[.*?\]', '', th.get_text(' ', strip=True)).strip().lower() for th in rows[0].find_all(['th', 'td'])]
        idx = next((i for i, h in enumerate(heads) if re.match(want, h)), None)
        if idx is None: continue
        syms = []
        for r in rows[1:]:
            cells = r.find_all(['td', 'th'])
            if len(cells) <= idx: continue
            s = re.sub(r'\[.*?\]', '', cells[idx].get_text(' ', strip=True)).strip()
            s = s.split()[-1] if s else s            # "NYSE: MMM" -> "MMM"
            if re.fullmatch(r'[A-Za-z0-9.\-]{1,8}', s): syms.append(s.upper())
        if len(syms) > len(best): best = syms
    return best
W = 'https://en.wikipedia.org/wiki/'
src = {'dow30': 'Dow_Jones_Industrial_Average', 'sp100': 'S%26P_100', 'nasdaq100': 'Nasdaq-100', 'sp500': 'List_of_S%26P_500_companies',
       'sp400': 'List_of_S%26P_400_companies', 'sp600': 'List_of_S%26P_600_companies', 'russell1000': 'Russell_1000_Index',
       'ftse100': 'FTSE_100_Index', 'asx50': 'S%26P/ASX_50', 'asx100': 'S%26P/ASX_100', 'asx200': 'S%26P/ASX_200', 'asx300': 'S%26P/ASX_300'}
out = {}
for k, p in src.items():
    try:
        h = page(W + p); out[k] = list(dict.fromkeys(table_symbols(h)))
    except Exception as e: out[k] = []; print(k, 'ERROR', str(e)[:80])
    print(f'{k:12} {len(out[k]):5}  {out[k][:8]}', flush=True); time.sleep(1)
# Nikkei 225: components are listed as "(TYO: 1332)" links, not a table
try:
    h = page(W + 'Nikkei_225'); soup = BeautifulSoup(h, 'html.parser'); txt = soup.get_text(' ')
    codes = list(dict.fromkeys(re.findall(r'TYO\s*:\s*([0-9]{3}[0-9A-Z])\b', txt)))
    out['nikkei225'] = codes
except Exception as e: out['nikkei225'] = []; print('nikkei ERROR', e)
print(f'{"nikkei225":12} {len(out["nikkei225"]):5}  {out["nikkei225"][:8]}')
# Russell 2000: iShares IWM holdings file
try:
    raw = urllib.request.urlopen(urllib.request.Request('https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/1467271812596.ajax?fileType=csv&fileName=IWM_holdings&dataType=fund', headers={'User-Agent': 'Mozilla/5.0'}), timeout=60).read().decode('utf-8', 'ignore')
    import csv, io
    rows = list(csv.reader(io.StringIO(raw))); hi = next(i for i, r in enumerate(rows) if r and r[0].strip() == 'Ticker')
    hdr = rows[hi]; ac = hdr.index('Asset Class') if 'Asset Class' in hdr else None
    r2 = [r[0].strip().upper() for r in rows[hi + 1:] if r and r[0].strip() and (ac is None or (len(r) > ac and r[ac].strip() == 'Equity')) and re.fullmatch(r'[A-Z0-9.\-]{1,6}', r[0].strip().upper())]
    out['russell2000'] = list(dict.fromkeys(r2)); print(f'{"russell2000":12} {len(out["russell2000"]):5}  {out["russell2000"][:8]}  (as of line: {rows[1][:2] if len(rows)>1 else ""})')
except Exception as e: out['russell2000'] = []; print('russell2000 ERROR', str(e)[:120])
json.dump(out, open('raw_lists.json', 'w'))
