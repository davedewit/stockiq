import json, urllib.request, urllib.parse, time, re
cg = json.load(open('coingecko.json'))
flat = [dict(sym=s, **c) for s, lst in cg.items() for c in lst if c.get('rank') and c.get('price')]
flat.sort(key=lambda c: c['rank'])
STABLE = {'USDT','USDC','DAI','FDUSD','TUSD','PYUSD','USDE','USDS','USD1','FRAX','LUSD','GUSD','USDP','USDD','USDX','USD0','USDB','USDG','RLUSD','BUSD','EURC','EURT','EURS','SUSD','CRVUSD','GHO','DOLA','USTC','BFUSD','USDF','USDY','USDL','USDTB','SUSDE','SUSDS','USYC','BUIDL','OUSG'}
DERIV = re.compile(r'wrapped|staked|bridged|restaked|liquid stak|staking|binance-peg|wormhole|tokenized|\bsteth\b|\(pos\)|\bpeg\b|l2 standard|vault|savings|usd|dollar|euro\b|treasury|t-bill|yield', re.I)
def is_excluded(c):
    if c['sym'] in STABLE: return True
    if DERIV.search(c['name']): return True
    if 0.97 <= c['price'] <= 1.03 and re.search(r'usd|dollar', c['sym'] + c['name'], re.I): return True
    if not re.fullmatch(r'[A-Z0-9]{2,10}', c['sym']): return True
    return False
def get(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=15).read())
def yahoo(base):
    try:
        m = get(f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(base)}-USD?range=1y&interval=1d')['chart']['result'][0]
        closes = [x for x in m['indicators']['quote'][0].get('close', []) if x]
        return m['meta'].get('regularMarketPrice'), m['meta'].get('shortName') or m['meta'].get('longName'), len(closes)
    except Exception: return None, None, 0
def near(a, b): return a and b and 0.8 <= a / b <= 1.25
accepted = []; skipped = []; seen = set(); n_probe = 0
for c in flat:
    if len(accepted) >= 560 or c['rank'] > 1100: break
    if c['sym'] in seen or is_excluded(c):
        continue
    seen.add(c['sym'])
    p, name, days = yahoo(c['sym']); n_probe += 1; time.sleep(0.2)
    if near(p, c['price']) and days >= 60:
        accepted.append(dict(symbol=c['sym'], yahoo=c['sym'], name=c['name'], rank=c['rank'], days=days)); continue
    found = None
    try:
        q = get('https://query2.finance.yahoo.com/v1/finance/search?quotesCount=8&newsCount=0&q=' + urllib.parse.quote(c['name']))
        cands = [x['symbol'][:-4] for x in q.get('quotes', []) if x.get('quoteType') == 'CRYPTOCURRENCY' and x.get('symbol', '').endswith('-USD')]
    except Exception: cands = []
    time.sleep(0.25)
    for base in cands[:5]:
        if base == c['sym']: continue
        p2, name2, days2 = yahoo(base); n_probe += 1; time.sleep(0.2)
        if near(p2, c['price']) and days2 >= 60 and re.fullmatch(r'[A-Z0-9]{2,16}', base):
            found = dict(symbol=c['sym'], yahoo=base, name=c['name'], rank=c['rank'], days=days2); break
    if found: accepted.append(found)
    else: skipped.append(dict(symbol=c['sym'], name=c['name'], rank=c['rank'], yahoo_price=p, cg_price=c['price'], days=days))
    if (len(accepted) + len(skipped)) % 50 == 0:
        print(f'rank {c["rank"]}: accepted {len(accepted)} skipped {len(skipped)} probes {n_probe}', flush=True)
        json.dump({'accepted': accepted, 'skipped': skipped}, open('crypto_new.json', 'w'))
json.dump({'accepted': accepted, 'skipped': skipped}, open('crypto_new.json', 'w'))
print('CRYPTO_DONE accepted', len(accepted), 'skipped', len(skipped), flush=True)
