import json, urllib.request, time, sys
out = {}; pages = 0
for page in range(1, 25):
    url = f'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page={page}'
    for attempt in range(6):
        try:
            d = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30).read()); break
        except Exception as e:
            d = None; time.sleep(20 + attempt * 15)
    if not d: print('gave up at page', page, flush=True); break
    for c in d:
        out.setdefault(c['symbol'].upper(), []).append({'name': c['name'], 'price': c.get('current_price'), 'rank': c.get('market_cap_rank'), 'mcap': c.get('market_cap')})
    pages += 1; print('page', page, 'coins so far', sum(len(v) for v in out.values()), flush=True)
    json.dump(out, open('coingecko.json', 'w')); time.sleep(8)
print('CG_DONE pages', pages, flush=True)
