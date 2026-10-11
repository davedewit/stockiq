"""Builds the new chart function from the live copy: the entry point and the storage stay, the drawing is new.
    python3 patch_chart.py <live lambda_function_simple.py> <out lambda_function_simple.py>"""
import sys
src = open(sys.argv[1]).read()

def swap(text, old, new):
    assert text.count(old) == 1, (text.count(old), old[:80])
    return text.replace(old, new)

src = swap(src, '        chart_svg = generate_svg_chart(symbol)\n', '        chart_svg = generate_svg_chart(symbol, body)\n')
a = src.index('def generate_svg_chart(symbol):'); b = src.index('def generate_error_svg(error_message):')
assert src.count('def generate_svg_chart(symbol):') == 1

NEW = r'''MONEY_SIGNS = {'USD': '$', 'AUD': 'A$', 'CAD': 'C$', 'NZD': 'NZ$', 'HKD': 'HK$', 'SGD': 'S$', 'GBP': '£', 'EUR': '€',
               'JPY': '¥', 'CNY': 'CN¥', 'INR': '₹', 'KRW': '₩'}
MINOR_UNITS = {'GBp': 'p', 'GBX': 'p', 'ZAc': 'c', 'ZAC': 'c', 'ILA': ' agorot'}

def bars_from_chart(result):
    """Daily bars from one Yahoo chart answer, oldest first, one bar per trading day: the same rules as the report and
    the screener workers (a session Yahoo sends twice is kept once; a latest session sent empty is taken from the quote)"""
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
            bar = {'t': ts, 'h': high, 'l': low, 'c': close, 'v': prices['volume'][i] or 0}
        except (KeyError, IndexError, TypeError):
            continue
        if bars and day(bars[-1]['t']) == day(ts):
            bars[-1] = bar
        else:
            bars.append(bar)
    price, quoted = meta.get('regularMarketPrice'), meta.get('regularMarketTime')
    if (bars and isinstance(price, (int, float)) and price > 0 and isinstance(quoted, (int, float)) and day(quoted) > day(bars[-1]['t'])):
        high, low, volume = meta.get('regularMarketDayHigh'), meta.get('regularMarketDayLow'), meta.get('regularMarketVolume')
        bars.append({'t': int(quoted), 'h': max(high, price) if isinstance(high, (int, float)) else price,
                     'l': min(low, price) if isinstance(low, (int, float)) and low > 0 else price,
                     'c': price, 'v': volume if isinstance(volume, (int, float)) else 0})
    return bars, (meta.get('currency') or '')

def chart_inputs(symbol, body):
    """The prices to draw. The report sends the very bars it scored (so the chart and the text can never differ);
    a page that asks for a chart by itself gets them fetched here."""
    series = (body or {}).get('series')
    if isinstance(series, dict):
        closes = series.get('c') or []
        if len(closes) >= 50 and all(len(series.get(k) or []) == len(closes) for k in ('t', 'h', 'l', 'v')):
            number = lambda values: [float(x) for x in values]
            return {'t': [int(x) for x in series['t']], 'h': number(series['h']), 'l': number(series['l']), 'c': number(closes),
                    'v': number(series['v']), 'currency': body.get('currency') or '', 'support': body.get('support'),
                    'resistance': body.get('resistance')}
    end_time = int(datetime.now().timestamp())
    start_time = int((datetime.now() - timedelta(days=365)).timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
    req = urllib.request.Request(f"{url}?{urllib.parse.urlencode({'period1': start_time, 'period2': end_time, 'interval': '1d'})}")
    req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read())
    if not data or 'chart' not in data or not data['chart']['result']:
        return None
    bars, currency = bars_from_chart(data['chart']['result'][0])
    return {k: [bar[k] for bar in bars] for k in ('t', 'h', 'l', 'c', 'v')} | {'currency': currency, 'support': None, 'resistance': None}

def generate_svg_chart(symbol, body=None):
    """The chart of one symbol as an SVG picture"""
    try:
        data = chart_inputs(symbol, body)
        if not data:
            return generate_error_svg(f"No data available for {symbol}")
        if len(data['c']) < 50:
            return generate_error_svg(f"Insufficient data for {symbol}")
        return draw_chart(symbol, data)
    except Exception as e:
        return generate_error_svg(f"Error generating chart for {symbol}: {str(e)}")

def moving_average(values, period):
    """The average of the last `period` values at each point; None until there are that many (it used to be padded with
    the first price, which drew a flat line and then a jump)"""
    out, total = [], 0.0
    for i, value in enumerate(values):
        total += value
        if i >= period:
            total -= values[i - period]
        out.append(total / period if i >= period - 1 else None)
    return out

def rsi_series(closes, period=14):
    """RSI the standard way (Wilder's smoothing) at each point; None until there is enough history"""
    out = [None] * len(closes)
    if len(closes) < period + 1:
        return out
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    value = lambda: 100 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss))
    out[period] = value()
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        out[i + 1] = value()
    return out

def support_resistance(highs, lows):
    """The report's own method (calculate_support_resistance_enhanced), for a chart asked for by itself"""
    if len(highs) >= 60 and len(lows) >= 60:
        top, bottom = sorted(highs[-60:], reverse=True)[:5], sorted(lows[-60:])[:5]
        return sum(bottom) / len(bottom), sum(top) / len(top)
    return (min(lows[-20:]) if len(lows) >= 20 else min(lows)), (max(highs[-20:]) if len(highs) >= 20 else max(highs))

def price_text(value, currency='', sign=False):
    """A price for a label: 1,234 / 123.45 / 1.234, with the currency's sign when asked"""
    digits = f"{value:,.0f}" if abs(value) >= 10000 else f"{value:,.2f}" if abs(value) >= 1 else f"{value:.4f}"
    if not sign:
        return digits
    if currency in MINOR_UNITS:
        return digits + MINOR_UNITS[currency]
    if currency in MONEY_SIGNS or not currency:
        return MONEY_SIGNS.get(currency, '$') + digits
    return f"{currency} {digits}"

def axis_text(value):
    """A price short enough for the side of the chart at any size: 52.3k / 3,396 / 290 / 61.85 / 0.4321"""
    size = abs(value)
    return f"{value / 1000:.1f}k" if size >= 10000 else f"{value:,.0f}" if size >= 100 else f"{value:.2f}" if size >= 1 else f"{value:.4f}"

def draw_chart(symbol, data):
    """Price with its 20-, 50- and 200-day averages, support and resistance; volume; RSI.
    No background of its own and mid-tone lettering, so it sits on a light page and on a dark one. Lettering grows when
    the picture is shown small (a phone), through the style rule at the top."""
    closes, highs, lows, volumes, times = data['c'], data['h'], data['l'], data['v'], data['t']
    currency = data.get('currency') or ''
    n = len(closes)
    ma20, ma50, ma200 = moving_average(closes, 20), moving_average(closes, 50), moving_average(closes, 200)
    rsi = rsi_series(closes)
    support, resistance = data.get('support'), data.get('resistance')
    if not isinstance(support, (int, float)) or not isinstance(resistance, (int, float)) or support <= 0 or resistance <= 0:
        support, resistance = support_resistance(highs, lows)

    W, H = 720, 600
    left, right = 70, 14
    plot_w = W - left - right
    price_top, price_h = 70, 270
    vol_top, vol_h = 376, 64
    rsi_top, rsi_h = 474, 84
    x = lambda i: left + (i / (n - 1)) * plot_w

    low_edge = min(min(closes), support)
    high_edge = max(max(closes), resistance)
    pad = (high_edge - low_edge) * 0.06 or high_edge * 0.02 or 1
    low_edge, high_edge = low_edge - pad, high_edge + pad
    py = lambda value: price_top + (1 - (value - low_edge) / (high_edge - low_edge)) * price_h

    def line(values, to_y):
        """An SVG path through the values, leaving out the points that are None"""
        parts, pen_down = [], False
        for i, value in enumerate(values):
            if value is None:
                pen_down = False
                continue
            parts.append(f"{'L' if pen_down else 'M'}{x(i):.1f},{to_y(value):.1f}")
            pen_down = True
        return ''.join(parts)

    change = (closes[-1] / closes[-2] - 1) * 100 if n > 1 and closes[-2] else 0
    tone = '#16a34a' if change > 0 else '#dc2626' if change < 0 else '#64748b'
    out = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-label="{symbol} price chart, one year" style="display:block;width:100%;height:auto;max-width:{W}px" '
           'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif">',
           '<style>text{fill:#64748b;font-size:12px}.h{font-size:18px;font-weight:700}.p{font-size:16px;font-weight:700}'
           '.s{font-size:11px}.g{stroke:#94a3b8;stroke-opacity:.28;stroke-width:1}'
           '.m{display:none}@media (max-width:480px){text{font-size:21px}.h{font-size:26px}.p{font-size:24px}.s{font-size:19px}'
           '.w{display:none}.m{display:inline}}</style>']

    # heading: the symbol, the latest price and the day's change
    out.append(f'<text class="h" x="{left}" y="26">{symbol}</text>')
    out.append(f'<text class="p" x="{W - right}" y="26" text-anchor="end" style="fill:{tone}">{price_text(closes[-1], currency, True)} '
               f'<tspan class="s" style="fill:{tone}">{change:+.2f}%</tspan></text>')
    # legend
    legend = [('Price', '#2563eb', '', ''), ('20-day avg', '#f59e0b', '', ''), ('50-day avg', '#f97316', '', ''),
              ('200-day avg', '#8b5cf6', '5,3', ''), ('Support', '#16a34a', '6,4', ''), ('Resistance', '#dc2626', '6,4', '')]
    # twice: six across for a wide picture; the four lines only, spaced wider, when it is shown small (class m)
    for css, items in (('w', legend), ('m', legend[:4])):
        step = plot_w / len(items)
        for k, (name, colour, dash, _) in enumerate(items):
            lx = left + k * step
            out.append(f'<g class="{css}"><line x1="{lx:.0f}" y1="48" x2="{lx + 18:.0f}" y2="48" stroke="{colour}" stroke-width="3"'
                       + (f' stroke-dasharray="{dash}"' if dash else '') + f'/><text class="s" x="{lx + 23:.0f}" y="52">{name}</text></g>')

    # price panel: grid, levels, lines
    for k in range(5):
        value = low_edge + (high_edge - low_edge) * k / 4
        y = py(value)
        out.append(f'<line class="g" x1="{left}" y1="{y:.1f}" x2="{W - right}" y2="{y:.1f}"/>')
        out.append(f'<text x="{left - 7}" y="{y + 4:.1f}" text-anchor="end">{axis_text(value)}</text>')
    for value, colour, name in ((support, '#16a34a', 'Support'), (resistance, '#dc2626', 'Resistance')):
        y = py(value)
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{W - right}" y2="{y:.1f}" stroke="{colour}" stroke-width="1.5" stroke-dasharray="6,4" stroke-opacity=".8"/>')
        out.append(f'<text class="s" x="{left + 5}" y="{y - 5:.1f}" style="fill:{colour}">{name} {price_text(value)}</text>')
    out.append(f'<path d="{line(ma200, py)}" fill="none" stroke="#8b5cf6" stroke-width="1.6" stroke-dasharray="5,3"/>')
    out.append(f'<path d="{line(ma50, py)}" fill="none" stroke="#f97316" stroke-width="1.6"/>')
    out.append(f'<path d="{line(ma20, py)}" fill="none" stroke="#f59e0b" stroke-width="1.6"/>')
    out.append(f'<path d="{line(closes, py)}" fill="none" stroke="#2563eb" stroke-width="2.2" stroke-linejoin="round"/>')
    out.append(f'<circle cx="{x(n - 1):.1f}" cy="{py(closes[-1]):.1f}" r="3.5" fill="#2563eb"/>')

    # months along the bottom of every panel
    months, last = [], None
    for i, ts in enumerate(times):
        stamp = datetime.utcfromtimestamp(ts)
        if (stamp.year, stamp.month) != last:
            last = (stamp.year, stamp.month)
            if i > 0:
                months.append((i, stamp.strftime('%b') + (" '" + stamp.strftime('%y') if stamp.month == 1 else '')))
    for k, (i, name) in enumerate(months):
        out.append(f'<line class="g" x1="{x(i):.1f}" y1="{price_top}" x2="{x(i):.1f}" y2="{rsi_top + rsi_h}"/>')
        if x(i) < W - right - 20:
            out.append(f'<text class="{"" if k % 2 == 0 else "w"}" x="{x(i):.1f}" y="{rsi_top + rsi_h + 18}" text-anchor="middle">{name}</text>')

    # volume: green on a day the price closed up, red on a day it closed down
    top_volume = max(volumes) or 1
    width = max(1.0, plot_w / n * 0.7)
    up, down = [], []
    for i, volume in enumerate(volumes):
        bar = f"M{x(i):.1f},{vol_top + vol_h:.1f}v{-(volume / top_volume) * vol_h:.1f}"
        (up if i == 0 or closes[i] >= closes[i - 1] else down).append(bar)
    out.append(f'<text class="s" x="{left}" y="{vol_top - 8}">Volume</text>')
    out.append(f'<line class="g" x1="{left}" y1="{vol_top + vol_h}" x2="{W - right}" y2="{vol_top + vol_h}"/>')
    out.append(f'<path d="{"".join(up)}" stroke="#16a34a" stroke-opacity=".75" stroke-width="{width:.1f}" fill="none"/>')
    out.append(f'<path d="{"".join(down)}" stroke="#dc2626" stroke-opacity=".75" stroke-width="{width:.1f}" fill="none"/>')

    # RSI with its 30 and 70 lines
    ry = lambda value: rsi_top + (1 - value / 100) * rsi_h
    latest_rsi = next((value for value in reversed(rsi) if value is not None), None)
    out.append(f'<text class="s" x="{left}" y="{rsi_top - 8}">RSI (14)' + (f': {latest_rsi:.0f}' if latest_rsi is not None else '') + '</text>')
    for level, colour in ((70, '#dc2626'), (30, '#16a34a')):
        out.append(f'<line x1="{left}" y1="{ry(level):.1f}" x2="{W - right}" y2="{ry(level):.1f}" stroke="{colour}" stroke-opacity=".55" stroke-dasharray="4,4"/>')
        out.append(f'<text x="{left - 7}" y="{ry(level) + 4:.1f}" text-anchor="end">{level}</text>')
    out.append(f'<line class="g" x1="{left}" y1="{rsi_top}" x2="{W - right}" y2="{rsi_top}"/><line class="g" x1="{left}" y1="{rsi_top + rsi_h}" x2="{W - right}" y2="{rsi_top + rsi_h}"/>')
    out.append(f'<path d="{line(rsi, ry)}" fill="none" stroke="#8b5cf6" stroke-width="1.8"/>')
    out.append('</svg>')
    # Plain ASCII only: the pages turn this text into a picture with btoa(), which fails on any other character
    return ''.join(out).encode('ascii', 'xmlcharrefreplace').decode('ascii')

'''
src = src[:a] + NEW + src[b:]
# the old helpers the new drawing does not use
for name, nxt in (('def calculate_moving_average(data, period):', 'def calculate_rsi(closes, period=14):'), ('def calculate_rsi(closes, period=14):', 'def create_professional_svg('), ('def create_professional_svg(', 'def generate_error_svg(error_message):')):
    if name in src:
        s = src.index(name); e = src.index(nxt, s + 1); src = src[:s] + src[e:]
compile(src, 'lambda_function_simple.py', 'exec')
open(sys.argv[2], 'w').write(src)
print('written:', len(src.split('\n')), 'lines')
