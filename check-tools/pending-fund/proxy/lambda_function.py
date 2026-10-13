import json
import urllib.request

def lambda_handler(event, context):
    try:
        symbol = event.get('queryStringParameters', {}).get('symbol', '')
        if not symbol:
            return {'statusCode': 400, 'body': json.dumps({'error': 'Symbol required'})}
        
        # Daily prices for the last month, unless a longer stretch is asked for (the practice portfolio's graph asks for the
        # S&P 500 fund back to the day an account began). Anything not in this list is answered with the month, as before.
        span = (event.get('queryStringParameters') or {}).get('range', '')
        if span not in ('3mo', '6mo', '1y', '2y', '5y'):
            span = '1mo'
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={span}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req) as response:
            data = response.read().decode('utf-8')
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'},
            'body': data
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }
