import json
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

# Prices for a list of symbols (shares, indices, coins, currencies), as Yahoo's one-day chart gives them.
# 18 Oct 2026: the symbols are fetched side by side (26 took 9 seconds one after the other; Lambda bills by the second), each
# with a time limit, at most MAX_TICKERS a call; with "spark": true each answer also carries `spark`, today's prices thinned to
# about SPARK_POINTS points, for the small charts of the market-data side panel (live-market.js), which were made-up lines.
MAX_TICKERS = 40
SPARK_POINTS = 30
FETCH_TIMEOUT = 6


def one(ticker, spark):
    try:
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}?interval=1m&range=1d'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as response:
            data = json.loads(response.read())
        res = data['chart']['result'][0]
        quote = res['meta']
        price = quote.get('regularMarketPrice', quote.get('chartPreviousClose', 0))
        prev_close = quote.get('chartPreviousClose', quote.get('previousClose', price))
        change = price - prev_close
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
        name = quote.get('longName', quote.get('shortName', ticker))
        out = {'name': name, 'price': round(price, 2), 'change': round(change, 2), 'changePercent': round(change_pct, 2), 'error': False}
        if spark:
            closes = [c for c in (((res.get('indicators') or {}).get('quote') or [{}])[0].get('close') or []) if c is not None]
            if len(closes) >= 2:
                step = max(1, len(closes) // SPARK_POINTS)
                pts = closes[::step]
                if pts[-1] != closes[-1]:
                    pts.append(closes[-1])
                out['spark'] = [round(p, 4) for p in pts]
                out['prev'] = round(prev_close, 4)
        return out
    except Exception as e:
        return {'error': True, 'message': str(e)}


def lambda_handler(event, context):
    # Handle OPTIONS preflight
    if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return {
            'statusCode': 200,
            'body': ''
        }

    # Get tickers from query string or body
    tickers, spark = [], False
    try:
        if event.get('queryStringParameters') and event['queryStringParameters'].get('tickers'):
            tickers = event['queryStringParameters']['tickers'].split(',')
        elif event.get('body'):
            body = json.loads(event['body'])
            tickers = body.get('tickers', [])
            spark = bool(body.get('spark'))
        if not tickers:
            tickers = ['NVDA', 'TSLA', 'AAPL', 'MSFT']
    except Exception as e:
        print(f"Error parsing tickers: {e}")
        tickers = ['NVDA', 'TSLA', 'AAPL', 'MSFT']

    tickers = list(dict.fromkeys(str(t).strip() for t in tickers if str(t).strip()))[:MAX_TICKERS]
    with ThreadPoolExecutor(max_workers=12) as pool:
        answers = list(pool.map(lambda t: one(t, spark), tickers))
    result = dict(zip(tickers, answers))

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'success': True,
            'data': result
        })
    }
