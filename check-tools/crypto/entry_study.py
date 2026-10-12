"""What have coins done since they entered the crypto screener's top 10? READ-ONLY (the entry log and the price proxy).

    python3 check-tools/crypto/entry_study.py [hours]        entries at least this many hours old (default 6)

The owner's question (12 Oct 2026): "i think alot of those are there because they did just rise up fast. typically stocks
rise fast hit a high then drop". For shares four years of prices say no (the top 10 did about what the whole list did:
check-tools/paper-test/). For coins there are no saved prices, but the orchestrator logs every entry into the top 10 with
its price (table stockiq-coinspot-predictions, log_version 2), so this compares each entry's price then with the price
now, splits the entries by how fast the coin had risen before it entered, and prints the large coins over the last day
as a rough yardstick. Entries from before 11:52 UTC on 11 Oct 2026 are left out (they were ranked without MACD).

Read it with care: entries of one day are not independent (one market day, the same coins coming back), small coins
move further than Bitcoin both ways, and "since entering" mixes different lengths of time. Run it at each weekly check;
it becomes evidence when the same thing shows over several separate days. About 80 calls to the price proxy a run.
"""
import datetime as dt, json, re, statistics as st, sys, os, urllib.request
from concurrent.futures import ThreadPoolExecutor
import boto3
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..', '..')
FIX = dt.datetime(2026, 10, 11, 11, 52, tzinfo=dt.timezone.utc)

def main():
    least = float(sys.argv[1]) if len(sys.argv) > 1 else 6
    table = boto3.Session(profile_name='default', region_name='us-east-1').resource('dynamodb').Table('stockiq-coinspot-predictions')
    items, more = [], {}
    while True:
        page = table.scan(**more); items += page['Items']
        if 'LastEvaluatedKey' not in page: break
        more = {'ExclusiveStartKey': page['LastEvaluatedKey']}
    rows = [i for i in items if str(i.get('log_version')) == '2']
    mapping = json.dumps(json.load(open(os.path.join(ROOT, 'lambda-url-mapping.json'))))
    page_js = open(os.path.join(ROOT, '..', 'website', 'practice-portfolio.js')).read()
    proxy = next(u for u in re.findall(r"https://[a-z0-9]+\.lambda-url\.us-east-1\.on\.aws/", page_js) if 'price-proxy' in mapping[max(0, mapping.find(u) - 200):mapping.find(u) + 200])
    def quote(symbol):
        try: return symbol, json.loads(urllib.request.urlopen(proxy + '?symbol=' + symbol, timeout=20).read())['chart']['result'][0]
        except Exception: return symbol, None
    with ThreadPoolExecutor(6) as pool: quotes = dict(pool.map(quote, sorted({str(i['ticker']) + '-USD' for i in rows} | {'BTC-USD', 'ETH-USD', 'SOL-USD'})))
    now, out = dt.datetime.now(dt.timezone.utc), []
    for i in rows:
        try: when = dt.datetime.fromisoformat(str(i['prediction_time']).replace('Z', '+00:00'))
        except Exception: continue
        when = when if when.tzinfo else when.replace(tzinfo=dt.timezone.utc)
        q = quotes.get(str(i['ticker']) + '-USD'); p0 = float(i.get('entry_price') or 0); hours = (now - when).total_seconds() / 3600
        if q and p0 and hours >= least and when >= FIX:
            out.append(dict(since=(q['meta']['regularMarketPrice'] / p0 - 1) * 100, hours=hours, day=when.strftime('%d %b'), d1=float(i.get('change_24h') or 0), d7=float(i.get('change_7d') or 0), symbol=str(i['symbol'])))
    print(f"ENTRIES INTO THE COIN TOP 10 since 11 Oct 2026 11:52 UTC, at least {least:g} hours old: {len(out)} (of {len(rows)} logged), {len({x['symbol'] for x in out})} different coins, on {len({x['day'] for x in out})} days; {now:%d %b %Y %H:%M} UTC")
    if not out: return
    print(f"hours since entering: median {st.median(x['hours'] for x in out):.0f}, longest {max(x['hours'] for x in out):.0f}")
    def show(name, group):
        v = [x['since'] for x in group]
        if len(v) < 3: print(f"  {name:<40} {len(v):>3} entries: too few"); return
        print(f"  {name:<40} {len(v):>3} entries   since entering: average {st.mean(v):+6.2f}% (± {st.stdev(v) / len(v) ** 0.5:.2f})   median {st.median(v):+6.2f}%   up {sum(1 for a in v if a > 0)}, down {sum(1 for a in v if a < 0)}")
    show('all entries', out)
    print('by its rise in the 24 hours before it entered:')
    show('  up 10% or more', [x for x in out if x['d1'] >= 10]); show('  up 3% to 10%', [x for x in out if 3 <= x['d1'] < 10]); show('  under 3%, or down', [x for x in out if x['d1'] < 3])
    print('by its rise in the 7 days before it entered:')
    show('  up 20% or more', [x for x in out if x['d7'] >= 20]); show('  up 5% to 20%', [x for x in out if 5 <= x['d7'] < 20]); show('  under 5%, or down', [x for x in out if x['d7'] < 5])
    print('by the day it entered:')
    for day in sorted({x['day'] for x in out}, key=lambda d: dt.datetime.strptime(d, '%d %b')): show('  ' + day, [x for x in out if x['day'] == day])
    print('the large coins over the last day, for scale (now against yesterday\'s close):')
    for s in ('BTC-USD', 'ETH-USD', 'SOL-USD'):
        q = quotes.get(s)
        if q:
            closes = [c for c in q['indicators']['quote'][0]['close'] if c]; print(f"  {s}: {(q['meta']['regularMarketPrice'] / closes[-2] - 1) * 100:+.2f}%")

if __name__ == '__main__':
    main()
