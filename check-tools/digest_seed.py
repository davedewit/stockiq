"""Start the progress score's history (1 Nov 2026): one row a US trading day from the account's start, from the dashboard's own
sums (versus_market.js), and the starting point for the next day, in item _digest of stockiq-ai-trader. Run once; it refuses
when the item exists (the function keeps it from then on). The score: 50, and 10 points for each 1% a day the account did better
than an S&P 500 fund (a point off for each 0.1% worse).
    python3 check-tools/digest_seed.py <seed.json>     (days and last, as worked out by a dry run of write_digests)"""
import json, sys, boto3
t = boto3.Session(profile_name='default', region_name='us-east-1').resource('dynamodb').Table('stockiq-ai-trader')
if t.get_item(Key={'userId': '_digest'}).get('Item'):
    sys.exit('_digest exists already: nothing written')
seed = json.load(open(sys.argv[1]))
t.put_item(Item={'userId': '_digest', 'enabled': False, 'data': json.dumps({'days': seed['days'], 'last': seed['last'], 'owner': None}, separators=(',', ':'))})
print(f"written: {len(seed['days'])} days, score {seed['days'][-1]['score']}, starting point {seed['last']['d']}")
