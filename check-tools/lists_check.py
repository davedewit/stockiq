#!/usr/bin/env python3
"""Are the screeners' stock lists still right? (17 Oct 2026; the owner: "do the stocks for each screener auto update? ... is there
any check for duplicates accuracy etc." They did not, and there was none.) Read-only.

    python3 check-tools/lists_check.py            the quick part (seconds): the page's list (website/screeners.js) and the
                                                  coordinator's (lambda-sync/) are the same for every screener, no list has a
                                                  symbol twice, no screener is missing from either
    python3 check-tools/lists_check.py --full     also (about 15 minutes, monthly): every symbol still has a year of prices at
                                                  the price function (on AWS, so this machine's Yahoo allowance is not used),
                                                  and the members now, read from each index's own source where a script can
                                                  read it, against the list: who has joined, who has left

What it never does: change a list. A change is a session's work (the page's entry, the coordinator, a deploy), so that it is
tested like any other. session_start.py runs the quick part every session and says when the full one is a month old.
Writes research-data/lists_check.json (when, and what it found).
"""
import os, sys, re, json, csv, io, time, base64, datetime, importlib.util, subprocess, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); WEB = os.path.join(os.path.dirname(ROOT), 'website')
OUT = os.path.join(ROOT, 'research-data', 'lists_check.json')
PROXY = 'https://dohdeb4vpu67fa2tq3ax56ls4i0rshvm.lambda-url.us-east-1.on.aws/'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
findings = []

def page_lists():
    js = ("const vm=require('vm'),fs=require('fs');const c={window:{}};c.window=c;vm.createContext(c);"
          "vm.runInContext(fs.readFileSync(process.argv[1],'utf8')+';this.__S=SHARE_SCREENERS;',c);"
          "const o={};for(const[k,v]of Object.entries(c.__S))o[k]={name:v.name,size:v.size,list:v.list,names:(v.report||{}).names||null};console.log(JSON.stringify(o));")
    return json.loads(subprocess.run(['node', '-e', js, os.path.join(WEB, 'screeners.js')], capture_output=True, text=True, check=True).stdout)

