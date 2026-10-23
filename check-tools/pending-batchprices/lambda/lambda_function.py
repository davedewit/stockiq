import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

RANGES = ('3mo', '6mo', '1y', '2y', '5y')
MAX_SYMBOLS = 40          # symbols one request may ask for (?symbols=A,B,C)
SIDE_BY_SIDE = 10         # of them fetched from the price source at once


def chart(symbol, span):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?interval=1d&range={span}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=8) as response:
        return response.read().decode('utf-8')


def lambda_handler(event, context):
    try:
        params = event.get('queryStringParameters') or {}
        # Daily prices for the last month, unless a longer stretch is asked for (the practice portfolio's graph asks for the
        # S&P 500 fund back to the day an account began). Anything not in this list is answered with the month, as before.
        span = params.get('range', '')
        if span not in RANGES:
            span = '1mo'

        # Many symbols in one request (23 Oct 2026): a browser sends only six requests at a time to one address, so the practice
        # portfolio's 60 single calls took about 15 seconds. Answer: {"results": {symbol: <the price source's answer, or null>}}.
        many = params.get('symbols', '')
        if many:
            symbols = list(dict.fromkeys(s.strip() for s in many.split(',') if s.strip()))[:MAX_SYMBOLS]

            def one(symbol):
                try:
                    return symbol, json.loads(chart(symbol, span))
                except Exception:
                    return symbol, None
            with ThreadPoolExecutor(SIDE_BY_SIDE) as pool:
                results = dict(pool.map(one, symbols))
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'},
                'body': json.dumps({'results': results}, separators=(',', ':'))
            }

        symbol = params.get('symbol', '')
        if not symbol:
            return {'statusCode': 400, 'body': json.dumps({'error': 'Symbol required'})}
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'},
            'body': chart(symbol, span)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }
