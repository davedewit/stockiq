"""The trading-signals functions: ONE file for both buttons under "Trading Signals" on the analysis page.

    stockiq-option-2-trading-signals    "Enter Symbols for Live Signals": the reading for each symbol sent (up to 10)
    stockiq-option-2-2-auto-signals     "Auto-detect Top 5 Signals": scans the S&P 100 (sp100.txt, beside this file) and
                                        returns the five shares with the strongest readings, in either direction

Which of the two a call is, is decided by the function's own name ("auto" in it), so both run this same file.

A reading is short-term and technical only: RSI (Wilder's, as everywhere on the site), MACD against its signal line,
and the price against its Bollinger bands. Each adds or takes points; +2 or more is a positive reading, -2 or less a
negative one. It is NOT the 0-100 score of the single-stock report and uses no company figures. The functions return
figures and plain descriptions; the page writes the report (and applies the wording rule: describe, don't advise).

Change it here, in git, never in the AWS console:
    python3 signals/test_signals.py     # on saved prices, nothing live
    python3 signals/build.py            # the package (signals.zip) and its fingerprint; --list rewrites sp100.txt
and deploy with a packaged script (site-overview.md section 8b, "Trading signals").

Until 11 Oct 2026 these were two separate files with a scoring of their own: RSI as a plain average (a third way of
working it out on this site), every price in dollars, a time the browser read as local when it was UTC, levels at an
arbitrary 5% either side, and an "auto-detect" that looked at the first 15 names of a list written into the code and
called its five picks "top performers".
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

SCAN_NAME = 'S&P 100'
SCAN_FILE = 'sp100.txt'
SCAN_THREADS = 8
TOP = 5
DEFAULT_SYMBOLS = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'TSLA']
LEVELS = 'the highest and lowest prices of the last 20 sessions'
SCALE = '+2 or more is a positive reading, -2 or less a negative one, anything between is mixed'
DISCLAIMER = ('Calculated automatically from prices. General information only: not financial advice and not a '
              'recommendation to buy or sell.')


def lambda_handler(event, context):
    try:
        body = event.get('body') if isinstance(event, dict) else None
        if isinstance(body, str):
            body = json.loads(body or '{}')
        if not isinstance(body, dict):
            body = event if isinstance(event, dict) else {}
        name = getattr(context, 'function_name', None) or os.environ.get('AWS_LAMBDA_FUNCTION_NAME', '')
        if 'auto' in name or body.get('mode') == 'auto':
            return success_response(auto_signals())
        return success_response(custom_signals(body.get('symbols')))
    except Exception as e:
        return error_response(500, str(e))


def custom_signals(symbols):
    """The reading for each symbol asked for (up to 10; the five defaults when none is sent)"""
    wanted = []
    for symbol in (symbols if isinstance(symbols, list) and symbols else DEFAULT_SYMBOLS):
        symbol = str(symbol or '').upper().strip()
        if symbol and symbol not in wanted:
            wanted.append(symbol)
    wanted = wanted[:10]
    with ThreadPoolExecutor(min(SCAN_THREADS, len(wanted) or 1)) as pool:
        found = list(pool.map(read_signal, wanted))
    signals = [s for s in found if s]
    return {
        'option': '2',
        'description': 'Trading signals: short-term technical readings (RSI, MACD, Bollinger bands)',
        'symbols_analyzed': len(signals),
        'signals': signals,
        'not_found': [symbol for symbol, s in zip(wanted, found) if not s],
        'scale': SCALE,
        'levels': LEVELS,
        'timestamp': now_text(),
        'disclaimer': DISCLAIMER,
    }


def auto_signals():
    """Scan the list and return the five strongest readings, in either direction"""
    symbols = scan_list()
    with ThreadPoolExecutor(SCAN_THREADS) as pool:
        found = [s for s in pool.map(read_signal, symbols) if s]
    place = {symbol: i for i, symbol in enumerate(symbols)}
    # strongest first; between equal readings the RSI further from its middle, then the order of the list
    ranked = sorted(found, key=lambda s: (-abs(s['signal_strength']), -abs((s['rsi'] or 50) - 50), place.get(s['symbol'], 0)))
    top = ranked[:TOP]
    count = lambda action: sum(1 for s in found if s['action'] == action)
    return {
        'option': '2.2',
        'description': f'Auto-detect: the five strongest short-term readings among the {SCAN_NAME} shares',
        'symbols_analyzed': len(top),
        # the page's name for the list it prints; they are the strongest readings, not the best performers
        'top_performers': [s['symbol'] for s in top],
        'signals': top,
        'universe': SCAN_NAME,
        'universe_size': len(symbols),
        'scanned': len(found),
        'readings': {'positive': count('BUY'), 'negative': count('SELL'), 'mixed': count('HOLD')},
        'methodology': (f"Scanned {len(found)} of the {len(symbols)} {SCAN_NAME} shares for three short-term readings (RSI, MACD, "
                        f"Bollinger bands). Shown: the {len(top)} strongest readings, in either direction"),
        'scale': SCALE,
        'levels': LEVELS,
        'timestamp': now_text(),
        'disclaimer': DISCLAIMER,
    }


def scan_list():
    """The shares the auto-detect scans: the screener's own S&P 100 list (build.py --list writes it from the coordinator)"""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), SCAN_FILE)) as f:
            symbols = f.read().split()
        if len(symbols) >= 20:
            return symbols
    except OSError as e:
        print(f"No scan list: {e}")
    return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK-B', 'UNH', 'JNJ', 'V', 'PG', 'JPM', 'HD', 'MA',
            'NFLX', 'DIS', 'ADBE', 'CRM', 'AMD', 'INTC', 'ORCL', 'CSCO', 'IBM', 'QCOM', 'TXN', 'AVGO', 'MU', 'KO', 'WMT']


