"""The share-screener worker: ONE file for every share screener on the site.

Every stockiq-option-3-{1,2,4,5,6,7,8}-worker-N, stockiq-asia-5-{1..5}-worker-N and stockiq-europe-4-1-worker-N function runs
this file (669 functions; the package is the same zip in all of them). It is given a batch of symbols, fetches a year of
daily prices for each from Yahoo, and returns the figures and the score; it writes no report text (the page and the
coordinator do that). The scoring is price, momentum and volume only: the "financial", "sentiment" and "risk" factors do
not use real company data.

Change it here, in git, never in the AWS console:
    python3 workers/prove.py        # what a change does to scores, on saved prices, against the copy that is live
    python3 workers/build.py        # the package (workers.zip) and its fingerprint
and deploy with a packaged script (site-overview.md section 8b, "The worker groups").

Before 11 Oct 2026 there were seven copies of this file that had drifted apart (two ways of working out RSI, a different
"financial" factor in the NASDAQ 100 and Dow 30 workers, lists of dead tickers in the Russell packages). This is the
ASX / Nikkei copy with the UK sectors, and with these faults fixed: a session that Yahoo sends twice (the ASX after its
close: the 24-hour change was 0), a latest session that arrives empty (London: prices a day old), SPY fetched once per
batch instead of once per stock.
"""
import json
import os
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
import math

# The currency Yahoo quotes each symbol in ('USD', 'AUD', 'JPY', 'GBp' = pence), filled as prices are fetched
CURRENCY = {}

# Which score the workers give (17 Oct 2026). 1: the original 12-factor score. 2: the trend score, built from what the score
# studies found on 1,750 shares in nine markets it was never tuned on (check-tools/scoring/: the original score's top 10 lost
# to its own list in 17 of 18 half-periods; a trend score's won 12). Left at 1 until the owner says yes; a test sets
# STOCKIQ_SCORE=2. Turning it back is this one line.
SCORE_VERSION = int(os.environ.get('STOCKIQ_SCORE', '1'))
# Where the labels change: HOLD above the first, MODERATE_SELL down to the second, SELL down to the third, STRONG_SELL below.
# Version 1 keeps its old numbers exactly (with them MODERATE_SELL is only given at exactly -0.8, as it always was); version 2
# has even steps, so that "Slightly negative" is given.
SELL_BANDS = {1: (-0.8, -0.8, -1.3), 2: (-0.5, -1.0, -1.5)}[SCORE_VERSION]
# The trend score runs higher on the positive side than the old one (its 91st percentile 4.0 against 2.4 on the S&P 100 over
# four years), which would call 30% of shares "Strongly positive". Its positive side is shrunk by this factor so that the
# labels are spread about as before (about 9%); the order of every ranking is unchanged.
TREND_POSITIVE_SCALE = 0.6


def trend_score(change_1yr, change_30d, distance_from_low, price, ma50, ma200, rsi):
    """The trend score (version 2), exactly as written down before the wide study's result was seen
    (check-tools/scoring/wide_study.py, "trend"): how far above its 52-week low (up to +2 at 100% above), the year's rise
    without the last month (up to +-1.5 at 60%), the price against its 200-day average (+-0.5), the 50-day average against the
    200-day (+-0.5), and -0.5 when RSI is over 80. Returns (score, the lines that explain it)."""
    mom = ((1 + change_1yr / 100) / (1 + change_30d / 100) - 1) * 100 if change_30d > -100 else 0
    a = min(2.0, max(0.0, distance_from_low) / 50)
    b = max(-1.5, min(1.5, mom / 40))
    c = 0.5 if price > ma200 else -0.5
    d = 0.5 if ma50 > ma200 else -0.5
    e = -0.5 if rsi > 80 else 0.0
    lines = [f"Above its 52-week low ({distance_from_low:.1f}%): +{a:.2f}",
             f"Rise over the year without the last month ({mom:+.1f}%): {b:+.2f}",
             f"Price {'above' if c > 0 else 'below'} its 200-day average: {c:+.2f}",
             f"50-day average {'above' if d > 0 else 'below'} the 200-day: {d:+.2f}"]
    if e:
        lines.append(f"RSI over 80, overheated ({rsi:.1f}): {e:+.2f}")
    raw = a + b + c + d + e
    score = raw * TREND_POSITIVE_SCALE if raw > 0 else raw
    lines.append(f"TREND SCORE: {raw:.2f}" + (f" x {TREND_POSITIVE_SCALE} = {score:.1f}" if raw > 0 else ""))
    return score, lines

def lambda_handler(event, context):
    """AWS Lambda entry point"""
    try:
        # Handle both HTTP requests (Lambda URL) and direct invocations
        if 'body' in event:
            # HTTP request - parse JSON body
            try:
                body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
                result = handle_batch_processing(body, context)
            except (json.JSONDecodeError, TypeError):
                result = {'success': False, 'error': 'Invalid JSON in request body', 'stocks_analyzed': 0}
        else:
            # Direct invocation
            result = handle_batch_processing(event, context)
        
        # Always return HTTP format for Lambda URLs
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps(result)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'success': False, 'error': str(e), 'stocks_analyzed': 0})
        }