def coord():
    spec = importlib.util.spec_from_file_location('coord', os.path.join(ROOT, 'lambda-sync', 'stockiq-screener-coordinator', 'lambda_function.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

# the page calls a few screeners by an older option number than the coordinator uses for them
ALIAS = {'3-8': '3-8', '3-100': '3-100', '3-7': '3-7', '3-3': '3-3', '3-2': '3-2', '3-4': '3-4', '3-5': '3-5', '3-6': '3-6',
         '5-50': '4-50', '5-100': '4-100', '5-200': '4-200', '5-300': '4-300', '4-ftse100': '5-ftse100'}

def quick():
    P, C = page_lists(), coord()
    for k, v in P.items():
        ck = ALIAS.get(k, k)
        if v['list'] is None:            # Russell 1000 / 2000: the workers hold the list (lists.txt); build.py checks it
            continue
        dup = sorted({s for s in v['list'] if v['list'].count(s) > 1})
        if dup: findings.append(f"{v['name']}: the page's list has {', '.join(dup)} more than once")
        cl = C.STOCK_UNIVERSES.get(ck)
        if cl is None: findings.append(f"{v['name']} ({k}): on the page but not in the coordinator"); continue
        if set(cl) != set(v['list']):
            findings.append(f"{v['name']}: the page and the coordinator differ (only on the page: {sorted(set(v['list']) - set(cl))[:8]}; only in the coordinator: {sorted(set(cl) - set(v['list']))[:8]})")
        cd = sorted({s for s in cl if cl.count(s) > 1})
        if cd: findings.append(f"{v['name']}: the coordinator's list has {', '.join(cd)} more than once")
        nums = [int(x) for x in re.findall(r'\d+', v['name'])]; nominal = set(nums) | {sum(nums)}          # a report may print the index's own number (S&P 500: 502 shares; S&P 400 + 600: 1000)
        if v['size'] != len(v['list']) and v['size'] not in nominal: findings.append(f"{v['name']}: the page's reports say {v['size']} stocks, its list has {len(v['list'])}")
    lost = [k for k in C.STOCK_UNIVERSES if k not in {ALIAS.get(p, p) for p in P} and k not in ('7-1', '7-coinspot')]
    if lost: findings.append(f"in the coordinator but not on the page: {lost}")
    print(f'quick check: {len(P)} page screeners, {len(C.STOCK_UNIVERSES)} coordinator lists')
    return P, C

def price_check(sym):
    for _ in range(3):
        try:
            with urllib.request.urlopen(f'{PROXY}?symbol={urllib.parse.quote(sym)}&range=1y', timeout=30) as r:
                d = json.load(r)['chart']['result'][0]
            return sym, len([c for c in d['indicators']['quote'][0]['close'] if c])
        except Exception:
            time.sleep(2)
    return sym, 0

def get(url, data=None):
    req = urllib.request.Request(url, data=data, headers={'User-Agent': UA})
    return urllib.request.urlopen(req, timeout=60).read()

# Each index's own members, from the sources that worked on 17 Oct 2026 (site-overview.md section 8b, the table)
def src_omx30():
    for back in range(7):            # the last trading day (a weekend or holiday answers with nothing)
        day = datetime.date.today() - datetime.timedelta(days=back)
        d = json.loads(get('https://indexes.nasdaqomx.com/Index/WeightingData', f"id=OMXS30&tradeDate={day}T00:00:00.000&timeOfDay=SOD".encode()))
        if d.get('aaData'): return {x['Symbol'].replace(' ', '-') + '.ST' for x in d['aaData']}
    raise RuntimeError('no trading day found in a week')
def src_ipc():
    rows = list(csv.reader(io.StringIO(get('https://www.blackrock.com/mx/intermediarios/productos/251895/ishares-naftrac-fund/1501904811835.ajax?fileType=csv&fileName=NAFTRAC_holdings&dataType=fund').decode('utf-8-sig'))))
    fix = {'LIVEPOLC.1': 'LIVEPOLC-1'}
    return {fix.get(r[0], r[0].replace('*', '')) + '.MX' for r in rows[3:] if len(r) > 4 and r[3] == 'Renta Variable'}
def src_kospi200():
    day = datetime.date.today()
    for back in range(7):
        try:
            d = json.loads(get(f"https://www.samsungfund.com/api/v1/kodex/product-pdf/2ETF01.do?gijunYMD={(day - datetime.timedelta(days=back)).strftime('%Y%m%d')}"))
            items = d.get('pdf', {}).get('list') or d.get('list') or []
            syms = {str(x.get('itmNo')).strip() + '.KS' for x in items if x.get('itmNo') and len(str(x.get('itmNo')).strip()) == 6}
            if len(syms) > 150: return syms
        except Exception:
            pass
    raise RuntimeError('no holdings read')
def src_bovespa():
    q = base64.b64encode(json.dumps({'language': 'en-us', 'pageNumber': 1, 'pageSize': 120, 'index': 'IBOV', 'segment': '1'}).encode()).decode()
    d = json.loads(get('https://sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetPortfolioDay/' + q))
    return {x['cod'].strip() + '.SA' for x in d['results']}
IBEX_NAMES = {"ACCIONA,S.A.": "ANA.MC", "ACERINOX, S.A.": "ACX.MC", "ACS,ACTIVIDADES DE CONST.Y SERVICIOS S.A": "ACS.MC", "AENA, S.M.E., S.A.": "AENA.MC", "AMADEUS IT GROUP, S.A.": "AMS.MC", "ARCELORMITTAL, S.A.": "MTS.MC", "BANCO BILBAO VIZCAYA ARGENTARIA, S.A.": "BBVA.MC", "BANCO DE SABADELL, S.A.": "SAB.MC", "BANCO SANTANDER, S.A.": "SAN.MC", "BANKINTER,S.A.": "BKT.MC", "CAIXABANK, S.A.": "CABK.MC", "CELLNEX TELECOM, S.A.": "CLNX.MC", "CIA. DE DIST. INTEG. LOGISTA HOLDINGS": "LOG.MC", "COLONIAL SFL, SOCIMI, S.A.": "COL.MC", "CORP.  ACCIONA ENERGÍAS RENOVABLES, S.A.": "ANE.MC", "ENAGAS, S.A.": "ENG.MC", "ENDESA, SOCIEDAD ANONIMA": "ELE.MC", "FERROVIAL N.V.": "FER.MC", "FLUIDRA, S.A.": "FDR.MC", "GRIFOLS, S.A.": "GRF.MC", "IBERDROLA, S.A.": "IBE.MC", "INDRA SISTEMAS, S.A., SERIE A": "IDR.MC", "INDUSTRIA DE DISEÑO TEXTIL, SA \"INDITEX\"": "ITX.MC", "INTERNATIONAL CONSOLIDAT. AIRLINES GROUP": "IAG.MC", "LABORATORIOS FARMACEUTICOS ROVI, S.A.": "ROVI.MC", "MAPFRE, S.A.": "MAP.MC", "MERLIN PROPERTIES, SOCIMI, S.A.": "MRL.MC", "NATURGY ENERGY GROUP, S.A.": "NTGY.MC", "PUIG BRANDS, S.A. CLASE B": "PUIG.MC", "REDEIA CORPORACION, S.A.": "RED.MC", "REPSOL, S.A.": "REP.MC", "SACYR, S.A.": "SCYR.MC", "SOLARIA ENERGIA Y MEDIO AMBIENTE, S.A.": "SLR.MC", "TELEFONICA, S.A.": "TEF.MC", "UNICAJA BANCO, S.A.": "UNI.MC"}      # the exchange's company name -> our symbol (17 Oct 2026)

def src_ibex35():
    """The exchange gives names, not tickers: a name in IBEX_NAMES is its symbol; a new name shows as "new: <name>"."""
    out = set()
    for page in range(4):
        d = json.loads(get(f'https://apiweb.bolsasymercados.es/Market/v1/EQ/ListedCompanies?tradingSystem=SIBE&page={page}&pageSize=50'))
        for r in d.get('data', []):
            if 'IBEX 35' in str(r.get('indices') or ''):
                n = (r.get('name') or '').strip(); out.add(IBEX_NAMES.get(n) or 'new: ' + n)
        if not d.get('hasMoreResults'): break
    if len(out) < 30: raise RuntimeError(f'only {len(out)} read')
    return out

KNOWN_LEFT_OUT = {'5-kospi200': {'0220W0.KS'}}     # left out on purpose: a new spin-off with too little history to score (13 Oct 2026)
SOURCES = {'5-omx30': src_omx30, '5-ipc': src_ipc, '5-kospi200': src_kospi200, '5-bovespa': src_bovespa, '5-ibex35': src_ibex35}

def full(P, C):
    syms = sorted({s for v in P.values() if v['list'] for s in v['list']})
    with ThreadPoolExecutor(10) as pool: got = dict(pool.map(price_check, syms))
    dead = [s for s, n in got.items() if n < 50]                 # the worker needs 50 days; a new listing with 50 to 250 is scored
    young = sorted(s for s, n in got.items() if 50 <= n < 200)
    owners = {s: [v['name'] for v in P.values() if v['list'] and s in v['list']] for s in dead}
    for s in dead: findings.append(f"{s} ({', '.join(owners[s])}): {'no prices at all' if got[s] == 0 else f'only {got[s]} days of prices'} (left the index, renamed, or the price source lost it)")
    print(f'prices: {len(syms)} symbols, {len(dead)} that cannot be scored; new listings with under a year (scored, fine): {", ".join(young) or "none"}')
    for k, fn in SOURCES.items():
        mine = set(C.STOCK_UNIVERSES.get(k) or [])
        try:
            now = fn()
            now -= KNOWN_LEFT_OUT.get(k, set())
        except Exception as e:
            findings.append(f"{k}: its members could not be read from the source this time ({type(e).__name__}): check by hand"); continue
        joined, left = sorted(now - mine), sorted(mine - now)
        print(f'{k}: the source has {len(now)}, the list {len(mine)}')
        if joined or left: findings.append(f"{k}: the index has changed: joined {joined or 'none'}; left {left or 'none'} (update the page's entry and the coordinator, then deploy)")

if __name__ == '__main__':
    P, C = quick()
    if '--full' in sys.argv: full(P, C)
    prev = json.load(open(OUT)) if os.path.exists(OUT) else {}
    rec = {'quick': datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%dT%H:%M:%SZ'), 'full': prev.get('full'), 'findings': findings}
    if '--full' in sys.argv: rec['full'] = rec['quick']
    os.makedirs(os.path.dirname(OUT), exist_ok=True); json.dump(rec, open(OUT, 'w'), indent=1)
    print('\nFINDINGS' + (':' if findings else ': none'))
    for i, f in enumerate(findings, 1): print(f'  {i}. {f}')