def now_text():
    """The time in UTC, marked as such: the page turns it into the visitor's own time (unmarked, a browser read it as local)"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def read_signal(symbol):
    """The short-term reading of one symbol, or None when there are no prices for it"""
    try:
        bars, facts = fetch_bars(symbol)
        if not bars or len(bars) < 50:
            return None

        closes = [bar['close'] for bar in bars]
        highs = [bar['high'] for bar in bars]
        lows = [bar['low'] for bar in bars]
        current = closes[-1]

        rsi = calculate_rsi(closes)
        macd_line, signal_line, _ = calculate_macd(closes)
        bb_upper, _, bb_lower = calculate_bollinger_bands(closes)
        resistance = max(highs[-20:])
        support = min(lows[-20:])

        strength = 0
        tags = []        # the short names the older page code knows
        reasons = []     # one plain line per reading, with its points

        def add(points, tag, words):
            nonlocal strength
            strength += points
            if tag:
                tags.append(tag)
            reasons.append(f"{words}: {points:+d}" if points else words)

        if rsi < 30:
            add(2, 'RSI Oversold', f"RSI {rsi:.0f}, in the oversold range (under 30)")
        elif rsi < 40:
            add(1, 'RSI Accumulation', f"RSI {rsi:.0f}, low (under 40)")
        elif rsi > 70:
            add(-2, 'RSI Overbought', f"RSI {rsi:.0f}, in the overbought range (over 70)")
        elif rsi > 60:
            add(-1, 'RSI Elevated', f"RSI {rsi:.0f}, high (over 60)")
        else:
            add(0, '', f"RSI {rsi:.0f}, in the middle of its range")

        if macd_line is not None and signal_line is not None and macd_line != signal_line:
            if macd_line > signal_line:
                add(1, 'MACD Bullish', 'MACD above its signal line')
            else:
                add(-1, 'MACD Bearish', 'MACD below its signal line')

        if bb_lower is not None and current <= bb_lower:
            add(2, 'BB Oversold', 'Price at or below its lower Bollinger band')
        elif bb_upper is not None and current >= bb_upper:
            add(-2, 'BB Overbought', 'Price at or above its upper Bollinger band')
        else:
            add(0, '', 'Price inside its Bollinger bands')

        if strength >= 2:
            action, confidence = 'BUY', ('HIGH' if strength >= 3 else 'MEDIUM')
        elif strength <= -2:
            action, confidence = 'SELL', ('HIGH' if strength <= -3 else 'MEDIUM')
        else:
            action, confidence = 'HOLD', 'LOW'

        # The two levels are facts, not targets: the top and the bottom of the last 20 sessions. (They were 2% inside
        # those, or an arbitrary 5% either side of the price for a mixed reading.) Field names as the page knows them:
        # for a negative reading the lower level is the one it calls take_profit.
        upper, lower = resistance, support
        take_profit, stop_loss = (lower, upper) if action == 'SELL' else (upper, lower)
        pct = lambda level: (level - current) / current * 100 if current else 0
        ma20 = sum(closes[-20:]) / 20
        ma50 = sum(closes[-50:]) / 50

        return {
            'symbol': symbol,
            'name': facts.get('name') or '',
            'currency': facts.get('currency') or '',
            'current_price': current,
            'change_pct': (current / closes[-2] - 1) * 100 if closes[-2] else 0,
            'action': action,
            'confidence': confidence,
            'entry_price': current,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'stop_loss_pct': pct(stop_loss),
            'take_profit_pct': pct(take_profit),
            'rsi': rsi,
            'support': support,
            'resistance': resistance,
            'signals': tags,
            'reasons': reasons,
            'signal_strength': strength,
            'trend': trend_words(current, ma20, ma50),
        }
    except Exception as e:
        print(f"No reading for {symbol}: {str(e)[:80]}")
        return None


def trend_words(current, ma20, ma50):
    """Where the price stands against its averages, in the single-stock report's own words (its trend_points)"""
    side = lambda gap: 'level with' if abs(gap) < 0.05 else f"{abs(gap):.1f}% {'above' if gap > 0 else 'below'}"
    if not ma20 or not ma50:
        return 'not enough history for the averages'
    return f"price {side((current / ma20 - 1) * 100)} its 20-day average; 20-day average {side((ma20 / ma50 - 1) * 100)} the 50-day"