def bars_from_chart(result):
    """Daily bars from one Yahoo chart result, oldest first, one bar per trading day"""
    if 'timestamp' not in result or 'indicators' not in result:
        return None
        
    timestamps = result['timestamp']
    if not result['indicators']['quote']:
        return None
        
    ohlcv = result['indicators']['quote'][0]
    required_keys = ['open', 'high', 'low', 'close', 'volume']
    
    if not all(key in ohlcv for key in required_keys):
        return None
    
    meta = result.get('meta') or {}
    offset = meta.get('gmtoffset') or 0
    
    def day(timestamp):
        # The trading day a time belongs to, on the exchange's own clock
        return (int(timestamp) + offset) // 86400
    
    stock_data = []
    for i in range(len(timestamps)):
        try:
            if all(ohlcv[key][i] is not None for key in required_keys):
                bar = {
                    'timestamp': timestamps[i],
                    'open': float(ohlcv['open'][i]),
                    'high': float(ohlcv['high'][i]),
                    'low': float(ohlcv['low'][i]),
                    'close': float(ohlcv['close'][i]),
                    'volume': int(ohlcv['volume'][i])
                }
                # Once a market has closed Yahoo can send its last session twice (seen on the ASX: the daily bar and the
                # closing quote). Two bars for one day made the 24-hour change 0: keep one bar a day, the later one.
                if stock_data and day(stock_data[-1]['timestamp']) == day(bar['timestamp']):
                    stock_data[-1] = bar
                else:
                    stock_data.append(bar)
        except (ValueError, TypeError):
            continue
    
    # The latest session can arrive with empty figures (seen for London shares the morning after), which left the
    # price a trading day old. The quote that comes with the chart has that session: use it as the last bar.
    price = meta.get('regularMarketPrice')
    quoted = meta.get('regularMarketTime')
    if (stock_data and isinstance(price, (int, float)) and price > 0 and isinstance(quoted, (int, float))
            and day(quoted) > day(stock_data[-1]['timestamp'])):
        high = meta.get('regularMarketDayHigh')
        low = meta.get('regularMarketDayLow')
        volume = meta.get('regularMarketVolume')
        stock_data.append({
            'timestamp': int(quoted),
            'open': stock_data[-1]['close'],
            'high': float(max(high, price)) if isinstance(high, (int, float)) else float(price),
            'low': float(min(low, price)) if isinstance(low, (int, float)) and low > 0 else float(price),
            'close': float(price),
            'volume': int(volume) if isinstance(volume, (int, float)) else 0
        })
    
    return stock_data

def get_stock_data(symbol, period='1y'):
    """Fetch comprehensive stock data from Yahoo Finance with improved error handling"""
    if not symbol or not isinstance(symbol, str):
        return None
        
    try:
        end_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(days=365)).timestamp())
        
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}"
        params = {
            'period1': start_time,
            'period2': end_time,
            'interval': '1d',
            'includePrePost': 'false'
        }
        
        req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}")
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.getcode() != 200:
                return None
            data = json.loads(response.read())
        
        if not data or 'chart' not in data or not data['chart']['result']:
            return None
            
        result = data['chart']['result'][0]
        stock_data = bars_from_chart(result)
        if not stock_data:
            return None
        
        if len(stock_data) < 20:  # Need minimum data for analysis
            return None
        
        CURRENCY[symbol.upper()] = (result.get('meta') or {}).get('currency') or ''
        return stock_data[-252:] if len(stock_data) > 252 else stock_data
        
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error for {symbol}: {e}")
        return None

def calculate_rsi(closes, period=14):
    """Calculate RSI using Wilder's smoothing method"""
    if len(closes) < period + 1:
        return 50
    
    # Calculate price changes
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]
    
    # First average (SMA for first period)
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # Wilder's smoothing for subsequent periods
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_macd(closes, fast=12, slow=26, signal=9):
    """Calculate MACD"""
    if len(closes) < slow:
        return 0, 0, 0
    
    def ema(data, period):
        multiplier = 2 / (period + 1)
        ema_values = [data[0]]
        for price in data[1:]:
            ema_values.append((price * multiplier) + (ema_values[-1] * (1 - multiplier)))
        return ema_values
    
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    
    # Align arrays - ema_fast is longer than ema_slow
    start_idx = len(ema_fast) - len(ema_slow)
    macd_line = [ema_fast[i + start_idx] - ema_slow[i] for i in range(len(ema_slow))]
    signal_line = ema(macd_line, signal)
    histogram = [macd_line[i] - signal_line[i] for i in range(len(signal_line))]
    
    return macd_line[-1], signal_line[-1], histogram[-1]

def calculate_bollinger_bands(closes, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    if len(closes) < period:
        return None, None, None
    
    sma = sum(closes[-period:]) / period
    variance = sum([(x - sma) ** 2 for x in closes[-period:]]) / period
    std = math.sqrt(variance)
    
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    
    return upper, sma, lower

def calculate_stochastic(highs, lows, closes, k_period=14, d_period=3):
    """Calculate Stochastic Oscillator with proper %D calculation"""
    if len(closes) < k_period + d_period - 1:
        return 50, 50
    
    # Calculate %K values for the last d_period days
    k_values = []
    for i in range(d_period):
        end_idx = len(closes) - d_period + i + 1
        start_idx = max(0, end_idx - k_period)
        
        period_lows = lows[start_idx:end_idx]
        period_highs = highs[start_idx:end_idx]
        period_close = closes[end_idx - 1]
        
        if not period_lows or not period_highs:
            k_values.append(50)
            continue
            
        lowest_low = min(period_lows)
        highest_high = max(period_highs)
        
        if highest_high == lowest_low:
            k_values.append(50)
        else:
            k_percent = ((period_close - lowest_low) / (highest_high - lowest_low)) * 100
            k_values.append(max(0, min(100, k_percent)))
    
    # %K is the most recent value
    k_percent = k_values[-1]
    
    # %D is the moving average of %K values
    d_percent = sum(k_values) / len(k_values)
    
    return k_percent, d_percent

def calculate_atr(highs, lows, closes, period=14):
    """Calculate Average True Range"""
    if len(closes) < period + 1:
        return 0
    
    true_ranges = []
    for i in range(1, len(closes)):
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i-1])
        tr3 = abs(lows[i] - closes[i-1])
        true_ranges.append(max(tr1, tr2, tr3))
    
    return sum(true_ranges[-period:]) / period

def get_market_context():
    """Get S&P 500 context for market regime detection"""
    try:
        spy_data = get_stock_data('SPY')
        if not spy_data or len(spy_data) < 20:
            return 'NEUTRAL', 0
        
        spy_closes = [d['close'] for d in spy_data]
        if len(spy_closes) > 20:
            spy_20d_change = ((spy_closes[-1] - spy_closes[-21]) / spy_closes[-21]) * 100
        else:
            spy_20d_change = 0
        
        if spy_20d_change < -10:
            return 'BEAR', spy_20d_change
        elif spy_20d_change > 10:
            return 'BULL', spy_20d_change
        else:
            return 'NEUTRAL', spy_20d_change
    except:
        return 'NEUTRAL', 0

