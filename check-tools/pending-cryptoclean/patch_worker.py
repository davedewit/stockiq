"""The crypto worker after a review of its code (11 Oct 2026). No score changes: for a coin with complete prices the
answer is the same, figure for figure (worker_test.py proves it on recorded answers of the price source).
    python3 patch_worker.py <live lambda_function.py> <out lambda_function.py>
 1. One request to the price source per coin where there were two (30 days for the changes, then 90 days for the rest:
    the second holds everything the first does).
 2. A day's high, low, close and volume stay together: each was filtered for missing values by itself, so one missing
    value shifted that list against the others.
 3. The old mode is gone: called with no coin, the worker used to analyse ten coins of a 540-coin CoinSpot list written
    into this file (stablecoins and dead coins among them), read one table and scan another for each, and write a
    report nobody saw. The worker's address is public; nothing on the site has called that mode since 10 Oct 2026.
    With it go the list, the report writer, the two database routines, a page scraper and the database library."""
import sys
src = open(sys.argv[1]).read()
def swap(text, old, new):
    assert text.count(old) == 1, (text.count(old), old[:80])
    return text.replace(old, new)
def cut(text, start, end, new):
    a = text.index(start); b = text.index(end, a + len(start))
    assert text.count(start) == 1 and text.count(end) >= 1, (start[:60], end[:60])
    return text[:a] + new + text[b:]

src = swap(src, "import requests\nimport json\nimport boto3\nfrom datetime import datetime, timedelta\n", '''"""The crypto screener's worker: one coin, or a list of coins, analysed from daily prices (Yahoo Finance).

The 54 stockiq-option-7-1-worker-N functions all run this file. stockiq-option-7-1-orchestrator holds the coin list and
sends it out ten coins a call ({"coin_list": [...]}); {"single_coin": "..."} analyses one. Called with neither, it
answers that there is nothing to do. How a coin is scored: site-overview.md section 8b, "How a coin is scored".
"""
import requests
import json
import time
from datetime import datetime, timedelta
''')
# 3. the built-in list and the routines only the old mode used
src = cut(src, "    def __init__(self):\n", "    def calculate_macd(", "    def __init__(self):\n        pass\n\n")
src = cut(src, "    def fetch_yahoo_data(self, symbol: str)", "    def calculate_bollinger_bands(", r'''    def fetch_bars(self, symbol: str) -> List[Dict]:
        """90 days of daily prices from Yahoo Finance (USD), oldest first, one dict a day: timestamp, high, low, close,
        volume. A day without a closing price is left out whole, so the figures of a day always stay together."""
        try:
            end_time = int(time.time())
            # 90 days: MACD needs 35 days of prices (with the 30 that were once asked for it was never worked out)
            start_time = end_time - (90 * 24 * 60 * 60)
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}-USD"
            params = {'period1': start_time, 'period2': end_time, 'interval': '1d'}
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
            response = requests.get(url, params=params, headers=headers, timeout=8)
            if response.status_code != 200:
                return []
            result = response.json()['chart']['result'][0]
            quotes = result['indicators']['quote'][0]
            closes = quotes.get('close') or []
            highs, lows, volumes = quotes.get('high') or [], quotes.get('low') or [], quotes.get('volume') or []
            pick = lambda values, i, fallback: values[i] if i < len(values) and values[i] is not None else fallback
            bars = []
            for i, timestamp in enumerate(result.get('timestamp') or []):
                close = pick(closes, i, None)
                if close is None:
                    continue
                bars.append({'timestamp': timestamp, 'high': pick(highs, i, close), 'low': pick(lows, i, close),
                             'close': close, 'volume': pick(volumes, i, 0)})
            return bars
        except Exception as e:
            print(f"Yahoo Finance error for {symbol}: {e}")
            return []

''')
src = swap(src, '''        historical_prices, change_24h, change_7d, change_30d = self.fetch_yahoo_data(symbol)
        current_price = historical_prices[-1] if historical_prices else 0
''', '''        # One request (it used to be two: 30 days for the changes, then 90 for everything else)
        bars = self.fetch_bars(symbol)
        # The last 30 days, counted as the price source counts them: from the start of the day 30 days back
        month_start = ((int(time.time()) - 30 * 24 * 60 * 60) // 86400) * 86400
        historical_prices = [bar['close'] for bar in bars if bar['timestamp'] >= month_start]
        change_24h = change_7d = change_30d = 0
        if len(historical_prices) > 7:
            current = historical_prices[-1]
            change_24h = ((current - historical_prices[-2]) / historical_prices[-2]) * 100
            change_7d = ((current - historical_prices[-8]) / historical_prices[-8]) * 100 if len(historical_prices) >= 8 else 0
            change_30d = ((current - historical_prices[0]) / historical_prices[0]) * 100
        else:
            historical_prices = []
        current_price = historical_prices[-1] if historical_prices else 0
''')
src = cut(src, "        # Get full OHLCV data for comprehensive analysis (USD only)\n", "        # COMPREHENSIVE TECHNICAL ANALYSIS", '''        # MACD is worked out on all 90 days; everything else on the last 31, as before
        highs = [bar['high'] for bar in bars]
        lows = [bar['low'] for bar in bars]
        closes = [bar['close'] for bar in bars]
        volumes = [bar['volume'] for bar in bars]
        macd_closes = closes[:]
        highs, lows, closes, volumes = highs[-31:], lows[-31:], closes[-31:], volumes[-31:]
        
''')
src = cut(src, "    def generate_report(self, analyzed_coins=None) -> str:", "def lambda_handler(event=None, context=None):", "")
a = src.index("        # Default multi-coin worker mode\n")
src = src[:a] + '''        # Nothing to do without a coin. (Until 11 Oct 2026 the worker then analysed ten coins of a list written into this
        # file; the orchestrator has driven the list itself since 10 Oct, and this address is public.)
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Nothing to analyse: send {"coin_list": [...]} or {"single_coin": "..."}', 'coins': [], 'status': 'error'})
        }
        
    except Exception as e:
        print(f"❌ Lambda error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e), 'coins': [], 'status': 'error'})
        }


# A run by hand (it asks the price source): python3 lambda_function.py BTC ETH SUI20947
if __name__ == "__main__":
    import sys
    answer = json.loads(lambda_handler({'body': json.dumps({'coin_list': sys.argv[1:] or ['BTC', 'ETH']})}, None)['body'])
    for item in answer.get('results', []):
        coin = item['coin'] or {}
        print(f"{item['ticker']:<12} {coin.get('price', 0):>14.6f}  score {coin.get('score', 0):+d}  {coin.get('recommendation', '-'):<11} " + '; '.join(coin.get('score_breakdown', [])))
'''
src = swap(src, "                analytics = CryptoAnalytics()\n                results = []\n", "                analytics = CryptoAnalytics()\n                results = []\n")
assert 'boto3' not in src and 'target_coins' not in src and 'coinspot' not in src.lower().replace('stockiq-coinspot', ''), [l for l in src.split('\n') if 'coinspot' in l.lower() or 'boto3' in l or 'target_coins' in l][:4]
assert 'import time\n            end_time' not in src
compile(src, 'lambda_function.py', 'exec'); open(sys.argv[2], 'w').write(src); print('written:', len(src.split('\n')), 'lines (it was', len(open(sys.argv[1]).read().split('\n')), ')')