def bars_from_chart(result):
    """Daily bars from one Yahoo chart answer, oldest first, one bar per trading day: the same rules as the screener
    workers and the single-stock report. Returns (bars, facts about the symbol)."""
    timestamps = result.get('timestamp') or []
    quotes = (result.get('indicators') or {}).get('quote') or []
    meta = result.get('meta') or {}
    offset = meta.get('gmtoffset') or 0
    day = lambda timestamp: (int(timestamp) + offset) // 86400
    prices = quotes[0] if quotes else {}
    bars = []
    for i, ts in enumerate(timestamps):
        try:
            close, high, low = prices['close'][i], prices['high'][i], prices['low'][i]
            if close is None or high is None or low is None:
                continue
            bar = {'timestamp': ts, 'high': high, 'low': low, 'close': close}
        except (KeyError, IndexError, TypeError):
            continue
        # a session Yahoo sends twice (the ASX after its close) is kept once, the later one
        if bars and day(bars[-1]['timestamp']) == day(ts):
            bars[-1] = bar
        else:
            bars.append(bar)
    # a latest session that arrives empty (London) is taken from the quote that comes with the chart
    price, quoted = meta.get('regularMarketPrice'), meta.get('regularMarketTime')
    if (bars and isinstance(price, (int, float)) and price > 0 and isinstance(quoted, (int, float)) and day(quoted) > day(bars[-1]['timestamp'])):
        high, low = meta.get('regularMarketDayHigh'), meta.get('regularMarketDayLow')
        bars.append({'timestamp': int(quoted), 'high': max(high, price) if isinstance(high, (int, float)) else price,
                     'low': min(low, price) if isinstance(low, (int, float)) and low > 0 else price, 'close': price})
    return bars, {'currency': meta.get('currency') or '', 'name': meta.get('longName') or meta.get('shortName') or ''}


def fetch_bars(symbol, tries=2):
    """A year of daily prices from Yahoo Finance. One more try after a refusal: a scan asks for many at once."""
    end_time = int(datetime.now().timestamp())
    start_time = int((datetime.now() - timedelta(days=365)).timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
    full_url = f"{url}?{urllib.parse.urlencode({'period1': start_time, 'period2': end_time, 'interval': '1d'})}"
    for attempt in range(tries):
        try:
            req = urllib.request.Request(full_url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read())
            if not data or 'chart' not in data or not data['chart']['result']:
                return None, {}
            return bars_from_chart(data['chart']['result'][0])
        except urllib.error.HTTPError as e:
            if e.code == 404 or attempt == tries - 1:
                return None, {}
            time.sleep(0.6)
        except Exception:
            if attempt == tries - 1:
                return None, {}
            time.sleep(0.6)
    return None, {}


def calculate_rsi(closes, period=14):
    """RSI using Wilder's smoothing: the same as the screener workers, the single-stock report and its chart"""
    if len(closes) < period + 1:
        return 50

    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_macd(closes, fast=12, slow=26, signal=9):
    """MACD line, its signal line and the difference (None when there is too little history)"""
    if len(closes) < slow:
        return None, None, None

    def ema(data, period):
        multiplier = 2 / (period + 1)
        ema_values = [data[0]]
        for i in range(1, len(data)):
            ema_values.append((data[i] * multiplier) + (ema_values[-1] * (1 - multiplier)))
        return ema_values

    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)
    macd_line = [fast_ema[i] - slow_ema[i] for i in range(len(closes))]
    signal_line = ema(macd_line, signal)
    return macd_line[-1], signal_line[-1], macd_line[-1] - signal_line[-1]


def calculate_bollinger_bands(closes, period=20, std_dev=2):
    """Upper band, middle and lower band of the last 20 closes (None when there is too little history)"""
    if len(closes) < period:
        return None, None, None

    recent_closes = closes[-period:]
    sma = sum(recent_closes) / period
    std = (sum((x - sma) ** 2 for x in recent_closes) / period) ** 0.5
    return sma + (std_dev * std), sma, sma - (std_dev * std)


def success_response(data):
    return {'statusCode': 200, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps(data)}


def error_response(status_code, message):
    return {'statusCode': status_code, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps({'error': message})}


# A run by hand (it asks Yahoo): python3 signals/lambda_function.py NVDA BHP.AX IMB.L     or     ... --auto
if __name__ == '__main__':
    import sys
    data = auto_signals() if '--auto' in sys.argv else custom_signals([a for a in sys.argv[1:] if not a.startswith('--')])
    if data.get('methodology'):
        print(data['methodology'], data['readings'])
    for s in data['signals']:
        print(f"{s['symbol']:<8} {s['current_price']:>10.2f} {s['currency']:<4} {s['action']:<4} {s['confidence']:<6} {s['signal_strength']:+d}  " + '; '.join(s['reasons']))