def get_sector_info(symbol):
    """Get sector classification and performance"""
    # ASX stocks (Australian)
    if symbol.endswith('.AX'):
        asx_sectors = {
            'TECH': ['XRO.AX', 'APT.AX', 'CPU.AX', 'NXT.AX', 'TNE.AX', 'Z1P.AX', 'KGN.AX', 'REA.AX'],
            'FINANCE': ['CBA.AX', 'ANZ.AX', 'WBC.AX', 'NAB.AX', 'MQG.AX', 'QBE.AX', 'IAG.AX', 'SUN.AX', 'AMP.AX', 'BOQ.AX'],
            'HEALTHCARE': ['CSL.AX', 'COH.AX', 'RHC.AX', 'SHL.AX', 'PME.AX', 'RMD.AX', 'FPH.AX', 'NAN.AX'],
            'RESOURCES': ['BHP.AX', 'RIO.AX', 'FMG.AX', 'STO.AX', 'WDS.AX', 'S32.AX', 'NCM.AX', 'MIN.AX', 'EVN.AX', 'NST.AX'],
            'CONSUMER': ['WOW.AX', 'WES.AX', 'COL.AX', 'JHX.AX', 'TWE.AX', 'DMP.AX', 'HVN.AX', 'SUL.AX'],
            'INDUSTRIAL': ['TCL.AX', 'ALL.AX', 'ASX.AX', 'WTC.AX', 'ALD.AX', 'LLC.AX', 'DXS.AX', 'GMG.AX']
        }
        
        for sector, stocks in asx_sectors.items():
            if symbol in stocks:
                return sector
        return 'OTHER'
    
    # UK stocks (London Stock Exchange)
    if symbol.endswith('.L'):
        uk_sectors = {
            'FINANCE': ['LLOY.L', 'BARC.L', 'HSBA.L', 'NWG.L', 'STAN.L', 'PRU.L', 'LSEG.L'],
            'ENERGY': ['BP.L', 'SHEL.L', 'GLEN.L', 'RIO.L', 'BHP.L', 'AAL.L', 'ANTO.L'],
            'CONSUMER': ['TSCO.L', 'ULVR.L', 'SBRY.L', 'BRBY.L', 'JD.L', 'MNDI.L', 'BATS.L'],
            'HEALTHCARE': ['AZN.L', 'GSK.L', 'HLMA.L', 'SMGK.L'],
            'TECH': ['VOD.L', 'BT-A.L', 'EXPN.L', 'SAGE.L', 'OCDO.L', 'AUTO.L'],
            'INDUSTRIAL': ['REL.L', 'NG.L', 'IAG.L', 'CRH.L', 'WEIR.L', 'RR.L', 'RYCEY.L']
        }
        
        for sector, stocks in uk_sectors.items():
            if symbol in stocks:
                return sector
        return 'OTHER'
    
    # US stocks
    sectors = {
        'TECH': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'ADBE', 'CRM', 'NFLX', 'AMD'],
        'FINANCE': ['JPM', 'BAC', 'WFC', 'GS', 'C', 'MS', 'AXP', 'BLK', 'SCHW'],
        'HEALTHCARE': ['UNH', 'JNJ', 'PFE', 'LLY', 'ABBV', 'MRK', 'TMO', 'DHR', 'BMY'],
        'CONSUMER': ['WMT', 'HD', 'PG', 'KO', 'PEP', 'COST', 'LOW', 'TGT', 'NKE'],
        'ENERGY': ['XOM', 'CVX', 'COP', 'EOG', 'SLB', 'MPC', 'PSX'],
        'INDUSTRIAL': ['CAT', 'BA', 'HON', 'UNP', 'RTX', 'LMT', 'MMM', 'GE']
    }
    
    for sector, stocks in sectors.items():
        if symbol in stocks:
            return sector
    return 'OTHER'

def check_earnings_risk(symbol):
    """Check if stock is near earnings (simplified)"""
    # Earnings typically occur quarterly - this is a simplified check
    # In reality, you'd need an earnings calendar API
    import datetime
    now = datetime.datetime.now()
    
    # Assume earnings risk during certain periods (simplified)
    high_risk_months = [1, 4, 7, 10]  # Typical earnings months
    if now.month in high_risk_months:
        # Higher risk during earnings season
        return 'HIGH'
    return 'LOW'

def get_fundamentals(symbol):
    """Get estimated fundamental data based on symbol characteristics"""
    # Since Yahoo Finance API is restricted, use estimated values based on known stock characteristics
    market_cap = 'Large'
    beta = 1.0
    dividend_yield = 0
    pe_ratio = 25.0  # Default P/E ratio
    
    # Estimated P/E ratios based on known stock characteristics
    pe_estimates = {
        'AAPL': 28.5, 'MSFT': 32.1, 'GOOGL': 24.8, 'AMZN': 45.2, 'NVDA': 65.3,
        'META': 22.7, 'TSLA': 58.9, 'BRK-B': 8.2, 'AVGO': 29.4, 'LLY': 42.1,
        'JPM': 12.8, 'V': 31.5, 'UNH': 24.3, 'XOM': 13.7, 'JNJ': 15.9,
        'WMT': 26.8, 'PG': 24.1, 'MA': 33.2, 'HD': 22.4, 'CVX': 14.2,
        'ABBV': 14.8, 'BAC': 11.9, 'KO': 25.3, 'PEP': 24.7, 'TMO': 28.9,
        'COST': 38.4, 'MRK': 16.2, 'ADBE': 41.7, 'WFC': 10.8, 'LIN': 35.6,
        'ACN': 27.3, 'NFLX': 34.8, 'AMD': 52.1, 'CRM': 48.3, 'DHR': 31.2,
        'VZ': 8.9, 'NEE': 22.1, 'TXN': 34.7, 'PM': 17.4, 'RTX': 19.8,
        'SPGI': 42.9, 'LOW': 21.6, 'QCOM': 18.3, 'UNP': 24.8, 'INTU': 58.2,
        'IBM': 22.4, 'CAT': 16.7, 'GS': 13.2, 'BKNG': 26.1, 'HON': 28.3
    }
    
    # Estimated dividend yields for common dividend-paying stocks
    dividend_stocks = {
        'AAPL': 0.5, 'MSFT': 0.7, 'JNJ': 2.9, 'PG': 2.4, 'KO': 3.1,
        'PFE': 5.8, 'VZ': 6.4, 'T': 7.2, 'XOM': 5.5, 'CVX': 3.2,
        'JPM': 2.1, 'BAC': 2.8, 'WFC': 2.4, 'C': 3.8, 'GS': 2.4,
        'HD': 2.5, 'WMT': 1.7, 'TGT': 2.9, 'LOW': 1.8, 'COST': 0.7,
        'UNH': 1.3, 'LLY': 1.2, 'ABBV': 3.5, 'MRK': 2.7, 'BMY': 4.5,
        'MMM': 3.3, 'CAT': 2.2, 'BA': 0.0, 'GE': 0.4, 'IBM': 4.8
    }
    
    # Estimated beta values for volatility assessment
    beta_estimates = {
        'TSLA': 2.0, 'NVDA': 1.8, 'AMD': 1.9, 'NFLX': 1.2, 'AMZN': 1.3,
        'META': 1.3, 'GOOGL': 1.1, 'AAPL': 1.2, 'MSFT': 0.9, 'BRK-B': 0.8,
        'JNJ': 0.7, 'PG': 0.5, 'KO': 0.6, 'WMT': 0.5, 'UNH': 0.8,
        'JPM': 1.1, 'BAC': 1.3, 'XOM': 1.4, 'CVX': 1.2, 'AVGO': 1.1
    }
    
    # Get estimated values
    if symbol in pe_estimates:
        pe_ratio = pe_estimates[symbol]
    
    if symbol in dividend_stocks:
        dividend_yield = dividend_stocks[symbol]
    
    if symbol in beta_estimates:
        beta = beta_estimates[symbol]
    
    # Estimate market cap category
    large_cap = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH', 'JNJ']
    if symbol in large_cap:
        market_cap = 'Large'
    else:
        market_cap = 'Mid'
    
    return market_cap, beta, dividend_yield, pe_ratio

def calculate_support_resistance(highs, lows, closes):
    """Calculate support and resistance levels"""
    recent_data = list(zip(highs[-50:], lows[-50:], closes[-50:]))
    
    resistance_levels = []
    support_levels = []
    
    for i in range(2, len(recent_data) - 2):
        high = recent_data[i][0]
        low = recent_data[i][1]
        
        if (high > recent_data[i-1][0] and high > recent_data[i-2][0] and 
            high > recent_data[i+1][0] and high > recent_data[i+2][0]):
            resistance_levels.append(high)
        
        if (low < recent_data[i-1][1] and low < recent_data[i-2][1] and 
            low < recent_data[i+1][1] and low < recent_data[i+2][1]):
            support_levels.append(low)
    
    current_price = closes[-1]
    
    resistance = min([r for r in resistance_levels if r > current_price], default=current_price * 1.1)
    support = max([s for s in support_levels if s < current_price], default=current_price * 0.9)
    
    return support, resistance

def analyze_stock_advanced(symbol, market=None):
    """Advanced stock analysis with all requested metrics (market: the result of get_market_context, when the caller has it)"""
    try:
        print(f"Analyzing {symbol}...")
        data = get_stock_data(symbol)
        if not data or len(data) < 50:
            return None
        
        closes = [d['close'] for d in data]
        highs = [d['high'] for d in data]
        lows = [d['low'] for d in data]
        volumes = [d['volume'] for d in data]
        
        current_price = closes[-1]
        
        # Extended price changes for deal-hunting
        change_24h = ((closes[-1] - closes[-2]) / closes[-2]) * 100 if len(closes) > 1 else 0
        change_5d = ((closes[-1] - closes[-6]) / closes[-6]) * 100 if len(closes) > 5 else 0
        change_7d = ((closes[-1] - closes[-8]) / closes[-8]) * 100 if len(closes) > 7 else 0
        change_10d = ((closes[-1] - closes[-11]) / closes[-11]) * 100 if len(closes) > 10 else 0
        change_30d = ((closes[-1] - closes[-31]) / closes[-31]) * 100 if len(closes) > 30 else 0
        change_90d = ((closes[-1] - closes[-91]) / closes[-91]) * 100 if len(closes) > 90 else 0
        change_200d = ((closes[-1] - closes[-201]) / closes[-201]) * 100 if len(closes) > 200 else 0
        change_1yr = ((closes[-1] - closes[0]) / closes[0]) * 100 if len(closes) > 200 else 0  # Use first available price for 1yr
        
        # Technical indicators
        rsi = calculate_rsi(closes)
        macd, macd_signal, macd_histogram = calculate_macd(closes)
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(closes)
        stoch_k, stoch_d = calculate_stochastic(highs, lows, closes)
        atr = calculate_atr(highs, lows, closes)
        support, resistance = calculate_support_resistance(highs, lows, closes)
        
        # Volume analysis
        avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else volumes[-1]
        volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1
        
        # Get fundamentals (skip Yahoo P/E API due to 401 errors)
        market_cap, beta, dividend_yield, pe_ratio = get_fundamentals(symbol)
        
        # Calculate moving averages for trend confirmation
        ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else current_price
        ma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else current_price
        ma200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else current_price
        
        # Price relative to moving averages
        price_vs_ma20 = ((current_price - ma20) / ma20) * 100
        price_vs_ma50 = ((current_price - ma50) / ma50) * 100
        price_vs_ma200 = ((current_price - ma200) / ma200) * 100
        
        # 52-week high/low analysis (252 trading days)
        week52_data_points = min(252, len(highs))  # Use available data up to 252 days
        week52_highs = highs[-week52_data_points:]
        week52_lows = lows[-week52_data_points:]
        week52_high = max(week52_highs)
        week52_low = min(week52_lows)
        
        # Debug: Check if values are reasonable
        if week52_high <= 0 or week52_low <= 0 or current_price <= 0:
            distance_from_high = 0
            distance_from_low = 0
        else:
            distance_from_high = ((current_price - week52_high) / week52_high) * 100
            distance_from_low = ((current_price - week52_low) / week52_low) * 100
            
            # Sanity check: Distance from low should be positive and reasonable
            if distance_from_low > 500 or distance_from_low < 0:
                # Something's wrong, recalculate with proper formula
                if week52_low > 0:
                    distance_from_low = ((current_price - week52_low) / week52_low) * 100
                else:
                    distance_from_low = 0
        
        # Signal analysis
        macd_signal_str = "BULLISH" if macd > macd_signal and macd_histogram > 0 else "BEARISH" if macd < macd_signal and macd_histogram < 0 else "NEUTRAL"
        bb_signal = "OVERSOLD" if current_price < bb_lower else "OVERBOUGHT" if current_price > bb_upper else "NEUTRAL"
        momentum_signal = "STRONG_UP" if change_24h > 3 else "UP" if change_24h > 1 else "DOWN" if change_24h < -1 else "STRONG_DOWN" if change_24h < -3 else "NEUTRAL"
        
        # Enhanced scoring algorithm with weighted factors
        technical_score = 0
        confidence = 50
        score_breakdown = []
        
        # 1. Deal-Hunter Multi-timeframe momentum analysis (32% weight)
        # Short-term (18%): 1d, 5d, 10d - High sensitivity for oversold bounces
        short_momentum = 0
        if change_5d < -8 and change_10d < -12 and change_200d > -20:  # Deep oversold but not broken
            short_momentum += 4  # Contrarian opportunity
            score_breakdown.append(f"Contrarian Opportunity (5d:{change_5d:.1f}%, 10d:{change_10d:.1f}%, 200d:{change_200d:.1f}%): +{4 * 0.18:.2f}")
        elif change_5d > 3 and change_10d > 5:  # Strong short-term momentum
            short_momentum += 3
            score_breakdown.append(f"Strong Short Momentum (5d:{change_5d:.1f}%, 10d:{change_10d:.1f}%): +{3 * 0.18:.2f}")
        elif change_5d < -15 or change_10d < -20:  # Falling knife territory
            short_momentum -= 4
            score_breakdown.append(f"Falling Knife Risk (5d:{change_5d:.1f}%, 10d:{change_10d:.1f}%): {-4 * 0.18:.2f}")
        elif change_5d < -3 and change_10d < -5:
            short_momentum -= 1
            score_breakdown.append(f"Weak Short Momentum (5d:{change_5d:.1f}%, 10d:{change_10d:.1f}%): {-1 * 0.18:.2f}")
        else:
            score_breakdown.append(f"Neutral Short Momentum (5d:{change_5d:.1f}%, 10d:{change_10d:.1f}%): 0.00")
        
        # Medium-term (8%): 30d, 90d - Trend filter
        medium_momentum = 0
        if change_30d > 15 and change_90d > 20:  # Strong medium-term trend
            medium_momentum += 3
            score_breakdown.append(f"Strong Medium Trend (30d:{change_30d:.1f}%, 90d:{change_90d:.1f}%): +{3 * 0.08:.2f}")
        elif change_30d < -25 and change_90d < -30:  # Structural decline
            medium_momentum -= 3
            score_breakdown.append(f"Structural Decline (30d:{change_30d:.1f}%, 90d:{change_90d:.1f}%): {-3 * 0.08:.2f}")
        elif change_30d > 5 or change_90d > 10:
            medium_momentum += 1
            score_breakdown.append(f"Positive Medium Trend (30d:{change_30d:.1f}%, 90d:{change_90d:.1f}%): +{1 * 0.08:.2f}")
        elif change_30d < -15 or change_90d < -20:
            medium_momentum -= 2
            score_breakdown.append(f"Weak Medium Trend (30d:{change_30d:.1f}%, 90d:{change_90d:.1f}%): {-2 * 0.08:.2f}")
        else:
            score_breakdown.append(f"Neutral Medium Trend (30d:{change_30d:.1f}%, 90d:{change_90d:.1f}%): 0.00")
        
        # Long-term (6%): 200d, 1yr - Quality filter
        long_momentum = 0
        if change_200d > 25 and change_1yr > 30:  # Excellent long-term performance
            long_momentum += 3
            score_breakdown.append(f"Excellent Long Performance (200d:{change_200d:.1f}%, 1yr:{change_1yr:.1f}%): +{3 * 0.06:.2f}")
        elif change_200d < -40 or change_1yr < -50:  # Structural problems
            long_momentum -= 4
            score_breakdown.append(f"Structural Problems (200d:{change_200d:.1f}%, 1yr:{change_1yr:.1f}%): {-4 * 0.06:.2f}")
        elif change_200d > 10 or change_1yr > 15:
            long_momentum += 2
            score_breakdown.append(f"Good Long Performance (200d:{change_200d:.1f}%, 1yr:{change_1yr:.1f}%): +{2 * 0.06:.2f}")
        elif change_200d < -20 or change_1yr < -25:
            long_momentum -= 2
            score_breakdown.append(f"Poor Long Performance (200d:{change_200d:.1f}%, 1yr:{change_1yr:.1f}%): {-2 * 0.06:.2f}")
        else:
            score_breakdown.append(f"Neutral Long Performance (200d:{change_200d:.1f}%, 1yr:{change_1yr:.1f}%): 0.00")
        
        momentum_score = short_momentum * 0.18 + medium_momentum * 0.08 + long_momentum * 0.06
        technical_score += momentum_score
        
        # 2. Enhanced RSI with deal-hunting bonuses (20% weight)
        rsi_score = 0
        if rsi < 25:  # Deep oversold - contrarian bonus
            rsi_score += 4  # Extra bonus for deep oversold
            confidence += 20
            score_breakdown.append(f"RSI Deep Oversold Bonus ({rsi:.1f}): +{4 * 0.2:.2f}")
        elif 25 <= rsi <= 35:  # Prime oversold zone
            rsi_score += 3
            confidence += 15
            score_breakdown.append(f"RSI Prime Oversold ({rsi:.1f}): +{3 * 0.2:.2f}")
        elif 35 < rsi <= 45:  # Good buy zone
            rsi_score += 2
            confidence += 10
            score_breakdown.append(f"RSI Buy Zone ({rsi:.1f}): +{2 * 0.2:.2f}")
        elif 45 < rsi < 55:  # Neutral
            score_breakdown.append(f"RSI Neutral ({rsi:.1f}): 0.00")
        elif 55 <= rsi <= 70:  # Caution zone
            rsi_score -= 1
            score_breakdown.append(f"RSI Caution Zone ({rsi:.1f}): {-1 * 0.2:.2f}")
        else:  # Overbought
            rsi_score -= 3
            confidence += 10
            score_breakdown.append(f"RSI Overbought ({rsi:.1f}): {-3 * 0.2:.2f}")
        technical_score += rsi_score * 0.2
        
        # 3. MACD trend strength (20% weight)
        macd_score = 0
        if macd > macd_signal and macd_histogram > 0:
            if abs(macd_histogram) > abs(macd) * 0.1:  # Strong momentum
                macd_score += 3
                confidence += 15
                score_breakdown.append(f"MACD Strong Bullish: +{3 * 0.2:.2f}")
            else:
                macd_score += 1
                confidence += 5
                score_breakdown.append(f"MACD Weak Bullish: +{1 * 0.2:.2f}")
        elif macd < macd_signal and macd_histogram < 0:
            if abs(macd_histogram) > abs(macd) * 0.1:  # Strong bearish
                macd_score -= 3
                confidence += 15
                score_breakdown.append(f"MACD Strong Bearish: {-3 * 0.2:.2f}")
            else:
                macd_score -= 1
                confidence += 5
                score_breakdown.append(f"MACD Weak Bearish: {-1 * 0.2:.2f}")
        else:
            score_breakdown.append(f"MACD Neutral: 0.00")
        technical_score += macd_score * 0.2
        
        # 4. Enhanced Volume-Price with capitulation detection (10% weight)
        volume_score = 0
        if volume_ratio > 3.0 and change_24h < -5 and rsi < 30:  # Capitulation signal
            volume_score += 2  # Potential bottom
            confidence += 15
            score_breakdown.append(f"Capitulation Signal ({volume_ratio:.1f}x, {change_24h:.1f}%, RSI:{rsi:.1f}): +{2 * 0.1:.2f}")
        elif volume_ratio > 2.0 and change_24h > 2:
            volume_score += 3  # Strong buying interest
            confidence += 10
            score_breakdown.append(f"Strong Volume Breakout ({volume_ratio:.1f}x, +{change_24h:.1f}%): +{3 * 0.1:.2f}")
        elif volume_ratio > 1.5 and change_24h > 0:
            volume_score += 1
            confidence += 5
            score_breakdown.append(f"Good Volume Support ({volume_ratio:.1f}x): +{1 * 0.1:.2f}")
        elif volume_ratio > 2.0 and change_24h < -2:
            volume_score -= 2  # Heavy selling
            confidence += 10
            score_breakdown.append(f"Heavy Selling Volume ({volume_ratio:.1f}x, {change_24h:.1f}%): {-2 * 0.1:.2f}")
        else:
            score_breakdown.append(f"Normal Volume ({volume_ratio:.1f}x): 0.00")
        technical_score += volume_score * 0.10
        
        # 5. Debt & Financial Strength (6% weight)
        debt_score = 0
        # Debt assessment based on known company profiles
        low_debt_stocks = {'AAPL', 'MSFT', 'GOOGL', 'BRK-B', 'NVDA', 'META'}
        high_debt_stocks = {'T', 'VZ', 'F', 'GM', 'BA', 'GE', 'XOM', 'CVX'}
        distressed_stocks = {'BBBY', 'BED', 'GME', 'AMC', 'SEARS', 'JCP', 'RITE'}
        
        if symbol in distressed_stocks:
            debt_score -= 5
            score_breakdown.append(f"High Bankruptcy Risk: {-5 * 0.06:.2f}")
        elif symbol in low_debt_stocks:
            debt_score += 3
            score_breakdown.append(f"Strong Balance Sheet (Low Debt): +{3 * 0.06:.2f}")
        elif symbol in high_debt_stocks:
            debt_score -= 2
            score_breakdown.append(f"High Debt Concern: {-2 * 0.06:.2f}")
        elif isinstance(pe_ratio, (int, float)):
            if pe_ratio < 0:  # Negative earnings - major red flag
                debt_score -= 4
                score_breakdown.append(f"Negative Earnings (PE<0): {-4 * 0.06:.2f}")
            elif pe_ratio > 100:  # Extremely high P/E - overvalued or distressed
                debt_score -= 3
                score_breakdown.append(f"Extreme Valuation (PE>{pe_ratio:.1f}): {-3 * 0.06:.2f}")
            elif 15 <= pe_ratio <= 25:  # Healthy P/E range
                debt_score += 2
                score_breakdown.append(f"Healthy Valuation (PE:{pe_ratio:.1f}): +{2 * 0.06:.2f}")
            else:
                score_breakdown.append(f"Normal Financial Profile: 0.00")
        else:
            score_breakdown.append(f"Financial Profile Unknown: 0.00")
        technical_score += debt_score * 0.06
        
        # 6. Bollinger Bands position (5% weight)
        bb_score = 0
        if bb_lower and bb_upper:
            bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)
            if bb_position < 0.2:  # Near lower band - potential bounce
                bb_score += 2
                confidence += 10
                score_breakdown.append(f"BB Oversold Position: +{2 * 0.05:.2f}")
            elif bb_position > 0.8:  # Near upper band - potential reversal
                bb_score -= 2
                confidence += 5
                score_breakdown.append(f"BB Overbought Position: {-2 * 0.05:.2f}")
            else:
                score_breakdown.append(f"BB Neutral Position: 0.00")
        technical_score += bb_score * 0.05
        
        # 7. Market Sentiment Analysis (3% weight)
        sentiment_score = 0
        # Sentiment based on recent performance vs market expectations
        if change_24h > 5:  # Strong positive sentiment
            sentiment_score += 3
            score_breakdown.append(f"Strong Positive Sentiment (+{change_24h:.1f}% today): +{3 * 0.03:.2f}")
        elif change_24h > 2:
            sentiment_score += 1
            score_breakdown.append(f"Positive Sentiment (+{change_24h:.1f}% today): +{1 * 0.03:.2f}")
        elif change_24h < -5:  # Strong negative sentiment
            sentiment_score -= 3
            score_breakdown.append(f"Strong Negative Sentiment ({change_24h:.1f}% today): {-3 * 0.03:.2f}")
        elif change_24h < -2:
            sentiment_score -= 1
            score_breakdown.append(f"Negative Sentiment ({change_24h:.1f}% today): {-1 * 0.03:.2f}")
        else:
            score_breakdown.append(f"Neutral Sentiment ({change_24h:.1f}% today): 0.00")
        technical_score += sentiment_score * 0.03
        
        # 8. Market Context & Regime (3% weight)
        market_regime, spy_change = market if market else get_market_context()
        market_score = 0
        if market_regime == 'BULL':
            market_score += 2
            score_breakdown.append(f"Bull Market Context (SPY +{spy_change:.1f}%): +{2 * 0.03:.2f}")
        elif market_regime == 'BEAR':
            market_score -= 3
            score_breakdown.append(f"Bear Market Risk (SPY {spy_change:.1f}%): {-3 * 0.03:.2f}")
        else:
            score_breakdown.append(f"Neutral Market (SPY {spy_change:.1f}%): 0.00")
        technical_score += market_score * 0.03
        
        # 9. Enhanced Sector & Earnings with deal opportunities (2% weight)
        sector = get_sector_info(symbol)
        earnings_risk = check_earnings_risk(symbol)
        risk_score = 0
        
        # Sector momentum (simplified)
        if sector == 'TECH' and market_regime == 'BULL':
            risk_score += 1
            score_breakdown.append(f"Tech Sector Strength: +{1 * 0.02:.2f}")
        elif sector == 'ENERGY' and spy_change < -5:
            risk_score -= 1
            score_breakdown.append(f"Energy Sector Weakness: {-1 * 0.02:.2f}")
        
        # Earnings dip opportunity - contrarian bonus
        if earnings_risk == 'HIGH' and change_24h < -3 and change_5d < -8:
            # Quality stock beaten down by earnings - opportunity
            quality_stocks = {'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'JPM', 'UNH', 'JNJ'}
            if symbol in quality_stocks:
                risk_score += 1
                score_breakdown.append(f"Earnings Dip Opportunity (Quality Stock): +{1 * 0.02:.2f}")
            else:
                risk_score -= 1
                score_breakdown.append(f"Earnings Season Risk: {-1 * 0.02:.2f}")
        elif earnings_risk == 'HIGH':
            risk_score -= 1
            score_breakdown.append(f"Earnings Season Risk: {-1 * 0.02:.2f}")
        
        if risk_score == 0:
            score_breakdown.append(f"Neutral Sector/Earnings Risk: 0.00")
        
        technical_score += risk_score * 0.02
        
        # 10. Moving Average Trend Analysis (1% weight)
        ma_score = 0
        if current_price > ma20 > ma50 > ma200:  # Perfect uptrend
            ma_score += 4
            score_breakdown.append(f"Perfect MA Uptrend: +{4 * 0.01:.2f}")
        elif current_price > ma20 > ma50:  # Good uptrend
            ma_score += 2
            score_breakdown.append(f"Good MA Uptrend: +{2 * 0.01:.2f}")
        elif current_price < ma20 < ma50 < ma200:  # Perfect downtrend
            ma_score -= 3
            score_breakdown.append(f"Perfect MA Downtrend: {-3 * 0.01:.2f}")
        elif current_price < ma20 < ma50:  # Weak downtrend
            ma_score -= 1
            score_breakdown.append(f"Weak MA Downtrend: {-1 * 0.01:.2f}")
        else:
            score_breakdown.append(f"Mixed MA Signals: 0.00")
        technical_score += ma_score * 0.01
        
        # Market regime adjustment
        if market_regime == 'BEAR':
            technical_score *= 0.7  # Reduce all scores in bear market
            score_breakdown.append(f"Bear Market Adjustment: Score × 0.7")
        
        # Store pre-scaling score
        pre_scale_score = technical_score
        
        # Scale final score for better range distribution (expand -0.7→+1.3 to -1.8→+3.3)
        technical_score *= 2.5
        score_breakdown.append(f"FINAL SCALED SCORE: {pre_scale_score:.2f} × 2.5 = {technical_score:.1f}")
        
        # Add weighted calculation summary to score breakdown
        score_breakdown.append(f"WEIGHTED CALCULATION:")
        score_breakdown.append(f"Short Momentum: {short_momentum:.1f} × 18% = {short_momentum * 0.18:.2f}")
        score_breakdown.append(f"Medium Momentum: {medium_momentum:.1f} × 8% = {medium_momentum * 0.08:.2f}")
        score_breakdown.append(f"Long Momentum: {long_momentum:.1f} × 6% = {long_momentum * 0.06:.2f}")
        score_breakdown.append(f"RSI: {rsi_score:.1f} × 20% = {rsi_score * 0.2:.2f}")
        score_breakdown.append(f"MACD: {macd_score:.1f} × 20% = {macd_score * 0.2:.2f}")
        score_breakdown.append(f"Volume: {volume_score:.1f} × 10% = {volume_score * 0.1:.2f}")
        score_breakdown.append(f"Financial: {debt_score:.1f} × 6% = {debt_score * 0.06:.2f}")
        score_breakdown.append(f"Bollinger: {bb_score:.1f} × 5% = {bb_score * 0.05:.2f}")
        score_breakdown.append(f"Sentiment: {sentiment_score:.1f} × 3% = {sentiment_score * 0.03:.2f}")
        score_breakdown.append(f"Market: {market_score:.1f} × 3% = {market_score * 0.03:.2f}")
        score_breakdown.append(f"Risk: {risk_score:.1f} × 2% = {risk_score * 0.02:.2f}")
        score_breakdown.append(f"MA Trend: {ma_score:.1f} × 1% = {ma_score * 0.01:.2f}")
        score_breakdown.append(f"PRE-SCALE TOTAL: {technical_score:.2f}")
        
        if SCORE_VERSION == 2:          # the trend score replaces the 12-factor one; every other figure stays as it is
            technical_score, score_breakdown = trend_score(change_1yr, change_30d, distance_from_low, current_price, ma50, ma200, rsi)

        # Use rounded score for thresholds to match user display
        rounded_score = round(technical_score, 1)
        
        # Professional 7-point rating system
        if rounded_score >= 2.5:
            recommendation = "STRONG_BUY"
            timeframe = "1-3 months"
            strategy_type = "SHORT_TERM"
            hold_days = "20-90 days"
        elif rounded_score >= 1.5:
            recommendation = "BUY"
            timeframe = "2-4 months"
            strategy_type = "MEDIUM_TERM"
            hold_days = "60-120 days"
        elif rounded_score >= 0.5:
            recommendation = "MODERATE_BUY"
            timeframe = "3-6 months"
            strategy_type = "MEDIUM_TERM"
            hold_days = "90-180 days"
        elif rounded_score > SELL_BANDS[0]:
            recommendation = "HOLD"
            timeframe = "6-12 months"
            strategy_type = "LONG_TERM"
            hold_days = "180-365 days"
        elif rounded_score >= SELL_BANDS[1]:
            recommendation = "MODERATE_SELL"
            timeframe = "1-3 months"
            strategy_type = "SHORT_TERM"
            hold_days = "30-90 days"
        elif rounded_score >= SELL_BANDS[2]:
            recommendation = "SELL"
            timeframe = "0-1 months"
            strategy_type = "SHORT_TERM"
            hold_days = "5-30 days"
        else:
            recommendation = "STRONG_SELL"
            timeframe = "0-2 weeks"
            strategy_type = "IMMEDIATE"
            hold_days = "1-14 days"
        
        # Calculate profit probability with better scaling
        base_probability = 50
        score_impact = technical_score * 12  # Increased impact
        confidence_impact = (confidence - 50) * 0.4
        momentum_boost = 0
        if change_5d > 0 and change_10d > 0:
            momentum_boost += 5
        if volume_ratio > 1.5 and change_24h > 0:
            momentum_boost += 5
        
        profit_probability = max(15, min(85, base_probability + score_impact + confidence_impact + momentum_boost))
        
        # Calculate stop loss and take profit
        if recommendation in ["STRONG_BUY", "BUY", "MODERATE_BUY"]:
            stop_loss = current_price * (0.93 if recommendation == "STRONG_BUY" else 0.95 if recommendation == "BUY" else 0.97)
            take_profit = current_price * (1.20 if recommendation == "STRONG_BUY" else 1.15 if recommendation == "BUY" else 1.08)
        else:
            stop_loss = current_price * 0.98
            take_profit = current_price * 1.03
        
        return {
            'symbol': symbol,
            'price': round(current_price, 2),
            'current_price': round(current_price, 2),  # 3.1 compatibility
            'score': round(technical_score, 1),
            'total_score': round(technical_score, 1),  # 3.1 compatibility
            'recommendation': recommendation,
            'timeframe': timeframe,
            'strategy_type': strategy_type,
            'hold_days': hold_days,
            'confidence': round(min(95, confidence), 1),
            'rsi': round(rsi, 1),
            'change_24h': round(change_24h, 2),
            'change_5d': round(change_5d, 2),
            'change_7d': round(change_7d, 2),
            'change_10d': round(change_10d, 2),
            'change_30d': round(change_30d, 2),
            'change_90d': round(change_90d, 2),
            'change_200d': round(change_200d, 2),
            'change_1yr': round(change_1yr, 2),
            'ytd_change': round(change_1yr, 2),  # Alias for HTML display compatibility
            'pe_ratio': pe_ratio,
            'market_cap': market_cap,
            'beta': beta,
            'dividend_yield': dividend_yield,
            'price_vs_ma20': round(price_vs_ma20, 2),
            'price_vs_ma50': round(price_vs_ma50, 2),
            'price_vs_ma200': round(price_vs_ma200, 2),
            'distance_from_52w_high': round(distance_from_high, 2),
            'distance_from_52w_low': round(distance_from_low, 2),
            '52w_high': round(week52_high, 2),
            '52w_low': round(week52_low, 2),
            'volume_ratio': round(volume_ratio, 2),
            'profit_probability': round(profit_probability, 1),
            'macd_signal': macd_signal_str,
            'bb_signal': bb_signal,
            'momentum_signal': momentum_signal,
            'stop_loss': round(stop_loss, 2),
            'take_profit': round(take_profit, 2),
            'support': round(support, 2),
            'resistance': round(resistance, 2),
            'atr': round(atr, 2),
            'stoch_k': round(stoch_k, 1),
            'market_regime': market_regime,
            'spy_change_20d': round(spy_change, 1),
            'sector': sector,
            'earnings_risk': earnings_risk,
            'currency': CURRENCY.get(symbol.upper(), ''),
            'score_breakdown': score_breakdown
        }
        
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None

def own_batch(group, worker_id, per_worker=10):
    """This worker's ten stocks of its group's list (lists.txt, in the package beside this file)"""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lists.txt')) as f:
            for line in f:
                name, _, symbols = line.partition(':')
                if name.strip() == group:
                    start = (int(worker_id) - 1) * per_worker
                    return symbols.split()[start:start + per_worker] if start >= 0 else []
    except (OSError, ValueError, TypeError) as e:
        print(f"No list for {group} worker {worker_id}: {e}")
    return []

def handle_batch_processing(event, context):
    """Handle batch processing with advanced analysis"""
    try:
        stock_batch = event.get('stock_batch')
        worker_id = event.get('worker_id', 1)
        
        if stock_batch is None:
            # Called with a worker number and no batch (the Russell screeners on the page): this worker's own ten
            # stocks of its group's list. A batch that was sent empty stays empty: nothing unrelated is ever returned.
            name = getattr(context, 'function_name', None) or os.environ.get('AWS_LAMBDA_FUNCTION_NAME', '')
            stock_batch = own_batch(name.rpartition('-')[0], worker_id)
        if not isinstance(stock_batch, list):
            stock_batch = []
        
        print(f"Worker {worker_id}: Processing {len(stock_batch)} stocks")
        
        # The market's state is the same for every stock of the batch: fetch SPY once, not once per stock
        market = get_market_context() if stock_batch else None
        
        results = []
        for symbol in stock_batch:
            try:
                result = analyze_stock_advanced(symbol, market)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"Error analyzing {symbol}: {e}")
                continue
        
        # Sort by score (best to worst)
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # Categorize recommendations
        buy_stocks = [r for r in results if r['recommendation'] in ['STRONG_BUY', 'BUY', 'MODERATE_BUY']]
        hold_stocks = [r for r in results if r['recommendation'] == 'HOLD']
        sell_stocks = [r for r in results if r['recommendation'] in ['MODERATE_SELL', 'SELL', 'STRONG_SELL']]
        
        return {
            'success': True,
            'results': results,
            'top_10': results[:10],
            'buy_recommendations': buy_stocks,
            'hold_recommendations': hold_stocks,
            'sell_recommendations': sell_stocks,
            'worker_id': worker_id,
            'stocks_processed': len(stock_batch),
            'stocks_analyzed': len(results),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Worker {worker_id} error: {e}")
        return {
            'success': False,
            'error': str(e),
            'worker_id': event.get('worker_id', 0),
            'stocks_analyzed': 0
        }

# A run by hand: python3 workers/stock_worker.py AAPL BHP.AX 7203.T IMB.L   (it asks Yahoo for each symbol and for SPY)
if __name__ == "__main__":
    import sys
    body = json.loads(lambda_handler({'stock_batch': sys.argv[1:] or ['AAPL', 'MSFT', 'BHP.AX', '7203.T', 'IMB.L'], 'worker_id': 1}, None)['body'])
    for stock in body.get('results', []):
        print(f"{stock['symbol']:<10} {stock['price']:>10.2f} {stock['currency']:<4} score {stock['score']:+.1f}  {stock['recommendation']:<14} 24h {stock['change_24h']:+.2f}%  RSI {stock['rsi']}")
    print(f"{body.get('stocks_analyzed', 0)} of {body.get('stocks_processed', 0)} analysed")
